# Nifty Next 50 experiment: result

Generated 2026-07-24. Data: ^NSMIDCP (Nifty Next 50) daily 2019-2023 from Yahoo, same
gap+US+FII reconstruction as the Nifty study (news+PCR omitted). Research only; not live.

## Why we tried it
Test whether the v3/v3i directional signal works on a different, higher-beta index.

## Result: the signal works at least as well on Next-50 as on Nifty.
| Strategy | Next-50 | Nifty (2019-2023, same method) |
|---|---|---|
| v3i same-day, realistic IV | **+41.6%** (maxDD -14%, 33/40) | +29.3% |
| v3i same-day + 3% slippage | **+27.6%** (maxDD -16%, 32/41) | — |
| v3 hold, realistic IV | +2.9% (maxDD -26%, 27/41) | -21.4% |

Same universal pattern: same-day exit (v3i) beats overnight hold (v3) decisively, and v3i
holds up even under heavy 3% slippage. Plausible story: Next-50's higher-beta, more
news-driven names give an overnight directional signal more to work with.

## Bias check (important)
We price options with India VIX. India VIX is a Nifty gauge, so it could mis-state Next-50
IV. Checked directly: Next-50 realized vol 20.4% vs Nifty 20.9% (ratio 0.97x) over this
window, so India VIX is a fine proxy and the pricing is NOT materially biased. This removes
the main worry.

## The caveats that DO remain, and they're the ones that matter for going live
1. **Liquidity.** Next-50 options are far thinner than Nifty's. We modeled up to 3% slippage
   and it survived, but real spreads on illiquid strikes can be worse, and that is exactly
   where a paper edge quietly dies. This is the make-or-break unknown.
2. **Expiry cadence.** Next-50 options are monthly, not weekly. The backtest assumed weekly
   (Thursday) expiries. Monthly options have slower theta and different dynamics; the same-day
   -exit edge (partly from dodging overnight theta on short weeklies) may not transfer cleanly
   to monthlies. This is a real structural gap between the test and reality.
3. Standard: gap+US+FII only (news+PCR omitted), so high-VIX days (67%) are untradeable and
   this is a normal-VIX result; ~66 trades; synthetic (Next-50 weekly options didn't exist
   2019-2023); BS/VIX pricing and daily opens are approximations.

## Recommendation
The signal result is genuinely promising, the best new finding so far. But unlike v3-strong
(which trades the same liquid Nifty options we already trade), a Next-50 book depends on an
instrument we have NOT confirmed is tradeable at reasonable cost. Before committing a live
paper book: confirm with the broker that Next-50 options have workable liquidity and check the
real expiry cadence (likely monthly). If liquidity is OK, add a Next-50 v3i-style paper book to
forward-test. If the spreads are wide, the modeled edge probably won't survive contact.
