"""
Build-7 / engine_b / engine_b_runtime
Real Engine B runtime path across signal emission, scoring, ranking and risk.

This closes the canonical Build-7 path while respecting the V5.3 DAG:
- Engine B emits a canonical SignalCandidate
- scoring_backbone applies soft penalties, hard blocks and ranking
- risk_backbone applies portfolio risk gates
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

from .engine_b_runner import EngineBDecision, EngineBInput, EngineBLogEntry, EngineBOutput, run_engine_b


_ENGINE_B_FEATURE_WEIGHTS: dict[str, float] = {
    "excess": 0.35,
    "structure": 0.25,
    "context": 0.20,
    "cost_preference": 0.20,
}
_BREAKOUT_WARNING_PENALTY_ID = "breakout_warning"


class EngineBRuntimeStatus(StrEnum):
    NO_TRADE = "no_trade"
    CIRCUIT_BREAKER_BLOCKED = "circuit_breaker_blocked"
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


class EngineBRuntimeResult(BaseModel, frozen=True):
    """Full Build-7 runtime result with audit-ready stage outputs."""

    status: EngineBRuntimeStatus
    engine_output: EngineBOutput
    signal_candidate: SignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    log_entries: tuple[EngineBLogEntry, ...] = ()


class EngineBRuntime:
    """Real Build-7 runtime across signal, score/rank and risk."""

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
        runtime_input: EngineBRuntimeInput,
        *,
        now: float | None = None,
    ) -> EngineBRuntimeResult:
        """Evaluate Engine B through the canonical Build-7 path."""
        timestamp = _resolve_runtime_now(runtime_input.timestamp_ms, now, context="EngineBRuntime.evaluate")
        _require_scoring_version(runtime_input.engine_inputs.scoring_version, context="EngineBRuntime.evaluate")
        if self._circuit_breaker is not None and not self._circuit_breaker.is_trading_allowed():
            return _build_circuit_breaker_blocked_result(runtime_input, self._circuit_breaker)
        engine_output = run_engine_b(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)

        if engine_output.decision != "emit":
            return EngineBRuntimeResult(
                status=EngineBRuntimeStatus.NO_TRADE,
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
            if audit.engine_id == "engine_b" and audit.pair == engine_output.pair
        )

        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        penalty_reasons = tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties)
        logs.append(
            EngineBLogEntry(
                event="engine_b_scoring_completed",
                pair=engine_output.pair,
                regime=runtime_input.engine_inputs.regime,
                local_mean=runtime_input.engine_inputs.local_mean,
                local_std=runtime_input.engine_inputs.local_std,
                z_score=engine_output.z_score,
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
                block_scores=engine_output.block_scores,
                expected_cost=engine_output.expected_cost,
                expected_duration=engine_output.expected_holding_hours,
                ce_expected=engine_output.ce_expected,
                ev_net=engine_output.ev_net,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                reasons=penalty_reasons,
                scoring_version=engine_output.scoring_version,
            ),
        )

        if scoring_audit.hard_block_decision.is_blocked:
            reasons = tuple(reason.human_reason for reason in scoring_audit.hard_block_decision.reasons)
            logs.append(
                EngineBLogEntry(
                    event="engine_b_hard_blocked",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    local_mean=runtime_input.engine_inputs.local_mean,
                    local_std=runtime_input.engine_inputs.local_std,
                    z_score=engine_output.z_score,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    expected_duration=engine_output.expected_holding_hours,
                    ce_expected=engine_output.ce_expected,
                    ev_net=engine_output.ev_net,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=reasons,
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineBRuntimeResult(
                status=EngineBRuntimeStatus.HARD_BLOCKED,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        selection_entry = scoring_audit.selection_entry
        if selection_entry is None:
            raise ValueError("Engine B scoring audit is missing its selection entry")

        if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
            logs.append(
                EngineBLogEntry(
                    event="engine_b_rejected_by_ranking",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    local_mean=runtime_input.engine_inputs.local_mean,
                    local_std=runtime_input.engine_inputs.local_std,
                    z_score=engine_output.z_score,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    expected_duration=engine_output.expected_holding_hours,
                    ce_expected=engine_output.ce_expected,
                    ev_net=engine_output.ev_net,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=(selection_entry.rejection_reason,),
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineBRuntimeResult(
                status=EngineBRuntimeStatus.REJECTED_RANKING,
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
                EngineBLogEntry(
                    event="engine_b_rejected_by_portfolio",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    local_mean=runtime_input.engine_inputs.local_mean,
                    local_std=runtime_input.engine_inputs.local_std,
                    z_score=engine_output.z_score,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    expected_duration=engine_output.expected_holding_hours,
                    ce_expected=engine_output.ce_expected,
                    ev_net=engine_output.ev_net,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=(portfolio_reason,),
                    scoring_version=engine_output.scoring_version,
                ),
            )
            return EngineBRuntimeResult(
                status=EngineBRuntimeStatus.REJECTED_PORTFOLIO,
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
                engine_id="engine_b",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=timestamp,
        )

        if risk_evaluation.action != RiskRuntimeAction.ACCEPT:
            reasons = risk_evaluation.reasons or ("risk runtime rejected candidate",)
            logs.append(
                EngineBLogEntry(
                    event="engine_b_risk_rejected",
                    pair=engine_output.pair,
                    regime=runtime_input.engine_inputs.regime,
                    local_mean=runtime_input.engine_inputs.local_mean,
                    local_std=runtime_input.engine_inputs.local_std,
                    z_score=engine_output.z_score,
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    block_scores=engine_output.block_scores,
                    expected_cost=engine_output.expected_cost,
                    expected_duration=engine_output.expected_holding_hours,
                    ce_expected=engine_output.ce_expected,
                    ev_net=engine_output.ev_net,
                    conviction=engine_output.conviction.value,
                    tier=engine_output.tier_suggestion.value,
                    reasons=reasons,
                    scoring_version=engine_output.scoring_version,
                ),
            )
            status = {
                RiskRuntimeAction.REJECT: EngineBRuntimeStatus.RISK_REJECTED,
                RiskRuntimeAction.REDUCE_EXPOSURE: EngineBRuntimeStatus.RISK_REDUCED,
                RiskRuntimeAction.OBSERVE_ONLY: EngineBRuntimeStatus.RISK_OBSERVE_ONLY,
            }.get(risk_evaluation.action, EngineBRuntimeStatus.RISK_REJECTED)
            return EngineBRuntimeResult(
                status=status,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                risk_evaluation=risk_evaluation,
                log_entries=tuple(logs),
            )

        logs.append(
            EngineBLogEntry(
                event="engine_b_accepted",
                pair=engine_output.pair,
                regime=runtime_input.engine_inputs.regime,
                local_mean=runtime_input.engine_inputs.local_mean,
                local_std=runtime_input.engine_inputs.local_std,
                z_score=engine_output.z_score,
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
                block_scores=engine_output.block_scores,
                expected_cost=engine_output.expected_cost,
                expected_duration=engine_output.expected_holding_hours,
                ce_expected=engine_output.ce_expected,
                ev_net=engine_output.ev_net,
                conviction=engine_output.conviction.value,
                tier=engine_output.tier_suggestion.value,
                reasons=(),
                scoring_version=engine_output.scoring_version,
            ),
        )
        return EngineBRuntimeResult(
            status=EngineBRuntimeStatus.ACCEPTED,
            engine_output=engine_output,
            signal_candidate=signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
            log_entries=tuple(logs),
        )


def _build_circuit_breaker_blocked_result(
    runtime_input: EngineBRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineBRuntimeResult:
    reason = circuit_breaker.current_reason.value
    log_entry = EngineBLogEntry(
        event="engine_b_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        local_mean=runtime_input.engine_inputs.local_mean,
        local_std=runtime_input.engine_inputs.local_std,
        reasons=(f"emergency circuit breaker tripped: {reason}",),
        scoring_version=runtime_input.engine_inputs.scoring_version,
    )
    engine_output = EngineBOutput(
        pair=runtime_input.engine_inputs.pair,
        decision=EngineBDecision.NO_TRADE,
        z_score=0.0,
        scoring_version=runtime_input.engine_inputs.scoring_version,
        log_entries=(log_entry,),
    )
    return EngineBRuntimeResult(
        status=EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        engine_output=engine_output,
        log_entries=(log_entry,),
    )


def _build_scoring_candidate(runtime_input: EngineBRuntimeInput, engine_output: EngineBOutput) -> ScoringCandidateInput:
    score_penalties = list(runtime_input.score_penalties)
    breakout_penalty = max(0.0, engine_output.raw_score - engine_output.penalized_score)
    if breakout_penalty > 0:
        score_penalties.append(
            ScorePenaltyItem(
                penalty_id=_BREAKOUT_WARNING_PENALTY_ID,
                value=breakout_penalty,
                reason=f"anti-breakout warning penalty ({engine_output.breakout_score:.3f})",
            )
        )

    return ScoringCandidateInput(
        engine_id="engine_b",
        pair=engine_output.pair,
        raw_features={
            key: engine_output.block_scores.get(key, 0.0)
            for key in _ENGINE_B_FEATURE_WEIGHTS
        },
        allowed_features=frozenset(_ENGINE_B_FEATURE_WEIGHTS),
        weights=dict(_ENGINE_B_FEATURE_WEIGHTS),
        scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version,
        score_penalties=tuple(score_penalties),
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


def _build_signal_candidate(inputs: EngineBInput, engine_output: EngineBOutput, timestamp_ms: int) -> SignalCandidate:
    max_hold_ms = None
    if engine_output.expected_holding_hours > 0:
        max_hold_ms = int(engine_output.expected_holding_hours * 3600 * 1000)

    return SignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.B,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.penalized_score)),
        regime=_to_regime_id(inputs.regime),
        entry_price=inputs.current_price,
        stop_loss=engine_output.invalidation.stop_price if engine_output.invalidation is not None else None,
        take_profit=engine_output.invalidation.target_price if engine_output.invalidation is not None else None,
        max_hold_ms=max_hold_ms,
        reason=f"engine_b:{engine_output.conviction.value}:z={engine_output.z_score:.3f}",
    )


def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    mapping = {
        "range": RegimeId.RANGE_BOUND,
        "range_bound": RegimeId.RANGE_BOUND,
        "trending_up": RegimeId.TRENDING_UP,
        "trending_down": RegimeId.TRENDING_DOWN,
        "high_volatility": RegimeId.HIGH_VOLATILITY,
        "low_volatility": RegimeId.LOW_VOLATILITY,
        "breakout": RegimeId.BREAKOUT,
    }
    return mapping.get(normalized, RegimeId.UNKNOWN)
