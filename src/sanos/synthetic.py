"""Quotes from a model whose call prices and density are known in closed form.

The model is a mixture of Black-Scholes models: Z_T is lognormal with volatility vols[i]
with probability weights[i]. It is arbitrage-free in strike and in time, because each
component is, and it has a smile whenever the volatilities differ. One component is
plain Black-Scholes.
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from sanos.black_scholes import call
from sanos.quotes import ExpiryQuotes


def mixture_call(
    k: ArrayLike, expiry: float, weights: Sequence[float], vols: Sequence[float]
) -> NDArray[np.float64]:
    """Pure call price E[(Z_T - k)^+]."""
    return sum(
        (
            w * call(1.0, k, vol**2 * expiry)
            for w, vol in zip(weights, vols, strict=True)
        ),
        start=np.zeros(np.shape(k)),
    )


def mixture_density(
    k: ArrayLike, expiry: float, weights: Sequence[float], vols: Sequence[float]
) -> NDArray[np.float64]:
    """Density of Z_T at k > 0: the second strike derivative of the call price."""
    k = np.asarray(k, dtype=float)
    density = np.zeros(k.shape)
    for w, vol in zip(weights, vols, strict=True):
        v = vol**2 * expiry
        d_minus = (-np.log(k) - 0.5 * v) / np.sqrt(v)
        density += w * np.exp(-0.5 * d_minus**2) / (k * np.sqrt(2 * np.pi * v))
    return density


def mixture_quotes(
    expiries: Sequence[float],
    strikes: ArrayLike,
    weights: Sequence[float],
    vols: Sequence[float],
    half_spread: float,
) -> list[ExpiryQuotes]:
    """Quotes whose mid is the exact model price, on the same strikes for every expiry.

    The bid is floored at zero, so the mid of a nearly worthless option sits above its
    model price.
    """
    assert np.isclose(sum(weights), 1.0) and half_spread > 0
    strikes = np.asarray(strikes, dtype=float)
    quotes = []
    for expiry in expiries:
        price = mixture_call(strikes, expiry, weights, vols)
        quotes.append(
            ExpiryQuotes(
                expiry=expiry,
                strikes=strikes,
                bid=np.maximum(price - half_spread, 0.0),
                ask=price + half_spread,
            )
        )
    return quotes
