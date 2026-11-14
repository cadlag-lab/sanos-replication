"""The strikes on which the model densities live (remark 2.7 and section 4.2)."""

from collections.abc import Sequence
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from sanos.quotes import ExpiryQuotes


def boundary_strikes(quotes: Sequence[ExpiryQuotes]) -> tuple[float, float]:
    """K_min and K_max, shared by all expiries, by the recipe of footnote 9.

    Per expiry, extend the first and the last segment of the mid call prices as straight
    lines (see the comment below for mids that do not allow it). The lower one meets
    the intrinsic value 1 - K at K*, the upper one meets zero at K#. Any boundary
    strike below K* (above K#) keeps the prices convex once the boundary values
    1 - K_min and 0 are inserted. The paper takes K_min = min K* / 10 and
    K_max = 1.5 max K#.
    """
    lows, highs = [], []
    for q in quotes:
        k, c = q.strikes, q.mid
        # Real prices move in ticks, so the outermost mids can be tied or out of order.
        # The line then goes through the nearest quote that gives a usable slope.
        from_first = (c[1:] - c[0]) / (k[1:] - k[0])
        to_last = ((c[-1] - c[:-1]) / (k[-1] - k[:-1]))[::-1]
        first_slope = next((s for s in from_first if s > -1), None)
        last_slope = next((s for s in to_last if s < 0), None)
        if first_slope is None or last_slope is None:
            raise ValueError(f"expiry {q.expiry}: mids are not decreasing at the wings")
        lows.append((1 - c[0] + first_slope * k[0]) / (1 + first_slope))
        highs.append(k[-1] - c[-1] / last_slope)
    k_min, k_max = min(lows) / 10, 1.5 * max(highs)
    if k_min <= 0:
        raise ValueError("a lowest-strike mid is below the intrinsic value")
    return k_min, k_max


def model_strikes(
    market_strikes: NDArray[np.float64],
    k_min: float,
    k_max: float,
    max_gap: float,
    reach: float = np.inf,
) -> NDArray[np.float64]:
    """K_min, the market strikes and K_max, with gaps over max_gap filled evenly.

    Gaps are only filled up to `reach` beyond the outermost market strikes. Further
    out the only model strikes are K_min and K_max.
    """
    low = max(k_min, market_strikes[0] - reach)
    high = min(k_max, market_strikes[-1] + reach)
    nodes = np.unique(np.concatenate(([k_min, low], market_strikes, [high, k_max])))
    # the 1e-9 keeps a gap of exactly max_gap from being split by rounding
    segments = [
        np.linspace(
            a, b, max(1, int(np.ceil((b - a) / max_gap - 1e-9))), endpoint=False
        )
        if low <= a and b <= high
        else [a]
        for a, b in pairwise(nodes)
    ]
    return np.concatenate([*segments, [k_max]])
