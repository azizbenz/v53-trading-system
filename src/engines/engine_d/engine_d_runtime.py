"""Engine D runtime across signal, scoring, ranking and risk."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from interface_contracts import (
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineCoordinationInput,
    EngineCoordinationOutcome,
    EngineCoordinationThresholds,
    EngineId,
    ForecastSignalCandidate,
    RefusalRecord,
    Side,
    SignalCandidate as DecisionSignalCandidate,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskEvaluation, RiskRuntime, RiskRuntimeAction
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.selection_resolver import SelectionEntry, SelectionOutcome
from scoring_backbone.scoring_runtime import (
    ScoringCandidateAudit,
    ScoringCandidateInput,
    ScoringRoundResult,
    ScoringRuntime,
)
from .engine_d_runner import EngineDDecision, EngineDInput, EngineDLogEntry, EngineDOutput, run_engine_d
from .engine_d_runtime_history_entry_mixin import EngineDRuntimeHistoricalEntryMixin
from .consecutive_stop_counter_d import EngineDResetStateInspection
from .first_episode_resolver_d import FirstEpisodeGapInspectionD
from .historical_linkage_guard_d import evaluate_engine_d_historical_linkage
from .engine_d_runtime_support import (
    _EngineDScoringState,
    annotate_forecast_signal_candidate_for_runtime_status,
    append_runtime_log as _append_runtime_log,
    build_runtime_refusal_record,
    build_scoring_state,
    build_signal_candidate,
    evaluate_risk,
    require_scoring_version,
    require_selection_entry,
    resolve_runtime_now,
    resolve_hook_blocked_reason_codes,
    run_reentry_validation_hook,
    validate_coordination_input,
)
_ENGINE_D_FEATURE_WEIGHTS: dict[str, float] = {
    "history": 0.25,
    "reformation": 0.30,
    "marginal_value": 0.25,
    "cost_preference": 0.20,
}


class _RefusalSink(Protocol):
    def record_refusal(self, record: RefusalRecord) -> None:
        ...


class _CoordinationEvaluator(Protocol):
    def __call__(
        self,
        coordination_input: EngineCoordinationInput,
        *,
        thresholds: EngineCoordinationThresholds | None = None,
    ) -> EngineCoordinationOutcome:
        ...


class EngineDRuntimeStatus(StrEnum):
    NO_TRADE = "no_trade"
    CIRCUIT_BREAKER_BLOCKED = "circuit_breaker_blocked"
    HOOK_BLOCKED = "hook_blocked"
    HARD_BLOCKED = "hard_blocked"
    REJECTED_RANKING = "rejected_ranking"
    REJECTED_PORTFOLIO = "rejected_portfolio"
    RISK_REJECTED = "risk_rejected"
    RISK_REDUCED = "risk_reduced"
    RISK_OBSERVE_ONLY = "risk_observe_only"
    ACCEPTED = "accepted"
class EngineDRuntimeInput(BaseModel, frozen=True):
    engine_inputs: EngineDInput
    timestamp_ms: int = Field(..., ge=1_000_000_000_000)  # BS-86: must be milliseconds, not seconds
    portfolio: PortfolioState
    projected_size: float
    projected_loss: float | None = None
    current_equity: float
    session_peak_equity: float
    pair_beta: float | None = None
    cluster_id: str
    score_penalties: tuple[ScorePenaltyItem, ...] = ()
    size_penalties: tuple[SizePenaltyItem, ...] = ()
    blocker_conditions: BlockerCondition = Field(default_factory=BlockerCondition)
    supplementary_refs: tuple[str, ...] = ()
    peer_candidates: tuple[ScoringCandidateInput, ...] = ()
    max_selections: int = 1
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
    coordination_input: EngineCoordinationInput | None = None
    first_episode_gap_inspection: FirstEpisodeGapInspectionD | None = None
    strategy_id: str | None = None
    @field_validator("strategy_id")
    @classmethod
    def _normalize_strategy_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("strategy_id must not be blank")
        return normalized
class EngineDReentryValidationHook(Protocol):
    def __call__(
        self,
        hook_input: EngineDReentryValidationInput,
    ) -> EngineDReentryValidationOutcome:
        ...
class EngineDRuntimeResult(BaseModel, frozen=True):
    status: EngineDRuntimeStatus
    engine_output: EngineDOutput
    signal_candidate: DecisionSignalCandidate | None = None
    forecast_signal_candidate: ForecastSignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    hook_outcome: EngineDReentryValidationOutcome | None = None
    coordination_outcome: EngineCoordinationOutcome | None = None
    historical_state_inspection: EngineDResetStateInspection | None = None
    first_episode_gap_inspection: FirstEpisodeGapInspectionD | None = None
    refusal_record: RefusalRecord | None = None
    log_entries: tuple[EngineDLogEntry, ...] = ()


from .engine_d_runtime_result_builders import (
    _build_accepted_runtime_result,
    _build_circuit_breaker_blocked_result,
    _build_hard_blocked_runtime_result,
    _build_hook_blocked_runtime_result,
    _build_missing_scoring_audit_runtime_result,
    _build_risk_runtime_result,
    _build_runtime_result,
    _build_selection_rejected_runtime_result,
)


class EngineDRuntime(EngineDRuntimeHistoricalEntryMixin):
    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        reentry_validation_hook: EngineDReentryValidationHook | None = None,
        refusal_sink: _RefusalSink | None = None,
        coordination_thresholds: EngineCoordinationThresholds | None = None,
        coordination_evaluator: _CoordinationEvaluator | None = None,
        first_episode_lookback_ns: int | None = None,
        first_episode_min_gap_ns: int | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineDRuntime requires a circuit_breaker")
        if first_episode_lookback_ns is not None and first_episode_lookback_ns <= 0:
            raise ValueError("first_episode_lookback_ns must be positive when provided")
        if first_episode_min_gap_ns is not None and first_episode_min_gap_ns <= 0:
            raise ValueError("first_episode_min_gap_ns must be positive when provided")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._reentry_validation_hook = reentry_validation_hook
        self._refusal_sink = refusal_sink
        self._coordination_thresholds = coordination_thresholds
        self._coordination_evaluator = coordination_evaluator
        self._first_episode_lookback_ns = first_episode_lookback_ns
        self._first_episode_min_gap_ns = first_episode_min_gap_ns

    def evaluate(
        self,
        runtime_input: EngineDRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineDRuntimeResult:
        timestamp = resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineDRuntime.evaluate")
        require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineDRuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return self._finalize_runtime_result(
                runtime_input,
                _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker),
            )

        engine_output = run_engine_d(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)
        if engine_output.decision != EngineDDecision.EMIT:
            return self._finalize_runtime_result(
                runtime_input,
                _build_runtime_result(
                    status=EngineDRuntimeStatus.NO_TRADE,
                    engine_output=engine_output,
                    logs=logs,
                ),
            )

        first_episode_gap_inspection = runtime_input.first_episode_gap_inspection
        if first_episode_gap_inspection is not None and first_episode_gap_inspection.blocked:
            gap_reason_code = first_episode_gap_inspection.reason_code or "hard_block.d_min_gap_not_elapsed"
            engine_output = engine_output.model_copy(
                update={"reason_codes": tuple(dict.fromkeys((*engine_output.reason_codes, gap_reason_code)))}
            )
            _append_runtime_log(
                logs,
                runtime_input,
                engine_output,
                event="engine_d_first_episode_gap_blocked",
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                reasons=(gap_reason_code,),
            )
            return self._finalize_runtime_result(runtime_input, _build_runtime_result(
                status=EngineDRuntimeStatus.HARD_BLOCKED,
                engine_output=engine_output,
                logs=logs,
                first_episode_gap_inspection=first_episode_gap_inspection,
            ))

        coordination_outcome = self._evaluate_coordination(runtime_input, engine_output, logs)
        if coordination_outcome is not None and coordination_outcome.blocked:
            return self._finalize_runtime_result(
                runtime_input,
                _build_runtime_result(
                    status=EngineDRuntimeStatus.HARD_BLOCKED,
                    engine_output=engine_output,
                    logs=logs,
                    coordination_outcome=coordination_outcome,
                ),
            )
        effective_runtime_input = self._apply_coordination(runtime_input, logs, engine_output, coordination_outcome)

        hook_outcome = run_reentry_validation_hook(
            self._reentry_validation_hook,
            effective_runtime_input,
            engine_output,
        )
        if hook_outcome is not None and not hook_outcome.accepted:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hook_blocked_runtime_result(
                    effective_runtime_input,
                    engine_output,
                    logs,
                    hook_outcome=hook_outcome,
                    coordination_outcome=coordination_outcome,
                ),
            )

        scoring_state = build_scoring_state(
            self._scoring_runtime,
            feature_weights=_ENGINE_D_FEATURE_WEIGHTS,
            runtime_input=effective_runtime_input,
            engine_output=engine_output,
            logs=logs,
            timestamp=timestamp,
        )
        if scoring_state.scoring_audit is None:
            return self._finalize_runtime_result(
                runtime_input,
                _build_missing_scoring_audit_runtime_result(
                    engine_output,
                    logs,
                    timestamp_ms=runtime_input.timestamp_ms,
                    scoring_state=scoring_state,
                    hook_outcome=hook_outcome,
                    coordination_outcome=coordination_outcome,
                ),
            )
        if scoring_state.scoring_audit.hard_block_decision.is_blocked:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hard_blocked_runtime_result(
                    effective_runtime_input,
                    engine_output,
                    logs,
                    scoring_state=scoring_state,
                    hook_outcome=hook_outcome,
                    coordination_outcome=coordination_outcome,
                ),
            )

        selection_entry = require_selection_entry(scoring_state.scoring_audit)
        selection_result = _build_selection_rejected_runtime_result(
            effective_runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            selection_entry=selection_entry,
            hook_outcome=hook_outcome,
            coordination_outcome=coordination_outcome,
        )
        if selection_result is not None:
            return self._finalize_runtime_result(runtime_input, selection_result)

        risk_evaluation = evaluate_risk(
            self._risk_runtime,
            runtime_input=effective_runtime_input,
            engine_output=engine_output,
            scoring_state=scoring_state,
            timestamp=timestamp,
        )
        risk_result = _build_risk_runtime_result(
            effective_runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            risk_evaluation=risk_evaluation,
            hook_outcome=hook_outcome,
            coordination_outcome=coordination_outcome,
        )
        if risk_result is not None:
            return self._finalize_runtime_result(runtime_input, risk_result)

        return self._finalize_runtime_result(
            runtime_input,
            _build_accepted_runtime_result(
                effective_runtime_input,
                engine_output,
                logs,
                scoring_state=scoring_state,
                risk_evaluation=risk_evaluation,
                hook_outcome=hook_outcome,
                coordination_outcome=coordination_outcome,
            ),
        )

    def _finalize_runtime_result(
        self,
        runtime_input: EngineDRuntimeInput,
        result: EngineDRuntimeResult,
    ) -> EngineDRuntimeResult:
        refusal_record = build_runtime_refusal_record(
            timestamp_ms=runtime_input.timestamp_ms,
            status=result.status.value,
            engine_output=result.engine_output,
            log_entries=result.log_entries,
            scoring_audit=result.scoring_audit,
            risk_evaluation=result.risk_evaluation,
            coordination_outcome=result.coordination_outcome,
        )
        if refusal_record is None:
            return result
        if self._refusal_sink is not None:
            self._refusal_sink.record_refusal(refusal_record)
        return result.model_copy(update={"refusal_record": refusal_record})

    def _evaluate_coordination(
        self,
        runtime_input: EngineDRuntimeInput,
        engine_output: EngineDOutput,
        logs: list[EngineDLogEntry],
    ) -> EngineCoordinationOutcome | None:
        coordination_input = runtime_input.coordination_input
        if coordination_input is None:
            return None
        if self._coordination_evaluator is None:
            raise ValueError("EngineDRuntime requires coordination_evaluator when coordination_input is provided")
        validate_coordination_input(
            coordination_input,
            engine_id=EngineId.D,
            pair=engine_output.pair,
            side=Side.BUY,
        )
        coordination_outcome = evaluate_engine_d_historical_linkage(
            coordination_input,
            thresholds=self._coordination_thresholds,
            evaluator=self._coordination_evaluator,
        )
        if coordination_outcome.blocked:
            _append_runtime_log(
                logs,
                runtime_input,
                engine_output,
                event="engine_d_coordination_blocked",
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                reasons=coordination_outcome.reason_codes or (coordination_outcome.detail,),
            )
        return coordination_outcome

    def _apply_coordination(
        self,
        runtime_input: EngineDRuntimeInput,
        logs: list[EngineDLogEntry],
        engine_output: EngineDOutput,
        coordination_outcome: EngineCoordinationOutcome | None,
    ) -> EngineDRuntimeInput:
        if coordination_outcome is None:
            return runtime_input
        effective_size = coordination_outcome.resolved_size
        if effective_size is None:
            effective_size = runtime_input.projected_size * coordination_outcome.size_multiplier
        if effective_size == runtime_input.projected_size:
            return runtime_input
        loss_scale = coordination_outcome.size_multiplier
        if runtime_input.projected_size > 0.0:
            loss_scale = effective_size / runtime_input.projected_size
        effective_loss = runtime_input.projected_loss
        if effective_loss is not None:
            effective_loss *= loss_scale
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_d_coordination_size_reduced",
            raw_score=engine_output.raw_score,
            penalized_score=engine_output.penalized_score,
            reasons=coordination_outcome.reason_codes or ("coordination.d.size_reduced",),
        )
        return runtime_input.model_copy(
            update={
                "projected_size": effective_size,
                "projected_loss": effective_loss,
            }
        )
