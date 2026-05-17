"""Shared Local IA Lab Deflated Sharpe Ratio helpers.

Reference: Bailey, D. H., and Lopez de Prado, M. (2014). The deflated Sharpe
ratio. Journal of Portfolio Management, 40(5), 94-107.
DOI: 10.3905/jpm.2014.40.5.094
"""

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
    """Compute the bounded Deflated Sharpe Ratio from a return series.

    `trial_count` represents the effective number of tested strategy candidates
    or promotion trials whose best-of-N selection effect must be deflated.
    """

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

    return _build_deflated_sharpe_ratio_result(
        observation_count=len(values),
        trial_count=trial_count,
        acceptance_floor=acceptance_floor,
        mean_return=mean_return,
        sample_std=sample_std,
        sharpe_ratio=sharpe_ratio,
        skewness=skewness,
        kurtosis=kurtosis,
        method_version="deflated_sharpe_ratio_v1",
    )


def compute_deflated_sharpe_ratio_from_moments(
    *,
    observation_count: int,
    trial_count: int,
    sharpe_ratio: float,
    skewness: float,
    kurtosis: float,
    acceptance_floor: float = 0.95,
    sample_std: float = 1.0,
) -> DeflatedSharpeRatioResult:
    """Compute the bounded DSR from a moments-style reference seam.

    This additive seam exists for audit / scientific anchoring when the caller
    already has the moments-space inputs used by Bailey et al. rather than a
    raw returns series.

    `trial_count` keeps the same semantics as the returns-based API:
    the effective number of tested strategy candidates or promotion trials.
    """

    if observation_count < 3:
        raise DeflatedSharpeRatioError("observation_count must be >= 3")
    if trial_count < 1:
        raise DeflatedSharpeRatioError("trial_count must be >= 1")
    if not math.isfinite(sharpe_ratio):
        raise DeflatedSharpeRatioError("sharpe_ratio must be finite")
    if not math.isfinite(skewness):
        raise DeflatedSharpeRatioError("skewness must be finite")
    if not math.isfinite(kurtosis):
        raise DeflatedSharpeRatioError("kurtosis must be finite")
    if not math.isfinite(sample_std) or sample_std <= 0.0:
        raise DeflatedSharpeRatioError("sample_std must be finite and > 0")

    mean_return = sharpe_ratio * sample_std
    return _build_deflated_sharpe_ratio_result(
        observation_count=observation_count,
        trial_count=trial_count,
        acceptance_floor=acceptance_floor,
        mean_return=mean_return,
        sample_std=sample_std,
        sharpe_ratio=sharpe_ratio,
        skewness=skewness,
        kurtosis=kurtosis,
        method_version="deflated_sharpe_ratio_from_moments_v1",
    )


def _build_deflated_sharpe_ratio_result(
    *,
    observation_count: int,
    trial_count: int,
    acceptance_floor: float,
    mean_return: float,
    sample_std: float,
    sharpe_ratio: float,
    skewness: float,
    kurtosis: float,
    method_version: str,
) -> DeflatedSharpeRatioResult:
    denominator_term = 1.0 - (skewness * sharpe_ratio) + (((kurtosis - 1.0) / 4.0) * sharpe_ratio**2)
    if denominator_term <= 0.0:
        raise DeflatedSharpeRatioError("DSR denominator is not positive")

    sharpe_variance = denominator_term / float(observation_count - 1)
    if sharpe_variance <= 0.0:
        raise DeflatedSharpeRatioError("DSR sharpe variance must be > 0")

    benchmark_sharpe = _benchmark_sharpe(sharpe_variance=sharpe_variance, trial_count=trial_count)
    z_score = ((sharpe_ratio - benchmark_sharpe) * math.sqrt(observation_count - 1)) / math.sqrt(
        denominator_term
    )
    dsr = NormalDist().cdf(z_score)

    return DeflatedSharpeRatioResult(
        method_version=method_version,
        observation_count=observation_count,
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
    "compute_deflated_sharpe_ratio_from_moments",
]
