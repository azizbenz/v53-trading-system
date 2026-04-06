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

from enum import StrEnum
import math

from pydantic import BaseModel, Field

from interface_contracts import EngineId, RegimeId, Side, SignalCandidate, SignalType
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntime, RiskRuntimeAction
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.selection_resolver import SelectionOutcome
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


_ENGINE_A_FEATURE_WEIGHTS: dict[str, float] = {
    "structure": 0.40,
    "context": 0.25,
    "flow": 0.15,
    "cost_preference": 0.20,
}


class EngineARuntimeStatus(StrEnum):
    NO_TRADE = "no_trade"
    CIRCUIT_BREAKER_BLOCKED = "circuit_breaker_blocked"
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
    timestamp_ms: int
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


class EngineARuntimeResult(BaseModel, frozen=True):
    """Full Build-6 runtime result with audit-ready stage outputs."""

    status: EngineARuntimeStatus
    engine_output: EngineAOutput
    signal_candidate: SignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    log_entries: tuple[EngineALogEntry, ...] = ()


class EngineARuntime:
    """Real Build-6 runtime across signal, score/rank and risk."""

    def __init__(
        self,
        *,
        scoring_runtime: ScoringRuntime,
        risk_runtime: RiskRuntime,
        circuit_breaker: EmergencyCircuitBreaker | None = None,
    ) -> None:
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime
        self._circuit_breaker = circuit_breaker

    def evaluate(
        self,
        runtime_input: EngineARuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineARuntimeResult:
        """Evaluate Engine A through the canonical Build-6 path."""
        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineARuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineARuntime.evaluate")
        if self._circuit_breaker is not None and not self._circuit_breaker.is_trading_allowed():
            return _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker)
        engine_output = run_engine_a(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)

        if engine_output.decision != "emit":
            return EngineARuntimeResult(
                status=EngineARuntimeStatus.NO_TRADE,
                engine_output=engine_output,
                log_entries=tuple(logs),
            )

        signal_candidate = _build_signal_candidate(runtime_input.engine_inputs, engine_output, runtime_input.timestamp_ms)

        engine_candidate = _build_scoring_candidate(runtime_input, engine_output)
        scoring_round = self._scoring_runtime.run_round(
            candidates=(engine_candidate, *runtime_input.peer_candidates),
            portfolio=runtime_input.portfolio,
            max_selections=runtime_input.max_selections,
            now=timestamp,
        )
        scoring_audit = next(
            audit
            for audit in scoring_round.audits
            if audit.engine_id == "engine_a" and audit.pair == engine_output.pair
        )

        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        penalty_reasons = tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties)
        logs.append(
            EngineALogEntry(
                event="engine_a_scoring_completed",
                pair=engine_output.pair,
                regime=runtime_input.engine_inputs.regime,
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
                block_scores=engine_output.block_scores,
                expected_cost=engine_output.expected_cost,
                ce_expected=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                reasons=penalty_reasons,
                scoring_version=engine_output.scoring_version,
            ),
        )

        if scoring_audit.hard_block_decision.is_blocked:
            reasons = tuple(reason.human_reason for reason in scoring_audit.hard_block_decision.reasons)
            logs.append(
                EngineALogEntry(
                    event="engine_a_hard_blocked",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    ce_expected=engine_output.ce_expected,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=reasons,
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineARuntimeResult(
                status=EngineARuntimeStatus.HARD_BLOCKED,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        selection_entry = scoring_audit.selection_entry
        if selection_entry is None:
            raise ValueError("Engine A scoring audit is missing its selection entry")

        if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
            logs.append(
                EngineALogEntry(
                    event="engine_a_rejected_by_ranking",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    ce_expected=engine_output.ce_expected,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=(selection_entry.rejection_reason,),
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineARuntimeResult(
                status=EngineARuntimeStatus.REJECTED_RANKING,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        if selection_entry.outcome == SelectionOutcome.REJECTED_PORTFOLIO:
            portfolio_reason = selection_entry.rejection_reason
            if scoring_audit.portfolio_result is not None and scoring_audit.portfolio_result.reason:
                portfolio_reason = scoring_audit.portfolio_result.reason
            logs.append(
                EngineALogEntry(
                    event="engine_a_rejected_by_portfolio",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    ce_expected=engine_output.ce_expected,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=(portfolio_reason,),
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineARuntimeResult(
                status=EngineARuntimeStatus.REJECTED_PORTFOLIO,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        size_multiplier = scoring_audit.penalty_cap_result.capped_size_multiplier
        planned_loss = runtime_input.projected_loss
        if planned_loss is not None:
            planned_loss *= size_multiplier
        self._risk_runtime.set_equity(
            current_equity=runtime_input.current_equity,
            session_peak_equity=runtime_input.session_peak_equity,
        )
        risk_evaluation = self._risk_runtime.evaluate_candidate(
            RiskCandidate(
                pair=engine_output.pair,
                engine_id="engine_a",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=timestamp,
        )

        if risk_evaluation.action != RiskRuntimeAction.ACCEPT:
            reasons = risk_evaluation.reasons or ("risk runtime rejected candidate",)
            logs.append(
                EngineALogEntry(
                    event="engine_a_risk_rejected",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    ce_expected=engine_output.ce_expected,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=reasons,
                    scoring_version=engine_output.scoring_version,
                ),
            )
            status = {
                RiskRuntimeAction.REJECT: EngineARuntimeStatus.RISK_REJECTED,
                RiskRuntimeAction.REDUCE_EXPOSURE: EngineARuntimeStatus.RISK_REDUCED,
                RiskRuntimeAction.OBSERVE_ONLY: EngineARuntimeStatus.RISK_OBSERVE_ONLY,
            }.get(risk_evaluation.action, EngineARuntimeStatus.RISK_REJECTED)
            return EngineARuntimeResult(
                status=status,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                risk_evaluation=risk_evaluation,
                log_entries=tuple(logs),
            )

        logs.append(
            EngineALogEntry(
                event="engine_a_accepted",
                pair=engine_output.pair,
                regime=runtime_input.engine_inputs.regime,
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
                block_scores=engine_output.block_scores,
                expected_cost=engine_output.expected_cost,
                ce_expected=engine_output.ce_expected,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                reasons=(),
                scoring_version=engine_output.scoring_version,
            ),
        )
        return EngineARuntimeResult(
            status=EngineARuntimeStatus.ACCEPTED,
            engine_output=engine_output,
            signal_candidate=signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
            log_entries=tuple(logs),
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
        for key in _ENGINE_A_FEATURE_WEIGHTS
    }
    return ScoringCandidateInput(
        engine_id="engine_a",
        pair=engine_output.pair,
        raw_features=raw_features,
        allowed_features=frozenset(_ENGINE_A_FEATURE_WEIGHTS),
        weights=dict(_ENGINE_A_FEATURE_WEIGHTS),
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


def _build_signal_candidate(inputs: EngineAInput, engine_output: EngineAOutput, timestamp_ms: int) -> SignalCandidate:
    stop_loss = None
    if engine_output.invalidation is not None:
        for rule in engine_output.invalidation.rules:
            if rule.level is not None:
                stop_loss = rule.level
                break

    take_profit = None
    if inputs.entry_price > 0 and inputs.expected_gain > 0:
        take_profit = inputs.entry_price * (1.0 + inputs.expected_gain)

    max_hold_ms = None
    if engine_output.holding_hours > 0:
        max_hold_ms = int(engine_output.holding_hours * 3600 * 1000)

    return SignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.A,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.raw_score)),
        regime=_to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        max_hold_ms=max_hold_ms,
        reason=f"engine_a:{engine_output.conviction.value}",
    )


def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    try:
        return RegimeId(normalized)
    except ValueError:
        return RegimeId.UNKNOWN
