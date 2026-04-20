"""
Build-7 / engine_b / engine_b_runtime
Real Engine B runtime path across signal emission, scoring, ranking and risk.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from interface_contracts import EngineId, ForecastSignalCandidate, SignalCandidate as DecisionSignalCandidate
from interface_contracts import RefusalCategory, RefusalRecord

from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskEvaluation, RiskRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringCandidateInput, ScoringRoundResult, ScoringRuntime

from .engine_b_runner import EngineBDecision, EngineBInput, EngineBLogEntry, EngineBOutput, run_engine_b

_BREAKOUT_WARNING_PENALTY_ID = "breakout_warning"


class _RefusalSink(Protocol):
    def record_refusal(self, record: RefusalRecord) -> None:
        ...


class EngineBRuntimeStatus(StrEnum):
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


class EngineBRuntimeInput(BaseModel, frozen=True):
    """Inputs required to run Engine B through Build-5 and Build-4."""

    engine_inputs: EngineBInput
    timestamp_ms: int = Field(..., ge=1_000_000_000_000)
    portfolio: PortfolioState
    projected_size: float = Field(gt=0.0)
    projected_loss: float | None = Field(default=None, ge=0.0)
    current_equity: float = Field(gt=0.0)
    session_peak_equity: float = Field(gt=0.0)
    pair_beta: float | None = None
    cluster_id: str
    score_penalties: tuple[ScorePenaltyItem, ...] = ()
    size_penalties: tuple[SizePenaltyItem, ...] = ()
    blocker_conditions: BlockerCondition = Field(default_factory=BlockerCondition)
    peer_candidates: tuple[ScoringCandidateInput, ...] = ()
    max_selections: int = Field(default=1, ge=1)
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


class EngineBSweepValidationInput(BaseModel, frozen=True):
    """Bounded typed input for the Engine B sweep-validation hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    raw_score: float = 0.0
    penalized_score: float = 0.0
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    conviction: str = ""
    tier: str = ""


class EngineBSweepValidationOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded Engine B sweep-validation hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    raw_score_multiplier_delta: float = 0.0
    raw_score_add: float = 0.0
    conviction_add: float = 0.0
    raw_score_cap: float | None = None


class EngineBSweepValidationHook(Protocol):
    """Bounded hook surface injected into the real Engine B runtime rail."""

    def __call__(
        self,
        hook_input: EngineBSweepValidationInput,
    ) -> EngineBSweepValidationOutcome:
        ...


class EngineBRuntimeResult(BaseModel, frozen=True):
    """Full Build-7 runtime result with audit-ready stage outputs."""

    status: EngineBRuntimeStatus
    engine_output: EngineBOutput
    signal_candidate: DecisionSignalCandidate | None = None
    forecast_signal_candidate: ForecastSignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    refusal_record: RefusalRecord | None = None
    log_entries: tuple[EngineBLogEntry, ...] = ()


from .engine_b_runtime_support import (
    _EngineBScoringState,
    _append_hook_adjustment_log,
    _build_accepted_runtime_result,
    _build_circuit_breaker_blocked_result,
    _build_forecast_signal_candidate,
    _build_hook_blocked_runtime_result,
    _build_hard_blocked_runtime_result,
    _build_risk_runtime_result,
    _build_scoring_candidate,
    _build_selection_rejected_runtime_result,
    _build_signal_candidate,
    _build_runtime_result,
    _hook_outcome_has_adjustment,
    _require_scoring_version,
    _require_selection_entry,
    _resolve_hook_score_adjustments,
    _resolve_runtime_economics_reason_codes,
    _resolve_runtime_now,
    _resolve_scoring_audit,
    _to_regime_id,
)
from interface_contracts.forecast_contracts import merge_reason_codes


