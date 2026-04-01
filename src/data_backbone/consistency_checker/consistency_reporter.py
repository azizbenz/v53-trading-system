"""
9.5.5 - Consistency Reporter: aggregate consistency metrics.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConsistencyScore(BaseModel, frozen=True):
    """Consistency score for a pair."""

    pair: str
    score: float
    gap_rate: float = 0.0
    dup_rate: float = 0.0
    disorder_rate: float = 0.0
    contradiction_rate: float = 0.0


class ConsistencyStats(BaseModel, frozen=True):
    """Aggregate consistency statistics."""

    total_gaps: int = 0
    total_duplicates: int = 0
    total_disorders: int = 0
    total_contradictions: int = 0
    scores_by_pair: dict[str, float] = Field(default_factory=dict)


def compute_consistency_score(
    gap_rate: float = 0.0,
    dup_rate: float = 0.0,
    disorder_rate: float = 0.0,
    contradiction_rate: float = 0.0,
    w_gap: float = 0.3,
    w_dup: float = 0.2,
    w_disorder: float = 0.2,
    w_contradiction: float = 0.3,
) -> float:
    """Compute consistency score clamped to [0, 1]."""
    raw = 1.0 - (
        w_gap * gap_rate
        + w_dup * dup_rate
        + w_disorder * disorder_rate
        + w_contradiction * contradiction_rate
    )
    return max(0.0, min(1.0, raw))


class ConsistencyReporter:
    """Track and report consistency metrics."""

    def __init__(self) -> None:
        self._scores: dict[str, ConsistencyScore] = {}
        self._total_gaps: int = 0
        self._total_duplicates: int = 0
        self._total_disorders: int = 0
        self._total_contradictions: int = 0

    def update_score(self, score: ConsistencyScore) -> None:
        self._scores[score.pair] = score

    def record_gap(self, count: int = 1) -> None:
        self._total_gaps += count

    def record_duplicate(self, count: int = 1) -> None:
        self._total_duplicates += count

    def record_disorder(self, count: int = 1) -> None:
        self._total_disorders += count

    def record_contradiction(self, count: int = 1) -> None:
        self._total_contradictions += count

    def get_score(self, pair: str) -> ConsistencyScore | None:
        return self._scores.get(pair)

    def get_all_scores(self) -> tuple[ConsistencyScore, ...]:
        return tuple(self._scores.values())

    def get_stats(self) -> ConsistencyStats:
        return ConsistencyStats(
            total_gaps=self._total_gaps,
            total_duplicates=self._total_duplicates,
            total_disorders=self._total_disorders,
            total_contradictions=self._total_contradictions,
            scores_by_pair={p: s.score for p, s in self._scores.items()},
        )

    def get_worst_pair(self) -> ConsistencyScore | None:
        if not self._scores:
            return None
        return min(self._scores.values(), key=lambda s: s.score)
