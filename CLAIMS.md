# Claims

The claims of the paper that this repo tests. This table was written before any code.
The "Result" column is filled in as experiments run, including the ones that fail.

| # | Claim | Paper | How we test it | Result |
|---|---|---|---|---|
| E0 | The fit recovers a known arbitrage-free surface | implicit | Synthetic quotes from Black–Scholes and a lognormal mixture; errors against the truth for prices and density | Holds on synthetic data (`tests/test_fit.py`), 3 expiries × 21 strikes, half-spread 1e-4. η = 0: quotes repriced to 1e-9. η = 0.06 and 0.25 with model strikes at most 0.02 apart: all quotes inside bid/ask; density within 10% (η = 0.06) and 1% (η = 0.25) of the true one, relative to its peak. With model strikes only at the quoted strikes (0.05 apart) η = 0.06 leaves bid/ask by one half-spread and the density is off by 20–50%: the model grid has to be finer than the smoothing width |
| E1 | Linear interpolation is "too expensive" between strikes | Fig. 2 | η = 0 against η = 0.25 implied vols between quoted strikes | pending |
| E2 | η trades smoothness of the density against fit | Figs. 3–5, 8 | η ∈ {0, 0.06, 0.25} on a short, a mid and a long expiry | pending |
| E3 | A full surface fits within bid/ask in under a second | §5: 91.4% inside bid/ask, median miss 21% of half-spread, under 1 s on 1000 SPX options | The same three numbers on each Deribit snapshot. The comparison is qualitative because the market differs | pending |
| E4 | Extrapolation beyond quoted strikes is sensible | Fig. 6 | Implied vols on added outer strikes | pending |
| E5 | The surface is strictly arbitrage-free for ω = 0, and not guaranteed to be for ω = 1 | §4.2 | Independent checks on both settings; any violation found with ω = 1 is reported | Synthetic only so far. ω = 0: no violation above 1e-11 in any fit. ω = 1: calendar violations of 1e-5 to 3e-5 in price (0.1 to 0.3 half-spreads) at η = 0.06 and 0.25 once model strikes are added between the quoted ones; where on the surface they sit was not examined. Real data: pending |
| E6 | Mid prices show arbitrage that bid/ask does not | Fig. 1, red dots | Negative mid-implied density points per expiry; feasibility of the hard bid/ask LP | Synthetic only so far: quotes with a calendar arbitrage make the hard bid/ask LP infeasible, and the penalized fit leaves bid/ask while staying arbitrage-free. Real data: pending |

Not tested: the generalized model (§3.4, §4.3).
