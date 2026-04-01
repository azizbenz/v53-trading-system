"""Runtime tests for Build-6 Engine A across canonical signal, scoring and risk."""

from __future__ import annotations

from engine_a import EngineARuntime, EngineARuntimeInput, EngineARuntimeStatus
from engines.engine_a.engine_a_runner import EngineAInput
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


def _good_engine_inputs(**overrides) -> EngineAInput:
    defaults = dict(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.9,
        structure_quality=0.85,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.9,
        regime_confidence=0.8,
        pair_health=0.9,
        data_freshness=0.95,
        flow_coherence=0.8,
        flow_score=0.4,
        cost_preference_score=0.5,
        expected_gain=0.005,
        expected_cost=0.001,
        candidate_size=1000.0,
        holding_period=4.0,
        entry_price=50000.0,
        atr=500.0,
        scoring_version="v1.0",
    )
    defaults.update(overrides)
    return EngineAInput(**defaults)


def _penalty_registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(
        PenaltyDefinition(
            penalty_id="context_soft",
            name="Context soft",
            penalty_type=PenaltyType.SCORE,
        )
    )
    registry.register(
        PenaltyDefinition(
            penalty_id="size_soft",
            name="Size soft",
            penalty_type=PenaltyType.SIZE,
        )
    )
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


def _runtime_input(**overrides) -> EngineARuntimeInput:
    defaults = dict(
        engine_inputs=_good_engine_inputs(),
        timestamp_ms=1_700_000_000_000,
        portfolio=_portfolio_state(),
        projected_size=1000.0,
        projected_loss=50.0,
        current_equity=10_000.0,
        session_peak_equity=10_000.0,
        pair_beta=0.8,
        cluster_id="btc_majors",
    )
    defaults.update(overrides)
    return EngineARuntimeInput(**defaults)


def test_runtime_emits_canonical_signal_and_accepts_through_risk():
    runtime = EngineARuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())

    result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.A
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.TRENDING_UP
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.max_hold_ms == 4 * 3600 * 1000
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    events = {entry.event for entry in result.log_entries}
    assert "engine_a_scoring_completed" in events
    assert "engine_a_accepted" in events


def test_runtime_hard_blocked_logs_explicit_reasons():
    runtime = EngineARuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    runtime_input = _runtime_input(
        blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
    )

    result = runtime.evaluate(runtime_input, now=20.0)

    assert result.status == EngineARuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.risk_evaluation is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_a_hard_blocked"]
    assert len(blocked_logs) == 1
    joined = " ".join(blocked_logs[0].reasons).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable():
    runtime = EngineARuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    peer = ScoringCandidateInput(
        engine_id="engine_b",
        pair="ETHUSDT",
        raw_features={"mean_reversion": 0.95},
        allowed_features=frozenset({"mean_reversion"}),
        weights={"mean_reversion": 1.0},
        scoring_version="engine_b.v1",
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
            portfolio=_portfolio_state(
                remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0},
            ),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.3, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
        ),
        now=30.0,
    )

    assert result.status == EngineARuntimeStatus.REJECTED_RANKING
    assert result.scoring_audit is not None
    assert result.scoring_audit.selection_entry is not None
    assert result.scoring_audit.selection_entry.outcome.value == "rejected_ranking"
    ranking_logs = [entry for entry in result.log_entries if entry.event == "engine_a_rejected_by_ranking"]
    assert len(ranking_logs) == 1
    assert "max selections" in ranking_logs[0].reasons[0]


def test_runtime_rejected_by_portfolio_is_auditable():
    runtime = EngineARuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(
        _runtime_input(
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineARuntimeStatus.REJECTED_PORTFOLIO
    portfolio_logs = [entry for entry in result.log_entries if entry.event == "engine_a_rejected_by_portfolio"]
    assert len(portfolio_logs) == 1
    assert "remaining gross" in portfolio_logs[0].reasons[0]


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
    runtime = EngineARuntime(scoring_runtime=_scoring_runtime(), risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)

    assert result.status == EngineARuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    risk_logs = [entry for entry in result.log_entries if entry.event == "engine_a_risk_rejected"]
    assert len(risk_logs) == 1
    assert "gross" in " ".join(risk_logs[0].reasons).lower()
