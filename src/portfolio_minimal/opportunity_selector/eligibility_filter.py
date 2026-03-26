"""
Build-8 / opportunity_selector / eligibility_filter
Check if an opportunity is structurally eligible for portfolio consideration.

IMPORTANT: This module does NOT reject based on size/capacity.
Size reduction is handled downstream by allocation_router.
Only hard structural rejections happen here (fail-closed no-cluster).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate


class EligibilityVerdict(StrEnum):
    ELIGIBLE = "eligible"
    REJECTED_NO_CLUSTER = "rejected_no_cluster"


class PortfolioSnapshot(BaseModel, frozen=True):
    """Current portfolio state for downstream allocation.

    Stored here as shared model used by both selector and allocation_router.
    """

    remaining_gross_capacity: float = 0.0
    remaining_loss_capacity: float = 0.0
    remaining_beta_capacity: float = 0.0
    remaining_cluster_capacity: dict[str, float] = Field(default_factory=dict)


class EligibilityResult(BaseModel, frozen=True):
    pair: str
    engine_id: str
    verdict: EligibilityVerdict
    reason: str = ""


def check_eligibility(
    candidate: OpportunityCandidate,
    snapshot: PortfolioSnapshot,
) -> EligibilityResult:
    """Check if a candidate is structurally eligible for selection.

    Only hard rejection: fail-closed when cluster_id is missing.
    Size-based constraints (gross cap, cluster cap, loss budget, beta budget)
    are NOT checked here — allocation_router handles reduction.
    """
    # ── Fail-closed: no cluster mapping ──
    if not candidate.cluster_id:
        return EligibilityResult(
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            verdict=EligibilityVerdict.REJECTED_NO_CLUSTER,
            reason=f"{candidate.pair}: no cluster mapping — fail-closed",
        )

    return EligibilityResult(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        verdict=EligibilityVerdict.ELIGIBLE,
    )
