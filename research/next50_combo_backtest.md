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

## Exit redesign attempt (2026-08-03, user-directed) — also fails

Rather than retune, the exit rule was rebuilt from the signal's properties. Three new opt-in
engine primitives were added (`decay_exit`/`decay_level`, `max_hold`, `expiry_buffer`, plus
per-underlying `expiries_file`); all default-off, and all 8 existing backtest baselines verified
**byte-identical** after the change.

**Design pre-registered before running** (each exit answers a distinct question, none chosen
from results):

| Exit | Rationale |
|---|---|
| `decay_exit`, level 1 | thesis-based: hold while the score still leans your way, exit when it stops. The honest "sell on sell signal" — unlike flip-only, it actually fires. |
| `max_hold` 5 | staleness: a morning signal is not a 3-week thesis. |
| `stop` 0.35 | risk: gap protection (the Jul 24→27 lesson on the Nifty books). |
| `expiry_buffer` 7 | structure: never hold a monthly into its final week (extrinsic decay + gamma cliff). |

Result — the pre-registered primary and its one-at-a-time sensitivities, real monthly expiries:

| Config | 2019-23 | 2026 OOS |
|---|---|---|
| **PRIMARY** decay(1) + hold5 + stop35 + buf7 | **−29.2%** | **−31.5%** |
| sens: decay_level 3 (strict) | −4.1% | −4.1% |
| sens: max_hold 3 / 10 / none | −26.7% / +1.6% / +10.2% | −20.1% / −31.5% / −31.5% |
| sens: expiry_buffer 1 | −34.1% | −8.8% |
| sens: no stop / no decay / +target 1.5 | −21.6% / +1.0% / −21.9% | −34.5% / −33.3% / −23.2% |

**Every single cell is negative out-of-sample.** The best (decay_level 3, −4.1%) is the variant
that barely holds at all — it exits the next morning unless the score stays ≥3, i.e. it
converges back toward the same-day book we already run. Meanwhile the in-sample column swings
from −34% to +10% across exit tweaks on 3-6 trades: that spread is noise, and any config picked
from it would be a fit to three trades.

**Conclusion: the exit was not the bottleneck.** A well-designed exit cannot rescue an entry
with no edge. This is consistent with the 2026-07-27 clean out-of-sample finding across the
whole platform (all strategies negative on real 2026 signals) and with the live signal audit
(overnight 7/10 is encouraging but n=10, and it has never been shown to persist beyond one day).

## Verdict

Candidate built (`strategies/v3h-next50/`, registry status `candidate`), **not recommended for
activation on this evidence**: it loses on the only clean out-of-sample data we have (−38.3%
once the expiry is corrected), its headline rule never triggers on that data, and its one
apparent advantage over config A was an artifact of a shared wrong-expiry assumption.

Before this family is worth re-testing, the **exit rule needs redesigning, not re-tuning**:
"flip-only" degenerates to "hold to expiry" on monthly contracts, which is a theta-donation
strategy, not a directional one. Candidate exit designs worth building instead — all human
redesigns, not tunables:

1. flip **or** stop 0.35 (variant E) — the stop is what actually closes positions;
2. flip **or** a max-hold of N sessions (e.g. 3-5), so a dead signal doesn't ride to expiry;
3. flip **or** roll — exit at expiry−7 rather than expiry−1 to keep extrinsic value.

Also worth noting the raw entry side: 25 sessions in 2026 hit |score| ≥ 3, but only 3-6 became
trades (gap-chase filter + one-position-per-direction blocking). Whatever edge the strong-signal
gate has, the current plumbing expresses very little of it.

Any future evaluation must use `engine/data/expiries_next50.csv` (or the last-Tuesday rule) —
the engine's default weekly-Thursday fallback silently produces a different, more favorable
strategy than the one that would trade live.
