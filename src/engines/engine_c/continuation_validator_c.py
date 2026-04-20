"""Pure continuation validation helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .signal_math_c import compute_continuation_score_components


ENGINE_C_CONTINUATION_PROFILE_ID = "engine_c_continuation.to_calibrate.v2"
ENGINE_C_OFI_MIN_THRESHOLD_ID = "THR-C_OFI_MIN"
ENGINE_C_QUEUE_MIN_THRESHOLD_ID = "THR-C_QUEUE_MIN"
ENGINE_C_VPIN_MAX_THRESHOLD_ID = "THR-C_VPIN_MAX"
# TO_CALIBRATE: keep continuation thresholds centralized here until the signed
# calibration loader owns the Engine C continuation seam.
ENGINE_C_CONTINUATION_THRESHOLDS_TO_CALIBRATE: dict[str, float | str] = {
    "calibration_status": "TO_CALIBRATE",
    "score_min": 0.58,
    "extension_pct_max": 0.72,
}

ENGINE_C_CONTINUATION_SCORE_MIN = ENGINE_C_CONTINUATION_THRESHOLDS_TO_CALIBRATE["score_min"]
ENGINE_C_EXTENSION_PCT_MAX = ENGINE_C_CONTINUATION_THRESHOLDS_TO_CALIBRATE["extension_pct_max"]

ENGINE_C_CONTINUATION_REASON = "engine_internal.c.continuation_viability"
ENGINE_C_MICROSTRUCTURE_MISSING_REASON = "engine_internal.c.microstructure_missing"
ENGINE_C_OFI_PERSISTENCE_REASON = "engine_internal.c.ofi_persistence"
ENGINE_C_QUEUE_PRESSURE_REASON = "engine_internal.c.queue_pressure"
ENGINE_C_VPIN_TOXIC_REASON = "engine_internal.c.vpin_toxic"
ENGINE_C_KYLE_LAMBDA_REASON = "engine_internal.c.kyle_lambda_excessive"


class EngineCContinuationCallerThresholds(BaseModel):
    """Caller-owned continuation microstructure thresholds pending signed governance."""

    ofi_min: float = 0.0
    queue_min: float = Field(default=0.0, ge=-1.0, le=1.0)
    vpin_max: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda_max: float | None = Field(default=None, ge=0.0)
    ofi_min_threshold_id: str = ENGINE_C_OFI_MIN_THRESHOLD_ID
    queue_min_threshold_id: str = ENGINE_C_QUEUE_MIN_THRESHOLD_ID
    vpin_max_threshold_id: str = ENGINE_C_VPIN_MAX_THRESHOLD_ID
    # Doctrine does not freeze a canonical THR-C id for this seam yet. If supplied,
    # the caller must carry the governed artifact threshold id explicitly.
    kyle_lambda_max_threshold_id: str | None = Field(default=None, min_length=1)
    calibration_profile_id: str = ENGINE_C_CONTINUATION_PROFILE_ID
    calibration_status: str = "TO_CALIBRATE"

    model_config = ConfigDict(frozen=True, extra="forbid")


ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE = EngineCContinuationCallerThresholds()


class EngineCContinuationValidationInput(BaseModel):
    """Additive microstructure-aware continuation gate input."""

    followthrough_room: float = Field(..., ge=0.0, le=1.0)
    extension_pct: float = Field(..., ge=0.0, le=1.0)
    context_score: float = Field(..., ge=0.0, le=1.0)
    cumulative_ofi: float | None = None
    queue_pressure: float | None = Field(default=None, ge=-1.0, le=1.0)
    vpin: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda: float | None = Field(default=None, ge=0.0)
    ofi_min: float = ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.ofi_min
    queue_min: float = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.queue_min,
        ge=-1.0,
        le=1.0,
    )
    vpin_max: float | None = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.vpin_max,
        ge=0.0,
        le=1.0,
    )
    kyle_lambda_max: float | None = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.kyle_lambda_max,
        ge=0.0,
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class EngineCContinuationValidationResult(BaseModel):
    """Deterministic continuation gate outcome."""

    continuation_score: float = Field(..., ge=0.0, le=1.0)
    continuation_viable: bool = True
    microstructure_confirmed: bool = True
    microstructure_gate_applied: bool = False
    microstructure_required: bool = False
    microstructure_missing: bool = False
    microstructure_contradictory: bool = False
    reason_codes: tuple[str, ...] = ()
    cumulative_ofi: float | None = None
    queue_pressure: float | None = None
    vpin: float | None = None
    kyle_lambda: float | None = None
    calibration_profile_id: str = ENGINE_C_CONTINUATION_PROFILE_ID

    model_config = ConfigDict(frozen=True, extra="forbid")

    @property
    def accepted(self) -> bool:
        return self.continuation_viable and self.microstructure_confirmed


def validate_continuation_c(
    inputs: EngineCContinuationValidationInput,
) -> EngineCContinuationValidationResult:
    """Validate continuation maturity plus optional microstructure confirmation."""

    continuation_score = compute_continuation_score_components(
        followthrough_room=inputs.followthrough_room,
        extension_pct=inputs.extension_pct,
        context_score=inputs.context_score,
    )
    continuation_viable = (
        continuation_score >= ENGINE_C_CONTINUATION_SCORE_MIN
        and inputs.extension_pct <= ENGINE_C_EXTENSION_PCT_MAX
    )
    microstructure_required = (
        inputs.ofi_min > 0.0
        or inputs.queue_min > 0.0
        or inputs.vpin_max is not None
        or inputs.kyle_lambda_max is not None
    )
    microstructure_gate_applied = microstructure_required or any(
        value is not None
        for value in (inputs.cumulative_ofi, inputs.queue_pressure, inputs.vpin, inputs.kyle_lambda)
    )
    reason_codes: list[str] = []

    if not continuation_viable:
        reason_codes.append(ENGINE_C_CONTINUATION_REASON)

    if microstructure_required:
        if inputs.ofi_min > 0.0 and inputs.cumulative_ofi is None:
            reason_codes.append(ENGINE_C_MICROSTRUCTURE_MISSING_REASON)
        if inputs.queue_min > 0.0 and inputs.queue_pressure is None:
            reason_codes.append(ENGINE_C_MICROSTRUCTURE_MISSING_REASON)
        if inputs.vpin_max is not None and inputs.vpin is None:
            reason_codes.append(ENGINE_C_MICROSTRUCTURE_MISSING_REASON)
        if inputs.kyle_lambda_max is not None and inputs.kyle_lambda is None:
            reason_codes.append(ENGINE_C_MICROSTRUCTURE_MISSING_REASON)

    if inputs.cumulative_ofi is not None and inputs.cumulative_ofi < inputs.ofi_min:
        reason_codes.append(ENGINE_C_OFI_PERSISTENCE_REASON)
    if inputs.queue_pressure is not None and inputs.queue_pressure < inputs.queue_min:
        reason_codes.append(ENGINE_C_QUEUE_PRESSURE_REASON)
    if inputs.vpin is not None and inputs.vpin_max is not None and inputs.vpin > inputs.vpin_max:
        reason_codes.append(ENGINE_C_VPIN_TOXIC_REASON)
    if (
        inputs.kyle_lambda is not None
        and inputs.kyle_lambda_max is not None
        and inputs.kyle_lambda > inputs.kyle_lambda_max
    ):
        reason_codes.append(ENGINE_C_KYLE_LAMBDA_REASON)

    microstructure_missing = ENGINE_C_MICROSTRUCTURE_MISSING_REASON in reason_codes
    microstructure_contradictory = any(
        reason in {
            ENGINE_C_OFI_PERSISTENCE_REASON,
            ENGINE_C_QUEUE_PRESSURE_REASON,
            ENGINE_C_VPIN_TOXIC_REASON,
            ENGINE_C_KYLE_LAMBDA_REASON,
        }
        for reason in reason_codes
    )
    microstructure_confirmed = not (microstructure_missing or microstructure_contradictory)

    return EngineCContinuationValidationResult(
        continuation_score=continuation_score,
        continuation_viable=continuation_viable,
        microstructure_confirmed=microstructure_confirmed,
        microstructure_gate_applied=microstructure_gate_applied,
        microstructure_required=microstructure_required,
        microstructure_missing=microstructure_missing,
        microstructure_contradictory=microstructure_contradictory,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        cumulative_ofi=inputs.cumulative_ofi,
        queue_pressure=inputs.queue_pressure,
        vpin=inputs.vpin,
        kyle_lambda=inputs.kyle_lambda,
    )


__all__ = [
    "ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_C_CONTINUATION_PROFILE_ID",
    "ENGINE_C_CONTINUATION_REASON",
    "ENGINE_C_CONTINUATION_SCORE_MIN",
    "ENGINE_C_EXTENSION_PCT_MAX",
    "ENGINE_C_KYLE_LAMBDA_REASON",
    "ENGINE_C_MICROSTRUCTURE_MISSING_REASON",
    "ENGINE_C_OFI_MIN_THRESHOLD_ID",
    "ENGINE_C_OFI_PERSISTENCE_REASON",
    "ENGINE_C_QUEUE_MIN_THRESHOLD_ID",
    "ENGINE_C_QUEUE_PRESSURE_REASON",
    "ENGINE_C_VPIN_MAX_THRESHOLD_ID",
    "ENGINE_C_VPIN_TOXIC_REASON",
    "EngineCContinuationCallerThresholds",
    "EngineCContinuationValidationInput",
    "EngineCContinuationValidationResult",
    "validate_continuation_c",
]
