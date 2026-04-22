from __future__ import annotations

import pytest

from execution_backbone import ExecutionOpportunity
from portfolio import (
    AllocationEntry,
    OpportunityCandidate,
    OrchestratorResult,
    SelectionEntry,
    SelectionResult,
    SelectionVerdict,
)
from protocols import (
    ExecutionOpportunityBridgeContext,
    PortfolioExecutionSelection,
    build_execution_opportunity_from_orchestrator_result,
    build_execution_opportunity_from_portfolio_selection,
    resolve_portfolio_execution_selection,
)


def _candidate(
    *,
    pair: str = "BTCUSDT",
    engine_id: str = "engine_a",
    direction: str = "long",
    emitted_at: float = 1_710_000_000.25,
    penalized_score: float = 0.81,
    ce_expected: float = 0.008,
    expected_cost: float = 0.001,
    ev_net: float = 0.4,
    candidate_size: float = 50.0,
    tier_suggestion: str = "tier_1",
    cluster_id: str = "btc_cluster",
    scoring_version: str = "scoring-v1",
) -> OpportunityCandidate:
    return OpportunityCandidate(
        pair=pair,
        engine_id=engine_id,
        direction=direction,
        emitted_at=emitted_at,
        penalized_score=penalized_score,
        raw_score=penalized_score,
        ce_expected=ce_expected,
        expected_cost=expected_cost,
        ev_net=ev_net,
        candidate_size=candidate_size,
        tier_suggestion=tier_suggestion,
        cluster_id=cluster_id,
        scoring_version=scoring_version,
    )


def _selection_entry(
    candidate: OpportunityCandidate,
    *,
    rank: int = 1,
    ranking_score: float = 0.77,
) -> SelectionEntry:
    return SelectionEntry(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        ranking_score=ranking_score,
        rank=rank,
        verdict=SelectionVerdict.SELECTED,
        candidate=candidate,
    )


def _allocation_entry(
    candidate: OpportunityCandidate,
    *,
    ranking_score: float = 0.77,
    final_size: float = 25.0,
    is_phantom: bool = False,
) -> AllocationEntry:
    return AllocationEntry(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        base_size=30.0,
        modulated_size=27.0,
        final_size=final_size,
        tier=candidate.tier_suggestion,
        ranking_score=ranking_score,
        is_phantom=is_phantom,
        cap_reason="gross_cap",
        viability_reason="viable",
    )


def _orchestrator_result(
    selection_entry: SelectionEntry,
    allocation_entry: AllocationEntry,
) -> OrchestratorResult:
    return OrchestratorResult(
        pool_size=1,
        selection=SelectionResult(
            selection_version="build8_selection_v1",
            ranking_version="build8_ranking_v1",
            selected=(selection_entry,),
        ),
        report={
            "allocations": (allocation_entry,),
            "count_allocated": 1,
            "total_allocated": allocation_entry.final_size,
        },
    )


def test_resolve_portfolio_execution_selection_pairs_selected_and_allocated_rows() -> None:
    candidate = _candidate()
    selection_entry = _selection_entry(candidate)
    allocation_entry = _allocation_entry(candidate)
    result = _orchestrator_result(selection_entry, allocation_entry)

    stitched = resolve_portfolio_execution_selection(
        result,
        pair="BTCUSDT",
        engine_id="engine_a",
    )

    assert stitched.selection_entry is selection_entry
    assert stitched.allocation_entry is allocation_entry
    assert stitched.selection_version == "build8_selection_v1"
    assert stitched.ranking_version == "build8_ranking_v1"


def test_build_execution_opportunity_from_portfolio_selection_projects_canonical_fields() -> None:
    candidate = _candidate()
    stitched = PortfolioExecutionSelection(
        selection_entry=_selection_entry(candidate, rank=2, ranking_score=0.79),
        allocation_entry=_allocation_entry(candidate, ranking_score=0.79, final_size=22.5),
        selection_version="build8_selection_v1",
        ranking_version="build8_ranking_v1",
    )

    opportunity = build_execution_opportunity_from_portfolio_selection(
        stitched,
        context=ExecutionOpportunityBridgeContext(
            intent_id="intent-portfolio-1",
            spread_bps=2.5,
            signal_arrival_monotonic_s=99.4,
            scoring_completed_monotonic_s=99.7,
            risk_completed_monotonic_s=99.85,
            portfolio_completed_monotonic_s=100.1,
            metadata={"rest_quota_ratio_current": 0.25},
        ),
    )

    assert isinstance(opportunity, ExecutionOpportunity)
    assert opportunity.intent_id == "intent-portfolio-1"
    assert opportunity.side == "buy"
    assert opportunity.quantity == pytest.approx(22.5)
    assert opportunity.expected_gain == pytest.approx(0.009)
    assert opportunity.expected_cost == pytest.approx(0.001)
    assert opportunity.score == pytest.approx(0.79)
    assert opportunity.signal_arrival_monotonic_s == pytest.approx(99.4)
    assert opportunity.scoring_completed_monotonic_s == pytest.approx(99.7)
    assert opportunity.risk_completed_monotonic_s == pytest.approx(99.85)
    assert opportunity.portfolio_completed_monotonic_s == pytest.approx(100.1)
    assert opportunity.metadata["rest_quota_ratio_current"] == pytest.approx(0.25)
    assert opportunity.metadata["timestamp_ms"] == 1_710_000_000_250
    assert opportunity.metadata["portfolio_bridge"]["selection_rank"] == 2
    assert opportunity.metadata["portfolio_bridge"]["final_size"] == pytest.approx(22.5)
    assert "portfolio selected BTCUSDT via engine_a" in opportunity.justification


def test_build_execution_opportunity_from_orchestrator_result_supports_short_direction() -> None:
    candidate = _candidate(
        pair="ETHUSDT",
        engine_id="engine_b",
        direction="short",
        ce_expected=0.004,
        expected_cost=0.0015,
        ev_net=0.275,
    )
    selection_entry = _selection_entry(candidate, ranking_score=0.71)
    allocation_entry = _allocation_entry(candidate, ranking_score=0.71, final_size=12.5)
    result = _orchestrator_result(selection_entry, allocation_entry)

    opportunity = build_execution_opportunity_from_orchestrator_result(
        result,
        pair="ETHUSDT",
        engine_id="engine_b",
        context=ExecutionOpportunityBridgeContext(
            intent_id="intent-short-1",
            spread_bps=1.5,
            pair_health_score=0.85,
        ),
    )

    assert opportunity.side == "sell"
    assert opportunity.quantity == pytest.approx(12.5)
    assert opportunity.pair_health_score == pytest.approx(0.85)
    assert opportunity.expected_gain == pytest.approx(0.0055)


def test_portfolio_execution_selection_rejects_phantom_allocations() -> None:
    candidate = _candidate()

    with pytest.raises(ValueError, match="phantom allocations"):
        PortfolioExecutionSelection(
            selection_entry=_selection_entry(candidate),
            allocation_entry=_allocation_entry(candidate, is_phantom=True),
        )


def test_build_execution_opportunity_rejects_unknown_direction() -> None:
    candidate = _candidate(direction="flat")
    stitched = PortfolioExecutionSelection(
        selection_entry=_selection_entry(candidate),
        allocation_entry=_allocation_entry(candidate),
    )

    with pytest.raises(ValueError, match="unsupported portfolio direction"):
        build_execution_opportunity_from_portfolio_selection(
            stitched,
            context=ExecutionOpportunityBridgeContext(intent_id="intent-flat-1"),
        )
