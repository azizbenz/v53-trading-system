"""Build-15 / engine_c.

Shadow-capable breakout continuation engine.
"""

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
    "EngineCDecision",
    "EngineCInput",
    "EngineCInvalidation",
    "EngineCLogEntry",
    "EngineCOutput",
    "EngineCVoidValidationHook",
    "EngineCVoidValidationInput",
    "EngineCVoidValidationOutcome",
    "EngineCRuntime",
    "EngineCRuntimeInput",
    "EngineCRuntimeResult",
    "EngineCRuntimeStatus",
    "run_engine_c",
]
