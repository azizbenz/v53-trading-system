"""
Build-6 / engine_a / context_validator_A
Validate that context does not contradict the structural signal.

Context does not decide — it confirms, degrades, or blocks (only if fatal).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from data_backbone import TO_CALIBRATE


class ContextVerdict(StrEnum):
    CONFIRMING = "confirming"
    NEUTRAL = "neutral"
    DEGRADED = "degraded"
    FATAL = "fatal"


class ContextInput(BaseModel, frozen=True):
    """Contextual inputs for Engine A validation."""

    pair: str
    regime_favorability: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — 1=ideal trend regime
    regime_confidence: float = Field(..., ge=0.0, le=1.0)  # [0, 1]
    pair_health: float = Field(..., ge=0.0, le=1.0)  # [0, 1]
    data_freshness: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — 1=perfectly fresh
    flow_coherence: float = Field(..., ge=0.0, le=1.0)  # [0, 1]


class ContextResult(BaseModel, frozen=True):
    """Result of context validation."""

    pair: str
    verdict: ContextVerdict
    context_score: float
    reason: str = ""
    calibration_profile_id: str = "engine_a_context.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE


ENGINE_A_CONTEXT_PROFILE_ID = "engine_a_context.to_calibrate.v1"
ENGINE_A_CONTEXT_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_CONTEXT_WEIGHTS: dict[str, float] = {
    "regime_favorability": 0.30,
    "regime_confidence": 0.20,
    "pair_health": 0.20,
    "data_freshness": 0.15,
    "flow_coherence": 0.15,
}
ENGINE_A_CONTEXT_THRESHOLDS: dict[str, float] = {
    "fatal": 0.15,
    "degraded": 0.35,
    "confirming": 0.65,
}


def validate_context(inputs: ContextInput) -> ContextResult:
    """Evaluate context compatibility for Engine A.

    context_score = 0.30·regime + 0.20·regime_conf + 0.20·health + 0.15·freshness + 0.15·flow
    """
    score = (
        ENGINE_A_CONTEXT_WEIGHTS["regime_favorability"] * inputs.regime_favorability
        + ENGINE_A_CONTEXT_WEIGHTS["regime_confidence"] * inputs.regime_confidence
        + ENGINE_A_CONTEXT_WEIGHTS["pair_health"] * inputs.pair_health
        + ENGINE_A_CONTEXT_WEIGHTS["data_freshness"] * inputs.data_freshness
        + ENGINE_A_CONTEXT_WEIGHTS["flow_coherence"] * inputs.flow_coherence
    )

    if score < ENGINE_A_CONTEXT_THRESHOLDS["fatal"]:
        verdict = ContextVerdict.FATAL
        reason = (
            f"context fatal: score {score:.3f} < "
            f"{ENGINE_A_CONTEXT_THRESHOLDS['fatal']}"
        )
    elif score < ENGINE_A_CONTEXT_THRESHOLDS["degraded"]:
        verdict = ContextVerdict.DEGRADED
        reason = f"context degraded: score {score:.3f}"
    elif score >= ENGINE_A_CONTEXT_THRESHOLDS["confirming"]:
        verdict = ContextVerdict.CONFIRMING
        reason = ""
    else:
        verdict = ContextVerdict.NEUTRAL
        reason = ""

    return ContextResult(
        pair=inputs.pair,
        verdict=verdict,
        context_score=score,
        reason=reason,
        calibration_profile_id=ENGINE_A_CONTEXT_PROFILE_ID,
        calibration_status=ENGINE_A_CONTEXT_CALIBRATION_STATUS,
    )
