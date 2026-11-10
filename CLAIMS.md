# Claims

The claims of the paper that this repo tests. This table was written before any code.
The "Result" column is filled in as experiments run, including the ones that fail.

| # | Claim | Paper | How we test it | Result |
|---|---|---|---|---|
| E0 | The fit recovers a known arbitrage-free surface | implicit | Synthetic quotes from Black–Scholes and a lognormal mixture; errors against the truth for prices and density | η = 0: holds for prices (`tests/test_fit.py`). η > 0 and density: pending |
| E1 | Linear interpolation is "too expensive" between strikes | Fig. 2 | η = 0 against η = 0.25 implied vols between quoted strikes | pending |
| E2 | η trades smoothness of the density against fit | Figs. 3–5, 8 | η ∈ {0, 0.06, 0.25} on a short, a mid and a long expiry | pending |
| E3 | A full surface fits within bid/ask in under a second | §5: 91.4% inside bid/ask, median miss 21% of half-spread, under 1 s on 1000 SPX options | The same three numbers on each Deribit snapshot. The comparison is qualitative because the market differs | pending |
| E4 | Extrapolation beyond quoted strikes is sensible | Fig. 6 | Implied vols on added outer strikes | pending |
| E5 | The surface is strictly arbitrage-free for ω = 0, and not guaranteed to be for ω = 1 | §4.2 | Independent checks on both settings; any violation found with ω = 1 is reported | pending |
| E6 | Mid prices show arbitrage that bid/ask does not | Fig. 1, red dots | Negative mid-implied density points per expiry; feasibility of the hard bid/ask LP | pending |

Not tested: the generalized model (§3.4, §4.3).
