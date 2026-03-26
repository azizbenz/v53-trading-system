"""
Build-8 / opportunity_selector / candidate_pool_builder
Build the pool of A/B opportunities that passed hard blockers.

Candidates = {i : HB_i = 0}
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OpportunityCandidate(BaseModel, frozen=True):
    """A single opportunity from Engine A or B, ready for portfolio selection."""

    pair: str
    engine_id: str  # "engine_a" or "engine_b"
    penalized_score: float
    raw_score: float = 0.0
    ce_expected: float = 0.0  # capital efficiency
    expected_cost: float = 0.0
    ev_net: float = 0.0
    candidate_size: float = 0.0
    tier_suggestion: str = "tier_1"
    cluster_id: str = ""
    beta_impact: float = 0.0
    holding_hours: float = 0.0
    scoring_version: str = ""


class CandidatePool(BaseModel, frozen=True):
    """Pool of opportunities available for selection."""

    candidates: tuple[OpportunityCandidate, ...] = ()
    pool_size: int = 0
    engines_present: tuple[str, ...] = ()


def build_candidate_pool(
    candidates: tuple[OpportunityCandidate, ...],
) -> CandidatePool:
    """Build the candidate pool from surviving opportunities.

    Only accepts candidates with positive penalized_score and positive candidate_size.
    """
    valid = tuple(
        c for c in candidates
        if c.penalized_score > 0.0 and c.candidate_size > 0.0
    )
    engines = tuple(sorted(set(c.engine_id for c in valid)))

    return CandidatePool(
        candidates=valid,
        pool_size=len(valid),
        engines_present=engines,
    )
