from __future__ import annotations

from pathlib import Path

from engines.engine_a import (
    EngineAInput,
    EngineARuntime,
    EngineARuntimeInput,
    EngineARuntimeStatus,
    run_engine_a,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyRegistry
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringRuntime


def test_engine_a_runner_and_runtime_smoke(repo_tmp_path: Path) -> None:
    engine_inputs = EngineAInput(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.8,
        structure_quality=0.8,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.8,
        regime_confidence=0.8,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        flow_score=0.8,
        cost_preference_score=0.8,
        delta_confirmation=0.9,
        competition_density=0.2,
        expected_gain=0.01,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=4.0,
        delta_safe=0.0005,
        ce_min=0.0001,
        entry_price=100.0,
        realized_vol_current=0.02,
        atr=2.0,
        scoring_version="A_v1",
    )
    runner_output = run_engine_a(engine_inputs)
    assert runner_output.decision.value == "emit"

    runtime = EngineARuntime(
        scoring_runtime=ScoringRuntime(PenaltyRegistry()),
        risk_runtime=RiskRuntime(
            RiskLimits(
                gross_cap=5000.0,
                position_cap=3000.0,
                loss_cap=500.0,
                beta_cap=5000.0,
                cluster_cap=5000.0,
            )
        ),
        circuit_breaker=EmergencyCircuitBreaker(
            state_dir=Path(repo_tmp_path) / ".codex_kill_switch_tests" / "engine_a_integration"
        ),
    )

    runtime_result = runtime.evaluate(
        EngineARuntimeInput(
            engine_inputs=engine_inputs,
            timestamp_ms=1_700_000_000_000,
            portfolio=PortfolioState(
                remaining_gross_capacity=5000.0,
                remaining_loss_capacity=500.0,
                remaining_beta_capacity=5000.0,
                remaining_cluster_capacity={"btc_majors": 5000.0},
            ),
            projected_size=1000.0,
            projected_loss=50.0,
            current_equity=10_000.0,
            session_peak_equity=10_000.0,
            pair_beta=0.8,
            cluster_id="btc_majors",
            strategy_id="strategy-a-breakout",
        ),
        now=10.0,
    )

    assert runtime_result.status == EngineARuntimeStatus.ACCEPTED
    assert runtime_result.signal_candidate is not None
    assert runtime_result.forecast_signal_candidate is not None
