"""Build-16 / engine_d.

Shadow-capable re-entry engine.
"""

from __future__ import annotations

from .engine_d_runner import (
    EngineDDecision,
    EngineDInput,
    EngineDInvalidation,
    EngineDLogEntry,
    EngineDOutput,
    run_engine_d,
)
from .engine_d_runtime import (
    EngineDReentryValidationHook,
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineDRuntime,
    EngineDRuntimeInput,
    EngineDRuntimeResult,
    EngineDRuntimeStatus,
)

ENGINE_D_BUILD_STAGE = 16
ENGINE_D_IMPLEMENTATION_STATUS = "shadow_capable"

__all__ = [
    "ENGINE_D_BUILD_STAGE",
    "ENGINE_D_IMPLEMENTATION_STATUS",
    "EngineDDecision",
    "EngineDInput",
    "EngineDInvalidation",
    "EngineDLogEntry",
    "EngineDOutput",
    "EngineDReentryValidationHook",
    "EngineDReentryValidationInput",
    "EngineDReentryValidationOutcome",
    "EngineDRuntime",
    "EngineDRuntimeInput",
    "EngineDRuntimeResult",
    "EngineDRuntimeStatus",
    "run_engine_d",
]
