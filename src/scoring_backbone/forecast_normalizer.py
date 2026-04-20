"""Additive doc20 forecast normalization seam for runtime-safe forecast scaling."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ForecastNormalizerConfig(BaseModel, frozen=True):
    """Governed normalization configuration.

    `target_mean_abs_forecast=10` follows the doc20 Carver-style target magnitude.
    """

    target_mean_abs_forecast: float = Field(default=10.0, gt=0.0)
    max_abs_forecast: float = Field(default=20.0, gt=0.0)


class ForecastNormalizationResult(BaseModel, frozen=True):
    raw_forecast: float
    forecast_scalar: float
    normalized_forecast: float
    clipped: bool = False


def compute_raw_forecast(*, expected_return: float, volatility_scale: float) -> float:
    """Compute the raw standardized forecast F ∝ E[r] / σ."""

    if not math.isfinite(expected_return):
        raise ValueError("expected_return must be finite")
    if not math.isfinite(volatility_scale) or volatility_scale <= 0.0:
        raise ValueError("volatility_scale must be finite and > 0")
    return expected_return / volatility_scale


def resolve_forecast_scalar(
    raw_forecasts: tuple[float, ...],
    config: ForecastNormalizerConfig | None = None,
) -> float:
    """Resolve ForecastScalar = target / E[|F|] on a governed sample."""

    if not raw_forecasts:
        raise ValueError("raw_forecasts must not be empty")
    if any(not math.isfinite(value) for value in raw_forecasts):
        raise ValueError("raw_forecasts must contain only finite values")
    mean_abs_forecast = sum(abs(value) for value in raw_forecasts) / len(raw_forecasts)
    if mean_abs_forecast <= 0.0:
        raise ValueError("raw_forecasts must have positive mean absolute magnitude")
    resolved_config = config or ForecastNormalizerConfig()
    return resolved_config.target_mean_abs_forecast / mean_abs_forecast


def normalize_raw_forecast(
    raw_forecast: float,
    *,
    forecast_scalar: float,
    config: ForecastNormalizerConfig | None = None,
) -> ForecastNormalizationResult:
    """Normalize and cap a pre-standardized raw forecast."""

    if not math.isfinite(raw_forecast):
        raise ValueError("raw_forecast must be finite")
    if not math.isfinite(forecast_scalar) or forecast_scalar <= 0.0:
        raise ValueError("forecast_scalar must be finite and > 0")
    resolved_config = config or ForecastNormalizerConfig()
    normalized_forecast = raw_forecast * forecast_scalar
    clipped_forecast = max(
        -resolved_config.max_abs_forecast,
        min(resolved_config.max_abs_forecast, normalized_forecast),
    )
    return ForecastNormalizationResult(
        raw_forecast=raw_forecast,
        forecast_scalar=forecast_scalar,
        normalized_forecast=clipped_forecast,
        clipped=not math.isclose(clipped_forecast, normalized_forecast),
    )


def normalize_forecast(
    *,
    expected_return: float,
    volatility_scale: float,
    forecast_scalar: float,
    config: ForecastNormalizerConfig | None = None,
) -> ForecastNormalizationResult:
    """End-to-end helper from expected return / volatility to normalized forecast."""

    raw_forecast = compute_raw_forecast(
        expected_return=expected_return,
        volatility_scale=volatility_scale,
    )
    return normalize_raw_forecast(
        raw_forecast,
        forecast_scalar=forecast_scalar,
        config=config,
    )


__all__ = [
    "ForecastNormalizerConfig",
    "ForecastNormalizationResult",
    "compute_raw_forecast",
    "normalize_forecast",
    "normalize_raw_forecast",
    "resolve_forecast_scalar",
]
