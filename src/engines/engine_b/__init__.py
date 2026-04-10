"""
Build-7 / engine_b — Mean Reversion Intraday Motor.

Captures local excess situations where price deviates from a local mean
in a context that does not suggest hostile continuation.
More cost-sensitive than Engine A, shorter holding, Tier 1-2 max.
"""

from .engine_b_runner import EngineBDecision, EngineBInput, EngineBLogEntry, EngineBOutput, run_engine_b
from .engine_b_runtime import (
    EngineBRuntime,
    EngineBRuntimeInput,
    EngineBRuntimeResult,
    EngineBRuntimeStatus,
    EngineBSweepValidationHook,
    EngineBSweepValidationInput,
    EngineBSweepValidationOutcome,
)

__all__ = [
    "EngineBDecision",
    "EngineBInput",
    "EngineBLogEntry",
    "EngineBOutput",
    "EngineBRuntime",
    "EngineBRuntimeInput",
    "EngineBRuntimeResult",
    "EngineBRuntimeStatus",
    "EngineBSweepValidationHook",
    "EngineBSweepValidationInput",
    "EngineBSweepValidationOutcome",
    "run_engine_b",
]
