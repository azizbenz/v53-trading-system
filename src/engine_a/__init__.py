"""
V5.3 - Canonical Engine A facade.

The manifest module name is `engine_a`; the implementation remains hosted
under `engines.engine_a`. This facade provides the stable top-level import
surface consumed by smoke tests and runtime callers.
"""

from engines.engine_a.engine_a_runner import (
    EngineADecision,
    EngineAInput,
    EngineALogEntry,
    EngineAOutput,
    run_engine_a,
)

__all__ = [
    "EngineADecision",
    "EngineAInput",
    "EngineALogEntry",
    "EngineAOutput",
    "run_engine_a",
]
