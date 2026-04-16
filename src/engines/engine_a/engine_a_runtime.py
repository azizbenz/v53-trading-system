"""
Build-6 / engine_a / engine_a_runtime
Real Engine A runtime path across signal emission, scoring, ranking and risk.

This module closes the canonical Build-6 path without bypassing the V5.3
layering:
- Engine A emits a canonical SignalCandidate
- scoring_backbone evaluates hard/soft/rank
- risk_backbone applies the real portfolio guards

Execution remains handled by Build-3 and is intentionally not imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from interface_contracts import (
    EngineId,
    ForecastSignalCandidate,
    SignalCandidate as DecisionSignalCandidate,
    Side,
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

from .engine_a_runner import (
    EngineADecision,
    EngineAInput,
    EngineALogEntry,
    EngineAOutput,
    run_engine_a,
)
from .engine_a_runtime_support import (
    _build_forecast_signal_candidate,
    _build_signal_candidate,
    _require_scoring_version,
    _resolve_runtime_now,
    _resolve_scoring_audit,
)
from .conviction_builder_a import ENGINE_A_CONVICTION_FEATURE_WEIGHTS


class EngineARuntimeStatus(StrEnum):
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


class EngineARuntimeInput(BaseModel, frozen=True):
    """Inputs required to run Engine A through Build-5 and Build-4."""

    engine_inputs: EngineAInput
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


class EngineAPreEntryValidationInput(BaseModel, frozen=True):
    """Bounded typed input for the Engine A pre-entry confirmation hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    raw_score: float = 0.0
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    conviction: str = ""
    tier: str = ""
    structure_verdict: str = ""
    context_verdict: str = ""
    cost_verdict: str = ""


class EngineAPreEntryValidationOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded Engine A pre-entry hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineAPreEntryValidationHook(Protocol):
    """Bounded hook surface injected into the real Engine A runtime rail."""

    def __call__(
        self,
        hook_input: EngineAPreEntryValidationInput,
    ) -> EngineAPreEntryValidationOutcome:
        ...


class EngineARuntimeResult(BaseModel, frozen=True):
    """Full Build-6 runtime result with audit-ready stage outputs."""

    status: EngineARuntimeStatus
    engine_output: EngineAOutput
    signal_candidate: DecisionSignalCandidate | None = None
    forecast_signal_candidate: ForecastSignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    log_entries: tuple[EngineALogEntry, ...] = ()


@dataclass(frozen=True)
class _EngineAScoringState:
    signal_candidate: DecisionSignalCandidate
    forecast_signal_candidate: ForecastSignalCandidate | None
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit
    penalized_score: float


