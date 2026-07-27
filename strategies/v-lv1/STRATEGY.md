# NIFTY Cheap-Vol Long Straddle (v-lv1)

**Pure paper trading. No real money. All fills are simulated.**

## Idea
Buy an ATM straddle (long call + long put, same strike/expiry) at the open **only when
implied volatility is cheap** (prior-day India VIX <= 13), and exit the same day at close.
This is a **non-directional, positive-convexity** book: it bleeds a little on quiet days and
pays off big when a move erupts in either direction. It is designed as a complement to the
directional v3 family and to a premium-selling book, NOT as a standalone income engine.

Backtest (May 15 – Jul 27 2026, 50 sessions, platform BS + friction): vix<=13 / same-day-close /
2 lots returned +25.3%, maxDD -6.6%, 12 trades. Honest caveat: nearly all of it came from the
08-Jul vol eruption. Expect small losses most days, occasional large win. See
`research/proposal_longvol_straddle.md`.

## Structure representation
A straddle is booked as **two independent naked-long positions** in `open_positions[]` — one
`call` and one `put`, same strike, same expiry, `short_strike: null`. This lets the existing
repricer and `engine/monitor.py` handle each leg with no engine changes. Both legs share the
same `trade_id` group is not required; use consecutive trade_ids and note "straddle leg" in the
trade_log reason.

## Rules (mechanical, no discretion)

### Entry (morning run only, executed at 9:15 open)
1. **Vol gate:** enter only if prior-day India VIX (`vix_prev`) <= `vix_entry_max` (13.0).
   If VIX > 13, stand aside (premium too rich, edge disappears).
2. Strike = ATM = open rounded to nearest 50. Expiry = next weekly Tuesday that is at least
   2 calendar days out (never today/tomorrow — same expiry rule as v3).
3. Buy `lots` (default 2) of the ATM call AND `lots` of the ATM put as two naked long legs.
4. **Non-directional:** no sentiment score, no gap filter. `no_opposite` is intentionally OFF
   (the call+put pair is the whole point).
5. **Sizing cap:** total straddle premium must be <= `size_cap` (30%) of current equity.
   If 2 lots would breach the cap, reduce to 1 lot; if 1 lot still breaches, skip.
6. Only one straddle open at a time (`max_positions` = 2 legs). Skip entry if a straddle is
   already open.

### Exit (same-day, no price stop)
- **EOD exit:** close both legs at the day's close (`eod_exit: true`; monitor closes from
  15:20 IST, evening run is the fallback). This is the only exit.
- **No stop / target / trail.** Backtest showed mechanical stops destroy the convexity
  (a -30% stop turned +25% into -33%). Max loss is naturally capped at the premium paid, and
  the same-day exit caps holding time, so no price stop is used. The `stop`/`target`/`trail`
  params are set to unreachable values on purpose.

### Pricing / friction
Identical to v3: Black-Scholes via `engine/pricing.py`, IV = India VIX proxy, r = 6.5%,
q = 1.2%. Entry = model x 1.015 + Rs 100/leg; exit = model x 0.985 − Rs 100/leg. A straddle is
2 legs, so entry/exit friction is charged on both.

### Run schedule (IST)
- 08:45 — score the vol gate, enter the straddle at the modeled 9:15 open if VIX<=13.
- 18:00 — fallback EOD close if the monitor did not already close the legs.
- 22:00 — night: no trades; note tomorrow's vol gate status in `pending_plan`.

## The number
`state.json → total_equity` minus 1,00,000 = running P&L.

## Status
Created 2026-07-27 as a **candidate** (registry status `candidate`). It will NOT be traded by
scheduled runs until a human flips its registry status to `active`.
