"""The arbitrage checker is tested on functions whose violations are known."""

import numpy as np

from sanos.black_scholes import call
from sanos.checks import arbitrage_violations

EXPIRIES = [0.25, 0.5, 1.0]
STRIKES = np.linspace(0.05, 4.0, 400)
VOL = 0.4


def black_scholes(expiry, k):
    return call(1.0, k, VOL**2 * expiry)


def test_black_scholes_has_no_violation():
    violations = arbitrage_violations(black_scholes, EXPIRIES, STRIKES)
    assert max(violations.values()) < 1e-12, violations


def test_each_violation_is_found_and_only_that_one():
    broken = {
        "unit mean": lambda t, k: 0.9 * black_scholes(t, k),
        "slope in [-1, 0]": lambda t, k: black_scholes(t, k) + 0.01 * k,
        "convex in strike": lambda t, k: (
            black_scholes(t, k) + 0.01 * np.sin(20 * k) ** 2
        ),
        "increasing in expiry": lambda t, k: black_scholes(1.25 - t, k),
    }
    for name, surface in broken.items():
        violations = arbitrage_violations(surface, EXPIRIES, STRIKES)
        assert violations[name] > 1e-4, (name, violations)
    only = arbitrage_violations(broken["increasing in expiry"], EXPIRIES, STRIKES)
    assert max(v for name, v in only.items() if name != "increasing in expiry") < 1e-12
