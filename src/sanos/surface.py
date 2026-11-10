"""The SANOS call price surface: eq. (17) at model expiries, eq. (14) between them."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from sanos.black_scholes import call


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
        j = int(np.searchsorted(self.expiries, expiry))  # expiry in (T_{j-1}, T_j]
        if not 0 < j < len(self.expiries):
            raise ValueError(f"expiry {expiry} is outside (0, {self.expiries[-1]}]")
        t_prev, t_next = self.expiries[j - 1], self.expiries[j]
        alpha = (expiry - t_prev) / (t_next - t_prev)
        v_prev, v_next = self.smoothing_variances[j - 1], self.smoothing_variances[j]
        v = alpha * v_next + (1 - alpha) * v_prev
        return alpha * self._mixture(j, k, v) + (1 - alpha) * self._mixture(j - 1, k, v)

    def _mixture(self, j: int, k: ArrayLike, v: float) -> NDArray[np.float64]:
        """sum_i q_j^i Call(K_j^i, k, v)."""
        k = np.asarray(k, dtype=float)
        return call(self.strikes[j], k[..., None], v) @ self.densities[j]
