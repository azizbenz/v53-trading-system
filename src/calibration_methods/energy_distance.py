"""Energy distance test for shadow gate distribution drift (Székely & Rizzo, 2004).

More powerful than KS for detecting distributional differences, especially
in the tails and for non-unimodal distributions.

Energy distance:
  E(F, G) = 2·E|X - Y| - E|X - X'| - E|Y - Y'|

Estimated via U-statistic. Permutation test (default 1000 replicas) for p-value.

Shadow gate thresholds (14_SHADOW_GATE_MATH.md §6.3.2):
  G2.1: Energy p-value >= 0.01
  G2.2: Energy p-value >= 0.05
  G2.3: Energy p-value >= 0.10

Reference: Székely, G. J., & Rizzo, M. L. (2004). Testing for equal distributions
           in high dimension. InterStat, Nov(5).
           Rizzo, M. L., & Székely, G. J. (2016). Energy distance. WIRES
           Computational Statistics, 8(1), 27–38.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from pydantic import BaseModel, Field


class EnergyDistanceError(ValueError):
    """Raised when energy distance inputs are mathematically unusable."""


class EnergyDistanceResult(BaseModel, frozen=True):
    """Audit-ready energy distance test result."""

    method_version: str = "energy_distance_permutation_v1"
    n_shadow: int = Field(..., ge=2)
    n_backtest: int = Field(..., ge=2)
    energy_statistic: float = Field(..., ge=0.0)
    p_value: float = Field(..., ge=0.0, le=1.0)
    n_permutations: int = Field(..., ge=99)
    passes_floor: bool
    acceptance_floor: float = Field(..., ge=0.0, le=1.0)


def compute_energy_distance_test(
    shadow_returns: Iterable[float],
    backtest_returns: Iterable[float],
    *,
    acceptance_floor: float = 0.05,
    n_permutations: int = 1000,
    random_seed: int | None = 42,
) -> EnergyDistanceResult:
    """Compute energy distance test between shadow and backtest return series.

    Args:
        shadow_returns: Returns observed during shadow phase.
        backtest_returns: Corresponding backtest ground-truth returns.
        acceptance_floor: Minimum p-value to passes_floor.
                          G2.1=0.01, G2.2=0.05, G2.3=0.10.
        n_permutations: Number of permutation replicas (min 99, recommended 1000).
        random_seed: Seed for permutation reproducibility. None = non-deterministic.

    Returns:
        EnergyDistanceResult with energy_statistic, p_value, passes_floor.

    Raises:
        EnergyDistanceError: if inputs are invalid.
    """
    if not (0.0 <= acceptance_floor <= 1.0):
        raise EnergyDistanceError("acceptance_floor must be in [0, 1]")
    if n_permutations < 99:
        raise EnergyDistanceError("n_permutations must be >= 99 for reliable p-value")

    x = _validated_series(shadow_returns, "shadow_returns")
    y = _validated_series(backtest_returns, "backtest_returns")

    # Observed test statistic
    t_obs = _energy_statistic(x, y)

    # Permutation test: pool x and y, randomly split, compute T each time
    pooled = x + y
    n = len(x)
    rng = random.Random(random_seed)

    count_extreme = 0
    pooled_list = list(pooled)
    for _ in range(n_permutations):
        rng.shuffle(pooled_list)
        perm_x = tuple(pooled_list[:n])
        perm_y = tuple(pooled_list[n:])
        t_perm = _energy_statistic(perm_x, perm_y)
        if t_perm >= t_obs:
            count_extreme += 1

    # p-value = proportion of permuted statistics >= observed
    p_val = (count_extreme + 1) / (n_permutations + 1)  # +1 for continuity

    return EnergyDistanceResult(
        n_shadow=len(x),
        n_backtest=len(y),
        energy_statistic=t_obs,
        p_value=p_val,
        n_permutations=n_permutations,
        passes_floor=p_val >= acceptance_floor,
        acceptance_floor=acceptance_floor,
    )


def compute_raw_energy_distance_statistic(
    shadow_returns: Iterable[float],
    backtest_returns: Iterable[float],
) -> float:
    """Compute the unscaled raw 1D Energy distance statistic E_n,m.

    This additive seam exists for audit/scientific anchoring only. It does not
    alter the production scaled test seam used by `compute_energy_distance_test`.
    """

    x = _validated_series(shadow_returns, "shadow_returns")
    y = _validated_series(backtest_returns, "backtest_returns")
    return _raw_energy_statistic(x, y)


# ---------------------------------------------------------------------------
# Energy statistic (scaled for sample sizes)
# ---------------------------------------------------------------------------

def _energy_statistic(x: tuple[float, ...], y: tuple[float, ...]) -> float:
    """Compute the scaled energy statistic T(x, y).

    T(x, y) = (n*m / (n+m)) * E_hat(x, y)

    where E_hat(F, G) = 2*E|X-Y| - E|X-X'| - E|Y-Y'|

    For 1D data: |a - b| is just abs(a - b).

    Uses O(n*m) pairwise computation — acceptable for shadow sample sizes
    (typically n, m < 1000 returns per month).
    """
    n = len(x)
    m = len(y)

    # Scaled statistic — positive by construction when F ≠ G
    scale = (n * m) / (n + m)
    return scale * _raw_energy_statistic(x, y)


def _raw_energy_statistic(x: tuple[float, ...], y: tuple[float, ...]) -> float:
    n = len(x)
    m = len(y)

    cross = 0.0
    for xi in x:
        for yj in y:
            cross += abs(xi - yj)
    cross_mean = (2.0 * cross) / (n * m)

    xx = 0.0
    for i in range(n):
        for j in range(n):
            xx += abs(x[i] - x[j])
    xx_mean = xx / (n * n)

    yy = 0.0
    for i in range(m):
        for j in range(m):
            yy += abs(y[i] - y[j])
    yy_mean = yy / (m * m)

    e_hat = cross_mean - xx_mean - yy_mean
    return max(e_hat, 0.0)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validated_series(values: Iterable[float], name: str) -> tuple[float, ...]:
    v = tuple(float(x) for x in values)
    if len(v) < 2:
        raise EnergyDistanceError(
            f"Energy test requires at least 2 observations in {name}, got {len(v)}"
        )
    if not all(math.isfinite(x) for x in v):
        raise EnergyDistanceError(
            f"Energy test requires only finite values in {name}"
        )
    return v


__all__ = [
    "EnergyDistanceError",
    "EnergyDistanceResult",
    "compute_energy_distance_test",
    "compute_raw_energy_distance_statistic",
]
