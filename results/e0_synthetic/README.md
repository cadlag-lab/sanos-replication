# E0: synthetic quotes from a known model

Produced by `experiments/e0_synthetic.py` at commit `90631f6`.

Model: mixture of Black-Scholes, weights (0.6, 0.4), volatilities (0.3, 0.8). Quotes: expiries [0.25, 0.5, 1.0], 21 strikes from 0.6 to 1.6, mid = model price, half-spread 0.0001.

Errors are in half-spreads. A miss is a model price outside bid/ask; its size is the distance to the nearer of bid and ask.

## linear (η = 0)

Fitted in 11 ms. Largest model strike gap: inf.

| Expiry (years) | Quotes | Inside bid/ask | Median miss | Worst error |
|---|---|---|---|---|
| 0.2500 | 21 | 100.0% | none | 0.00 |
| 0.5000 | 21 | 100.0% | none | 0.00 |
| 1.0000 | 21 | 100.0% | none | 0.00 |
| all | 63 | 100.0% | none | 0.00 |

Largest arbitrage violations on the check grid: unit mean 1e-16, slope in [-1, 0] 3e-14, convex in strike 6e-14, increasing in expiry 1e-16.

## η = 0.06

Fitted in 72 ms. Largest model strike gap: 0.02.

| Expiry (years) | Quotes | Inside bid/ask | Median miss | Worst error |
|---|---|---|---|---|
| 0.2500 | 21 | 100.0% | none | 0.00 |
| 0.5000 | 21 | 100.0% | none | 0.00 |
| 1.0000 | 21 | 100.0% | none | 0.00 |
| all | 63 | 100.0% | none | 0.00 |

Largest arbitrage violations on the check grid: unit mean 7e-13, slope in [-1, 0] 8e-15, convex in strike 6e-14, increasing in expiry 9e-16.

## η = 0.25

Fitted in 63 ms. Largest model strike gap: 0.02.

| Expiry (years) | Quotes | Inside bid/ask | Median miss | Worst error |
|---|---|---|---|---|
| 0.2500 | 21 | 100.0% | none | 0.00 |
| 0.5000 | 21 | 100.0% | none | 0.00 |
| 1.0000 | 21 | 100.0% | none | 0.00 |
| all | 63 | 100.0% | none | 0.00 |

Largest arbitrage violations on the check grid: unit mean 6e-13, slope in [-1, 0] 1e-12, convex in strike 8e-14, increasing in expiry 3e-13.
