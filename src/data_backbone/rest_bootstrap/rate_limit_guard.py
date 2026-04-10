"""
5.5.2 — Rate Limit Guard: protect API quotas, log usage.

Invariant: every REST call is tracked. Quota exceeded = explicit rejection.
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel, Field


class RateLimitState(BaseModel, frozen=True):
    calls_in_window: int
    window_start: float
    max_calls: int
    window_size_s: float
    is_throttled: bool


class RateLimitGuard:
    """Sliding window rate limiter for REST API calls."""

    def __init__(self, max_calls: int = 10, window_size_s: float = 60.0) -> None:
        self._max_calls = max_calls
        self._window_size = window_size_s
        self._call_times: deque[float] = deque()

    def can_call(self, now: float) -> bool:
        self._prune(now)
        return len(self._call_times) < self._max_calls

    def record_call(self, now: float) -> bool:
        """Record a call. Returns True if allowed, False if throttled."""
        self._prune(now)
        if len(self._call_times) >= self._max_calls:
            return False
        self._call_times.append(now)
        return True

    def get_state(self, now: float) -> RateLimitState:
        self._prune(now)
        return RateLimitState(
            calls_in_window=len(self._call_times),
            window_start=now - self._window_size,
            max_calls=self._max_calls,
            window_size_s=self._window_size,
            is_throttled=len(self._call_times) >= self._max_calls,
        )

    @property
    def usage_rate(self) -> float:
        """Current usage as fraction of max."""
        if self._max_calls == 0:
            return 1.0
        return len(self._call_times) / self._max_calls

    def _prune(self, now: float) -> None:
        cutoff = now - self._window_size
        while self._call_times and self._call_times[0] <= cutoff:
            self._call_times.popleft()
