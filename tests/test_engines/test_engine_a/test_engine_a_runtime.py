"""Runtime tests for Build-6 Engine A across canonical signal, scoring and risk."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from engines.engine_a import (
    EngineAPreEntryValidationInput,
    EngineAPreEntryValidationOutcome,
    EngineARuntime,
    EngineARuntimeInput,
    EngineARuntimeStatus,
)
from engines.engine_a.engine_a_runner import EngineAInput
from interface_contracts import (
    ConditioningFamily,
    EngineId,
    ForecastHorizonClass,
    ForecastTargetClass,
    RegimeId,
    Side,
    SignalType,
)
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


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / ".codex_kill_switch_tests" / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides: object) -> EngineARuntime:
    return EngineARuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop(
            "circuit_breaker",
            EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, name)),
        ),
        **overrides,
    )


def _blocking_pre_entry_hook(_: EngineAPreEntryValidationInput) -> EngineAPreEntryValidationOutcome:
    return EngineAPreEntryValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_PRE_ENTRY_BLOCK",),
        detail="artifact veto on engine_a pre-entry confirmation",
    )


def test_runtime_emits_canonical_signal_and_accepts_through_risk(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_accepts")

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
    assert result.forecast_signal_candidate is None


def test_runtime_emits_additive_forecast_signal_when_strategy_id_is_provided(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_accepts_forecast")

    result = runtime.evaluate(
        _runtime_input(strategy_id=" strategy-a-trend "),
        now=10.0,
    )

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.strategy_id == "strategy-a-trend"
    assert result.forecast_signal_candidate.engine_id == EngineId.A
    assert result.forecast_signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate.forecast_target_class == (
        ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )
    assert result.forecast_signal_candidate.forecast_horizon_class == ForecastHorizonClass.MEDIUM
    assert result.forecast_signal_candidate.expected_cost == pytest.approx(0.001)
    assert result.forecast_signal_candidate.expected_gain == pytest.approx(0.005)
    assert result.forecast_signal_candidate.expected_break_even == pytest.approx(0.0015)
    assert result.forecast_signal_candidate.reason_codes == ("engine_a.conviction.high",)
    assert result.forecast_signal_candidate.conditioning_state[0].family == ConditioningFamily.ENGINE_INTERNAL
    assert result.forecast_signal_candidate.versions["scoring_version"] == "v1.0"


def test_runtime_input_rejects_blank_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id must not be blank"):
        _runtime_input(strategy_id="   ")


def test_runtime_can_derive_now_from_timestamp_ms_when_omitted(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_derive_now")

    result = runtime.evaluate(_runtime_input())

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(repo_tmp_path: Path) -> None:
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_a"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineARuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineARuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.scoring_audit is None
    assert result.risk_evaluation is None
    assert result.engine_output.decision == "no_trade"
    assert any(entry.event == "engine_a_circuit_breaker_blocked" for entry in result.log_entries)


def test_runtime_requires_explicit_circuit_breaker() -> None:
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineARuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
        )


def test_runtime_rejects_blank_scoring_version(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_pre_entry_validation_hook(repo_tmp_path: Path) -> None:
    runtime = _runtime(
        repo_tmp_path,
        "engine_a_hook_blocked",
        pre_entry_validation_hook=_blocking_pre_entry_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineARuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_a_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("ARTIFACT_PRE_ENTRY_BLOCK",)


def test_runtime_rejects_missing_scoring_audit_for_engine_candidate(repo_tmp_path: Path) -> None:
    class _MalformedScoringRuntime:
        def run_round(self, *args, **kwargs):
            return type("MalformedScoringRound", (), {"audits": ()})()

    runtime = _runtime(
        repo_tmp_path,
        "engine_a_missing_audit",
        scoring_runtime=_MalformedScoringRuntime(),
    )

    with pytest.raises(ValueError, match="missing scoring audit for engine_a/BTCUSDT"):
        runtime.evaluate(_runtime_input(), now=13.0)


def test_runtime_hard_blocked_logs_explicit_reasons(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_hard_blocked")
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


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_rejected_ranking")
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


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_rejected_portfolio")
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


def test_runtime_cannot_bypass_risk_runtime(repo_tmp_path: Path) -> None:
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_a_risk_runtime", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)

    assert result.status == EngineARuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    risk_logs = [entry for entry in result.log_entries if entry.event == "engine_a_risk_rejected"]
    assert len(risk_logs) == 1
    assert "gross" in " ".join(risk_logs[0].reasons).lower()
