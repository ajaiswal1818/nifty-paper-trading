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
6. Per active strategy: score sentiment per its `STRATEGY.md` signal table. Gather all overnight inputs directly in this run: the finalized US close (S&P 500, fully closed by ~02:00 IST), fresh GIFT Nifty vs previous NIFTY close, latest published FII/DII, and overnight/weekend global + India news (the Every-run step 2 fetch already covers these). This run is self-sufficient and does not depend on any prior night run.
7. If the score triggers an entry and the strategy's constraints allow: enter per its rules (strike selection, spread vs naked, sizing cap, expiry choice all come from `STRATEGY.md`/`params.json`). Entry price = model value × entry_slippage + fee per leg. Update cash, open_positions, trade_log.csv, increment next_trade_id.
8. Record the sentiment score and each signal's value in the trade_log reason field.
9. **Data capture:** write the day's score into each active strategy's `state.json` as `"morning_score_today": {"date": "YYYY-MM-DD", "score": n}` — even on no-trade days. This is the hindsight-free record the weekly research loop depends on.

## Evening run only (18:00 IST), after the every-run steps
9. **Data capture:** append one row to `engine/data/sessions_2026.csv`: date, today's open, previous close, today's close, VIX close, previous VIX close, and the morning score recorded in `morning_score_today` (0 if the morning run was skipped). Never edit past rows. Add new weekly expiries to `engine/data/expiries.csv` as they become known.
9b. **Flows capture:** append one row to `engine/data/flows_2026.csv`: `date,fii_net_cr,dii_net_cr` = today's session date and today's FII and DII net cash (₹ Cr) as published on this evening's data fetch (the same `fii_net_cash_cr` / `dii_net_cash_cr` written to `market_snapshot`). Use the provisional figure if final is not yet out; leave a field blank only if genuinely unavailable. One row per session, never edit past rows. This is the durable FII/DII series (state.json only holds the latest value and is overwritten each run); it is joined by date for signal backtests, exactly like `research/fii_history.csv`.

## (Removed 2026-07-27) Night run — retired as redundant
The 22:00 IST night run only wrote a provisional `pending_plan` that the 08:45 morning run
re-scored from scratch with better data (finalized US close, fresh GIFT Nifty, latest FII), and
it placed no trades and captured no durable data. Its overnight-news gathering now lives in the
morning run (step 6). Schedule is 08:45 + 18:00 only. Existing `pending_plan` fields in state.json
are harmless leftovers and are simply no longer updated.

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
{"trade_id": n, "underlying": "NIFTY|NIFTYNXT50", "option_type": "call|put", "strike": n, "short_strike": n|null, "expiry": "YYYY-MM-DD", "lots": 1, "lot_size": n, "entry_premium": n, "entry_cost_total": n, "entry_date": "...", "current_premium": n, "sentiment_at_entry": n}
(`short_strike` non-null means a debit spread; premium fields are the net structure value.
`underlying` defaults to NIFTY; NIFTYNXT50 positions use lot_size 25 and are priced against the Next-50 index. Set it from the strategy's `params.json → underlying`.)

## Multi-index strategies (e.g. v3i-next50)
Some strategies trade a different index (params.json → `underlying`). For those:
get the index spot for the RIGHT underlying (Nifty from GIFT/niftytrader; Next-50 from
niftytrader/Yahoo ^NSMIDCP), use India VIX as the IV proxy for all, and score the same
market-direction signals (for Next-50: gap via GIFT Nifty proxy, US/FII/news market-wide,
Nifty PCR as proxy). Strikes and lot size come from that index; expiry cadence may differ
(Next-50 is monthly). The intraday monitor already prices each position against its own
underlying, so it just needs the position's `underlying` field set correctly at entry.

## Adding a strategy (for future sessions)
Create `strategies/<new-id>/` with STRATEGY.md, params.json, state.json (same schema, own virtual capital), empty trade_log.csv/equity_curve.csv with headers, and add an entry to registry.json. Backtest it first with `engine/backtest.py` against `engine/data/`. Registry statuses: `active` (runs trade it), `candidate` (proposed by the research loop, never run until a human flips it to active), `paused`, `retired`.

## Self-adjustment (strict)
Daily runs NEVER change strategy rules or parameters. The weekly research run (RESEARCH_RUNBOOK.md) may only PROPOSE changes; a human accepts them in a normal session, which then edits params.json and appends a dated row to DECISIONS.md. One change at a time.
