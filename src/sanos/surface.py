"""The SANOS call price surface: eq. (17) at model expiries, eq. (14) between them."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from sanos import black_scholes


@dataclass(frozen=True)
class Surface:
    """Densities q_j on strikes K_j with smoothing variances eta * V_j, for j = 0..M.

    Index 0 is today: T_0 = 0, a unit mass at strike 1 and no smoothing. Storing it
    makes the first expiry interpolate like every other one.
    """

    expiries: NDArray[np.float64]
    strikes: list[NDArray[np.float64]]
    densities: list[NDArray[np.float64]]
    smoothing_variances: NDArray[np.float64]

    def call(self, expiry: float, k: ArrayLike) -> NDArray[np.float64]:
        """Pure call price at any strike and any expiry in (0, T_M].

        Time interpolation uses the linear alpha of eq. (9). Extrapolation beyond the
        last expiry, eq. (15), is not implemented.
        """
        return self._evaluate(black_scholes.call, expiry, k)

    def density(self, expiry: float, k: ArrayLike) -> NDArray[np.float64]:
        """Density of Z_T at k > 0, the second strike derivative of the call price.

        Only the smooth model has one: for eta = 0 the distribution is the discrete q_j.
        """
        if self.smoothing_variances[-1] == 0:
            raise ValueError("the linear model (eta = 0) has atoms, not a density")
        return self._evaluate(black_scholes.density, expiry, k)

    def _evaluate(
        self, kernel: Callable[..., NDArray[np.float64]], expiry: float, k: ArrayLike
    ) -> NDArray[np.float64]:
        """Eq. (14), with `kernel` either the Black-Scholes call or its density."""
        j = int(np.searchsorted(self.expiries, expiry))  # expiry in (T_{j-1}, T_j]
        if not 0 < j < len(self.expiries):
            raise ValueError(f"expiry {expiry} is outside (0, {self.expiries[-1]}]")
        t_prev, t_next = self.expiries[j - 1], self.expiries[j]
        alpha = (expiry - t_prev) / (t_next - t_prev)
        v_prev, v_next = self.smoothing_variances[j - 1], self.smoothing_variances[j]
        v = alpha * v_next + (1 - alpha) * v_prev

        k = np.asarray(k, dtype=float)[..., None]
        at_next = kernel(self.strikes[j], k, v) @ self.densities[j]
        if alpha == 1:  # at a model expiry the previous density does not enter
            return at_next
        at_prev = kernel(self.strikes[j - 1], k, v) @ self.densities[j - 1]
        return alpha * at_next + (1 - alpha) * at_prev
