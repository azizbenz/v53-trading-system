"""
7.5.1 — Consumer Registry: register consumers and their subscriptions.

Invariant: every consumer has explicit subscriptions. No implicit routing.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ConsumerPriority(StrEnum):
    CRITICAL = "critical"  # execution, risk
    HIGH = "high"  # scoring
    NORMAL = "normal"  # analytics, monitoring
    LOW = "low"  # logging, debug


class ConsumerSubscription(BaseModel, frozen=True):
    """A consumer's subscription to specific event types/pairs."""

    consumer_id: str
    event_types: frozenset[str] = frozenset()  # empty = all types
    pairs: frozenset[str] = frozenset()  # empty = all pairs
    priority: ConsumerPriority = ConsumerPriority.NORMAL


class ConsumerRegistry:
    """Track registered consumers and their subscriptions."""

    def __init__(self) -> None:
        self._consumers: dict[str, ConsumerSubscription] = {}

    def register(self, subscription: ConsumerSubscription) -> None:
        """Register a consumer. Overwrites if already registered."""
        self._consumers[subscription.consumer_id] = subscription

    def unregister(self, consumer_id: str) -> bool:
        """Remove a consumer. Returns False if not found."""
        return self._consumers.pop(consumer_id, None) is not None

    def get(self, consumer_id: str) -> ConsumerSubscription | None:
        return self._consumers.get(consumer_id)

    def get_consumers_for_event(
        self, event_type: str, pair: str,
    ) -> tuple[ConsumerSubscription, ...]:
        """Find all consumers interested in a given event type + pair."""
        result = []
        for sub in self._consumers.values():
            type_match = not sub.event_types or event_type in sub.event_types
            pair_match = not sub.pairs or pair in sub.pairs
            if type_match and pair_match:
                result.append(sub)
        # Sort by priority (critical first)
        priority_order = {
            ConsumerPriority.CRITICAL: 0,
            ConsumerPriority.HIGH: 1,
            ConsumerPriority.NORMAL: 2,
            ConsumerPriority.LOW: 3,
        }
        result.sort(key=lambda s: priority_order.get(s.priority, 99))
        return tuple(result)

    @property
    def consumer_count(self) -> int:
        return len(self._consumers)

    def all_consumers(self) -> tuple[ConsumerSubscription, ...]:
        return tuple(self._consumers.values())
