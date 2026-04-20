from __future__ import annotations

import pytest

from engines.engine_d.invalidation_mapper_d import build_invalidation_levels_d


def test_reentry_anchor_price_invalid_rejected() -> None:
    with pytest.raises(ValueError, match="reentry_anchor_price must be > 0"):
        build_invalidation_levels_d(
            entry_price=100.0,
            reentry_anchor_price=0.0,
            realized_vol_current=0.01,
            realized_vol_post_close=0.01,
            expected_gain=0.01,
        )


def test_realized_vol_current_negative_rejected() -> None:
    with pytest.raises(ValueError, match="realized_vol_current must be >= 0 when provided"):
        build_invalidation_levels_d(
            entry_price=100.0,
            reentry_anchor_price=99.0,
            realized_vol_current=-0.01,
            realized_vol_post_close=None,
            expected_gain=0.01,
        )


def test_realized_vol_post_close_negative_rejected() -> None:
    with pytest.raises(ValueError, match="realized_vol_post_close must be >= 0 when provided"):
        build_invalidation_levels_d(
            entry_price=100.0,
            reentry_anchor_price=99.0,
            realized_vol_current=0.01,
            realized_vol_post_close=-0.01,
            expected_gain=0.01,
        )


def test_expected_gain_floor_behaviour() -> None:
    result = build_invalidation_levels_d(
        entry_price=100.0,
        reentry_anchor_price=99.0,
        realized_vol_current=0.001,
        realized_vol_post_close=0.001,
        expected_gain=0.0,
    )

    assert result.target_price == pytest.approx(100.8)
    assert result.reference_source == "realized_vol_post_close"


def test_stop_price_fallback_only_when_allowed() -> None:
    result = build_invalidation_levels_d(
        entry_price=100.0,
        reentry_anchor_price=0.001,
        realized_vol_current=None,
        realized_vol_post_close=None,
        expected_gain=0.01,
    )

    assert result.stop_price == pytest.approx(98.7)
    assert result.reference_source == "entry_price_floor_fallback"


def test_risk_multiple_positive_on_valid_case() -> None:
    result = build_invalidation_levels_d(
        entry_price=100.0,
        reentry_anchor_price=99.5,
        realized_vol_current=0.012,
        realized_vol_post_close=0.012,
        expected_gain=0.01,
    )

    assert result.risk_multiple > 0.0
    assert result.reference_source == "realized_vol_post_close"


def test_realized_vol_current_fallback_is_explicit_when_post_close_vol_missing() -> None:
    result = build_invalidation_levels_d(
        entry_price=104.0,
        reentry_anchor_price=101.5,
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=None,
        expected_gain=0.009,
    )

    assert result.stop_price == pytest.approx(100.96)
    assert result.target_price == pytest.approx(106.52)
    assert result.reference_source == "realized_vol_current_fallback"
