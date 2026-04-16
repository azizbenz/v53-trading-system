"""Typed end-to-end regression tests for the Build-8 portfolio orchestrator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from portfolio_minimal.allocation_router.base_size_builder import SizeProfile
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CandidatePoolRejectReason,
    build_enforced_candidate_pool_freshness,
)
from portfolio_minimal.opportunity_selector.correlation_conflict_checker import ConflictType
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
from portfolio_minimal.opportunity_selector.selection_resolver import SelectionVerdict
from portfolio_minimal.portfolio_orchestrator import (
    OrchestratorConfig,
    PortfolioRelativeRankAdjustmentInput,
    PortfolioRelativeRankAdjustmentOutcome,
    run_portfolio_pipeline,
)

from ._portfolio_support import build_candidate, build_config


class TestPortfolioOrchestrator:
    def test_orchestrator_requires_explicit_freshness_policy(self) -> None:
        with pytest.raises(ValidationError, match="freshness_policy"):
            OrchestratorConfig(
                size_profile=SizeProfile(available_capital=10_000.0),
                initial_snapshot=PortfolioSnapshot(
                    remaining_gross_capacity=1_000.0,
                    remaining_loss_capacity=50.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"btc_cluster": 500.0},
                ),
            )

    def test_basic_e2e_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                ),
                build_candidate(
                    pair="ETH/USDT",
                    score=0.6,
                    size=100.0,
                    cluster="eth_cluster",
                ),
            ),
            build_config(),
        )
        assert result.pool_size == 2
        assert result.report.count_allocated == 2
        assert result.report.count_phantom == 0

    def test_portfolio_relative_rank_hook_reorders_candidates_before_selection(self) -> None:
        candidates = (
            build_candidate(
                pair="BTC/USDT",
                score=0.8,
                ce=0.05,
                cluster="btc_cluster",
            ),
            build_candidate(
                pair="ETH/USDT",
                score=0.6,
                ce=0.10,
                cluster="eth_cluster",
            ),
        )

        def _hook(
            hook_input: PortfolioRelativeRankAdjustmentInput,
        ) -> PortfolioRelativeRankAdjustmentOutcome:
            if hook_input.pair == "ETH/USDT":
                return PortfolioRelativeRankAdjustmentOutcome(
                    rank_delta=0.5,
                    reason_codes=("ARTIFACT_PORTFOLIO_RANK_BOOST",),
                    detail="artifact promoted ETH in relative rank",
                )
            return PortfolioRelativeRankAdjustmentOutcome()

        result = run_portfolio_pipeline(
            candidates,
            build_config(),
            relative_rank_hook=_hook,
        )
        assert result.selection is not None
        assert tuple(entry.pair for entry in result.selection.selected) == (
            "ETH/USDT",
            "BTC/USDT",
        )
        assert result.selection.selected[0].rank == 1
        assert result.selection.selected[1].rank == 2
        assert result.report.allocations[0].pair == "ETH/USDT"

    def test_empty_candidates(self) -> None:
        result = run_portfolio_pipeline((), build_config())
        assert result.pool_size == 0
        assert result.report.count_allocated == 0

    def test_no_cluster_rejected_in_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (build_candidate(pair="X", cluster=""),),
            build_config(),
        )
        assert result.report.count_allocated == 0
        assert result.selection is not None
        assert len(result.selection.rejected) == 1

    def test_unknown_cluster_rejected_in_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (build_candidate(pair="X", cluster="unknown"),),
            build_config(),
        )
        assert result.report.count_allocated == 0
        assert result.selection is not None
        assert len(result.selection.rejected) == 1
        assert (
            result.selection.rejected[0].verdict
            == SelectionVerdict.REJECTED_UNKNOWN_CLUSTER
        )
        assert result.report.count_phantom == 0

    def test_oversized_reduced_not_rejected(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=5000.0,
                    cluster="btc_cluster",
                ),
            ),
            build_config(capital=50000.0, gross=200.0, cluster_cap=500.0),
        )
        assert result.selection is not None
        assert len(result.selection.selected) == 1
        assert result.report.count_allocated == 1
        assert result.report.total_allocated <= 200.0

    def test_loss_budget_reduces_allocation(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                    estimated_loss=10.0,
                ),
            ),
            build_config(loss_cap=5.0),
        )
        assert result.report.count_allocated == 1
        assert result.report.total_allocated <= 50.0 + 1e-6

    def test_beta_budget_reduces_allocation(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                    beta_impact=0.5,
                ),
            ),
            build_config(beta_cap=0.1),
        )
        assert result.report.count_allocated == 1
        assert result.report.total_allocated <= 20.0 + 1e-6

    def test_phantom_sterilized_in_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                    beta_impact=0.5,
                ),
            ),
            build_config(beta_cap=0.01),
        )
        assert result.report.count_phantom == 1
        assert result.report.count_allocated == 0

    def test_cost_exceeds_edge_after_allocation_sterilized(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                    cost=0.02,
                    ev_net=0.01,
                    estimated_loss=1.0,
                    beta_impact=0.01,
                ),
            ),
            build_config(),
        )
        assert result.report.count_phantom == 1
        assert result.report.count_allocated == 0
        assert (
            "COST_EXCEEDS_EDGE_AFTER_ALLOCATION"
            in result.report.phantoms[0].viability_reason
        )

    def test_duplicate_pair_deduped_in_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    score=0.9,
                    cluster="btc_cluster",
                ),
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_b",
                    score=0.5,
                    cluster="btc_cluster",
                ),
            ),
            build_config(),
        )
        assert result.conflicts is not None
        assert result.conflicts.duplicates_removed == 1
        assert result.report.count_allocated == 1

    def test_multiple_trades_budget_decremented(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.9,
                    size=100.0,
                    cluster="btc_cluster",
                    estimated_loss=5.0,
                    beta_impact=0.2,
                ),
                build_candidate(
                    pair="ETH/USDT",
                    score=0.7,
                    size=100.0,
                    cluster="eth_cluster",
                    estimated_loss=5.0,
                    beta_impact=0.2,
                ),
            ),
            build_config(loss_cap=8.0, beta_cap=10.0),
        )
        assert result.report.count_allocated >= 1

    def test_orchestrator_result_has_all_stages(self) -> None:
        result = run_portfolio_pipeline(
            (build_candidate(pair="BTC/USDT", cluster="btc_cluster"),),
            build_config(),
        )
        assert result.pool_size == 1
        assert result.conflicts is not None
        assert result.selection is not None
        assert result.report is not None

    def test_contradictory_a_b_signals_are_neutralized_in_pipeline(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    direction="long",
                    emitted_at=100.0,
                    cluster="btc_cluster",
                ),
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_b",
                    direction="short",
                    emitted_at=120.0,
                    cluster="btc_cluster",
                ),
            ),
            build_config(),
        )
        assert result.conflicts is not None
        assert any(
            conflict.conflict_type == ConflictType.CONTRADICTORY_SIGNAL
            for conflict in result.conflicts.conflicts
        )
        assert result.report.count_allocated == 0
        assert len(result.conflicts.rejection_audit) == 2

    def test_expired_signal_is_visible_and_not_allocated(self) -> None:
        config = build_config().model_copy(
            update={
                "freshness_policy": build_enforced_candidate_pool_freshness(
                    now_ts=500.0,
                    max_signal_age_s=60.0,
                )
            }
        )
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    emitted_at=100.0,
                    cluster="btc_cluster",
                ),
            ),
            config,
        )
        assert result.pool_size == 0
        assert len(result.pool_rejections) == 1
        assert result.pool_rejections[0].reason == CandidatePoolRejectReason.SIGNAL_EXPIRED
        assert result.report.count_allocated == 0

    def test_report_exposes_remaining_capital_after_allocation(self) -> None:
        result = run_portfolio_pipeline(
            (
                build_candidate(
                    pair="BTC/USDT",
                    score=0.8,
                    size=100.0,
                    cluster="btc_cluster",
                ),
            ),
            build_config(gross=1000.0),
        )
        assert result.report.count_allocated == 1
        assert result.report.capital_remaining < 1000.0
