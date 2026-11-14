"""E1 to E6 on every frozen Deribit snapshot.

Run with `uv run python experiments/deribit.py`. Writes results/<snapshot>/ with a
README.md that has one section per claim of CLAIMS.md, and the figures it refers to.
The surfaces are fitted once and shared by the sections.
"""

import time
from pathlib import Path

import numpy as np

from sanos.black_scholes import implied_variance
from sanos.checks import arbitrage_violations
from sanos.deribit import FOLDER, MIN_TICK, Snapshot, load
from sanos.fit import atm_bid_variances, fit
from sanos.report import (
    fit_metrics,
    git_commit,
    metrics_table,
    mid_density,
    plot_expiry,
)

RESULTS = Path(__file__).parent.parent / "results"

LINEAR, ROUGH, SMOOTH, HEAVY = "linear (η = 0)", "η = 0.06", "η = 0.25", "η = 0.5"
ETA = {LINEAR: 0.0, ROUGH: 0.06, SMOOTH: 0.25, HEAVY: 0.5}  # the first three: figs. 3-5
DENSE = "linear, dense grid"
# Model strikes of the smooth fits, in at-the-money standard deviations sqrt(V_j):
# at most GAP apart, up to REACH beyond the outermost quotes (see DEVIATIONS.md).
# The linear fit lives on the quoted strikes only, which is the linear interpolation
# of section 2.2; DENSE is the linear model on the grid of the smooth fits.
GAP, REACH = 0.1, 2.0


def fit_all(snapshot: Snapshot) -> tuple[dict, dict, dict]:
    """Every fit the sections need: surfaces, seconds, and whether a fit exists."""
    quotes = snapshot.quotes
    deviation = np.sqrt(atm_bid_variances(quotes))
    dense = {"max_gap": GAP * deviation, "reach": REACH * deviation}
    surfaces, seconds, feasible = {}, {}, {}
    for label, eta in {**ETA, DENSE: 0.0}.items():
        grid = {} if label == LINEAR else dense
        start = time.perf_counter()
        surfaces[label] = fit(quotes, eta=eta, **grid)
        seconds[label] = time.perf_counter() - start
        try:  # E6: is there a fit with every price inside bid/ask?
            fit(quotes, eta=eta, bid_ask="constrain", **grid)
            feasible[label] = True
        except RuntimeError:
            feasible[label] = False
    # E5: the calendar condition on smoothed prices
    surfaces[SMOOTH + ", ω = 1"] = fit(quotes, eta=ETA[SMOOTH], omega=1, **dense)
    return surfaces, seconds, feasible


def vol(surface, expiry: float, k) -> np.ndarray:
    return np.sqrt(implied_variance(k, surface.call(expiry, k)) / expiry)


def table(header: list[str], rows: list[list]) -> str:
    lines = [header, ["---"] * len(header), *rows]
    return "\n".join("| " + " | ".join(map(str, line)) + " |" for line in lines)


