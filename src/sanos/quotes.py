"""The input of a fit: bid/ask quotes of pure call prices, one expiry at a time.

"Pure" is the paper's term (section 2): strikes are divided by the forward and prices by
discount factor times forward, so a quote is on E[(Z_T - k)^+] for a unit-mean
martingale Z.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class ExpiryQuotes:
    expiry: float  # in years
    strikes: NDArray[np.float64]  # pure, increasing
    bid: NDArray[np.float64]
    ask: NDArray[np.float64]

    def __post_init__(self) -> None:
        assert self.expiry > 0
        assert self.strikes.shape == self.bid.shape == self.ask.shape
        assert np.all(np.diff(self.strikes) > 0)
        # the paper assumes a strictly positive spread (section 4.2)
        assert np.all(self.bid >= 0) and np.all(self.ask > self.bid)

    @property
    def mid(self) -> NDArray[np.float64]:
        return 0.5 * (self.bid + self.ask)
