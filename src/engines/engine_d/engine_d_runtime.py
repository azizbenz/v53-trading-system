"""Engine D runtime across signal, scoring, ranking and risk."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from interface_contracts import (
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineId,
    Side,
    SignalCandidate,
    SignalType,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntime, RiskRuntimeAction
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
from .engine_d_runtime_support import (
    require_scoring_version,
    resolve_runtime_now,
    resolve_scoring_audit,
    to_regime_id,
)


_ENGINE_D_FEATURE_WEIGHTS: dict[str, float] = {
    "history": 0.25,
    "reformation": 0.30,
    "marginal_value": 0.25,
    "cost_preference": 0.20,
}
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
    peer_candidates: tuple[ScoringCandidateInput, ...] = ()
    max_selections: int = 1
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
class EngineDReentryValidationHook(Protocol):
    """Bounded hook surface injected into the real Engine D runtime rail."""

    def __call__(
        self,
        hook_input: EngineDReentryValidationInput,
    ) -> EngineDReentryValidationOutcome:
        ...
class EngineDRuntimeResult(BaseModel, frozen=True):
    status: EngineDRuntimeStatus
    engine_output: EngineDOutput
    signal_candidate: SignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    hook_outcome: EngineDReentryValidationOutcome | None = None
    log_entries: tuple[EngineDLogEntry, ...] = ()
@dataclass(frozen=True)
class _EngineDScoringState:
    signal_candidate: SignalCandidate
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit | None
    penalized_score: float
def _runtime_log_entry(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    **overrides: object,
) -> EngineDLogEntry:
    payload: dict[str, object] = {
        "pair": engine_output.pair,
        "regime": runtime_input.engine_inputs.regime,
        "origin_context_id": engine_output.origin_context_id,
        "origin_trade_id": engine_output.origin_trade_id,
        "link_type": engine_output.link_type,
        "structure_reformed_detected": engine_output.structure_reformed_detected,
        "first_episode_id": engine_output.first_episode_id,
        "first_episode_engine_id": engine_output.first_episode_engine_id,
        "first_episode_close_reason": engine_output.first_episode_close_reason,
        "consecutive_stop_count": engine_output.consecutive_stop_count,
        "last_stop_at_ns": engine_output.last_stop_at_ns,
        "last_fresh_a_detection_at_ns": engine_output.last_fresh_a_detection_at_ns,
        "anti_revenge_state": engine_output.anti_revenge_state,
        "history_score": engine_output.history_score,
        "reformation_score": engine_output.reformation_score,
        "marginal_value_score": engine_output.marginal_value_score,
        "concentration_risk": engine_output.concentration_risk,
        "marginal_concentration": engine_output.marginal_concentration,
        "expected_cost": engine_output.expected_cost,
        "ce_expected": engine_output.ce_expected,
        "ev_net": engine_output.ev_net,
        "duplication_possible_with_engine_a": engine_output.duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": engine_output.duplication_overlap_with_engine_a,
        "marginal_portfolio_gain": engine_output.marginal_portfolio_gain,
        "covered_share_by_engine_a": engine_output.covered_share_by_engine_a,
        "conviction": engine_output.conviction.value,
        "tier": engine_output.tier_suggestion.value,
        "holding_hours": engine_output.holding_hours,
        "scoring_version": engine_output.scoring_version,
    }
    payload.update(overrides)
    return EngineDLogEntry(**payload)
class EngineDRuntime:
    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        reentry_validation_hook: EngineDReentryValidationHook | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineDRuntime requires a circuit_breaker")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._reentry_validation_hook = reentry_validation_hook

    def evaluate(
        self,
        runtime_input: EngineDRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineDRuntimeResult:
        timestamp = resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineDRuntime.evaluate")
        require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineDRuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker)

        engine_output = run_engine_d(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)
        if engine_output.decision != EngineDDecision.EMIT:
            return _build_runtime_result(
                status=EngineDRuntimeStatus.NO_TRADE,
                engine_output=engine_output,
                logs=logs,
            )

        hook_outcome = self._run_reentry_validation_hook(runtime_input, engine_output)
        if hook_outcome is not None and not hook_outcome.accepted:
            return _build_hook_blocked_runtime_result(
                runtime_input,
                engine_output,
                logs,
                hook_outcome=hook_outcome,
            )

        scoring_state = self._build_scoring_state(
            runtime_input,
            engine_output,
            logs,
            timestamp=timestamp,
        )
        if scoring_state.scoring_audit is None:
            return _build_missing_scoring_audit_runtime_result(
                engine_output,
                logs,
                scoring_state=scoring_state,
                hook_outcome=hook_outcome,
            )
        if scoring_state.scoring_audit.hard_block_decision.is_blocked:
            return _build_hard_blocked_runtime_result(
                runtime_input,
                engine_output,
                logs,
                scoring_state=scoring_state,
                hook_outcome=hook_outcome,
            )

        selection_entry = _require_selection_entry(scoring_state.scoring_audit)
        selection_result = _build_selection_rejected_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            selection_entry=selection_entry,
            hook_outcome=hook_outcome,
        )
        if selection_result is not None:
            return selection_result

        risk_evaluation = self._evaluate_risk(
            runtime_input,
            engine_output,
            scoring_state,
            timestamp=timestamp,
        )
        risk_result = _build_risk_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            risk_evaluation=risk_evaluation,
            hook_outcome=hook_outcome,
        )
        if risk_result is not None:
            return risk_result

        return _build_accepted_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            risk_evaluation=risk_evaluation,
            hook_outcome=hook_outcome,
        )

    def _build_scoring_state(
        self,
        runtime_input: EngineDRuntimeInput,
        engine_output: EngineDOutput,
        logs: list[EngineDLogEntry],
        *,
        timestamp: float,
    ) -> _EngineDScoringState:
        signal_candidate = _build_signal_candidate(
            runtime_input.engine_inputs,
            engine_output,
            runtime_input.timestamp_ms,
        )
        scoring_round = self._scoring_runtime.run_round(
            candidates=(_build_scoring_candidate(runtime_input, engine_output), *runtime_input.peer_candidates),
            portfolio=runtime_input.portfolio,
            max_selections=runtime_input.max_selections,
            now=timestamp,
        )
        scoring_audit = resolve_scoring_audit(
            scoring_round,
            engine_id="engine_d",
            pair=engine_output.pair,
        )
        if scoring_audit is None:
            _append_runtime_log(
                logs,
                runtime_input,
                engine_output,
                event="engine_d_scoring_audit_missing",
                reasons=("scoring audit not found for engine_d - hard blocked",),
            )
            return _EngineDScoringState(
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=None,
                penalized_score=0.0,
            )

        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_d_scoring_completed",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=penalized_score,
            reasons=tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties),
        )
        return _EngineDScoringState(
            signal_candidate=signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            penalized_score=penalized_score,
        )

    def _evaluate_risk(
        self,
        runtime_input: EngineDRuntimeInput,
        engine_output: EngineDOutput,
        scoring_state: _EngineDScoringState,
        *,
        timestamp: float,
    ) -> RiskEvaluation:
        scoring_audit = scoring_state.scoring_audit
        if scoring_audit is None:
            raise ValueError("Engine D scoring state is missing its scoring audit")
        size_multiplier = scoring_audit.penalty_cap_result.capped_size_multiplier
        planned_loss = runtime_input.projected_loss
        if planned_loss is not None:
            planned_loss *= size_multiplier
        self._risk_runtime.set_equity(
            current_equity=runtime_input.current_equity,
            session_peak_equity=runtime_input.session_peak_equity,
        )
        return self._risk_runtime.evaluate_candidate(
            RiskCandidate(
                pair=engine_output.pair,
                engine_id="engine_d",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=timestamp,
        )

    def _run_reentry_validation_hook(
        self,
        runtime_input: EngineDRuntimeInput,
        engine_output: EngineDOutput,
    ) -> EngineDReentryValidationOutcome | None:
        if self._reentry_validation_hook is None:
            return None
        return self._reentry_validation_hook(
            EngineDReentryValidationInput(
                context_id=engine_output.origin_context_id,
                trade_id=engine_output.origin_trade_id,
                pair=engine_output.pair,
                engine_id=engine_output.engine_id,
                scoring_version=engine_output.scoring_version,
                link_type=engine_output.link_type,
                structure_reformed_detected=engine_output.structure_reformed_detected,
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                expected_cost=engine_output.expected_cost,
                expected_ce=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                first_episode_id=engine_output.first_episode_id,
                first_episode_engine_id=engine_output.first_episode_engine_id,
                first_episode_close_reason=engine_output.first_episode_close_reason,
                consecutive_stop_count=engine_output.consecutive_stop_count,
                last_stop_at_ns=engine_output.last_stop_at_ns,
                last_fresh_a_detection_at_ns=engine_output.last_fresh_a_detection_at_ns,
                anti_revenge_state=engine_output.anti_revenge_state,
            )
        )
def _append_runtime_log(
    logs: list[EngineDLogEntry],
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    *,
    event: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        _runtime_log_entry(
            runtime_input,
            engine_output,
            event=event,
            raw_score=raw_score,
            penalized_score=penalized_score,
            reasons=reasons,
        )
    )
def _build_runtime_result(
    *,
    status: EngineDRuntimeStatus,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    signal_candidate: SignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
) -> EngineDRuntimeResult:
    return EngineDRuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
        log_entries=tuple(logs),
    )
def _build_hook_blocked_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    hook_outcome: EngineDReentryValidationOutcome,
) -> EngineDRuntimeResult:
    detail = hook_outcome.detail.strip()
    if not detail:
        detail = (
            "compiled engine_d re-entry validation blocked "
            f"{engine_output.pair} / {engine_output.engine_id}"
        )
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_d_hook_blocked",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=hook_outcome.reason_codes or (detail,),
    )
    return _build_runtime_result(
        status=EngineDRuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        hook_outcome=hook_outcome,
    )
def _build_missing_scoring_audit_runtime_result(
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
) -> EngineDRuntimeResult:
    return _build_runtime_result(
        status=EngineDRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        scoring_round=scoring_state.scoring_round,
        hook_outcome=hook_outcome,
    )
def _build_hard_blocked_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        hook_outcome=hook_outcome,
    )
def _require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine D scoring audit is missing its selection entry")
    return selection_entry
def _build_selection_rejected_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    selection_entry: SelectionEntry,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
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
            scoring_round=scoring_state.scoring_round,
            scoring_audit=scoring_audit,
            hook_outcome=hook_outcome,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        hook_outcome=hook_outcome,
    )
def _build_risk_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    risk_evaluation: RiskEvaluation,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
) -> EngineDRuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D risk evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_d_risk_rejected",
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
    )
def _build_accepted_runtime_result(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    *,
    scoring_state: _EngineDScoringState,
    risk_evaluation: RiskEvaluation,
    hook_outcome: EngineDReentryValidationOutcome | None = None,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        hook_outcome=hook_outcome,
    )
def _build_circuit_breaker_blocked_result(
    runtime_input: EngineDRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineDRuntimeResult:
    reason = circuit_breaker.current_reason.value
    log_entry = EngineDLogEntry(
        event="engine_d_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        origin_context_id=runtime_input.engine_inputs.origin_context_id,
        origin_trade_id=runtime_input.engine_inputs.origin_trade_id,
        link_type=runtime_input.engine_inputs.link_type,
        structure_reformed_detected=runtime_input.engine_inputs.structure_reformed_detected,
        reasons=(f"emergency circuit breaker tripped: {reason}",),
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
def _build_scoring_candidate(runtime_input: EngineDRuntimeInput, engine_output: EngineDOutput) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id="engine_d",
        pair=engine_output.pair,
        raw_features={key: engine_output.block_scores.get(key, 0.0) for key in _ENGINE_D_FEATURE_WEIGHTS},
        allowed_features=frozenset(_ENGINE_D_FEATURE_WEIGHTS),
        weights=dict(_ENGINE_D_FEATURE_WEIGHTS),
        scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version,
        score_penalties=runtime_input.score_penalties,
        size_penalties=runtime_input.size_penalties,
        blocker_conditions=runtime_input.blocker_conditions,
        expected_cost=engine_output.expected_cost,
        expected_ce=engine_output.ce_expected,
        projected_size=runtime_input.projected_size,
        projected_loss=0.0 if runtime_input.projected_loss is None else runtime_input.projected_loss,
        projected_beta_impact=0.0 if runtime_input.pair_beta is None else runtime_input.pair_beta * runtime_input.projected_size,
        cluster_id=runtime_input.cluster_id,
        corr_penalty=runtime_input.corr_penalty,
        risk_penalty=runtime_input.risk_penalty,
    )
def _build_signal_candidate(inputs: EngineDInput, engine_output: EngineDOutput, timestamp_ms: int) -> SignalCandidate:
    max_hold_ms = None
    if engine_output.holding_hours > 0:
        max_hold_ms = int(engine_output.holding_hours * 3600 * 1000)
    return SignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.D,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.penalized_score)),
        regime=to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=engine_output.invalidation.stop_price if engine_output.invalidation is not None else None,
        take_profit=engine_output.invalidation.target_price if engine_output.invalidation is not None else None,
        max_hold_ms=max_hold_ms,
        reason=(
            f"engine_d:{engine_output.conviction.value}:{engine_output.link_type}:"
            f"{engine_output.origin_trade_id or engine_output.origin_context_id}"
        ),
    )
