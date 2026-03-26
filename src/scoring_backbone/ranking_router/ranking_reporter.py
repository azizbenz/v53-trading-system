"""
Build-5 / ranking_router / ranking_reporter
Complete ranking and relative rejection reporting.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RankingEvent(BaseModel, frozen=True):
    pool_size: int
    selected_count: int
    rejected_by_ranking: int
    rejected_by_portfolio: int
    version: str = ""
    timestamp: float = 0.0


class RankingStats(BaseModel, frozen=True):
    total_rounds: int = 0
    total_candidates: int = 0
    total_selected: int = 0
    total_rejected_ranking: int = 0
    total_rejected_portfolio: int = 0
    mean_pool_size: float = 0.0
    selection_rate: float = 0.0


class RankingReporter:
    """Track and report ranking events."""

    def __init__(self) -> None:
        self._events: list[RankingEvent] = []

    def record(self, event: RankingEvent) -> None:
        self._events.append(event)

    def get_stats(self) -> RankingStats:
        n = len(self._events)
        if n == 0:
            return RankingStats()

        total_cand = sum(e.pool_size for e in self._events)
        total_sel = sum(e.selected_count for e in self._events)
        total_rr = sum(e.rejected_by_ranking for e in self._events)
        total_rp = sum(e.rejected_by_portfolio for e in self._events)

        return RankingStats(
            total_rounds=n,
            total_candidates=total_cand,
            total_selected=total_sel,
            total_rejected_ranking=total_rr,
            total_rejected_portfolio=total_rp,
            mean_pool_size=total_cand / n,
            selection_rate=total_sel / total_cand if total_cand > 0 else 0.0,
        )

    def get_events(self) -> tuple[RankingEvent, ...]:
        return tuple(self._events)
