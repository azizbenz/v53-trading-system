"""Runtime tests for Build-7 Engine B across canonical signal, scoring and risk."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from engines.engine_b import (
    EngineBRuntime,
    EngineBRuntimeInput,
    EngineBRuntimeStatus,
    EngineBSweepValidationInput,
    EngineBSweepValidationOutcome,
)
from engines.engine_b.conviction_builder_b import ENGINE_B_CONVICTION_FEATURE_WEIGHTS
from engines.engine_b.engine_b_runner import EngineBInput
from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    EngineId,
    ForecastHorizonClass,
    ForecastTargetClass,
    RegimeId,
    Side,
    SignalType,
)
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
from scoring_backbone import normalize_forecast
from engines.engine_b.engine_b_runtime_forecast_support import (
    _ENGINE_B_FORECAST_NORMALIZER_CONFIG,
)


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


def _breaker_state_dir(repo_tmp_path: Path, name: str) -> Path:
    state_dir = repo_tmp_path / ".codex_kill_switch_tests" / name
    shutil.rmtree(state_dir, ignore_errors=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _runtime(repo_tmp_path: Path, name: str, **overrides: object) -> EngineBRuntime:
    return EngineBRuntime(
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
            engine_id="engine_b",
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


def test_runtime_emits_canonical_signal_and_accepts_through_risk(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_accepts")

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
    assert result.forecast_signal_candidate is None


def test_runtime_emits_additive_forecast_signal_when_strategy_id_is_provided(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_accepts_forecast")

    result = runtime.evaluate(
        _runtime_input(strategy_id=" strategy-b-reversion "),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.signal_candidate is not None
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.strategy_id == "strategy-b-reversion"
    assert result.forecast_signal_candidate.engine_id == EngineId.B
    assert result.forecast_signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate.bet_structure == BetStructure.MEAN_REVERT
    assert result.forecast_signal_candidate.forecast_target_class == (
        ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )
    assert result.forecast_signal_candidate.forecast_horizon_class == ForecastHorizonClass.MEDIUM
    assert result.forecast_signal_candidate.expected_cost == pytest.approx(0.001)
    assert result.forecast_signal_candidate.expected_gain == pytest.approx(0.003)
    assert result.forecast_signal_candidate.expected_break_even == pytest.approx(0.0018)
    assert "engine_b.conviction.medium" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.excess.exploitable" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.breakout.clear" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.cost.feasible" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.economics.break_even_cleared" in result.forecast_signal_candidate.reason_codes
    assert result.forecast_signal_candidate.conditioning_state[0].family == ConditioningFamily.ENGINE_INTERNAL


def test_runtime_forecast_reason_codes_include_toxic_flow_fade(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_accepts_forecast_toxic_flow")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            engine_inputs=_good_engine_inputs(
                vpin_current=0.40,
            ),
        ),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_b.conviction.medium" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.excess.exploitable" in result.forecast_signal_candidate.reason_codes
    assert "b.toxic_flow_fade" in result.forecast_signal_candidate.reason_codes


def test_runtime_forecast_reason_codes_include_toxic_flow_fade_suppressed_by_correlation(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_accepts_forecast_toxic_flow_suppressed")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            engine_inputs=_good_engine_inputs(
                vpin_current=0.40,
                toxic_flow_correlation=0.95,
            ),
        ),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "b.toxic_flow_fade" not in result.forecast_signal_candidate.reason_codes
    assert "b.toxic_flow_fade_suppressed.correlation" in result.forecast_signal_candidate.reason_codes


def test_forecast_signal_candidate_contains_expected_break_even(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_forecast_break_even")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion"),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.expected_break_even == pytest.approx(0.0018)


def test_forecast_signal_candidate_strength_cap_matches_engine_b_normalizer_config() -> None:
    result = normalize_forecast(
        expected_return=0.002,
        volatility_scale=0.0001,
        forecast_scalar=_ENGINE_B_FORECAST_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_ENGINE_B_FORECAST_NORMALIZER_CONFIG,
    )

    assert result.normalized_forecast == pytest.approx(15.0)


def test_forecast_reason_codes_include_engine_and_penalties(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_forecast_penalties")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.2, reason="context soft"),),
        ),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert "engine_b.conviction.medium" in result.forecast_signal_candidate.reason_codes
    assert "engine_b.excess.exploitable" in result.forecast_signal_candidate.reason_codes
    assert "scoring.penalty.context_soft" in result.forecast_signal_candidate.reason_codes


def test_conditioning_state_contains_engine_internal_and_scoring_records(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_forecast_conditioning")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            score_penalties=(ScorePenaltyItem(penalty_id="context_soft", value=0.2, reason="context soft"),),
        ),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    families = {record.family for record in result.forecast_signal_candidate.conditioning_state}
    codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert ConditioningFamily.ENGINE_INTERNAL in families
    assert ConditioningFamily.SCORING in families
    assert "scoring.penalty.context_soft" in codes
    assert "engine_internal.engine_b.excess.exploitable" in codes
    assert "engine_internal.engine_b.break_even.cleared" in codes
    assert "engine_internal.engine_b.runtime.raw_score.base_matches_runner" in codes
    assert "engine_internal.engine_b.invalidation.present" in codes


def test_runtime_raw_score_delta_vs_runner_is_explicitly_governed(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_raw_score_parity")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion"),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.scoring_audit is not None
    assert result.scoring_audit.raw_score_result.base_raw_score == pytest.approx(result.engine_output.raw_score)
    legacy_raw = sum(
        ENGINE_B_CONVICTION_FEATURE_WEIGHTS[name] * result.engine_output.block_scores.get(name, 0.0)
        for name in ENGINE_B_CONVICTION_FEATURE_WEIGHTS
    )
    assert legacy_raw != pytest.approx(result.engine_output.raw_score)
    assert result.forecast_signal_candidate is not None
    parity_record = next(
        record
        for record in result.forecast_signal_candidate.conditioning_state
        if record.code == "engine_internal.engine_b.runtime.raw_score.base_matches_runner"
    )
    assert parity_record.value == pytest.approx(0.0, abs=1e-12)


def test_forecast_versions_non_regression(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_forecast_versions")

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion"),
        now=10.0,
    )

    assert result.status == EngineBRuntimeStatus.ACCEPTED
    assert result.forecast_signal_candidate is not None
    assert result.forecast_signal_candidate.versions == {
        "scoring_version": "B_v1",
        "calibration_profile_id": "engine_b_conviction.to_calibrate.v1",
        "calibration_status": "TO_CALIBRATE",
        "physics_calibration_profile_id": "market_physics.to_calibrate.v1",
        "physics_calibration_status": "TO_CALIBRATE",
    }


def test_runtime_input_rejects_blank_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id must not be blank"):
        _runtime_input(strategy_id="   ")


def test_runtime_input_rejects_zero_projected_size() -> None:
    with pytest.raises(ValidationError, match="projected_size"):
        _runtime_input(projected_size=0.0)


def test_runtime_input_rejects_zero_current_equity() -> None:
    with pytest.raises(ValidationError, match="current_equity"):
        _runtime_input(current_equity=0.0)


def test_runtime_input_rejects_negative_session_peak_equity() -> None:
    with pytest.raises(ValidationError, match="session_peak_equity"):
        _runtime_input(session_peak_equity=-1.0)


def test_runtime_input_rejects_zero_max_selections() -> None:
    with pytest.raises(ValidationError, match="max_selections"):
        _runtime_input(max_selections=0)


def test_runtime_blocks_before_scoring_when_circuit_breaker_is_tripped(repo_tmp_path: Path) -> None:
    breaker = EmergencyCircuitBreaker(state_dir=_breaker_state_dir(repo_tmp_path, "engine_b"))
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


def test_runtime_requires_explicit_circuit_breaker() -> None:
    with pytest.raises(ValueError, match="requires a circuit_breaker"):
        EngineBRuntime(
            scoring_runtime=_scoring_runtime(),
            risk_runtime=_risk_runtime(),
            circuit_breaker=None,
        )


def test_runtime_rejects_blank_scoring_version(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_blank_version")

    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        runtime.evaluate(
            _runtime_input(engine_inputs=_good_engine_inputs(scoring_version="   ")),
            now=12.0,
        )


def test_runtime_can_be_blocked_by_sweep_validation_hook(repo_tmp_path: Path) -> None:
    runtime = _runtime(
        repo_tmp_path,
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


def test_runtime_applies_sweep_validation_score_adjustments_before_scoring(
    repo_tmp_path: Path,
) -> None:
    runtime = _runtime(
        repo_tmp_path,
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


def test_runtime_rejects_missing_scoring_audit_for_engine_candidate(repo_tmp_path: Path) -> None:
    class _MalformedScoringRuntime:
        def run_round(self, *args, **kwargs):
            return type("MalformedScoringRound", (), {"audits": ()})()

    runtime = _runtime(
        repo_tmp_path,
        "engine_b_missing_audit",
        scoring_runtime=_MalformedScoringRuntime(),
    )

    with pytest.raises(ValueError, match="missing scoring audit for engine_b/BTCUSDT"):
        runtime.evaluate(_runtime_input(), now=13.0)


def test_runtime_hard_blocked_logs_explicit_reasons(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_hard_blocked")
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


def test_runtime_hard_blocked_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_hard_blocked_forecast")

    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            blocker_conditions=BlockerCondition(is_stale_hard=True, is_pair_suspended=True),
        ),
        now=20.0,
    )

    assert result.status == EngineBRuntimeStatus.HARD_BLOCKED
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.hard_blocked" in result.forecast_signal_candidate.reason_codes
    assert result.refusal_record is not None
    assert result.refusal_record.reason_codes
    hard_block_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "hard_block.engine_b.runtime.hard_blocked" in hard_block_codes


def test_runtime_rejected_by_ranking_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_rejected_ranking")
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


def test_runtime_rejected_by_ranking_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_rejected_ranking_forecast")
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
            strategy_id="strategy-b-reversion",
            peer_candidates=(peer,),
            max_selections=1,
            portfolio=_portfolio_state(
                remaining_cluster_capacity={"btc_majors": 5000.0, "eth_ecosystem": 5000.0},
            ),
            engine_inputs=_good_engine_inputs(
                regime_trend_strength=0.5,
                volume_anomaly=0.4,
                structural_break=0.3,
                continuation_momentum=0.3,
            ),
        ),
        now=31.0,
    )

    assert result.status == EngineBRuntimeStatus.REJECTED_RANKING
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.rejected_ranking" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "scoring.engine_b.runtime.rejected_ranking" in conditioning_codes
    assert result.refusal_record is not None
    assert result.refusal_record.category.value == "no_trade"


def test_runtime_rejected_by_portfolio_is_auditable(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_rejected_portfolio")
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


def test_runtime_rejected_by_portfolio_annotates_forecast_truthfully(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_rejected_portfolio_forecast")
    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            portfolio=_portfolio_state(remaining_gross_capacity=10.0),
        ),
        now=40.0,
    )

    assert result.status == EngineBRuntimeStatus.REJECTED_PORTFOLIO
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.rejected_portfolio" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "portfolio.engine_b.runtime.rejected_portfolio" in conditioning_codes
    assert result.refusal_record is not None
    assert result.refusal_record.category.value == "portfolio_rejected"


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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_runtime", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(projected_size=1000.0), now=50.0)

    assert result.status == EngineBRuntimeStatus.RISK_REJECTED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.accepted is False
    risk_logs = [entry for entry in result.log_entries if entry.event == "engine_b_risk_rejected"]
    assert len(risk_logs) == 1
    assert "gross" in " ".join(risk_logs[0].reasons).lower()


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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_runtime_forecast", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion", projected_size=1000.0),
        now=50.0,
    )

    assert result.status == EngineBRuntimeStatus.RISK_REJECTED
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.risk_rejected" in result.forecast_signal_candidate.reason_codes
    assert result.refusal_record is not None
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "hard_block.engine_b.runtime.risk_rejected" in conditioning_codes


def test_runtime_risk_reduced_event_matches_status(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_reduced", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=70.0)

    assert result.status == EngineBRuntimeStatus.RISK_REDUCED
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.REDUCE_EXPOSURE
    assert any(entry.event == "engine_b_risk_reduced" for entry in result.log_entries)
    assert not any(entry.event == "engine_b_risk_rejected" for entry in result.log_entries)
    assert result.refusal_record is None


def test_runtime_risk_reduced_is_governed_without_refusal_record(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_reduced_forecast", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion"),
        now=70.0,
    )

    assert result.status == EngineBRuntimeStatus.RISK_REDUCED
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.risk_reduced" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "engine_internal.engine_b.runtime.risk_reduced" in conditioning_codes
    assert result.refusal_record is None


def test_runtime_risk_observe_only_event_matches_status(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_observe", risk_runtime=risk_runtime)

    result = runtime.evaluate(_runtime_input(), now=80.0)

    assert result.status == EngineBRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.risk_evaluation is not None
    assert result.risk_evaluation.action == RiskRuntimeAction.OBSERVE_ONLY
    assert any(entry.event == "engine_b_risk_observe_only" for entry in result.log_entries)
    assert not any(entry.event == "engine_b_risk_rejected" for entry in result.log_entries)


def test_runtime_risk_observe_only_is_governed_without_refusal_record(repo_tmp_path: Path) -> None:
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
    runtime = _runtime(repo_tmp_path, "engine_b_risk_observe_forecast", risk_runtime=risk_runtime)

    result = runtime.evaluate(
        _runtime_input(strategy_id="strategy-b-reversion"),
        now=80.0,
    )

    assert result.status == EngineBRuntimeStatus.RISK_OBSERVE_ONLY
    assert result.forecast_signal_candidate is not None
    assert "engine_b.runtime.risk_observe_only" in result.forecast_signal_candidate.reason_codes
    conditioning_codes = {record.code for record in result.forecast_signal_candidate.conditioning_state}
    assert "engine_internal.engine_b.runtime.risk_observe_only" in conditioning_codes
    assert result.refusal_record is None


def test_runtime_never_creates_fake_flat_side_or_fake_blocked_trade(repo_tmp_path: Path) -> None:
    runtime = _runtime(repo_tmp_path, "engine_b_no_fake_flat")
    result = runtime.evaluate(
        _runtime_input(
            strategy_id="strategy-b-reversion",
            blocker_conditions=BlockerCondition(is_stale_hard=True),
        ),
        now=25.0,
    )

    assert result.status == EngineBRuntimeStatus.HARD_BLOCKED
    assert result.signal_candidate is not None
    assert result.signal_candidate.side == Side.BUY
    assert result.forecast_signal_candidate is not None
