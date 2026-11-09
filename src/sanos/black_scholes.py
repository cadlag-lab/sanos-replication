"""The Black-Scholes call in total variance, eq. (3) of the paper."""

import numpy as np
from numpy.typing import ArrayLike, NDArray
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
