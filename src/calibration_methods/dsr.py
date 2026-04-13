"""Shared Local IA Lab Deflated Sharpe Ratio helpers."""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Iterable

from pydantic import BaseModel, Field


class DeflatedSharpeRatioError(ValueError):
    """Raised when DSR inputs are mathematically unusable."""


class DeflatedSharpeRatioResult(BaseModel, frozen=True):
    """Audit-ready DSR computation result."""

    method_version: str = "deflated_sharpe_ratio_v1"
    observation_count: int = Field(..., ge=3)
    trial_count: int = Field(..., ge=1)
    acceptance_floor: float = Field(..., gt=0.0, lt=1.0)
    mean_return: float
    sample_std: float
    sharpe_ratio: float
    skewness: float
    kurtosis: float
    sharpe_variance: float
    benchmark_sharpe: float
    dsr: float
    passes_floor: bool


def compute_deflated_sharpe_ratio(
    returns: Iterable[float],
    *,
    trial_count: int,
    acceptance_floor: float = 0.95,
) -> DeflatedSharpeRatioResult:
    """Compute the bounded Deflated Sharpe Ratio from a return series."""

    if trial_count < 1:
        raise DeflatedSharpeRatioError("trial_count must be >= 1")

    values = _validated_returns(returns)
    mean_return = sum(values) / len(values)
    sample_std = _sample_standard_deviation(values, mean_return)
    if sample_std <= 0.0:
        raise DeflatedSharpeRatioError("DSR requires non-zero sample standard deviation")

    sharpe_ratio = mean_return / sample_std
    skewness = _population_skewness(values, mean_return, sample_std)
    kurtosis = _population_kurtosis(values, mean_return, sample_std)

    denominator_term = 1.0 - (skewness * sharpe_ratio) + (((kurtosis - 1.0) / 4.0) * sharpe_ratio**2)
    if denominator_term <= 0.0:
        raise DeflatedSharpeRatioError("DSR denominator is not positive")

    sharpe_variance = denominator_term / float(len(values) - 1)
    if sharpe_variance <= 0.0:
        raise DeflatedSharpeRatioError("DSR sharpe variance must be > 0")

    benchmark_sharpe = _benchmark_sharpe(sharpe_variance=sharpe_variance, trial_count=trial_count)
    z_score = ((sharpe_ratio - benchmark_sharpe) * math.sqrt(len(values) - 1)) / math.sqrt(
        denominator_term
    )
    dsr = NormalDist().cdf(z_score)

    return DeflatedSharpeRatioResult(
        observation_count=len(values),
        trial_count=trial_count,
        acceptance_floor=acceptance_floor,
        mean_return=mean_return,
        sample_std=sample_std,
        sharpe_ratio=sharpe_ratio,
        skewness=skewness,
        kurtosis=kurtosis,
        sharpe_variance=sharpe_variance,
        benchmark_sharpe=benchmark_sharpe,
        dsr=dsr,
        passes_floor=dsr >= acceptance_floor,
    )


def _validated_returns(returns: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in returns)
    if len(values) < 3:
        raise DeflatedSharpeRatioError("DSR requires at least three return observations")
    if not all(math.isfinite(value) for value in values):
        raise DeflatedSharpeRatioError("DSR requires only finite return observations")
    return values


def _sample_standard_deviation(values: tuple[float, ...], mean_return: float) -> float:
    variance = sum((value - mean_return) ** 2 for value in values) / float(len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _population_skewness(
    values: tuple[float, ...],
    mean_return: float,
    sample_std: float,
) -> float:
    if sample_std <= 0.0:
        return 0.0
    centered = tuple((value - mean_return) / sample_std for value in values)
    return sum(value**3 for value in centered) / len(centered)


def _population_kurtosis(
    values: tuple[float, ...],
    mean_return: float,
    sample_std: float,
) -> float:
    if sample_std <= 0.0:
        return 3.0
    centered = tuple((value - mean_return) / sample_std for value in values)
    return sum(value**4 for value in centered) / len(centered)


def _benchmark_sharpe(*, sharpe_variance: float, trial_count: int) -> float:
    if trial_count <= 1:
        return 0.0
    distribution = NormalDist()
    gamma_e = 0.5772156649015329
    variance_scale = math.sqrt(sharpe_variance)
    upper_quantile = distribution.inv_cdf(1.0 - (1.0 / trial_count))
    corrected_quantile = distribution.inv_cdf(1.0 - (1.0 / (trial_count * math.e)))
    return variance_scale * (((1.0 - gamma_e) * upper_quantile) + (gamma_e * corrected_quantile))


__all__ = [
    "DeflatedSharpeRatioError",
    "DeflatedSharpeRatioResult",
    "compute_deflated_sharpe_ratio",
]
