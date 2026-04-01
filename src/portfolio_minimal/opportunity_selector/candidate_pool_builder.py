"""
Build-8 / opportunity_selector / candidate_pool_builder
Build the pool of A/B opportunities that passed hard blockers.

Candidates = {i : HB_i = 0}
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OpportunityCandidate(BaseModel, frozen=True):
    """A single opportunity from Engine A or B, ready for portfolio selection."""

    pair: str
    engine_id: str  # "engine_a" or "engine_b"
    direction: str = "long"
    emitted_at: float = 0.0
    penalized_score: float
    raw_score: float = 0.0
    ce_expected: float = 0.0  # capital efficiency
    expected_cost: float = 0.0
    ev_net: float = 0.0
    candidate_size: float = 0.0
    tier_suggestion: str = "tier_1"
    cluster_id: str = ""
    estimated_loss: float = 0.0  # L_i at candidate_size
    beta_impact: float = 0.0  # β impact at candidate_size
    holding_hours: float = 0.0
    scoring_version: str = ""


class CandidatePoolRejectReason(StrEnum):
    NON_POSITIVE_SCORE = "non_positive_score"
    NON_POSITIVE_SIZE = "non_positive_size"
    SIGNAL_EXPIRED = "signal_expired"


class CandidatePoolRejection(BaseModel, frozen=True):
    """Auditable rejection for candidates dropped before ranking."""

    pair: str
    engine_id: str
    reason: CandidatePoolRejectReason
    detail: str = ""


class CandidatePool(BaseModel, frozen=True):
    """Pool of opportunities available for selection."""

    candidates: tuple[OpportunityCandidate, ...] = ()
    pool_size: int = 0
    engines_present: tuple[str, ...] = ()
    rejected_candidates: tuple[CandidatePoolRejection, ...] = ()
    rejected_count: int = 0


def build_candidate_pool(
    candidates: tuple[OpportunityCandidate, ...],
    now_ts: float | None = None,
    max_signal_age_s: float | None = None,
) -> CandidatePool:
    """Build the candidate pool from surviving opportunities.

    Only accepts candidates with positive penalized_score and positive candidate_size.
    """
    valid: list[OpportunityCandidate] = []
    rejected: list[CandidatePoolRejection] = []

    for candidate in candidates:
        if candidate.penalized_score <= 0.0:
            rejected.append(CandidatePoolRejection(
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                reason=CandidatePoolRejectReason.NON_POSITIVE_SCORE,
                detail="candidate dropped before portfolio selection because penalized_score <= 0",
            ))
            continue

        if candidate.candidate_size <= 0.0:
            rejected.append(CandidatePoolRejection(
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                reason=CandidatePoolRejectReason.NON_POSITIVE_SIZE,
                detail="candidate dropped before portfolio selection because candidate_size <= 0",
            ))
            continue

        if (
            now_ts is not None
            and max_signal_age_s is not None
            and max_signal_age_s >= 0.0
            and candidate.emitted_at > 0.0
            and now_ts - candidate.emitted_at > max_signal_age_s
        ):
            rejected.append(CandidatePoolRejection(
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                reason=CandidatePoolRejectReason.SIGNAL_EXPIRED,
                detail=(
                    f"signal age {now_ts - candidate.emitted_at:.3f}s exceeds "
                    f"max_signal_age_s={max_signal_age_s:.3f}s"
                ),
            ))
            continue

        valid.append(candidate)

    engines = tuple(sorted(set(c.engine_id for c in valid)))

    return CandidatePool(
        candidates=tuple(valid),
        pool_size=len(valid),
        engines_present=engines,
        rejected_candidates=tuple(rejected),
        rejected_count=len(rejected),
    )
