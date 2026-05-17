from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import shutil
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from engines.engine_d import (
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineDRuntime,
    EngineDRuntimeInput,
    EngineDRuntimeStatus,
)
from engines.engine_d.engine_d_runtime import _ENGINE_D_FEATURE_WEIGHTS
from engines.engine_d.engine_d_runner import EngineDInput, NoTradeReasonD, run_engine_d
from engines.engine_d.engine_d_runtime_support import build_scoring_candidate
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
from protocols.closed_episode_journal import EpisodeCloseReason, EpisodeRef
from protocols.engine_coordination_rules import EngineCoordinationInput, evaluate_engine_coordination
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker, KillSwitchReason
from risk_backbone.risk_runtime import RiskCandidate, RiskLimits, RiskRuntime, RiskRuntimeAction
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


def _good_engine_inputs(**overrides: float | str | bool | int | None) -> EngineDInput:
    defaults = dict(
        pair="BTCUSDT",
        origin_context_id="ctx-btc-01",
        origin_trade_id="trade-btc-01",
        link_type="prior_trade",
        first_episode_id="episode-btc-01",
        first_episode_engine_id="engine_a",
        first_episode_close_reason="time_stop",
        consecutive_stop_count=1,
        last_stop_at_ns=1_700_000_000_000_000_000,
        last_fresh_a_detection_at_ns=1_700_000_100_000_000_000,
        anti_revenge_state="reset_required",
        prior_trade_quality=0.85,
        reformation_quality=0.77,
        pullback_quality=0.73,
        continuation_room=0.70,
        concentration_headroom=0.78,
        marginal_edge=0.72,
        reentry_lateness=0.18,
        structure_reformed_detected=True,
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
        realized_vol_current=1.8 / 104.0,
        realized_vol_post_close=1.8 / 104.0,
        atr=1.8,
        duplication_overlap_with_engine_a=0.24,
        marginal_portfolio_gain=6.0,
        covered_share_by_engine_a=0.18,
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


def _portfolio_state(**overrides: float | dict[str, float]) -> PortfolioState:
    defaults = dict(
        remaining_gross_capacity=5000.0,
        remaining_loss_capacity=500.0,
        remaining_beta_capacity=5000.0,
        remaining_cluster_capacity={"btc_majors": 5000.0},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)


def _runtime_input(**overrides: object) -> EngineDRuntimeInput:
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


def _episode_ref() -> EpisodeRef:
    return EpisodeRef(
        episode_id=UUID("11111111-1111-1111-1111-111111111111"),
        engine_id_of_origin=EngineId.A,
        pair="BTCUSDT",
        side=Side.BUY,
        entry_level=Decimal("100.0"),
        exit_level=Decimal("104.0"),
        bet_structure=BetStructure.DIRECTIONAL_LONG,
        forecast_horizon_class=ForecastHorizonClass.SHORT,
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        closed_at_ns=1_700_000_000_000_000_000,
        close_reason=EpisodeCloseReason.TIME_STOP,
        realized_pnl_decimal=Decimal("4.0"),
    )


def _coordination_input_d(**overrides: object) -> EngineCoordinationInput:
    defaults = dict(
        evaluated_at_ns=1_700_000_200_000_000_000,
        engine_id=EngineId.D,
        pair="BTCUSDT",
        side=Side.BUY,
        first_episode_ref=_episode_ref(),
        reference_size=800.0,
    )
    defaults.update(overrides)
    return EngineCoordinationInput(**defaults)


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides: object) -> EngineDRuntime:
    return EngineDRuntime(
        scoring_runtime=overrides.pop("scoring_runtime", _scoring_runtime()),
        risk_runtime=overrides.pop("risk_runtime", _risk_runtime()),
        circuit_breaker=overrides.pop(
            "circuit_breaker",
            EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, name)),
        ),
        coordination_evaluator=overrides.pop("coordination_evaluator", evaluate_engine_coordination),
        **overrides,
    )


def _forced_risk_evaluation(action: RiskRuntimeAction) -> object:
    risk_runtime = _risk_runtime()
    risk_runtime.set_equity(current_equity=10_000.0, session_peak_equity=10_000.0)
    base = risk_runtime.evaluate_candidate(
        RiskCandidate(
            pair="BTCUSDT",
            engine_id="engine_d",
            size=100.0,
            planned_loss=10.0,
            pair_beta=0.3,
        ),
        now=10.0,
    )
    return base.model_copy(
        update={
            "action": action,
            "accepted": False,
            "reasons": (f"forced_{action.value}",),
        }
    )


