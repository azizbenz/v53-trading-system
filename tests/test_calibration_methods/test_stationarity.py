from __future__ import annotations

import pytest

from calibration_methods import StationarityTestError, evaluate_dual_stationarity


def _stationary_series(length: int = 64) -> tuple[float, ...]:
    values: list[float] = []
    current = 0.0
    shocks = (0.20, -0.12, 0.08, -0.05, 0.03, -0.02, 0.01)
    for index in range(length):
        current = (0.65 * current) + shocks[index % len(shocks)]
        values.append(current)
    return tuple(values)


def _random_walk_series(length: int = 64) -> tuple[float, ...]:
    values: list[float] = []
    current = 0.0
    shocks = (0.18, -0.07, 0.10, -0.03, 0.06, -0.01, 0.04)
    for index in range(length):
        current += 0.04 + shocks[index % len(shocks)]
        values.append(current)
    return tuple(values)


def test_dual_stationarity_passes_for_mean_reverting_series():
    result = evaluate_dual_stationarity(_stationary_series())

    assert result.passes_dual_test is True
    assert result.adf.rejects_unit_root_5pct is True
    assert result.kpss.rejects_stationarity_5pct is False


def test_dual_stationarity_fails_for_random_walk_like_series():
    result = evaluate_dual_stationarity(_random_walk_series())

    assert result.passes_dual_test is False
    assert (
        result.adf.rejects_unit_root_5pct is False
        or result.kpss.rejects_stationarity_5pct is True
    )


def test_dual_stationarity_rejects_too_short_series():
    with pytest.raises(StationarityTestError, match="at least eight observations"):
        evaluate_dual_stationarity((0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7))
