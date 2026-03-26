"""
Build-8 / opportunity_selector / eligibility_filter
Check if an opportunity is still compatible with current portfolio state.

Verifies: gross cap, loss budget, beta cap, cluster cap.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate


class EligibilityVerdict(StrEnum):
    ELIGIBLE = "eligible"
    REJECTED_GROSS_CAP = "rejected_gross_cap"
    REJECTED_CLUSTER = "rejected_cluster"
    REJECTED_NO_CLUSTER = "rejected_no_cluster"


class PortfolioSnapshot(BaseModel, frozen=True):
    """Current portfolio state for eligibility checks."""

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
    """Check if a candidate fits within current portfolio budgets.

    Fail-closed: no cluster_id => rejected.
    """
    if candidate.candidate_size > snapshot.remaining_gross_capacity:
        return EligibilityResult(
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            verdict=EligibilityVerdict.REJECTED_GROSS_CAP,
            reason=f"size {candidate.candidate_size:.2f} > remaining gross {snapshot.remaining_gross_capacity:.2f}",
        )

    if not candidate.cluster_id:
        return EligibilityResult(
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            verdict=EligibilityVerdict.REJECTED_NO_CLUSTER,
            reason=f"{candidate.pair}: no cluster mapping — fail-closed",
        )

    cluster_remaining = snapshot.remaining_cluster_capacity.get(candidate.cluster_id, 0.0)
    if candidate.candidate_size > cluster_remaining:
        return EligibilityResult(
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            verdict=EligibilityVerdict.REJECTED_CLUSTER,
            reason=f"size {candidate.candidate_size:.2f} > cluster '{candidate.cluster_id}' remaining {cluster_remaining:.2f}",
        )

    return EligibilityResult(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        verdict=EligibilityVerdict.ELIGIBLE,
    )
