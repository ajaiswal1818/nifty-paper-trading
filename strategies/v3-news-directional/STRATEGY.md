# NIFTY News-Driven Directional Options Simulation

**Pure paper trading. No real money. All fills are simulated.**

## Setup
- Underlying: NIFTY 50 index options (weekly expiry, Tuesdays)
- Starting capital: ₹1,00,000 (virtual)
- Lot size: 75
- Start date: 2026-07-14
- Strategy version: **v3** (walk-forward evolved; v1 May window -68%, v2 out-of-sample +9.8%, v3 survives both regimes: May -9.2%, June +16.9%. See research/backtest_walkforward_report.md; reproduce with `engine/backtest.py v3`)

## Strategy rules (v3 — mechanical, no discretion)

### Entry (morning run only, executed at 9:15 open)
1. Gather signals: overnight US close, GIFT Nifty vs previous NIFTY close, India VIX, PCR, FII/DII flows, major India/global news headlines.
2. Score sentiment using the signal table below.
3. **Regime gate:** if previous-day India VIX > 16, required |score| for entry is 4 (else 2), and any entry must be a debit spread (see 4b).
4. Score >= threshold → BUY CALL structure; score <= -threshold → BUY PUT structure. ATM strike = open rounded to nearest 50.
   4a. VIX <= 16: naked ATM option, 1 lot.
   4b. VIX > 16: debit spread — buy ATM, sell 150 pts OTM same expiry (cuts theta/IV cost ~65%).
5. **Gap-chase filter:** skip entry if the opening gap already moved > 0.9% in the trade's direction (the news is priced; chasing gaps lost money in both test windows).
6. Never enter if expiry is today or tomorrow. Use next weekly.
7. **Never enter opposite to an open position** (no accidental strangles). Direction changes only via the reversal exit, which needs |score| >= 3.
8. Max 2 open positions. Max 20% of current equity deployed per entry as premium.
9. Skip entry if a position in the same direction is already open.

### Signal scoring
| Signal | Bullish (+1) | Bearish (-1) |
|---|---|---|
| GIFT Nifty vs prev close | > +0.3% | < -0.3% |
| US markets overnight (S&P 500) | > +0.5% | < -0.5% |
| FII net cash flow (latest) | > +₹1,000 Cr | < -₹1,000 Cr |
| News sentiment (headlines, judged) | clearly positive | clearly negative |
| PCR | > 1.2 | < 0.8 |
(India VIX > 20 halves position conviction: require score >= +3 / <= -3 to enter.)

### Exit (checked every run, executed at next available price)
- Stop loss: structure value down 35% from entry → exit
- Target: value up 50% from entry (naked) / up 40% (spread) → exit
- Trailing lock: once value has been up 25% at any check, exit if it falls back to entry (breakeven trail)
- Time stop: exit at Monday evening run if position expires Tuesday (never hold into expiry day)
- Signal reversal: opposite signal of |score| >= 3 → exit (a fresh entry the other way is then allowed same morning if entry rules pass)

### Pricing model
Option premiums computed via Black-Scholes:
- Spot: live NIFTY from niftytrader.in / search
- IV: India VIX (proxy; ATM weekly IV runs close to VIX)
- r = 6.5%, q = 1.2% (dividend yield)
- Time: calendar days to expiry / 365
- Friction: entry at model price +1.5%, exit at model price -1.5% (spread + slippage), plus flat ₹100 per side (brokerage/STT approximation)

### Run schedule (IST)
- 08:45 — pre-open: score signals, decide entries/exits, execute at modeled 9:15 open price
- 18:00 — post-close: mark to market at close, check stops/targets, log day P&L
- 22:00 — night: scan US open + global news, pre-score for tomorrow, no trades

## The number
`state.json → total_equity` minus 1,00,000 = running P&L.
Every run appends to trade_log.csv and equity_curve.csv.