class EngineARuntime:
    """Real Build-6 runtime across signal, score/rank and risk."""

    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        pre_entry_validation_hook: EngineAPreEntryValidationHook | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineARuntime requires a circuit_breaker")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._pre_entry_validation_hook = pre_entry_validation_hook

    def evaluate(
        self,
        runtime_input: EngineARuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineARuntimeResult:
        """Evaluate Engine A through the canonical Build-6 path."""
        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineARuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineARuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker)
        engine_output = run_engine_a(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)

        if engine_output.decision != EngineADecision.EMIT:
            return _build_runtime_result(
                status=EngineARuntimeStatus.NO_TRADE,
                engine_output=engine_output,
                logs=logs,
            )

        hook_outcome = self._run_pre_entry_validation_hook(runtime_input, engine_output)
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
        runtime_input: EngineARuntimeInput,
        engine_output: EngineAOutput,
        logs: list[EngineALogEntry],
        *,
        timestamp: float,
    ) -> _EngineAScoringState:
        signal_candidate = _build_signal_candidate(
            runtime_input.engine_inputs,
            engine_output,
            runtime_input.timestamp_ms,
        )
        engine_candidate = _build_scoring_candidate(runtime_input, engine_output)
        scoring_round = self._scoring_runtime.run_round(
            candidates=(engine_candidate, *runtime_input.peer_candidates),
            portfolio=runtime_input.portfolio,
            max_selections=runtime_input.max_selections,
            now=timestamp,
        )
        scoring_audit = _resolve_scoring_audit(
            scoring_round,
            engine_id="engine_a",
            pair=engine_output.pair,
            context="EngineARuntime.evaluate",
        )
        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score
            - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_a_scoring_completed",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=penalized_score,
            reasons=tuple(
                item.penalty_id for item in scoring_audit.score_penalty_result.penalties
            ),
        )
        return _EngineAScoringState(
            signal_candidate=signal_candidate,
            forecast_signal_candidate=_build_forecast_signal_candidate(
                strategy_id=runtime_input.strategy_id,
                timestamp_ms=runtime_input.timestamp_ms,
                engine_inputs=runtime_input.engine_inputs,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_audit=scoring_audit,
            ),
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            penalized_score=penalized_score,
        )

    def _evaluate_risk(
        self,
        runtime_input: EngineARuntimeInput,
        engine_output: EngineAOutput,
        scoring_state: _EngineAScoringState,
        *,
        timestamp: float,
    ) -> RiskEvaluation:
        size_multiplier = scoring_state.scoring_audit.penalty_cap_result.capped_size_multiplier
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
                engine_id="engine_a",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=timestamp,
        )

    def _run_pre_entry_validation_hook(
        self,
        runtime_input: EngineARuntimeInput,
        engine_output: EngineAOutput,
    ) -> EngineAPreEntryValidationOutcome | None:
        if self._pre_entry_validation_hook is None:
            return None
        return self._pre_entry_validation_hook(
            EngineAPreEntryValidationInput(
                context_id=(
                    f"{engine_output.pair}:{runtime_input.timestamp_ms}:"
                    f"{engine_output.engine_id}:{engine_output.scoring_version}"
                ),
                pair=engine_output.pair,
                engine_id=engine_output.engine_id,
                scoring_version=engine_output.scoring_version,
                raw_score=engine_output.raw_score,
                expected_cost=engine_output.expected_cost,
                expected_ce=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                structure_verdict=engine_output.structure_verdict.value,
                context_verdict=engine_output.context_verdict.value,
                cost_verdict=engine_output.cost_verdict.value,
            )
        )


def _append_runtime_log(
    logs: list[EngineALogEntry],
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    *,
    event: str,
    raw_score: float,
    penalized_score: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        EngineALogEntry(
            event=event,
            pair=engine_output.pair,
            regime=runtime_input.engine_inputs.regime,
            raw_score=raw_score,
            penalized_score=penalized_score,
            block_scores=engine_output.block_scores,
            expected_cost=engine_output.expected_cost,
            ce_expected=engine_output.ce_expected,
            conviction=engine_output.conviction.value,
            tier=engine_output.tier_suggestion.value,
            reasons=reasons,
            scoring_version=engine_output.scoring_version,
        )
    )


def _build_runtime_result(
    *,
    status: EngineARuntimeStatus,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    signal_candidate: DecisionSignalCandidate | None = None,
    forecast_signal_candidate: ForecastSignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
) -> EngineARuntimeResult:
    return EngineARuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        forecast_signal_candidate=forecast_signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        log_entries=tuple(logs),
    )


def _build_hook_blocked_runtime_result(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    *,
    hook_outcome: EngineAPreEntryValidationOutcome,
) -> EngineARuntimeResult:
    detail = hook_outcome.detail.strip()
    if not detail:
        detail = (
            "compiled engine_a pre-entry confirmation blocked "
            f"{engine_output.pair} / {engine_output.engine_id}"
        )
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_a_hook_blocked",
        raw_score=engine_output.raw_score,
        reasons=hook_outcome.reason_codes or (detail,),
    )
    return _build_runtime_result(
        status=EngineARuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
    )


def _build_hard_blocked_runtime_result(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    *,
    scoring_state: _EngineAScoringState,
) -> EngineARuntimeResult:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_a_hard_blocked",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=tuple(
            reason.human_reason
            for reason in scoring_state.scoring_audit.hard_block_decision.reasons
        ),
    )
    return _build_runtime_result(
        status=EngineARuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
    )