def _accepted_risk_evaluation() -> object:
    risk_runtime = _risk_runtime()
    risk_runtime.set_equity(current_equity=10_000.0, session_peak_equity=10_000.0)
    return risk_runtime.evaluate_candidate(
        RiskCandidate(
            pair="BTCUSDT",
            engine_id="engine_d",
            size=100.0,
            planned_loss=10.0,
            pair_beta=0.3,
        ),
        now=10.0,
    )


def _blocking_reentry_hook(_: EngineDReentryValidationInput) -> EngineDReentryValidationOutcome:
    return EngineDReentryValidationOutcome(
        accepted=False,
        reason_codes=("ARTIFACT_REENTRY_BLOCK",),
        detail="artifact veto on engine_d re-entry validation",
        episode_reference_id="episode-btc-01",
        anti_revenge_state="cooldown_active",
        observability_tags=("backtest.anti_revenge_state",),
    )


class _CapturingRiskRuntime:
    def __init__(self, evaluation: object) -> None:
        self._evaluation = evaluation
        self.candidate: RiskCandidate | None = None

    def set_equity(self, *, current_equity: float, session_peak_equity: float) -> None:
        self._equity = (current_equity, session_peak_equity)

    def evaluate_candidate(self, candidate: RiskCandidate, *, now: float) -> object:
        self.candidate = candidate
        self._now = now
        return self._evaluation


