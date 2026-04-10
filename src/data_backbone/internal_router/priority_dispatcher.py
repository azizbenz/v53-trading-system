"""
7.5.2 — Priority Dispatcher: dispatch events with priority ordering.

Invariant: priority execution/risk > analytics. Deterministic routing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .consumer_registry import ConsumerPriority, ConsumerSubscription


_CONSUMER_PRIORITY_ORDER = {
    ConsumerPriority.CRITICAL: 0,
    ConsumerPriority.HIGH: 1,
    ConsumerPriority.NORMAL: 2,
    ConsumerPriority.LOW: 3,
}


class DispatchResult(BaseModel, frozen=True):
    """Result of dispatching a single event."""

    event_type: str
    pair: str
    dispatched_to: tuple[str, ...] = ()
    dropped_for: tuple[str, ...] = ()
    total_dispatched: int = 0
    total_dropped: int = 0


def dispatch_event(
    event_type: str,
    pair: str,
    consumers: tuple[ConsumerSubscription, ...],
    blocked_consumers: frozenset[str] = frozenset(),
) -> DispatchResult:
    """Dispatch an event to matching consumers by priority.

    Consumers in blocked_consumers are skipped (backpressure).
    Returns dispatch result with success/drop tracking.
    """
    dispatched: list[str] = []
    dropped: list[str] = []

    ordered_consumers = sorted(
        consumers,
        key=lambda consumer: (
            _CONSUMER_PRIORITY_ORDER.get(consumer.priority, 99),
            consumer.consumer_id,
        ),
    )

    for consumer in ordered_consumers:
        if consumer.consumer_id in blocked_consumers:
            dropped.append(consumer.consumer_id)
        else:
            dispatched.append(consumer.consumer_id)

    return DispatchResult(
        event_type=event_type,
        pair=pair,
        dispatched_to=tuple(dispatched),
        dropped_for=tuple(dropped),
        total_dispatched=len(dispatched),
        total_dropped=len(dropped),
    )
