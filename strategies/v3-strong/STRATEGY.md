# NIFTY News-Directional v3-strong (higher conviction)

**Pure paper trading. No real money. All fills are simulated.**

## What this is
Identical to `v3-news-directional` in every rule EXCEPT the entry threshold: it requires
**|score| >= 3** to enter (v3 uses 2). It holds overnight like v3. Separate ₹1,00,000 book.
Started 2026-07-24 as a live forward-test of the conviction hypothesis.

## Why it exists
Both live losing trades (Jul 17, Jul 20) were minimum-conviction (|score| = 2) entries. A
pre-registered backtest over 2019-2023 (gap+US+FII reconstruction, normal-VIX) showed that
requiring |score| >= 3 turned v3's overnight-hold return from -21.4% to +13.1% and cut max
drawdown from -57% to -13%. It also made v3 (hold) and v3i (same-day) nearly converge, implying
the overnight-hold penalty was concentrated in low-conviction trades. BUT that was one sample of
only ~15 trades. This book exists to confirm or refute it on genuinely unseen forward data.

## Rules
See `../v3-news-directional/STRATEGY.md`. The only change: entry requires |score| >= 3 (normal
VIX) instead of 2. The VIX>16 gate (threshold 4) and all other rules — signal table, gap-chase,
spreads above VIX 16, stops/targets/trail, sizing, no-opposite — are unchanged.

## The number
`state.json -> total_equity` minus 1,00,000 = running P&L.

## Success criterion
Judge against v3 and v3i over the same forward period. The hypothesis is supported only if
v3-strong shows better risk-adjusted results (return and drawdown) than v3 live, over a
meaningful number of trades. Given the higher bar, expect few trades; be patient before concluding.