def test_runtime_emits_signal_and_accepts_through_risk(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_accepts")
    result = runtime.evaluate(_runtime_input(), now=10.0)
    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.signal_candidate.engine_id == EngineId.D
    assert result.signal_candidate.signal_type == SignalType.ENTRY
    assert result.signal_candidate.side == Side.BUY
    assert result.signal_candidate.regime == RegimeId.TRENDING_UP
    assert result.signal_candidate.reason == "engine_d:high:prior_trade:trade-btc-01"
    assert result.signal_candidate.stop_loss is not None
    assert result.signal_candidate.take_profit is not None
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is True
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_d_accepted")
    assert accepted_log.origin_context_id == "ctx-btc-01"
    assert accepted_log.duplication_overlap_with_engine_a == 0.24
    assert result.forecast_signal_candidate is None


def test_scoring_candidate_marks_shared_physics_mapping_partial_for_engine_d() -> None:
    runtime_input = _runtime_input(
        supplementary_refs=("E:/shadow/regime_detector_artifact.summary.json",),
    )
    engine_output = run_engine_d(runtime_input.engine_inputs)

    candidate = build_scoring_candidate(runtime_input, engine_output, _ENGINE_D_FEATURE_WEIGHTS)

    assert candidate.supplementary_refs == ("E:/shadow/regime_detector_artifact.summary.json",)
    assert candidate.carriage_statuses == ("local_math_only", "shared_scoring_physics_partial")
    assert candidate.carriage_reason_codes == (
        "SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",
        "HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE",
        "REGIME_SCORING_REINJECTION_PARTIAL",
    )
    assert candidate.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert candidate.engine_role == (
        "Re-entry / second-chance engine with first-episode linkage, anti-revenge, "
        "reformation, and realized-vol context."
    )
    assert candidate.execution_fragility == pytest.approx(0.0)
    assert candidate.market_toxicity == pytest.approx(0.0)
    assert candidate.spread_regime_penalty == pytest.approx(0.0)
    assert candidate.participation_penalty == pytest.approx(0.0)
    assert candidate.risk_penalty == pytest.approx(0.0)
    assert candidate.cost_model_completeness_status == "NOT_PROVEN"
    assert candidate.fee_source_status == "NOT_PROVEN"
    assert candidate.impact_source_status == "NOT_PROVEN"
    assert candidate.fill_realism_status == "NOT_PROVEN"
    assert candidate.realized_slippage_status == "NOT_PROVEN"


def test_runtime_emits_additive_forecast_signal_when_strategy_id_is_provided(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_accepts_forecast")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id=" strategy-d-reentry ",
            coordination_input=_coordination_input_d(),
        ),
        now=10.0,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.strategy_id == "strategy-d-reentry"
    assert result.forecast_signal_candidate.engine_id == EngineId.D
    assert result.forecast_signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate.bet_structure == BetStructure.DIRECTIONAL_LONG
    assert result.forecast_signal_candidate.forecast_target_class == (
        ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )
    assert result.forecast_signal_candidate.forecast_horizon_class == ForecastHorizonClass.MEDIUM
    assert result.forecast_signal_candidate.forecast_strength == pytest.approx(4.044444444444444)
    assert 0.0 <= result.forecast_signal_candidate.forecast_strength <= 10.0
    assert result.forecast_signal_candidate.expected_cost == pytest.approx(0.0020)
    assert result.forecast_signal_candidate.expected_gain == pytest.approx(0.009)
    assert result.forecast_signal_candidate.expected_break_even == pytest.approx(0.0025)
    assert result.forecast_signal_candidate.invalidation_ref is not None
    assert "engine_d.conviction.high" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.link_type.prior_trade" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.invalidation.present" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.forecast.volatility_proxy.realized_vol_post_close" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.economics.break_even_cleared" in result.forecast_signal_candidate.reason_codes
    assert result.forecast_signal_candidate.conditioning_state[0].family == ConditioningFamily.ENGINE_INTERNAL


def test_forecast_reason_codes_include_engine_and_penalties(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_forecast_penalties")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
        ),
        now=10.5,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_d.conviction.high" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.link_type.prior_trade" in result.forecast_signal_candidate.reason_codes
    assert "scoring.penalty.context_soft" in result.forecast_signal_candidate.reason_codes


def test_conditioning_state_contains_engine_internal_and_scoring_records(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_forecast_conditioning")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.25, reason="context soft"),),
        ),
        now=10.75,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    families = {record.family for record in result.forecast_signal_candidate.conditioning_state}
    codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert ConditioningFamily.ENGINE_INTERNAL in families
    assert ConditioningFamily.SCORING in families
    assert "scoring.penalty.context_soft" in codes
    assert "engine_internal.engine_d.invalidation.present" in codes
    assert "engine_internal.engine_d.marginal_value.present" in codes
    assert "engine_internal.engine_d.cost.present" in codes
    assert "engine_internal.engine_d.forecast.volatility_proxy.realized_vol_post_close" in codes
    assert "engine_internal.engine_d.forecast.normalized_strength" in codes
    assert "engine_internal.engine_d.break_even.cleared" in codes


def test_runtime_uses_delta_safe_fallback_and_clips_forecast_strength(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_forecast_delta_safe_fallback")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            engine_inputs=_good_engine_inputs(
                realized_vol_current=None,
                realized_vol_post_close=None,
                atr=0.0,
            ),
        ),
        now=10.9,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.forecast_strength == pytest.approx(10.0)
    assert "engine_d.forecast.volatility_proxy.delta_safe_fallback" in result.forecast_signal_candidate.reason_codes
    assert "engine_d.forecast.normalized_forecast_clipped" in result.forecast_signal_candidate.reason_codes
    assert "engine_internal.engine_d.forecast.volatility_proxy.delta_safe_fallback" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }


def test_runtime_uses_current_realized_vol_fallback_when_post_close_vol_is_missing(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_forecast_realized_vol_current_fallback")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            engine_inputs=_good_engine_inputs(
                realized_vol_post_close=None,
                realized_vol_current=1.8 / 104.0,
            ),
        ),
        now=10.95,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_d.forecast.volatility_proxy.realized_vol_current_fallback" in (
        result.forecast_signal_candidate.reason_codes
    )
    assert "engine_internal.engine_d.forecast.volatility_proxy.realized_vol_current_fallback" in {
        record.code for record in result.forecast_signal_candidate.conditioning_state
    }


def test_forecast_versions_non_regression(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_forecast_versions")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-d-reentry"),
        now=11.0,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.versions == {
        "scoring_version": "engine_d.v1",
        "runtime_adapter_version": "engine_d.forecast_adapter.v1",
    }


