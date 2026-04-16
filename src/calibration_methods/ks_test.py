"""Two-sample Kolmogorov-Smirnov test for shadow gate distribution drift.

Tests H0: shadow returns and backtest returns come from the same distribution.
A small p-value means the distributions have diverged (shadow ≠ backtest).

Shadow gate thresholds (14_SHADOW_GATE_MATH.md §6.3.1):
  G2.1: KS p-value >= 0.01
  G2.2: KS p-value >= 0.05
  G2.3: KS p-value >= 0.10

Reference: Kolmogorov (1933), Smirnov (1948).
           p-value formula: Smirnov asymptotic approximation via the
           Kolmogorov distribution K(t) = 2 Σ (-1)^(k-1) exp(-2k²t²).
"""

from __future__ import annotations

import math
from typing import Iterable

from pydantic import BaseModel, Field


class KolmogorovSmirnovError(ValueError):
    """Raised when KS test inputs are mathematically unusable."""


class KolmogorovSmirnovResult(BaseModel, frozen=True):
    """Audit-ready two-sample KS test result."""

    method_version: str = "ks_2sample_v1"
    n_shadow: int = Field(..., ge=2)
    n_backtest: int = Field(..., ge=2)
    ks_statistic: float = Field(..., ge=0.0, le=1.0)
    p_value: float = Field(..., ge=0.0, le=1.0)
    passes_floor: bool
    acceptance_floor: float = Field(..., ge=0.0, le=1.0)


def compute_ks_2sample(
    shadow_returns: Iterable[float],
    backtest_returns: Iterable[float],
    *,
    acceptance_floor: float = 0.05,
) -> KolmogorovSmirnovResult:
    """Compute two-sample KS test between shadow and backtest return series.

    Args:
        shadow_returns: Returns observed during shadow phase (live fills).
        backtest_returns: Corresponding backtest ground-truth returns.
        acceptance_floor: Minimum p-value to passes_floor.
                          G2.1=0.01, G2.2=0.05, G2.3=0.10.

    Returns:
        KolmogorovSmirnovResult with ks_statistic, p_value, passes_floor.

    Raises:
        KolmogorovSmirnovError: if inputs are invalid.
    """
    if not (0.0 <= acceptance_floor <= 1.0):
        raise KolmogorovSmirnovError("acceptance_floor must be in [0, 1]")

    x = _validated_series(shadow_returns, "shadow_returns")
    y = _validated_series(backtest_returns, "backtest_returns")

    ks_stat = _ks_statistic(x, y)
    p_val = _ks_pvalue(ks_stat, len(x), len(y))

    return KolmogorovSmirnovResult(
        n_shadow=len(x),
        n_backtest=len(y),
        ks_statistic=ks_stat,
        p_value=p_val,
        passes_floor=p_val >= acceptance_floor,
        acceptance_floor=acceptance_floor,
    )


# ---------------------------------------------------------------------------
# Core computation — pure Python, no scipy dependency
# ---------------------------------------------------------------------------

def _ks_statistic(x: tuple[float, ...], y: tuple[float, ...]) -> float:
    """Compute D_{n,m} = sup_t |F_n(t) - G_m(t)|."""
    n = len(x)
    m = len(y)
    xs = sorted(x)
    ys = sorted(y)

    # Merge all unique values, then compute empirical CDF difference at each
    all_vals = sorted(set(xs + ys))
    max_diff = 0.0

    # Walk through merged sorted values
    i = 0  # pointer into xs
    j = 0  # pointer into ys
    for val in all_vals:
        # Advance pointers to include all values <= val
        while i < n and xs[i] <= val:
            i += 1
        while j < m and ys[j] <= val:
            j += 1
        diff = abs(i / n - j / m)
        if diff > max_diff:
            max_diff = diff

    return max_diff


def _ks_pvalue(d: float, n: int, m: int) -> float:
    """Smirnov asymptotic p-value for two-sample KS.

    p ≈ 2 * Σ_{k=1}^{∞} (-1)^(k-1) * exp(-2 * k² * d² * n*m / (n+m))

    Converges rapidly; truncate at k=100 (negligible error after k=10).
    """
    if d <= 0.0:
        return 1.0

    nm = (n * m) / (n + m)
    t = d * math.sqrt(nm)

    # Compute K(t) via alternating series (Kolmogorov distribution)
    p = 0.0
    sign = 1.0
    for k in range(1, 101):
        term = sign * math.exp(-2.0 * k * k * t * t)
        p += term
        sign = -sign
        if abs(term) < 1e-15:
            break

    p_val = 2.0 * p
    # Clamp to [0, 1] — floating point can produce tiny negatives or >1
    return max(0.0, min(1.0, p_val))


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validated_series(values: Iterable[float], name: str) -> tuple[float, ...]:
    v = tuple(float(x) for x in values)
    if len(v) < 2:
        raise KolmogorovSmirnovError(
            f"KS test requires at least 2 observations in {name}, got {len(v)}"
        )
    if not all(math.isfinite(x) for x in v):
        raise KolmogorovSmirnovError(
            f"KS test requires only finite values in {name}"
        )
    return v


__all__ = [
    "KolmogorovSmirnovError",
    "KolmogorovSmirnovResult",
    "compute_ks_2sample",
]
