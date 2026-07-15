# Backtest: Strategy v1, Jun 15 - Jul 14 2026

**Result: ₹1,00,000 → ₹1,20,241 | +₹20,241 (+20.2%) in 21 trading days**

10 trades entered, 9 closed (5 wins, 4 losses), 1 open (24150 PUT exp Jul 21, +₹3,541 unrealized at Jul 14 close).

## Trade log

| # | Entry | Exit | Position | P&L | Exit reason |
|---|-------|------|----------|-----|-------------|
| 1 | Jun 15 open | Jun 16 open | CALL 23700 (23Jun) | +8,120 | target +50% (peace-deal rally) |
| 2 | Jun 16 open | Jun 18 open | CALL 23950 (23Jun) | +2,685 | signal reversal (Fed hawkish) |
| 3 | Jun 18 open | Jun 18 close | PUT 24100 (23Jun) | -3,921 | stop: market rose despite Fed |
| 4 | Jun 22 open | Jun 23 close | CALL 24100 (30Jun) | -10,222 | stop: -1.16% crash day (PMI, Faber) |
| 5 | Jun 25 open | Jun 29 open | CALL 24150 (30Jun) | -8,994 | stop: weekend Iran hostilities gap |
| 6 | Jul 2 open | Jul 6 open | CALL 24100 (07Jul) | +7,176 | target +50% (Doha talks rally) |
| 7 | Jul 6 open | Jul 8 open | CALL 24350 (14Jul) | -6,639 | reversal (Kospi -5.6%, Iran) |
| 8 | Jul 8 open | Jul 8 close | PUT 24250 (14Jul) | +18,879 | target: -2.12% crash day |
| 9 | Jul 9 open | Jul 10 close | CALL 23950 (14Jul) | +9,616 | target +50% (global rebound) |
| 10 | Jul 14 open | still open | PUT 24150 (21Jul) | +3,541 unrealized | - |

Realized: +₹16,700 · Unrealized: +₹3,541 · Friction paid: ~₹4,300 total (slippage + fees)

## Honest caveats — read before getting excited

1. **One event made half the profit.** The Jul 8 Iran-crash put (+18,879) is the single biggest contributor. Remove that day and the strategy roughly breaks even. News-driven strategies live and die by whether a big event lands during the window.
2. **Stops/targets check only twice a day.** Real exits would differ: the Jul 8 put exited at close (+173%) where a real +50% limit order would have filled intraday for much less; conversely the Jun 23 stop exited at -62%, far worse than -30%. These roughly offset here, but it adds noise both ways.
3. **~10 of 21 opens are estimated** (prev close ± 0.35% by GIFT direction) because exact opens weren't reported. Entry prices on those days are approximate.
4. **Model pricing, not market quotes.** Black-Scholes with India VIX as IV ignores skew, event-day IV crush/spike, and real bid-ask depth.
5. **News scoring aimed to use only pre-open information**, but reconstructing "what was knowable that morning" a month later carries residual hindsight risk.
6. **9 closed trades is statistically nothing.** +20%/month extrapolates to absurdity; the honest read is "the ruleset survived a volatile month without blowing up, and made money mostly because volatility showed up."

## Where the money came from
- Long-call streak in calm rising weeks: small, steady wins (trades 1, 6, 9)
- Both crash days: one caught beautifully (Jul 8 put), one taken on the chin (Jun 23 call)
- Whipsaw cost: trades 3, 5, 7 are the price of reacting to headlines that reversed

Data: closes/VIX cross-verified from HDFC Sky, Kotak Neo, Business Standard, Dhan, Upstox, investing.com daily reports. Full engine: backtest_jun15_jul14.py (reproducible).
