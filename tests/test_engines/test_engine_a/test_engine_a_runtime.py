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
from engines.engine_a.engine_a_scoring_candidate_builder import _build_scoring_candidate
from engines.engine_a.engine_a_runner import EngineAInput
from engines.engine_a.engine_a_runner import run_engine_a
from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    EngineId,
    ForecastHorizonClass,
    ForecastTargetClass,
    Side,
    SignalType,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskLimits, RiskRuntime, RiskRuntimeAction
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringRuntime

from .test_engine_a import _good_inputs as _runner_good_inputs


def _good_engine_inputs(**overrides: object) -> EngineAInput:
    return _runner_good_inputs(**overrides)


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


def _portfolio_state(**overrides: object) -> PortfolioState:
    defaults = dict(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)


def _runtime_input(**overrides: object) -> EngineARuntimeInput:
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


def _base_risk_evaluation() -> RiskEvaluation:
    risk_runtime = _risk_runtime()
    risk_runtime.set_equity(current_equity=10_000.0, session_peak_equity=10_000.0)
    return risk_runtime.evaluate_candidate(
        RiskCandidate(
            pair="BTCUSDT",
            engine_id="engine_a",
            size=100.0,
            planned_loss=10.0,
            pair_beta=0.5,
        ),
        now=10.0,
    )


class _FixedRiskRuntime:
    def __init__(self, evaluation: RiskEvaluation) -> None:
        self._evaluation = evaluation

    def set_equity(self, *, current_equity: float, session_peak_equity: float) -> None:
        self._equity = (current_equity, session_peak_equity)

    def evaluate_candidate(self, candidate: object, *, now: float) -> RiskEvaluation:
        self._candidate = candidate
        self._now = now
        return self._evaluation


def _blocking_pre_entry_hook(
    _: EngineAPreEntryValidationInput,
) -> EngineAPreEntryValidationOutcome:
    return EngineAPreEntryValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_PRE_ENTRY_BLOCK",),
        detail="artifact veto on engine_a pre-entry validation",
    )


def _detail_only_pre_entry_hook(
    _: EngineAPreEntryValidationInput,
) -> EngineAPreEntryValidationOutcome:
    return EngineAPreEntryValidationOutcome(
        accepted=False,
        reason_codes=(),
        detail="compiled block detail",
    )


