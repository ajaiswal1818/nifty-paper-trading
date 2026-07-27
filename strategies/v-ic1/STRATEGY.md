# NIFTY Iron Condor income (v-ic1)

**Pure paper trading. No real money. All fills are simulated.**

## Idea
Sell a defined-risk iron condor and hold it toward expiry to harvest theta. This is the
**income / anti-fragile-complement** book: it earns in calm, range-bound chop — exactly the
regime where the directional v3 family and the long-vol straddle (v-lv1) bleed — and it is
strongly negatively correlated (~-0.9 in backtest) with v-lv1, so the straddle offsets the
condor's losses on the days the condor gets hurt.

Backtest (May 15 – Jul 27 2026, hold-to-expiry, buy back a side at 2x credit): condor 300/450,
1 lot returned +7.3%, 64% win, maxDD -6.7%. Undefined-risk short strangles scored higher (+48%)
but are deliberately NOT used — defined risk only, consistent with the platform's high-VIX
debit-spread rule. See `research/premsell_holdtoexpiry_backtest.py`.

## Structure representation (important)
An iron condor is **net-short** and is booked as **two separate position objects**, each a
short credit spread the existing pricer already values via `structure_value(long, short)`:

- **Call side:** sell ATM+`offset_pts` call, buy ATM+`offset_pts`+`wing_pts` call.
  Stored as `{option_type: "call", strike: sold_call, short_strike: protective_call, side: "short"}`.
- **Put side:** sell ATM-`offset_pts` put, buy ATM-`offset_pts`-`wing_pts` put.
  Stored as `{option_type: "put", strike: sold_put, short_strike: protective_put, side: "short"}`.

`entry_premium` per side = that side's credit in points. **`entry_cost_total` is stored NEGATIVE**
per side (the credit is a cash inflow at entry). The `side: "short"` flag tells `engine/monitor.py`
to invert the P&L and stop/target directions (added 2026-07-27). Each side is managed
independently.

## Rules (mechanical, no discretion)

### Entry (morning run only, executed at 9:15 open)
1. Enter only if no condor is currently open and prior-day India VIX >= `vix_entry_min` (0.0 = always).
2. Choose the weekly Tuesday expiry with days-to-expiry <= `dte_max` (6). If the nearest weekly is
   further out than dte_max, wait.
3. ATM = open rounded to nearest 50. Sell the call at ATM+`offset_pts`, buy wing at
   +`offset_pts`+`wing_pts`; sell the put at ATM-`offset_pts`, buy wing at -`offset_pts`-`wing_pts`.
4. `lots` = 1 (tunable to 2). Size so defined max risk
   (`(wing_pts - total_credit) x lot_size x lots`) is <= `size_cap_risk` (15%) of equity.
5. Book both sides as two short positions; add both credits to cash; set each
   `entry_cost_total = -(credit_pts x exit_slippage x lot x lots - 2 x fee_per_leg)`.

### Exit (per side, mechanical — handled by the monitor)
- **Stop:** buy back a side when its value >= `stop_mult` (2.0) x its entry credit.
- **Target:** buy back a side when its value <= (1 - `target_capture`) x entry credit
  (i.e. 50% of the credit captured).
- **Expiry:** `expiry_exit: true` — close any remaining side on/after 15:20 IST on expiry day,
  settling at model value (≈ intrinsic).
- Not an `eod_exit` book: positions are held across days until one of the above fires.

### MTM / P&L sign (net-short)
- Unrealized per side = `(entry_premium - current_premium) x lot_size x lots` (profit as value decays).
- Equity contribution of an open short = `- current_premium x lot_size x lots` (it is a liability;
  the credit already sits in cash).
- Realized on close = `credit_received - buyback_cost`.

### Pricing / friction
Black-Scholes via `engine/pricing.py`, IV = India VIX proxy, r = 6.5%, q = 1.2%. Selling to open =
model x `exit_slippage` (0.985) receive; buying to close = model x `entry_slippage` (1.015) pay;
Rs 100/leg each side (2 legs per side).

### Run schedule (IST)
- 08:45 — enter a condor if none open and rules pass.
- 18:00 / intraday monitor — per-side stop / target / expiry management.
- 22:00 — no trades.

## The number
`state.json → total_equity` minus 1,00,000 = running P&L.

## Status
Created 2026-07-27 as a **candidate**. Requires the `side: "short"` support added to
`engine/monitor.py` (same date). Will NOT be traded until a human flips its registry status to
`active`. Recommended to run alongside v-lv1 (the two are ~-0.9 correlated).
