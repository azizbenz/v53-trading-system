"""
9.5.1 — Sequence Checker: verify logical ordering of messages.

Invariant: every disorder event is visible. No silent reordering.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SequenceVerdict(StrEnum):
    IN_ORDER = "in_order"
    OUT_OF_ORDER = "out_of_order"
    FIRST_MESSAGE = "first_message"


class SequenceCheckResult(BaseModel, frozen=True):
    """Result of checking a single message's sequence."""

    pair: str
    stream_type: str
    sequence: int
    expected: int | None
    verdict: SequenceVerdict


class SequenceChecker:
    """Track and verify message sequence ordering per pair+stream."""

    def __init__(self) -> None:
        self._last_seq: dict[tuple[str, str], int] = {}
        self._disorder_count: dict[tuple[str, str], int] = {}
        self._total_checked: int = 0

    def check(self, pair: str, stream_type: str, sequence: int) -> SequenceCheckResult:
        """Check if a message is in order."""
        key = (pair, stream_type)
        self._total_checked += 1

        last = self._last_seq.get(key)
        if last is None:
            self._last_seq[key] = sequence
            return SequenceCheckResult(
                pair=pair,
                stream_type=stream_type,
                sequence=sequence,
                expected=None,
                verdict=SequenceVerdict.FIRST_MESSAGE,
            )

        expected = last + 1
        if sequence >= expected:
            self._last_seq[key] = sequence
            return SequenceCheckResult(
                pair=pair,
                stream_type=stream_type,
                sequence=sequence,
                expected=expected,
                verdict=SequenceVerdict.IN_ORDER,
            )

        # Out of order
        self._disorder_count[key] = self._disorder_count.get(key, 0) + 1
        return SequenceCheckResult(
            pair=pair,
            stream_type=stream_type,
            sequence=sequence,
            expected=expected,
            verdict=SequenceVerdict.OUT_OF_ORDER,
        )

    def get_disorder_count(self, pair: str, stream_type: str) -> int:
        return self._disorder_count.get((pair, stream_type), 0)

    @property
    def total_checked(self) -> int:
        return self._total_checked

    @property
    def total_disorders(self) -> int:
        return sum(self._disorder_count.values())
