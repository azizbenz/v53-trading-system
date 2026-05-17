from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from engines.engine_c import (
    EngineCRuntime,
    EngineCRuntimeInput,
    EngineCRuntimeStatus,
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
)
from engines.engine_c.engine_c_runtime import _ENGINE_C_FEATURE_WEIGHTS
from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
from engines.engine_c.engine_c_runtime_support import build_scoring_candidate
from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    EngineId,
    ForecastHorizonClass,
    ForecastTargetClass,
    RefusalCategory,
    RegimeId,
    Side,
    SignalType,
)
from meta_minimal.refusal_journal import RefusalJournal, RefusalJournalSink
from protocols.engine_coordination_rules import EngineCoordinationInput, evaluate_engine_coordination
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskLimits, RiskRuntime, RiskRuntimeAction
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
        cumulative_ofi=24.0,
        queue_pressure=0.36,
        vpin=0.22,
        kyle_lambda=0.0012,
        continuation_ofi_min=0.0,
        continuation_queue_min=0.0,
        continuation_vpin_max=0.35,
        expected_gain=0.012,
        expected_cost=0.0025,
        candidate_size=1000.0,
        holding_period=3.0,
        entry_price=105.0,
        breakout_level=101.0,
        range_low=97.5,
        range_high=101.0,
        realized_vol_current=2.0 / 105.0,
        realized_vol_at_break=2.0 / 105.0,
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
        coordination_input=_coordination_input_c(),
    )
    defaults.update(overrides)
    return EngineCRuntimeInput(**defaults)


def _coordination_input_c(**overrides: object) -> EngineCoordinationInput:
    defaults = dict(
        evaluated_at_ns=1_700_000_000_000_000_000,
        engine_id=EngineId.C,
        pair="BTCUSDT",
        side=Side.BUY,
    )
    defaults.update(overrides)
    return EngineCoordinationInput(**defaults)


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / ".codex_kill_switch_tests" / name
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides: object) -> EngineCRuntime:
    return EngineCRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop(
            "circuit_breaker",
            EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, name)),
        ),
        coordination_evaluator=overrides.pop("coordination_evaluator", evaluate_engine_coordination),
        **overrides,
    )


def _blocking_void_hook(_: EngineCVoidValidationInput) -> EngineCVoidValidationOutcome:
    return EngineCVoidValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_VOID_BLOCK",),
        detail="artifact veto on engine_c void validation",
    )


