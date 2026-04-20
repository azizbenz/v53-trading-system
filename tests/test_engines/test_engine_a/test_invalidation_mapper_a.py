from __future__ import annotations

import pytest

from engines.engine_a.invalidation_mapper_a import InvalidationType, build_invalidation


def test_build_invalidation_uses_realized_vol_current_for_price_level() -> None:
    invalidation = build_invalidation(
        pair="BTCUSDT",
        direction_score=0.8,
        entry_price=100.0,
        realized_vol_current=0.02,
        holding_hours=4.0,
    )

    price_rule = next(rule for rule in invalidation.rules if rule.invalidation_type is InvalidationType.PRICE_LEVEL)
    assert price_rule.level == pytest.approx(97.0)
    assert invalidation.primary_invalidation == "structural invalidation at 97.00"


def test_build_invalidation_explicitly_drops_price_rule_when_realized_vol_missing() -> None:
    invalidation = build_invalidation(
        pair="BTCUSDT",
        direction_score=0.8,
        entry_price=100.0,
        realized_vol_current=None,
        holding_hours=4.0,
    )

    assert all(rule.invalidation_type is not InvalidationType.PRICE_LEVEL for rule in invalidation.rules)
    assert invalidation.rules[0].description.endswith("(realized_vol_missing_no_price_level_rule)")


def test_build_invalidation_rejects_negative_realized_vol_current() -> None:
    with pytest.raises(ValueError, match="realized_vol_current must be >= 0 when provided"):
        build_invalidation(
            pair="BTCUSDT",
            direction_score=0.8,
            entry_price=100.0,
            realized_vol_current=-0.01,
            holding_hours=4.0,
        )
