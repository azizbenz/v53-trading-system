"""Shared Local IA Lab stationarity helpers (ADF + KPSS, bounded implementation)."""

from __future__ import annotations

import math
from typing import Iterable

from pydantic import BaseModel, Field


class StationarityTestError(ValueError):
    """Raised when the bounded stationarity helpers receive unusable inputs."""


class AugmentedDickeyFullerResult(BaseModel, frozen=True):
    """Bounded ADF test result with intercept and no lag augmentation."""

    method_version: str = "adf_level_intercept_v1"
    observation_count: int = Field(..., ge=8)
    statistic: float
    critical_value_10pct: float = -2.57
    critical_value_5pct: float = -2.86
    critical_value_1pct: float = -3.43
    rejects_unit_root_5pct: bool


class KpssLevelStationarityResult(BaseModel, frozen=True):
    """Bounded KPSS result for level stationarity."""

    method_version: str = "kpss_level_newey_west_v1"
    observation_count: int = Field(..., ge=8)
    bandwidth: int = Field(..., ge=1)
    statistic: float
    critical_value_10pct: float = 0.347
    critical_value_5pct: float = 0.463
    critical_value_1pct: float = 0.739
    rejects_stationarity_5pct: bool


class DualStationarityResult(BaseModel, frozen=True):
    """Audit-ready dual stationarity verdict enforcing MI-9."""

    method_version: str = "dual_stationarity_adf_kpss_v1"
    observation_count: int = Field(..., ge=8)
    adf: AugmentedDickeyFullerResult
    kpss: KpssLevelStationarityResult
    passes_dual_test: bool


def evaluate_dual_stationarity(series: Iterable[float]) -> DualStationarityResult:
    """Run the bounded dual stationarity check required by MI-9."""

    values = _validated_series(series)
    adf = compute_adf_level_stationarity(values)
    kpss = compute_kpss_level_stationarity(values)
    return DualStationarityResult(
        observation_count=len(values),
        adf=adf,
        kpss=kpss,
        passes_dual_test=adf.rejects_unit_root_5pct and (not kpss.rejects_stationarity_5pct),
    )


def compute_adf_level_stationarity(series: Iterable[float]) -> AugmentedDickeyFullerResult:
    """Compute a bounded ADF statistic with intercept and no lag augmentation."""

    values = _validated_series(series)
    y_lag = values[:-1]
    y_diff = tuple(current - previous for previous, current in zip(values[:-1], values[1:]))
    sample_size = len(y_diff)
    if sample_size < 6:
        raise StationarityTestError("ADF requires at least seven level observations")

    sum_x = sum(y_lag)
    sum_y = sum(y_diff)
    sum_xx = sum(value * value for value in y_lag)
    sum_xy = sum(x * y for x, y in zip(y_lag, y_diff))
    denominator = (sample_size * sum_xx) - (sum_x * sum_x)
    if abs(denominator) <= 1e-12:
        raise StationarityTestError("ADF regression is singular")

    beta = ((sample_size * sum_xy) - (sum_x * sum_y)) / denominator
    alpha = (sum_y - (beta * sum_x)) / sample_size
    residuals = tuple(y - alpha - (beta * x) for x, y in zip(y_lag, y_diff))
    degrees_of_freedom = sample_size - 2
    if degrees_of_freedom <= 0:
        raise StationarityTestError("ADF requires positive regression degrees of freedom")

    residual_variance = sum(value * value for value in residuals) / degrees_of_freedom
    var_beta = residual_variance * (sample_size / denominator)
    if var_beta <= 0.0:
        raise StationarityTestError("ADF beta variance must be positive")

    statistic = beta / math.sqrt(var_beta)
    return AugmentedDickeyFullerResult(
        observation_count=len(values),
        statistic=statistic,
        rejects_unit_root_5pct=statistic <= -2.86,
    )


def compute_kpss_level_stationarity(series: Iterable[float]) -> KpssLevelStationarityResult:
    """Compute a bounded KPSS level-stationarity statistic using a Bartlett kernel."""

    values = _validated_series(series)
    sample_size = len(values)
    mean_value = sum(values) / sample_size
    residuals = tuple(value - mean_value for value in values)
    cumulative = []
    running = 0.0
    for residual in residuals:
        running += residual
        cumulative.append(running)

    bandwidth = max(1, int(round(math.sqrt(sample_size))))
    long_run_variance = _newey_west_long_run_variance(residuals, bandwidth=bandwidth)
    if long_run_variance <= 0.0:
        raise StationarityTestError("KPSS long-run variance must be positive")

    eta = sum(value * value for value in cumulative)
    statistic = eta / ((sample_size * sample_size) * long_run_variance)
    return KpssLevelStationarityResult(
        observation_count=sample_size,
        bandwidth=bandwidth,
        statistic=statistic,
        rejects_stationarity_5pct=statistic >= 0.463,
    )


def _newey_west_long_run_variance(
    residuals: tuple[float, ...],
    *,
    bandwidth: int,
) -> float:
    sample_size = len(residuals)
    gamma0 = sum(value * value for value in residuals) / sample_size
    variance = gamma0
    for lag in range(1, bandwidth + 1):
        covariance = sum(
            residuals[index] * residuals[index - lag]
            for index in range(lag, sample_size)
        ) / sample_size
        weight = 1.0 - (lag / (bandwidth + 1.0))
        variance += 2.0 * weight * covariance
    return variance


def _validated_series(series: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in series)
    if len(values) < 8:
        raise StationarityTestError("stationarity tests require at least eight observations")
    if not all(math.isfinite(value) for value in values):
        raise StationarityTestError("stationarity tests require only finite observations")
    return values


__all__ = [
    "AugmentedDickeyFullerResult",
    "DualStationarityResult",
    "KpssLevelStationarityResult",
    "StationarityTestError",
    "compute_adf_level_stationarity",
    "compute_kpss_level_stationarity",
    "evaluate_dual_stationarity",
]
