"""
Build-6 / engine_a / invalidation_mapper_A
Define structural invalidation for Engine A signals.

Engine A is long-only on the governed rail. The short branch is retained
defensively but is not reachable in normal runtime flow.
"""

from __future__ import annotations

from enum import StrEnum

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel


ENGINE_A_INVALIDATION_PROFILE_ID = "engine_a_invalidation.to_calibrate.v1"
ENGINE_A_INVALIDATION_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_INVALIDATION_DEFAULTS: dict[str, float] = {
    "vol_stop_multiplier": 1.5,
    "default_holding_hours": 4.0,
}


class InvalidationType(StrEnum):
    PRICE_LEVEL = "price_level"
    STRUCTURE_BREAK = "structure_break"
    TIME_EXPIRY = "time_expiry"
    REGIME_CHANGE = "regime_change"


class InvalidationRule(BaseModel, frozen=True):
    """A single invalidation condition."""

    invalidation_type: InvalidationType
    description: str
    level: float | None = None
    horizon_hours: float | None = None


class InvalidationMap(BaseModel, frozen=True):
    """Complete invalidation specification for a signal."""

    pair: str
    engine_id: str = "engine_a"
    rules: tuple[InvalidationRule, ...] = ()
    primary_invalidation: str = ""
    expected_holding_hours: float = 0.0
    has_invalidation: bool = False
    calibration_profile_id: str = ENGINE_A_INVALIDATION_PROFILE_ID
    calibration_status: str = ENGINE_A_INVALIDATION_CALIBRATION_STATUS


def build_invalidation(
    pair: str,
    direction_score: float,
    entry_price: float,
    realized_vol_current: float | None,
    holding_hours: float = ENGINE_A_INVALIDATION_DEFAULTS["default_holding_hours"],
) -> InvalidationMap:
    """Build invalidation map for an Engine A signal."""

    if entry_price <= 0.0:
        raise ValueError("entry_price must be > 0")
    if holding_hours <= 0.0:
        raise ValueError("holding_hours must be > 0")
    if realized_vol_current is not None and realized_vol_current < 0.0:
        raise ValueError("realized_vol_current must be >= 0 when provided")
    if direction_score == 0.0:
        raise ValueError("direction_score must be non-zero")

    rules: list[InvalidationRule] = []
    vol_stop_multiplier = ENGINE_A_INVALIDATION_DEFAULTS["vol_stop_multiplier"]
    time_expiry_description = f"time expiry after {holding_hours:.1f}h"

    if realized_vol_current is not None and realized_vol_current > 0.0:
        price_delta = vol_stop_multiplier * entry_price * realized_vol_current
        if direction_score > 0:
            inv_level = entry_price - price_delta
        else:
            inv_level = entry_price + price_delta

        rules.append(
            InvalidationRule(
                invalidation_type=InvalidationType.PRICE_LEVEL,
                description=f"structural invalidation at {inv_level:.2f}",
                level=inv_level,
            )
        )
    else:
        time_expiry_description += " (realized_vol_missing_no_price_level_rule)"

    rules.append(
        InvalidationRule(
            invalidation_type=InvalidationType.TIME_EXPIRY,
            description=time_expiry_description,
            horizon_hours=holding_hours,
        )
    )
    rules.append(
        InvalidationRule(
            invalidation_type=InvalidationType.STRUCTURE_BREAK,
            description="trend structure broken - continuation invalidated",
        )
    )
    rules.append(
        InvalidationRule(
            invalidation_type=InvalidationType.REGIME_CHANGE,
            description="regime shifted to unfavorable",
        )
    )

    primary = rules[0].description if rules else ""

    return InvalidationMap(
        pair=pair,
        rules=tuple(rules),
        primary_invalidation=primary,
        expected_holding_hours=holding_hours,
        has_invalidation=len(rules) > 0,
        calibration_profile_id=ENGINE_A_INVALIDATION_PROFILE_ID,
        calibration_status=ENGINE_A_INVALIDATION_CALIBRATION_STATUS,
    )
