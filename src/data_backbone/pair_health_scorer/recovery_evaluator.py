"""
10.5.3 — Recovery Evaluator: decide if a suspended pair can return to active.

Invariant: every recovery has an explicit reason. Controlled re-entry.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecoveryDecision(BaseModel, frozen=True):
    """Decision about whether a suspended pair can recover."""

    pair: str
    can_recover: bool
    health_score: float
    recovery_threshold: float
    consecutive_healthy: int = 0
    required_consecutive: int = 3
    message: str = ""


def evaluate_recovery(
    pair: str,
    health_score: float,
    recovery_threshold: float = 0.5,
    consecutive_healthy: int = 0,
    required_consecutive: int = 3,
) -> RecoveryDecision:
    """Decide if a suspended pair can return to active.

    Recovery requires:
    - health_score >= recovery_threshold
    - N consecutive healthy checks (hysteresis to prevent flapping)
    """
    is_healthy = health_score >= recovery_threshold
    new_consecutive = consecutive_healthy + 1 if is_healthy else 0
    can_recover = new_consecutive >= required_consecutive

    if can_recover:
        msg = f"{pair}: recovered after {new_consecutive} consecutive healthy checks"
    elif is_healthy:
        msg = f"{pair}: healthy but need {required_consecutive - new_consecutive} more checks"
    else:
        msg = f"{pair}: still unhealthy ({health_score:.3f} < {recovery_threshold:.3f})"

    return RecoveryDecision(
        pair=pair,
        can_recover=can_recover,
        health_score=health_score,
        recovery_threshold=recovery_threshold,
        consecutive_healthy=new_consecutive,
        required_consecutive=required_consecutive,
        message=msg,
    )