def run(snapshot: Snapshot) -> None:
    commit = git_commit()  # before anything is written
    out = RESULTS / snapshot.name
    out.mkdir(parents=True, exist_ok=True)
    quotes, labels = snapshot.quotes, snapshot.labels
    deviation = np.sqrt(atm_bid_variances(quotes))
    surfaces, seconds, feasible = fit_all(snapshot)
    main = {label: surfaces[label] for label in ETA}
    three = {label: surfaces[label] for label in (LINEAR, ROUGH, SMOOTH)}
    shown = [0, len(quotes) // 2, len(quotes) - 1]  # a short, a mid and a long expiry

    text = [
        f"# SANOS on {snapshot.name}",
        f"Produced by `experiments/deribit.py` at commit `{commit}` from "
        f"`data/deribit/{snapshot.name}.json` (sha256 `{snapshot.sha256[:16]}…`), "
        f"captured {snapshot.captured:%Y-%m-%d %H:%M:%S} UTC.",
        "Quotes after each filter of `sanos.deribit.load`: "
        + ", ".join(f"{name} {n}" for name, n in snapshot.filtered.items())
        + ".",
        "Errors are in half-spreads. A miss is a model price outside bid/ask; its size "
        "is the distance to the nearer of bid and ask. Prices are pure prices, which "
        f"for Deribit are BTC; the tick is {MIN_TICK}.",
        table(
            ["Expiry", "Days", "Forward", "Quotes", "Pure strikes", "ATM bid vol"],
            [
                [
                    label,
                    f"{365 * q.expiry:.1f}",
                    f"{forward:.0f}",
                    len(q.strikes),
                    f"{q.strikes[0]:.2f} to {q.strikes[-1]:.2f}",
                    f"{d / np.sqrt(q.expiry):.1%}",
                ]
                for label, forward, q, d in zip(
                    labels, snapshot.forwards, quotes, deviation, strict=True
                )
            ],
        ),
    ]

    # E1: between quoted strikes, the linear model is the chord of the call prices.
    # The bump is the implied volatility halfway between two neighbouring quoted
    # strikes minus the average of the implied volatilities at the two strikes.
    rows = []
    for label in (LINEAR, SMOOTH):
        bump = np.concatenate(
            [
                vol(surfaces[label], q.expiry, 0.5 * (q.strikes[1:] + q.strikes[:-1]))
                - 0.5 * (at_strikes[1:] + at_strikes[:-1])
                for q in quotes
                for at_strikes in [vol(surfaces[label], q.expiry, q.strikes)]
            ]
        )
        low, median, high = 100 * np.quantile(bump, [0.1, 0.5, 0.9])
        rows.append(
            [
                label,
                len(bump),
                f"{np.mean(bump > 0):.0%}",
                f"{median:.2f}",
                f"{low:.2f} to {high:.2f}",
            ]
        )
    q = quotes[shown[1]]
    near = (1 - deviation[shown[1]], 1 + deviation[shown[1]])
    plot_expiry(q, three, k_range=near).savefig(out / "e1_between_strikes.png", dpi=150)
    text += [
        "## E1: linear interpolation is too expensive between strikes",
        "The bump is the implied volatility halfway between two neighbouring quoted "
        "strikes, minus the average of the implied volatilities at the two strikes, in "
        "volatility points. A smile without kinks has bumps near zero.",
        table(["Fit", "Midpoints", "Bump > 0", "Median bump", "10% to 90%"], rows),
        f"![{labels[shown[1]]}, one standard deviation around the money]"
        "(e1_between_strikes.png)",
    ]

    # E2: smoothness against fit
    rows = []
    for label, surface in main.items():
        m = fit_metrics(quotes, surface)
        miss = "none" if np.isnan(m.median_miss) else f"{m.median_miss:.2f}"
        modes = []
        for i in shown:
            if ETA[label] == 0:
                modes.append("atoms")
                continue
            k = np.linspace(quotes[i].strikes[0], quotes[i].strikes[-1], 2000)
            slope = np.sign(np.diff(surface.density(quotes[i].expiry, k)))
            modes.append(int(np.sum((slope[:-1] > 0) & (slope[1:] < 0))))
        rows.append([label, f"{m.inside:.1%}", miss, f"{m.worst:.2f}", *modes])
    for i in shown:
        plot_expiry(quotes[i], three).savefig(out / f"e2_{labels[i]}.png", dpi=150)
    text += [
        "## E2: η trades smoothness of the density against fit",
        "The last three columns count the local maxima of the model density over the "
        "quoted strikes of a short, a mid and a long expiry: 1 is a single hump.",
        table(
            ["Fit", "Inside bid/ask", "Median miss", "Worst error"]
            + [f"Maxima {labels[i]}" for i in shown],
            rows,
        ),
        *(f"![{labels[i]}](e2_{labels[i]}.png)" for i in shown),
    ]

    # E3: the whole surface at the paper's default smoothness
    model_strikes = sum(len(K) for K in surfaces[SMOOTH].strikes[1:])
    text += [
        "## E3: a full surface fits within bid/ask in under a second",
        f"The {SMOOTH} fit of all {len(quotes)} expiries, as one linear program with "
        f"{model_strikes} model strikes, took {seconds[SMOOTH]:.2f} s including the "
        f"construction of the program ({seconds[ROUGH]:.2f} s for {ROUGH}, "
        f"{seconds[LINEAR]:.2f} s for the linear fit).",
        metrics_table(quotes, surfaces[SMOOTH]),
    ]

    # E4: beyond the quoted strikes
    rows = []
    for i in shown:
        q, far = quotes[i], REACH * deviation[i]
        wide = (max(q.strikes[0] - far, 0.05), q.strikes[-1] + far)
        ends = np.array([wide[0], q.strikes[0], q.strikes[-1], wide[1]])
        rows.append(
            [
                labels[i],
                *(
                    f"{k:.2f}: {v:.1%}"
                    for k, v in zip(
                        ends, vol(surfaces[SMOOTH], q.expiry, ends), strict=True
                    )
                ),
            ]
        )
        plot_expiry(q, three, k_range=wide).savefig(
            out / f"e4_{labels[i]}.png", dpi=150
        )
    text += [
        "## E4: extrapolation beyond the quoted strikes",
        f"Implied volatility of the {SMOOTH} fit at the outermost quoted strikes and "
        f"{REACH:.0f} at-the-money standard deviations beyond them, as "
        "strike: volatility. "
        "`nan` means the price has no implied volatility in double precision.",
        table(["Expiry", "Below", "Lowest quote", "Highest quote", "Above"], rows),
        *(f"![{labels[i]}](e4_{labels[i]}.png)" for i in shown),
    ]

    # E5: the conditions of theorem 2.2, at and between the fitted expiries
    expiries = np.array([q.expiry for q in quotes])
    check_expiries = np.sort(
        np.concatenate(
            [expiries, 0.5 * (expiries[1:] + expiries[:-1]), [0.5 * expiries[0]]]
        )
    )
    check_strikes = np.linspace(0.02, 1.5 * quotes[-1].strikes[-1], 5000)
    rows = [
        [
            label,
            *(
                f"{v:.0e}"
                for v in arbitrage_violations(
                    surface.call, check_expiries, check_strikes
                ).values()
            ),
        ]
        for label, surface in surfaces.items()
    ]
    text += [
        "## E5: strictly arbitrage-free for ω = 0",
        f"Largest violation of each condition, in price, on {len(check_expiries)} "
        f"expiries (the fitted ones, the midpoints between them, and half the first) "
        f"times {len(check_strikes)} strikes from {check_strikes[0]} to "
        f"{check_strikes[-1]:.2f}. Fits are with ω = 0 unless stated.",
        table(
            [
                "Fit",
                "Unit mean",
                "Slope in [-1, 0]",
                "Convex in strike",
                "Increasing in expiry",
            ],
            rows,
        ),
    ]

    # E6: arbitrage in the mids, and in bid/ask
    rows = []
    for label, q in zip(labels, quotes, strict=True):
        _, implied = mid_density(q)
        rows.append([label, len(implied), int(np.sum(implied < 0))])
    text += [
        "## E6: mid prices show arbitrage that bid/ask does not",
        "Inner quoted strikes at which the density implied by three neighbouring mids "
        "is negative (a butterfly arbitrage at mid prices):",
        table(["Expiry", "Inner strikes", "Negative"], rows),
        "Does a fit exist with every model price inside bid/ask, "
        '`bid_ask="constrain"`? '
        + ", ".join(
            f"{label}: {'yes' if ok else 'no'}" for label, ok in feasible.items()
        )
        + ". A linear fit is a set of arbitrage-free prices at the quoted strikes "
        "(theorem 2.6), so a yes for either linear fit means that arbitrage-free "
        "prices exist inside bid/ask. A no does not show an arbitrage: the fit is also "
        "restricted by where its model strikes are.",
    ]
    (out / "README.md").write_text("\n\n".join(text) + "\n")


if __name__ == "__main__":
    for path in sorted(FOLDER.glob("*.json")):
        run(load(path))
        print(RESULTS / path.stem / "README.md")