def test_runtime_input_rejects_blank_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id must not be blank"):
        _runtime_input(strategy_id="   ")


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(repo_tmp_path: Path) -> None:
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_d"))
    breaker.trip(KillSwitchReason.OPERATOR_MANUAL, "manual stop")
    runtime = EngineDRuntime(
        scoring_runtime=_scoring_runtime(),
        risk_runtime=_risk_runtime(),
        circuit_breaker=breaker,
        coordination_evaluator=evaluate_engine_coordination,
    )

    result = runtime.evaluate(_runtime_input(), now=11.0)

    assert result.status == EngineDRuntimeStatus.CIRCUIT_BREAKER_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.scoring_audit is None
    assert result.risk_evaluation is None
    assert result.engine_output.decision == "no_trade"
    assert any(entry.event == "engine_d_circuit_breaker_blocked" for entry in result.log_entries)


def test_runner_returns_no_trade_status(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_runner_no_trade")
    result = runtime.evaluate(
        _runtime_input(engine_inputs=_good_engine_inputs(candidate_size=0.0)),
        now=11.5,
    )

    assert result.status == EngineDRuntimeStatus.NO_TRADE
    assert result.signal_candidate is None
    assert result.engine_output.decision == "no_trade"
    assert result.engine_output.no_trade_reasons == (NoTradeReasonD.INVALID_CANDIDATE_SIZE,)
    assert result.log_entries[-1].event == "engine_d_no_trade"


def test_runtime_requires_explicit_circuit_breaker() -> None:
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineDRuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
            coordination_evaluator=evaluate_engine_coordination,
        )


