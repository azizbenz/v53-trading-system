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
from pydantic import BaseModel, Field


ENGINE_B_INVALIDATION_PROFILE_ID = "engine_b_invalidation.to_calibrate.v1"
ENGINE_B_INVALIDATION_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_MAX_HOLDING_HOURS_THRESHOLD_ID = "THR-B10"
ENGINE_B_FALLBACK_STOP_RATIO_THRESHOLD_ID = "THR-B11"
ENGINE_B_STOP_MULTIPLIER_THRESHOLD_ID = "THR-B12"


class EngineBInvalidationThresholds(BaseModel, frozen=True):
    """Single-source threshold ownership for Engine B invalidation governance."""

    max_holding_hours: float = Field(default=8.0, gt=0.0)
    fallback_stop_ratio: float = Field(default=0.98, gt=0.0, lt=1.0)
    stop_multiplier: float = Field(default=1.5, gt=0.0)
    max_holding_hours_threshold_id: str = ENGINE_B_MAX_HOLDING_HOURS_THRESHOLD_ID
    fallback_stop_ratio_threshold_id: str = ENGINE_B_FALLBACK_STOP_RATIO_THRESHOLD_ID
    stop_multiplier_threshold_id: str = ENGINE_B_STOP_MULTIPLIER_THRESHOLD_ID
    calibration_profile_id: str = ENGINE_B_INVALIDATION_PROFILE_ID
    calibration_status: str = ENGINE_B_INVALIDATION_CALIBRATION_STATUS


ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE = EngineBInvalidationThresholds()
# TO_CALIBRATE: keep the runner-visible invalidation defaults consolidated here
# until the signed calibration loader owns the final Engine B thresholds.
ENGINE_B_INVALIDATION_DEFAULTS: dict[str, float] = {
    "max_holding_hours": ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.max_holding_hours,
    "fallback_stop_ratio": ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.fallback_stop_ratio,
    "stop_multiplier": ENGINE_B_INVALIDATION_THRESHOLDS_TO_CALIBRATE.stop_multiplier,
}
ENGINE_B_INVALIDATION_REASON_CODES: dict[str, str] = {
    "fallback_stop_non_positive": "engine_b.invalidation.fallback_stop.non_positive",
}
ENGINE_B_INVALIDATION_ERROR_CODES: dict[str, str] = {
    "stop_ge_entry": "INVALID_STOP_GE_ENTRY",
    "target_le_entry": "INVALID_TARGET_LE_ENTRY",
    "risk_multiple": "INVALID_RISK_MULTIPLE",
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
    if entry_price <= 0.0:
        raise ValueError("entry_price must be > 0")
    if local_mean <= 0.0:
        raise ValueError("local_mean must be > 0")
    if local_std < 0.0:
        raise ValueError("local_std must be >= 0")
    if holding_hours <= 0.0:
        raise ValueError("holding_hours must be > 0")

    target = local_mean
    if target <= entry_price:
        raise ValueError(ENGINE_B_INVALIDATION_ERROR_CODES["target_le_entry"])
    stop_multiplier = ENGINE_B_INVALIDATION_DEFAULTS["stop_multiplier"]
    fallback_stop_ratio = ENGINE_B_INVALIDATION_DEFAULTS["fallback_stop_ratio"]
    reason = ""
    stop = (
        entry_price - stop_multiplier * local_std
        if local_std > 0
        else entry_price * fallback_stop_ratio
    )
    if stop <= 0.0:
        stop = entry_price * fallback_stop_ratio
        reason = ENGINE_B_INVALIDATION_REASON_CODES["fallback_stop_non_positive"]
    if stop >= entry_price:
        raise ValueError(ENGINE_B_INVALIDATION_ERROR_CODES["stop_ge_entry"])
    risk_multiple = (target - entry_price) / (entry_price - stop)
    if target <= stop or risk_multiple <= 0.0:
        raise ValueError(ENGINE_B_INVALIDATION_ERROR_CODES["risk_multiple"])

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
        reason=reason,
        calibration_profile_id=ENGINE_B_INVALIDATION_PROFILE_ID,
        calibration_status=ENGINE_B_INVALIDATION_CALIBRATION_STATUS,
    )
