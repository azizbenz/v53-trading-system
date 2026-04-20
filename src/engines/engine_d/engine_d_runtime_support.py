"""Support helpers for the Engine D runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING, Callable

from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    EngineCoordinationInput,
    EngineCoordinationOutcome,
    EngineId,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    RefusalCategory,
    RefusalRecord,
    RegimeId,
    Side,
    SignalCandidate,
    SignalType,
)
from interface_contracts.forecast_contracts import build_scoring_conditioning_records, merge_reason_codes
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntime
from scoring_backbone import (
    BreakEvenFilterConfig,
    BreakEvenFilterDecision,
    ForecastNormalizationResult,
    ForecastNormalizerConfig,
    evaluate_break_even_filter,
    normalize_forecast,
)
from scoring_backbone.ranking_router.selection_resolver import SelectionEntry
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringCandidateInput, ScoringRoundResult, ScoringRuntime

from .engine_d_runner import EngineDInput, EngineDLogEntry, EngineDOutput
from .engine_d_runtime_support_refusal import _resolve_runtime_refusal_category, _resolve_runtime_refusal_reason_codes

if TYPE_CHECKING:
    from .engine_d_runtime import EngineDRuntimeInput
_ENGINE_D_FORECAST_NORMALIZER_CONFIG = ForecastNormalizerConfig(max_abs_forecast=10.0)
_ENGINE_D_BREAK_EVEN_FILTER_CONFIG = BreakEvenFilterConfig()

@dataclass(frozen=True)
class _EngineDForecastEconomics:
    normalization: ForecastNormalizationResult
    break_even_decision: BreakEvenFilterDecision
    volatility_proxy_reason_code: str
    volatility_proxy_conditioning_code: str

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

def build_signal_candidate(inputs: EngineDInput, engine_output: EngineDOutput, timestamp_ms: int) -> SignalCandidate:
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
    engine_output: EngineDOutput,
    log_entries: tuple[EngineDLogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
    coordination_outcome: EngineCoordinationOutcome | None,
) -> RefusalRecord | None:
    if status == "hard_blocked" and coordination_outcome is not None and coordination_outcome.refusal_record is not None:
        return coordination_outcome.refusal_record
    category = _resolve_runtime_refusal_category(status)
    if category is None:
        return None
    return RefusalRecord(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.D,
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
        "anti_revenge_blocked": engine_output.anti_revenge_blocked,
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
        "duplication_blocked": engine_output.duplication_blocked,
        "marginal_portfolio_gain": engine_output.marginal_portfolio_gain,
        "covered_share_by_engine_a": engine_output.covered_share_by_engine_a,
        "conviction": engine_output.conviction.value,
        "tier": engine_output.tier_suggestion.value,
        "holding_hours": engine_output.holding_hours,
        "scoring_version": engine_output.scoring_version,
    }
    payload.update(overrides)
    return EngineDLogEntry(**payload)
def append_runtime_log(
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
class _EngineDScoringState:
    signal_candidate: SignalCandidate
    forecast_signal_candidate: ForecastSignalCandidate | None
    scoring_round: ScoringRoundResult
    scoring_audit: ScoringCandidateAudit | None
    penalized_score: float

def build_scoring_candidate(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    feature_weights: dict[str, float],
) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id="engine_d",
        pair=engine_output.pair,
        raw_features={key: engine_output.block_scores.get(key, 0.0) for key in feature_weights},
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
    )


def build_scoring_state(
    scoring_runtime: ScoringRuntime,
    *,
    feature_weights: dict[str, float],
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    logs: list[EngineDLogEntry],
    timestamp: float,
) -> _EngineDScoringState:
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
        engine_id="engine_d",
        pair=engine_output.pair,
    )
    if scoring_audit is None:
        append_runtime_log(
            logs,
            runtime_input,
            engine_output,
            event="engine_d_scoring_audit_missing",
            reasons=("scoring audit not found for engine_d - hard blocked",),
        )
        return _EngineDScoringState(
            signal_candidate=signal_candidate,
            forecast_signal_candidate=None,
            scoring_round=scoring_round,
            scoring_audit=None,
            penalized_score=0.0,
        )

    penalized_score = max(
        0.0,
        scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
    )
    append_runtime_log(
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
        forecast_signal_candidate=build_forecast_signal_candidate(
            strategy_id=runtime_input.strategy_id,
            timestamp_ms=runtime_input.timestamp_ms,
            runtime_input=runtime_input,
            engine_output=engine_output,
            signal_candidate=signal_candidate,
            scoring_audit=scoring_audit,
        ),
        scoring_round=scoring_round,
        scoring_audit=scoring_audit,
        penalized_score=penalized_score,
    )

def build_forecast_signal_candidate(
    *,
    strategy_id: str | None,
    timestamp_ms: int,
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    signal_candidate: SignalCandidate,
    scoring_audit: ScoringCandidateAudit,
) -> ForecastSignalCandidate | None:
    if strategy_id is None:
        return None
    forecast_economics = _resolve_forecast_economics(runtime_input.engine_inputs, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id,
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=abs(forecast_economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_forecast_horizon_class(runtime_input.engine_inputs, signal_candidate),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=_resolve_bet_structure(runtime_input),
        conditioning_state=_build_conditioning_state(
            timestamp_ms=timestamp_ms,
            engine_output=engine_output,
            scoring_audit=scoring_audit,
            forecast_economics=forecast_economics,
        ),
        expected_cost=engine_output.expected_cost,
        expected_break_even=forecast_economics.break_even_decision.expected_break_even,
        expected_ce=engine_output.ce_expected,
        expected_gain=runtime_input.engine_inputs.expected_gain,
        invalidation_ref=_resolve_invalidation_ref(engine_output),
        reason_codes=_build_forecast_reason_codes(
            engine_output,
            scoring_audit,
            forecast_economics=forecast_economics,
        ),
        versions=_build_forecast_versions(runtime_input, engine_output),
        confidence_band=signal_candidate.confidence,
    )


def _build_conditioning_state(
    *,
    timestamp_ms: int,
    engine_output: EngineDOutput,
    scoring_audit: ScoringCandidateAudit,
    forecast_economics: _EngineDForecastEconomics,
) -> tuple[ConditioningRecord, ...]:
    records = [
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_d.conviction.{engine_output.conviction.value}",
            value=engine_output.penalized_score,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_d.tier.{engine_output.tier_suggestion.value}",
            value=engine_output.penalized_score,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_d.link_type.{engine_output.link_type or 'unknown'}",
            value=engine_output.history_score,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_d.anti_revenge.{engine_output.anti_revenge_state or 'unknown'}",
            value=1.0 if engine_output.anti_revenge_blocked else 0.0,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_d.marginal_value.present",
            value=engine_output.marginal_value_score,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_d.cost.present",
            value=engine_output.ce_expected,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=forecast_economics.volatility_proxy_conditioning_code,
            value=forecast_economics.normalization.raw_forecast,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_d.forecast.normalized_strength",
            value=forecast_economics.normalization.normalized_forecast,
            triggered_no_trade=False,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_resolve_break_even_conditioning_code(forecast_economics.break_even_decision),
            value=forecast_economics.break_even_decision.expected_break_even,
            triggered_no_trade=not forecast_economics.break_even_decision.allowed,
        ),
    ]
    if engine_output.structure_reformed_detected:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_d.reformation.detected",
                value=engine_output.reformation_score,
                triggered_no_trade=False,
            )
        )
    if engine_output.first_episode_id:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_d.first_episode.present",
                value=1.0,
                triggered_no_trade=False,
            )
        )
    if engine_output.invalidation is not None:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_d.invalidation.present",
                value=1.0,
                triggered_no_trade=False,
            )
        )
    records.extend(
        build_scoring_conditioning_records(
            timestamp_ms=timestamp_ms,
            penalties=((penalty.penalty_id, penalty.value) for penalty in scoring_audit.score_penalty_result.penalties),
        )
    )
    return tuple(records)
def _build_forecast_reason_codes(
    engine_output: EngineDOutput,
    scoring_audit: ScoringCandidateAudit,
    *,
    forecast_economics: _EngineDForecastEconomics,
) -> tuple[str, ...]:
    additive_reason_codes: list[str] = [
        forecast_economics.volatility_proxy_reason_code,
        _resolve_break_even_reason_code(forecast_economics.break_even_decision),
    ]
    if forecast_economics.normalization.clipped:
        additive_reason_codes.append("engine_d.forecast.normalized_forecast_clipped")
    return merge_reason_codes(
        additive_reason_codes,
        engine_output.reason_codes,
        ("engine_d.invalidation.present",) if engine_output.invalidation is not None else (),
        (
            f"scoring.penalty.{penalty.penalty_id}"
            for penalty in scoring_audit.score_penalty_result.penalties
        ),
    )


def _build_forecast_versions(
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
) -> dict[str, str]:
    return {"scoring_version": engine_output.scoring_version or runtime_input.engine_inputs.scoring_version, "runtime_adapter_version": "engine_d.forecast_adapter.v1"}

def _resolve_forecast_economics(
    engine_inputs: EngineDInput,
    engine_output: EngineDOutput,
) -> _EngineDForecastEconomics:
    volatility_scale, volatility_proxy_reason_code, volatility_proxy_conditioning_code = _resolve_volatility_proxy(
        engine_inputs
    )
    normalization = normalize_forecast(
        expected_return=max(0.0, engine_inputs.expected_gain - engine_output.expected_cost),
        volatility_scale=volatility_scale,
        forecast_scalar=_ENGINE_D_FORECAST_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_ENGINE_D_FORECAST_NORMALIZER_CONFIG,
    )
    return _EngineDForecastEconomics(
        normalization=normalization,
        break_even_decision=_build_additive_break_even_decision(engine_inputs, engine_output),
        volatility_proxy_reason_code=volatility_proxy_reason_code,
        volatility_proxy_conditioning_code=volatility_proxy_conditioning_code,
    )

def _resolve_volatility_proxy(
    engine_inputs: EngineDInput,
) -> tuple[float, str, str]:
    if engine_inputs.realized_vol_post_close is not None and engine_inputs.realized_vol_post_close > 0.0:
        return (
            engine_inputs.realized_vol_post_close,
            "engine_d.forecast.volatility_proxy.realized_vol_post_close",
            "engine_internal.engine_d.forecast.volatility_proxy.realized_vol_post_close",
        )
    if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
        return (
            engine_inputs.realized_vol_current,
            "engine_d.forecast.volatility_proxy.realized_vol_current_fallback",
            "engine_internal.engine_d.forecast.volatility_proxy.realized_vol_current_fallback",
        )
    return (max(engine_inputs.delta_safe, 1e-6), "engine_d.forecast.volatility_proxy.delta_safe_fallback", "engine_internal.engine_d.forecast.volatility_proxy.delta_safe_fallback")

def _build_additive_break_even_decision(
    engine_inputs: EngineDInput,
    engine_output: EngineDOutput,
) -> BreakEvenFilterDecision:
    return evaluate_break_even_filter(
        expected_gain=engine_inputs.expected_gain,
        expected_cost=engine_output.expected_cost,
        candidate_size=engine_inputs.candidate_size,
        delta_safe=engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        ce_min=engine_inputs.ce_min,
        config=_ENGINE_D_BREAK_EVEN_FILTER_CONFIG,
    )

def _resolve_break_even_reason_code(decision: BreakEvenFilterDecision) -> str:
    return "engine_d.economics.break_even_cleared" if decision.allowed else f"engine_d.economics.{decision.reason_code.lower()}"

def _resolve_break_even_conditioning_code(decision: BreakEvenFilterDecision) -> str:
    return "engine_internal.engine_d.break_even.cleared" if decision.allowed else f"engine_internal.engine_d.break_even.{decision.reason_code.lower()}"

def _resolve_invalidation_ref(engine_output: EngineDOutput) -> str | None:
    if engine_output.invalidation is None:
        return None
    invalidation = engine_output.invalidation
    return (
        f"engine_d.invalidation.{invalidation.reference_source or 'unknown'}"
        f".stop.{invalidation.stop_price:.8f}"
        f".target.{invalidation.target_price:.8f}"
        f".risk_multiple.{invalidation.risk_multiple:.6f}"
    )


def _resolve_forecast_horizon_class(
    engine_inputs: EngineDInput,
    signal_candidate: SignalCandidate,
) -> ForecastHorizonClass:
    max_hold_ms = signal_candidate.max_hold_ms
    if max_hold_ms is None: max_hold_ms = int(engine_inputs.holding_period * 3600 * 1000)
    if max_hold_ms < 60_000:
        return ForecastHorizonClass.INTRABAR
    if max_hold_ms <= 15 * 60_000:
        return ForecastHorizonClass.SHORT
    if max_hold_ms <= 4 * 60 * 60_000:
        return ForecastHorizonClass.MEDIUM
    return ForecastHorizonClass.LONG


def _resolve_bet_structure(runtime_input: EngineDRuntimeInput) -> BetStructure:
    coordination_input = runtime_input.coordination_input
    if coordination_input is not None and coordination_input.first_episode_ref is not None:
        return coordination_input.first_episode_ref.bet_structure
    return BetStructure.DIRECTIONAL_LONG


def evaluate_risk(
    risk_runtime: RiskRuntime,
    *,
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
    scoring_state: _EngineDScoringState,
    timestamp: float,
) -> RiskEvaluation:
    scoring_audit = scoring_state.scoring_audit
    if scoring_audit is None:
        raise ValueError("Engine D scoring state is missing its scoring audit")
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
            engine_id="engine_d",
            size=runtime_input.projected_size * size_multiplier,
            planned_loss=planned_loss,
            pair_beta=runtime_input.pair_beta,
        ),
        now=timestamp,
    )


def run_reentry_validation_hook(
    hook: Callable[[EngineDReentryValidationInput], EngineDReentryValidationOutcome] | None,
    runtime_input: EngineDRuntimeInput,
    engine_output: EngineDOutput,
) -> EngineDReentryValidationOutcome | None:
    if hook is None:
        return None
    return hook(
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


def require_selection_entry(scoring_audit: ScoringCandidateAudit) -> SelectionEntry:
    selection_entry = scoring_audit.selection_entry
    if selection_entry is None:
        raise ValueError("Engine D scoring audit is missing its selection entry")
    return selection_entry

# Backward-compatible re-exports for callers that import refusal helpers
# from engine_d_runtime_support directly. Do not add new imports here.
from .engine_d_runtime_support_refusal import (  # noqa: E402,F401
    annotate_forecast_signal_candidate_for_runtime_status,
    resolve_hook_blocked_reason_codes,
)

__all__ = [
    "annotate_forecast_signal_candidate_for_runtime_status",
    "_EngineDScoringState",
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
    "resolve_hook_blocked_reason_codes",
    "run_reentry_validation_hook",
    "to_regime_id",
    "validate_coordination_input",
]