def test_runtime_rejects_blank_scoring_version(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_reentry_validation_hook(repo_tmp_path: Path) -> None:
    runtime = _runtime(
        repo_tmp_path,
        "engine_d_hook_blocked",
        reentry_validation_hook=_blocking_reentry_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.5)

    assert result.status == EngineDRuntimeStatus.HOOK_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_d_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("ARTIFACT_REENTRY_BLOCK",)
    assert result.hook_outcome is not None
    assert result.hook_outcome.episode_reference_id == "episode-btc-01"
    assert result.hook_outcome.anti_revenge_state == "cooldown_active"


def test_runtime_hook_blocked_falls_back_to_stable_reason_code(repo_tmp_path: Path) -> None:
    def _blank_hook(_: EngineDReentryValidationInput) -> EngineDReentryValidationOutcome:
        return EngineDReentryValidationOutcome(accepted=False, reason_codes=(), detail="")

    runtime = _runtime(
        repo_tmp_path,
        "engine_d_hook_blocked_stable_code",
        reentry_validation_hook=_blank_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=12.6)

    assert result.status == EngineDRuntimeStatus.HOOK_BLOCKED
    blocked_logs = [entry for entry in result.log_entries if entry.event == "engine_d_hook_blocked"]
    assert len(blocked_logs) == 1
    assert blocked_logs[0].reasons == ("engine_d.runtime.hook_blocked",)


def test_runtime_coordination_block_is_hard_block_and_records_refusal(repo_tmp_path: Path) -> None:
    journal = RefusalJournal(flush_dir=repo_tmp_path / "refusals_d_coordination")
    runtime = _runtime(
        repo_tmp_path,
        "engine_d_coordination_blocked",
        refusal_sink=RefusalJournalSink(journal),
    )

    result = runtime.evaluate(
        _runtime_input(
            coordination_input=_coordination_input_d(first_episode_ref=None),
        ),
        now=12.75,
    )

    assert result.status == EngineDRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is None
    assert result.scoring_round is None
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.blocked is True
    assert result.refusal_record is not None
    assert result.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert result.refusal_record.reason_codes == ("hard_block.d_no_historical_linkage",)
    assert any(entry.event == "engine_d_coordination_blocked" for entry in result.log_entries)
    assert journal.read() == (result.refusal_record,)


def test_runtime_coordination_size_reduction_reaches_risk_candidate(repo_tmp_path: Path) -> None:
    risk_runtime = _CapturingRiskRuntime(_accepted_risk_evaluation())
    runtime = _runtime(
        repo_tmp_path,
        "engine_d_coordination_size_reduced",
        risk_runtime=risk_runtime,
    )

    result = runtime.evaluate(
        _runtime_input(
            coordination_input=_coordination_input_d(),
        ),
        now=12.9,
    )

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert result.coordination_outcome is not None
    assert result.coordination_outcome.size_multiplier == pytest.approx(0.5)
    assert result.coordination_outcome.resolved_size == pytest.approx(400.0)
    assert risk_runtime.candidate is not None
    assert risk_runtime.candidate.size == pytest.approx(400.0)
    assert risk_runtime.candidate.planned_loss == pytest.approx(20.0)
    assert risk_runtime.candidate.shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert risk_runtime.candidate.engine_role == (
        "Re-entry / second-chance engine with first-episode linkage, anti-revenge, "
        "reformation, and realized-vol context."
    )
    assert risk_runtime.candidate.execution_fragility == pytest.approx(0.0)
    assert risk_runtime.candidate.market_toxicity == pytest.approx(0.0)
    assert risk_runtime.candidate.spread_regime_penalty == pytest.approx(0.0)
    assert risk_runtime.candidate.execution_fragility_status == "NOT_PROVEN"
    assert risk_runtime.candidate.market_toxicity_status == "NOT_PROVEN"
    assert risk_runtime.candidate.spread_regime_penalty_status == "NOT_PROVEN"
    assert risk_runtime.candidate.participation_penalty_status == "NOT_PROVEN"
    assert risk_runtime.candidate.cost_model_completeness_status == "NOT_PROVEN"
    assert risk_runtime.candidate.fee_source_status == "NOT_PROVEN"
    assert risk_runtime.candidate.impact_source_status == "NOT_PROVEN"
    assert risk_runtime.candidate.fill_realism_status == "NOT_PROVEN"
    assert risk_runtime.candidate.realized_slippage_status == "NOT_PROVEN"
    assert any(entry.event == "engine_d_coordination_size_reduced" for entry in result.log_entries)


def test_runtime_surfaces_anti_revenge_observability_for_backtest(repo_tmp_path: Path) -> None:
    captured: dict[str, EngineDReentryValidationInput] = {}

    def _capturing_hook(hook_input: EngineDReentryValidationInput) -> EngineDReentryValidationOutcome:
        captured["hook_input"] = hook_input
        return EngineDReentryValidationOutcome(
            accepted=True,
            episode_reference_id=hook_input.first_episode_id,
            anti_revenge_state=hook_input.anti_revenge_state,
            observability_tags=("backtest.anti_revenge_state", "backtest.episode_ref"),
        )

    runtime = _runtime(
        repo_tmp_path,
        "engine_d_backtest_observability",
        reentry_validation_hook=_capturing_hook,
    )

    result = runtime.evaluate(_runtime_input(), now=13.0)

    assert result.status == EngineDRuntimeStatus.ACCEPTED
    assert captured["hook_input"].first_episode_id == "episode-btc-01"
    assert captured["hook_input"].first_episode_engine_id == "engine_a"
    assert captured["hook_input"].first_episode_close_reason == "time_stop"
    assert captured["hook_input"].consecutive_stop_count == 1
    assert captured["hook_input"].anti_revenge_state == "reset_required"
    assert result.hook_outcome is not None
    assert result.hook_outcome.episode_reference_id == "episode-btc-01"
    assert result.hook_outcome.anti_revenge_state == "reset_required"
    accepted_log = next(entry for entry in result.log_entries if entry.event == "engine_d_accepted")
    assert accepted_log.first_episode_id == "episode-btc-01"
    assert accepted_log.anti_revenge_state == "reset_required"


def test_runtime_hard_blocked_logs_reasons(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_hard_blocked")
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


def test_runtime_hard_blocked_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_hard_blocked_forecast")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
        ),
        now=20.0,
    )

    assert result.status == EngineDRuntimeStatus.HARD_BLOCKED
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.hard_blocked" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "hard_block.engine_d.runtime.hard_blocked" in conditioning_codes
    assert result.refusal_record is not None


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_ranking")
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
    assert result.signal_candidate is not None
    assert any(entry.event == "engine_d_rejected_by_ranking" for entry in result.log_entries)


