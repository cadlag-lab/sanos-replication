"""The conditions of theorem 2.2, checked on a grid for any call price function.

This module knows nothing about the model: it only evaluates prices. That is what lets
it judge a fitted surface without sharing any logic with the fit.
"""

from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import NDArray


def arbitrage_violations(
    call: Callable[[float, NDArray[np.float64]], NDArray[np.float64]],
    expiries: Sequence[float],
    strikes: NDArray[np.float64],
) -> dict[str, float]:
    """The largest violation of each condition on the grid, 0.0 where it holds.

    `call(expiry, strikes)` returns pure call prices. `strikes` are increasing and
    positive, `expiries` increasing. Strike 0 is added to the grid.

    Condition 3 (prices vanish as the strike grows) cannot be seen on a finite grid and
    is not checked. Condition 2 (no mass at zero) is only checked as slope >= -1.
    """
    k = np.concatenate(([0.0], strikes))
    prices = np.array([call(t, k) for t in expiries])  # one row per expiry
    slopes = np.diff(prices, axis=1) / np.diff(k)

    def worst(violation: NDArray[np.float64]) -> float:
        return float(max(violation.max(initial=0.0), 0.0))

    return {
        "unit mean": worst(np.abs(prices[:, 0] - 1)),  # 1. C(T, 0) = 1
        "slope in [-1, 0]": worst(np.maximum(-1 - slopes, slopes)),  # 2. and 7.
        "convex in strike": worst(-np.diff(slopes, axis=1)),  # 4.
        "increasing in expiry": worst(-np.diff(prices, axis=0)),  # 5.
    }
