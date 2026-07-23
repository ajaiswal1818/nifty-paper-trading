# Decision log

One dated row per accepted change to any strategy or platform rule. The weekly research run
proposes; only rows here are real. Newest first.

| Date | Decision | Evidence / rationale |
|---|---|---|
| 2026-07-24 | Added `v3-strong` (entry >=3) as a live paper candidate alongside v3/v3i | Pre-registered 2019-2023 backtest: entry>=3 turned v3 hold from -21.4% to +13.1%, maxDD -57%->-13%; but only ~15 trades, needs forward confirmation |
| 2026-07-23 | One-year (2019-2023) reconstruction backtest run (gap+US+FII, news+PCR omitted) | v3i same-day exit +29.3% vs v3 hold -21.4% out-of-sample (normal-VIX only); supports same-day-exit thesis. See research/year_backtest_report.md |
| 2026-07-15 | Self-adjustment loop added: weekly Sunday research run, proposals-only, tunable_bounds gates, candidate-strategy mechanism | Guardrails against automated overfitting on ~10 trades/month |
| 2026-07-15 | Two-Mac sync moved to git (repo + host gitsync agent); platform moved ~/Documents → ~/Projects | macOS TCC blocked launchd from Documents; git beats iCloud for conflict safety |
| 2026-07-15 | engine/monitor.py launchd daemon added: 5-min intraday exit checks (stop/target/trail; EOD close for eod_exit books from 15:20 IST) | Twice-daily exit checks were the platform's biggest modeling gap |
| 2026-07-15 | v3i-intraday activated as live A/B against v3: identical entries, same-day exit | In-sample: v3i +23.0% vs v3 +7.7% full-range, maxDD -8.9% vs -28.9%; 14 trades, needs live confirmation |
| 2026-07-14 | v3 adopted for live paper from Jul 15 (highvix_entry 4, no_opposite, size_cap 20%) | Walk-forward report: only variant surviving both May and June regimes |
| 2026-07-14 | v2 lessons locked: flip threshold 3, spreads above VIX 16, gap-chase filter 0.9%, stop -35%, breakeven trail at +25% | May window diagnostics (reversal churn -₹46k, high-IV bleed 7/7 losses) |
| 2026-07-14 | Cooldown-after-stop rule REJECTED | Would have blocked the Jul 8 crash-day put (+₹18,879), the strategy's best trade type |
