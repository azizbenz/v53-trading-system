"""
4.5.4 — Reconnect Controller: backoff strategy, reconnection logging.

Invariant: every reconnection must be logged with reason and attempt count.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class ReconnectEvent(BaseModel, frozen=True):
    """Log entry for a reconnection attempt."""

    endpoint: str
    attempt: int
    delay_s: float
    reason: str
    success: bool
    timestamp: float


class ReconnectController:
    """Exponential backoff reconnection controller.

    Stateless logic: given attempt number, compute delay.
    Tracks history for auditability.
    """

    def __init__(
        self,
        base_delay_s: float = 1.0,
        max_delay_s: float = 60.0,
        max_attempts: int = 10,
    ) -> None:
        self._base_delay = base_delay_s
        self._max_delay = max_delay_s
        self._max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._history: list[ReconnectEvent] = []

    def compute_delay(self, endpoint: str) -> float:
        """Compute delay for next reconnect attempt (exponential backoff)."""
        attempt = self._attempts.get(endpoint, 0)
        delay = min(self._base_delay * (2 ** attempt), self._max_delay)
        return delay

    def should_retry(self, endpoint: str) -> bool:
        return self._attempts.get(endpoint, 0) < self._max_attempts

    def record_attempt(
        self, endpoint: str, delay_s: float, reason: str, success: bool, timestamp: float,
    ) -> ReconnectEvent:
        attempt = self._attempts.get(endpoint, 0) + 1
        self._attempts[endpoint] = attempt
        event = ReconnectEvent(
            endpoint=endpoint,
            attempt=attempt,
            delay_s=delay_s,
            reason=reason,
            success=success,
            timestamp=timestamp,
        )
        self._history.append(event)
        if success:
            self._attempts[endpoint] = 0
        return event

    def reset(self, endpoint: str) -> None:
        self._attempts[endpoint] = 0

    def get_attempt_count(self, endpoint: str) -> int:
        return self._attempts.get(endpoint, 0)

    def get_history(self, endpoint: str | None = None) -> tuple[ReconnectEvent, ...]:
        if endpoint is None:
            return tuple(self._history)
        return tuple(e for e in self._history if e.endpoint == endpoint)
