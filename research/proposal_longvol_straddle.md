# Proposal: cheap-vol long-straddle strategy (v-lv1)

**Type:** long volatility, pre-event / non-directional
**Backtest window:** 2026-05-15 to 2026-07-27 (50 sessions), Rs 1,00,000 virtual, platform BS pricer + friction model
**Status:** proposal only. Paper. In-sample. Not activated.

## The idea in one line
Buy an ATM straddle (call + put, same strike/expiry) at the 9:15 open **only when prior-day India VIX is low**, and exit the same day at close. You are buying cheap volatility and getting paid when a move erupts, in either direction, without having to guess which way.

## Why this fits the problem
Your v3 book is 100% long-premium **directional**: it buys a put or a call off a weak news score. It loses two ways at once, wrong direction guess plus theta bleed in low-VIX chop. A straddle removes the direction guess entirely. Critically, it profits from the exact crash days your directional puts are trying (and failing) to catch: on 08-Jul, a straddle bought when VIX was 11.65 captured the -1.47% move for +Rs 11,759 with no overnight direction call required.

## Backtest results (ranked)

| # | Rule | Return | Trades | Win% | Max DD | Notes |
|---|------|-------:|-------:|-----:|-------:|-------|
| **1** | **vix_prev <= 13, hold to same-day close, 2 lots** | **+25.3%** | 12 | 42% | **-6.6%** | Recommended. Doubles #2 with proportional risk. |
| 2 | vix_prev <= 13, hold to same-day close, 1 lot | +12.6% | 12 | 42% | -3.3% | Conservative sizing of the same edge. |
| 3 | vix_prev <= 12.5 + flat open (gap<=0.3%), hold 2d | +19.5% | 1 | 100% | 0% | Best "buy vol not direction" logic but sample too small to trust. |
| - | **Baseline: buy vol EVERY session, hold 1d** | **-16.5%** | 50 | 30% | -21.8% | Proves the filter is the whole point: always-long-vol bleeds. |
| - | vix_prev <= 13, hold<=3d, +40%/-30% target/stop, 2 lots | -33.3% | 6 | 33% | -37.9% | Mechanical stops DESTROY it, see below. |

## What the backtest taught (the honest version)

1. **The filter is everything.** Being long vol indiscriminately loses -16.5% (theta + friction). Restricting to prior-day VIX <= 13 flips it positive: on quiet days a cheap straddle loses little, and you stay positioned for the one pop.

2. **Do NOT put mechanical target/stop on a straddle.** The -30% stop fires on ordinary intraday wiggle and cuts the convex winners short (turns +25% into -33%). Long vol wants to run to the close. Use a time exit, not a price stop.

3. **Same-day close exit beats holding overnight.** Holding 2+ days in the 13-13.5 VIX band adds theta bleed and overnight gap risk for little gain.

4. **Sizing up works here, cleanly.** Going 1 -> 2 lots roughly doubles return (+12.6% -> +25.3%) with proportional drawdown (-3.3% -> -6.6%). This directly answers your "very less money" point: a straddle deploys ~2x the premium of a single naked option, and the convex payoff scales. Suggested cap: <=30% of equity per entry.

5. **The uncomfortable truth (same as your own v3 report).** Nearly the entire +12.6% comes from ONE day, 08-Jul. Strip the single best trade and it is +Rs 881; strip the best two and it is -Rs 2,368. This is inherent to long vol: you bleed small most days and one eruption pays for everything. It is a **tail-capture / insurance** profile, not a steady-income one. Run it as a convex complement to a premium-selling strategy, not as your only book.

## Caveats
- In-sample on 50 sessions; only ~1 genuine vol eruption in the window. Real expectation is lumpier than the table.
- BS pricing with VIX as an IV proxy; marks at open/close only, no intraday path.
- Expiry assumed clean weekly Tuesdays; holidays not modelled.
- 12-trade sample. Treat return figures as directional evidence, not an expectation.

## Suggested next steps
1. Activate as `v-lv1` paper alongside v3 (registry status `active`, 2 lots, VIX<=13 gate, same-day-close exit, no price stop).
2. Add a **premium-selling** strategy later so the two are anti-correlated (straddle profits when the condor is stressed). That pairing is where a paper book like this usually stabilises.
3. Re-run this backtest monthly as `sessions_2026.csv` grows, to see whether the edge survives out-of-sample.

*Reproduce:* `longvol_backtest.py` (uses the platform's own bs_price + friction constants).
