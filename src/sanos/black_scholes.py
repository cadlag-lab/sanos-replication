"""The Black-Scholes call in total variance, eq. (3), its density and its inverse."""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import brentq
from scipy.special import ndtr


def call(s: ArrayLike, k: ArrayLike, v: ArrayLike) -> NDArray[np.float64]:
    """Call(s, k, v) for spot s > 0, strike k >= 0 and total variance v >= 0.

    At v = 0 or k = 0 this is the intrinsic value (s - k)^+, which is what makes
    eta = 0 in SANOS the linear-interpolation model with no special case.
    """
    s, k, v = np.broadcast_arrays(*(np.asarray(x, dtype=float) for x in (s, k, v)))
    smooth = (v > 0) & (k > 0)
    # placeholders keep log and the division finite where the limit is taken instead
    sqrt_v = np.sqrt(np.where(smooth, v, 1.0))
    d_plus = np.log(s / np.where(smooth, k, s)) / sqrt_v + 0.5 * sqrt_v
    price = s * ndtr(d_plus) - k * ndtr(d_plus - sqrt_v)
    return np.where(smooth, price, np.maximum(s - k, 0.0))


def density(s: ArrayLike, k: ArrayLike, v: ArrayLike) -> NDArray[np.float64]:
    """Second strike derivative of Call(s, k, v), for k > 0 and v > 0.

    It is the density at k of s * Y with Y lognormal, unit mean and log-variance v.
    """
    s, k, v = (np.asarray(x, dtype=float) for x in (s, k, v))
    d_minus = (np.log(s / k) - 0.5 * v) / np.sqrt(v)
    return np.exp(-0.5 * d_minus**2) / (k * np.sqrt(2 * np.pi * v))


def implied_variance(k: ArrayLike, price: ArrayLike) -> NDArray[np.float64]:
    """The v solving Call(1, k, v) = price.

    It is nan where the price is not strictly between the intrinsic value and 1,
    because no variance gives such a price.
    """
    k, price = np.broadcast_arrays(np.asarray(k, float), np.asarray(price, float))
    variance = np.full(k.shape, np.nan)
    for i in np.ndindex(k.shape):
        if max(1 - k[i], 0) < price[i] < 1:
            # Call(1, k, 400) is 1 to machine precision, so the root is bracketed
            variance[i] = brentq(_pricing_error, 0.0, 400.0, args=(k[i], price[i]))
    return variance


def _pricing_error(v: float, k: float, price: float) -> float:
    return float(call(1.0, k, v)) - price
