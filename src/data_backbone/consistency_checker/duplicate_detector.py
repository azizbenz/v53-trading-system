"""
9.5.3 — Duplicate Detector: detect message duplications.

DupRate = N_dup / N_events
Invariant: every duplicate is visible.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DuplicateEvent(BaseModel, frozen=True):
    """A detected duplicate message."""

    pair: str
    stream_type: str
    sequence: int
    occurrence: int  # how many times seen


class DuplicateDetector:
    """Detect duplicate messages per pair+stream."""

    def __init__(self) -> None:
        self._seen: dict[tuple[str, str, int], int] = {}  # (pair, stream, seq) -> count
        self._duplicates: list[DuplicateEvent] = []
        self._total_events: int = 0

    def check(self, pair: str, stream_type: str, sequence: int) -> DuplicateEvent | None:
        """Check for duplicates. Returns DuplicateEvent if duplicate, None otherwise."""
        key = (pair, stream_type, sequence)
        self._total_events += 1

        count = self._seen.get(key, 0) + 1
        self._seen[key] = count

        if count > 1:
            dup = DuplicateEvent(
                pair=pair,
                stream_type=stream_type,
                sequence=sequence,
                occurrence=count,
            )
            self._duplicates.append(dup)
            return dup

        return None

    def get_duplicates(self, pair: str | None = None) -> tuple[DuplicateEvent, ...]:
        if pair is None:
            return tuple(self._duplicates)
        return tuple(d for d in self._duplicates if d.pair == pair)

    @property
    def total_duplicates(self) -> int:
        return len(self._duplicates)

    @property
    def dup_rate(self) -> float:
        """DupRate = N_dup / N_events."""
        if self._total_events == 0:
            return 0.0
        return len(self._duplicates) / self._total_events
