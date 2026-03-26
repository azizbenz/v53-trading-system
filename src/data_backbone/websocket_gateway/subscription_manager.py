"""
4.5.2 — Subscription Manager: pair → stream mapping, no duplicate subscriptions.

Invariant: double subscription is forbidden.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Subscription(BaseModel, frozen=True):
    """A single subscription to a WS stream."""

    pair: str
    stream_type: str  # "trade" | "depth" | "kline" | "ticker"
    endpoint: str


class SubscriptionRegistry:
    """Track active subscriptions. Prevent duplicates."""

    def __init__(self) -> None:
        self._subscriptions: dict[tuple[str, str], Subscription] = {}

    def subscribe(self, pair: str, stream_type: str, endpoint: str) -> Subscription:
        key = (pair, stream_type)
        if key in self._subscriptions:
            raise ValueError(
                f"Duplicate subscription: {pair}/{stream_type} already subscribed"
            )
        sub = Subscription(pair=pair, stream_type=stream_type, endpoint=endpoint)
        self._subscriptions[key] = sub
        return sub

    def unsubscribe(self, pair: str, stream_type: str) -> bool:
        key = (pair, stream_type)
        if key in self._subscriptions:
            del self._subscriptions[key]
            return True
        return False

    def is_subscribed(self, pair: str, stream_type: str) -> bool:
        return (pair, stream_type) in self._subscriptions

    def get_subscriptions_for_pair(self, pair: str) -> tuple[Subscription, ...]:
        return tuple(s for s in self._subscriptions.values() if s.pair == pair)

    def get_all_subscriptions(self) -> tuple[Subscription, ...]:
        return tuple(self._subscriptions.values())

    @property
    def count(self) -> int:
        return len(self._subscriptions)
