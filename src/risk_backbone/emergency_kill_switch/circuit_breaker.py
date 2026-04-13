"""Compatibility surface for the canonical execution-owned circuit breaker."""

from execution_backbone.emergency_circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchReason,
    KillSwitchRecord,
    KillSwitchState,
)

__all__ = [
    "EmergencyCircuitBreaker",
    "KillSwitchReason",
    "KillSwitchRecord",
    "KillSwitchState",
]
