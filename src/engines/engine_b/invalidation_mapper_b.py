"""
Build-7 / engine_b / invalidation_mapper_B
Define mean-reversion invalidation conditions.

Engine B invalidation:
- target: local mean (reversion target)
- stop: deviation extends further (breakout confirmation)
- time: holding duration exceeds expected horizon
- ce_degradation: CE drops below minimum

Engine B is LONG-ONLY (spot-halal profile).
Only long mean-reversion entries are mapped.
"""

from __future__ import annotations

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel


ENGINE_B_INVALIDATION_PROFILE_ID = "engine_b_invalidation.to_calibrate.v1"
ENGINE_B_INVALIDATION_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_INVALIDATION_DEFAULTS: dict[str, float] = {
    "max_holding_hours": 8.0,
    "fallback_stop_ratio": 0.98,
    "stop_multiplier": 1.5,
}


class InvalidationMapB(BaseModel, frozen=True):
    """Engine B invalidation - mean-reversion specific."""

    pair: str
    direction: str  # always "long" for spot-halal
    entry_price: float
    target_price: float  # local mean - reversion target
    stop_price: float  # breakout confirmation level
    max_holding_hours: float  # time-based invalidation
    primary_invalidation: str  # human-readable summary
    reason: str = ""
    calibration_profile_id: str = ENGINE_B_INVALIDATION_PROFILE_ID
    calibration_status: str = ENGINE_B_INVALIDATION_CALIBRATION_STATUS


def build_invalidation_b(
    pair: str,
    entry_price: float,
    local_mean: float,
    local_std: float,
    holding_hours: float = ENGINE_B_INVALIDATION_DEFAULTS["max_holding_hours"],
) -> InvalidationMapB:
    """Build invalidation for a long mean-reversion trade.

    Target: local_mean (price should revert here).
    Stop: entry_price - 1.5 x local_std (breakout confirmation below).
    Max holding: capped at holding_hours (B should be short).
    """
    target = local_mean
    stop_multiplier = ENGINE_B_INVALIDATION_DEFAULTS["stop_multiplier"]
    fallback_stop_ratio = ENGINE_B_INVALIDATION_DEFAULTS["fallback_stop_ratio"]
    stop = (
        entry_price - stop_multiplier * local_std
        if local_std > 0
        else entry_price * fallback_stop_ratio
    )

    primary = (
        f"Long reversion {pair}: "
        f"entry={entry_price:.4f}, target={target:.4f}, "
        f"stop={stop:.4f}, max_hold={holding_hours:.1f}h"
    )

    return InvalidationMapB(
        pair=pair,
        direction="long",
        entry_price=entry_price,
        target_price=target,
        stop_price=stop,
        max_holding_hours=holding_hours,
        primary_invalidation=primary,
        calibration_profile_id=ENGINE_B_INVALIDATION_PROFILE_ID,
        calibration_status=ENGINE_B_INVALIDATION_CALIBRATION_STATUS,
    )
