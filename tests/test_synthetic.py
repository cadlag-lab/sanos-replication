import numpy as np
from scipy.integrate import trapezoid

from sanos.black_scholes import call
from sanos.synthetic import mixture_call, mixture_density, mixture_quotes

WEIGHTS, VOLS, EXPIRY = (0.6, 0.4), (0.3, 0.8), 0.5
GRID = np.linspace(1e-4, 12.0, 200_001)


def test_one_component_is_black_scholes():
    strikes = np.linspace(0.5, 1.5, 11)
    assert np.allclose(
        mixture_call(strikes, 2.0, [1.0], [0.2]), call(1.0, strikes, 0.08)
    )


def test_density_has_unit_mass_and_unit_mean():
    density = mixture_density(GRID, EXPIRY, WEIGHTS, VOLS)
    assert np.isclose(trapezoid(density, GRID), 1.0, atol=1e-6)
    assert np.isclose(trapezoid(GRID * density, GRID), 1.0, atol=1e-5)


def test_density_is_second_strike_derivative_of_call():
    k, h = np.linspace(0.5, 2.0, 16), 1e-3
    up, mid, down = (mixture_call(k + d, EXPIRY, WEIGHTS, VOLS) for d in (h, 0.0, -h))
    second_difference = (up - 2 * mid + down) / h**2
    assert np.allclose(
        second_difference, mixture_density(k, EXPIRY, WEIGHTS, VOLS), atol=1e-5
    )


def test_call_prices_increase_with_expiry():
    strikes = np.linspace(0.3, 3.0, 28)
    early, late = (mixture_call(strikes, t, WEIGHTS, VOLS) for t in (0.25, 0.5))
    assert np.all(late > early)


def test_quotes_bracket_the_model_price():
    strikes = np.linspace(0.5, 1.5, 11)
    quotes = mixture_quotes([0.25, 0.5], strikes, WEIGHTS, VOLS, half_spread=1e-4)
    assert [q.expiry for q in quotes] == [0.25, 0.5]
    for q in quotes:
        price = mixture_call(strikes, q.expiry, WEIGHTS, VOLS)
        assert np.all(q.bid < price) and np.all(price < q.ask)
