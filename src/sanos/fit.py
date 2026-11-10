"""Fitting the densities to quotes: the linear program (MDL) of section 4.2.

Model expiries are the quoted expiries, so each quote depends on one density only
(alpha = 1 in eq. (32)).
"""

from collections.abc import Sequence
from typing import Literal

import numpy as np
import scipy.sparse as sp
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import linprog

from sanos.black_scholes import call, implied_variance
from sanos.grid import boundary_strikes, model_strikes
from sanos.quotes import ExpiryQuotes
from sanos.surface import Surface

# The three treatments of bid/ask in remark 4.1, as (cost of the distance to mid, cost
# of the distance outside bid/ask, whether prices outside bid/ask are allowed).
# The costs multiply the weights 1 / spread of eq. (34).
BID_ASK = {
    "weight": (1.0, 0.0, True),  # 1. fit the mid
    "constrain": (1.0, 0.0, False),  # 2. fit the mid, inside bid/ask
    "penalize": (1e-8, 1.0, True),  # 3. stay inside bid/ask, then fit the mid
}


def atm_bid_variances(quotes: Sequence[ExpiryQuotes]) -> NDArray[np.float64]:
    """Backbone variances V_j: the implied variance of the bid at the money (figure 8).

    The paper does not say how to reach strike 1 when it is not quoted, nor what to do
    when the result is not increasing. Here the implied variances of the bids are
    interpolated linearly in strike, and a running maximum makes them non-decreasing.
    """
    at_the_money = [
        np.interp(1.0, q.strikes, implied_variance(q.strikes, q.bid)) for q in quotes
    ]
    assert np.all(np.isfinite(at_the_money)), (
        "a bid next to strike 1 has no implied vol"
    )
    return np.maximum.accumulate(at_the_money)


def fit(
    quotes: Sequence[ExpiryQuotes],
    eta: float = 0.0,
    variances: ArrayLike | None = None,
    max_gap: float = np.inf,
    bid_ask: Literal["weight", "constrain", "penalize"] = "penalize",
    omega: Literal[0, 1] = 0,
) -> Surface:
    """Fit SANOS to bid/ask quotes.

    `eta` is the smoothness; 0 is the linear model of section 2.2.
    `variances` are the backbone variances V_j, one per expiry and non-decreasing.
    The default is `atm_bid_variances`. They do not matter when eta = 0.
    `max_gap` is the largest allowed distance between neighbouring model strikes.
    `bid_ask` picks the treatment of bid/ask of remark 4.1, see `BID_ASK`.
    `omega` = 0 imposes the calendar condition on the densities, which guarantees
    absence of arbitrage; 1 imposes it on the smoothed prices, which does not.

    Raises RuntimeError if the linear program has no solution.
    """
    expiries = np.array([q.expiry for q in quotes])
    if eta == 0:
        smoothing = np.zeros(len(quotes))
    elif variances is None:
        smoothing = eta * atm_bid_variances(quotes)
    else:
        smoothing = eta * np.asarray(variances, dtype=float)
    assert 0 <= eta < 1 and smoothing.shape == expiries.shape
    assert np.all(np.diff(expiries) > 0) and np.all(np.diff(smoothing) >= 0)

    k_min, k_max = boundary_strikes(quotes)
    strikes = [model_strikes(q.strikes, k_min, k_max, max_gap) for q in quotes]

    # Unknowns, all non-negative: the densities q_1..q_M, then three numbers per quote:
    # the distance of the model price to the mid, how far it is above the ask, and how
    # far it is below the bid.
    n_density = sum(len(K) for K in strikes)
    n_quotes = sum(len(q.strikes) for q in quotes)

    def no_quote_terms(rows: int) -> sp.csr_array:
        return sp.csr_array((rows, 3 * n_quotes))

    # Each q_j has unit mass and unit mean: 1'q_j = 1 and K_j'q_j = 1.
    moments = sp.block_diag(
        [sp.coo_array(np.vstack([np.ones_like(K), K])) for K in strikes]
    )
    a_eq = sp.hstack([moments, no_quote_terms(moments.shape[0])])
    b_eq = np.ones(moments.shape[0])

    # Model prices at the quoted strikes are linear in the densities, eq. (32):
    # c_j = C_j q_j with C_j[r, i] = Call(K_j^i, k_j^r, eta V_j).
    C = sp.block_diag(
        [
            sp.coo_array(call(K, q.strikes[:, None], v))
            for K, q, v in zip(strikes, quotes, smoothing, strict=True)
        ]
    )
    mid, bid, ask = (
        np.concatenate([getattr(q, x) for q in quotes]) for x in ("mid", "bid", "ask")
    )
    identity = sp.identity(n_quotes)
    a_ub = [
        sp.bmat(
            [
                [C, -identity, None, None],  # c - to_mid <= mid
                [-C, -identity, None, None],  # mid - c <= to_mid
                [C, None, -identity, None],  # c - above_ask <= ask
                [-C, None, None, -identity],  # bid - c <= below_bid
            ]
        )
    ]
    b_ub = [mid, -mid, ask, -bid]

    # Calendar condition (*), u_j >= r_j, as R_j q_{j-1} - U_j q_j <= 0, eq. (33): at
    # the strikes K_j, the call prices of q_j dominate those of q_{j-1}. With omega = 0
    # these are the prices of the discrete densities themselves, which makes q a
    # martingale density. For j = 1 the condition holds by Jensen's inequality.
    if len(quotes) > 1:
        blocks = [[None] * len(quotes) for _ in strikes[1:]]
        for j in range(1, len(quotes)):
            at = strikes[j][:, None]
            blocks[j - 1][j - 1] = call(
                strikes[j - 1], at, omega * smoothing[j - 1]
            )  # R_j
            blocks[j - 1][j] = -call(strikes[j], at, omega * smoothing[j])  # -U_j
        calendar = sp.bmat(blocks)
        a_ub.append(sp.hstack([calendar, no_quote_terms(calendar.shape[0])]))
        b_ub.append(np.zeros(calendar.shape[0]))

    mid_cost, outside_cost, outside_allowed = BID_ASK[bid_ask]
    weights = 1 / (ask - bid)
    upper = np.full(n_density + 3 * n_quotes, np.inf)
    if not outside_allowed:
        upper[n_density + n_quotes :] = 0.0
    result = linprog(
        c=np.concatenate(
            [
                np.zeros(n_density),
                mid_cost * weights,
                outside_cost * weights,
                outside_cost * weights,
            ]
        ),
        A_ub=sp.vstack(a_ub).tocsr(),
        b_ub=np.concatenate(b_ub),
        A_eq=a_eq.tocsr(),
        b_eq=b_eq,
        bounds=np.column_stack([np.zeros_like(upper), upper]),
        method="highs",
    )
    if result.status != 0:
        raise RuntimeError(f"the linear program was not solved: {result.message}")

    densities = np.split(
        result.x[:n_density], np.cumsum([len(K) for K in strikes])[:-1]
    )
    return Surface(
        expiries=np.concatenate(([0.0], expiries)),
        strikes=[np.array([1.0]), *strikes],
        densities=[np.array([1.0]), *densities],
        smoothing_variances=np.concatenate(([0.0], smoothing)),
    )
