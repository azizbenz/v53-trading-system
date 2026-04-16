"""Shared typed helpers for portfolio_minimal tests."""

from __future__ import annotations

from portfolio_minimal.allocation_router.allocation_reporter import AllocationEntry
from portfolio_minimal.allocation_router.base_size_builder import SizeProfile
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CANDIDATE_POOL_FRESHNESS_DISABLED,
    OpportunityCandidate,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
from portfolio_minimal.portfolio_orchestrator import OrchestratorConfig


def build_candidate(
    pair: str = "BTC/USDT",
    engine: str = "engine_a",
    direction: str = "long",
    emitted_at: float = 0.0,
    score: float = 0.8,
    ce: float = 0.05,
    cost: float = 0.01,
    ev_net: float = 4.0,
    size: float = 100.0,
    tier: str = "tier_1",
    cluster: str = "btc_cluster",
    estimated_loss: float = 0.0,
    beta_impact: float = 0.0,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        pair=pair,
        engine_id=engine,
        direction=direction,
        emitted_at=emitted_at,
        penalized_score=score,
        raw_score=score,
        ce_expected=ce,
        expected_cost=cost,
        ev_net=ev_net,
        candidate_size=size,
        tier_suggestion=tier,
        cluster_id=cluster,
        estimated_loss=estimated_loss,
        beta_impact=beta_impact,
    )


def build_snapshot(
    *,
    gross: float = 1000.0,
    cluster_capacities: dict[str, float] | None = None,
    loss_cap: float = 0.0,
    beta_cap: float = 0.0,
) -> PortfolioSnapshot:
    if cluster_capacities is None:
        cluster_capacities = {"btc_cluster": 500.0}
    return PortfolioSnapshot(
        remaining_gross_capacity=gross,
        remaining_loss_capacity=loss_cap,
        remaining_beta_capacity=beta_cap,
        remaining_cluster_capacity=cluster_capacities,
    )


def build_allocation_entry(
    pair: str = "X",
    size: float = 100.0,
    *,
    phantom: bool = False,
) -> AllocationEntry:
    return AllocationEntry(
        pair=pair,
        engine_id="engine_a",
        base_size=100.0,
        modulated_size=size,
        final_size=size,
        tier="tier_1",
        ranking_score=0.5,
        is_phantom=phantom,
    )


def build_config(
    *,
    capital: float = 10000.0,
    gross: float = 1000.0,
    cluster_cap: float = 500.0,
    loss_cap: float = 50.0,
    beta_cap: float = 1.0,
) -> OrchestratorConfig:
    return OrchestratorConfig(
        size_profile=SizeProfile(available_capital=capital),
        initial_snapshot=build_snapshot(
            gross=gross,
            cluster_capacities={
                "btc_cluster": cluster_cap,
                "eth_cluster": cluster_cap,
            },
            loss_cap=loss_cap,
            beta_cap=beta_cap,
        ),
        freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
    )
