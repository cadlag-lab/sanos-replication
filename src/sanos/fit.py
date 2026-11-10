"""Fitting the densities to quotes: the linear program (MDL) of section 4.2.

Model expiries are the quoted expiries, so each quote depends on one density only
(alpha = 1 in eq. (32)). The calendar condition is imposed with omega = 0, which is the
setting that guarantees absence of arbitrage.
"""

from collections.abc import Sequence

import numpy as np
import scipy.sparse as sp
from numpy.typing import ArrayLike
from scipy.optimize import linprog

from sanos.black_scholes import call
from sanos.grid import boundary_strikes, model_strikes
from sanos.quotes import ExpiryQuotes
from sanos.surface import Surface


def fit(
    quotes: Sequence[ExpiryQuotes],
    eta: float = 0.0,
    variances: ArrayLike | None = None,
    max_gap: float = np.inf,
) -> Surface:
    """Fit SANOS to mid prices, each error weighted by the inverse spread, eq. (34).

    `variances` are the backbone variances V_j, one per expiry and increasing. They are
    only needed when eta > 0; eta = 0 is the linear model of section 2.2.
    `max_gap` is the largest allowed distance between neighbouring model strikes.
    """
    expiries = np.array([q.expiry for q in quotes])
    smoothing = eta * np.asarray(variances, dtype=float) if eta > 0 else 0 * expiries
    assert 0 <= eta < 1 and smoothing.shape == expiries.shape
    assert np.all(np.diff(expiries) > 0) and np.all(np.diff(smoothing) >= 0)

    k_min, k_max = boundary_strikes(quotes)
    strikes = [model_strikes(q.strikes, k_min, k_max, max_gap) for q in quotes]

    # Unknowns: the densities q_1..q_M, then one absolute fitting error per quote.
    # Everything is non-negative, which is linprog's default bound.
    n_density = sum(len(K) for K in strikes)
    n_quotes = sum(len(q.strikes) for q in quotes)

    # Each q_j has unit mass and unit mean: 1'q_j = 1 and K_j'q_j = 1.
    moments = sp.block_diag(
        [sp.coo_array(np.vstack([np.ones_like(K), K])) for K in strikes]
    )
    a_eq = sp.hstack([moments, sp.csr_array((moments.shape[0], n_quotes))])
    b_eq = np.ones(moments.shape[0])

    # Model prices at the quoted strikes are linear in the densities, eq. (32):
    # c_j = C_j q_j with C_j[r, i] = Call(K_j^i, k_j^r, eta V_j).
    # |mid - c| <= error is the pair c - error <= mid and -c - error <= -mid.
    price_map = sp.block_diag(
        [
            sp.coo_array(call(K, q.strikes[:, None], v))
            for K, q, v in zip(strikes, quotes, smoothing, strict=True)
        ]
    )
    mid = np.concatenate([q.mid for q in quotes])
    identity = sp.identity(n_quotes)
    a_ub = [sp.bmat([[price_map, -identity], [-price_map, -identity]])]
    b_ub = [mid, -mid]

    # Calendar condition (*), u_j >= r_j, as R_j q_{j-1} - U_j q_j <= 0, eq. (33)
    # with omega = 0: the undiffused call prices of q_j dominate those of q_{j-1} at the
    # strikes K_j. At K_min and K_max both sides are equal by the moment constraints, so
    # only inner strikes are imposed. For j = 1 it holds by Jensen's inequality.
    if len(quotes) > 1:
        blocks = [[None] * len(quotes) for _ in strikes[1:]]
        for j in range(1, len(quotes)):
            inner = strikes[j][1:-1, None]
            blocks[j - 1][j - 1] = call(strikes[j - 1], inner, 0.0)  # R_j
            blocks[j - 1][j] = -call(strikes[j], inner, 0.0)  # -U_j
        calendar = sp.bmat(blocks)
        a_ub.append(sp.hstack([calendar, sp.csr_array((calendar.shape[0], n_quotes))]))
        b_ub.append(np.zeros(calendar.shape[0]))

    weights = np.concatenate([1 / (q.ask - q.bid) for q in quotes])
    result = linprog(
        c=np.concatenate([np.zeros(n_density), weights]),
        A_ub=sp.vstack(a_ub).tocsr(),
        b_ub=np.concatenate(b_ub),
        A_eq=a_eq.tocsr(),
        b_eq=b_eq,
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
