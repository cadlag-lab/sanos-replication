"""How well a surface fits the quotes: numbers, and one figure per expiry.

Nothing here depends on how the surface was fitted. A surface is anything with
`call(expiry, strikes)`; the figure also uses `density` and the model's attributes.
"""

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

from sanos.black_scholes import implied_variance
from sanos.quotes import ExpiryQuotes
from sanos.surface import Surface

# A price this far outside bid/ask still counts as inside: it is the feasibility
# tolerance of the LP solver, and the "penalize" fit puts prices exactly on the edge.
INSIDE_TOLERANCE = 1e-7


def spread_errors(q: ExpiryQuotes, surface: Surface) -> NDArray[np.float64]:
    """(model - mid) / half-spread per quote: inside bid/ask means within [-1, 1]."""
    return (surface.call(q.expiry, q.strikes) - q.mid) / (0.5 * (q.ask - q.bid))


def mid_density(q: ExpiryQuotes) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """The density implied by the mids at the inner quoted strikes, as in eq. (23).

    It is the second difference of the mid prices over the local strike spacing.
    A negative value is a butterfly arbitrage between three neighbouring mids.
    """
    k = q.strikes
    slopes = np.diff(q.mid) / np.diff(k)
    return k[1:-1], np.diff(slopes) / (0.5 * (k[2:] - k[:-2]))


@dataclass(frozen=True)
class FitMetrics:
    quotes: int
    inside: float  # share of quotes whose model price is inside bid/ask
    # Over the quotes outside bid/ask: median distance to the nearer of bid and ask, in
    # half-spreads. This is our reading of "of those options not fitted the median
    # error is 21% of half spread" in section 5. nan when every quote is inside.
    median_miss: float
    worst: float  # largest |model - mid| in half-spreads


def fit_metrics(quotes: Sequence[ExpiryQuotes], surface: Surface) -> FitMetrics:
    """Metrics pooled over the given expiries; pass one expiry for a breakdown."""
    errors = np.concatenate([np.abs(spread_errors(q, surface)) for q in quotes])
    half_spreads = np.concatenate([0.5 * (q.ask - q.bid) for q in quotes])
    outside = (errors - 1) * half_spreads > INSIDE_TOLERANCE
    return FitMetrics(
        quotes=len(errors),
        inside=float(np.mean(~outside)),
        median_miss=float(np.median(errors[outside] - 1)) if outside.any() else np.nan,
        worst=float(errors.max()),
    )


def metrics_table(quotes: Sequence[ExpiryQuotes], surface: Surface) -> str:
    """A markdown table with one row per expiry and a row for all of them."""
    rows = [(f"{q.expiry:.4f}", fit_metrics([q], surface)) for q in quotes]
    rows.append(("all", fit_metrics(quotes, surface)))
    lines = [
        "| Expiry (years) | Quotes | Inside bid/ask | Median miss | Worst error |",
        "|---|---|---|---|---|",
    ]
    for label, m in rows:
        miss = "none" if np.isnan(m.median_miss) else f"{m.median_miss:.2f}"
        lines.append(
            f"| {label} | {m.quotes} | {m.inside:.1%} | {miss} | {m.worst:.2f} |"
        )
    return "\n".join(lines)


def git_commit() -> str:
    """The commit that produced a result, marked if the working tree differs from it."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    return git("rev-parse", "--short", "HEAD") + (
        "-dirty" if git("status", "--porcelain") else ""
    )


# Colours: one fixed colour per surface in the order given, quotes in grey ink.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID, PAPER, ALERT = "#52514e", "#898781", "#e1e0d9", "#fcfcfb", "#d03b3b"


def plot_expiry(
    q: ExpiryQuotes,
    surfaces: Mapping[str, Surface],
    true_density: Callable[[NDArray[np.float64]], NDArray[np.float64]] | None = None,
) -> Figure:
    """One expiry in the layout of the paper's figure 1, for one or more surfaces.

    Panels: call prices, implied volatilities, density, and the fit error in
    half-spreads. The paper overlays the error on the first two panels with a second
    axis; here it has its own panel.
    """
    k = np.linspace(q.strikes[0], q.strikes[-1], 300)
    figure = Figure(figsize=(16, 3.8), facecolor=PAPER, layout="constrained")
    prices, vols, density, errors = figure.subplots(1, 4)

    def vol(strikes: NDArray[np.float64], price: NDArray[np.float64]):
        return np.sqrt(implied_variance(strikes, price) / q.expiry)

    # the market: bid to ask as a bar, in prices and in implied volatilities
    prices.vlines(q.strikes, q.bid, q.ask, color=INK, lw=1.2, label="bid to ask")
    vols.vlines(
        q.strikes, vol(q.strikes, q.bid), vol(q.strikes, q.ask), color=INK, lw=1.2
    )
    at, implied = mid_density(q)
    negative = implied < 0
    density.plot(
        at[~negative], implied[~negative], ".", color=INK, ms=4, label="implied by mids"
    )
    if negative.any():
        density.plot(
            at[negative],
            implied[negative],
            "x",
            color=ALERT,
            ms=6,
            label="mids with arbitrage",
        )
    if true_density is not None:
        density.plot(k, true_density(k), "--", color=INK, lw=1, label="true density")

    for (label, surface), colour in zip(surfaces.items(), SERIES, strict=False):
        model = surface.call(q.expiry, k)
        prices.plot(k, model, color=colour, lw=1.5, label=label)
        vols.plot(k, vol(k, model), color=colour, lw=1.5)
        errors.plot(q.strikes, spread_errors(q, surface), "o", color=colour, ms=3.5)
        j = int(np.searchsorted(surface.expiries, q.expiry))
        if surface.smoothing_variances[j] > 0:
            density.plot(k, surface.density(q.expiry, k), color=colour, lw=1.5)
        else:
            # the linear model has atoms: show each mass over its local strike spacing
            K, mass = surface.strikes[j], surface.densities[j]
            shown = (K[1:-1] >= k[0]) & (K[1:-1] <= k[-1])
            spacing = 0.5 * (K[2:] - K[:-2])
            density.plot(
                K[1:-1][shown], (mass[1:-1] / spacing)[shown], "o", color=colour, ms=3.5
            )

    errors.axhspan(-1, 1, color=GRID, alpha=0.6, lw=0, label="inside bid/ask")
    titles = ["Call price", "Implied volatility", "Density", "Fit error (half-spreads)"]
    for axes, title in zip((prices, vols, density, errors), titles, strict=True):
        axes.set_title(title, loc="left", fontsize=10, color=INK)
        axes.set_xlabel("pure strike", fontsize=9, color=MUTED)
        axes.set_facecolor(PAPER)
        axes.grid(color=GRID, lw=0.6)
        axes.tick_params(colors=MUTED, labelsize=8)
        axes.spines[["top", "right"]].set_visible(False)
        axes.spines[["left", "bottom"]].set_color(GRID)
    handles = [
        h
        for axes in (prices, density, errors)
        for h in axes.get_legend_handles_labels()[0]
    ]
    figure.legend(
        handles=handles,
        loc="outside lower center",
        ncols=len(handles),
        frameon=False,
        fontsize=9,
    )
    figure.suptitle(
        f"Expiry {q.expiry:.4f} years ({q.expiry * 365:.0f} days)",
        x=0.01,
        ha="left",
        fontsize=11,
    )
    return figure
