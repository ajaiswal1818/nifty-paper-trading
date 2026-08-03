# Nifty Next 50 strong-signal hold, exit on signal flip (v3h-next50)

**Pure paper trading. No real money. All fills are simulated.**
**STATUS: CANDIDATE — built and backtested, NOT active. A human flips it in registry.json.**

## What this is
User-proposed combination (2026-08-03) of the platform's three "best-leg" hypotheses:
Next-50 underlying (higher beta per correct call) + v3-strong entry gate (|score| ≥ 3, the
strong-signal filter) + **no daily EOD exit — hold until the signal itself flips**. The thesis:
the live signal audit shows the composite score has edge at the overnight/multi-day horizon
(7/10) and none intraday (5/10), so stop selling at 15:20 and stay in until the signal says
otherwise.

## Rules
- Entry: |morning score| ≥ 3 (≥ 4 if prev India VIX > 16), same v3 signal table and Next-50
  adaptations as v3i-next50 (GIFT as gap proxy ±0.3%, Nifty PCR as proxy, India VIX as IV).
  gap-chase 0.9%, no_opposite, size_cap 35%, max 2 positions.
- Exit: **signal flip only** — an opposite-direction morning score with |score| ≥ 3 closes the
  position at that open. Plus the expiry time-stop (close when ≤ 1 day to expiry). There is NO
  mechanical stop, NO profit target, NO trail, NO EOD exit, by design (stop/target params are
  disabling sentinels; see params.json _note).
- Instrument: Next-50 monthly options, lot 25, expiry = last Tuesday of the month
  (`engine/data/expiries_next50.csv`), strikes ~100 spacing. Stale-quote guard applies
  (no live quote → no entry).
- Friction: 3% slippage each way, ₹100/leg fee.

## Honest backtest (2026-08-03, engine/backtest.py on research/sessions_next50_signals.csv)
Full matrix in `research/next50_combo_backtest.md`. Headline, this exact config (D):

| Window | Result | maxDD | W/L |
|---|---|---|---|
| 2019-2023 reconstruction | +22.5% | −28.5% | 16/19 |
| 2026 real-signal OOS (Jan 2–Jul 17), weekly-expiry fallback | −11.7% | −27.2% | 3/3 |
| **2026 real-signal OOS, TRUE monthly expiry (last Tue)** | **−38.3%** | **−39.9%** | **0/3** |

**Two findings that undercut the design, both from the 2026 trade list:**

1. **The flip exit never fires.** All 2026 exits were expiry time-stops; no opposite ≥3 score
   ever arrived while a position was open. On real monthly contracts "exit on signal flip"
   degenerates to **"hold to expiry"** — positions sit 2-4 weeks, block re-entry, and bleed all
   extrinsic value (two of three expired at 0.4 and 3.3 pts).
2. **The expiry assumption was doing the work.** The −11.7% run used the engine's weekly-Thursday
   fallback (3-7 day holds). Corrected to real monthlies it is −38.3%, 0 wins — and the apparent
   edge over v3i-next50 disappears, since that config was run under the same wrong assumption.

Variant E (identical but keeping stop 0.35) is the only member of this family with a defensible
shape, because the stop is what actually closes positions. See the report for three alternative
exit designs worth building before this family is retested.

## Known caveats
1. The backtest engine assumes weekly expiries and force-closes at expiry−1; live Next-50 is
   monthly, so real holds would be longer and theta slower than modeled — untested territory.
2. 2026 OOS is ~6 trades. Tiny n cuts both ways.
3. "Combining the strongest legs" is a selection-on-noise risk: each leg's "strength" was
   measured on a different small sample/regime, and the clean 2026 replay says the underlying
   directional edge is weak-to-negative everywhere.
4. No stop means a gap through the position (like Jul 24→27 on the Nifty books, −₹8.7k) rides
   unprotected until a ≥3 opposite signal appears — which may never come during the drawdown.

## The number
`state.json → total_equity` minus ₹1,00,000 = running P&L.
