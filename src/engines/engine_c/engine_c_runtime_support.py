"""Support helpers for the Engine C runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Callable

from interface_contracts import (
    EngineCVoidValidationInput,
    EngineCVoidValidationOutcome,
    EngineCoordinationInput,
    EngineCoordinationOutcome,
    EngineId,
    RefusalCategory,
    RefusalRecord,
    RegimeId,
    Side,
    SignalCandidate,
    SignalType,
)
from interface_contracts.forecast_contracts import merge_reason_codes
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntime
from scoring_backbone.ranking_router.selection_resolver import SelectionEntry
from scoring_backbone.scoring_runtime import (
    ScoringCandidateAudit,
    ScoringCandidateInput,
    ScoringRoundResult,
    ScoringRuntime,
)

from .engine_c_runner import EngineCInput, EngineCLogEntry, EngineCOutput
from .engine_c_runtime_forecast_support import (
    annotate_forecast_signal_candidate_for_runtime_status as _annotate_forecast_signal_candidate_for_runtime_status,
    build_forecast_signal_candidate,
    resolve_hook_blocked_reason_codes as _resolve_hook_blocked_reason_codes,
)

if TYPE_CHECKING:
    from .engine_c_runtime import EngineCRuntimeInput


def resolve_runtime_now(timestamp_ms: int, now: float | None, *, context: str) -> float:
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


def require_scoring_version(scoring_version: str, *, context: str) -> str:
    """Reject empty audit versions on the open engine runtime rail."""

    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized


def resolve_scoring_audit(
    scoring_round: ScoringRoundResult,
    *,
    engine_id: str,
    pair: str,
) -> ScoringCandidateAudit | None:
    for audit in scoring_round.audits:
        if audit.engine_id == engine_id and audit.pair == pair:
            return audit
    return None


def build_signal_candidate(inputs: EngineCInput, engine_output: EngineCOutput, timestamp_ms: int) -> SignalCandidate:
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
        regime=to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=engine_output.invalidation.stop_price if engine_output.invalidation is not None else None,
        take_profit=engine_output.invalidation.target_price if engine_output.invalidation is not None else None,
        max_hold_ms=max_hold_ms,
        reason=f"engine_c:{engine_output.conviction.value}:{engine_output.breakout_type or 'breakout'}",
    )


def to_regime_id(value: str) -> RegimeId:
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


def validate_coordination_input(
    coordination_input: EngineCoordinationInput,
    *,
    engine_id: EngineId,
    pair: str,
    side: Side,
) -> None:
    normalized_pair = pair.strip().upper()
    if coordination_input.engine_id != engine_id:
        raise ValueError(
            f"coordination_input.engine_id must be {engine_id.value} for {engine_id.value} runtime"
        )
    if coordination_input.pair != normalized_pair:
        raise ValueError(f"coordination_input.pair must match runtime pair {normalized_pair}")
    if coordination_input.side != side:
        raise ValueError(f"coordination_input.side must be {side.value} for {engine_id.value} runtime")


def build_runtime_refusal_record(
    *,
    timestamp_ms: int,
    status: str,
    engine_output: EngineCOutput,
    log_entries: tuple[EngineCLogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
    coordination_outcome: EngineCoordinationOutcome | None,
) -> RefusalRecord | None:
    if status == "hard_blocked" and coordination_outcome is not None and coordination_outcome.refusal_record is not None:
        return coordination_outcome.refusal_record.model_copy(
            update={
                "reason_codes": merge_reason_codes(
                    coordination_outcome.refusal_record.reason_codes,
                    _resolve_coordination_runtime_reason_codes(log_entries),
                    _resolve_local_duplication_reason_codes(engine_output),
                )
            }
        )
    category = _resolve_runtime_refusal_category(status)
    if category is None:
        return None
    return RefusalRecord(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.C,
        category=category,
        reason_codes=_resolve_runtime_refusal_reason_codes(
            status=status,
            engine_output=engine_output,
            log_entries=log_entries,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
        ),
    )


def runtime_log_entry(
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
        "local_duplication_policy_triggered": engine_output.local_duplication_policy_triggered,
        "duplication_blocked": engine_output.duplication_blocked,
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


def append_runtime_log(
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
        runtime_log_entry(
            runtime_input,
            engine_output,
            event=event,
            raw_score=raw_score,
            penalized_score=penalized_score,
            reasons=reasons,
        )
    )


@dataclass(frozen=True)
class _EngineCScoringState:
    signal_candidate: SignalCandidate
    forecast_signal_candidate: ForecastSignalCandidate | None
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit | None
    penalized_score: float


_ENGINE_C_ROLE = (
    "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context."
)
_ENGINE_C_SHARED_PHYSICS_MAPPING_STATUS = "PARTIAL_BY_DESIGN"
_ENGINE_C_COST_STATUS = "NOT_PROVEN"
_ENGINE_C_RISK_INPUT_STATUS = "PARTIAL"


def build_scoring_candidate(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    feature_weights: dict[str, float],
) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id="engine_c",
        pair=engine_output.pair,
        raw_features={key: engine_output.block_scores.get(key, 0.0) for key in feature_weights},
        supplementary_refs=runtime_input.supplementary_refs,
        carriage_statuses=("local_math_only", "shared_scoring_physics_partial"),
        carriage_reason_codes=(
            "SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",
            "HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE",
            "REGIME_SCORING_REINJECTION_PARTIAL",
        ),
        shared_physics_mapping_status=_ENGINE_C_SHARED_PHYSICS_MAPPING_STATUS,
        engine_role=_ENGINE_C_ROLE,
        allowed_features=frozenset(feature_weights),
        weights=dict(feature_weights),
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
        cost_model_completeness_status=_ENGINE_C_COST_STATUS,
        fee_source_status=_ENGINE_C_COST_STATUS,
        impact_source_status=_ENGINE_C_COST_STATUS,
        fill_realism_status=_ENGINE_C_COST_STATUS,
        realized_slippage_status=_ENGINE_C_COST_STATUS,
    )


def build_scoring_state(
    scoring_runtime: ScoringRuntime,
    *,
    feature_weights: dict[str, float],
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    logs: list[EngineCLogEntry],
    timestamp: float,
) -> _EngineCScoringState:
    """Build the runtime scoring state.

    On the emitted Engine C rail, `raw_score_result.base_raw_score` is expected to
    reconstruct `engine_output.penalized_score`, i.e. the local runner score
    after the fake-breakout adjustment and before downstream scoring penalties
    and caps. Downstream penalized score remains a distinct surface because
    scoring penalties and caps are applied after the local runner conviction
    score.
    """
    signal_candidate = build_signal_candidate(
        runtime_input.engine_inputs,
        engine_output,
        runtime_input.timestamp_ms,
    )
    scoring_round = scoring_runtime.run_round(
        candidates=(build_scoring_candidate(runtime_input, engine_output, feature_weights), *runtime_input.peer_candidates),
        portfolio=runtime_input.portfolio,
        max_selections=runtime_input.max_selections,
        now=timestamp,
    )
    scoring_audit = resolve_scoring_audit(
        scoring_round,
        engine_id="engine_c",
        pair=engine_output.pair,
    )
    if scoring_audit is None:
        append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_c_scoring_audit_missing",
            reasons=("scoring audit not found for engine_c - hard blocked",),
        )
        return _EngineCScoringState(
            signal_candidate=signal_candidate,
            forecast_signal_candidate=None,
            scoring_round=scoring_round,
            scoring_audit=None,
            penalized_score=0.0,
        )

    penalized_score = _resolve_runtime_penalized_score(scoring_audit)
    append_runtime_log(
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
        forecast_signal_candidate=build_forecast_signal_candidate(
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


def _resolve_runtime_penalized_score(scoring_audit: ScoringCandidateAudit) -> float:
    """Resolve the downstream Build-5 penalized score.

    This is intentionally distinct from `engine_output.penalized_score`, which is
    the local Engine C conviction score before scoring/ranking portfolio effects.
    """

    return max(
        0.0,
        scoring_audit.raw_score_result.raw_score
        - scoring_audit.penalty_cap_result.capped_score_penalty,
    )


def evaluate_risk(
    risk_runtime: RiskRuntime,
    *,
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    scoring_state: _EngineCScoringState,
    timestamp: float,
) -> RiskEvaluation:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine C scoring state is missing its scoring audit")
    size_multiplier = scoring_audit.penalty_cap_result.capped_size_multiplier
    planned_loss = runtime_input.projected_loss
    if planned_loss is not None:
        planned_loss *= size_multiplier
    risk_runtime.set_equity(
        current_equity=runtime_input.current_equity,
        session_peak_equity=runtime_input.session_peak_equity,
    )
    return risk_runtime.evaluate_candidate(
        RiskCandidate(
            pair=engine_output.pair,
            engine_id="engine_c",
            size=runtime_input.projected_size * size_multiplier,
            planned_loss=planned_loss,
            pair_beta=runtime_input.pair_beta,
            carriage_statuses=("risk_micro_friction_missing", "not_carried_to_risk_rail"),
            carriage_reason_codes=(
                "RISK_MICRO_FRICTION_FIELD_MISSING",
                "RISK_INFO_STRESS_FIELD_MISSING",
                "RISK_REGIME_STATE_MISSING",
            ),
            shared_physics_mapping_status=_ENGINE_C_SHARED_PHYSICS_MAPPING_STATUS,
            engine_role=_ENGINE_C_ROLE,
            execution_fragility_status="NOT_PROVEN",
            market_toxicity_status="NOT_PROVEN",
            spread_regime_penalty_status="NOT_PROVEN",
            participation_penalty_status="NOT_PROVEN",
            micro_friction_source_status="NOT_PROVEN",
            risk_input_completeness_status=_ENGINE_C_RISK_INPUT_STATUS,
            cost_model_completeness_status=_ENGINE_C_COST_STATUS,
            fee_source_status=_ENGINE_C_COST_STATUS,
            impact_source_status=_ENGINE_C_COST_STATUS,
            fill_realism_status=_ENGINE_C_COST_STATUS,
            realized_slippage_status=_ENGINE_C_COST_STATUS,
        ),
        now=timestamp,
    )


def run_void_validation_hook(
    hook: Callable[[EngineCVoidValidationInput], EngineCVoidValidationOutcome] | None,
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
) -> EngineCVoidValidationOutcome | None:
    if hook is None:
        return None
    return hook(
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


def require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine C scoring audit is missing its selection entry")
    return selection_entry


def _resolve_runtime_refusal_category(status: str) -> RefusalCategory | None:
    if status == "no_trade":
        return RefusalCategory.NO_TRADE
    if status in {
        "circuit_breaker_blocked",
        "hook_blocked",
        "hard_blocked",
        "risk_rejected",
    }:
        return RefusalCategory.HARD_BLOCK
    if status == "rejected_ranking":
        return RefusalCategory.NO_TRADE
    if status == "rejected_portfolio":
        return RefusalCategory.PORTFOLIO_REJECTED
    return None


def _resolve_runtime_refusal_reason_codes(
    *,
    status: str,
    engine_output: EngineCOutput,
    log_entries: tuple[EngineCLogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if status == "no_trade":
        if engine_output.reason_codes:
            return engine_output.reason_codes
        if engine_output.no_trade_reasons:
            return tuple(f"engine_c.no_trade.{reason.value}" for reason in engine_output.no_trade_reasons)
        return ("engine_c.runtime.no_trade",)
    if status == "hook_blocked":
        hook_reason_codes = _extract_log_reason_codes(log_entries, "engine_c_hook_blocked")
        return merge_reason_codes(hook_reason_codes, engine_output.reason_codes)
    if status == "circuit_breaker_blocked":
        breaker_reason_codes = _extract_log_reason_codes(log_entries, "engine_c_circuit_breaker_blocked")
        if breaker_reason_codes:
            return breaker_reason_codes
        return ("engine_c.runtime.circuit_breaker_blocked",)
    if status == "hard_blocked":
        coordination_reason_codes = _resolve_coordination_runtime_reason_codes(log_entries)
        if coordination_reason_codes:
            return merge_reason_codes(
                coordination_reason_codes,
                _resolve_local_duplication_reason_codes(engine_output),
            )
        if scoring_audit is not None and scoring_audit.hard_block_decision.reasons:
            return merge_reason_codes(
                engine_output.reason_codes,
                ("hard_block.engine_c.runtime.hard_blocked", "engine_c.runtime.hard_blocked"),
                (reason.code for reason in scoring_audit.hard_block_decision.reasons),
            )
        return merge_reason_codes(
            engine_output.reason_codes,
            ("hard_block.engine_c.runtime.hard_blocked", "engine_c.runtime.hard_blocked"),
        )
    if status == "rejected_ranking":
        return merge_reason_codes(
            engine_output.reason_codes,
            ("scoring.engine_c.runtime.rejected_ranking", "engine_c.runtime.rejected_ranking"),
        )
    if status == "rejected_portfolio":
        return merge_reason_codes(
            engine_output.reason_codes,
            ("portfolio.engine_c.runtime.rejected_portfolio", "engine_c.runtime.rejected_portfolio"),
        )
    if status == "risk_rejected":
        if risk_evaluation is not None:
            if risk_evaluation.reason_details:
                return merge_reason_codes(
                    engine_output.reason_codes,
                    ("hard_block.engine_c.runtime.risk_rejected", "engine_c.runtime.risk_rejected"),
                    (detail.code for detail in risk_evaluation.reason_details),
                )
            if risk_evaluation.dominant_reason_code:
                return merge_reason_codes(
                    engine_output.reason_codes,
                    (
                        "hard_block.engine_c.runtime.risk_rejected",
                        "engine_c.runtime.risk_rejected",
                        risk_evaluation.dominant_reason_code,
                    ),
                )
        return merge_reason_codes(
            engine_output.reason_codes,
            ("hard_block.engine_c.runtime.risk_rejected", "engine_c.runtime.risk_rejected"),
        )
    return ("engine_c.runtime.unknown_refusal",)
def _extract_log_reason_codes(log_entries: tuple[EngineCLogEntry, ...], event: str) -> tuple[str, ...]:
    for entry in reversed(log_entries):
        if entry.event != event:
            continue
        reason_codes = tuple(reason for reason in entry.reasons if reason.strip())
        if reason_codes:
            return reason_codes
    return ()


def _resolve_coordination_runtime_reason_codes(
    log_entries: tuple[EngineCLogEntry, ...],
) -> tuple[str, ...]:
    coordination_missing_reason_codes = _extract_log_reason_codes(log_entries, "engine_c_coordination_missing")
    if coordination_missing_reason_codes:
        return coordination_missing_reason_codes
    coordination_blocked_reason_codes = _extract_log_reason_codes(log_entries, "engine_c_coordination_blocked")
    if coordination_blocked_reason_codes:
        return coordination_blocked_reason_codes
    return ()


def _resolve_local_duplication_reason_codes(
    engine_output: EngineCOutput,
) -> tuple[str, ...]:
    if engine_output.local_duplication_policy_triggered:
        return ("engine_c.duplication.local_policy_triggered",)
    return ()


__all__ = [
    "_EngineCScoringState",
    "_annotate_forecast_signal_candidate_for_runtime_status",
    "_resolve_hook_blocked_reason_codes",
    "append_runtime_log",
    "build_forecast_signal_candidate",
    "build_runtime_refusal_record",
    "build_scoring_candidate",
    "build_scoring_state",
    "build_signal_candidate",
    "evaluate_risk",
    "require_scoring_version",
    "require_selection_entry",
    "resolve_runtime_now",
    "resolve_scoring_audit",
    "run_void_validation_hook",
    "to_regime_id",
    "validate_coordination_input",
]
