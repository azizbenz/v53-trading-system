"""
9.5.2 — Gap Detector: detect observable gaps in message sequences.

GapRate = N_gaps / N_expected
Invariant: every gap is traced.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GapEvent(BaseModel, frozen=True):
    """A detected gap in a message sequence."""

    pair: str
    stream_type: str
    expected_seq: int
    actual_seq: int
    gap_size: int  # actual - expected


class GapDetector:
    """Detect sequence gaps per pair+stream."""

    def __init__(self) -> None:
        self._last_seq: dict[tuple[str, str], int] = {}
        self._gaps: list[GapEvent] = []
        self._total_expected: int = 0

    def check(self, pair: str, stream_type: str, sequence: int) -> GapEvent | None:
        """Check for a gap. Returns GapEvent if gap detected, None otherwise."""
        key = (pair, stream_type)
        self._total_expected += 1

        last = self._last_seq.get(key)
        self._last_seq[key] = sequence

        if last is None:
            return None

        expected = last + 1
        if sequence > expected:
            gap = GapEvent(
                pair=pair,
                stream_type=stream_type,
                expected_seq=expected,
                actual_seq=sequence,
                gap_size=sequence - expected,
            )
            self._gaps.append(gap)
            return gap

        return None

    def get_gaps(self, pair: str | None = None) -> tuple[GapEvent, ...]:
        if pair is None:
            return tuple(self._gaps)
        return tuple(g for g in self._gaps if g.pair == pair)

    @property
    def total_gaps(self) -> int:
        return len(self._gaps)

    @property
    def gap_rate(self) -> float:
        """GapRate = N_gaps / N_expected."""
        if self._total_expected == 0:
            return 0.0
        return len(self._gaps) / self._total_expected
