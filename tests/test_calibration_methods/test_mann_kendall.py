"""Tests for Mann-Kendall monotonic trend detection."""

from __future__ import annotations

import math

import pytest

from calibration_methods.mann_kendall import (
    MannKendallError,
    MannKendallResult,
    compute_mann_kendall_test,
)


def test_mann_kendall_returns_result_type() -> None:
    result = compute_mann_kendall_test([1.0, 2.0, 3.0, 4.0])
    assert isinstance(result, MannKendallResult)
    assert result.method_version == "mann_kendall_v1"
    assert result.observation_count == 4


def test_descending_trend_is_detected_and_fails_floor() -> None:
    result = compute_mann_kendall_test(
        [8.0, 7.0, 6.0, 5.0, 4.0, 3.0],
        acceptance_floor=0.05,
    )
    assert result.trend_direction == "descending"
    assert result.has_significant_trend is True
    assert result.descending_trend_detected is True
    assert result.passes_floor is False


def test_ascending_trend_passes_even_if_significant() -> None:
    result = compute_mann_kendall_test(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        acceptance_floor=0.05,
    )
    assert result.trend_direction == "ascending"
    assert result.has_significant_trend is True
    assert result.descending_trend_detected is False
    assert result.passes_floor is True


def test_flat_series_returns_no_trend_and_p_one() -> None:
    result = compute_mann_kendall_test([1.0, 1.0, 1.0, 1.0])
    assert result.trend_direction == "flat"
    assert result.kendall_tau == 0.0
    assert result.z_score == 0.0
    assert result.p_value == 1.0
    assert result.passes_floor is True


def test_ties_are_handled_with_finite_statistics() -> None:
    result = compute_mann_kendall_test([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    assert result.variance_s > 0.0
    assert math.isfinite(result.z_score)
    assert 0.0 <= result.p_value <= 1.0


def test_acceptance_floor_is_preserved() -> None:
    result = compute_mann_kendall_test(
        [5.0, 4.0, 4.0, 3.0, 2.0, 1.0],
        acceptance_floor=0.20,
    )
    assert result.acceptance_floor == 0.20


def test_rejects_fewer_than_two_observations() -> None:
    with pytest.raises(MannKendallError, match="at least two"):
        compute_mann_kendall_test([1.0])


def test_rejects_non_finite_observations() -> None:
    with pytest.raises(MannKendallError, match="finite"):
        compute_mann_kendall_test([1.0, float("nan"), 2.0])


def test_rejects_invalid_acceptance_floor() -> None:
    with pytest.raises(MannKendallError, match="acceptance_floor"):
        compute_mann_kendall_test([1.0, 2.0, 3.0], acceptance_floor=1.5)