def test_runtime_rejected_by_ranking_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_ranking_forecast")
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
            strategy_id="strategy-d-reentry",
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0}),
        ),
        now=30.0,
    )

    assert result.status == EngineDRuntimeStatus.REJECTED_RANKING
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.rejected_ranking" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "scoring.engine_d.runtime.rejected_ranking" in conditioning_codes
    assert result.refusal_record is not None


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_portfolio")
    result = runtime.evaluate(_runtime_input(portfolio=_portfolio_state(remaining_gross_capacity=10.0)), now=40.0)
    assert result.status == EngineDRuntimeStatus.REJECTED_PORTFOLIO
    assert result.signal_candidate is not None
    assert any(entry.event == "engine_d_rejected_by_portfolio" for entry in result.log_entries)


def test_runtime_rejected_by_portfolio_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_rejected_portfolio_forecast")
    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineDRuntimeStatus.REJECTED_PORTFOLIO
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.rejected_portfolio" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "portfolio.engine_d.runtime.rejected_portfolio" in conditioning_codes
    assert result.refusal_record is not None


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
    runtime = _runtime(repo_tmp_path, "engine_d_risk_runtime", risk_runtime=risk_runtime)
    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)
    assert result.status == EngineDRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    assert any(entry.event == "engine_d_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_rejected_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    risk_runtime = RiskRuntime(
        RiskLimits(
            gross_cap=500.0,
            position_cap=2000.0,
            loss_cap=500.0,
            beta_cap=5000.0,
            cluster_cap=5000.0,
        )
    )
    runtime = _runtime(repo_tmp_path, "engine_d_risk_runtime_forecast", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-d-reentry", projected_size=1000.0),
        now=50.0,
    )

    assert result.status == EngineDRuntimeStatus.RISK_REJECTED
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.risk_rejected" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "hard_block.engine_d.runtime.risk_rejected" in conditioning_codes
    assert result.refusal_record is not None


def test_runtime_risk_reduced_status(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_risk_reduced")
    forced = _forced_risk_evaluation(RiskRuntimeAction.REDUCE_EXPOSURE)

    with patch.object(runtime._risk_runtime, "evaluate_candidate", return_value=forced):
        result = runtime.evaluate(_runtime_input(), now=55.0)

    assert result.status == EngineDRuntimeStatus.RISK_REDUCED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
    assert result.log_entries[-1].event == "engine_d_risk_reduced"
    assert result.refusal_record is None


def test_runtime_risk_reduced_is_governed_without_refusal_record(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_risk_reduced_forecast")
    forced = _forced_risk_evaluation(RiskRuntimeAction.REDUCE_EXPOSURE)

    with patch.object(runtime._risk_runtime, "evaluate_candidate", return_value=forced):
        result = runtime.evaluate(_runtime_input(strategy_id="strategy-d-reentry"), now=55.0)

    assert result.status == EngineDRuntimeStatus.RISK_REDUCED
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.risk_reduced" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "engine_internal.engine_d.runtime.risk_reduced" in conditioning_codes
    assert result.refusal_record is None


def test_runtime_risk_observe_only_status(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_risk_observe")
    forced = _forced_risk_evaluation(RiskRuntimeAction.OBSERVE_ONLY)

    with patch.object(runtime._risk_runtime, "evaluate_candidate", return_value=forced):
        result = runtime.evaluate(_runtime_input(), now=56.0)

    assert result.status == EngineDRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
    assert result.log_entries[-1].event == "engine_d_risk_observe_only"
    assert result.refusal_record is None


def test_runtime_risk_observe_only_is_governed_without_refusal_record(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_risk_observe_forecast")
    forced = _forced_risk_evaluation(RiskRuntimeAction.OBSERVE_ONLY)

    with patch.object(runtime._risk_runtime, "evaluate_candidate", return_value=forced):
        result = runtime.evaluate(_runtime_input(strategy_id="strategy-d-reentry"), now=56.0)

    assert result.status == EngineDRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.forecast_signal_candidate is not None
    assert "engine_d.runtime.risk_observe_only" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "engine_internal.engine_d.runtime.risk_observe_only" in conditioning_codes
    assert result.refusal_record is None


def test_runtime_never_creates_fake_flat_side_or_fake_blocked_trade(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_no_fake_flat")
    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-d-reentry",
            blocker_conditions=BlockerCondition(is_stale_hard=True),
        ),
        now=21.0,
    )

    assert result.status == EngineDRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate is not None


def test_invalid_now_rejected(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_d_invalid_now")

    with pytest.raises(ValueError, match="requires finite now"):
        runtime.evaluate(_runtime_input(), now=float("nan"))
