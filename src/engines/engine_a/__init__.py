"""Build-6 — Engine A: Premium Trend / Expansion.

High-conviction engine capturing structured trend continuations
with readable cost, auditable score, and explicit invalidation.

Entry points:
- engines.engine_a.engine_a_runner.run_engine_a()
- engines.engine_a.engine_a_runtime.EngineARuntime
"""

from .engine_a_runner import EngineADecision, EngineAInput, EngineALogEntry, EngineAOutput, run_engine_a
from .engine_a_runtime import (
    EngineAPreEntryValidationHook,
    EngineAPreEntryValidationInput,
    EngineAPreEntryValidationOutcome,
    EngineARuntime,
    EngineARuntimeInput,
    EngineARuntimeResult,
    EngineARuntimeStatus,
)

__all__ = [
    "EngineADecision",
    "EngineAInput",
    "EngineALogEntry",
    "EngineAOutput",
    "EngineAPreEntryValidationHook",
    "EngineAPreEntryValidationInput",
    "EngineAPreEntryValidationOutcome",
    "EngineARuntime",
    "EngineARuntimeInput",
    "EngineARuntimeResult",
    "EngineARuntimeStatus",
    "run_engine_a",
]
