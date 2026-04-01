"""
Build-8 / opportunity_selector / comparative_ranker
Rank opportunities by composite score.

R_i = w1·S_i + w2·CE_i - w3·Cost_i - w4·CorrPenalty_i

Rules:
- At similar score, favor better CE
- At similar CE, favor lower cost
- Engine A can beat B on high conviction, but not automatically
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate


RANKING_VERSION = "build8_rank_v1"


class RankedCandidate(BaseModel, frozen=True):
    """A candidate with its ranking score."""

    candidate: OpportunityCandidate
    ranking_score: float
    rank: int = 0  # 1-based, set after sorting
    ranking_version: str = RANKING_VERSION


# Ranking weights
_W_SCORE = 0.35
_W_CE = 0.30
_W_COST = 0.20
_W_CORR = 0.15


def compute_ranking_score(
    candidate: OpportunityCandidate,
    cluster_utilization: float = 0.0,  # [0,1] — how full the candidate's cluster is
) -> float:
    """Compute composite ranking score for a candidate.

    R_i = w1·penalized_score + w2·CE_expected - w3·expected_cost - w4·cluster_utilization

    Higher is better.
    """
    return (
        _W_SCORE * candidate.penalized_score
        + _W_CE * candidate.ce_expected
        - _W_COST * candidate.expected_cost
        - _W_CORR * cluster_utilization
    )


def rank_candidates(
    candidates: tuple[OpportunityCandidate, ...],
    cluster_utilizations: dict[str, float] | None = None,
) -> tuple[RankedCandidate, ...]:
    """Rank candidates by composite score, highest first.

    Returns tuple sorted by ranking_score descending, with 1-based rank.
    """
    utils = cluster_utilizations or {}

    scored = []
    for c in candidates:
        corr_util = utils.get(c.cluster_id, 0.0)
        rs = compute_ranking_score(c, cluster_utilization=corr_util)
        scored.append((c, rs))

    scored.sort(
        key=lambda x: (
            -x[1],
            x[0].pair,
            x[0].engine_id,
            x[0].direction,
            x[0].emitted_at,
        )
    )

    return tuple(
        RankedCandidate(candidate=c, ranking_score=rs, rank=i + 1)
        for i, (c, rs) in enumerate(scored)
    )
