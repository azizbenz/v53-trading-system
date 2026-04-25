"""Canonical inter-build stitch from Build-8 portfolio output to Build-3 execution."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from execution_backbone.execution_runtime_models import ExecutionOpportunity
from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from portfolio import (
    AllocationEntry,
    OpportunityCandidate,
    OrchestratorResult,
    SelectionEntry,
    SelectionVerdict,
)


_DIRECTION_TO_SIDE = {
    "long": "buy",
    "buy": "buy",
    "short": "sell",
    "sell": "sell",
}


class ExecutionOpportunityBridgeContext(BaseModel, frozen=True):
    """Additive execution-edge context layered over a canonical portfolio choice."""

    intent_id: str = Field(..., min_length=1)
    spread_bps: float = 0.0
    safety_margin: float = 0.0005
    pair_suspended: bool = False
    pair_health_score: float = 1.0
    pair_health_min: float = 0.3
    risk_budget_available: bool = True
    infrastructure_ok: bool = True
    data_stale: bool = False
    max_acceptable_cost: float = 0.01
    reference_price: float | None = None
    price_limit: float | None = None
    profile: str = "COMPLETE"
    venue_constraints: VenueConstraintSnapshot | None = None
    signal_arrival_monotonic_s: float | None = Field(default=None, ge=0.0)
    scoring_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    risk_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    portfolio_completed_monotonic_s: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, object] = Field(default_factory=dict)


class PortfolioExecutionSelection(BaseModel, frozen=True):
    """Resolved one-to-one stitch between the selected and allocated Build-8 rows."""

    selection_entry: SelectionEntry
    allocation_entry: AllocationEntry
    selection_version: str = ""
    ranking_version: str = ""

    @model_validator(mode="after")
    def validate_consistency(self) -> "PortfolioExecutionSelection":
        if self.selection_entry.verdict != SelectionVerdict.SELECTED:
            raise ValueError("portfolio execution stitch requires SelectionVerdict.SELECTED")
        if self.selection_entry.pair != self.allocation_entry.pair:
            raise ValueError("selection/allocation pair mismatch")
        if self.selection_entry.engine_id != self.allocation_entry.engine_id:
            raise ValueError("selection/allocation engine_id mismatch")
        if self.allocation_entry.is_phantom:
            raise ValueError("phantom allocations cannot be stitched into ExecutionOpportunity")
        if self.allocation_entry.final_size <= 0.0:
            raise ValueError("allocation final_size must stay > 0 for execution stitching")
        if not math.isclose(
            self.selection_entry.ranking_score,
            self.allocation_entry.ranking_score,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("selection/allocation ranking_score mismatch")
        return self


def resolve_portfolio_execution_selection(
    orchestrator_result: OrchestratorResult,
    *,
    pair: str,
    engine_id: str,
) -> PortfolioExecutionSelection:
    """Resolve one canonical Build-8 choice into a stitchable selection/allocation pair."""

    selection = orchestrator_result.selection
    if selection is None:
        raise ValueError("orchestrator_result.selection is required for execution stitching")

    selected_matches = tuple(
        entry
        for entry in selection.selected
        if entry.pair == pair and entry.engine_id == engine_id
    )
    if not selected_matches:
        raise ValueError(
            f"no selected portfolio entry found for pair={pair!r}, engine_id={engine_id!r}"
        )
    if len(selected_matches) > 1:
        raise ValueError(
            f"multiple selected portfolio entries found for pair={pair!r}, engine_id={engine_id!r}"
        )

    allocation_matches = tuple(
        entry
        for entry in orchestrator_result.report.allocations
        if entry.pair == pair and entry.engine_id == engine_id
    )
    if not allocation_matches:
        raise ValueError(
            f"no viable allocation found for pair={pair!r}, engine_id={engine_id!r}"
        )
    if len(allocation_matches) > 1:
        raise ValueError(
            f"multiple viable allocations found for pair={pair!r}, engine_id={engine_id!r}"
        )

    return PortfolioExecutionSelection(
        selection_entry=selected_matches[0],
        allocation_entry=allocation_matches[0],
        selection_version=selection.selection_version,
        ranking_version=selection.ranking_version,
    )


def build_execution_opportunity_from_portfolio_selection(
    selection: PortfolioExecutionSelection,
    *,
    context: ExecutionOpportunityBridgeContext,
) -> ExecutionOpportunity:
    """Project one resolved portfolio decision into the canonical Build-3 input contract."""

    candidate = selection.selection_entry.candidate
    side = _resolve_execution_side(candidate)
    metadata = _build_execution_metadata(selection, context=context)
    expected_gain = _resolve_expected_gain(candidate)
    return ExecutionOpportunity(
        intent_id=context.intent_id,
        pair=selection.selection_entry.pair,
        engine_id=selection.selection_entry.engine_id,
        side=side,
        quantity=selection.allocation_entry.final_size,
        expected_gain=expected_gain,
        expected_cost=candidate.expected_cost,
        score=selection.selection_entry.ranking_score,
        justification=_build_execution_justification(selection),
        spread_bps=context.spread_bps,
        safety_margin=context.safety_margin,
        pair_suspended=context.pair_suspended,
        pair_health_score=context.pair_health_score,
        pair_health_min=context.pair_health_min,
        risk_budget_available=context.risk_budget_available,
        infrastructure_ok=context.infrastructure_ok,
        data_stale=context.data_stale,
        max_acceptable_cost=context.max_acceptable_cost,
        reference_price=context.reference_price,
        price_limit=context.price_limit,
        profile=context.profile,
        venue_constraints=context.venue_constraints,
        signal_arrival_monotonic_s=context.signal_arrival_monotonic_s,
        scoring_completed_monotonic_s=context.scoring_completed_monotonic_s,
        risk_completed_monotonic_s=context.risk_completed_monotonic_s,
        portfolio_completed_monotonic_s=context.portfolio_completed_monotonic_s,
        metadata=metadata,
    )


def build_execution_opportunity_from_orchestrator_result(
    orchestrator_result: OrchestratorResult,
    *,
    pair: str,
    engine_id: str,
    context: ExecutionOpportunityBridgeContext,
) -> ExecutionOpportunity:
    """Resolve and project one viable Build-8 choice into Build-3."""

    selection = resolve_portfolio_execution_selection(
        orchestrator_result,
        pair=pair,
        engine_id=engine_id,
    )
    return build_execution_opportunity_from_portfolio_selection(
        selection,
        context=context,
    )


def _resolve_execution_side(candidate: OpportunityCandidate) -> str:
    normalized = candidate.direction.strip().casefold()
    try:
        return _DIRECTION_TO_SIDE[normalized]
    except KeyError as exc:
        raise ValueError(
            f"unsupported portfolio direction for execution stitching: {candidate.direction!r}"
        ) from exc


def _resolve_expected_gain(candidate: OpportunityCandidate) -> float:
    return max(0.0, candidate.expected_cost + candidate.ce_expected)


def _build_execution_justification(selection: PortfolioExecutionSelection) -> str:
    allocation = selection.allocation_entry
    return (
        f"portfolio selected {allocation.pair} via {allocation.engine_id} "
        f"rank={selection.selection_entry.rank} "
        f"score={selection.selection_entry.ranking_score:.6f} "
        f"tier={allocation.tier} "
        f"final_size={allocation.final_size:.6f}"
    )


def _build_execution_metadata(
    selection: PortfolioExecutionSelection,
    *,
    context: ExecutionOpportunityBridgeContext,
) -> dict[str, object]:
    metadata = dict(context.metadata)
    candidate = selection.selection_entry.candidate
    bridge_payload = {
        "selection_version": selection.selection_version,
        "ranking_version": selection.ranking_version,
        "selection_rank": selection.selection_entry.rank,
        "selection_score": selection.selection_entry.ranking_score,
        "selection_verdict": selection.selection_entry.verdict.value,
        "direction": candidate.direction,
        "tier_suggestion": candidate.tier_suggestion,
        "cluster_id": candidate.cluster_id,
        "candidate_size": candidate.candidate_size,
        "base_size": selection.allocation_entry.base_size,
        "modulated_size": selection.allocation_entry.modulated_size,
        "final_size": selection.allocation_entry.final_size,
        "cap_reason": selection.allocation_entry.cap_reason,
        "viability_reason": selection.allocation_entry.viability_reason,
        "scoring_version": candidate.scoring_version,
    }
    existing_bridge = metadata.get("portfolio_bridge")
    if isinstance(existing_bridge, dict):
        bridge_payload = {**existing_bridge, **bridge_payload}
    metadata["portfolio_bridge"] = bridge_payload
    if "timestamp_ms" not in metadata and candidate.emitted_at >= 1_000_000_000.0:
        metadata["timestamp_ms"] = int(candidate.emitted_at * 1000.0)
    return metadata


__all__ = [
    "ExecutionOpportunityBridgeContext",
    "PortfolioExecutionSelection",
    "build_execution_opportunity_from_orchestrator_result",
    "build_execution_opportunity_from_portfolio_selection",
    "resolve_portfolio_execution_selection",
]
