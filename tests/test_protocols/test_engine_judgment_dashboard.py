from __future__ import annotations

from protocols import (
    ShadowEngineJudgment,
    ShadowEngineJudgmentSummary,
    ShadowPortfolioJudgment,
    build_engine_judgment_projection,
)


def test_build_engine_judgment_projection_maps_portfolio_and_cards():
    projection = build_engine_judgment_projection(
        ShadowEngineJudgmentSummary(
            source_report_id="shadow-report-1",
            source_shadow_run_id="shadow-run-1",
            source_shadow_days_completed=30,
            source_shadow_required_days=30,
            portfolio_judgment=ShadowPortfolioJudgment(
                judgment_verdict="shadow-only",
                physics_pressure="elevated",
                cluster_pressure="critical",
                beta_pressure="nominal",
                gross_capacity_pressure="nominal",
                loss_capacity_pressure="elevated",
                portfolio_rejected_engine_count=1,
                ranking_rejected_engine_count=1,
                elevated_physics_engine_count=1,
                critical_physics_engine_count=1,
                phantom_trade_count=2,
                rationale="portfolio concentration remained elevated in Shadow",
            ),
            judgments=(
                ShadowEngineJudgment(
                    engine_id="engine_a",
                    component_verdict="shadow_validated",
                    judgment_verdict="promotable",
                    useful_frequency=0.18,
                    ce_expected=0.0007,
                    estimated_cost_bps=4.0,
                    edge_net=8.4,
                    economic_pass_rate=0.88,
                    conflict_rate=0.10,
                    marginal_edge=0.0040,
                    redundancy_score=0.10,
                    portfolio_contribution=0.0040,
                    observations=12,
                    rationale="positive supervised shadow metrics",
                    evidence_summary="engine_a shadow evidence rendered",
                ),
                ShadowEngineJudgment(
                    engine_id="engine_b",
                    component_verdict="shadow_validated",
                    judgment_verdict="shadow-only",
                    useful_frequency=0.07,
                    ce_expected=0.0001,
                    estimated_cost_bps=3.4,
                    edge_net=1.2,
                    economic_pass_rate=0.64,
                    conflict_rate=0.31,
                    marginal_edge=0.0008,
                    redundancy_score=0.31,
                    portfolio_contribution=0.0008,
                    observations=8,
                    rationale="execution physics pressure remained elevated",
                    evidence_summary="engine_b shadow evidence rendered",
                ),
            ),
        )
    )

    assert projection.status == "warning"
    assert projection.portfolio_judgment_verdict == "shadow-only"
    assert projection.portfolio_physics_pressure == "elevated"
    assert projection.portfolio_cluster_pressure == "critical"
    assert projection.portfolio_rejected_engine_count == 1
    assert projection.critical_physics_engine_count == 1
    assert projection.phantom_trade_count == 2
    assert projection.portfolio_rationale == "portfolio concentration remained elevated in Shadow"
    assert len(projection.cards) == 2
    assert projection.cards[0].engine_id == "engine_a"
    assert projection.cards[0].status == "healthy"
    assert projection.cards[1].engine_id == "engine_b"
    assert projection.cards[1].status == "warning"

