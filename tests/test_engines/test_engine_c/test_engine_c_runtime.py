from __future__ import annotations

from engine_c import EngineCRuntime, EngineCRuntimeInput, EngineCRuntimeStatus
from engines.engine_c.engine_c_runner import EngineCInput
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


def _good_engine_inputs(**overrides) -> EngineCInput:
    defaults = dict(
        pair="BTCUSDT",
        breakout_strength=0.88,
        range_quality=0.78,
        compression_quality=0.74,
        volume_confirmation=0.81,
        followthrough_room=0.76,
        extension_pct=0.24,
        retrace_risk=0.18,
        rejection_wick_ratio=0.12,
        regime="breakout",
        regime_favorability=0.80,
        pair_health=0.92,
        data_freshness=0.95,
        flow_coherence=0.79,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        atr=2.0,
        engine_a_overlap_ratio=0.28,
        marginal_portfolio_gain=9.2,
        covered_share_by_engine_a=0.22,
        keff_contribution=0.31,
        scoring_version="engine_c.v1",
    )
    defaults.update(overrides)
    return EngineCInput(**defaults)


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


def _runtime_input(**overrides) -> EngineCRuntimeInput:
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
    return EngineCRuntimeInput(**defaults)


def test_runtime_emits_signal_and_accepts_through_risk():
    runtime = EngineCRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(_runtime_input(), now=10.0)
    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.C
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.BREAKOUT
    assert result.signal_candidate.reason == "engine_c:medium:range_expansion"
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.take_profit is not None
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_c_accepted")
    assert accepted_log.breakout_type == "range_expansion"
    assert accepted_log.duplication_overlap_with_engine_a == 0.28


def test_runtime_hard_blocked_logs_reasons():
    runtime = EngineCRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(
        _runtime_input(blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True)),
        now=20.0,
    )
    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    joined = " ".join(
        reason
        for entry in result.log_entries
        if entry.event == "engine_c_hard_blocked"
        for reason in entry.reasons
    ).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable():
    runtime = EngineCRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    peer = ScoringCandidateInput(
        engine_id="engine_a",
        pair="ETHUSDT",
        raw_features={"structure": 0.98},
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
    assert result.status == EngineCRuntimeStatus.REJECTED_RANKING
    assert any(entry.event == "engine_c_rejected_by_ranking" for entry in result.log_entries)


def test_runtime_rejected_by_portfolio_is_auditable():
    runtime = EngineCRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=_risk_runtime())
    result = runtime.evaluate(_runtime_input(portfolio=_portfolio_state(remaining_gross_capacity=10.0)), now=40.0)
    assert result.status == EngineCRuntimeStatus.REJECTED_PORTFOLIO
    assert any(entry.event == "engine_c_rejected_by_portfolio" for entry in result.log_entries)


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
    runtime = EngineCRuntime(scoring_runtime=_scoring_runtime(), risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineCRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
