import numpy as np

from sanos.fit import fit
from sanos.quotes import ExpiryQuotes
from sanos.report import (
    fit_metrics,
    metrics_table,
    mid_density,
    plot_expiry,
    spread_errors,
)
from sanos.synthetic import mixture_density, mixture_quotes

# four quotes with half-spread 0.01, and a "surface" that prices them at chosen
# distances from the mid: 0, 0.5, 1.5 and 3 half-spreads
QUOTE = ExpiryQuotes(
    expiry=1.0,
    strikes=np.array([0.8, 0.9, 1.0, 1.1]),
    bid=np.array([0.29, 0.19, 0.09, 0.04]),
    ask=np.array([0.31, 0.21, 0.11, 0.06]),
)


class Priced:
    def call(self, expiry, strikes):
        return QUOTE.mid + 0.01 * np.array([0.0, 0.5, -1.5, 3.0])


def test_errors_are_in_half_spreads():
    assert np.allclose(spread_errors(QUOTE, Priced()), [0.0, 0.5, -1.5, 3.0])


def test_metrics():
    metrics = fit_metrics([QUOTE], Priced())
    assert metrics.quotes == 4 and metrics.inside == 0.5
    assert np.isclose(metrics.median_miss, 1.25)  # the misses are 0.5 and 2 outside
    assert np.isclose(metrics.worst, 3.0)


def test_a_price_on_the_edge_of_bid_ask_is_inside():
    class OnTheAsk:
        def call(self, expiry, strikes):
            return QUOTE.ask

    metrics = fit_metrics([QUOTE], OnTheAsk())
    assert metrics.inside == 1.0 and np.isnan(metrics.median_miss)


def test_table_has_a_row_per_expiry_and_a_total():
    table = metrics_table([QUOTE], Priced()).splitlines()
    assert len(table) == 4 and table[-1].startswith("| all | 4 | 50.0% | 1.25 | 3.00 |")


def test_mid_density_is_the_true_density_and_turns_negative_under_arbitrage():
    strikes = np.linspace(0.6, 1.6, 101)
    (q,) = mixture_quotes([0.5], strikes, [1.0], [0.4], half_spread=1e-5)
    at, implied = mid_density(q)
    assert np.allclose(implied, mixture_density(at, 0.5, [1.0], [0.4]), atol=1e-2)

    bumped = q.bid.copy()
    bumped[50] += 1e-3  # one mid far above its neighbours
    _, implied = mid_density(ExpiryQuotes(q.expiry, strikes, bumped, bumped + 2e-5))
    assert implied[49] < 0


def test_figure_renders(tmp_path):
    quotes = mixture_quotes([0.25, 0.5], np.linspace(0.6, 1.6, 21), [1.0], [0.4], 1e-4)
    surfaces = {"linear": fit(quotes), "smooth": fit(quotes, eta=0.25, max_gap=0.02)}
    figure = plot_expiry(
        quotes[1], surfaces, lambda k: mixture_density(k, 0.5, [1.0], [0.4])
    )
    figure.savefig(tmp_path / "figure.png")
    assert len(figure.axes) == 4 and (tmp_path / "figure.png").stat().st_size > 0
