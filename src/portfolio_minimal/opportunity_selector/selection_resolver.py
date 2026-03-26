"""
Build-8 / opportunity_selector / selection_resolver
Produce the final selection and explicit relative rejections.

IMPORTANT: This module only rejects on structural grounds (no cluster).
Size/capacity constraints are NOT applied here — allocation_router
will reduce oversized trades rather than reject them outright.
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


def resolve_selection(
    ranked: tuple[RankedCandidate, ...],
    initial_snapshot: PortfolioSnapshot,
) -> SelectionResult:
    """Select candidates that deserve capital.

    Only structural rejection: no-cluster (fail-closed).
    ALL other candidates pass through to allocation_router,
    which will reduce sizes to fit budgets.
    """
    selected: list[SelectionEntry] = []
    rejected: list[SelectionEntry] = []

    for rc in ranked:
        c = rc.candidate

        elig = check_eligibility(c, initial_snapshot)

        if elig.verdict == EligibilityVerdict.ELIGIBLE:
            selected.append(SelectionEntry(
                pair=c.pair,
                engine_id=c.engine_id,
                ranking_score=rc.ranking_score,
                rank=rc.rank,
                verdict=SelectionVerdict.SELECTED,
                candidate=c,
            ))
        else:
            selected_verdict = SelectionVerdict.REJECTED_NO_CLUSTER
            rejected.append(SelectionEntry(
                pair=c.pair,
                engine_id=c.engine_id,
                ranking_score=rc.ranking_score,
                rank=rc.rank,
                verdict=selected_verdict,
                reason=elig.reason,
                candidate=c,
            ))

    return SelectionResult(
        selected=tuple(selected),
        rejected=tuple(rejected),
    )
