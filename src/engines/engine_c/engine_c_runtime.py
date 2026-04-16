"""Engine C runtime across signal, scoring, ranking and risk."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Protocol

from pydantic import BaseModel, Field

from interface_contracts import (
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
    EngineId,
    RegimeId,
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

from .engine_c_runner import EngineCDecision, EngineCInput, EngineCLogEntry, EngineCOutput, run_engine_c


_ENGINE_C_FEATURE_WEIGHTS: dict[str, float] = {
    "breakout": 0.35,
    "continuation": 0.30,
    "context": 0.15,
    "cost_preference": 0.20,
}
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
    peer_candidates: tuple[ScoringCandidateInput, ...] = ()
    max_selections: int = 1
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
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
    signal_candidate: SignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    log_entries: tuple[EngineCLogEntry, ...] = ()
@dataclass(frozen=True)
class _EngineCScoringState:
    signal_candidate: SignalCandidate
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit | None
    penalized_score: float
def _runtime_log_entry(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    **overrides: object,
) -> EngineCLogEntry:
    payload: dict[str, object] = {
        "pair": engine_output.pair,
        "regime": runtime_input.engine_inputs.regime,
        "range_low": engine_output.range_low,
        "range_high": engine_output.range_high,
        "range_width_pct": engine_output.range_width_pct,
        "breakout_type": engine_output.breakout_type,
        "continuation_context": engine_output.continuation_context,
        "distance_to_breakout_pct": engine_output.distance_to_breakout_pct,
        "breakout_score": engine_output.breakout_score,
        "continuation_score": engine_output.continuation_score,
        "cumulative_ofi": engine_output.cumulative_ofi,
        "queue_pressure": engine_output.queue_pressure,
        "vpin": engine_output.vpin,
        "kyle_lambda": engine_output.kyle_lambda,
        "microstructure_gate_applied": engine_output.microstructure_gate_applied,
        "fake_breakout_risk": engine_output.fake_breakout_risk,
        "expected_cost": engine_output.expected_cost,
        "ce_expected": engine_output.ce_expected,
        "ev_net": engine_output.ev_net,
        "duplication_possible_with_engine_a": engine_output.duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": engine_output.duplication_overlap_with_engine_a,
        "marginal_portfolio_gain": engine_output.marginal_portfolio_gain,
        "covered_share_by_engine_a": engine_output.covered_share_by_engine_a,
        "keff_contribution": engine_output.keff_contribution,
        "conviction": engine_output.conviction.value,
        "tier": engine_output.tier_suggestion.value,
        "holding_hours": engine_output.holding_hours,
        "scoring_version": engine_output.scoring_version,
    }
    payload.update(overrides)
    return EngineCLogEntry(**payload)
class EngineCRuntime:
    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        void_validation_hook: EngineCVoidValidationHook | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineCRuntime requires a circuit_breaker")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._void_validation_hook = void_validation_hook

    def evaluate(
        self,
        runtime_input: EngineCRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineCRuntimeResult:
        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineCRuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineCRuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker)

        engine_output = run_engine_c(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)
        if engine_output.decision != EngineCDecision.EMIT:
            return _build_runtime_result(
                status=EngineCRuntimeStatus.NO_TRADE,
                engine_output=engine_output,
                logs=logs,
            )

        hook_outcome = self._run_void_validation_hook(runtime_input, engine_output)
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
            )
        if scoring_state.scoring_audit.hard_block_decision.is_blocked:
            return _build_hard_blocked_runtime_result(
                runtime_input,
                engine_output,
                logs,
                scoring_state=scoring_state,
            )

        selection_entry = _require_selection_entry(scoring_state.scoring_audit)
        selection_result = _build_selection_rejected_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            selection_entry=selection_entry,
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
        )
        if risk_result is not None:
            return risk_result

        return _build_accepted_runtime_result(
            runtime_input,
            engine_output,
            logs,
            scoring_state=scoring_state,
            risk_evaluation=risk_evaluation,
        )

    def _build_scoring_state(
        self,
        runtime_input: EngineCRuntimeInput,
        engine_output: EngineCOutput,
        logs: list[EngineCLogEntry],
        *,
        timestamp: float,
    ) -> _EngineCScoringState:
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
        scoring_audit = _resolve_scoring_audit(
            scoring_round,
            engine_id="engine_c",
            pair=engine_output.pair,
        )
        if scoring_audit is None:
            _append_runtime_log(
                logs,
                runtime_input,
                engine_output,
                event="engine_c_scoring_audit_missing",
                reasons=("scoring audit not found for engine_c - hard blocked",),
            )
            return _EngineCScoringState(
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
            event="engine_c_scoring_completed",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=penalized_score,
            reasons=tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties),
        )
        return _EngineCScoringState(
            signal_candidate=signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            penalized_score=penalized_score,
        )

    def _evaluate_risk(
        self,
        runtime_input: EngineCRuntimeInput,
        engine_output: EngineCOutput,
        scoring_state: _EngineCScoringState,
        *,
        timestamp: float,
    ) -> RiskEvaluation:
        scoring_audit = scoring_state.scoring_audit
        if scoring_audit is None:
            raise ValueError("Engine C scoring state is missing its scoring audit")
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
                engine_id="engine_c",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=timestamp,
        )

    def _run_void_validation_hook(
        self,
        runtime_input: EngineCRuntimeInput,
        engine_output: EngineCOutput,
    ) -> EngineCVoidValidationOutcome | None:
        if self._void_validation_hook is None:
            return None
        return self._void_validation_hook(
            EngineCVoidValidationInput(
                context_id=(
                    f"{engine_output.pair}:{runtime_input.timestamp_ms}:"
                    f"{engine_output.engine_id}:{engine_output.scoring_version}"
                ),
                pair=engine_output.pair,
                engine_id=engine_output.engine_id,
                scoring_version=engine_output.scoring_version,
                breakout_type=engine_output.breakout_type,
                continuation_context=engine_output.continuation_context,
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                expected_cost=engine_output.expected_cost,
                expected_ce=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
            )
        )
def _append_runtime_log(
    logs: list[EngineCLogEntry],
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
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
    status: EngineCRuntimeStatus,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    signal_candidate: SignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
) -> EngineCRuntimeResult:
    return EngineCRuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        log_entries=tuple(logs),
    )
def _build_hook_blocked_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    hook_outcome: EngineCVoidValidationOutcome,
) -> EngineCRuntimeResult:
    detail = hook_outcome.detail.strip()
    if not detail:
        detail = (
            "compiled engine_c void validation blocked "
            f"{engine_output.pair} / {engine_output.engine_id}"
        )
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_hook_blocked",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=hook_outcome.reason_codes or (detail,),
    )
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
    )
def _build_missing_scoring_audit_runtime_result(
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
) -> EngineCRuntimeResult:
    return _build_runtime_result(
        status=EngineCRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        scoring_round=scoring_state.scoring_round,
    )
def _build_hard_blocked_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
    )
def _require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine C scoring audit is missing its selection entry")
    return selection_entry
def _build_selection_rejected_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    selection_entry: SelectionEntry,
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
            scoring_round=scoring_state.scoring_round,
            scoring_audit=scoring_audit,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
    )
def _build_risk_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    risk_evaluation: RiskEvaluation,
) -> EngineCRuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C risk evaluation requires a scoring audit")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_c_risk_rejected",
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
    )
def _build_accepted_runtime_result(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    *,
    scoring_state: _EngineCScoringState,
    risk_evaluation: RiskEvaluation,
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
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
    )
def _build_circuit_breaker_blocked_result(
    runtime_input: EngineCRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineCRuntimeResult:
    reason = circuit_breaker.current_reason.value
    log_entry = EngineCLogEntry(
        event="engine_c_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        reasons=(f"emergency circuit breaker tripped: {reason}",),
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
def _build_scoring_candidate(runtime_input: EngineCRuntimeInput, engine_output: EngineCOutput) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id="engine_c",
        pair=engine_output.pair,
        raw_features={key: engine_output.block_scores.get(key, 0.0) for key in _ENGINE_C_FEATURE_WEIGHTS},
        allowed_features=frozenset(_ENGINE_C_FEATURE_WEIGHTS),
        weights=dict(_ENGINE_C_FEATURE_WEIGHTS),
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
def _resolve_runtime_now(timestamp_ms: int, now: float | None, *, context: str) -> float:
    """Resolve an audit timestamp from the explicit arg or the governed input."""

    if now is None:
        if timestamp_ms <= 0:
            raise ValueError(f"{context} requires timestamp_ms > 0 when now is omitted")
        return timestamp_ms / 1000.0
    if not math.isfinite(now):
        raise ValueError(f"{context} requires finite now")
    if now <= 0.0:
        raise ValueError(f"{context} requires now > 0")
    return now
def _require_scoring_version(scoring_version: str, *, context: str) -> str:
    """Reject empty audit versions on the open engine runtime rail."""

    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized
def _resolve_scoring_audit(
    scoring_round: ScoringRoundResult,
    *,
    engine_id: str,
    pair: str,
) -> ScoringCandidateAudit | None:
    for audit in scoring_round.audits:
        if audit.engine_id == engine_id and audit.pair == pair:
            return audit
    return None
def _build_signal_candidate(inputs: EngineCInput, engine_output: EngineCOutput, timestamp_ms: int) -> SignalCandidate:
    max_hold_ms = None
    if engine_output.holding_hours > 0:
        max_hold_ms = int(engine_output.holding_hours * 3600 * 1000)
    return SignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.C,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.penalized_score)),
        regime=_to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=engine_output.invalidation.stop_price if engine_output.invalidation is not None else None,
        take_profit=engine_output.invalidation.target_price if engine_output.invalidation is not None else None,
        max_hold_ms=max_hold_ms,
        reason=f"engine_c:{engine_output.conviction.value}:{engine_output.breakout_type or 'breakout'}",
    )
def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    mapping = {
        "breakout": RegimeId.BREAKOUT,
        "trending_up": RegimeId.TRENDING_UP,
        "trending_down": RegimeId.TRENDING_DOWN,
        "range": RegimeId.RANGE_BOUND,
        "range_bound": RegimeId.RANGE_BOUND,
        "high_volatility": RegimeId.HIGH_VOLATILITY,
        "low_volatility": RegimeId.LOW_VOLATILITY,
    }
    return mapping.get(normalized, RegimeId.UNKNOWN)
