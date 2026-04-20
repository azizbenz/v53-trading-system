"""Build-15 / engine_c.

Shadow-capable breakout continuation engine.
"""

from __future__ import annotations

from .continuation_validator_c import (
    ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_C_CONTINUATION_PROFILE_ID,
    ENGINE_C_CONTINUATION_REASON,
    ENGINE_C_KYLE_LAMBDA_REASON,
    ENGINE_C_MICROSTRUCTURE_MISSING_REASON,
    ENGINE_C_OFI_MIN_THRESHOLD_ID,
    ENGINE_C_OFI_PERSISTENCE_REASON,
    ENGINE_C_QUEUE_MIN_THRESHOLD_ID,
    ENGINE_C_QUEUE_PRESSURE_REASON,
    ENGINE_C_VPIN_MAX_THRESHOLD_ID,
    ENGINE_C_VPIN_TOXIC_REASON,
    EngineCContinuationCallerThresholds,
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
from .cost_feasibility_c import (
    ENGINE_C_CE_MIN_THRESHOLD_FAMILY_ID,
    ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_C_COST_PROFILE_ID,
    ENGINE_C_DELTA_SAFE_THRESHOLD_FAMILY_ID,
    EngineCCostCallerThresholds,
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
    "ENGINE_C_CE_MIN_THRESHOLD_FAMILY_ID",
    "ENGINE_C_IMPLEMENTATION_STATUS",
    "ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_C_CONTINUATION_PROFILE_ID",
    "ENGINE_C_CONTINUATION_REASON",
    "ENGINE_C_KYLE_LAMBDA_REASON",
    "ENGINE_C_MICROSTRUCTURE_MISSING_REASON",
    "ENGINE_C_OFI_MIN_THRESHOLD_ID",
    "ENGINE_C_OFI_PERSISTENCE_REASON",
    "ENGINE_C_QUEUE_MIN_THRESHOLD_ID",
    "ENGINE_C_QUEUE_PRESSURE_REASON",
    "ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_C_COST_PROFILE_ID",
    "ENGINE_C_DELTA_SAFE_THRESHOLD_FAMILY_ID",
    "ENGINE_C_VPIN_MAX_THRESHOLD_ID",
    "ENGINE_C_VPIN_TOXIC_REASON",
    "EngineCCostCallerThresholds",
    "EngineCContinuationCallerThresholds",
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
