"""
4.5.3 — Heartbeat Monitor: detect silence, missing heartbeats.

Invariant: absence of heartbeat must be visible, not silent.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class HeartbeatStatus(StrEnum):
    ALIVE = "alive"
    LATE = "late"
    SILENT = "silent"


class HeartbeatState(BaseModel, frozen=True):
    endpoint: str
    status: HeartbeatStatus
    last_heartbeat_time: float | None = None
    miss_count: int = 0
    silence_duration_s: float = 0.0


class HeartbeatMonitor:
    """Track heartbeats per endpoint. Detect silence."""

    def __init__(self, heartbeat_interval_s: float = 30.0, late_threshold_s: float = 45.0) -> None:
        self._interval = heartbeat_interval_s
        self._late_threshold = late_threshold_s
        self._last_heartbeat: dict[str, float] = {}
        self._miss_counts: dict[str, int] = {}

    def record_heartbeat(self, endpoint: str, timestamp: float) -> None:
        self._last_heartbeat[endpoint] = timestamp
        self._miss_counts[endpoint] = 0

    def check_status(self, endpoint: str, now: float) -> HeartbeatState:
        last = self._last_heartbeat.get(endpoint)
        if last is None:
            return HeartbeatState(
                endpoint=endpoint,
                status=HeartbeatStatus.SILENT,
                miss_count=0,
                silence_duration_s=0.0,
            )

        elapsed = now - last
        if elapsed <= self._interval:
            return HeartbeatState(
                endpoint=endpoint,
                status=HeartbeatStatus.ALIVE,
                last_heartbeat_time=last,
                miss_count=0,
            )
        elif elapsed <= self._late_threshold:
            return HeartbeatState(
                endpoint=endpoint,
                status=HeartbeatStatus.LATE,
                last_heartbeat_time=last,
                miss_count=1,
                silence_duration_s=elapsed - self._interval,
            )
        else:
            misses = int(elapsed / self._interval)
            self._miss_counts[endpoint] = misses
            return HeartbeatState(
                endpoint=endpoint,
                status=HeartbeatStatus.SILENT,
                last_heartbeat_time=last,
                miss_count=misses,
                silence_duration_s=elapsed,
            )

    def get_miss_count(self, endpoint: str) -> int:
        return self._miss_counts.get(endpoint, 0)
