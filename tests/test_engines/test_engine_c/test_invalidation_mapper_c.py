from __future__ import annotations

import pytest

from engines.engine_c.invalidation_mapper_c import build_invalidation_levels_c


def test_breakout_level_invalid_rejected() -> None:
    with pytest.raises(ValueError, match="INVALID_BREAKOUT_LEVEL: breakout_level must be > 0"):
        build_invalidation_levels_c(
            entry_price=100.0,
            breakout_level=0.0,
            realized_vol_current=0.02,
            realized_vol_at_break=0.02,
            expected_gain=0.01,
        )


def test_realized_vol_current_negative_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="INVALID_REALIZED_VOL_CURRENT: realized_vol_current must be >= 0 when provided",
    ):
        build_invalidation_levels_c(
            entry_price=100.0,
            breakout_level=99.0,
            realized_vol_current=-0.01,
            realized_vol_at_break=None,
            expected_gain=0.01,
        )


def test_realized_vol_at_break_negative_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="INVALID_REALIZED_VOL_AT_BREAK: realized_vol_at_break must be >= 0 when provided",
    ):
        build_invalidation_levels_c(
            entry_price=100.0,
            breakout_level=99.0,
            realized_vol_current=0.01,
            realized_vol_at_break=-0.01,
            expected_gain=0.01,
        )


def test_expected_gain_floor_behaviour() -> None:
    result = build_invalidation_levels_c(
        entry_price=100.0,
        breakout_level=99.0,
        realized_vol_current=0.001,
        realized_vol_at_break=0.001,
        expected_gain=0.0,
    )

    assert result.target_price == pytest.approx(101.0)
    assert result.reference_source == "realized_vol_at_break"


def test_stop_price_fallback_only_when_allowed() -> None:
    result = build_invalidation_levels_c(
        entry_price=100.0,
        breakout_level=0.001,
        realized_vol_current=None,
        realized_vol_at_break=None,
        expected_gain=0.01,
    )

    assert result.stop_price == pytest.approx(98.5)
    assert result.reference_source == "entry_price_floor_fallback"


def test_risk_multiple_positive_on_valid_case() -> None:
    result = build_invalidation_levels_c(
        entry_price=100.0,
        breakout_level=99.5,
        realized_vol_current=0.012,
        realized_vol_at_break=0.012,
        expected_gain=0.01,
    )

    assert result.risk_multiple > 0.0
    assert result.reference_source == "realized_vol_at_break"


def test_realized_vol_current_fallback_is_explicit_when_break_vol_missing() -> None:
    result = build_invalidation_levels_c(
        entry_price=105.0,
        breakout_level=101.0,
        realized_vol_current=2.0 / 105.0,
        realized_vol_at_break=None,
        expected_gain=0.012,
    )

    assert result.stop_price == pytest.approx(100.3)
    assert result.target_price == pytest.approx(108.6)
    assert result.reference_source == "realized_vol_current_fallback"


def test_stop_price_structured_error_code_when_stop_crosses_entry() -> None:
    with pytest.raises(ValueError, match="INVALID_STOP_GE_ENTRY: stop_price must remain below entry_price"):
        build_invalidation_levels_c(
            entry_price=105.0,
            breakout_level=110.0,
            realized_vol_current=None,
            realized_vol_at_break=None,
            expected_gain=0.01,
        )
