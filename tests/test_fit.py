"""Claim E0: the fit recovers a known arbitrage-free surface."""

from dataclasses import replace

import numpy as np
import pytest

from sanos.checks import arbitrage_violations
from sanos.fit import atm_bid_variances, fit
from sanos.grid import boundary_strikes, model_strikes
from sanos.synthetic import mixture_call, mixture_density, mixture_quotes

WEIGHTS, VOLS = (0.6, 0.4), (0.3, 0.8)
EXPIRIES = [0.25, 0.5, 1.0]
STRIKES = np.linspace(0.6, 1.6, 21)
HALF_SPREAD = 1e-4
QUOTES = mixture_quotes(EXPIRIES, STRIKES, WEIGHTS, VOLS, HALF_SPREAD)
# for the arbitrage checks: beyond the quoted strikes and between the expiries
CHECK_EXPIRIES = [0.1, 0.25, 0.4, 0.5, 0.75, 1.0]
CHECK_STRIKES = np.linspace(0.02, 5.0, 800)


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


# The smooth model. Tolerances on the density are what this setup achieves, recorded
# so that a regression shows; they are not claims of the paper.
DENSITY_TOLERANCE = {0.06: 0.1, 0.25: 0.01}


@pytest.fixture(scope="module", params=DENSITY_TOLERANCE)
def smooth(request):
    return fit(QUOTES, eta=request.param, max_gap=0.02)


def test_backbone_variances_are_close_to_the_true_ones_at_the_money():
    true = [truth(expiry, 1.0) for expiry in EXPIRIES]
    backbone = atm_bid_variances(QUOTES)
    assert np.all(np.diff(backbone) > 0)
    for expiry, v, price in zip(EXPIRIES, backbone, true, strict=True):
        assert (
            0 < price - mixture_call(1.0, expiry, [1.0], [np.sqrt(v / expiry)]) < 2e-4
        )


def test_smooth_fit_is_inside_bid_ask(smooth):
    for q in QUOTES:
        model = smooth.call(q.expiry, q.strikes)
        assert np.all(q.bid < model) and np.all(model < q.ask)


def test_smooth_density_is_close_to_the_true_density(smooth):
    eta = smooth.smoothing_variances[-1] / atm_bid_variances(QUOTES)[-1]
    k = np.linspace(STRIKES[0], STRIKES[-1], 201)
    for expiry in EXPIRIES:
        true = mixture_density(k, expiry, WEIGHTS, VOLS)
        error = np.abs(smooth.density(expiry, k) - true).max() / true.max()
        assert error < DENSITY_TOLERANCE[round(eta, 2)]


def test_density_is_the_second_strike_derivative_of_the_price(smooth):
    k, h = np.linspace(0.5, 2.0, 16), 1e-3
    for expiry in (0.25, 0.4):  # a model expiry, and one between two
        up, mid, down = (smooth.call(expiry, k + d) for d in (h, 0.0, -h))
        assert np.allclose(
            (up - 2 * mid + down) / h**2, smooth.density(expiry, k), atol=1e-4
        )


def test_linear_model_has_no_density(linear):
    with pytest.raises(ValueError):
        linear.density(0.5, 1.0)


def test_fitted_surfaces_are_arbitrage_free(linear, smooth):
    for surface in (linear, smooth):
        violations = arbitrage_violations(surface.call, CHECK_EXPIRIES, CHECK_STRIKES)
        assert max(violations.values()) < 1e-9, violations


@pytest.mark.parametrize("bid_ask", ["weight", "constrain", "penalize"])
@pytest.mark.parametrize("omega", [0, 1])
def test_every_setting_fits_arbitrage_free_quotes_inside_bid_ask(bid_ask, omega):
    surface = fit(QUOTES, eta=0.25, max_gap=0.02, bid_ask=bid_ask, omega=omega)
    for q in QUOTES:
        assert np.all(np.abs(surface.call(q.expiry, q.strikes) - q.mid) < HALF_SPREAD)


@pytest.mark.parametrize("eta", [0.0, 0.25])
def test_calendar_arbitrage_in_the_quotes(eta):
    # the one-year prices quoted for a one-month expiry: far above the three-month ones
    arbitraged = [replace(QUOTES[-1], expiry=1 / 12), *QUOTES[:-1]]
    with pytest.raises(RuntimeError, match="infeasible"):
        fit(arbitraged, eta=eta, max_gap=0.02, bid_ask="constrain")
    # without the hard constraint there is a fit, which has to leave bid/ask
    surface = fit(arbitraged, eta=eta, max_gap=0.02)
    assert any(
        np.any(np.abs(surface.call(q.expiry, q.strikes) - q.mid) > HALF_SPREAD)
        for q in arbitraged
    )
    violations = arbitrage_violations(surface.call, [1 / 12, 0.25, 0.5], CHECK_STRIKES)
    assert max(violations.values()) < 1e-9, violations


@pytest.mark.parametrize("expiries", [1, 2])
def test_fits_one_or_two_expiries(expiries):
    # with one expiry there is no calendar condition, with two a single one
    surface = fit(QUOTES[:expiries], eta=0.25, max_gap=0.02)
    for q in QUOTES[:expiries]:
        assert np.all(np.abs(surface.call(q.expiry, q.strikes) - q.mid) < HALF_SPREAD)
