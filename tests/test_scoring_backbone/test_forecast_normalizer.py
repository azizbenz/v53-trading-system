from __future__ import annotations

import pytest

from scoring_backbone import (
    ForecastNormalizerConfig,
    compute_raw_forecast,
    normalize_forecast,
    normalize_raw_forecast,
    resolve_forecast_scalar,
)


def test_compute_raw_forecast_uses_expected_return_over_volatility() -> None:
    assert compute_raw_forecast(expected_return=0.012, volatility_scale=0.003) == pytest.approx(4.0)


def test_compute_raw_forecast_rejects_non_positive_volatility() -> None:
    with pytest.raises(ValueError, match="volatility_scale"):
        compute_raw_forecast(expected_return=0.012, volatility_scale=0.0)


def test_resolve_forecast_scalar_targets_mean_absolute_forecast() -> None:
    scalar = resolve_forecast_scalar((2.0, -4.0, 6.0))
    assert scalar == pytest.approx(10.0 / 4.0)


def test_normalized_sample_targets_mean_absolute_forecast_near_ten() -> None:
    raw_forecasts = (2.0, -3.0, 1.5, -1.0, 4.0)
    scalar = resolve_forecast_scalar(raw_forecasts)
    normalized = [
        normalize_raw_forecast(value, forecast_scalar=scalar).normalized_forecast
        for value in raw_forecasts
    ]

    assert sum(abs(value) for value in normalized) / len(normalized) == pytest.approx(10.0, abs=0.5)


def test_resolve_forecast_scalar_rejects_zero_mean_absolute_forecast() -> None:
    with pytest.raises(ValueError, match="positive mean absolute magnitude"):
        resolve_forecast_scalar((0.0, 0.0))


def test_normalize_raw_forecast_clips_to_max_abs_forecast() -> None:
    result = normalize_raw_forecast(
        3.0,
        forecast_scalar=10.0,
        config=ForecastNormalizerConfig(max_abs_forecast=20.0),
    )

    assert result.normalized_forecast == pytest.approx(20.0)
    assert result.clipped is True


def test_normalize_raw_forecast_rejects_non_positive_scalar() -> None:
    with pytest.raises(ValueError, match="forecast_scalar"):
        normalize_raw_forecast(2.0, forecast_scalar=0.0)


def test_normalize_forecast_end_to_end() -> None:
    result = normalize_forecast(
        expected_return=0.008,
        volatility_scale=0.002,
        forecast_scalar=2.5,
    )

    assert result.raw_forecast == pytest.approx(4.0)
    assert result.normalized_forecast == pytest.approx(10.0)
    assert result.clipped is False
