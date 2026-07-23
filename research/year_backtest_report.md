# Multi-year reconstruction backtest: v3 vs v3i (2019-2023)

Generated 2026-07-23. Out-of-sample in time: v3/v3i rules were shaped on May-Jul 2026 data,
so 2019-2023 is a genuine historical out-of-sample test of the mechanical rules.

## Data
1,012 sessions, 2019-02-12 to 2023-04-27. NIFTY open/close, S&P 500, and India VIX from Yahoo;
FII net cash from the uploaded NSE cash dataset. Entry score reconstructed from three signals:
gap (proxy for GIFT), US close, and FII flow. **PCR and news are omitted** (news can't be scored
without hindsight; PCR history wasn't sourced). Reproduce:
`python3 research/fetch_history.py --start 2019-02-11 --end 2023-04-27` then
`python3 engine/backtest.py <v3|params.json> --data engine/data/sessions_history.csv`.

## The dominant caveat, up front
Only 3 of 5 signals are reconstructed, so the max |score| is 3. The VIX>16 regime gate requires
a score of 4, so **every high-VIX day is untradeable here** — and 678 of 1,012 days (67%) are
high-VIX, including the entire 2020 COVID crash and much of 2022. The real tradeable universe is
the **334 normal-VIX days**. So this validates normal-VIX behavior only; it says nothing about the
strategy's high-VIX "event capture," which is exactly where its claimed edge lives. Treat every
number below as a normal-VIX-regime result.

## Results (full window, continuous ₹1,00,000)
| Strategy | Final | Return | Max drawdown | W/L | Entries |
|---|---|---|---|---|---|
| v3 (holds overnight) | ₹78,625 | **-21.4%** | **-56.6%** | 26/36 | 62 |
| v3i (same-day exit)  | ₹1,29,277 | **+29.3%** | -24.1% | 32/40 | 72 |

## Per-year (each year reset to ₹1,00,000)
| Year | v3 | v3i |
|---|---|---|
| 2019 (Feb-Dec) | +1.7% (10W/9L) | +3.6% (9W/11L) |
| 2020 | +5.7% (2W/1L) | +1.5% (1W/2L) |
| 2021 | **-24.6%** (3W/12L) | +0.4% (6W/9L) |
| 2022 | **-35.5%** (4W/11L) | -20.9% (5W/14L) |
(2020 shows few trades because COVID pushed VIX>16 for months, freezing entries.)

## What it says
Over ~60-70 out-of-sample trades, **same-day exit (v3i) clearly beat overnight holding (v3)**,
and by a wide margin: +29.3% vs -21.4% on the full window, with roughly half the drawdown
(-24% vs -57%). v3's overnight holding produced poor win rates (25-30%) in 2021-2022 and a
brutal -56.6% peak drawdown — overnight gap risk compounding against it.

This **supports the original walk-forward thesis** (v3i's same-day exit is the more robust
policy) and suggests the recent live result — where v3's one overnight put won +₹6,265 on Jul 22
— was the small-sample luck flagged at the time, not evidence that holding is better.

## What it does NOT say
- Nothing about high-VIX regimes (67% of the period, untradeable without PCR/news). The COVID
  crash and 2022's worst stretches contributed zero trades.
- It's a 3-signal reconstruction with a gap proxy for GIFT and no news, not the live 5-signal v3.
- BS/VIX pricing and daily (not tick) opens are approximations; weekly expiries computed as
  Thursdays (NIFTY's 2019-2023 convention), not holiday-adjusted.

## Use
This is validation and expectation-setting, **not** a tuning input. It strengthens the case for
running v3i as the primary policy and treating v3's overnight hold with suspicion, but the
decision still waits on live paper trading and, ideally, a PCR history to test the high-VIX
regime the strategy is actually built for.
