"""
7.5.4 — Backpressure Guard: protect the system if a consumer slows down.

Invariant: no non-critical consumer can freeze ingestion. Message loss is bounded and visible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .consumer_registry import ConsumerPriority


class BackpressureAction(StrEnum):
    NONE = "none"
    WARN = "warn"
    DROP = "drop"
    BLOCK = "block"


class BackpressureStatus(BaseModel, frozen=True):
    """Backpressure status for a consumer."""

    consumer_id: str
    queue_utilization: float
    action: BackpressureAction
    is_blocked: bool = False


def evaluate_backpressure(
    consumer_id: str,
    queue_utilization: float,
    priority: ConsumerPriority,
    warn_threshold: float = 0.7,
    drop_threshold: float = 0.9,
) -> BackpressureStatus:
    """Evaluate backpressure action for a consumer based on queue utilization.

    - Critical consumers: only warn, never drop
    - High: warn + drop at threshold
    - Normal/Low: warn + drop at threshold
    """
    if queue_utilization < warn_threshold:
        return BackpressureStatus(
            consumer_id=consumer_id,
            queue_utilization=queue_utilization,
            action=BackpressureAction.NONE,
        )

    if queue_utilization < drop_threshold:
        return BackpressureStatus(
            consumer_id=consumer_id,
            queue_utilization=queue_utilization,
            action=BackpressureAction.WARN,
        )

    # At or above drop threshold
    if priority == ConsumerPriority.CRITICAL:
        # Never drop critical consumers, only warn
        return BackpressureStatus(
            consumer_id=consumer_id,
            queue_utilization=queue_utilization,
            action=BackpressureAction.WARN,
        )

    return BackpressureStatus(
        consumer_id=consumer_id,
        queue_utilization=queue_utilization,
        action=BackpressureAction.DROP,
        is_blocked=True,
    )
