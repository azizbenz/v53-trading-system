"""Result builders for the Engine D runtime facade."""

from __future__ import annotations

from interface_contracts import (
    EngineCoordinationOutcome,
    ForecastSignalCandidate,
    RefusalRecord,
    SignalCandidate as DecisionSignalCandidate,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskEvaluation, RiskRuntimeAction
from scoring_backbone.ranking_router.selection_resolver import SelectionEntry, SelectionOutcome
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringRoundResult

from .consecutive_stop_counter_d import EngineDResetStateInspection
from .first_episode_resolver_d import FirstEpisodeGapInspectionD
from .engine_d_models import EngineDDecision, EngineDLogEntry, EngineDOutput
from .engine_d_runtime import (
    EngineDReentryValidationOutcome,
    EngineDRuntimeInput,
    EngineDRuntimeResult,
    EngineDRuntimeStatus,
)
from .engine_d_runtime_support import (
    _EngineDScoringState,
    annotate_forecast_signal_candidate_for_runtime_status,
    append_runtime_log as _append_runtime_log,
    resolve_hook_blocked_reason_codes,
)


def _build_runtime_result(
    *,
    status: EngineDRuntimeStatus,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    signal_candidate: DecisionSignalCandidate | None = None,
    forecast_signal_candidate: ForecastSignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
    historical_state_inspection: EngineDResetStateInspection | None = None,
    first_episode_gap_inspection: FirstEpisodeGapInspectionD | None = None,
    refusal_record: RefusalRecord | None = None,
) -> EngineDRuntimeResult:
    return EngineDRuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        forecast_signal_candidate=forecast_signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
        historical_state_inspection=historical_state_inspection,
        first_episode_gap_inspection=first_episode_gap_inspection,
        refusal_record=refusal_record,
        log_entries=tuple(logs),
    )


def _build_hook_blocked_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    hook_outcome: EngineDReentryValidationOutcome,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult:
    hook_reason_codes = resolve_hook_blocked_reason_codes(hook_outcome.reason_codes)
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_d_hook_blocked",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=hook_reason_codes,
    )
    return _build_runtime_result(
        status=EngineDRuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_missing_scoring_audit_runtime_result(
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    timestamp_ms: int,
    scoring_state: _EngineDScoringState,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult:
    return _build_runtime_result(
        status=EngineDRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=timestamp_ms,
            status=EngineDRuntimeStatus.HARD_BLOCKED.value,
            scoring_audit=None,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_hard_blocked_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D hard-block evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_d_hard_blocked",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=tuple(reason.human_reason for reason in scoring_audit.hard_block_decision.reasons),
    )
    return _build_runtime_result(
        status=EngineDRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineDRuntimeStatus.HARD_BLOCKED.value,
            scoring_audit=scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_selection_rejected_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    selection_entry: SelectionEntry,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult | None:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D selection evaluation requires a scoring audit")
    if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_d_rejected_by_ranking",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=scoring_state.penalized_score,
            reasons=(selection_entry.rejection_reason,),
        )
        return _build_runtime_result(
            status=EngineDRuntimeStatus.REJECTED_RANKING,
            engine_output=engine_output,
            logs=logs,
            signal_candidate=scoring_state.signal_candidate,
            forecast_signal_candidate=annotate_forecast_signal_candidate_for_runtime_status(
                scoring_state.forecast_signal_candidate,
                timestamp_ms=runtime_input.timestamp_ms,
                status=EngineDRuntimeStatus.REJECTED_RANKING.value,
                scoring_audit=scoring_audit,
                risk_evaluation=None,
            ),
            scoring_round=scoring_state.scoring_round,
            scoring_audit=scoring_audit,
            hook_outcome=hook_outcome,
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
        event="engine_d_rejected_by_portfolio",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=(portfolio_reason,),
    )
    return _build_runtime_result(
        status=EngineDRuntimeStatus.REJECTED_PORTFOLIO,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineDRuntimeStatus.REJECTED_PORTFOLIO.value,
            scoring_audit=scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_risk_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    risk_evaluation: RiskEvaluation,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D risk evaluation requires a scoring audit")
    event = {
        RiskRuntimeAction.REJECT: "engine_d_risk_rejected",
        RiskRuntimeAction.REDUCE_EXPOSURE: "engine_d_risk_reduced",
        RiskRuntimeAction.OBSERVE_ONLY: "engine_d_risk_observe_only",
    }.get(risk_evaluation.action, "engine_d_risk_rejected")
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
        RiskRuntimeAction.REJECT: EngineDRuntimeStatus.RISK_REJECTED,
        RiskRuntimeAction.REDUCE_EXPOSURE: EngineDRuntimeStatus.RISK_REDUCED,
        RiskRuntimeAction.OBSERVE_ONLY: EngineDRuntimeStatus.RISK_OBSERVE_ONLY,
    }.get(risk_evaluation.action, EngineDRuntimeStatus.RISK_REJECTED)
    return _build_runtime_result(
        status=status,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=status.value,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_accepted_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    risk_evaluation: RiskEvaluation,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
    coordination_outcome: EngineCoordinationOutcome | None = None,
) -> EngineDRuntimeResult:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D accepted evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_d_accepted",
        raw_score=scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
    )
    return _build_runtime_result(
        status=EngineDRuntimeStatus.ACCEPTED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
        coordination_outcome=coordination_outcome,
    )


def _build_circuit_breaker_blocked_result(
    runtime_input: EngineDRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineDRuntimeResult:
    reason = circuit_breaker.current_reason.value
    reason_code = f"engine_d.runtime.circuit_breaker.{reason}"
    log_entry = EngineDLogEntry(
        event="engine_d_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        origin_context_id=runtime_input.engine_inputs.origin_context_id,
        origin_trade_id=runtime_input.engine_inputs.origin_trade_id,
        link_type=runtime_input.engine_inputs.link_type,
        structure_reformed_detected=runtime_input.engine_inputs.structure_reformed_detected,
        reasons=(reason_code,),
        scoring_version=runtime_input.engine_inputs.scoring_version,
    )
    engine_output = EngineDOutput(
        pair=runtime_input.engine_inputs.pair,
        decision=EngineDDecision.NO_TRADE,
        origin_context_id=runtime_input.engine_inputs.origin_context_id,
        origin_trade_id=runtime_input.engine_inputs.origin_trade_id,
        link_type=runtime_input.engine_inputs.link_type,
        structure_reformed_detected=runtime_input.engine_inputs.structure_reformed_detected,
        scoring_version=runtime_input.engine_inputs.scoring_version,
        log_entries=(log_entry,),
    )
    return EngineDRuntimeResult(
        status=EngineDRuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        engine_output=engine_output,
        log_entries=(log_entry,),
    )
