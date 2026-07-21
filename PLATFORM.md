# Personal algo-trading platform (paper only)

One-person platform for designing, backtesting, and paper-running trading strategies.
**No real money, no broker connection. All fills are simulated.**

## How it runs
Claude executes `RUNBOOK.md` on scheduled runs (08:45 / 18:00 / 22:00 IST): fetches live
market data, then updates every strategy marked `active` in `strategies/registry.json`.
Between runs, `engine/monitor.py` (5-min polls, Yahoo ^NSEI/^INDIAVIX) executes mechanical
intraday exits. Judgment lives in the scheduled runs; arithmetic lives in the daemon.

**Where the monitor runs:** on an always-on Oracle Cloud free VM (see SETUP_ORACLE_VM.md),
so exits are checked even when the Mac is off. The VM is the SOLE monitor: it pulls the Mac's
state, runs `engine/monitor_cloud.sh` each 5 min, and pushes back only when a trade fires. The
Mac's local launchd monitor is unloaded to avoid double-exits. If the Mac is off at 08:45 IST
no new entry is made that day (safe), but any open position stays protected by the VM. For a
Mac-only fallback, `com.nifty.monitor.plist` still exists; never run it and the VM at once.

Monitor install (one time, on the run Mac):
`cp ~/Projects/nifty-paper-trading/engine/com.nifty.monitor.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.nifty.monitor.plist`
(The platform lives in ~/Projects, deliberately NOT ~/Documents: launchd background jobs cannot read macOS privacy-protected folders without per-binary Full Disk Access grants.)

## Two-Mac sync (git)
This folder is a git repo. The run Mac owns all state writes (scheduled runs commit each cycle;
the `com.nifty.gitsync` launchd agent auto-commits leftovers and pulls/pushes every 15 min). The
other Mac pulls, and commits only research/docs/strategy edits. Sync agent install (run Mac):
`cp ~/Projects/nifty-paper-trading/engine/com.nifty.gitsync.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.nifty.gitsync.plist`
Check: `engine/monitor.log` (activity) and `engine/monitor.launchd.log` (crashes). Uninstall: `launchctl unload ~/Library/LaunchAgents/com.nifty.monitor.plist`.

## Layout
| Path | What |
|---|---|
| `RUNBOOK.md` | The exact procedure every scheduled run follows |
| `strategies/registry.json` | Which strategies exist and which are active |
| `strategies/<id>/` | One strategy: rules (STRATEGY.md), tunables (params.json), portfolio (state.json), trade_log.csv, equity_curve.csv |
| `engine/pricing.py` | Black-Scholes pricer (importable + CLI) |
| `engine/backtest.py` | Reusable backtest engine (presets v1/v2/v3, any params.json, walk-forward chaining, eod_exit mode) |
| `engine/monitor.py` | Intraday exit daemon (launchd, every 5 min in market hours): repricing + mechanical exits only, never entries |
| `engine/data/` | Historical session data (sessions_2026.csv) and weekly expiries |
| `dashboard/build_dashboard.py` | Regenerates dashboard/dashboard.html (equity curves, positions, trade logs) |
| `research/` | Frozen one-off backtest scripts and reports (provenance for v1→v3 evolution) |

## Workflows
- **Daily P&L**: open `dashboard/dashboard.html`, or read the scheduled-run report message.
- **Backtest an idea**: add rows to `engine/data/sessions_2026.csv` as history accumulates, then
  `python3 engine/backtest.py <preset|params.json> [--from D --to D] [--chain v2:DATE]`.
- **New strategy**: follow "Adding a strategy" in RUNBOOK.md. Backtest before activating.
- **Pause a strategy**: set its `status` to `paused` in registry.json; runs skip it, state is kept.

## History
v1 (naive) lost 68% in the May 2026 high-VIX window. v2 (May-tuned) made +9.8% out-of-sample in June.
v3 (both-window) is live paper from 2026-07-15. Full story: `research/backtest_walkforward_report.md`.
