# SANOS on BTC_20261114T223559Z

Produced by `experiments/deribit.py` at commit `90631f6` from `data/deribit/BTC_20261114T223559Z.json` (sha256 `222674d924f6323f…`), captured 2026-11-14 22:35:59 UTC.

Quotes after each filter of `sanos.deribit.load`: out-of-the-money quotes 509, no bid 69, bid at the minimum tick 37, expiry too thin 29, kept 374.

Errors are in half-spreads. A miss is a model price outside bid/ask; its size is the distance to the nearer of bid and ask. Prices are pure prices, which for Deribit are BTC; the tick is 0.0001.

| Expiry | Days | Forward | Quotes | Pure strikes | ATM bid vol |
| --- | --- | --- | --- | --- | --- |
| 17NOV26 | 2.4 | 63804 | 23 | 0.91 to 1.12 | 65.4% |
| 18NOV26 | 3.4 | 63823 | 24 | 0.89 to 1.14 | 62.6% |
| 20NOV26 | 5.4 | 63847 | 22 | 0.86 to 1.21 | 58.6% |
| 27NOV26 | 12.4 | 63908 | 29 | 0.78 to 1.42 | 50.1% |
| 4DEC26 | 19.4 | 63984 | 22 | 0.78 to 1.25 | 46.4% |
| 25DEC26 | 40.4 | 64198 | 44 | 0.47 to 2.02 | 43.3% |
| 29JAN27 | 75.4 | 64515 | 53 | 0.78 to 1.86 | 42.0% |
| 26MAR27 | 131.4 | 65066 | 50 | 0.54 to 3.07 | 41.9% |
| 25JUN27 | 222.4 | 65994 | 54 | 0.45 to 3.03 | 41.8% |
| 24SEP27 | 313.4 | 66920 | 53 | 0.52 to 3.29 | 41.5% |

## E1: linear interpolation is too expensive between strikes

The bump is the implied volatility halfway between two neighbouring quoted strikes, minus the average of the implied volatilities at the two strikes, in volatility points. A smile without kinks has bumps near zero.

| Fit | Midpoints | Bump > 0 | Median bump | 10% to 90% |
| --- | --- | --- | --- | --- |
| linear (η = 0) | 364 | 99% | 0.04 | 0.01 to 0.26 |
| η = 0.25 | 364 | 8% | -0.01 | -0.04 to -0.00 |

![25DEC26, one standard deviation around the money](e1_between_strikes.png)

## E2: η trades smoothness of the density against fit

The last three columns count the local maxima of the model density over the quoted strikes of a short, a mid and a long expiry: 1 is a single hump.

| Fit | Inside bid/ask | Median miss | Worst error | Maxima 17NOV26 | Maxima 25DEC26 | Maxima 24SEP27 |
| --- | --- | --- | --- | --- | --- | --- |
| linear (η = 0) | 97.9% | 3.46 | 9.96 | atoms | atoms | atoms |
| η = 0.06 | 100.0% | none | 1.00 | 3 | 7 | 3 |
| η = 0.25 | 100.0% | none | 1.00 | 1 | 2 | 1 |
| η = 0.5 | 99.5% | 0.12 | 1.23 | 1 | 2 | 1 |

![17NOV26](e2_17NOV26.png)

![25DEC26](e2_25DEC26.png)

![24SEP27](e2_24SEP27.png)

## E3: a full surface fits within bid/ask in under a second

The η = 0.25 fit of all 10 expiries, as one linear program with 1244 model strikes, took 0.31 s including the construction of the program (0.26 s for η = 0.06, 0.04 s for the linear fit).

| Expiry (years) | Quotes | Inside bid/ask | Median miss | Worst error |
|---|---|---|---|---|
| 0.0066 | 23 | 100.0% | none | 0.56 |
| 0.0093 | 24 | 100.0% | none | 0.35 |
| 0.0148 | 22 | 100.0% | none | 0.77 |
| 0.0339 | 29 | 100.0% | none | 0.86 |
| 0.0531 | 22 | 100.0% | none | 0.55 |
| 0.1107 | 44 | 100.0% | none | 1.00 |
| 0.2066 | 53 | 100.0% | none | 0.63 |
| 0.3600 | 50 | 100.0% | none | 1.00 |
| 0.6093 | 54 | 100.0% | none | 0.41 |
| 0.8586 | 53 | 100.0% | none | 1.00 |
| all | 374 | 100.0% | none | 1.00 |

## E4: extrapolation beyond the quoted strikes

Implied volatility of the η = 0.25 fit at the outermost quoted strikes and 2 at-the-money standard deviations beyond them, as strike: volatility. `nan` means the price has no implied volatility in double precision.

| Expiry | Below | Lowest quote | Highest quote | Above |
| --- | --- | --- | --- | --- |
| 17NOV26 | 0.80: 73.8% | 0.91: 94.4% | 1.12: 66.6% | 1.23: 82.5% |
| 25DEC26 | 0.18: 191.7% | 0.47: 101.4% | 2.02: 77.4% | 2.31: 89.6% |
| 24SEP27 | 0.05: 122.9% | 0.52: 54.9% | 3.29: 48.8% | 4.06: 54.9% |

![17NOV26](e4_17NOV26.png)

![25DEC26](e4_25DEC26.png)

![24SEP27](e4_24SEP27.png)

## E5: strictly arbitrage-free for ω = 0

Largest violation of each condition, in price, on 20 expiries (the fitted ones, the midpoints between them, and half the first) times 5000 strikes from 0.02 to 4.93. Fits are with ω = 0 unless stated.

| Fit | Unit mean | Slope in [-1, 0] | Convex in strike | Increasing in expiry |
| --- | --- | --- | --- | --- |
| linear (η = 0) | 9e-16 | 3e-13 | 8e-13 | 7e-16 |
| η = 0.06 | 7e-13 | 3e-13 | 7e-13 | 4e-14 |
| η = 0.25 | 7e-12 | 3e-13 | 5e-13 | 3e-12 |
| η = 0.5 | 1e-11 | 3e-13 | 7e-13 | 7e-12 |
| linear, dense grid | 3e-16 | 4e-13 | 7e-13 | 3e-16 |
| η = 0.25, ω = 1 | 3e-14 | 3e-13 | 6e-13 | 3e-05 |

## E6: mid prices show arbitrage that bid/ask does not

Inner quoted strikes at which the density implied by three neighbouring mids is negative (a butterfly arbitrage at mid prices):

| Expiry | Inner strikes | Negative |
| --- | --- | --- |
| 17NOV26 | 21 | 1 |
| 18NOV26 | 22 | 0 |
| 20NOV26 | 20 | 1 |
| 27NOV26 | 27 | 5 |
| 4DEC26 | 20 | 0 |
| 25DEC26 | 42 | 8 |
| 29JAN27 | 51 | 8 |
| 26MAR27 | 48 | 7 |
| 25JUN27 | 52 | 5 |
| 24SEP27 | 51 | 11 |

Does a fit exist with every model price inside bid/ask, `bid_ask="constrain"`? linear (η = 0): no, η = 0.06: yes, η = 0.25: yes, η = 0.5: no, linear, dense grid: yes. A linear fit is a set of arbitrage-free prices at the quoted strikes (theorem 2.6), so a yes for either linear fit means that arbitrage-free prices exist inside bid/ask. A no does not show an arbitrage: the fit is also restricted by where its model strikes are.
