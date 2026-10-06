IMC Prosperity 4: Write-up

Result: 934th of 18,803 teams (top 5%). Peak rank was 643, after Round 3.

IMC Prosperity is a simulated trading competition run by IMC Trading. Each round has an algorithmic trading task and a manual challenge. I competed in a team of five. This repo covers the parts I personally worked on, and it is honest about what went wrong.

What I worked on

Round 1

Market making on ASH_COATED_OSMIUM, focused on spread capture.
Passive bid logic for INTARIAN_PEPPER_ROOT.
Solved the manual challenge (auction pricing) and achieved the highest possible score.

Round 2

Worked out an optimal bid for the market access auction, based on expected profit.
Tested changes to the market making logic using the new data. None beat my existing strategy, so I kept it, and it performed well.
Manual challenge: a teammate built the Monte Carlo and the game theory framework. I used our analysis to model competitor behaviour and forecast PnL. The forecast was 230k and the actual result was 210k.

Round 3

Wrote the options trader: Black-Scholes pricing, Greeks and implied volatility, with an Ornstein-Uhlenbeck (OU) mean reversion adjustment to fair value for the mean-reverting underlying.
The full submitted trader is in trader_FINAL_r3.py. Round 3 was our best round.

Round 4

Deployed a Black-Scholes implied volatility smile framework for the options. We never properly justified it, and it lost money. See below.

Round 5

Microstructure analysis: order flow imbalance, spread distributions and related work.
Product categorisation was done by teammates, not me.
What went wrong in Round 4

In Round 3 we priced options with a Black-Scholes model plus an OU drift adjustment. In Round 4 we switched to an IV smile framework. We had not effectively tested whether it suited the underlying, which is mean-reverting and not log-normal, and the PnL was negative, which costed us a chunk of our rank.

The lesson is simple: changing the pricing model between rounds needs evidence first. Before swapping models, check the data-generating process (stationarity tests, half-life, variance ratios) and backtest the new version against the old one. We changed it because it looked reasonable, and that wasn't enough.

Known limitations of the Round 3 code

I'd do several things differently now:

Hard-coded parameters. The OU speed, long-run mean fallback, edge thresholds and the delta approximation used for high strikes were set by hand. I did not estimate the OU half-life from data.

No walk-forward validation on those parameters.

One desk quotes full size without checking the book, so it can cross the spread and take bad prices.

Inventory logic on one product limits size by absolute position, so it can't always reduce risk when it should.

Limited handling of empty or one-sided order books. Several functions would raise an error on a malformed book.

What I took from it

Microstructure basics: spread capture, inventory risk, order flow imbalance.

Pricing options in Python from scratch (Black-Scholes, Greeks, implied volatility) and why the model has to match the process.

Working in a team of five where each person owned different roles.

Writing down what failed, and why.

Files

trader_FINAL_r3.py: the Round 3 trader (requires IMC's datamodel module to run).
