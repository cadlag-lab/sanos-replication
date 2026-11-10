"""The strikes on which the model densities live (remark 2.7 and section 4.2)."""

from collections.abc import Sequence
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from sanos.quotes import ExpiryQuotes


def boundary_strikes(quotes: Sequence[ExpiryQuotes]) -> tuple[float, float]:
    """K_min and K_max, shared by all expiries, by the recipe of footnote 9.

    Per expiry, extend the first and the last segment of the mid call prices as straight
    lines. The lower one meets the intrinsic value 1 - K at K*, the upper one meets zero
    at K#. Any boundary strike below K* (above K#) keeps the prices convex once the
    boundary values 1 - K_min and 0 are inserted. The paper takes
    K_min = min K* / 10 and K_max = 1.5 max K#.
    """
    lows, highs = [], []
    for q in quotes:
        k, c = q.strikes, q.mid
        first_slope = (c[1] - c[0]) / (k[1] - k[0])
        last_slope = (c[-1] - c[-2]) / (k[-1] - k[-2])
        if first_slope <= -1 or last_slope >= 0:
            raise ValueError(f"expiry {q.expiry}: mids are not decreasing at the wings")
        lows.append((1 - c[0] + first_slope * k[0]) / (1 + first_slope))
        highs.append(k[-1] - c[-1] / last_slope)
    k_min, k_max = min(lows) / 10, 1.5 * max(highs)
    if k_min <= 0:
        raise ValueError("a lowest-strike mid is below the intrinsic value")
    return k_min, k_max


def model_strikes(
    market_strikes: NDArray[np.float64], k_min: float, k_max: float, max_gap: float
) -> NDArray[np.float64]:
    """K_min, the market strikes and K_max, with gaps over max_gap filled evenly."""
    nodes = np.concatenate(([k_min], market_strikes, [k_max]))
    segments = [
        np.linspace(a, b, max(1, int(np.ceil((b - a) / max_gap))), endpoint=False)
        for a, b in pairwise(nodes)
    ]
    return np.concatenate([*segments, [k_max]])
