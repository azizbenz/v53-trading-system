"""
Build-5 / ranking_router / candidate_pool_builder
Build pool of surviving (non-hard-blocked) opportunities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RankingCandidate(BaseModel, frozen=True):
    """A candidate that survived hard block gate."""

    engine_id: str
    pair: str
    penalized_score: float
    size_multiplier: float = 1.0
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    projected_risk: float = 0.0
    cluster_id: str = ""


class CandidatePool(BaseModel, frozen=True):
    """Pool of surviving candidates."""

    candidates: tuple[RankingCandidate, ...] = ()
    total_submitted: int = 0
    hard_blocked: int = 0

    @property
    def pool_size(self) -> int:
        return len(self.candidates)


def build_candidate_pool(
    all_candidates: tuple[RankingCandidate, ...],
    blocked_keys: frozenset[tuple[str, str]],
) -> CandidatePool:
    """Build pool, filtering out hard-blocked (engine_id, pair) combos."""
    survivors: list[RankingCandidate] = []
    blocked_count = 0

    for c in all_candidates:
        key = (c.engine_id, c.pair)
        if key in blocked_keys:
            blocked_count += 1
        else:
            survivors.append(c)

    return CandidatePool(
        candidates=tuple(survivors),
        total_submitted=len(all_candidates),
        hard_blocked=blocked_count,
    )