def test_runtime_emits_signal_and_accepts_through_risk(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_c_accepts")
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
    assert result.engine_output.microstructure_gate_applied is True
    assert result.engine_output.cumulative_ofi == pytest.approx(24.0)
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_c_accepted")
    assert accepted_log.breakout_type == "range_expansion"
    assert accepted_log.duplication_overlap_with_engine_a == 0.28
    assert accepted_log.queue_pressure == pytest.approx(0.36)
    assert result.forecast_signal_candidate is None


def test_scoring_candidate_marks_shared_physics_mapping_partial_for_engine_c() -> None:
    runtime_input = _runtime_input(
        supplementary_refs=("E:/shadow/regime_detector_artifact.summary.json",),
    )
    engine_output = run_engine_c(runtime_input.engine_inputs)

    candidate = build_scoring_candidate(runtime_input, engine_output, _ENGINE_C_FEATURE_WEIGHTS)

    assert candidate.supplementary_refs == ("E:/shadow/regime_detector_artifact.summary.json",)
    assert candidate.carriage_statuses == ("local_math_only", "shared_scoring_physics_partial")
    assert candidate.carriage_reason_codes == (
        "SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",
        "HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE",
        "REGIME_SCORING_REINJECTION_PARTIAL",
    )
    assert candidate.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert candidate.engine_role == (
        "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context."
    )
    assert candidate.execution_fragility == pytest.approx(0.0)
    assert candidate.market_toxicity == pytest.approx(0.0)
    assert candidate.spread_regime_penalty == pytest.approx(0.0)
    assert candidate.participation_penalty == pytest.approx(0.0)
    assert candidate.cost_model_completeness_status == "NOT_PROVEN"
    assert candidate.fee_source_status == "NOT_PROVEN"
    assert candidate.impact_source_status == "NOT_PROVEN"
    assert candidate.fill_realism_status == "NOT_PROVEN"
    assert candidate.realized_slippage_status == "NOT_PROVEN"


def test_runtime_emits_additive_forecast_signal_when_strategy_id_is_provided(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_accepts_forecast")

    result = runtime.evaluate(
        _runtime_input(strategy_id=" strategy-c-breakout "),
        now=10.0,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.strategy_id == "strategy-c-breakout"
    assert result.forecast_signal_candidate.engine_id == EngineId.C
    assert result.forecast_signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate.bet_structure == BetStructure.BREAKOUT
    assert result.forecast_signal_candidate.forecast_target_class == (
        ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )
    assert result.forecast_signal_candidate.forecast_horizon_class == ForecastHorizonClass.MEDIUM
    assert result.forecast_signal_candidate.forecast_strength == pytest.approx(4.9875)
    assert 0.0 <= result.forecast_signal_candidate.forecast_strength <= 15.0
    assert result.forecast_signal_candidate.expected_cost == pytest.approx(0.0025)
    assert result.forecast_signal_candidate.expected_gain == pytest.approx(0.012)
    assert result.forecast_signal_candidate.expected_break_even == pytest.approx(0.003)
    assert result.forecast_signal_candidate.invalidation_ref is not None
    assert result.forecast_signal_candidate.invalidation_ref.startswith(
        "engine_c.invalidation.realized_vol_at_break.stop."
    )
    assert "engine_c.conviction.medium" in result.forecast_signal_candidate.reason_codes
    assert "engine_c.breakout.range_expansion" in result.forecast_signal_candidate.reason_codes
    assert "engine_c.microstructure.confirmed" in result.forecast_signal_candidate.reason_codes
    assert "engine_c.forecast.volatility_proxy.realized_vol_current" in result.forecast_signal_candidate.reason_codes
    assert "engine_c.economics.break_even_cleared" in result.forecast_signal_candidate.reason_codes
    assert result.forecast_signal_candidate.conditioning_state[0].family == ConditioningFamily.ENGINE_INTERNAL


def test_forecast_reason_codes_include_engine_and_penalties(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_forecast_penalties")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
        ),
        now=10.5,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_c.conviction.medium" in result.forecast_signal_candidate.reason_codes
    assert "engine_c.breakout.range_expansion" in result.forecast_signal_candidate.reason_codes
    assert "scoring.penalty.context_soft" in result.forecast_signal_candidate.reason_codes


def test_conditioning_state_contains_engine_internal_and_scoring_records(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_forecast_conditioning")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
        ),
        now=10.75,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    families = {record.family for record in result.forecast_signal_candidate.conditioning_state}
    codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert ConditioningFamily.ENGINE_INTERNAL in families
    assert ConditioningFamily.SCORING in families
    assert "engine_internal.engine_c.forecast.volatility_proxy.realized_vol_current" in codes
    assert "engine_internal.engine_c.forecast.normalized_strength" in codes
    assert "engine_internal.engine_c.break_even.cleared" in codes
    assert "engine_internal.engine_c.score.engine_local" in codes
    assert "engine_internal.engine_c.score.runtime_downstream" in codes
    assert "engine_internal.engine_c.runtime.raw_score.base_matches_runner" in codes
    assert "scoring.penalty.context_soft" in codes


def test_forecast_uses_realized_vol_at_break_fallback_when_current_vol_is_missing(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_forecast_realized_vol_at_break_fallback")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-c-breakout",
            engine_inputs=_good_engine_inputs(
                realized_vol_current=None,
                realized_vol_at_break=2.0 / 105.0,
            ),
        ),
        now=10.8,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_c.forecast.volatility_proxy.realized_vol_at_break_fallback" in (
        result.forecast_signal_candidate.reason_codes
    )
    assert "engine_internal.engine_c.forecast.volatility_proxy.realized_vol_at_break_fallback" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }


def test_runtime_scoring_base_raw_score_matches_runner_score(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_score_parity")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-c-breakout"),
        now=10.9,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.scoring_audit is not None
    assert result.scoring_audit.raw_score_result.base_raw_score == pytest.approx(result.engine_output.penalized_score)
    assert result.forecast_signal_candidate is not None
    parity_record = next(
        record
        for record in result.forecast_signal_candidate.conditioning_state
        if record.code == "engine_internal.engine_c.runtime.raw_score.base_matches_runner"
    )
    assert parity_record.value == pytest.approx(0.0, abs=1e-12)


def test_forecast_versions_non_regression(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_forecast_versions")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-c-breakout"),
        now=11.0,
    )

    assert result.status == EngineCRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.versions == {
        "scoring_version": "engine_c.v1",
        "runtime_adapter_version": "engine_c.forecast_adapter.v1",
    }


