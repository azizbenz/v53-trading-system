"""Private helper functions for the Engine B runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
import math

from interface_contracts import (
    EngineId,
    ForecastSignalCandidate,
    RegimeId,
    RefusalRecord,
    Side,
    SignalCandidate as DecisionSignalCandidate,
    SignalType,
)
from risk_backbone.emergency_kill_switch.circuit_breaker import EmergencyCircuitBreaker
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntimeAction
from scoring_backbone.ranking_router.selection_resolver import SelectionEntry, SelectionOutcome
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringCandidateInput, ScoringRoundResult
from .engine_b_runtime_forecast_support import (
    annotate_forecast_signal_candidate_for_runtime_status as _annotate_forecast_signal_candidate_for_runtime_status,
    build_forecast_signal_candidate as _build_forecast_signal_candidate,
    resolve_hook_blocked_reason_codes as _resolve_hook_blocked_reason_codes,
    resolve_runtime_economics_reason_codes as _resolve_runtime_economics_reason_codes,
)

from .conviction_builder_b import (
    ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS,
    ENGINE_B_CONVICTION_FEATURE_WEIGHTS,
    ENGINE_B_CONVICTION_NORMALIZATION,
)
from .engine_b_runner import EngineBDecision, EngineBInput, EngineBLogEntry, EngineBOutput
from .engine_b_runtime import (
    _BREAKOUT_WARNING_PENALTY_ID,
    EngineBRuntimeInput,
    EngineBRuntimeResult,
    EngineBRuntimeStatus,
    EngineBSweepValidationOutcome,
)


def _append_runtime_log(
    logs: list[EngineBLogEntry],
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    *,
    event: str,
    raw_score: float,
    penalized_score: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        EngineBLogEntry(
            event=event,
            pair=engine_output.pair,
            regime=runtime_input.engine_inputs.regime,
            local_mean=runtime_input.engine_inputs.local_mean,
            local_std=runtime_input.engine_inputs.local_std,
            z_score=engine_output.z_score,
            raw_score=raw_score,
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
        )
    )


def _append_hook_adjustment_log(
    logs: list[EngineBLogEntry],
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    *,
    hook_outcome: EngineBSweepValidationOutcome,
    raw_score_multiplier: float,
    raw_score_add: float,
    raw_score_cap: float | None,
) -> None:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_b_sweep_validation_applied",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=tuple(
            part
            for part in (
                *hook_outcome.reason_codes,
                f"raw_score_multiplier={raw_score_multiplier:.4f}" if raw_score_multiplier != 1.0 else "",
                f"raw_score_add={raw_score_add:.4f}" if raw_score_add != 0.0 else "",
                f"raw_score_cap={raw_score_cap:.4f}" if raw_score_cap is not None else "",
            )
            if part
        ),
    )


def _build_runtime_result(
    *,
    status: EngineBRuntimeStatus,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    signal_candidate: DecisionSignalCandidate | None = None,
    forecast_signal_candidate: ForecastSignalCandidate | None = None,
    scoring_round: ScoringRoundResult | None = None,
    scoring_audit: ScoringCandidateAudit | None = None,
    risk_evaluation: RiskEvaluation | None = None,
    refusal_record: RefusalRecord | None = None,
) -> EngineBRuntimeResult:
    return EngineBRuntimeResult(
        status=status,
        engine_output=engine_output,
        signal_candidate=signal_candidate,
        forecast_signal_candidate=forecast_signal_candidate,
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
        refusal_record=refusal_record,
        log_entries=tuple(logs),
    )


def _build_hook_blocked_runtime_result(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    *,
    hook_outcome: EngineBSweepValidationOutcome,
) -> EngineBRuntimeResult:
    hook_reason_codes = _resolve_hook_blocked_reason_codes(
        hook_outcome.reason_codes,
    )
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_b_hook_blocked",
        raw_score=engine_output.raw_score,
        penalized_score=engine_output.penalized_score,
        reasons=hook_reason_codes,
    )
    return _build_runtime_result(
        status=EngineBRuntimeStatus.HOOK_BLOCKED,
        engine_output=engine_output,
        logs=logs,
    )


@dataclass(frozen=True)
class _EngineBScoringState:
    signal_candidate: DecisionSignalCandidate
    forecast_signal_candidate: ForecastSignalCandidate | None
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit
    penalized_score: float

    @classmethod
    def from_audit(
        cls,
        runtime_input: EngineBRuntimeInput,
        engine_output: EngineBOutput,
        logs: list[EngineBLogEntry],
        *,
        signal_candidate: DecisionSignalCandidate,
        forecast_signal_candidate: ForecastSignalCandidate | None,
        scoring_round: ScoringRoundResult,
        scoring_audit: ScoringCandidateAudit,
    ) -> _EngineBScoringState:
        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score
            - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_b_scoring_completed",
            raw_score=scoring_audit.raw_score_result.raw_score,
            penalized_score=penalized_score,
            reasons=tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties),
        )
        return cls(
            signal_candidate=signal_candidate,
            forecast_signal_candidate=forecast_signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            penalized_score=penalized_score,
        )

    def build_risk_candidate(
        self,
        runtime_input: EngineBRuntimeInput,
        engine_output: EngineBOutput,
    ) -> RiskCandidate:
        size_multiplier = self.scoring_audit.penalty_cap_result.capped_size_multiplier
        planned_loss = runtime_input.projected_loss
        if planned_loss is not None:
            planned_loss *= size_multiplier
        return RiskCandidate(
            pair=engine_output.pair,
            engine_id="engine_b",
            size=runtime_input.projected_size * size_multiplier,
            planned_loss=planned_loss,
            pair_beta=runtime_input.pair_beta,
            carriage_statuses=("risk_micro_friction_carried",),
            carriage_reason_codes=(
                "RISK_INFO_STRESS_FIELD_MISSING",
                "RISK_REGIME_STATE_MISSING",
            ),
            execution_fragility=runtime_input.engine_inputs.execution_fragility,
            market_toxicity=runtime_input.engine_inputs.market_toxicity,
            spread_regime_penalty=runtime_input.engine_inputs.spread_regime_penalty,
        )


def _build_hard_blocked_runtime_result(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    *,
    scoring_state: _EngineBScoringState,
) -> EngineBRuntimeResult:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_b_hard_blocked",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=tuple(reason.human_reason for reason in scoring_state.scoring_audit.hard_block_decision.reasons),
    )
    return _build_runtime_result(
        status=EngineBRuntimeStatus.HARD_BLOCKED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineBRuntimeStatus.HARD_BLOCKED.value,
            scoring_audit=scoring_state.scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
    )


def _require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine B scoring audit is missing its selection entry")
    return selection_entry


def _build_selection_rejected_runtime_result(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    *,
    scoring_state: _EngineBScoringState,
    selection_entry: SelectionEntry,
) -> EngineBRuntimeResult | None:
    if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
        _append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_b_rejected_by_ranking",
            raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
            penalized_score=scoring_state.penalized_score,
            reasons=(selection_entry.rejection_reason,),
        )
        return _build_runtime_result(
            status=EngineBRuntimeStatus.REJECTED_RANKING,
            engine_output=engine_output,
            logs=logs,
            signal_candidate=scoring_state.signal_candidate,
            forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
                scoring_state.forecast_signal_candidate,
                timestamp_ms=runtime_input.timestamp_ms,
                status=EngineBRuntimeStatus.REJECTED_RANKING.value,
                scoring_audit=scoring_state.scoring_audit,
                risk_evaluation=None,
            ),
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
        event="engine_b_rejected_by_portfolio",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=(portfolio_reason,),
    )
    return _build_runtime_result(
        status=EngineBRuntimeStatus.REJECTED_PORTFOLIO,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=EngineBRuntimeStatus.REJECTED_PORTFOLIO.value,
            scoring_audit=scoring_state.scoring_audit,
            risk_evaluation=None,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
    )


def _build_risk_runtime_result(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    *,
    scoring_state: _EngineBScoringState,
    risk_evaluation: RiskEvaluation,
) -> EngineBRuntimeResult | None:
    if risk_evaluation.action == RiskRuntimeAction.ACCEPT:
        return None
    event = {
        RiskRuntimeAction.REJECT: "engine_b_risk_rejected",
        RiskRuntimeAction.REDUCE_EXPOSURE: "engine_b_risk_reduced",
        RiskRuntimeAction.OBSERVE_ONLY: "engine_b_risk_observe_only",
    }.get(risk_evaluation.action, "engine_b_risk_rejected")
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event=event,
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
        reasons=risk_evaluation.reasons or ("risk runtime rejected candidate",),
    )
    status = {
        RiskRuntimeAction.REJECT: EngineBRuntimeStatus.RISK_REJECTED,
        RiskRuntimeAction.REDUCE_EXPOSURE: EngineBRuntimeStatus.RISK_REDUCED,
        RiskRuntimeAction.OBSERVE_ONLY: EngineBRuntimeStatus.RISK_OBSERVE_ONLY,
    }.get(risk_evaluation.action, EngineBRuntimeStatus.RISK_REJECTED)
    return _build_runtime_result(
        status=status,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=_annotate_forecast_signal_candidate_for_runtime_status(
            scoring_state.forecast_signal_candidate,
            timestamp_ms=runtime_input.timestamp_ms,
            status=status.value,
            scoring_audit=scoring_state.scoring_audit,
            risk_evaluation=risk_evaluation,
        ),
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
        risk_evaluation=risk_evaluation,
    )


def _build_accepted_runtime_result(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    logs: list[EngineBLogEntry],
    *,
    scoring_state: _EngineBScoringState,
    risk_evaluation: RiskEvaluation,
) -> EngineBRuntimeResult:
    _append_runtime_log(
        logs,
        runtime_input,
        engine_output,
        event="engine_b_accepted",
        raw_score=scoring_state.scoring_audit.raw_score_result.raw_score,
        penalized_score=scoring_state.penalized_score,
    )
    return _build_runtime_result(
        status=EngineBRuntimeStatus.ACCEPTED,
        engine_output=engine_output,
        logs=logs,
        signal_candidate=scoring_state.signal_candidate,
        forecast_signal_candidate=scoring_state.forecast_signal_candidate,
        scoring_round=scoring_state.scoring_round,
        scoring_audit=scoring_state.scoring_audit,
        risk_evaluation=risk_evaluation,
    )


def _build_circuit_breaker_blocked_result(
    runtime_input: EngineBRuntimeInput,
    circuit_breaker: EmergencyCircuitBreaker,
) -> EngineBRuntimeResult:
    reason = circuit_breaker.current_reason.value
    reason_codes = (f"engine_b.runtime.circuit_breaker.{reason}",)
    log_entry = EngineBLogEntry(
        event="engine_b_circuit_breaker_blocked",
        pair=runtime_input.engine_inputs.pair,
        regime=runtime_input.engine_inputs.regime,
        local_mean=runtime_input.engine_inputs.local_mean,
        local_std=runtime_input.engine_inputs.local_std,
        reasons=reason_codes,
        scoring_version=runtime_input.engine_inputs.scoring_version,
    )
    engine_output = EngineBOutput(
        pair=runtime_input.engine_inputs.pair,
        decision=EngineBDecision.NO_TRADE,
        z_score=0.0,
        scoring_version=runtime_input.engine_inputs.scoring_version,
        reason_codes=reason_codes,
        log_entries=(log_entry,),
    )
    return EngineBRuntimeResult(
        status=EngineBRuntimeStatus.CIRCUIT_BREAKER_BLOCKED,
        engine_output=engine_output,
        log_entries=(log_entry,),
    )


def _build_engine_b_scoring_raw_features(
    engine_output: EngineBOutput,
) -> dict[str, float]:
    neutral_midpoint = ENGINE_B_CONVICTION_NORMALIZATION["neutral_midpoint"]
    block_scores = engine_output.block_scores
    return {
        "excess": block_scores.get("excess", 0.0),
        "structure": block_scores.get("structure", 0.0),
        "context": block_scores.get("context", 0.0),
        "cost_preference": block_scores.get("cost_preference", 0.0),
        "sweep_score_centered": block_scores.get("sweep_score", neutral_midpoint) - neutral_midpoint,
        "absorption_score_centered": (
            block_scores.get("absorption_score", neutral_midpoint) - neutral_midpoint
        ),
        "poc_reversion_score_centered": (
            block_scores.get("poc_reversion_score", neutral_midpoint) - neutral_midpoint
        ),
        "false_breakout_score": block_scores.get("false_breakout_score", neutral_midpoint),
        "fragility_score": block_scores.get("fragility_score", 0.0),
        "toxicity_score": block_scores.get("toxicity_score", 0.0),
        "micro_friction_score": block_scores.get("micro_friction_score", 0.0),
    }


def _build_engine_b_scoring_weights() -> dict[str, float]:
    return {
        **ENGINE_B_CONVICTION_FEATURE_WEIGHTS,
        "sweep_score_centered": ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["sweep_score"],
        "absorption_score_centered": ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["absorption_score"],
        "poc_reversion_score_centered": ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["poc_reversion_score"],
        "false_breakout_score": -ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["false_breakout_penalty"],
        "fragility_score": -ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["fragility_penalty"],
        "toxicity_score": -ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["toxicity_penalty"],
        "micro_friction_score": -ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["micro_friction_penalty"],
    }


def _build_scoring_candidate(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    *,
    raw_score_multiplier: float = 1.0,
    raw_score_add: float = 0.0,
    raw_score_cap: float | None = None,
) -> ScoringCandidateInput:
    score_penalties = list(runtime_input.score_penalties)
    breakout_penalty = max(0.0, engine_output.raw_score - engine_output.penalized_score)
    if breakout_penalty > 0:
        # This keeps the scoring backbone audit surface aligned with the runner-visible
        # breakout warning penalty; it is not a second independent breakout logic.
        score_penalties.append(
            ScorePenaltyItem(
                penalty_id=_BREAKOUT_WARNING_PENALTY_ID,
                value=breakout_penalty,
                reason=f"anti-breakout warning penalty ({engine_output.breakout_score:.3f})",
            )
        )
    raw_features = _build_engine_b_scoring_raw_features(engine_output)
    return ScoringCandidateInput(
        engine_id="engine_b",
        pair=engine_output.pair,
        raw_features=raw_features,
        supplementary_refs=runtime_input.supplementary_refs,
        carriage_statuses=(
            "derived_shared_scoring",
            "shared_scoring_physics_carried",
            "shared_scoring_physics_partial",
        ),
        carriage_reason_codes=("SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",),
        allowed_features=frozenset(raw_features),
        weights=_build_engine_b_scoring_weights(),
        scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version,
        raw_score_multiplier=raw_score_multiplier,
        raw_score_add=raw_score_add,
        raw_score_cap=1.0 if raw_score_cap is None else min(1.0, raw_score_cap),
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
        execution_fragility=runtime_input.engine_inputs.execution_fragility,
        market_toxicity=runtime_input.engine_inputs.market_toxicity,
        spread_regime_penalty=runtime_input.engine_inputs.spread_regime_penalty,
    )


def _hook_outcome_has_adjustment(hook_outcome: EngineBSweepValidationOutcome) -> bool:
    return (
        hook_outcome.raw_score_multiplier_delta != 0.0
        or hook_outcome.raw_score_add != 0.0
        or hook_outcome.conviction_add != 0.0
        or hook_outcome.raw_score_cap is not None
    )


def _resolve_hook_score_adjustments(
    hook_outcome: EngineBSweepValidationOutcome | None,
    *,
    context: str,
) -> tuple[float, float, float | None]:
    if hook_outcome is None or not hook_outcome.accepted:
        return 1.0, 0.0, None
    raw_score_multiplier = 1.0 + hook_outcome.raw_score_multiplier_delta
    if not math.isfinite(raw_score_multiplier):
        raise ValueError(f"{context} requires finite hook raw_score_multiplier")
    raw_score_multiplier = max(0.0, raw_score_multiplier)
    raw_score_add = hook_outcome.raw_score_add + hook_outcome.conviction_add
    if not math.isfinite(raw_score_add):
        raise ValueError(f"{context} requires finite hook raw_score_add")
    raw_score_cap = hook_outcome.raw_score_cap
    if raw_score_cap is not None:
        if not math.isfinite(raw_score_cap):
            raise ValueError(f"{context} requires finite hook raw_score_cap")
        if raw_score_cap < 0.0:
            raise ValueError(f"{context} requires hook raw_score_cap >= 0")
    return raw_score_multiplier, raw_score_add, raw_score_cap


def _resolve_runtime_now(timestamp_ms: int, now: float | None, *, context: str) -> float:
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
    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized


def _resolve_scoring_audit(
    scoring_round: ScoringRoundResult,
    *,
    engine_id: str,
    pair: str,
    context: str,
) -> ScoringCandidateAudit:
    matches = [
        audit
        for audit in scoring_round.audits
        if audit.engine_id == engine_id and audit.pair == pair
    ]
    if not matches:
        raise ValueError(f"{context} is missing scoring audit for {engine_id}/{pair}")
    if len(matches) > 1:
        raise ValueError(f"{context} found duplicate scoring audits for {engine_id}/{pair}")
    return matches[0]


def _build_signal_candidate(
    inputs: EngineBInput,
    engine_output: EngineBOutput,
    timestamp_ms: int,
) -> DecisionSignalCandidate:
    max_hold_ms = None
    if engine_output.expected_holding_hours > 0:
        max_hold_ms = int(engine_output.expected_holding_hours * 3600 * 1000)
    return DecisionSignalCandidate(
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
