"""Canonical facade tests for Build-8 portfolio."""

from __future__ import annotations

import portfolio
from portfolio import OrchestratorConfig, OrchestratorResult, run_portfolio_pipeline
from portfolio_minimal.allocation_router.base_size_builder import SizeProfile
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CANDIDATE_POOL_FRESHNESS_DISABLED,
    OpportunityCandidate,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
from portfolio_minimal.portfolio_orchestrator import (
    OrchestratorConfig as ImplOrchestratorConfig,
    OrchestratorResult as ImplOrchestratorResult,
    run_portfolio_pipeline as impl_run_portfolio_pipeline,
)


def test_portfolio_facade_exports_expected_symbols():
    assert portfolio.__all__ == [
        "allocation_router",
        "opportunity_selector",
        "OrchestratorConfig",
        "OrchestratorResult",
        "run_portfolio_pipeline",
    ]


def test_portfolio_facade_reexports_impl_symbols():
    assert OrchestratorConfig is ImplOrchestratorConfig
    assert OrchestratorResult is ImplOrchestratorResult
    assert run_portfolio_pipeline is impl_run_portfolio_pipeline


def test_portfolio_facade_runs_minimal_pipeline():
    candidate = OpportunityCandidate(
        pair="BTCUSDT",
        engine_id="engine_a",
        penalized_score=0.90,
        raw_score=0.90,
        ce_expected=0.05,
        expected_cost=0.01,
        ev_net=0.04,
        candidate_size=100.0,
        tier_suggestion="tier_1",
        cluster_id="btc_cluster",
        estimated_loss=5.0,
        beta_impact=0.10,
    )
    config = OrchestratorConfig(
        size_profile=SizeProfile(
            available_capital=10000.0,
            base_fraction=0.02,
            min_size=10.0,
            max_size=500.0,
        ),
        initial_snapshot=PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"btc_cluster": 500.0},
        ),
        freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
    )

    result = run_portfolio_pipeline((candidate,), config)

    assert isinstance(result, OrchestratorResult)
    assert result.pool_size == 1
    assert result.report.count_allocated == 1
    assert result.report.allocations[0].pair == "BTCUSDT"
    assert result.report.allocations[0].engine_id == "engine_a"
    assert result.report.capital_remaining < 1000.0
