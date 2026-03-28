"""
V5.3 - Canonical Engine B facade.

The manifest module name is `engine_b`; the implementation remains hosted
under `engines.engine_b`. This facade provides the stable top-level import
surface consumed by smoke tests and runtime callers.
"""

from engines.engine_b.engine_b_runner import (
    EngineBDecision,
    EngineBInput,
    EngineBLogEntry,
    EngineBOutput,
    run_engine_b,
)

__all__ = [
    "EngineBDecision",
    "EngineBInput",
    "EngineBLogEntry",
    "EngineBOutput",
    "run_engine_b",
]
