# Short-premium (iron condor) experiment: result

Generated 2026-07-23. Engine: `research/backtest_shortvol.py` (shares `engine/pricing.py`).
Data: reconstructed 2019-2023 (gap+US+FII, normal-VIX tradeable). Research only; NOT wired live.

## Hypothesis
The opposite of v3: in calm, range-bound markets, COLLECTING theta (selling a defined-risk
short iron condor) should beat PAYING it (buying options). Entry on low-VIX, low-|score| days;
sell OTM call spread + put spread; keep the credit if NIFTY stays in range; loss capped by wings.

## Result: the hypothesis is not supported here.
| Config | With fees | Frictionless | Trades | W/L |
|---|---|---|---|---|
| 2% OTM strikes (default) | -90.7% | — | 103 | 38/65 |
| 1% OTM strikes (closer) | -78.1% | **-20.9%** | 71 | 42/29 |
| 1.5% OTM strikes | -86.8% | — | 96 | 47/49 |

Two independent problems, both real:

1. **Friction dominates.** A 4-leg condor at ₹100/leg costs ₹800 per round trip. Over ~70 trades
   that's ~₹57k of pure cost on a ₹1,00,000 account. The closer-strike config loses 78% with fees
   but only 21% without them — roughly 57 points of the loss is transaction cost alone.
2. **Negative edge even frictionless.** At -20.9% with zero fees, the raw strategy still loses.
   It wins a majority of trades (42/29) but the breach losses are larger than the frequent small
   wins — the classic short-premium payoff, and here it nets negative.

## The caveat that stops this being a final verdict
The profit source of real premium-selling is the **implied-vs-realized volatility premium**
(option IV tends to sit above subsequent realized vol). Our pricer values options with Black-Scholes
using India VIX as IV at BOTH entry and exit, so it captures time decay and directional P&L but does
**not** embed a systematic IV>RV premium. That is precisely the edge a premium-seller harvests, so
this backtest is structurally ill-suited to evaluate short premium fairly and likely understates it.

## Conclusion / recommendation
Do not wire a short-premium condor into the live platform. On the evidence here it loses, and our
tooling can't fairly test the one mechanism that could make it work. Pursuing it properly would need
(a) a pricing model that separates implied from realized vol, and (b) far lower per-leg friction than
a retail flat fee on 4 legs. Neither is worth building now.

The more promising, far cheaper avenue is `v3-strong` (the conviction finding), now running live.
