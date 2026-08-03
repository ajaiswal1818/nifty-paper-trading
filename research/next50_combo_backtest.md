# Combined-strategy backtest: Next-50 × strong entry × hold-until-flip — 2026-08-03

User proposal (2026-08-03 session): "combine our strongest strategies — Next-50, |score| ≥ 3,
no 15:20 EOD sell, sell on sell signal only." Built as candidate `v3h-next50`; this is the
supporting evidence. All runs: `engine/backtest.py --data research/sessions_next50_signals.csv`
(real FII-based signals 2019→2026), lot 25, 3% slippage, ₹100/leg, size_cap 0.35, capital ₹1L.

## Matrix

| Config | 2019-23 reconstruction | 2026 real-signal OOS |
|---|---|---|
| A. v3i-next50 as live (entry 2, EOD exit) | +19.0% (DD −19.0%, 70/76) | **−38.7%** (DD −43.4%, 10/19) |
| B. entry 3, EOD exit | −29.4% (DD −30.6%, 23/26) | −7.8% (DD −19.0%, 5/4) |
| C. entry 3, hold, v3 exits (stop/target/trail) | −5.8% (DD −21.2%, 23/23) | −6.2% (DD −26.2%, 3/5) |
| **D. entry 3, hold, flip-only exit (the proposal)** | **+22.5%** (DD −28.5%, 16/19) | **−11.7%** (DD −27.2%, 3/3) |
| E. entry 3, hold, flip + stop 0.35 (no target/trail) | **+41.0%** (DD −19.0%, 17/21) | −11.3% (DD −30.8%, 2/6) |

## Follow-up (same day, after inspecting the trade list) — two findings that change the verdict

**The 2026 window is Jan 2 → Jul 17 2026 (131 sessions, 25 of them |score| ≥ 3)** — the full
year-to-date real-signal series, not a short tail. But printing D's trades exposes two problems:

**(i) The "sell on sell signal only" rule never fired once.** All six 2026 exits are `time stop`
(expiry−1); there is not a single `signal reversal` exit in the window. Every entry was a CALL,
and no opposite ≥3 score arrived while a position was open. So what the matrix actually tested
is **"hold to expiry,"** not "hold until the signal flips." The flip rule is untested, not
validated — on this data it is inert.

**(ii) Corrected to the real monthly expiry, it gets much worse.** The runs above used the
engine's weekly-Thursday fallback (`expiries.csv` doesn't cover Jan-Jun 2026), so modeled holds
were 3-7 days. Re-running D with true Next-50 monthlies (last Tuesday, per the spec pinned
2026-08-03):

| D, 2026 OOS | Result | maxDD | W/L | Trades |
|---|---|---|---|---|
| weekly-expiry fallback (as first run) | −11.7% | −27.2% | 3/3 | 6 |
| **true monthly expiry (correct)** | **−38.3%** | **−39.9%** | **0/3** | 3 |

Holding a monthly contract to expiry−1 means each position sits ~2-4 weeks, blocks re-entry
that whole time (`no_opposite` + max one per direction), and gives back all extrinsic value:
two of the three trades expired near worthless (0.4 and 3.3 pts). The one apparent advantage
over config A therefore does not survive the expiry correction — A was run under the same
weekly fallback, so that comparison was apples-to-apples-wrong.

## Reading

1. **No variant is positive on the clean 2026 out-of-sample window.** The proposal (D) loses
   −11.7% there. This matches the 2026-07-27 finding (DECISIONS): the directional edge itself
   is weak-to-negative on real 2026 signals; recombining its expressions does not create edge.
2. The proposal does beat the **current** v3i-next50 config out-of-sample by a wide margin
   (−11.7% vs −38.7%). Note A's −38.7% is worse than the −8% recorded on 2026-07-27 because
   the size_cap raise (0.20→0.35, accepted 2026-08-02) lets the 2026 replay actually take its
   trades — the old cap had been silently blocking most of them. **The cap that made the book
   untradeable was also suppressing its losses.** Worth weighing when deciding v3i-next50's
   future.
3. **Keeping the stop strictly dominates dropping it** (E vs D: +18.5pp in-sample, +0.4pp OOS,
   and D's no-stop tail risk is structural: a gap through the position rides unprotected until
   an opposite ≥3 signal appears, which can be never during the drawdown).
4. In-sample/OOS split is stark for every hold variant (D: +22.5% → −11.7%). Classic regime
   sensitivity, same lesson as the Nifty v3-vs-v3i A/B (hold won the trending week, lost the
   reversal).
5. Engine caveats: weekly-expiry assumption + expiry−1 time-stop, so modeled holds are ≤ ~1
   week; live monthly contracts would hold longer with slower theta — the flip-only rule is
   effectively untested at its real horizon. 2026 OOS trade counts are single digits.

## Verdict

Candidate built (`strategies/v3h-next50/`, registry status `candidate`), **not recommended for
activation on this evidence**: it loses on the only clean out-of-sample data we have, and its
best property (beating config A out-of-sample) is an argument about A's weakness, not D's
strength. If the user still wants a live A/B leg from this family, variant E (with the stop) is
the defensible one. Suggested next check before any activation: 4–6 more weeks of live morning
scores, then re-run this matrix on 2026-only data that post-dates the proposal (hard rule 5:
never evaluate on the data that suggested it).
