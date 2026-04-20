"""
Build-6 / engine_a / structure_detector_A
Detect exploitable trend/expansion structure.

A premium setup requires:
- readable direction
- coherent continuation
- no major structural contradiction
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from data_backbone import TO_CALIBRATE


class StructureVerdict(StrEnum):
    FAVORABLE = "favorable"
    MARGINAL = "marginal"
    UNFAVORABLE = "unfavorable"


class StructureInput(BaseModel, frozen=True):
    """Structural inputs for Engine A detection."""

    pair: str
    direction_score: float = Field(..., ge=-1.0, le=1.0)  # [-1, 1] — dominant local direction quality
    continuation_score: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — quality of continuation
    structure_quality: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — overall structure readability
    zone_proximity: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — proximity to relevant zones (higher = closer)
    trend_stability: float = Field(..., ge=0.0, le=1.0)  # [0, 1] — stability of the trend
    realized_kernel_vol_scale: float | None = Field(default=None, ge=0.0, le=1.0)


class StructureResult(BaseModel, frozen=True):
    """Result of structure detection."""

    pair: str
    verdict: StructureVerdict
    structure_score: float  # combined structural score
    direction_strength: float
    continuation_strength: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    reason: str = ""
    calibration_profile_id: str = "engine_a_structure.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE


ENGINE_A_STRUCTURE_PROFILE_ID = "engine_a_structure.to_calibrate.v1"
ENGINE_A_STRUCTURE_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_STRUCTURE_WEIGHTS: dict[str, float] = {
    "direction_strength": 0.30,
    "continuation_strength": 0.25,
    "structure_quality": 0.20,
    "zone_proximity": 0.10,
    "trend_stability": 0.15,
}
ENGINE_A_STRUCTURE_THRESHOLDS: dict[str, float] = {
    "favorable": 0.60,
    "marginal": 0.30,
    "min_direction": 0.20,
}


def detect_structure(inputs: StructureInput) -> StructureResult:
    """Evaluate whether a premium trend/expansion structure is present.

    structure_score = 0.30·|direction| + 0.25·continuation + 0.20·quality + 0.10·zone_proximity + 0.15·stability
    """
    direction_strength = abs(inputs.direction_score)
    continuation_strength = inputs.continuation_score
    effective_trend_stability = (
        inputs.trend_stability
        if inputs.realized_kernel_vol_scale is None
        else inputs.realized_kernel_vol_scale
    )

    score = (
        ENGINE_A_STRUCTURE_WEIGHTS["direction_strength"] * direction_strength
        + ENGINE_A_STRUCTURE_WEIGHTS["continuation_strength"] * continuation_strength
        + ENGINE_A_STRUCTURE_WEIGHTS["structure_quality"] * inputs.structure_quality
        + ENGINE_A_STRUCTURE_WEIGHTS["zone_proximity"] * inputs.zone_proximity
        + ENGINE_A_STRUCTURE_WEIGHTS["trend_stability"] * effective_trend_stability
    )
    block_scores = {
        "direction_strength": direction_strength,
        "continuation_strength": continuation_strength,
        "structure_quality": inputs.structure_quality,
        "zone_proximity": inputs.zone_proximity,
        "trend_stability": effective_trend_stability,
        "trend_stability_legacy_score": inputs.trend_stability,
        "trend_stability_source_is_realized_kernel": (
            1.0 if inputs.realized_kernel_vol_scale is not None else 0.0
        ),
    }
    if inputs.realized_kernel_vol_scale is not None:
        block_scores["realized_kernel_vol_scale"] = inputs.realized_kernel_vol_scale

    if direction_strength < ENGINE_A_STRUCTURE_THRESHOLDS["min_direction"]:
        verdict = StructureVerdict.UNFAVORABLE
        reason = (
            "direction too weak: "
            f"{direction_strength:.3f} < {ENGINE_A_STRUCTURE_THRESHOLDS['min_direction']}"
        )
    elif score >= ENGINE_A_STRUCTURE_THRESHOLDS["favorable"]:
        verdict = StructureVerdict.FAVORABLE
        reason = ""
    elif score >= ENGINE_A_STRUCTURE_THRESHOLDS["marginal"]:
        verdict = StructureVerdict.MARGINAL
        reason = f"structure marginal: score {score:.3f}"
    else:
        verdict = StructureVerdict.UNFAVORABLE
        reason = (
            "structure insufficient: "
            f"score {score:.3f} < {ENGINE_A_STRUCTURE_THRESHOLDS['marginal']}"
        )

    return StructureResult(
        pair=inputs.pair,
        verdict=verdict,
        structure_score=score,
        direction_strength=direction_strength,
        continuation_strength=continuation_strength,
        block_scores=block_scores,
        reason=reason,
        calibration_profile_id=ENGINE_A_STRUCTURE_PROFILE_ID,
        calibration_status=ENGINE_A_STRUCTURE_CALIBRATION_STATUS,
    )