def test_runtime_input_rejects_blank_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id must not be blank"):
        _runtime_input(strategy_id="   ")


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(repo_tmp_path: Path):
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_c"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineCRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
        coordination_evaluator=evaluate_engine_coordination,
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
            coordination_evaluator=evaluate_engine_coordination,
        )


def test_runtime_rejects_blank_scoring_version(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_c_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_void_validation_hook(repo_tmp_path: Path):
    runtime = _runtime(
        repo_tmp_path,
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


def test_runtime_hook_blocked_without_structured_codes_uses_stable_runtime_code(repo_tmp_path: Path) -> None:
    def detail_only_hook(_: EngineCVoidValidationInput) -> EngineCVoidValidationOutcome:
        return EngineCVoidValidationOutcome(accepted=False, reason_codes=(), detail="compiled block detail")

    runtime = _runtime(
        repo_tmp_path,
        "engine_c_hook_blocked_stable",
        void_validation_hook=detail_only_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.6)

    assert result.status == EngineCRuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.forecast_signal_candidate is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_c_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("engine_c.runtime.hook_blocked",)


def test_runtime_coordination_block_is_hard_block_and_records_refusal(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_c_coordination")
    runtime = _runtime(
        repo_tmp_path,
        "engine_c_coordination_blocked",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            coordination_input=_coordination_input_c(a_holding_block_active=True),
        ),
        now=13.0,
    )

    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.blocked is True
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert "hard_block.ac_mutual_exclusion.a_holding" in result.refusal_record.reason_codes
    assert "engine_c.runtime.coordination_blocked" in result.refusal_record.reason_codes
    assert any(entry.event == "engine_c_coordination_blocked" for entry in result.log_entries)
    assert journal.read() == (result.refusal_record,)


def test_runtime_missing_coordination_input_is_hard_blocked(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_c_coordination_missing")
    runtime = _runtime(
        repo_tmp_path,
        "engine_c_coordination_missing",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(coordination_input=None),
        now=13.1,
    )

    assert result.status == EngineCRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.coordination_outcome is None
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes == (
        "engine_c.runtime.coordination_input_missing",
        "engine_c.runtime.coordination_required",
    )
    assert any(entry.event == "engine_c_coordination_missing" for entry in result.log_entries)
    assert journal.read() == (result.refusal_record,)


def test_runtime_coordination_input_engine_mismatch_is_rejected(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_coordination_mismatch")

    with pytest.raises(ValueError, match="coordination_input.engine_id must be engine_c"):
        runtime.evaluate(
            _runtime_input(
                coordination_input=_coordination_input_c(engine_id=EngineId.D),
            ),
            now=13.5,
        )


def test_runtime_hard_blocked_logs_reasons(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_c_hard_blocked")
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


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_c_rejected_ranking")
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


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path):
    runtime = _runtime(repo_tmp_path, "engine_c_rejected_portfolio")
    result = runtime.evaluate(_runtime_input(portfolio=_portfolio_state(remaining_gross_capacity=10.0)), now=40.0)
    assert result.status == EngineCRuntimeStatus.REJECTED_PORTFOLIO
    assert any(entry.event == "engine_c_rejected_by_portfolio" for entry in result.log_entries)


def test_runtime_cannot_bypass_risk_runtime(repo_tmp_path: Path):
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_c_risk_runtime", risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineCRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False


def _base_risk_evaluation() -> RiskEvaluation:
    risk_runtime = _risk_runtime()
    risk_runtime.set_equity(current_equity=10_000.0, session_peak_equity=10_000.0)
    return risk_runtime.evaluate_candidate(
        RiskCandidate(
            pair="BTCUSDT",
            engine_id="engine_c",
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


def test_runtime_surfaces_partial_by_design_and_not_proven_cost_statuses_to_risk(
    repo_tmp_path: Path,
) -> None:
    base = _base_risk_evaluation()
    risk_runtime = _FixedRiskRuntime(base)
    runtime = _runtime(repo_tmp_path, "engine_c_risk_candidate_statuses", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(strategy_id="strategy-c-breakout"), now=69.0)

    assert result.risk_evaluation is not None
    candidate = risk_runtime._candidate
    assert isinstance(candidate, RiskCandidate)
    assert candidate.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert candidate.engine_role == (
        "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context."
    )
    assert candidate.execution_fragility == pytest.approx(0.0)
    assert candidate.market_toxicity == pytest.approx(0.0)
    assert candidate.spread_regime_penalty == pytest.approx(0.0)
    assert candidate.execution_fragility_status == "NOT_PROVEN"
    assert candidate.market_toxicity_status == "NOT_PROVEN"
    assert candidate.spread_regime_penalty_status == "NOT_PROVEN"
    assert candidate.participation_penalty_status == "NOT_PROVEN"
    assert candidate.cost_model_completeness_status == "NOT_PROVEN"
    assert candidate.fee_source_status == "NOT_PROVEN"
    assert candidate.impact_source_status == "NOT_PROVEN"
    assert candidate.fill_realism_status == "NOT_PROVEN"
    assert candidate.realized_slippage_status == "NOT_PROVEN"


def test_runner_returns_no_trade_status(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_runner_no_trade")
    result = runtime.evaluate(_runtime_input(engine_inputs=_good_engine_inputs(cumulative_ofi=-5.0)), now=60.0)

    assert result.status == EngineCRuntimeStatus.NO_TRADE
    assert result.signal_candidate is None
    assert result.engine_output.no_trade_reasons[-1] == "microstructure_unconfirmed"
    assert _good_engine_inputs().pair == result.engine_output.pair
    assert any(entry.event == "engine_c_no_trade" for entry in result.log_entries)


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
    runtime = _runtime(repo_tmp_path, "engine_c_risk_reduced", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=70.0)

    assert result.status == EngineCRuntimeStatus.RISK_REDUCED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
    assert any(entry.event == "engine_c_risk_reduced" for entry in result.log_entries)
    assert not any(entry.event == "engine_c_risk_rejected" for entry in result.log_entries)


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
    runtime = _runtime(repo_tmp_path, "engine_c_risk_observe", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=80.0)

    assert result.status == EngineCRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
    assert any(entry.event == "engine_c_risk_observe_only" for entry in result.log_entries)
    assert not any(entry.event == "engine_c_risk_rejected" for entry in result.log_entries)


def test_invalid_now_rejected(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_c_invalid_now")

    with pytest.raises(ValueError, match="requires finite now"):
        runtime.evaluate(_runtime_input(), now=float("nan"))