def test_runtime_emits_canonical_signal_and_accepts_through_risk(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_accepts")

    result = runtime.evaluate(_runtime_input(), now=10.0)

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.A
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.reason == "engine_a:high"
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    events = {entry.event for entry in result.log_entries}
    assert "engine_a_scoring_completed" in events
    assert "engine_a_accepted" in events
    assert result.forecast_signal_candidate is None


def test_scoring_candidate_carries_shared_physics_for_engine_a() -> None:
    runtime_input = _runtime_input(
        engine_inputs=_good_engine_inputs(
            execution_fragility=0.8,
            market_toxicity=0.7,
            spread_regime_penalty=0.6,
        ),
        supplementary_refs=("E:/shadow/ml_model_artifact.summary.json",),
    )
    engine_output = run_engine_a(runtime_input.engine_inputs)

    candidate = _build_scoring_candidate(runtime_input, engine_output)

    assert candidate.execution_fragility == pytest.approx(0.8)
    assert candidate.market_toxicity == pytest.approx(0.7)
    assert candidate.spread_regime_penalty == pytest.approx(0.6)
    assert candidate.supplementary_refs == ("E:/shadow/ml_model_artifact.summary.json",)
    assert "shared_scoring_physics_carried" in candidate.carriage_statuses
    assert "shared_scoring_physics_partial" in candidate.carriage_statuses
    assert candidate.carriage_reason_codes == ("SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",)


def test_runtime_carries_risk_micro_friction_for_engine_a(repo_tmp_path: Path) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(base)
    runtime = _runtime(repo_tmp_path, "engine_a_risk_carriage", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(
            engine_inputs=_good_engine_inputs(
                execution_fragility=0.8,
                market_toxicity=0.7,
                spread_regime_penalty=0.6,
            ),
            strategy_id="strategy-a-breakout",
        ),
        now=15.0,
    )

    assert result.risk_evaluation is not None
    candidate = risk_runtime._candidate
    assert isinstance(candidate, RiskCandidate)
    assert candidate.execution_fragility == pytest.approx(0.8)
    assert candidate.market_toxicity == pytest.approx(0.7)
    assert candidate.spread_regime_penalty == pytest.approx(0.6)
    assert candidate.carriage_statuses == ("risk_micro_friction_carried",)
    assert candidate.carriage_reason_codes == (
        "RISK_INFO_STRESS_FIELD_MISSING",
        "RISK_REGIME_STATE_MISSING",
    )


def test_runtime_emits_additive_forecast_signal_when_strategy_id_is_provided(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_a_accepts_forecast")

    result = runtime.evaluate(
        _runtime_input(strategy_id=" strategy-a-breakout "),
        now=10.0,
    )

    assert result.status == EngineARuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.strategy_id == "strategy-a-breakout"
    assert result.forecast_signal_candidate.engine_id == EngineId.A
    assert result.forecast_signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate.bet_structure == BetStructure.DIRECTIONAL_LONG
    assert result.forecast_signal_candidate.forecast_target_class == (
        ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )
    assert result.forecast_signal_candidate.forecast_horizon_class == ForecastHorizonClass.MEDIUM
    assert result.forecast_signal_candidate.expected_cost == pytest.approx(0.001)
    assert result.forecast_signal_candidate.expected_gain == pytest.approx(0.01)
    assert result.forecast_signal_candidate.expected_break_even > 0.0
    assert result.forecast_signal_candidate.invalidation_ref is not None
    assert "engine_a.conviction.high" in result.forecast_signal_candidate.reason_codes
    assert "engine_a.structure.favorable" in result.forecast_signal_candidate.reason_codes
    assert "engine_a.context.confirming" in result.forecast_signal_candidate.reason_codes
    assert "engine_a.cost.feasible" in result.forecast_signal_candidate.reason_codes
    assert "engine_a.forecast.volatility_proxy.realized_vol_current" in (
        result.forecast_signal_candidate.reason_codes
    )
    assert "engine_a.economics.break_even_cleared" in result.forecast_signal_candidate.reason_codes
    assert result.forecast_signal_candidate.conditioning_state[0].family == (
        ConditioningFamily.ENGINE_INTERNAL
    )


def test_runtime_input_rejects_blank_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id must not be blank"):
        _runtime_input(strategy_id="   ")


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(
    repo_tmp_path: Path,
) -> None:
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
    assert result.engine_output.decision.value == "no_trade"
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


def test_runtime_risk_reduced_status(repo_tmp_path: Path) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(
        base.model_copy(
            update={
                "action": RiskRuntimeAction.REDUCE_EXPOSURE,
                "accepted": False,
                "reasons": ("reduce exposure",),
            }
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_a_risk_reduced", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=70.0)

    assert result.status == EngineARuntimeStatus.RISK_REDUCED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
    assert any(entry.event == "engine_a_risk_reduced" for entry in result.log_entries)
    assert not any(entry.event == "engine_a_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_observe_only_status(repo_tmp_path: Path) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(
        base.model_copy(
            update={
                "action": RiskRuntimeAction.OBSERVE_ONLY,
                "accepted": False,
                "reasons": ("observe only",),
            }
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_a_risk_observe", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=80.0)

    assert result.status == EngineARuntimeStatus.RISK_OBSERVE_ONLY
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
    assert any(entry.event == "engine_a_risk_observe_only" for entry in result.log_entries)
    assert not any(entry.event == "engine_a_risk_rejected" for entry in result.log_entries)
