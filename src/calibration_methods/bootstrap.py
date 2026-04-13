"""Shared Local IA Lab stationary bootstrap helpers."""

from __future__ import annotations

import math
import random
from typing import Callable, Iterable

from pydantic import BaseModel, Field


class StationaryBootstrapError(ValueError):
    """Raised when stationary bootstrap inputs are mathematically unusable."""


class StationaryBootstrapConfig(BaseModel, frozen=True):
    """Bounded configuration for stationary block bootstrap."""

    bootstrap_samples: int = Field(default=10_000, ge=100)
    confidence_level: float = Field(default=0.95, gt=0.50, lt=1.0)
    expected_block_length: int | None = Field(default=None, ge=1)
    max_block_length: int | None = Field(default=None, ge=1)
    rng_seed: int = 53


class StationaryBootstrapInterval(BaseModel, frozen=True):
    """Audit-ready stationary bootstrap estimate and confidence interval."""

    method_version: str = "stationary_block_bootstrap_v1"
    selection_method: str = "truncated_autocorrelation_v1"
    sample_count: int = Field(..., ge=2)
    bootstrap_samples: int = Field(..., ge=100)
    expected_block_length: int = Field(..., ge=1)
    confidence_level: float = Field(..., gt=0.50, lt=1.0)
    point_estimate: float
    ci_lower: float
    ci_upper: float
    rng_seed: int


def infer_stationary_block_length(
    values: Iterable[float],
    *,
    max_block_length: int | None = None,
) -> int:
    """Infer a bounded stationary bootstrap block length from autocorrelation."""

    series = _validated_series(values)
    if len(series) < 3:
        return 1
    upper_bound = max_block_length or max(2, min(len(series) // 3, int(math.sqrt(len(series))) + 1))
    upper_bound = max(1, min(upper_bound, len(series)))

    variance = _population_variance(series)
    if variance <= 0.0:
        return 1

    positive_autocorrelations: list[tuple[int, float]] = []
    for lag in range(1, upper_bound + 1):
        autocorrelation = _autocorrelation(series, lag, variance)
        if not math.isfinite(autocorrelation):
            continue
        if autocorrelation > 0.0:
            positive_autocorrelations.append((lag, autocorrelation))

    if not positive_autocorrelations:
        return 1

    integrated_autocorrelation = 1.0 + sum(lag * autocorrelation for lag, autocorrelation in positive_autocorrelations)
    return max(1, min(upper_bound, int(round(integrated_autocorrelation))))


def stationary_bootstrap_confidence_interval(
    values: Iterable[float],
    *,
    estimator: Callable[[tuple[float, ...]], float],
    config: StationaryBootstrapConfig | None = None,
) -> StationaryBootstrapInterval:
    """Estimate a statistic with stationary block bootstrap confidence intervals."""

    bootstrap = config or StationaryBootstrapConfig()
    series = _validated_series(values)
    point_estimate = _validated_estimate(estimator(series))

    expected_block_length = bootstrap.expected_block_length or infer_stationary_block_length(
        series,
        max_block_length=bootstrap.max_block_length,
    )
    expected_block_length = max(1, min(expected_block_length, len(series)))

    rng = random.Random(bootstrap.rng_seed)
    estimates: list[float] = []
    for _ in range(bootstrap.bootstrap_samples):
        indices = _draw_stationary_bootstrap_indices(
            sample_count=len(series),
            expected_block_length=expected_block_length,
            rng=rng,
        )
        sample = tuple(series[index] for index in indices)
        estimates.append(_validated_estimate(estimator(sample)))

    ci_lower, ci_upper = _confidence_interval(
        tuple(estimates),
        confidence_level=bootstrap.confidence_level,
    )
    return StationaryBootstrapInterval(
        sample_count=len(series),
        bootstrap_samples=bootstrap.bootstrap_samples,
        expected_block_length=expected_block_length,
        confidence_level=bootstrap.confidence_level,
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        rng_seed=bootstrap.rng_seed,
    )


def _draw_stationary_bootstrap_indices(
    *,
    sample_count: int,
    expected_block_length: int,
    rng: random.Random,
) -> tuple[int, ...]:
    if sample_count <= 0:
        raise StationaryBootstrapError("sample_count must be > 0")
    if expected_block_length <= 0:
        raise StationaryBootstrapError("expected_block_length must be > 0")

    restart_probability = 1.0 / float(expected_block_length)
    indices: list[int] = []
    current_index = rng.randrange(sample_count)
    for position in range(sample_count):
        if position == 0 or rng.random() < restart_probability:
            current_index = rng.randrange(sample_count)
        else:
            current_index = (current_index + 1) % sample_count
        indices.append(current_index)
    return tuple(indices)


def _validated_series(values: Iterable[float]) -> tuple[float, ...]:
    series = tuple(float(value) for value in values)
    if len(series) < 2:
        raise StationaryBootstrapError("stationary bootstrap requires at least two values")
    if not all(math.isfinite(value) for value in series):
        raise StationaryBootstrapError("stationary bootstrap requires only finite values")
    return series


def _validated_estimate(value: float) -> float:
    estimate = float(value)
    if not math.isfinite(estimate):
        raise StationaryBootstrapError("bootstrap estimator must produce a finite value")
    return estimate


def _population_variance(values: tuple[float, ...]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _autocorrelation(values: tuple[float, ...], lag: int, variance: float) -> float:
    if lag <= 0 or lag >= len(values):
        return 0.0
    if variance <= 0.0:
        return 0.0
    mean = sum(values) / len(values)
    numerator = sum(
        (values[index] - mean) * (values[index - lag] - mean)
        for index in range(lag, len(values))
    )
    denominator = (len(values) - lag) * variance
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def _confidence_interval(
    values: tuple[float, ...],
    *,
    confidence_level: float,
) -> tuple[float, float]:
    alpha = (1.0 - confidence_level) / 2.0
    return (
        _empirical_quantile(values, alpha),
        _empirical_quantile(values, 1.0 - alpha),
    )


def _empirical_quantile(values: Iterable[float], quantile: float) -> float:
    ordered = tuple(sorted(values))
    if not ordered:
        raise StationaryBootstrapError("quantile requires at least one value")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return ordered[lower_index]
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    weight = position - lower_index
    return lower + (upper - lower) * weight


__all__ = [
    "StationaryBootstrapConfig",
    "StationaryBootstrapError",
    "StationaryBootstrapInterval",
    "infer_stationary_block_length",
    "stationary_bootstrap_confidence_interval",
]
