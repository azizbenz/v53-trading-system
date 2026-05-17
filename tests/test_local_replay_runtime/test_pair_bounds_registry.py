"""Tests pour pair_bounds_registry (Audit 2026-05-07 MVP)."""

from __future__ import annotations

import pytest

from local_replay_runtime.pair_bounds_registry import (
    BNBUSDT_SPOT_BOUNDS,
    DEFAULT_BOUNDS,
    PAIR_BOUNDS,
    clamp_with_warning,
    get_bounds_for_pair,
)


def test_get_bounds_for_pair_known() -> None:
    bounds = get_bounds_for_pair("BNBUSDT")
    assert bounds is BNBUSDT_SPOT_BOUNDS
    assert bounds.spread_bps == (0.5, 50.0)


def test_get_bounds_for_pair_unknown_returns_default() -> None:
    bounds = get_bounds_for_pair("UNKNOWN_PAIR_XYZ")
    assert bounds is DEFAULT_BOUNDS


def test_clamp_with_warning_within_bounds() -> None:
    value, warning, rejected = clamp_with_warning(
        5.0, field_name="spread_bps", pair="BNBUSDT", bounds=(0.5, 50.0)
    )
    assert value == 5.0
    assert warning is None
    assert rejected is False


def test_clamp_with_warning_below_floor() -> None:
    value, warning, rejected = clamp_with_warning(
        0.1, field_name="spread_bps", pair="BNBUSDT", bounds=(0.5, 50.0)
    )
    assert value == 0.5
    assert warning is not None
    assert "spread_bps_CLAMPED_AT_FLOOR" in warning
    assert rejected is False


def test_clamp_with_warning_above_ceiling() -> None:
    value, warning, rejected = clamp_with_warning(
        80.0, field_name="spread_bps", pair="BNBUSDT", bounds=(0.5, 50.0)
    )
    assert value == 50.0
    assert warning is not None
    assert "spread_bps_CLAMPED_AT_CEILING" in warning
    assert rejected is False


def test_clamp_with_warning_outlier_rejected() -> None:
    """Au-dela de ceiling × reject_threshold (default 2.0), rejected=True."""
    value, warning, rejected = clamp_with_warning(
        150.0, field_name="spread_bps", pair="BNBUSDT", bounds=(0.5, 50.0),
        reject_threshold=2.0,
    )
    # 150 > 50 * 2 = 100 → REJECTED outlier
    assert value == 50.0
    assert warning is not None
    assert "spread_bps_REJECTED_AS_OUTLIER" in warning
    assert rejected is True


def test_clamp_with_warning_nan_replaced() -> None:
    value, warning, rejected = clamp_with_warning(
        float("nan"), field_name="x", pair="BNBUSDT", bounds=(0.5, 50.0)
    )
    assert value == 0.5  # floor
    assert warning is not None
    assert "x_NAN_REPLACED_BY_FLOOR" in warning
    assert rejected is False
