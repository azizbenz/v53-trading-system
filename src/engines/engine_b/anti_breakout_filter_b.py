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
from pydantic import BaseModel


class BreakoutVerdict(StrEnum):
    CLEAR = "clear"
    WARNING = "warning"
    BLOCKED = "blocked"


class BreakoutInput(BaseModel, frozen=True):
    """Inputs for anti-breakout filter."""

    pair: str
    regime_trend_strength: float = 0.0
    volume_anomaly: float = 0.0
    structural_break: float = 0.0
    continuation_momentum: float = 0.0
    microstructure_breakout_confirmation: float = 0.0


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
ENGINE_B_BREAKOUT_FILTER_WEIGHTS: dict[str, float] = {
    "regime_trend_strength": 0.30,
    "volume_anomaly": 0.25,
    "structural_break": 0.25,
    "continuation_momentum": 0.20,
    "microstructure_breakout_confirmation": 0.15,
}
ENGINE_B_BREAKOUT_FILTER_THRESHOLDS: dict[str, float] = {
    "blocked": 0.65,
    "warning": 0.35,
}


def evaluate_breakout_risk(inputs: BreakoutInput) -> BreakoutResult:
    """Evaluate breakout risk for a mean-reversion candidate."""

    score = (
        ENGINE_B_BREAKOUT_FILTER_WEIGHTS["regime_trend_strength"]
        * inputs.regime_trend_strength
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS["volume_anomaly"] * inputs.volume_anomaly
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS["structural_break"] * inputs.structural_break
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS["continuation_momentum"]
        * inputs.continuation_momentum
    )
    score = min(
        1.0,
        score
        + ENGINE_B_BREAKOUT_FILTER_WEIGHTS["microstructure_breakout_confirmation"]
        * inputs.microstructure_breakout_confirmation,
    )

    if score >= ENGINE_B_BREAKOUT_FILTER_THRESHOLDS["blocked"]:
        verdict = BreakoutVerdict.BLOCKED
        reason = (
            f"breakout risk {score:.3f} >= "
            f"{ENGINE_B_BREAKOUT_FILTER_THRESHOLDS['blocked']} hostile continuation"
        )
    elif score >= ENGINE_B_BREAKOUT_FILTER_THRESHOLDS["warning"]:
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
