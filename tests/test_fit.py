"""Claim E0 for eta = 0: the linear model recovers a known arbitrage-free surface."""

import numpy as np
import pytest

from sanos.fit import fit
from sanos.grid import boundary_strikes, model_strikes
from sanos.synthetic import mixture_call, mixture_quotes

WEIGHTS, VOLS = (0.6, 0.4), (0.3, 0.8)
EXPIRIES = [0.25, 0.5, 1.0]
STRIKES = np.linspace(0.6, 1.6, 21)
QUOTES = mixture_quotes(EXPIRIES, STRIKES, WEIGHTS, VOLS, half_spread=1e-4)


def truth(expiry, k):
    return mixture_call(k, expiry, WEIGHTS, VOLS)


@pytest.fixture(scope="module")
def linear():
    return fit(QUOTES)


def test_reprices_the_quotes(linear):
    for expiry in EXPIRIES:
        assert np.allclose(
            linear.call(expiry, STRIKES), truth(expiry, STRIKES), atol=1e-9
        )


def test_densities_are_probabilities_with_unit_mean(linear):
    for K, q in zip(linear.strikes, linear.densities, strict=True):
        assert np.all(q >= 0)
        assert np.isclose(q.sum(), 1.0) and np.isclose(K @ q, 1.0)


def test_density_is_the_second_difference_of_the_quoted_prices(linear):
    # eq. (7), computed from the true prices without going through the fit. It needs
    # both neighbours to be quoted strikes, which excludes the two outermost ones.
    for j, expiry in enumerate(EXPIRIES, start=1):
        slopes = np.diff(truth(expiry, STRIKES)) / np.diff(STRIKES)
        assert np.allclose(linear.densities[j][2:-2], np.diff(slopes), atol=1e-7)


def test_between_strikes_it_is_the_chord_which_is_too_expensive(linear):
    midpoints = 0.5 * (STRIKES[1:] + STRIKES[:-1])
    for expiry in EXPIRIES:
        at_strikes = truth(expiry, STRIKES)
        chord = 0.5 * (at_strikes[1:] + at_strikes[:-1])
        assert np.allclose(linear.call(expiry, midpoints), chord, atol=1e-9)
        assert np.all(linear.call(expiry, midpoints) > truth(expiry, midpoints))


def test_prices_increase_with_expiry_also_between_model_expiries(linear):
    k = np.linspace(0.05, 4.0, 400)
    prices = np.array([linear.call(t, k) for t in (0.1, 0.25, 0.3, 0.5, 0.75, 1.0)])
    assert np.all(np.diff(prices, axis=0) >= -1e-12)


def test_no_price_outside_the_fitted_expiries(linear):
    with pytest.raises(ValueError):
        linear.call(1.5, 1.0)


def test_extra_model_strikes_fill_gaps_and_keep_the_fit():
    surface = fit(QUOTES, max_gap=0.02)
    assert np.all(np.diff(surface.strikes[1]) <= 0.02 + 1e-12)
    assert set(STRIKES) <= set(surface.strikes[1])
    for expiry in EXPIRIES:
        assert np.allclose(
            surface.call(expiry, STRIKES), truth(expiry, STRIKES), atol=1e-9
        )


def test_boundary_strikes_keep_the_quoted_prices_convex():
    k_min, k_max = boundary_strikes(QUOTES)
    assert 0 < k_min < STRIKES[0] and STRIKES[-1] < k_max
    for q in QUOTES:
        strikes = model_strikes(q.strikes, k_min, k_max, np.inf)
        prices = np.concatenate(([1 - k_min], q.mid, [0.0]))
        assert np.all(np.diff(np.diff(prices) / np.diff(strikes)) >= 0)


def test_smooth_fit_runs_and_stays_close_to_black_scholes():
    # only a smoke test of eta > 0; the smooth model is claim E0's next step
    vol = 0.4
    quotes = mixture_quotes(EXPIRIES, STRIKES, [1.0], [vol], half_spread=1e-4)
    surface = fit(quotes, eta=0.25, variances=vol**2 * np.array(EXPIRIES), max_gap=0.02)
    for expiry in EXPIRIES:
        model = surface.call(expiry, STRIKES)
        assert np.allclose(
            model, mixture_call(STRIKES, expiry, [1.0], [vol]), atol=1e-3
        )
