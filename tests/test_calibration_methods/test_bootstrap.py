from __future__ import annotations

import math

import pytest

from calibration_methods import (
    StationaryBootstrapConfig,
    StationaryBootstrapError,
    infer_stationary_block_length,
    stationary_bootstrap_confidence_interval,
)


def _autocorrelated_series(length: int = 120) -> tuple[float, ...]:
    value = 0.0
    series: list[float] = []
    for index in range(length):
        innovation = 0.20 if index % 5 == 0 else -0.05
        value = (0.85 * value) + innovation
        series.append(value)
    return tuple(series)


def test_infer_stationary_block_length_detects_dependence():
    series = _autocorrelated_series()

    block_length = infer_stationary_block_length(series)

    assert block_length > 1
    assert block_length <= len(series) // 3


def test_stationary_bootstrap_confidence_interval_is_deterministic():
    series = _autocorrelated_series()
    config = StationaryBootstrapConfig(
        bootstrap_samples=300,
        confidence_level=0.95,
        rng_seed=17,
    )

    first = stationary_bootstrap_confidence_interval(
        series,
        estimator=lambda sample: sum(sample) / len(sample),
        config=config,
    )
    second = stationary_bootstrap_confidence_interval(
        series,
        estimator=lambda sample: sum(sample) / len(sample),
        config=config,
    )

    assert first == second
    assert first.ci_lower <= first.point_estimate <= first.ci_upper
    assert first.expected_block_length >= 1
    assert math.isfinite(first.ci_upper - first.ci_lower)


def test_stationary_bootstrap_rejects_non_finite_series():
    with pytest.raises(StationaryBootstrapError, match="finite"):
        stationary_bootstrap_confidence_interval(
            (0.1, float("nan"), 0.2),
            estimator=lambda sample: sum(sample) / len(sample),
        )
