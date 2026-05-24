# IMC Prosperity 4 — Kernel Wizards write up

> **Final Rank: 934 / 18,803** (top 5%)
> **Peak Rank: 643** (end of Round 3)
> **R2 Manual Highlight:** segmented Monte Carlo on competitor behaviour — modelled
> E[PnL] of **230k**, actual **210k** (within 9% of forecast)

This repository documents our team's run through IMC Prosperity 4, the algorithmic
trading simulation hosted by IMC Trading. It contains the code, the EDA notebooks,
and — more importantly — a candid record of what we learned about quantitative
finance at the practical level: what actually matters when alpha has to survive
contact with a live order book.

---

## Table of Contents

- [Final Result](#final-result)
- [The Story](#the-story)
- [Round-by-Round Breakdown](#round-by-round-breakdown)
- [The R4 Reversal: When Discipline Slipped](#the-r4-reversal-when-discipline-slipped)
- [The R2 Manual Win: Game Theory + Monte Carlo](#the-r2-manual-win-game-theory--monte-carlo)
- [Technical Capabilities Developed](#technical-capabilities-developed)
- [The Timo Diehm Pivot: First Principles](#the-timo-diehm-pivot-first-principles)
- [What We'd Do Differently](#what-wed-do-differently)

---

## Final Result

| Metric | Value |
| --- | --- |
| Final rank | **934 / 18,803** (top 5%) |
| Peak rank | **643** (end of R3) |
| Number of rounds | 5 + manual challenges per round |
| Best single decision | R2 manual: 210k vs 230k modelled |
| Worst single round | R4: deployed an unvalidated options model under time pressure |

The peak-to-final trajectory is the most important fact on this page. We climbed
into the top 4% by the end of R3 and gave a meaningful chunk of it back in R4.
Most of this README exists to explain *why*, and what we'd now do differently.

---

## The Story

We went into Prosperity treating it like a coding competition with a finance
theme. We came out of it understanding that it is, very precisely, a **model-risk**
competition with a coding component. Anyone can write a market-making loop; the
quants who win are the ones whose mental model of the data-generating process
matches the real one — and who have the discipline to stay out of markets where
their model isn't ready.

Rounds 1 through 3 went well because we played to our strengths and resisted the
pull of areas we hadn't modelled properly yet. R1 and R2 were classic market-
making problems on `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT`. R3 introduced
options on `VELVETFRUIT_EXTRACT` — and crucially, we couldn't model those options
profitably in time, so we **deliberately didn't trade them**. The R3 PnL came
entirely from delta-1 trading on `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT`. By the
end of R3 we were sitting at **643rd**.

**R4 was where the wheels came off**, and the reason is not the one we initially
told ourselves. It wasn't that we suddenly miscalibrated something. It's that we
had been *staying out* of options because we knew we couldn't price them well, and
in R4 — under the competitive pressure of the GOAT phase and with counterparty
information unlocked — we decided to start trading them anyway, with a model we
hadn't validated. We tried Black-Scholes and a calibrated IV smile.
`VELVETFRUIT_EXTRACT` is mean-reverting, not log-normal, so the model was
structurally wrong from the first quote. Every option we traded carried a hidden
mispricing.

Late in R4, we tested an Ornstein-Uhlenbeck-based call pricing model against the
same data. **It worked.** The backtests came back positive. But by the time we had
that result, it was too late to swap it into the production trader. We submitted
with the broken model and watched the PnL bleed.

Round 5 was a partial recovery. By then we had absorbed the lesson and rebuilt
the EDA pipeline from scratch on first principles before writing a single line of
trading logic. The notebook `R5_EDA.ipynb` is a record of that pivot.

We finished at **934**. Not the rank we were hoping for in R3, not the rank we
feared after R4. The competition's real value was in the asymmetry: every round
of profit felt like a confirmation of skill, and every round of loss was an
unambiguous, P&L-quantified piece of feedback about which of our assumptions were
wrong — or which of our disciplines we had let slip.

---

## Round-by-Round Breakdown

### Round 1 — "Trading Groundwork"
**Algo:** `ASH_COATED_OSMIUM` (stable, fair value ≈ 10,000) and
`INTARIAN_PEPPER_ROOT`. For OSMIUM, classic market-making with inside-quote logic,
inventory skew, and a hard halt on position limits. For PEPPER_ROOT, a take-cheap-
inventory + passive-bid hybrid (take best ask when below fair, place passive bid
at `best_bid+1` to capture sell-aggressor flow). Parameters were chosen via
cross-validated walk-forward analysis (120 combinations across 8 folds) rather
than hand-tuned, which became our template for every later parameter choice.

**Manual:** *"An Intarian Welcome"* — opening auctions for `DRYLAND_FLAX` and
`EMBER_MUSHROOM` with guaranteed buyback (Flax at 30/unit, Mushroom at 20/unit
minus 0.10 fee). Standard auction pricing: bid such that clearing price minus
buyback price maximises expected profit, allowing for the tie-break-by-higher-
price mechanic and time priority.

### Round 2 — "Growing Your Outpost"
**Algo:** Same two products as R1, with one new wrinkle: a **Market Access Fee
blind auction**. Each team submits a `bid()` value via their `Trader` class; the
top 50% of bids gain access to 25% extra order book volume and pay their bid as a
one-time fee. This is itself a game-theoretic problem — overbid and you waste
XIRECs, underbid and you miss the extra flow. Our trader is `Trader_best.py`,
which combines a regime-aware OSMIUM market maker (calm/active/volatile sizing,
jump detection on standardised return shocks, gamma-style reservation pricing)
with the PEPPER_ROOT taker+maker logic.

**Manual:** *"Invest & Expand"* — allocate 50,000 XIRECs across Research, Scale,
and Speed, where:
- Research grows logarithmically in your investment
- Scale grows linearly
- **Speed is rank-based across all players** (top investor gets 0.9 multiplier, bottom gets 0.1, linear interpolation by rank in between)

The Speed pillar is what makes this game-theoretic: your payoff depends on what
*everyone else* invests. This is where the segmented Monte Carlo went in. See
[The R2 Manual Win](#the-r2-manual-win-game-theory--monte-carlo) below.

### Round 3 — "Gloves Off"
**Algo:** Three product types. `HYDROGEL_PACK` (delta-1, mean-reverting, position
limit 200), `VELVETFRUIT_EXTRACT` (delta-1, position limit 200), and **10
`VELVETFRUIT_EXTRACT_VOUCHER` options** (`VEV_4000` through `VEV_6500`, position
limit 300 each), with TTE shrinking by one day each round.

For Hydrogel: rolling-window z-score with taker thresholds at ±2σ and quarter-
size maker quotes inside ±0.5σ. For Velvetfruit: edge-based take-and-make around
a fair value estimate.

**For the options: we did not trade them.** We spent significant time in
`01_smile_calibration.ipynb` trying to calibrate a Black-Scholes IV smile to the
voucher tape, and the residuals never settled into something we trusted enough to
quote on. Rather than deploy a model we didn't believe in, we sat the options out
entirely. This was the right call. R3 PnL came cleanly from the two delta-1
products, and we ended the round at **rank 643** — our peak.

**Manual:** *"Celestial Gardeners' Guild"* — two-bid sealed auction against
counterparties with reserve prices uniformly distributed at increments of 5
between 670 and 920, with the second bid penalty
`((920 - avg_b2) / (920 - b2))^3` applying when our bid is below the cross-player
mean. Solve for two bids that trade off expected fill rate against margin to fair
(920).

### Round 4 — "The More The Merrier" (and the Reversal)
**Algo:** Same three product types as R3, with one new piece of information:
**counterparty IDs** are now exposed via the `buyer` and `seller` fields on every
`Trade` object. The brief is explicit that some counterparties are informed and
others are noise — the alpha is in identifying which is which.

In principle this is a clear edge. In practice, two things happened:

1. **We decided to start trading the options.** We had been sitting them out in
   R3 and watching other teams capture PnL there; under the competitive pressure
   of the GOAT phase we chose to enter, with the same Black-Scholes-plus-IV-smile
   framework we hadn't trusted enough to deploy in R3. The framework was
   structurally wrong because `VELVETFRUIT_EXTRACT` is mean-reverting, not
   log-normal — Black-Scholes assumes geometric Brownian motion under the
   risk-neutral measure, and nothing the underlying did obeyed that. Every
   `VEV_*` quote we put up was based on the wrong distribution for the underlying.
2. **We tested a stationary-OU options pricing model late in the round, and it
   worked.** The OU formulation gave a positive backtest. We could have switched.
   We didn't, because by the time the validation was done it was too late to
   re-test the integrated trader, harden the parameters, and submit with
   confidence. We submitted the Black-Scholes version and accepted the loss.

The corrected pricing — preserved in `FinalTrader_v3.py` — uses a closed-form
stationary-OU call:

```
C(K) = (θ - K) · Φ(d) + σ_stat · φ(d),   d = (θ - K) / σ_stat
```

with θ ≈ 5247.43 (long-run mean) and σ_stat ≈ 17.0 (stationary standard
deviation). This is the model that would have been right, and that we had the
evidence for, but that we couldn't operationalise in time.

**Manual:** *"Vanilla Just Isn't Exotic Enough"* — `AETHER_CRYSTAL` (GBM, σ=251%
annualised, zero drift) plus 2-week and 3-week vanilla calls/puts and three
exotics: a **chooser option** (3-week, becomes a call or a put after 2 weeks), a
**binary put** (all-or-nothing payoff), and a **knock-out put** (regular put
unless barrier breached). PnL is mark-to-fair-at-expiry, averaged across 100
simulations of the underlying. Buy-and-hold only, no intra-round trading.

### Round 5 — "The Final Stretch"
50 new products across 10 named categories, position limit 10 per product, three
days of price and trade data. The brief is deliberately incomplete — figure out
the structure yourself.

We rebuilt the EDA workflow from the ground up. `R5_EDA.ipynb` is a 7-section
empirical discovery exercise covering, in order:

1. **Foundation** — what is verifiable vs. hypothesised before any analysis runs
2. **Per-product DGP analysis** — stationarity (ADF), Hurst exponent, OU half-
   life, ACF of signed and squared returns (volatility clustering), jump detection
3. **Microstructure analysis** — spread distribution and regimes, order book
   depth and imbalance, the Frankfurt Hedgehogs *wall-mid* construction, one-
   sided book detection, order flow imbalance (OFI), aggressor inference from
   trade prices, trade size distribution
4. **Cross-product structure** — full 50×50 correlation matrix, within-category
   correlation, hierarchical clustering tested against the named categories,
   pairwise cointegration, per-category PCA
5. **Lead-lag analysis** — Granger causality on the most promising pairs
6. **Strategy hypothesis playbook** — per-cluster archetype mapping, FV estimator
   candidates, inventory rules, lead-lag monetisation, Bollinger/z-score specs,
   OFI monetisation, vol-regime gating, **falsification criteria** for each idea
7. **Risk and robustness review**

Every claim in that notebook is grounded in something measurable from the three
days of data. Every parameter range came with a confidence band. No assumption
was treated as fact until it had been tested.

This is the workflow we should have used from R3 onwards.

---

## The R4 Reversal: When Discipline Slipped

R4 cost real rank, and the autopsy is worth writing down explicitly because the
failure mode is not what you'd guess from the PnL chart alone.

The temptation is to summarise R4 as "we miscalibrated the IV smile." That's
true, but it's not the actual lesson. The actual lesson is about **what changed
between R3 and R4**.

**In R3:**
- We knew our options model wasn't ready
- We sat out the options market entirely
- We made our PnL on delta-1 products we *did* understand
- We finished at rank 643 — the best position of the entire competition

**In R4:**
- We still didn't have a validated options model
- We saw other teams making money on options
- We chose to enter anyway, with the same calibration we hadn't trusted in R3
- We discovered, late in the round, that a stationary-OU model worked
- We didn't redeploy in time
- We submitted with the wrong model and lost rank

The model error itself — using Black-Scholes on a mean-reverting underlying — was
a real problem. But the deeper problem was a **discipline problem**, not a
modelling problem. We knew the model wasn't ready. We deployed it anyway, under
competitive pressure, in exchange for the chance of upside we hadn't earned. And
when validation arrived for the right model, we didn't have the time buffer to
act on it because we'd spent that buffer integrating the wrong one.

**What was actually true:**

The underlying was an OU process with a long-run mean θ ≈ 5247.43 and a
stationary standard deviation σ_stat ≈ 17.0. Calls on a stationary underlying
have a closed form that is *not* Black-Scholes. A GBM-priced call on a stationary
process will systematically misprice deep ITM and deep OTM strikes in opposite
directions, which is exactly what the post-mortem in
`PnL_Analysis_-_v5_HK.ipynb` shows.

**What we'd check first now, before any options work:**

- ADF p-value on the underlying (is it stationary?)
- Hurst exponent (is it mean-reverting, random-walk, or trending?)
- OU half-life via AR(1) regression (if mean-reverting, on what timescale?)
- Variance ratio test at multiple horizons (cross-check)

Any one of these would have flagged the problem in R3. Running them in R3 — and
having the OU pricer ready before R4 opened — would have changed the outcome of
the competition.

---

## The R2 Manual Win: Game Theory + Monte Carlo

The R2 manual challenge — *"Invest & Expand"* — has a payoff function

```
PnL ∝ Research(r) × Scale(s) × Speed_rank − budget_used
```

where Research grows logarithmically in your investment, Scale grows linearly,
and **Speed is rank-based**: the highest investor across all players gets a 0.9
multiplier, the lowest gets 0.1, with linear interpolation by rank in between.

This is the part that makes the problem game-theoretic. Our optimal allocation
depends on what *every other player* invests in Speed. The naive approach is to
pick the choice that maximises payoff under a uniform prior over opponents. The
better approach is to model the opponents.

We did the latter. The pipeline:

1. **Segmentation.** Pulled the public rankings data from R1 to identify rough
   skill segments in the competitor population. Top performers behave differently
   from median performers, who behave differently from the long tail.
2. **Behavioural priors.** Assigned a game-theoretic decision rule to each
   segment — broadly, sophisticated players play closer to a Nash mixed strategy
   or exploit the log-curvature of Research, median players anchor on focal
   points like a 33/33/33 split, and the long tail behaves close to uniform
   random.
3. **Monte Carlo.** Sampled opponent profiles from the segmented distribution,
   computed the Speed rank distribution our own choice would land in, evaluated
   our candidate allocations against thousands of opponent draws, and built a
   full distribution of PnL outcomes per allocation.
4. **Decision.** Picked the allocation with the best risk-adjusted expectation,
   with E[PnL] = **230k**.

Realised PnL was **210k**. That is a 9% miss on a forecast built from segmented
behavioural priors and a Monte Carlo over thousands of opponent draws — well
inside the simulation's standard error.

The reason this matters for the rest of the competition is that it was the one
moment where we followed the workflow we now believe in: we refused to assume,
we modelled the actual mechanism (opponent behaviour), we quantified uncertainty,
and we verified the prediction against reality. R4 is what happens when we don't.

---

## Technical Capabilities Developed

These are the skills the competition forced us to develop or sharpen:

**Market microstructure**
- Order book mechanics, matching priority, why "orders fill at *your* price, not the market price" is a strategy-defining constraint
- Spread distribution analysis, regime detection, one-sided book detection
- Order flow imbalance (OFI) as a short-horizon predictor
- Wall-mid construction (Frankfurt Hedgehogs technique) for robust fair-value estimation when the inside book is noisy
- Aggressor inference from trade prices

**Fair-value modelling**
- Stable assets (constant FV, spread capture)
- Mean-reverting assets (OU process, EMA trackers, z-score signals)
- Options on GBM (Black-Scholes) vs. options on OU (closed-form stationary call)
- IV smile calibration — and the failure mode when the underlying assumption is wrong

**EDA and statistical testing**
- ADF stationarity tests, Hurst exponent, OU half-life estimation
- Autocorrelation of signed and squared returns (vol clustering diagnostics)
- Jump detection (return z-scores, threshold tuning)
- Distribution moments, fat-tail diagnostics, Jarque-Bera
- Hierarchical clustering on correlation matrices, PCA per category
- Pairwise cointegration testing within candidate baskets
- Granger causality for lead-lag

**Algorithmic trading logic**
- Market-making with inventory skew and circuit breakers
- Mean-reversion entries with falsification criteria
- Volatility-regime-adaptive order sizing (calm / active / volatile)
- Velocity-breakout filters to stand down during directional moves
- Multi-component strategies (taker for cheap inventory, maker for spread capture)
- Game-theoretic blind-auction bidding (R2 Market Access Fee)

**Game theory and meta-strategy**
- Segmentation of competitor population using public rankings data
- Behavioural prior assignment per segment
- Monte Carlo over opponent action distributions
- Risk-adjusted decision under uncertainty (the R2 manual win)

**The full pipeline**
Signal generation → algo trading logic → backtesting →
PnL attribution → hyperparameter tuning → overfitting tests →
walk-forward validation. Every parameter in our production traders was chosen via
cross-validated walk-forward analysis, not hand-tuned. Flat regions of stability
were preferred over sharp optima.

**Engineering**
- Stateless trader with JSON-serialised `traderData` and corruption fallback
- Bounded history buffers to prevent memory growth
- Defensive coding around malformed order books

**Discipline (the underrated capability)**
- Knowing when *not* to trade. The R3 decision to stay out of the options book
  preserved our peak rank. The R4 decision to enter without a validated model
  cost us. Both are data points in the same lesson.

---

## The Timo Diehm Pivot: First Principles

Mid-competition we read an article by Timo Diehm that genuinely changed how we
think about problems. The frame is:

1. **Verify what is true.** Competition objectives, mechanics, payoff functions
   — write these down explicitly. Anything not on the list is a hypothesis.
2. **Build only on the verified.** Strategies are constructed on top of the
   verified base, not on top of unexamined priors.
3. **Understand the problem deeply, then go further.** Most people stop at
   "deeply enough." The edge is in going further.
4. **Do whatever it takes to win.** Including, especially, throwing away work
   that was based on an assumption that turned out to be wrong — and refusing to
   deploy work that hasn't been verified, even when the leaderboard is moving.

Mapping this back to our performance: R2 manual was the one place we followed
this workflow end-to-end, and the prediction landed within 9% of reality. R3 was
where we *partially* followed it — we refused to deploy the unvalidated options
model. R4 was where we abandoned step 1, deployed under pressure, and validated
the right model only after it was too late.

The R5 EDA notebook is structured around this discipline. Section 1 is literally
titled *"foundation, what is true and verifiable"* and lists what we know vs.
what we are still hypothesising. Every later section closes with a falsification
criterion: what would we need to observe to invalidate this idea?

---

## What We'd Do Differently

Three things, mostly.

**First: validate the DGP before building any pricing or strategy logic on top
of it.** The R4 failure was not a tuning problem, it was a model-selection
problem, and model selection should always come before tuning. ADF, Hurst,
half-life, variance ratio — these are five-minute checks. Run them in R3, not
after R4 closes. If we'd run an ADF test on `VELVETFRUIT_EXTRACT` on day one of
R3, we would have known to build the OU pricer instead of the BS pricer from the
start, and we would have entered R4 with a validated options strategy already in
production.

**Second: never deploy a model we haven't validated, no matter what the
leaderboard is doing.** R3 was the decision we got right (sit out the options
book until the model is ready). R4 was the decision we got wrong (deploy because
others are profiting there). The leaderboard is not a model-validation signal.

**Third: design every parameter choice with a falsification criterion built in.**
Not "this z-score threshold maxes out backtest PnL" but "this z-score threshold
sits in a flat region of stability across folds, and if we observe X regime
change the strategy must reduce size or stop." The Devil's Advocate role from
the multi-agent framework we now use exists precisely to enforce this — its job
is to assume the strategy is wrong and find the fastest path to invalidation.

A few smaller things: tighter PnL attribution between adverse selection vs.
inventory drag vs. spread capture, more aggressive use of cross-validated walk-
forward analysis from day one rather than as a late-round patch, and an earlier
commitment to closed-form fair values where they exist (the OU call formula
applied in R3, not after R4 closed).

---

## Closing Note

Prosperity is not a coding contest. It is a model-risk contest with a coding
component, and the gap between rank 643 and rank 934 is the gap between a team
that knew when to say no to a market and a team that didn't. Everything in this
repository — the EDA pipelines, the falsification criteria, the OU call pricer,
the segmented Monte Carlo for R2 manual — is an attempt to build the workflow
that catches that gap *before* it shows up in the PnL.

934 out of 18,803 is a good result. The lesson in how it could have been better
is worth more than the rank.
