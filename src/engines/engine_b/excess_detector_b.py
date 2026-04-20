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
from pydantic import BaseModel, Field


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
    structure_is_range: float = Field(default=0.5, ge=0.0, le=1.0)
    recent_expansion: float = Field(default=0.0, ge=0.0, le=1.0)
    vpin_current: float | None = Field(default=None, ge=0.0, le=1.0)
    toxic_flow_correlation: float | None = Field(default=None, ge=0.0, le=1.0)


class ExcessResult(BaseModel, frozen=True):
    """Result of excess detection."""

    pair: str
    verdict: ExcessVerdict
    z_score: float
    abs_z: float
    excess_score: float
    reason: str = ""
    active_reason_codes: tuple[str, ...] = ()
    suppressed_reason_codes: tuple[str, ...] = ()
    calibration_profile_id: str = "engine_b_excess.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE


ENGINE_B_EXCESS_PROFILE_ID = "engine_b_excess.to_calibrate.v1"
ENGINE_B_EXCESS_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_Z_MARGINAL_THRESHOLD_ID = "THR-B05"
ENGINE_B_Z_STAR_THRESHOLD_ID = "THR-B06"
ENGINE_B_Z_MAX_THRESHOLD_ID = "THR-B07"
ENGINE_B_VPIN_TOXIC_THRESHOLD_ID = "THR-B08"
ENGINE_B_MAX_INTRA_FAMILY_CORRELATION_THRESHOLD_ID = "THR-B09"


class EngineBExcessThresholds(BaseModel, frozen=True):
    """Single-source threshold ownership for Engine B excess governance."""

    z_star: float = Field(default=1.5, gt=0.0)
    z_marginal: float = Field(default=1.0, gt=0.0)
    z_max: float = Field(default=4.0, gt=0.0)
    vpin_toxic: float = Field(default=0.35, ge=0.0, le=1.0)
    max_intra_family_correlation: float = Field(default=0.7, ge=0.0, le=1.0)
    z_marginal_threshold_id: str = ENGINE_B_Z_MARGINAL_THRESHOLD_ID
    z_star_threshold_id: str = ENGINE_B_Z_STAR_THRESHOLD_ID
    z_max_threshold_id: str = ENGINE_B_Z_MAX_THRESHOLD_ID
    vpin_toxic_threshold_id: str = ENGINE_B_VPIN_TOXIC_THRESHOLD_ID
    max_intra_family_correlation_threshold_id: str = (
        ENGINE_B_MAX_INTRA_FAMILY_CORRELATION_THRESHOLD_ID
    )
    calibration_profile_id: str = ENGINE_B_EXCESS_PROFILE_ID
    calibration_status: str = ENGINE_B_EXCESS_CALIBRATION_STATUS


class EngineBExcessAdjustments(BaseModel, frozen=True):
    """Single-source adjustment ownership for Engine B excess governance."""

    range_bonus: float = Field(default=0.15, ge=0.0)
    expansion_penalty: float = Field(default=0.20, ge=0.0)
    calibration_profile_id: str = ENGINE_B_EXCESS_PROFILE_ID
    calibration_status: str = ENGINE_B_EXCESS_CALIBRATION_STATUS


ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE = EngineBExcessThresholds()
ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE = EngineBExcessAdjustments()
# TO_CALIBRATE: grouped Engine B excess thresholds pending signed calibration.
ENGINE_B_EXCESS_THRESHOLDS: dict[str, float] = {
    "z_star": ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_star,
    "z_marginal": ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal,
    "z_max": ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_max,
    "vpin_toxic": ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.vpin_toxic,
    "max_intra_family_correlation": ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.max_intra_family_correlation,
}
ENGINE_B_EXCESS_ADJUSTMENTS: dict[str, float] = {
    "range_bonus": ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.range_bonus,
    "expansion_penalty": ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.expansion_penalty,
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
            active_reason_codes=(),
            suppressed_reason_codes=(),
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    if abs_z > ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_max:
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
            active_reason_codes=(),
            suppressed_reason_codes=(),
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    if abs_z < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal:
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
            active_reason_codes=(),
            suppressed_reason_codes=(),
            calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
            calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
        )

    z_quality = min(
        (
            abs_z - ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal
        ) / (
            ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_max
            - ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal
        ),
        1.0,
    )
    range_bonus = (
        ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.range_bonus * inputs.structure_is_range
    )
    expansion_penalty = (
        ENGINE_B_EXCESS_ADJUSTMENTS_TO_CALIBRATE.expansion_penalty
        * inputs.recent_expansion
    )
    excess_score = max(0.0, min(1.0, z_quality + range_bonus - expansion_penalty))

    if abs_z >= ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_star:
        verdict = ExcessVerdict.EXPLOITABLE
        reason = ""
    else:
        verdict = ExcessVerdict.MARGINAL
        reason = (
            f"|z|={abs_z:.2f} marginal "
            f"({ENGINE_B_EXCESS_THRESHOLDS['z_marginal']}-{ENGINE_B_EXCESS_THRESHOLDS['z_star']})"
        )
    active_reason_codes, suppressed_reason_codes = _resolve_toxic_flow_reason_codes(
        inputs=inputs,
        abs_z=abs_z,
    )

    return ExcessResult(
        pair=inputs.pair,
        verdict=verdict,
        z_score=inputs.z_score,
        abs_z=abs_z,
        excess_score=excess_score,
        reason=reason,
        active_reason_codes=active_reason_codes,
        suppressed_reason_codes=suppressed_reason_codes,
        calibration_profile_id=ENGINE_B_EXCESS_PROFILE_ID,
        calibration_status=ENGINE_B_EXCESS_CALIBRATION_STATUS,
    )


def _resolve_toxic_flow_reason_codes(
    *,
    inputs: ExcessInput,
    abs_z: float,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Resolve B-local VPIN-fade semantics without changing the excess formula."""

    if inputs.vpin_current is None:
        return (), ()
    if inputs.vpin_current < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.vpin_toxic:
        return (), ()
    if inputs.z_score >= 0.0:
        return (), ()
    if abs_z < ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.z_marginal:
        return (), ()
    if (
        inputs.toxic_flow_correlation is not None
        and inputs.toxic_flow_correlation
        > ENGINE_B_EXCESS_THRESHOLDS_TO_CALIBRATE.max_intra_family_correlation
    ):
        return (), ("b.toxic_flow_fade_suppressed.correlation",)
    return ("b.toxic_flow_fade",), ()
