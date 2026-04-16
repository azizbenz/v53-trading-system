"""Probabilistic Sharpe Ratio — Bailey & López de Prado (2012).

PSR(SR*) = Φ( (SR_hat - SR*) * sqrt(n-1) / sqrt(1 - γ3*SR_hat + ((γ4-1)/4)*SR_hat²) )

Answers: P(true SR > SR* | observed returns).

Used by shadow gate G2.1/G2.2/G2.3:
  G2.1: PSR(0) >= 0.60
  G2.2: PSR(0) >= 0.85
  G2.3: PSR(0) >= 0.95

Reference: Bailey, D. H., & López de Prado, M. (2012). The Sharpe ratio efficient frontier.
           Journal of Risk, 15(2), 3–44.
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Iterable

from pydantic import BaseModel, Field


class ProbabilisticSharpeRatioError(ValueError):
    """Raised when PSR inputs are mathematically unusable."""


class ProbabilisticSharpeRatioResult(BaseModel, frozen=True):
    """Audit-ready PSR computation result."""

    method_version: str = "probabilistic_sharpe_ratio_v1"
    observation_count: int = Field(..., ge=3)
    benchmark_sharpe: float
    sample_sharpe: float
    skewness: float
    kurtosis: float
    psr: float = Field(..., ge=0.0, le=1.0)
    passes_floor: bool
    acceptance_floor: float = Field(..., gt=0.0, lt=1.0)


def compute_probabilistic_sharpe_ratio(
    returns: Iterable[float],
    *,
    benchmark_sharpe: float = 0.0,
    acceptance_floor: float = 0.95,
) -> ProbabilisticSharpeRatioResult:
    """Compute the Probabilistic Sharpe Ratio.

    Args:
        returns: Series of period returns (shadow or live fills).
        benchmark_sharpe: SR* — the benchmark to test against. Default 0.0 (test SR > 0).
        acceptance_floor: Minimum PSR to pass_floor. G2.1=0.60, G2.2=0.85, G2.3=0.95.

    Returns:
        ProbabilisticSharpeRatioResult with psr and passes_floor.

    Raises:
        ProbabilisticSharpeRatioError: if inputs are mathematically invalid.
    """
    if not math.isfinite(benchmark_sharpe):
        raise ProbabilisticSharpeRatioError("benchmark_sharpe must be finite")
    if not (0.0 < acceptance_floor < 1.0):
        raise ProbabilisticSharpeRatioError("acceptance_floor must be in (0, 1)")

    values = _validated_returns(returns)
    n = len(values)

    mean = sum(values) / n
    sample_std = _sample_std(values, mean)
    if sample_std <= 0.0:
        raise ProbabilisticSharpeRatioError(
            "PSR requires non-zero sample standard deviation"
        )

    sr_hat = mean / sample_std
    skewness = _population_skewness(values, mean, sample_std)
    kurtosis = _population_kurtosis(values, mean, sample_std)

    # Variance of SR_hat under non-normality (Bailey-López de Prado 2012, eq. 3)
    # V[SR_hat] ≈ (1 - γ3*SR_hat + ((γ4-1)/4)*SR_hat²) / (n - 1)
    inner = 1.0 - (skewness * sr_hat) + (((kurtosis - 1.0) / 4.0) * sr_hat**2)
    if inner <= 0.0:
        raise ProbabilisticSharpeRatioError(
            f"PSR denominator inner term non-positive ({inner:.6f}): "
            "returns distribution produces degenerate SR variance"
        )

    # PSR formula: Φ( (SR_hat - SR*) * sqrt(n-1) / sqrt(inner) )
    z_score = (sr_hat - benchmark_sharpe) * math.sqrt(n - 1) / math.sqrt(inner)
    psr = NormalDist().cdf(z_score)

    return ProbabilisticSharpeRatioResult(
        observation_count=n,
        benchmark_sharpe=benchmark_sharpe,
        sample_sharpe=sr_hat,
        skewness=skewness,
        kurtosis=kurtosis,
        psr=psr,
        passes_floor=psr >= acceptance_floor,
        acceptance_floor=acceptance_floor,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validated_returns(returns: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(v) for v in returns)
    if len(values) < 3:
        raise ProbabilisticSharpeRatioError(
            "PSR requires at least three return observations"
        )
    if not all(math.isfinite(v) for v in values):
        raise ProbabilisticSharpeRatioError(
            "PSR requires only finite return observations"
        )
    return values


def _sample_std(values: tuple[float, ...], mean: float) -> float:
    variance = sum((v - mean) ** 2 for v in values) / float(len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _population_skewness(
    values: tuple[float, ...], mean: float, std: float
) -> float:
    if std <= 0.0:
        return 0.0
    centered = tuple((v - mean) / std for v in values)
    return sum(v**3 for v in centered) / len(centered)


def _population_kurtosis(
    values: tuple[float, ...], mean: float, std: float
) -> float:
    if std <= 0.0:
        return 3.0
    centered = tuple((v - mean) / std for v in values)
    return sum(v**4 for v in centered) / len(centered)


__all__ = [
    "ProbabilisticSharpeRatioError",
    "ProbabilisticSharpeRatioResult",
    "compute_probabilistic_sharpe_ratio",
]
