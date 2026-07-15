# Runbook for scheduled simulation runs

You are running one cycle of the personal algo-trading platform. **Everything is PAPER TRADING. No real money. Never suggest or place real trades.** Follow this procedure exactly.

## Platform layout
All state lives in `~/Projects/nifty-paper-trading/` (request this folder via directory access if not mounted).

- `strategies/registry.json` — list of strategies; run every one with `"status": "active"`.
- `strategies/<id>/` — per strategy: `STRATEGY.md` (rules), `params.json` (tunables), `state.json` (portfolio), `trade_log.csv`, `equity_curve.csv`.
- `engine/pricing.py` — Black-Scholes pricer (CLI: `SPOT STRIKE VIX DAYS call|put`).
- `engine/backtest.py` + `engine/data/` — research/backtest tooling (not used in live runs).
- `engine/monitor.py` — launchd daemon, polls every 5 min during market hours and executes mechanical exits (stop/target/trail, and EOD close for eod_exit strategies from 15:20 IST). Entries are never made by the monitor.
- `dashboard/build_dashboard.py` — regenerates `dashboard/dashboard.html`; run at the end of every cycle.

## Coordination with the intraday monitor
- Positions may have been closed intraday by the monitor since the last cycle. Always trust `state.json` + `trade_log.csv` as ground truth; never assume a position from a previous cycle is still open.
- Before modifying any state files, create `.monitor.lock` in the platform root; delete it when done (the monitor skips its pass while the lock is fresh, and ignores locks older than 3 minutes).
- The 18:00 evening run remains the fallback EOD-exit executor: if an `eod_exit` strategy still has open positions at the evening run (monitor missed/offline), close them at the day's close.
- If `engine/monitor.log` shows repeated "quote fetch FAILED" lines, tell the user: the monitor's data feed is down and intraday exits are not protecting positions.

## Every run
1. Read `strategies/registry.json`. For each **active** strategy, read its `STRATEGY.md`, `params.json`, and `state.json`.
2. Get live data ONCE and share it across strategies: WebSearch "NIFTY 50 India VIX today", then web_fetch https://www.niftytrader.in/nifty-today (spot, VIX, PCR, FII/DII, pivots). For morning runs also fetch https://www.niftytrader.in/gift-nifty-live and search "US stock market close S&P 500" + "India stock market news today".
3. If it's a weekend or NSE holiday (check search results if unsure), log a skip note in each active strategy's `state.json` and stop.
4. Then, per active strategy:
   a. Reprice all open positions with `engine/pricing.py` (spot, strike, VIX as IV, calendar days to expiry; for spreads price both legs, long minus short). Update `unrealized_pnl` and `total_equity` (cash + sum of position marks × lot_size × lots).
   b. Check exits per that strategy's `STRATEGY.md`. If an exit triggers: sell at model value × exit_slippage − fee per leg, move P&L to realized, update cash, append a row to its `trade_log.csv`.
   c. Append one row to its `equity_curve.csv`.
   d. Write updated `state.json` (set last_run, last_run_type, market_snapshot).
5. Regenerate the dashboard: `python3 dashboard/build_dashboard.py`.

## Morning run only (08:45 IST)
6. Per active strategy: score sentiment per its `STRATEGY.md` signal table (use `pending_plan` from last night's run plus fresh GIFT Nifty and overnight US data).
7. If the score triggers an entry and the strategy's constraints allow: enter per its rules (strike selection, spread vs naked, sizing cap, expiry choice all come from `STRATEGY.md`/`params.json`). Entry price = model value × entry_slippage + fee per leg. Update cash, open_positions, trade_log.csv, increment next_trade_id.
8. Record the sentiment score and each signal's value in the trade_log reason field.
9. **Data capture:** write the day's score into each active strategy's `state.json` as `"morning_score_today": {"date": "YYYY-MM-DD", "score": n}` — even on no-trade days. This is the hindsight-free record the weekly research loop depends on.

## Evening run only (18:00 IST), after the every-run steps
9. **Data capture:** append one row to `engine/data/sessions_2026.csv`: date, today's open, previous close, today's close, VIX close, previous VIX close, and the morning score recorded in `morning_score_today` (0 if the morning run was skipped). Never edit past rows. Add new weekly expiries to `engine/data/expiries.csv` as they become known.

## Night run only (22:00 IST)
6. Search US market open/afternoon status and global news. Per active strategy, write a short `pending_plan` into its `state.json`: {"bias": bullish/bearish/neutral, "score_draft": n, "key_news": [...], "written_at": ...}. No trades.

## Git (every run, after all file updates)
Commit the cycle's changes: `git add -A && git commit -m "<run-type> YYYY-MM-DD: <one-line summary>"`.
Do NOT `git push` from a session (no SSH keys in the sandbox; it will fail). The host launchd agent
`com.nifty.gitsync` pulls/pushes every 15 minutes. If a commit fails on a stale `.git/index.lock`,
delete the lock file and retry once.

## Report (every run)
End by messaging the user a compact summary:
- NIFTY spot, VIX, run type
- Per active strategy: actions taken (entries/exits or "held / no trade") and why, in 1-2 lines
- THE NUMBER per strategy: total_equity and P&L vs its capital_start (e.g. "v3: ₹1,02,340 | +₹2,340 (+2.3%)")

Keep it short. The user mainly wants the P&L numbers.

## Position object schema (open_positions[])
{"trade_id": n, "option_type": "call|put", "strike": n, "short_strike": n|null, "expiry": "YYYY-MM-DD", "lots": 1, "lot_size": 75, "entry_premium": n, "entry_cost_total": n, "entry_date": "...", "current_premium": n, "sentiment_at_entry": n}
(`short_strike` non-null means a debit spread; premium fields are the net structure value.)

## Adding a strategy (for future sessions)
Create `strategies/<new-id>/` with STRATEGY.md, params.json, state.json (same schema, own virtual capital), empty trade_log.csv/equity_curve.csv with headers, and add an entry to registry.json. Backtest it first with `engine/backtest.py` against `engine/data/`. Registry statuses: `active` (runs trade it), `candidate` (proposed by the research loop, never run until a human flips it to active), `paused`, `retired`.

## Self-adjustment (strict)
Daily runs NEVER change strategy rules or parameters. The weekly research run (RESEARCH_RUNBOOK.md) may only PROPOSE changes; a human accepts them in a normal session, which then edits params.json and appends a dated row to DECISIONS.md. One change at a time.
