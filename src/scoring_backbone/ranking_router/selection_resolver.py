"""
Build-5 / ranking_router / selection_resolver
Choose which opportunities actually pass.

Selected = arg top-k R_i subject to portfolio constraints.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SelectionOutcome(StrEnum):
    SELECTED = "selected"
    REJECTED_RANKING = "rejected_ranking"
    REJECTED_PORTFOLIO = "rejected_portfolio"


class SelectionEntry(BaseModel, frozen=True):
    """Entry in the final selection list."""

    engine_id: str
    pair: str
    ranking_score: float
    rank: int
    outcome: SelectionOutcome
    rejection_reason: str = ""


class SelectionResult(BaseModel, frozen=True):
    """Complete selection result."""

    entries: tuple[SelectionEntry, ...] = ()
    selected_count: int = 0
    rejected_by_ranking: int = 0
    rejected_by_portfolio: int = 0


def resolve_selection(
    ranked_candidates: tuple[dict[str, object], ...],
    max_selections: int,
    portfolio_rejected_keys: frozenset[tuple[str, str]],
) -> SelectionResult:
    """Select top-k candidates that pass portfolio compatibility.

    ranked_candidates must be pre-sorted by ranking_score descending.
    Each dict: engine_id, pair, ranking_score, rank.
    portfolio_rejected_keys: set of (engine_id, pair) that failed portfolio check.
    """
    entries: list[SelectionEntry] = []
    selected = 0

    for c in ranked_candidates:
        eid = str(c["engine_id"])
        pair = str(c["pair"])
        rs = float(c["ranking_score"])
        rank = int(c["rank"])
        key = (eid, pair)

        if key in portfolio_rejected_keys:
            entries.append(SelectionEntry(
                engine_id=eid,
                pair=pair,
                ranking_score=rs,
                rank=rank,
                outcome=SelectionOutcome.REJECTED_PORTFOLIO,
                rejection_reason="portfolio budget insufficient",
            ))
        elif selected < max_selections:
            entries.append(SelectionEntry(
                engine_id=eid,
                pair=pair,
                ranking_score=rs,
                rank=rank,
                outcome=SelectionOutcome.SELECTED,
            ))
            selected += 1
        else:
            entries.append(SelectionEntry(
                engine_id=eid,
                pair=pair,
                ranking_score=rs,
                rank=rank,
                outcome=SelectionOutcome.REJECTED_RANKING,
                rejection_reason=f"rank {rank} exceeded max selections {max_selections}",
            ))

    rej_ranking = sum(1 for e in entries if e.outcome == SelectionOutcome.REJECTED_RANKING)
    rej_portfolio = sum(1 for e in entries if e.outcome == SelectionOutcome.REJECTED_PORTFOLIO)

    return SelectionResult(
        entries=tuple(entries),
        selected_count=selected,
        rejected_by_ranking=rej_ranking,
        rejected_by_portfolio=rej_portfolio,
    )
