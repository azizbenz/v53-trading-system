"""Engine C runtime across signal, scoring, ranking and risk."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from interface_contracts import (
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
    EngineCoordinationInput,
    EngineCoordinationOutcome,
    EngineCoordinationThresholds,
    EngineId,
    ForecastSignalCandidate,
    RefusalRecord,
    Side,
    SignalCandidate as DecisionSignalCandidate,
)
from interface_contracts.forecast_contracts import merge_reason_codes
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

from .engine_c_runner import EngineCDecision, EngineCInput, EngineCLogEntry, EngineCOutput, run_engine_c
from .engine_c_runtime_support import (
    _EngineCScoringState,
    _annotate_forecast_signal_candidate_for_runtime_status,
    append_runtime_log as _append_runtime_log,
    build_runtime_refusal_record as _build_runtime_refusal_record,
    build_scoring_state as _build_scoring_state,
    build_signal_candidate as _build_signal_candidate,
    evaluate_risk as _evaluate_risk,
    require_scoring_version as _require_scoring_version,
    _resolve_hook_blocked_reason_codes,
    require_selection_entry as _require_selection_entry,
    resolve_runtime_now as _resolve_runtime_now,
    run_void_validation_hook as _run_void_validation_hook,
    validate_coordination_input as _validate_coordination_input,
)


_ENGINE_C_FEATURE_WEIGHTS: dict[str, float] = {
    "breakout": 0.40,
    "continuation": 0.30,
    "context": 0.20,
    "ce_component": 0.10,
    "fake_breakout_risk": -0.10,
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


class EngineCRuntimeStatus(StrEnum):
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
class EngineCRuntimeInput(BaseModel, frozen=True):
    engine_inputs: EngineCInput
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
class EngineCVoidValidationHook(Protocol):
    """Bounded hook surface injected into the real Engine C runtime rail."""

    def __call__(
        self,
        hook_input: EngineCVoidValidationInput,
    ) -> EngineCVoidValidationOutcome:
        ...
class EngineCRuntimeResult(BaseModel, frozen=True):
    status: EngineCRuntimeStatus
    engine_output: EngineCOutput
    signal_candidate: DecisionSignalCandidate | None = None
    forecast_signal_candidate: ForecastSignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    coordination_outcome: EngineCoordinationOutcome | None = None
    refusal_record: RefusalRecord | None = None
    log_entries: tuple[EngineCLogEntry, ...] = ()
class EngineCRuntime:
    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        void_validation_hook: EngineCVoidValidationHook | None = None,
        refusal_sink: _RefusalSink | None = None,
        coordination_thresholds: EngineCoordinationThresholds | None = None,
        coordination_evaluator: _CoordinationEvaluator | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineCRuntime requires a circuit_breaker")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._void_validation_hook = void_validation_hook
        self._refusal_sink = refusal_sink
        self._coordination_thresholds = coordination_thresholds
        self._coordination_evaluator = coordination_evaluator

    def evaluate(
        self,
        runtime_input: EngineCRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineCRuntimeResult:
        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineCRuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineCRuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return self._finalize_runtime_result(
                runtime_input,
                _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker),
            )

        engine_output = run_engine_c(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)
        if engine_output.decision != EngineCDecision.EMIT:
            return self._finalize_runtime_result(
                runtime_input,
                _build_runtime_result(
                    status=EngineCRuntimeStatus.NO_TRADE,
                    engine_output=engine_output,
                    logs=logs,
                ),
            )

        try:
            coordination_input = _require_coordination_input(runtime_input)
        except ValueError:
            return self._finalize_runtime_result(
                runtime_input,
                _build_coordination_missing_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                ),
            )

        coordination_outcome = self._evaluate_coordination(
            runtime_input,
            coordination_input,
            engine_output,
            logs,
        )
        if coordination_outcome is not None and coordination_outcome.blocked:
            return self._finalize_runtime_result(
                runtime_input,
                _build_runtime_result(
                    status=EngineCRuntimeStatus.HARD_BLOCKED,
                    engine_output=engine_output,
                    logs=logs,
                    coordination_outcome=coordination_outcome,
                ),
            )

        hook_outcome = _run_void_validation_hook(self._void_validation_hook, runtime_input, engine_output)
        if hook_outcome is not None and not hook_outcome.accepted:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hook_blocked_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                    hook_outcome=hook_outcome,
                    coordination_outcome=coordination_outcome,
                ),
            )

        scoring_state = _build_scoring_state(
            self._scoring_runtime,
            feature_weights=_ENGINE_C_FEATURE_WEIGHTS,
            runtime_input=runtime_input,
            engine_output=engine_output,
            logs=logs,
            timestamp=timestamp,
        )
        if scoring_state.scoring_audit is None:
            return self._finalize_runtime_result(
                runtime_input,
                _build_missing_scoring_audit_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                    scoring_state=scoring_state,
                    coordination_outcome=coordination_outcome,
                ),
            )
        if scoring_state.scoring_audit.hard_block_decision.is_blocked:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hard_blocked_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                    scoring_state=scoring_state,
                    coordination_outcome=coordination_outcome,
                ),
            )

        selection_entry = _require_selection_entry(scoring_state.scoring_audit)
        selection_result = _build_selection_rejected_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            selection_entry=selection_entry,
            coordination_outcome=coordination_outcome,
        )
        if selection_result is not None:
            return self._finalize_runtime_result(runtime_input, selection_result)

        risk_evaluation = _evaluate_risk(
            self._risk_runtime,
            runtime_input=runtime_input,
            engine_output=engine_output,
            scoring_state=scoring_state,
            timestamp=timestamp,
        )
        risk_result = _build_risk_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            risk_evaluation=risk_evaluation,
            coordination_outcome=coordination_outcome,
        )
        if risk_result is not None:
            return self._finalize_runtime_result(runtime_input, risk_result)

        return self._finalize_runtime_result(
            runtime_input,
            _build_accepted_runtime_result(
                runtime_input,
                engine_output,
                logs,
                scoring_state=scoring_state,
                risk_evaluation=risk_evaluation,
                coordination_outcome=coordination_outcome,
            ),
        )

    def _finalize_runtime_result(
        self,
        runtime_input: EngineCRuntimeInput,
        result: EngineCRuntimeResult,
    ) -> EngineCRuntimeResult:
        refusal_record = _build_runtime_refusal_record(
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
        runtime_input: EngineCRuntimeInput,
        coordination_input: EngineCoordinationInput,
        engine_output: EngineCOutput,
        logs: list[EngineCLogEntry],
    ) -> EngineCoordinationOutcome | None:
        """Evaluate canonical runtime coordination.

        Engine C local duplication heuristics remain observability-only; the
        doctrinal A/C hard-block lives here through engine_coordination_rules.
        """
        _validate_coordination_input(
            coordination_input,
            engine_id=EngineId.C,
            pair=engine_output.pair,
            side=Side.BUY,
        )
        if self._coordination_evaluator is None:
            raise ValueError("EngineCRuntime requires coordination_evaluator when coordination_input is provided")
        coordination_outcome = self._coordination_evaluator(
            coordination_input,
            thresholds=self._coordination_thresholds,
        )
        if coordination_outcome.blocked:
            _append_runtime_log(
                logs,
                runtime_input,
                engine_output,
                event="engine_c_coordination_blocked",
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                reasons=merge_reason_codes(
                    ("engine_c.runtime.coordination_blocked",),
                    coordination_outcome.reason_codes or (),
                ),
            )
        return coordination_outcome


def _require_coordination_input(
    runtime_input: EngineCRuntimeInput,
) -> EngineCoordinationInput:
    coordination_input = runtime_input.coordination_input
    if coordination_input is None:
        raise ValueError("coordination_input is required on the Engine C runtime emit rail")
    return coordination_input

def _build_runtime_result(
    *,
    status: EngineCRuntimeStatus,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    signal_candidate: DecisionSignalCandidate | None = None,
    forecast_signal_candidate: ForecastSignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
    refusal_record: RefusalRecord | None = None,
) -> EngineCRuntimeResult:
    return EngineCRuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        forecast_signal_candidate=forecast_signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        coordination_outcome=coordination_outcome,
        refusal_record=refusal_record,
        log_entries=tuple(logs),
    )


def _build_coordination_missing_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
) -> EngineCRuntimeResult:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_coordination_missing",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=(
            "engine_c.runtime.coordination_input_missing",
            "engine_c.runtime.coordination_required",
        ),
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
    )
def _build_hook_blocked_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    hook_outcome: EngineCVoidValidationOutcome,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult:
    hook_reason_codes = _resolve_hook_blocked_reason_codes(hook_outcome.reason_codes)
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_hook_blocked",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=hook_reason_codes,
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        coordination_outcome=coordination_outcome,
    )
def _build_missing_scoring_audit_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult:
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineCRuntimeStatus.HARD_BLOCKED.value,
            scoring_audit=None,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        coordination_outcome=coordination_outcome,
    )
def _build_hard_blocked_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C hard-block evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_hard_blocked",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=tuple(reason.human_reason for reason in scoring_audit.hard_block_decision.reasons),
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineCRuntimeStatus.HARD_BLOCKED.value,
            scoring_audit=scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        coordination_outcome=coordination_outcome,
    )
def _build_selection_rejected_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    selection_entry: SelectionEntry,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult | None:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C selection evaluation requires a scoring audit")
    if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_c_rejected_by_ranking",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=scoring_state.penalized_score,
            reasons=(selection_entry.rejection_reason,),
        )
        return _build_runtime_result(
            status=EngineCRuntimeStatus.REJECTED_RANKING,
            engine_output=engine_output,
            logs=logs,
            signal_candidate=scoring_state.signal_candidate,
            forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
                scoring_state.forecast_signal_candidate,
                timestamp_ms=runtime_input.timestamp_ms,
                status=EngineCRuntimeStatus.REJECTED_RANKING.value,
                scoring_audit=scoring_audit,
                risk_evaluation=None,
            ),
            scoring_round=scoring_state.scoring_round,
            scoring_audit=scoring_audit,
            coordination_outcome=coordination_outcome,
        )
    if selection_entry.outcome != SelectionOutcome.REJECTED_PORTFOLIO:
        return None
    portfolio_reason = selection_entry.rejection_reason
    if scoring_audit.portfolio_result is not None and scoring_audit.portfolio_result.reason:
        portfolio_reason = scoring_audit.portfolio_result.reason
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_rejected_by_portfolio",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=(portfolio_reason,),
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.REJECTED_PORTFOLIO,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineCRuntimeStatus.REJECTED_PORTFOLIO.value,
            scoring_audit=scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        coordination_outcome=coordination_outcome,
    )
def _build_risk_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    risk_evaluation: RiskEvaluation,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C risk evaluation requires a scoring audit")
    event = {
        RiskRuntimeAction.REJECT: "engine_c_risk_rejected",
        RiskRuntimeAction.REDUCE_EXPOSURE: "engine_c_risk_reduced",
        RiskRuntimeAction.OBSERVE_ONLY: "engine_c_risk_observe_only",
    }.get(risk_evaluation.action, "engine_c_risk_rejected")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event=event,
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=risk_evaluation.reasons or ("risk runtime rejected candidate",),
    )
    status = {
        RiskRuntimeAction.REJECT: EngineCRuntimeStatus.RISK_REJECTED,
        RiskRuntimeAction.REDUCE_EXPOSURE: EngineCRuntimeStatus.RISK_REDUCED,
        RiskRuntimeAction.OBSERVE_ONLY: EngineCRuntimeStatus.RISK_OBSERVE_ONLY,
    }.get(risk_evaluation.action, EngineCRuntimeStatus.RISK_REJECTED)
    return _build_runtime_result(
        status=status,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=status.value,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        coordination_outcome=coordination_outcome,
    )
def _build_accepted_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    risk_evaluation: RiskEvaluation,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineCRuntimeResult:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C accepted evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_accepted",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.ACCEPTED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        coordination_outcome=coordination_outcome,
    )
def _build_circuit_breaker_blocked_result(
    runtime_input: EngineCRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineCRuntimeResult:
    reason = circuit_breaker.current_reason.value
    reason_code = f"engine_c.runtime.circuit_breaker.{reason}"
    log_entry = EngineCLogEntry(
        event="engine_c_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        reasons=(reason_code,),
        scoring_version=runtime_input.engine_inputs.scoring_version,
    )
    engine_output = EngineCOutput(
        pair=runtime_input.engine_inputs.pair,
        decision=EngineCDecision.NO_TRADE,
        scoring_version=runtime_input.engine_inputs.scoring_version,
        log_entries=(log_entry,),
    )
    return EngineCRuntimeResult(
        status=EngineCRuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        engine_output=engine_output,
        log_entries=(log_entry,),
    )
