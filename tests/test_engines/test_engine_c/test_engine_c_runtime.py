from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from engines.engine_c import (
    EngineCRuntime,
    EngineCRuntimeInput,
    EngineCRuntimeStatus,
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
)
from engines.engine_c.engine_c_runner import EngineCInput
from interface_contracts import EngineId, RegimeId, Side, SignalType
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
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


def _breaker_state_dir(name: str) -> Path:
    state_dir = Path(".codex_kill_switch_tests") / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(name: str, **overrides) -> EngineCRuntime:
    return EngineCRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop("circuit_breaker", EmergencyCircuitBreaker(state_dir=_breaker_state_dir(name))),
        **overrides,
    )


def _blocking_void_hook(_: EngineCVoidValidationInput) -> EngineCVoidValidationOutcome:
    return EngineCVoidValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_VOID_BLOCK",),
        detail="artifact veto on engine_c void validation",
    )


def test_runtime_emits_signal_and_accepts_through_risk():
    runtime = _runtime("engine_c_accepts")
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


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped():
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir("engine_c"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineCRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineCRuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.scoring_audit is None
    assert result.risk_evaluation is None
    assert result.engine_output.decision == "no_trade"
    assert any(entry.event == "engine_c_circuit_breaker_blocked" for entry in result.log_entries)


def test_runtime_requires_explicit_circuit_breaker():
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineCRuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
        )


def test_runtime_rejects_blank_scoring_version():
    runtime = _runtime("engine_c_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_void_validation_hook():
    runtime = _runtime(
        "engine_c_hook_blocked",
        void_validation_hook=_blocking_void_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineCRuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_c_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("ARTIFACT_VOID_BLOCK",)


def test_runtime_hard_blocked_logs_reasons():
    runtime = _runtime("engine_c_hard_blocked")
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
    runtime = _runtime("engine_c_rejected_ranking")
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
    runtime = _runtime("engine_c_rejected_portfolio")
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
    runtime = _runtime("engine_c_risk_runtime", risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineCRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
