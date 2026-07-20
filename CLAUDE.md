# Orientation for any Claude chat working in this folder

This is a **personal, paper-only algo-trading platform**. No real money, no broker
connection, all fills simulated. Never suggest or place real trades. If asked to go
live with real execution, build the integration but leave order placement to the user.

**Read first:** `PLATFORM.md` (map of the whole system), then `RUNBOOK.md` (what the
scheduled runs do) and `DECISIONS.md` (dated history of every rule change and why).

## What's here
- `strategies/registry.json` + `strategies/<id>/` — each strategy's rules (STRATEGY.md),
  tunables (params.json), portfolio (state.json), trade_log.csv, equity_curve.csv.
  Active now: `v3-news-directional` (holds overnight) and `v3i-intraday` (same-day exit),
  a live A/B on the same signals.
- `engine/` — pricing.py (Black-Scholes), backtest.py (reusable), monitor.py (launchd
  intraday exit daemon), git_sync.sh + plists.
- `dashboard/build_dashboard.py` → dashboard.html (regenerated each run).
- `research/` — frozen backtests and weekly `proposals/`.

## Ground rules for edits
- This Mac is the RUN machine: scheduled runs and the monitor write all state here.
  Only edit state files (`state.json`, trade logs, equity curves) if you ARE the run.
- It's a git repo synced to GitHub. Commit after changes; do NOT push from a session
  (no SSH keys) — the host `com.nifty.gitsync` agent pushes every 15 min.
- Self-adjustment is proposals-only: daily runs never change rules; the weekly research
  run may only propose, inside each param's `tunable_bounds`; a human accepts one change
  at a time and logs it in DECISIONS.md.
- Delete-permission and stale `.git/index.lock` / `HEAD.lock` files may need clearing.

## The number
Each strategy's P&L = `state.json → total_equity` minus its `capital_start` (₹1,00,000).
