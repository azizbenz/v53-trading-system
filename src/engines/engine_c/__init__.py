"""Build-15 / engine_c.

Shadow-capable breakout continuation engine.
"""

from __future__ import annotations

from .continuation_validator_c import (
    ENGINE_C_CONTINUATION_PROFILE_ID,
    ENGINE_C_CONTINUATION_REASON,
    ENGINE_C_OFI_PERSISTENCE_REASON,
    ENGINE_C_QUEUE_PRESSURE_REASON,
    ENGINE_C_VPIN_TOXIC_REASON,
    EngineCContinuationValidationInput,
    EngineCContinuationValidationResult,
    validate_continuation_c,
)
from .engine_c_runner import (
    EngineCDecision,
    EngineCInput,
    EngineCInvalidation,
    EngineCLogEntry,
    EngineCOutput,
    run_engine_c,
)
from .engine_c_runtime import (
    EngineCVoidValidationHook,
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
    EngineCRuntime,
    EngineCRuntimeInput,
    EngineCRuntimeResult,
    EngineCRuntimeStatus,
)

ENGINE_C_BUILD_STAGE = 15
ENGINE_C_IMPLEMENTATION_STATUS = "shadow_capable"

__all__ = [
    "ENGINE_C_BUILD_STAGE",
    "ENGINE_C_IMPLEMENTATION_STATUS",
    "ENGINE_C_CONTINUATION_PROFILE_ID",
    "ENGINE_C_CONTINUATION_REASON",
    "ENGINE_C_OFI_PERSISTENCE_REASON",
    "ENGINE_C_QUEUE_PRESSURE_REASON",
    "ENGINE_C_VPIN_TOXIC_REASON",
    "EngineCDecision",
    "EngineCInput",
    "EngineCInvalidation",
    "EngineCLogEntry",
    "EngineCOutput",
    "EngineCContinuationValidationInput",
    "EngineCContinuationValidationResult",
    "EngineCVoidValidationHook",
    "EngineCVoidValidationInput",
    "EngineCVoidValidationOutcome",
    "EngineCRuntime",
    "EngineCRuntimeInput",
    "EngineCRuntimeResult",
    "EngineCRuntimeStatus",
    "run_engine_c",
    "validate_continuation_c",
]
