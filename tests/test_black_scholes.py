import numpy as np
from scipy.special import ndtr

from sanos.black_scholes import call

STRIKES = np.linspace(0.2, 3.0, 57)


def test_at_the_money_closed_form():
    v = 0.09
    assert np.isclose(call(1.0, 1.0, v), 2 * ndtr(0.5 * np.sqrt(v)) - 1)


def test_zero_variance_is_intrinsic():
    assert np.array_equal(call(1.0, STRIKES, 0.0), np.maximum(1.0 - STRIKES, 0.0))


def test_zero_strike_is_spot():
    assert call(1.3, 0.0, 0.04) == 1.3


def test_tends_to_intrinsic_as_variance_vanishes():
    assert np.allclose(call(1.0, STRIKES, 1e-12), call(1.0, STRIKES, 0.0), atol=1e-6)


def test_homogeneous_in_spot_and_strike():
    assert np.allclose(call(1.7, STRIKES, 0.04), 1.7 * call(1.0, STRIKES / 1.7, 0.04))


def test_shape_in_strike_and_variance():
    prices = call(1.0, STRIKES, 0.04)
    assert np.all(np.diff(prices) < 0)  # decreasing in strike
    assert np.all(np.diff(prices, 2) > 0)  # convex in strike
    assert np.all(call(1.0, STRIKES, 0.05) > prices)  # increasing in variance
    # deep in the money the formula rounds to within one ulp of intrinsic
    assert np.all(prices >= np.maximum(1.0 - STRIKES, 0.0) - 1e-15)
