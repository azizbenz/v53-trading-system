"""
8.5.1 — Last Update Tracker: store last update timestamp per stream/pair.

Invariant: age must be measured explicitly. No implicit assumptions about freshness.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UpdateRecord(BaseModel, frozen=True):
    """Last update record for a pair+stream combination."""

    pair: str
    stream_type: str
    last_update_time: float
    update_count: int = 0


class LastUpdateTracker:
    """Track last update times per pair and stream type."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], float] = {}  # (pair, stream) -> timestamp
        self._counts: dict[tuple[str, str], int] = {}

    def record_update(self, pair: str, stream_type: str, timestamp: float) -> None:
        """Record an update for a pair+stream."""
        key = (pair, stream_type)
        self._records[key] = timestamp
        self._counts[key] = self._counts.get(key, 0) + 1

    def get_last_update(self, pair: str, stream_type: str) -> float | None:
        """Get last update time. Returns None if never updated."""
        return self._records.get((pair, stream_type))

    def get_record(self, pair: str, stream_type: str) -> UpdateRecord | None:
        key = (pair, stream_type)
        ts = self._records.get(key)
        if ts is None:
            return None
        return UpdateRecord(
            pair=pair,
            stream_type=stream_type,
            last_update_time=ts,
            update_count=self._counts.get(key, 0),
        )

    def get_all_records(self) -> tuple[UpdateRecord, ...]:
        result = []
        for (pair, stream), ts in self._records.items():
            result.append(UpdateRecord(
                pair=pair,
                stream_type=stream,
                last_update_time=ts,
                update_count=self._counts.get((pair, stream), 0),
            ))
        return tuple(result)

    def get_pairs(self) -> frozenset[str]:
        return frozenset(pair for pair, _ in self._records)
