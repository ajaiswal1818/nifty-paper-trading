# Nifty Next 50 directional, same-day exit (v3i-next50)

**Pure paper trading. No real money. All fills are simulated.**

## What this is
The v3i playbook (buy directional options, exit same day) applied to **Nifty Next 50**
(NIFTYNXT50) options instead of Nifty 50. Separate ₹1,00,000 book. Started 2026-07-24.
The bet is that the same market-direction signal expressed through a higher-beta index
captures more move per correct call. Backtest 2019-2023 (gap+US+FII, vol-corrected IV):
+41.6%, and +27.6% even with 3% slippage, vs Nifty v3i +29.3%. See research/next50_report.md.

## Instrument
- Underlying: **Nifty Next 50** index options (Yahoo/data symbol `^NSMIDCP`). Lot size **25**.
- Expiry: Next-50 options are **monthly**, not weekly. Per NSE contract spec (circular
  NSE/FAOP/68747): expiry is the **last Tuesday of the month** (declared holiday → previous
  trading day). Use the nearest monthly expiry >= 2 days out, read from
  `engine/data/expiries_next50.csv` — do NOT assume last-Thursday (legacy) or improvise.
  (The backtest assumed weekly; monthly theta is slower, so watch live behavior.)
- **Stale-quote guard:** never use a close from `engine/data/sessions_next50.csv` (or any
  historical file) as the live spot — that file ends in 2023 reconstruction data and its last
  rows have leaked into a live run before (03-Aug-2026, spot recorded = 16-Jul close). If no
  live Next-50 quote is fetchable (niftytrader / Yahoo ^NSMIDCP), record the spot as blank and
  make NO entry that run: no sizing on stale data.
- Strikes: round to the nearest listed Next-50 strike (~100 spacing).

## Signals (same market-direction score as the Nifty books)
Score with the v3 signal table, adapted where Next-50 lacks its own feed:
- **gap**: Next-50 has no GIFT feed pre-open; use GIFT Nifty as the market-direction proxy
  (Next-50 tracks the broad market), thresholds ±0.3%.
- **US S&P 500, FII net cash, news**: market-wide, identical to the Nifty books.
- **PCR**: use Nifty PCR as a market-sentiment proxy (no clean Next-50 PCR).
- **IV for pricing / VIX regime gate**: India VIX (Next-50 realized vol was ~equal to Nifty's
  2019-2023, so it's a fair proxy).
Entry threshold |score| >= 2 (>= 4 if prev India VIX > 16). All other v3 rules apply.

## Exit
Same-day only, like v3i: close at the last price by the 15:20 monitor pass (primary) or the
18:00 evening run (fallback). Stop -35%, target +50% (naked)/+40% (spread), breakeven trail
after +25%, all checked intraday. Never held overnight.

## Friction
entry_slippage 1.03 / exit_slippage 0.97 (3% each way) to reflect Next-50's thin liquidity,
vs 1.5% for the liquid Nifty books. This is the key real-world risk: if actual spreads are
wider still, the edge shrinks.

## The number
`state.json -> total_equity` minus 1,00,000 = running P&L.

## What to watch (this is a live test of two unknowns)
1. **Fills**: are Next-50 option spreads workable, or do they eat the edge? The 3% slippage is a
   guess; live fills are the real test.
2. **Monthly expiry**: the same-day-exit edge partly came from dodging weekly theta; on monthly
   options it may differ. Judge against the Nifty v3i book over the same period.
