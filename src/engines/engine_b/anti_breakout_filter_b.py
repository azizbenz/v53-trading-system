"""
Build-7 / engine_b / anti_breakout_filter_B
Prevent Engine B from trading against genuine breakouts.

Reject or penalize when:
P(continuation hostile | context) > P(reversion exploitable | context)

Components: regime, volume anomaly, structural confirmation, microstructure.
"""

from __future__ import annotations

from enum import StrEnum

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel, Field


class BreakoutVerdict(StrEnum):
    CLEAR = "clear"
    WARNING = "warning"
    BLOCKED = "blocked"


class BreakoutInput(BaseModel, frozen=True):
    """Inputs for anti-breakout filter."""

    pair: str
    regime_trend_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_anomaly: float = Field(default=0.0, ge=0.0, le=1.0)
    structural_break: float = Field(default=0.0, ge=0.0, le=1.0)
    continuation_momentum: float = Field(default=0.0, ge=0.0, le=1.0)
    microstructure_breakout_confirmation: float = Field(default=0.0, ge=0.0, le=1.0)


class BreakoutResult(BaseModel, frozen=True):
    """Result of anti-breakout evaluation."""

    pair: str
    verdict: BreakoutVerdict
    breakout_score: float
    reason: str = ""
    calibration_profile_id: str = "engine_b_breakout_filter.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE


ENGINE_B_BREAKOUT_FILTER_PROFILE_ID = "engine_b_breakout_filter.to_calibrate.v1"
ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_BREAKOUT_WARNING_THRESHOLD_ID = "THR-B03"
ENGINE_B_BREAKOUT_BLOCKED_THRESHOLD_ID = "THR-B04"


class EngineBBreakoutFilterWeights(BaseModel, frozen=True):
    """Single-source weight ownership for Engine B anti-breakout governance."""

    regime_trend_strength: float = Field(default=0.30, ge=0.0)
    volume_anomaly: float = Field(default=0.25, ge=0.0)
    structural_break: float = Field(default=0.25, ge=0.0)
    continuation_momentum: float = Field(default=0.20, ge=0.0)
    microstructure_breakout_confirmation: float = Field(default=0.15, ge=0.0)
    calibration_profile_id: str = ENGINE_B_BREAKOUT_FILTER_PROFILE_ID
    calibration_status: str = ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS


class EngineBBreakoutFilterThresholds(BaseModel, frozen=True):
    """Single-source threshold ownership for Engine B anti-breakout governance."""

    blocked: float = Field(default=0.65, ge=0.0, le=1.0)
    warning: float = Field(default=0.35, ge=0.0, le=1.0)
    blocked_threshold_id: str = ENGINE_B_BREAKOUT_BLOCKED_THRESHOLD_ID
    warning_threshold_id: str = ENGINE_B_BREAKOUT_WARNING_THRESHOLD_ID
    calibration_profile_id: str = ENGINE_B_BREAKOUT_FILTER_PROFILE_ID
    calibration_status: str = ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS


ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE = EngineBBreakoutFilterWeights()
ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE = EngineBBreakoutFilterThresholds()
# TO_CALIBRATE: grouped Engine B breakout weights/thresholds pending loader wiring.
ENGINE_B_BREAKOUT_FILTER_WEIGHTS: dict[str, float] = {
    "regime_trend_strength": ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.regime_trend_strength,
    "volume_anomaly": ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.volume_anomaly,
    "structural_break": ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.structural_break,
    "continuation_momentum": ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.continuation_momentum,
    "microstructure_breakout_confirmation": ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.microstructure_breakout_confirmation,
}
ENGINE_B_BREAKOUT_FILTER_THRESHOLDS: dict[str, float] = {
    "blocked": ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.blocked,
    "warning": ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.warning,
}


def evaluate_breakout_risk(inputs: BreakoutInput) -> BreakoutResult:
    """Evaluate breakout risk for a mean-reversion candidate."""

    score = (
        ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.regime_trend_strength
        * inputs.regime_trend_strength
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.volume_anomaly * inputs.volume_anomaly
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.structural_break * inputs.structural_break
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.continuation_momentum
        * inputs.continuation_momentum
    )
    score = min(
        1.0,
        score
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS_TO_CALIBRATE.microstructure_breakout_confirmation
        * inputs.microstructure_breakout_confirmation,
    )

    if score >= ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.blocked:
        verdict = BreakoutVerdict.BLOCKED
        reason = (
            f"breakout risk {score:.3f} >= "
            f"{ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.blocked} hostile continuation"
        )
    elif score >= ENGINE_B_BREAKOUT_FILTER_THRESHOLDS_TO_CALIBRATE.warning:
        verdict = BreakoutVerdict.WARNING
        reason = f"breakout risk {score:.3f} ambiguous, penalizing"
    else:
        verdict = BreakoutVerdict.CLEAR
        reason = ""

    return BreakoutResult(
        pair=inputs.pair,
        verdict=verdict,
        breakout_score=score,
        reason=reason,
        calibration_profile_id=ENGINE_B_BREAKOUT_FILTER_PROFILE_ID,
        calibration_status=ENGINE_B_BREAKOUT_FILTER_CALIBRATION_STATUS,
    )
