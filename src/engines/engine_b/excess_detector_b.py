"""
Build-7 / engine_b / excess_detector_B
Detect exploitable local excess for mean-reversion.

Entry condition: |z_t| > z*
Quality depends on z-score magnitude, structure (range vs breakout),
and recent compression/expansion context.
"""

from __future__ import annotations

from enum import StrEnum

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel


class ExcessVerdict(StrEnum):
    EXPLOITABLE = "exploitable"
    MARGINAL = "marginal"
    NO_EXCESS = "no_excess"
    INVALID = "invalid"


class ExcessInput(BaseModel, frozen=True):
    """Inputs for excess detection."""

    pair: str
    z_score: float
    z_score_valid: bool = True
    structure_is_range: float = 0.5
    recent_expansion: float = 0.0


class ExcessResult(BaseModel, frozen=True):
    """Result of excess detection."""

    pair: str
    verdict: ExcessVerdict
    z_score: float
    abs_z: float
    excess_score: float
    reason: str = ""
    calibration_profile_id: str = "engine_b_excess.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE


ENGINE_B_EXCESS_PROFILE_ID = "engine_b_excess.to_calibrate.v1"
ENGINE_B_EXCESS_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_EXCESS_THRESHOLDS: dict[str, float] = {
    "z_star": 1.5,
    "z_marginal": 1.0,
    "z_max": 4.0,
}
ENGINE_B_EXCESS_ADJUSTMENTS: dict[str, float] = {
    "range_bonus": 0.15,
    "expansion_penalty": 0.20,
}


def detect_excess(inputs: ExcessInput) -> ExcessResult:
    """Detect whether a local excess is exploitable for mean reversion."""

    abs_z = abs(inputs.z_score)

    if not inputs.z_score_valid:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.INVALID,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason="z-score invalid (zero dispersion)",
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    if abs_z > ENGINE_B_EXCESS_THRESHOLDS["z_max"]:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.NO_EXCESS,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason=(
                f"|z|={abs_z:.2f} > {ENGINE_B_EXCESS_THRESHOLDS['z_max']} "
                "likely breakout, not reversion"
            ),
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    if abs_z < ENGINE_B_EXCESS_THRESHOLDS["z_marginal"]:
        return ExcessResult(
            pair=inputs.pair,
            verdict=ExcessVerdict.NO_EXCESS,
            z_score=inputs.z_score,
            abs_z=abs_z,
            excess_score=0.0,
            reason=(
                f"|z|={abs_z:.2f} < {ENGINE_B_EXCESS_THRESHOLDS['z_marginal']} "
                "insufficient deviation"
            ),
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    z_quality = min(
        (
            abs_z - ENGINE_B_EXCESS_THRESHOLDS["z_marginal"]
        ) / (
            ENGINE_B_EXCESS_THRESHOLDS["z_max"]
            - ENGINE_B_EXCESS_THRESHOLDS["z_marginal"]
        ),
        1.0,
    )
    range_bonus = ENGINE_B_EXCESS_ADJUSTMENTS["range_bonus"] * inputs.structure_is_range
    expansion_penalty = (
        ENGINE_B_EXCESS_ADJUSTMENTS["expansion_penalty"] * inputs.recent_expansion
    )
    excess_score = max(0.0, min(1.0, z_quality + range_bonus - expansion_penalty))

    if abs_z >= ENGINE_B_EXCESS_THRESHOLDS["z_star"]:
        verdict = ExcessVerdict.EXPLOITABLE
        reason = ""
    else:
        verdict = ExcessVerdict.MARGINAL
        reason = (
            f"|z|={abs_z:.2f} marginal "
            f"({ENGINE_B_EXCESS_THRESHOLDS['z_marginal']}-{ENGINE_B_EXCESS_THRESHOLDS['z_star']})"
        )

    return ExcessResult(
        pair=inputs.pair,
        verdict=verdict,
        z_score=inputs.z_score,
        abs_z=abs_z,
        excess_score=excess_score,
        reason=reason,
        calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
        calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
    )
