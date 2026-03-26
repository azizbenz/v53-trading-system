"""
Build-5 / hard_block_gate / blocker_reporter
Report hard blocking statistics.

HBRate = N_HB / N_candidates
HBRate_r = N_{HB,r} / N_candidates
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from scoring_backbone.hard_block_gate.blocker_registry import BlockerID


class BlockerStats(BaseModel, frozen=True):
    total_candidates: int = 0
    total_blocked: int = 0
    total_passed: int = 0
    hb_rate: float = 0.0
    by_reason: dict[str, int] = Field(default_factory=dict)


class BlockerReporter:
    """Track and report hard block events."""

    def __init__(self) -> None:
        self._total: int = 0
        self._blocked: int = 0
        self._by_reason: dict[str, int] = {}

    def record_passed(self) -> None:
        self._total += 1

    def record_blocked(self, reason_codes: tuple[str, ...]) -> None:
        self._total += 1
        self._blocked += 1
        for code in reason_codes:
            self._by_reason[code] = self._by_reason.get(code, 0) + 1

    def get_stats(self) -> BlockerStats:
        n = self._total
        rate = self._blocked / n if n > 0 else 0.0

        return BlockerStats(
            total_candidates=n,
            total_blocked=self._blocked,
            total_passed=n - self._blocked,
            hb_rate=rate,
            by_reason=dict(self._by_reason),
        )
