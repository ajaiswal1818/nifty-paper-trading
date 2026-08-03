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