class EngineBRuntime:
    """Real Build-7 runtime across signal, score/rank and risk."""

    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker,
        sweep_validation_hook: EngineBSweepValidationHook | None = None,
        refusal_sink: _RefusalSink | None = None,
    ) -> None:
        if circuit_breaker is None:
            raise ValueError("EngineBRuntime requires a circuit_breaker")
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker
        self._sweep_validation_hook = sweep_validation_hook
        self._refusal_sink = refusal_sink

    def evaluate(
        self,
        runtime_input: EngineBRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineBRuntimeResult:
        """Evaluate Engine B through the canonical Build-7 path."""

        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineBRuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineBRuntime.evaluate")
        if not self._circuit_breaker.is_trading_allowed():
            return self._finalize_runtime_result(
                runtime_input,
                _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker),
            )

        engine_output = run_engine_b(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)
        if engine_output.decision != EngineBDecision.EMIT:
            return self._finalize_runtime_result(
                runtime_input,
                _build_runtime_result(
                    status=EngineBRuntimeStatus.NO_TRADE,
                    engine_output=engine_output,
                    logs=logs,
                ),
            )

        hook_outcome = self._run_sweep_validation_hook(runtime_input, engine_output)
        if hook_outcome is not None and not hook_outcome.accepted:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hook_blocked_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                    hook_outcome=hook_outcome,
                ),
            )

        raw_score_multiplier, raw_score_add, raw_score_cap = _resolve_hook_score_adjustments(
            hook_outcome,
            context="EngineBRuntime.evaluate",
        )
        if hook_outcome is not None and _hook_outcome_has_adjustment(hook_outcome):
            _append_hook_adjustment_log(
                logs,
                runtime_input,
                engine_output,
                hook_outcome=hook_outcome,
                raw_score_multiplier=raw_score_multiplier,
                raw_score_add=raw_score_add,
                raw_score_cap=raw_score_cap,
            )

        scoring_state = self._build_scoring_state(
            runtime_input,
            engine_output,
            logs,
            timestamp=timestamp,
            raw_score_multiplier=raw_score_multiplier,
            raw_score_add=raw_score_add,
            raw_score_cap=raw_score_cap,
        )
        if scoring_state.scoring_audit.hard_block_decision.is_blocked:
            return self._finalize_runtime_result(
                runtime_input,
                _build_hard_blocked_runtime_result(
                    runtime_input,
                    engine_output,
                    logs,
                    scoring_state=scoring_state,
                ),
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
            return self._finalize_runtime_result(runtime_input, selection_result)

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
            return self._finalize_runtime_result(runtime_input, risk_result)

        return self._finalize_runtime_result(
            runtime_input,
            _build_accepted_runtime_result(
                runtime_input,
                engine_output,
                logs,
                scoring_state=scoring_state,
                risk_evaluation=risk_evaluation,
            ),
        )

    def _finalize_runtime_result(
        self,
        runtime_input: EngineBRuntimeInput,
        result: EngineBRuntimeResult,
    ) -> EngineBRuntimeResult:
        refusal_record = _build_runtime_refusal_record(runtime_input, result)
        if refusal_record is None:
            return result
        if self._refusal_sink is not None:
            self._refusal_sink.record_refusal(refusal_record)
        return result.model_copy(update={"refusal_record": refusal_record})

    def _build_scoring_state(
        self,
        runtime_input: EngineBRuntimeInput,
        engine_output: EngineBOutput,
        logs: list[EngineBLogEntry],
        *,
        timestamp: float,
        raw_score_multiplier: float,
        raw_score_add: float,
        raw_score_cap: float | None,
    ) -> _EngineBScoringState:
        signal_candidate = _build_signal_candidate(runtime_input.engine_inputs, engine_output, runtime_input.timestamp_ms)
        engine_candidate = _build_scoring_candidate(
            runtime_input,
            engine_output,
            raw_score_multiplier=raw_score_multiplier,
            raw_score_add=raw_score_add,
            raw_score_cap=raw_score_cap,
        )
        scoring_round = self._scoring_runtime.run_round(
            candidates=(engine_candidate, *runtime_input.peer_candidates),
            portfolio=runtime_input.portfolio,
            max_selections=runtime_input.max_selections,
            now=timestamp,
        )
        scoring_audit = _resolve_scoring_audit(
            scoring_round,
            engine_id="engine_b",
            pair=engine_output.pair,
            context="EngineBRuntime.evaluate",
        )
        return _EngineBScoringState.from_audit(
            runtime_input,
            engine_output,
            logs,
            signal_candidate=signal_candidate,
            forecast_signal_candidate=_build_forecast_signal_candidate(
                runtime_input,
                engine_output,
                signal_candidate,
                scoring_audit,
            ),
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
        )

    def _evaluate_risk(
        self,
        runtime_input: EngineBRuntimeInput,
        engine_output: EngineBOutput,
        scoring_state: _EngineBScoringState,
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
            scoring_state.build_risk_candidate(runtime_input, engine_output),
            now=timestamp,
        )

    def _run_sweep_validation_hook(
        self,
        runtime_input: EngineBRuntimeInput,
        engine_output: EngineBOutput,
    ) -> EngineBSweepValidationOutcome | None:
        if self._sweep_validation_hook is None:
            return None
        return self._sweep_validation_hook(
            EngineBSweepValidationInput(
                context_id=(
                    f"{engine_output.pair}:{runtime_input.timestamp_ms}:"
                    f"{engine_output.scoring_version or runtime_input.engine_inputs.scoring_version}"
                ),
                pair=engine_output.pair,
                engine_id=engine_output.engine_id,
                scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version,
                raw_score=engine_output.raw_score,
                penalized_score=engine_output.penalized_score,
                expected_cost=engine_output.expected_cost,
                expected_ce=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
            )
        )


def _build_runtime_refusal_record(
    runtime_input: EngineBRuntimeInput,
    result: EngineBRuntimeResult,
) -> RefusalRecord | None:
    category = _resolve_runtime_refusal_category(result.status)
    if category is None:
        return None
    return RefusalRecord(
        timestamp_ms=runtime_input.timestamp_ms,
        pair=result.engine_output.pair,
        engine_id=EngineId.B,
        category=category,
        reason_codes=_resolve_runtime_refusal_reason_codes(runtime_input, result),
    )


def _resolve_runtime_refusal_category(
    status: EngineBRuntimeStatus,
) -> RefusalCategory | None:
    if status == EngineBRuntimeStatus.NO_TRADE:
        return RefusalCategory.NO_TRADE
    if status in {
        EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        EngineBRuntimeStatus.HOOK_BLOCKED,
        EngineBRuntimeStatus.HARD_BLOCKED,
        EngineBRuntimeStatus.RISK_REJECTED,
    }:
        return RefusalCategory.HARD_BLOCK
    if status == EngineBRuntimeStatus.REJECTED_RANKING:
        return RefusalCategory.NO_TRADE
    if status == EngineBRuntimeStatus.REJECTED_PORTFOLIO:
        return RefusalCategory.PORTFOLIO_REJECTED
    return None


def _resolve_runtime_refusal_reason_codes(
    runtime_input: EngineBRuntimeInput,
    result: EngineBRuntimeResult,
) -> tuple[str, ...]:
    economics_reason_codes = _resolve_runtime_economics_reason_codes(
        runtime_input=runtime_input,
        engine_output=result.engine_output,
    )
    if result.status == EngineBRuntimeStatus.NO_TRADE:
        if result.engine_output.reason_codes:
            return merge_reason_codes(result.engine_output.reason_codes, economics_reason_codes)
        if result.engine_output.no_trade_reasons:
            return merge_reason_codes(
                (
                    f"engine_b.no_trade.{reason.value}"
                    for reason in result.engine_output.no_trade_reasons
                ),
                economics_reason_codes,
            )
        return merge_reason_codes(("engine_b.runtime.no_trade",), economics_reason_codes)
    if result.status == EngineBRuntimeStatus.HOOK_BLOCKED:
        hook_reason_codes = _extract_log_reason_codes(result.log_entries, "engine_b_hook_blocked")
        if hook_reason_codes:
            return merge_reason_codes(hook_reason_codes, economics_reason_codes)
        return merge_reason_codes(("engine_b.runtime.hook_blocked",), economics_reason_codes)
    if result.status == EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED:
        if result.engine_output.reason_codes:
            return merge_reason_codes(result.engine_output.reason_codes, economics_reason_codes)
        return merge_reason_codes(("engine_b.runtime.circuit_breaker_blocked",), economics_reason_codes)
    if result.status == EngineBRuntimeStatus.HARD_BLOCKED:
        if result.scoring_audit is not None and result.scoring_audit.hard_block_decision.reasons:
            return merge_reason_codes(
                (
                    reason.code
                    for reason in result.scoring_audit.hard_block_decision.reasons
                ),
                result.engine_output.reason_codes,
                economics_reason_codes,
            )
        return merge_reason_codes(
            result.engine_output.reason_codes,
            ("hard_block.engine_b.runtime.hard_blocked", "engine_b.runtime.hard_blocked"),
            economics_reason_codes,
        )
    if result.status == EngineBRuntimeStatus.REJECTED_RANKING:
        return merge_reason_codes(
            result.engine_output.reason_codes,
            ("scoring.engine_b.runtime.rejected_ranking", "engine_b.runtime.rejected_ranking"),
            economics_reason_codes,
        )
    if result.status == EngineBRuntimeStatus.REJECTED_PORTFOLIO:
        return merge_reason_codes(
            ("portfolio.engine_b.runtime.rejected_portfolio", "engine_b.runtime.rejected_portfolio"),
            economics_reason_codes,
        )
    if result.status == EngineBRuntimeStatus.RISK_REJECTED:
        if result.risk_evaluation is not None:
            if result.risk_evaluation.reason_details:
                return merge_reason_codes(
                    (
                        detail.code for detail in result.risk_evaluation.reason_details
                    ),
                    result.engine_output.reason_codes,
                    economics_reason_codes,
                )
            if result.risk_evaluation.dominant_reason_code:
                return merge_reason_codes(
                    (result.risk_evaluation.dominant_reason_code,),
                    result.engine_output.reason_codes,
                    economics_reason_codes,
                )
        return merge_reason_codes(
            result.engine_output.reason_codes,
            ("hard_block.engine_b.runtime.risk_rejected", "engine_b.runtime.risk_rejected"),
            economics_reason_codes,
        )
    return merge_reason_codes(("engine_b.runtime.unknown_refusal",), economics_reason_codes)


def _extract_log_reason_codes(
    log_entries: tuple[EngineBLogEntry, ...],
    event: str,
) -> tuple[str, ...]:
    for entry in reversed(log_entries):
        if entry.event != event:
            continue
        reason_codes = tuple(reason for reason in entry.reasons if reason.strip())
        if reason_codes:
            return reason_codes
    return ()


__all__ = [
    "EngineBRuntimeStatus",
    "EngineBRuntimeInput",
    "EngineBSweepValidationInput",
    "EngineBSweepValidationOutcome",
    "EngineBSweepValidationHook",
    "EngineBRuntimeResult",
    "EngineBRuntime",
]
