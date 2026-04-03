from __future__ import annotations

from engine_d import EngineDRuntime, EngineDRuntimeInput, EngineDRuntimeStatus
from engines.engine_d.engine_d_runner import EngineDInput
from interface_contracts import EngineId, RegimeId, Side, SignalType
from risk_backbone.risk_runtime import RiskLimits, RiskRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringCandidateInput, ScoringRuntime


def _good_engine_inputs(**overrides) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        regime="trending_up",
        regime_favorability=0.78,
        pair_health=0.90,
        data_freshness=0.94,
        flow_coherence=0.81,
        expected_gain=0.009,
        expected_cost=0.0020,
        candidate_size=800.0,
        holding_period=2.0,
        entry_price=104.0,
        reentry_anchor_price=101.5,
        atr=1.8,
        scoring_version="engine_d.v1",
    )
    defaults.update(overrides)
    return EngineDInput(**defaults)


def _penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(PenaltyDefinition(penalty_id="context_soft", name="Context soft", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="size_soft", name="Size soft", penalty_type=PenaltyType.SIZE))
    return registry


def _scoring_runtime() -> ScoringRuntime:
    return ScoringRuntime(_penalty_registry())


def _risk_runtime() -> RiskRuntime:
    return RiskRuntime(
        RiskLimits(
            gross_cap=5000.0,
            position_cap=3000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )


def _portfolio_state(**overrides) -> PortfolioState:
    defaults = dict(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)


def _runtime_input(**overrides) -> EngineDRuntimeInput:
    defaults = dict(
        engine_inputs=_good_engine_inputs(),
        timestamp_ms=1_700_000_000_000,
        portfolio=_portfolio_state(),
        projected_size=800.0,
        projected_loss=40.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.7,
        cluster_id="btc_majors",
    )
    defaults.update(overrides)
    return EngineDRuntimeInput(**defaults)


def test_runtime_emits_signal_and_accepts_through_risk():
    runtime = EngineDRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(_runtime_input(), now=10.0)
    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.D
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.TRENDING_UP
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.take_profit is not None
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True


def test_runtime_hard_blocked_logs_reasons():
    runtime = EngineDRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(
        _runtime_input(blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True)),
        now=20.0,
    )
    assert result.status == EngineDRuntimeStatus.HARD_BLOCKED
    joined = " ".join(
        reason
        for entry in result.log_entries
        if entry.event == "engine_d_hard_blocked"
        for reason in entry.reasons
    ).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable():
    runtime = EngineDRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    peer = ScoringCandidateInput(
        engine_id="engine_a",
        pair="ETHUSDT",
        raw_features={"structure": 0.99},
        allowed_features=frozenset({"structure"}),
        weights={"structure": 1.0},
        scoring_version="engine_a.v1",
        expected_cost=0.0005,
        expected_ce=0.003,
        projected_size=500.0,
        projected_loss=20.0,
        projected_beta_impact=0.0,
        cluster_id="eth_ecosystem",
    )
    result = runtime.evaluate(
        _runtime_input(
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0}),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
        ),
        now=30.0,
    )
    assert result.status == EngineDRuntimeStatus.REJECTED_RANKING
    assert any(entry.event == "engine_d_rejected_by_ranking" for entry in result.log_entries)


def test_runtime_rejected_by_portfolio_is_auditable():
    runtime = EngineDRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(_runtime_input(portfolio=_portfolio_state(remaining_gross_capacity=10.0)), now=40.0)
    assert result.status == EngineDRuntimeStatus.REJECTED_PORTFOLIO
    assert any(entry.event == "engine_d_rejected_by_portfolio" for entry in result.log_entries)


def test_runtime_cannot_bypass_risk_runtime():
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = EngineDRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineDRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
