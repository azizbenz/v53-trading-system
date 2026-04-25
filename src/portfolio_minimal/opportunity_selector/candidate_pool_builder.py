"""
Build-8 / opportunity_selector / candidate_pool_builder
Build the pool of A/B opportunities that passed hard blockers.

Candidates = {i : HB_i = 0}
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


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
    forecast_strength: float | None = None
    instrument_price: float | None = None
    instrument_pct_vol: float | None = None
    point_value: float = 1.0


class CandidatePoolRejectReason(StrEnum):
    NON_POSITIVE_SCORE = "non_positive_score"
    NON_POSITIVE_SIZE = "non_positive_size"
    SIGNAL_EXPIRED = "signal_expired"


class CandidatePoolFreshnessMode(StrEnum):
    DISABLED = "disabled"
    ENFORCED = "enforced"


class CandidatePoolFreshnessPolicy(BaseModel, frozen=True):
    """Explicit freshness policy for candidate-pool construction."""

    mode: CandidatePoolFreshnessMode
    now_ts: float | None = None
    max_signal_age_s: float | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> "CandidatePoolFreshnessPolicy":
        if self.mode == CandidatePoolFreshnessMode.DISABLED:
            if self.now_ts is not None or self.max_signal_age_s is not None:
                raise ValueError(
                    "disabled candidate-pool freshness policy cannot carry now_ts/max_signal_age_s"
                )
            return self
        if self.now_ts is None or self.max_signal_age_s is None:
            raise ValueError(
                "enforced candidate-pool freshness policy requires now_ts and max_signal_age_s"
            )
        if not math.isfinite(self.now_ts) or self.now_ts < 0.0:
            raise ValueError("candidate-pool freshness policy now_ts must be finite and >= 0")
        if not math.isfinite(self.max_signal_age_s) or self.max_signal_age_s < 0.0:
            raise ValueError(
                "candidate-pool freshness policy max_signal_age_s must be finite and >= 0"
            )
        return self


def build_enforced_candidate_pool_freshness(
    *,
    now_ts: float,
    max_signal_age_s: float,
) -> CandidatePoolFreshnessPolicy:
    return CandidatePoolFreshnessPolicy(
        mode=CandidatePoolFreshnessMode.ENFORCED,
        now_ts=now_ts,
        max_signal_age_s=max_signal_age_s,
    )


CANDIDATE_POOL_FRESHNESS_DISABLED = CandidatePoolFreshnessPolicy(
    mode=CandidatePoolFreshnessMode.DISABLED
)


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
    *,
    freshness_policy: CandidatePoolFreshnessPolicy,
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

        if freshness_policy.mode == CandidatePoolFreshnessMode.ENFORCED:
            assert freshness_policy.now_ts is not None
            assert freshness_policy.max_signal_age_s is not None
            # BS-125: emitted_at=0.0 (default) previously bypassed expiry.
            # When expiry checking is active, unknown emission time is unsafe.
            if candidate.emitted_at <= 0.0:
                rejected.append(CandidatePoolRejection(
                    pair=candidate.pair,
                    engine_id=candidate.engine_id,
                    reason=CandidatePoolRejectReason.SIGNAL_EXPIRED,
                    detail="emitted_at not set — signal age unknown, rejected while expiry checking is active",
                ))
                continue
            signal_age_s = freshness_policy.now_ts - candidate.emitted_at
            if signal_age_s > freshness_policy.max_signal_age_s:
                rejected.append(CandidatePoolRejection(
                    pair=candidate.pair,
                    engine_id=candidate.engine_id,
                    reason=CandidatePoolRejectReason.SIGNAL_EXPIRED,
                    detail=(
                        f"signal age {signal_age_s:.3f}s exceeds "
                        f"max_signal_age_s={freshness_policy.max_signal_age_s:.3f}s"
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
