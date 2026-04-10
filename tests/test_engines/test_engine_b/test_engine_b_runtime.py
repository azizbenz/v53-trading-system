"""Runtime tests for Build-7 Engine B across canonical signal, scoring and risk."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from engines.engine_b import (
    EngineBRuntime,
    EngineBRuntimeInput,
    EngineBRuntimeStatus,
    EngineBSweepValidationInput,
    EngineBSweepValidationOutcome,
)
from engines.engine_b.engine_b_runner import EngineBInput
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


def _good_engine_inputs(**overrides) -> EngineBInput:
    defaults = dict(
        pair="BTCUSDT",
        current_price=97.0,
        local_mean=100.0,
        local_std=1.5,
        structure_is_range=0.7,
        recent_expansion=0.1,
        regime="range",
        regime_trend_strength=0.1,
        volume_anomaly=0.1,
        structural_break=0.0,
        continuation_momentum=0.1,
        microstructure_breakout_confirmation=0.0,
        regime_favorability=0.7,
        pair_health=0.8,
        data_freshness=0.9,
        flow_coherence=0.8,
        expected_gain=0.003,
        expected_cost=0.001,
        candidate_size=100.0,
        holding_period=2.0,
        scoring_version="B_v1",
    )
    defaults.update(overrides)
    return EngineBInput(**defaults)


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
    registry.register(
        PenaltyDefinition(
            penalty_id="breakout_warning",
            name="Breakout warning",
            penalty_type=PenaltyType.SCORE,
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


def _runtime_input(**overrides) -> EngineBRuntimeInput:
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
    return EngineBRuntimeInput(**defaults)


def _breaker_state_dir(name: str) -> Path:
    state_dir = Path(".codex_kill_switch_tests") / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(name: str, **overrides) -> EngineBRuntime:
    return EngineBRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop("circuit_breaker", EmergencyCircuitBreaker(state_dir=_breaker_state_dir(name))),
        **overrides,
    )


def _blocking_sweep_hook(_: EngineBSweepValidationInput) -> EngineBSweepValidationOutcome:
    return EngineBSweepValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_SWEEP_BLOCK",),
        detail="artifact veto on sweep validation",
    )


def _boosting_sweep_hook(_: EngineBSweepValidationInput) -> EngineBSweepValidationOutcome:
    return EngineBSweepValidationOutcome(
        accepted=True,
        raw_score_multiplier_delta=0.10,
        raw_score_add=0.05,
        conviction_add=0.03,
        raw_score_cap=0.80,
        detail="artifact boost on confirmed sweep reversion",
    )


def test_runtime_emits_canonical_signal_and_accepts_through_risk():
    runtime = _runtime("engine_b_accepts")

    result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.B
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.RANGE_BOUND
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.take_profit == pytest.approx(100.0)
    assert result.signal_candidate.max_hold_ms == 2 * 3600 * 1000
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    events = {entry.event for entry in result.log_entries}
    assert "engine_b_scoring_completed" in events
    assert "engine_b_accepted" in events


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped():
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir("engine_b"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineBRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.scoring_audit is None
    assert result.risk_evaluation is None
    assert result.engine_output.decision == "no_trade"
    assert any(entry.event == "engine_b_circuit_breaker_blocked" for entry in result.log_entries)


def test_runtime_requires_explicit_circuit_breaker():
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineBRuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
        )


def test_runtime_rejects_blank_scoring_version():
    runtime = _runtime("engine_b_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_sweep_validation_hook():
    runtime = _runtime(
        "engine_b_hook_blocked",
        sweep_validation_hook=_blocking_sweep_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineBRuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_b_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("ARTIFACT_SWEEP_BLOCK",)


def test_runtime_applies_sweep_validation_score_adjustments_before_scoring():
    runtime = _runtime(
        "engine_b_hook_boosted",
        sweep_validation_hook=_boosting_sweep_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.75)

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.scoring_audit is not None
    base_raw_score = result.scoring_audit.raw_score_result.base_raw_score
    assert result.scoring_audit.raw_score_result.raw_score_multiplier == pytest.approx(1.10)
    assert result.scoring_audit.raw_score_result.raw_score_add == pytest.approx(0.08)
    assert result.scoring_audit.raw_score_result.raw_score_cap == pytest.approx(0.80)
    assert result.scoring_audit.raw_score_result.raw_score == pytest.approx(
        min(base_raw_score * 1.10 + 0.08, 0.80)
    )
    applied_logs = [entry for entry in result.log_entries if entry.event == "engine_b_sweep_validation_applied"]
    assert len(applied_logs) == 1
    assert "raw_score_multiplier=1.1000" in applied_logs[0].reasons
    assert "raw_score_add=0.0800" in applied_logs[0].reasons


def test_runtime_rejects_missing_scoring_audit_for_engine_candidate():
    class _MalformedScoringRuntime:
        def run_round(self, *args, **kwargs):
            return type("MalformedScoringRound", (), {"audits": ()})()

    runtime = _runtime(
        "engine_b_missing_audit",
        scoring_runtime=_MalformedScoringRuntime(),
    )

    with pytest.raises(ValueError, match="missing scoring audit for engine_b/BTCUSDT"):
        runtime.evaluate(_runtime_input(), now=13.0)


def test_runtime_hard_blocked_logs_explicit_reasons():
    runtime = _runtime("engine_b_hard_blocked")
    runtime_input = _runtime_input(
        blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
    )

    result = runtime.evaluate(runtime_input, now=20.0)

    assert result.status == EngineBRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.risk_evaluation is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_b_hard_blocked"]
    assert len(blocked_logs) == 1
    joined = " ".join(blocked_logs[0].reasons).lower()
    assert "stale" in joined
    assert "suspended" in joined


def test_runtime_rejected_by_ranking_is_auditable():
    runtime = _runtime("engine_b_rejected_ranking")
    peer = ScoringCandidateInput(
        engine_id="engine_a",
        pair="ETHUSDT",
        raw_features={"structure": 0.95},
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
            portfolio=_portfolio_state(
                remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0},
            ),
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.2, reason="context soft"),),
            size_penalties=(SizePenaltyItem(penalty_id="size_soft", multiplier=0.9, reason="size soft"),),
            engine_inputs=_good_engine_inputs(
                regime_trend_strength=0.5,
                volume_anomaly=0.4,
                structural_break=0.3,
                continuation_momentum=0.3,
            ),
        ),
        now=30.0,
    )

    assert result.status == EngineBRuntimeStatus.REJECTED_RANKING
    assert result.scoring_audit is not None
    assert result.scoring_audit.selection_entry is not None
    assert result.scoring_audit.selection_entry.outcome.value == "rejected_ranking"
    ranking_logs = [entry for entry in result.log_entries if entry.event == "engine_b_rejected_by_ranking"]
    assert len(ranking_logs) == 1
    assert "max selections" in ranking_logs[0].reasons[0]


def test_runtime_rejected_by_portfolio_is_auditable():
    runtime = _runtime("engine_b_rejected_portfolio")
    result = runtime.evaluate(
        _runtime_input(
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineBRuntimeStatus.REJECTED_PORTFOLIO
    portfolio_logs = [entry for entry in result.log_entries if entry.event == "engine_b_rejected_by_portfolio"]
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
    runtime = _runtime("engine_b_risk_runtime", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)

    assert result.status == EngineBRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    risk_logs = [entry for entry in result.log_entries if entry.event == "engine_b_risk_rejected"]
    assert len(risk_logs) == 1
    assert "gross" in " ".join(risk_logs[0].reasons).lower()