def _require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine A scoring audit is missing its selection entry")
    return selection_entry


def _build_selection_rejected_runtime_result(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    *,
    scoring_state: _EngineAScoringState,
    selection_entry: SelectionEntry,
) -> EngineARuntimeResult | None:
    if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_a_rejected_by_ranking",
            raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
            penalized_score=scoring_state.penalized_score,
            reasons=(selection_entry.rejection_reason,),
        )
        return _build_runtime_result(
            status=EngineARuntimeStatus.REJECTED_RANKING,
            engine_output=engine_output,
            logs=logs,
            signal_candidate=scoring_state.signal_candidate,
            forecast_signal_candidate=scoring_state.forecast_signal_candidate,
            scoring_round=scoring_state.scoring_round,
            scoring_audit=scoring_state.scoring_audit,
        )
    if selection_entry.outcome != SelectionOutcome.REJECTED_PORTFOLIO:
        return None
    portfolio_reason = selection_entry.rejection_reason
    portfolio_result = scoring_state.scoring_audit.portfolio_result
    if portfolio_result is not None and portfolio_result.reason:
        portfolio_reason = portfolio_result.reason
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_a_rejected_by_portfolio",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=(portfolio_reason,),
    )
    return _build_runtime_result(
        status=EngineARuntimeStatus.REJECTED_PORTFOLIO,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
    )


def _build_risk_runtime_result(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    *,
    scoring_state: _EngineAScoringState,
    risk_evaluation: RiskEvaluation,
) -> EngineARuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_a_risk_rejected",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=risk_evaluation.reasons or ("risk runtime rejected candidate",),
    )
    status = {
        RiskRuntimeAction.REJECT: EngineARuntimeStatus.RISK_REJECTED,
        RiskRuntimeAction.REDUCE_EXPOSURE: EngineARuntimeStatus.RISK_REDUCED,
        RiskRuntimeAction.OBSERVE_ONLY: EngineARuntimeStatus.RISK_OBSERVE_ONLY,
    }.get(risk_evaluation.action, EngineARuntimeStatus.RISK_REJECTED)
    return _build_runtime_result(
        status=status,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
        risk_evaluation=risk_evaluation,
    )


def _build_accepted_runtime_result(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
    logs: list[EngineALogEntry],
    *,
    scoring_state: _EngineAScoringState,
    risk_evaluation: RiskEvaluation,
) -> EngineARuntimeResult:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_a_accepted",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
    )
    return _build_runtime_result(
        status=EngineARuntimeStatus.ACCEPTED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
        risk_evaluation=risk_evaluation,
    )


def _build_circuit_breaker_blocked_result(
    runtime_input: EngineARuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineARuntimeResult:
    reason = circuit_breaker.current_reason.value
    log_entry = EngineALogEntry(
        event="engine_a_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        reasons=(f"emergency circuit breaker tripped: {reason}",),
        scoring_version=runtime_input.engine_inputs.scoring_version,
    )
    engine_output = EngineAOutput(
        pair=runtime_input.engine_inputs.pair,
        decision=EngineADecision.NO_TRADE,
        scoring_version=runtime_input.engine_inputs.scoring_version,
        log_entries=(log_entry,),
    )
    return EngineARuntimeResult(
        status=EngineARuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        engine_output=engine_output,
        log_entries=(log_entry,),
    )


def _build_scoring_candidate(runtime_input: EngineARuntimeInput, engine_output: EngineAOutput) -> ScoringCandidateInput:
    raw_features = {
        key: engine_output.block_scores.get(key, 0.0)
        for key in ENGINE_A_CONVICTION_FEATURE_WEIGHTS
    }
    return ScoringCandidateInput(
        engine_id="engine_a",
        pair=engine_output.pair,
        raw_features=raw_features,
        allowed_features=frozenset(ENGINE_A_CONVICTION_FEATURE_WEIGHTS),
        weights=dict(ENGINE_A_CONVICTION_FEATURE_WEIGHTS),
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
