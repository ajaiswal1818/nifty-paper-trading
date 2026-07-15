# NIFTY News-Driven Directional v3i (same-day exit)

**Pure paper trading. No real money. All fills are simulated.**

## Setup
- Underlying: NIFTY 50 index options (weekly expiry, Tuesdays)
- Starting capital: ₹1,00,000 (virtual), separate book from v3
- Lot size: 75
- Start date: 2026-07-15
- Variant of v3 with exactly one change: **no overnight holds**. Live A/B against v3-news-directional (identical signals, different exit policy).
- Backtest (in-sample, 14 trades, treat as weak evidence): May -1.9% vs v3's -9.2%; June +24.8% vs +16.9%; maxDD -8.8% vs -26.6%. Reproduce: `engine/backtest.py strategies/v3i-intraday/params.json`.

## Rules (identical to v3 except exits)

### Entry (morning run only, executed at 9:15 open)
Same as v3-news-directional/STRATEGY.md in full: signal table and scoring, regime gate (VIX > 16 requires |score| >= 4 and debit spread; else threshold 2 and naked ATM), gap-chase filter (skip if open gapped > 0.9% in trade direction), never enter if expiry is today/tomorrow, no opposite-direction entries, max 2 positions, max 20% of equity per entry.

### Exit
- **EOD exit (the defining rule): every open position is closed same-day at the last price** (exit slippage × fees apply, reason "eod exit"). No position ever carries overnight. Primary executor: `engine/monitor.py` from 15:20 IST; fallback: the 18:00 run at the close if the monitor was offline.
- Before that, standard checks apply intraday via the monitor's 5-minute polls: stop -35%, target +50% (naked) / +40% (spread), breakeven trail after +25%.
- Time stop and Monday-evening rule are moot (nothing is ever held into another day), but keep the expiry-not-today/tomorrow entry rule so entries always have >= 2 days of time value to sell back.
- Signal reversal exit is moot for the same reason.

### Pricing model & friction
Same as v3: Black-Scholes with India VIX as IV, r 6.5%, q 1.2%, entry at model +1.5% + ₹100/leg, exit at model -1.5% - ₹100/leg.

### Run schedule (IST)
Same three runs: 08:45 entry decision, 18:00 mark + forced EOD exit, 22:00 night plan.

## The number
`state.json → total_equity` minus 1,00,000 = running P&L.

## What this A/B is testing
Whether overnight theta + gap-back costs more than multi-day trend rides earn. In the 10-week backtest, holding overnight donated money in both regimes; the big event wins (e.g. Jul 8 crash put) hit target same-day anyway. If v3i also wins live over 4-6 weeks, retire v3.
