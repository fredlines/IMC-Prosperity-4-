from __future__ import annotations
import json
import math
import numpy as np
from statistics import NormalDist
from datamodel import Order, OrderDepth, TradingState

# --- MATH CORE (Locked Baseline) ---
_PHI = NormalDist()
def norm_cdf(x): return _PHI.cdf(x)
def norm_pdf(x): return _PHI.pdf(x)

def bs_call(S, K, T, sig):
    if T <= 0 or sig <= 0: return max(S - K, 0.0)
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return S * norm_cdf(d1) - K * norm_cdf(d2)

def bs_delta(S, K, T, sig):
    if T <= 0 or sig <= 0: return 1.0 if S > K else 0.0
    return norm_cdf((math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T)))

def bs_vega(S, K, T, sig):
    if T <= 0 or sig <= 0: return 0.0
    return S * math.sqrt(T) * norm_pdf((math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T)))

def implied_vol(target, S, K, T):
    lo, hi = 1e-6, 0.01
    if target <= max(S - K, 0.0): return lo
    for _ in range(30):
        mid = (lo + hi) / 2
        if bs_call(S, K, T, mid) > target: hi = mid
        else: lo = mid
    return (lo + hi) / 2

class Trader:
    # --- BASELINE CONSTANTS ---
    HP_MEAN, HP_LIMIT = 9991.0, 200 
    VE_LIMIT, VEV_LIMIT = 200, 300

    def __init__(self):
        self._mem = {}

    def _gel_desk(self, book, held, hp_hist):
        """LOCKED BASELINE (11k)"""
        out, hp_px = [], (max(book.buy_orders) + min(book.sell_orders)) / 2
        hp_hist.append(hp_px); hp_hist = hp_hist[-50:]
        vol = np.std(hp_hist) if len(hp_hist) > 10 else 15.0
        curr_lim = int(200 * min(1.0, 30.0 / vol))
        fair = 9991.0 - int((held / curr_lim) * 6)
        dev = hp_px - fair
        if abs(dev) > 22.0:
            b, a = max(book.buy_orders), min(book.sell_orders)
            qty = min(200 - abs(held), sum(abs(v) for v in (book.buy_orders if dev > 0 else book.sell_orders).values()))
            if qty > 0: out.append(Order("HYDROGEL_PACK", b if dev > 0 else a, -qty if dev > 0 else qty))
        self._mem["hp_hist"] = hp_hist
        return out

    def _titan_mr_desk(self, tag, book, held, S, E_dS):
        """NEW: OU-Titan Hybrid Quoter"""
        out = []
        # Fair = Current Price + Expected Mean-Reversion Drift
        fair = S + E_dS
        
        # Aggressive inventory skew: lean into the reversion
        buy_px = int(math.floor(fair - 1 - (held / self.VE_LIMIT) * 2))
        sell_px = int(math.ceil(fair + 1 - (held / self.VE_LIMIT) * 2))
        
        rb, rs = self.VE_LIMIT - held, self.VE_LIMIT + held
        if rb > 0: out.append(Order(tag, buy_px, rb))
        if rs > 0: out.append(Order(tag, sell_px, -rs))
        return out

    def _david_leg(self, tag, book, held, edge):
        """LOCKED BASELINE CORE"""
        b, a = max(book.buy_orders), min(book.sell_orders)
        mid = (b + a) / 2
        prior = self._mem.get(f"oema_{tag}", mid)
        edge_fair = prior - 0.005 * held
        edge_need = max(edge, (a - b) * 1.5)
        self._mem[f"oema_{tag}"] = prior + 0.0003 * (mid - prior)
        if a <= edge_fair - edge_need: return [Order(tag, a, min(30, -book.sell_orders[a], 300 - held))]
        elif b >= edge_fair + edge_need: return [Order(tag, b, -min(30, book.buy_orders[b], 300 + held))]
        return []

    def _comp_mr_desk(self, tag, strike, book, held, S, T_rem, sigma, sigma_eff, E_dS):
        """LOCKED BASELINE MR"""
        b, a = max(book.buy_orders), min(book.sell_orders)
        if strike <= 5000:
            edge, theo_bs = 1.5, bs_call(S, strike, T_rem, sigma)
            theo = theo_bs + (bs_delta(S, strike, T_rem, sigma) * E_dS + bs_vega(S, strike, T_rem, sigma) * (sigma_eff - sigma))
        else:
            edge, intrinsic = 0.5, max(S - strike, 0)
            d_emp = (0.3 + 0.4 * min(intrinsic / 100.0, 1.0)) if S > strike else (0.1 + 0.2 * max(1.0 - (strike - S) / 200.0, 0.0))
            theo = ((b + a) / 2) + d_emp * E_dS
        orders = []
        if a < theo - edge: orders.append(Order(tag, a, min(30, -book.sell_orders[a], 300 - held)))
        if b > theo + edge: orders.append(Order(tag, b, -min(30, book.buy_orders[b], 300 + held)))
        return orders

    def run(self, state: TradingState):
        self._mem = json.loads(state.traderData) if state.traderData else {}
        bundle, spot_od = {}, state.order_depths.get("VELVETFRUIT_EXTRACT")
        if not spot_od or not spot_od.buy_orders: return {}, 0, json.dumps(self._mem)
        
        S = (max(spot_od.buy_orders) + min(spot_od.sell_orders)) / 2
        s_hist = self._mem.get("s_hist", [])
        s_hist.append(S); s_hist = s_hist[-2000:]
        self._mem["s_hist"] = s_hist
        
        # 1. Hydrogel (Untouched)
        if "HYDROGEL_PACK" in state.order_depths:
            bundle["HYDROGEL_PACK"] = self._gel_desk(state.order_depths["HYDROGEL_PACK"], state.position.get("HYDROGEL_PACK", 0), self._mem.get("hp_hist", []))

        # --- OU Calculations for Drift ---
        T_rem = max(30000 - (state.timestamp // 100), 100)
        mu = sum(s_hist) / len(s_hist) if len(s_hist) > 50 else 5270.0
        kappa = math.log(2.0) / 30000.0
        E_dS = (mu - S) * (1.0 - math.exp(-kappa * T_rem))

        # 2. Extract (NEW: OU-Titan Hybrid)
        bundle["VELVETFRUIT_EXTRACT"] = self._titan_mr_desk("VELVETFRUIT_EXTRACT", spot_od, state.position.get("VELVETFRUIT_EXTRACT", 0), S, E_dS)

        # 3. Options (Untouched MR Logic)
        var_rat = (1.0 - math.exp(-2.0 * kappa * T_rem)) / (2.0 * kappa * T_rem)
        ivs = []
        for opt in ["VEV_5200", "VEV_5300"]:
            if opt in state.order_depths:
                od = state.order_depths[opt]
                ivs.append(implied_vol((max(od.buy_orders) + min(od.sell_orders)) / 2, S, int(opt[-4:]), T_rem))
        sigma = sum(ivs) / len(ivs) if ivs else 0.000207
        sigma_eff = sigma * math.sqrt(var_rat)

        for k in [4000, 4500, 5000, 5200, 5400, 5500]:
            tag = f"VEV_{k}"
            if tag in state.order_depths: bundle[tag] = self._comp_mr_desk(tag, k, state.order_depths[tag], state.position.get(tag, 0), S, T_rem, sigma, sigma_eff, E_dS)
        for k in [5100, 5300]:
            tag = f"VEV_{k}"
            if tag in state.order_depths: bundle[tag] = self._david_leg(tag, state.order_depths[tag], state.position.get(tag, 0), 14.0 if k==5100 else 8.0)

        return bundle, 0, json.dumps(self._mem)