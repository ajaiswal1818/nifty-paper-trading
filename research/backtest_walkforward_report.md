# Walk-forward backtest & strategy evolution report
May 15 → Jul 14 2026 · ₹1,00,000 virtual capital · NIFTY weekly options

## Method
- **Train window (A):** May 15 – Jun 12 (21 sessions). High-VIX regime (15–19.6), grinding downtrend, record FII selling, US-Iran headline whipsaw, FOMC + RBI events.
- **Test window (B):** Jun 15 – Jul 14 (21 sessions). Low-VIX regime (11.6–14.7), rallies punctuated by two crash days.
- v2 was tuned ONLY on window A, then run untouched on window B (true out-of-sample).
- v3 was designed after seeing both windows (in-sample everywhere; its real test is live paper trading from Jul 15).
- Morning decisions use only pre-open-knowable info: GIFT Nifty, overnight S&P 500, last published FII net, overnight/weekend news.

## Results matrix

| Strategy | May window (train) | Jun window (test) | Notes |
|---|---|---|---|
| v1 (naive) | **-68.0%** (0W/8L) | +20.2% (5W/4L) | June profit was regime luck |
| v2 (May-tuned) | -25.6% in-sample | **+9.8% out-of-sample** (4W/5L) | defenses work, blunt |
| v3 (both-window) | -9.2% (0W/1L) | +16.9% (4W/4L) | only version that survives both |

**Full "started May 15" simulation (honest path: v1 live through May, upgraded to v2 on Jun 15):
₹1,00,000 → ₹67,253 = -32.7%, max drawdown -67%.**
The May drawdown also shrank position capacity so badly the strategy couldn't afford June's early winning trades — drawdowns compound by locking you out.

## What each generation learned

**v1 → v2 (from May carnage):**
- Reversal churn was the #1 killer: 4 flips in 5 sessions (May 15–21) cost ₹46k. Flipping now needs |score| ≥ 3, entering only ±2.
- High-IV premiums bleed: above VIX 16, trade debit spreads (buy ATM, sell 150 OTM), cutting per-trade loss ~65%.
- Gap-chasing loses: if the open already gapped >0.9% in your direction, the news is priced — skip (saved Jun 8 and Jun 12 whipsaws).
- Stop widened -30% → -35% (noise vs signal), breakeven trail added after +25%.

**v2 → v3 (from June out-of-sample degradation):**
- v2 accidentally held a call AND put simultaneously (Jun 18) paying double theta — v3 forbids opposite-direction entries; direction changes only via reversal exit.
- Above VIX 16, even spreads lost 7/7 in May — v3 demands |score| ≥ 4 there, which stands aside almost entirely in that regime.
- A cooldown-after-stop rule was tried and REJECTED: it blocked the Jul 8 crash-day put (+₹18,879), the strategy's single best trade type. Churn is already contained by the flip threshold.
- Sizing cap tightened 35% → 20% of equity per entry.

## The uncomfortable truths
1. The whole edge, if any, is event capture. Across 10 weeks, profitable months required a crash landing inside the window. v3's May performance is mostly "refusing to play" — which is the correct move but shows the signal itself is weak in chop.
2. v3 is in-sample on both windows. Its +16.9%/-9.2% is a best-case reconstruction, not an expectation. The out-of-sample evidence we do have (v2 on June) says roughly: tuned rules keep about half the naive upside while halving the downside.
3. All caveats from the first backtest still apply: BS/VIX pricing, twice-daily exit checks, ~half the opens estimated, residual hindsight in news scoring, tiny sample.
4. Realistic expectation for v3 live: small losses most weeks, occasional large win when volatility erupts. If VIX stays 11–14 and nothing breaks, expect slow bleed from theta and friction.

## Live deployment
STRATEGY.md updated to v3 as of Jul 14 evening. The scheduled runs (08:45 / 18:00 / 22:00 IST) execute v3 from Jul 15 morning. That is the true out-of-sample test.

Engine: backtest_walkforward.py (all five runs reproducible).
