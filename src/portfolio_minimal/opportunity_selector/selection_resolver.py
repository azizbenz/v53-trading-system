"""
Build-8 / opportunity_selector / selection_resolver
Produce the final selection and explicit relative rejections.

Greedy fill: walk ranked survivors top-down, accept if eligible, reject otherwise.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate
from portfolio_minimal.opportunity_selector.comparative_ranker import RankedCandidate
from portfolio_minimal.opportunity_selector.eligibility_filter import (
    EligibilityVerdict,
    PortfolioSnapshot,
    check_eligibility,
)


class SelectionVerdict(StrEnum):
    SELECTED = "selected"
    REJECTED_CAPACITY = "rejected_capacity"
    REJECTED_CLUSTER = "rejected_cluster"
    REJECTED_NO_CLUSTER = "rejected_no_cluster"


class SelectionEntry(BaseModel, frozen=True):
    """One entry in the final selection output."""

    pair: str
    engine_id: str
    ranking_score: float
    rank: int
    verdict: SelectionVerdict
    reason: str = ""
    candidate: OpportunityCandidate


class SelectionResult(BaseModel, frozen=True):
    """Full selection output: selected + rejected with reasons."""

    selected: tuple[SelectionEntry, ...] = ()
    rejected: tuple[SelectionEntry, ...] = ()
    total_selected_size: float = 0.0


_VERDICT_MAP: dict[EligibilityVerdict, SelectionVerdict] = {
    EligibilityVerdict.REJECTED_GROSS_CAP: SelectionVerdict.REJECTED_CAPACITY,
    EligibilityVerdict.REJECTED_CLUSTER: SelectionVerdict.REJECTED_CLUSTER,
    EligibilityVerdict.REJECTED_NO_CLUSTER: SelectionVerdict.REJECTED_NO_CLUSTER,
}


def resolve_selection(
    ranked: tuple[RankedCandidate, ...],
    initial_snapshot: PortfolioSnapshot,
) -> SelectionResult:
    """Greedy top-down selection under portfolio constraints.

    Walk ranked candidates from best to worst. For each:
    - Check eligibility against *remaining* capacity
    - If eligible → select, decrement remaining capacity
    - If ineligible → reject with reason

    Returns selected and rejected entries.
    """
    remaining_gross = initial_snapshot.remaining_gross_capacity
    remaining_cluster: dict[str, float] = dict(initial_snapshot.remaining_cluster_capacity)

    selected: list[SelectionEntry] = []
    rejected: list[SelectionEntry] = []
    total_size = 0.0

    for rc in ranked:
        c = rc.candidate

        # Build a live snapshot with current remaining capacity
        live_snapshot = PortfolioSnapshot(
            remaining_gross_capacity=remaining_gross,
            remaining_loss_capacity=initial_snapshot.remaining_loss_capacity,
            remaining_beta_capacity=initial_snapshot.remaining_beta_capacity,
            remaining_cluster_capacity=remaining_cluster,
        )

        elig = check_eligibility(c, live_snapshot)

        if elig.verdict == EligibilityVerdict.ELIGIBLE:
            selected.append(SelectionEntry(
                pair=c.pair,
                engine_id=c.engine_id,
                ranking_score=rc.ranking_score,
                rank=rc.rank,
                verdict=SelectionVerdict.SELECTED,
                candidate=c,
            ))
            # Decrement capacity
            remaining_gross -= c.candidate_size
            if c.cluster_id in remaining_cluster:
                remaining_cluster[c.cluster_id] -= c.candidate_size
            total_size += c.candidate_size
        else:
            sel_verdict = _VERDICT_MAP.get(elig.verdict, SelectionVerdict.REJECTED_CAPACITY)
            rejected.append(SelectionEntry(
                pair=c.pair,
                engine_id=c.engine_id,
                ranking_score=rc.ranking_score,
                rank=rc.rank,
                verdict=sel_verdict,
                reason=elig.reason,
                candidate=c,
            ))

    return SelectionResult(
        selected=tuple(selected),
        rejected=tuple(rejected),
        total_selected_size=total_size,
    )
