"""Pure continuation validation helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .signal_math_c import compute_continuation_score_components


ENGINE_C_CONTINUATION_PROFILE_ID = "engine_c_continuation.to_calibrate.v1"

ENGINE_C_CONTINUATION_REASON = "engine_internal.c.continuation_viability"
ENGINE_C_OFI_PERSISTENCE_REASON = "engine_internal.c.ofi_persistence"
ENGINE_C_QUEUE_PRESSURE_REASON = "engine_internal.c.queue_pressure"
ENGINE_C_VPIN_TOXIC_REASON = "engine_internal.c.vpin_toxic"


class EngineCContinuationValidationInput(BaseModel):
    """Additive microstructure-aware continuation gate input."""

    followthrough_room: float = Field(..., ge=0.0, le=1.0)
    extension_pct: float = Field(..., ge=0.0, le=1.0)
    context_score: float = Field(..., ge=0.0, le=1.0)
    cumulative_ofi: float | None = None
    queue_pressure: float | None = Field(default=None, ge=-1.0, le=1.0)
    vpin: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda: float | None = None
    ofi_min: float = 0.0
    queue_min: float = 0.0
    vpin_max: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class EngineCContinuationValidationResult(BaseModel):
    """Deterministic continuation gate outcome."""

    continuation_score: float = Field(..., ge=0.0, le=1.0)
    continuation_viable: bool = True
    microstructure_confirmed: bool = True
    microstructure_gate_applied: bool = False
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
    continuation_viable = continuation_score >= 0.58 and inputs.extension_pct <= 0.72
    microstructure_gate_applied = False
    reason_codes: list[str] = []

    if not continuation_viable:
        reason_codes.append(ENGINE_C_CONTINUATION_REASON)

    if inputs.cumulative_ofi is not None:
        microstructure_gate_applied = True
        if inputs.cumulative_ofi < inputs.ofi_min:
            reason_codes.append(ENGINE_C_OFI_PERSISTENCE_REASON)

    if inputs.queue_pressure is not None:
        microstructure_gate_applied = True
        if inputs.queue_pressure < inputs.queue_min:
            reason_codes.append(ENGINE_C_QUEUE_PRESSURE_REASON)

    if inputs.vpin is not None and inputs.vpin_max is not None:
        microstructure_gate_applied = True
        if inputs.vpin > inputs.vpin_max:
            reason_codes.append(ENGINE_C_VPIN_TOXIC_REASON)

    microstructure_confirmed = not any(
        reason in {
            ENGINE_C_OFI_PERSISTENCE_REASON,
            ENGINE_C_QUEUE_PRESSURE_REASON,
            ENGINE_C_VPIN_TOXIC_REASON,
        }
        for reason in reason_codes
    )
    return EngineCContinuationValidationResult(
        continuation_score=continuation_score,
        continuation_viable=continuation_viable,
        microstructure_confirmed=microstructure_confirmed,
        microstructure_gate_applied=microstructure_gate_applied,
        reason_codes=tuple(reason_codes),
        cumulative_ofi=inputs.cumulative_ofi,
        queue_pressure=inputs.queue_pressure,
        vpin=inputs.vpin,
        kyle_lambda=inputs.kyle_lambda,
    )


__all__ = [
    "ENGINE_C_CONTINUATION_PROFILE_ID",
    "ENGINE_C_CONTINUATION_REASON",
    "ENGINE_C_OFI_PERSISTENCE_REASON",
    "ENGINE_C_QUEUE_PRESSURE_REASON",
    "ENGINE_C_VPIN_TOXIC_REASON",
    "EngineCContinuationValidationInput",
    "EngineCContinuationValidationResult",
    "validate_continuation_c",
]
