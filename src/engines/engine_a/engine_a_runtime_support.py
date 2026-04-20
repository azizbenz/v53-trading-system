"""Private helper functions for the Engine A runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
import math

from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    EngineId,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    RegimeId,
    RefusalCategory,
    RefusalRecord,
    Side,
    SignalCandidate as DecisionSignalCandidate,
    SignalType,
)
from interface_contracts.forecast_contracts import (
    build_forecast_versions,
    build_scoring_conditioning_records,
    merge_reason_codes,
)
from risk_backbone.risk_runtime import RiskEvaluation
from scoring_backbone import (
    BreakEvenFilterConfig,
    BreakEvenFilterDecision,
    ForecastNormalizationResult,
    ForecastNormalizerConfig,
    evaluate_break_even_filter,
    normalize_forecast,
)
from scoring_backbone.scoring_runtime import ScoringCandidateAudit, ScoringRoundResult

from .engine_a_runner import EngineAInput, EngineALogEntry, EngineAOutput

_ENGINE_A_FORECAST_NORMALIZER_CONFIG = ForecastNormalizerConfig()
_ENGINE_A_BREAK_EVEN_FILTER_CONFIG = BreakEvenFilterConfig()


@dataclass(frozen=True)
class _EngineAForecastEconomics:
    normalization: ForecastNormalizationResult
    break_even_decision: BreakEvenFilterDecision
    volatility_proxy_reason_code: str
    volatility_proxy_conditioning_code: str


def _conditioning_record(
    *,
    timestamp_ms: int,
    family: ConditioningFamily,
    code: str,
    value: float | None = None,
    triggered_no_trade: bool = False,
) -> ConditioningRecord:
    return ConditioningRecord(
        timestamp_ms=timestamp_ms,
        family=family,
        code=code,
        value=value,
        triggered_no_trade=triggered_no_trade,
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
    inputs: EngineAInput,
    engine_output: EngineAOutput,
    timestamp_ms: int,
) -> DecisionSignalCandidate:
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

    return DecisionSignalCandidate(
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


def _build_forecast_signal_candidate(
    *,
    strategy_id: str | None,
    timestamp_ms: int,
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
    signal_candidate: DecisionSignalCandidate,
    scoring_audit: ScoringCandidateAudit,
) -> ForecastSignalCandidate | None:
    if strategy_id is None:
        return None
    forecast_economics = _resolve_forecast_economics(engine_inputs, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id,
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=abs(forecast_economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_forecast_horizon_class(
            holding_period_hours=engine_inputs.holding_period,
            signal_candidate=signal_candidate,
        ),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=_resolve_bet_structure(signal_candidate.side),
        conditioning_state=_build_conditioning_state(
            timestamp_ms=timestamp_ms,
            engine_output=engine_output,
            scoring_audit=scoring_audit,
            forecast_economics=forecast_economics,
        ),
        expected_cost=engine_output.expected_cost,
        expected_break_even=forecast_economics.break_even_decision.expected_break_even,
        expected_ce=engine_output.ce_expected,
        expected_gain=engine_inputs.expected_gain,
        invalidation_ref=_resolve_invalidation_ref(engine_output),
        reason_codes=_build_forecast_reason_codes(
            engine_output,
            scoring_audit,
            forecast_economics=forecast_economics,
        ),
        versions=_build_forecast_versions(
            scoring_version=engine_output.scoring_version or engine_inputs.scoring_version,
            engine_output=engine_output,
        ),
        confidence_band=signal_candidate.confidence,
    )


def _build_conditioning_state(
    *,
    timestamp_ms: int,
    engine_output: EngineAOutput,
    scoring_audit: ScoringCandidateAudit,
    forecast_economics: _EngineAForecastEconomics,
) -> tuple[ConditioningRecord, ...]:
    records = [
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=f"engine_internal.engine_a.conviction.{engine_output.conviction.value}", value=engine_output.raw_score),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=f"engine_internal.engine_a.tier.{engine_output.tier_suggestion.value}", value=engine_output.raw_score),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=f"engine_internal.engine_a.structure.{engine_output.structure_verdict.value}", value=engine_output.block_scores.get("structure", 0.0)),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=f"engine_internal.engine_a.context.{engine_output.context_verdict.value}", value=engine_output.block_scores.get("context", 0.0)),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=f"engine_internal.engine_a.cost.{engine_output.cost_verdict.value}", value=engine_output.ce_expected),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=forecast_economics.volatility_proxy_conditioning_code, value=forecast_economics.normalization.raw_forecast),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code="engine_internal.engine_a.forecast.normalized_strength", value=forecast_economics.normalization.normalized_forecast),
        _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code=_resolve_break_even_conditioning_code(forecast_economics.break_even_decision), value=forecast_economics.break_even_decision.expected_break_even, triggered_no_trade=not forecast_economics.break_even_decision.allowed),
    ]
    invalidation_ref = _resolve_invalidation_ref(engine_output)
    if invalidation_ref is not None:
        records.append(
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_a.invalidation.present",
                value=1.0,
            )
        )
    records.extend(
        build_scoring_conditioning_records(
            timestamp_ms=timestamp_ms,
            penalties=(
                (penalty.penalty_id, penalty.value)
                for penalty in scoring_audit.score_penalty_result.penalties
            ),
        )
    )
    return tuple(records)


def _build_forecast_reason_codes(
    engine_output: EngineAOutput,
    scoring_audit: ScoringCandidateAudit,
    *,
    forecast_economics: _EngineAForecastEconomics,
) -> tuple[str, ...]:
    additive_reason_codes: list[str] = [
        f"engine_a.structure.{engine_output.structure_verdict.value}",
        f"engine_a.context.{engine_output.context_verdict.value}",
        f"engine_a.cost.{engine_output.cost_verdict.value}",
        f"engine_a.conviction.{engine_output.conviction.value}",
        forecast_economics.volatility_proxy_reason_code,
        _resolve_break_even_reason_code(forecast_economics.break_even_decision),
    ]
    if forecast_economics.normalization.clipped:
        additive_reason_codes.append("engine_a.forecast.normalized_forecast_clipped")
    return merge_reason_codes(
        engine_output.reason_codes,
        additive_reason_codes,
        (
            f"scoring.penalty.{penalty.penalty_id}"
            for penalty in scoring_audit.score_penalty_result.penalties
        ),
    )


def _build_forecast_versions(
    *,
    scoring_version: str,
    engine_output: EngineAOutput,
) -> dict[str, str]:
    return build_forecast_versions(
        scoring_version=scoring_version,
        calibration_profile_id=engine_output.calibration_profile_id,
        calibration_status=engine_output.calibration_status,
        physics_calibration_profile_id=engine_output.physics_calibration_profile_id,
        physics_calibration_status=engine_output.physics_calibration_status,
    )


def _resolve_invalidation_ref(engine_output: EngineAOutput) -> str | None:
    invalidation = engine_output.invalidation
    if invalidation is None:
        return None
    primary = invalidation.primary_invalidation.strip()
    if primary:
        return primary
    return None


def _resolve_forecast_horizon_class(
    *,
    holding_period_hours: float,
    signal_candidate: DecisionSignalCandidate,
) -> ForecastHorizonClass:
    max_hold_ms = signal_candidate.max_hold_ms
    if max_hold_ms is None:
        max_hold_ms = int(holding_period_hours * 3600 * 1000)
    if max_hold_ms < 60_000:
        return ForecastHorizonClass.INTRABAR
    if max_hold_ms <= 15 * 60_000:
        return ForecastHorizonClass.SHORT
    if max_hold_ms <= 4 * 60 * 60_000:
        return ForecastHorizonClass.MEDIUM
    return ForecastHorizonClass.LONG


def _resolve_bet_structure(side: Side) -> BetStructure:
    if side == Side.BUY:
        return BetStructure.DIRECTIONAL_LONG
    return BetStructure.DIRECTIONAL_SHORT


def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    try:
        return RegimeId(normalized)
    except ValueError:
        return RegimeId.UNKNOWN


def _build_runtime_refusal_record(
    *,
    timestamp_ms: int,
    engine_inputs: EngineAInput,
    status: str,
    engine_output: EngineAOutput,
    log_entries: tuple[EngineALogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> RefusalRecord | None:
    category = _resolve_runtime_refusal_category(status)
    if category is None:
        return None
    return RefusalRecord(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.A,
        category=category,
        reason_codes=_resolve_runtime_refusal_reason_codes(
            engine_inputs=engine_inputs,
            status=status,
            engine_output=engine_output,
            log_entries=log_entries,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
        ),
    )


def _annotate_forecast_signal_candidate_for_runtime_status(
    forecast_signal_candidate: ForecastSignalCandidate | None,
    *,
    timestamp_ms: int,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> ForecastSignalCandidate | None:
    if forecast_signal_candidate is None:
        return None
    downstream_reason_codes = _resolve_runtime_forecast_reason_codes(
        status=status,
        scoring_audit=scoring_audit,
        risk_evaluation=risk_evaluation,
    )
    downstream_conditioning_state = _build_runtime_downstream_conditioning_records(
        timestamp_ms=timestamp_ms,
        status=status,
        scoring_audit=scoring_audit,
    )
    if not downstream_reason_codes and not downstream_conditioning_state:
        return forecast_signal_candidate
    return forecast_signal_candidate.model_copy(
        update={
            "reason_codes": merge_reason_codes(
                forecast_signal_candidate.reason_codes,
                downstream_reason_codes,
            ),
            "conditioning_state": (
                forecast_signal_candidate.conditioning_state + downstream_conditioning_state
            ),
        }
    )


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


def _resolve_hook_blocked_reason_codes(
    reason_codes: tuple[str, ...],
) -> tuple[str, ...]:
    normalized = tuple(code.strip() for code in reason_codes if code.strip())
    if normalized:
        return normalized
    return ("engine_a.runtime.hook_blocked",)


def _resolve_runtime_refusal_reason_codes(
    *,
    engine_inputs: EngineAInput,
    status: str,
    engine_output: EngineAOutput,
    log_entries: tuple[EngineALogEntry, ...],
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    economics_reason_codes = _resolve_runtime_economics_reason_codes(
        engine_inputs=engine_inputs,
        engine_output=engine_output,
    )
    if status == "no_trade":
        if engine_output.reason_codes:
            return merge_reason_codes(engine_output.reason_codes, economics_reason_codes)
        if engine_output.no_trade_reasons:
            return merge_reason_codes(
                (
                    f"engine_a.no_trade.{reason.value}"
                    for reason in engine_output.no_trade_reasons
                ),
                economics_reason_codes,
            )
        return merge_reason_codes(("engine_a.runtime.no_trade",), economics_reason_codes)
    if status == "hook_blocked":
        hook_reason_codes = _extract_log_reason_codes(log_entries, "engine_a_hook_blocked")
        if hook_reason_codes:
            return merge_reason_codes(hook_reason_codes, economics_reason_codes)
        return merge_reason_codes(("engine_a.runtime.hook_blocked",), economics_reason_codes)
    if status == "circuit_breaker_blocked":
        if engine_output.reason_codes:
            return merge_reason_codes(engine_output.reason_codes, economics_reason_codes)
        return merge_reason_codes(("engine_a.runtime.circuit_breaker_blocked",), economics_reason_codes)
    if status == "hard_blocked":
        if scoring_audit is not None and scoring_audit.hard_block_decision.reasons:
            return merge_reason_codes(
                (
                    reason.code
                    for reason in scoring_audit.hard_block_decision.reasons
                ),
                economics_reason_codes,
            )
        return merge_reason_codes(
            ("hard_block.engine_a.runtime.hard_blocked", "engine_a.runtime.hard_blocked"),
            economics_reason_codes,
        )
    if status == "rejected_ranking":
        return merge_reason_codes(
            ("scoring.engine_a.runtime.rejected_ranking", "engine_a.runtime.rejected_ranking"),
            economics_reason_codes,
        )
    if status == "rejected_portfolio":
        return merge_reason_codes(
            ("portfolio.engine_a.runtime.rejected_portfolio", "engine_a.runtime.rejected_portfolio"),
            economics_reason_codes,
        )
    if status == "risk_rejected":
        if risk_evaluation is not None:
            if risk_evaluation.reason_details:
                return merge_reason_codes(
                    (detail.code for detail in risk_evaluation.reason_details),
                    economics_reason_codes,
                )
            if risk_evaluation.dominant_reason_code:
                return merge_reason_codes((risk_evaluation.dominant_reason_code,), economics_reason_codes)
        return merge_reason_codes(
            ("hard_block.engine_a.runtime.risk_rejected", "engine_a.runtime.risk_rejected"),
            economics_reason_codes,
        )
    return merge_reason_codes(("engine_a.runtime.unknown_refusal",), economics_reason_codes)


def _resolve_runtime_forecast_reason_codes(
    *,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if status == "hard_blocked":
        return merge_reason_codes(
            ("hard_block.engine_a.runtime.hard_blocked", "engine_a.runtime.hard_blocked"),
            (
                reason.code
                for reason in (() if scoring_audit is None else scoring_audit.hard_block_decision.reasons)
                if reason.code.strip()
            ),
        )
    if status == "rejected_ranking":
        return ("scoring.engine_a.runtime.rejected_ranking", "engine_a.runtime.rejected_ranking")
    if status == "rejected_portfolio":
        if scoring_audit is not None and scoring_audit.portfolio_result is not None:
            return (
                "portfolio.engine_a.runtime.rejected_portfolio",
                "engine_a.runtime.rejected_portfolio",
                f"portfolio.engine_a.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
                f"engine_a.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
            )
        return ("portfolio.engine_a.runtime.rejected_portfolio", "engine_a.runtime.rejected_portfolio")
    if status == "risk_rejected":
        return merge_reason_codes(
            ("hard_block.engine_a.runtime.risk_rejected", "engine_a.runtime.risk_rejected"),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_reduced":
        return merge_reason_codes(
            ("engine_a.runtime.risk_reduced",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_observe_only":
        return merge_reason_codes(
            ("engine_a.runtime.risk_observe_only",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    return ()


def _resolve_runtime_risk_reason_codes(
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if risk_evaluation is None:
        return ()
    if risk_evaluation.reason_details:
        return tuple(
            detail.code
            for detail in risk_evaluation.reason_details
            if detail.code.strip()
        )
    dominant_reason_code = (risk_evaluation.dominant_reason_code or "").strip()
    if dominant_reason_code:
        return (dominant_reason_code,)
    return ()


def _build_runtime_downstream_conditioning_records(
    *,
    timestamp_ms: int,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
) -> tuple[ConditioningRecord, ...]:
    if status == "hard_blocked":
        hard_block_count = 0.0 if scoring_audit is None else float(len(scoring_audit.hard_block_decision.reasons))
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.HARD_BLOCK, code="hard_block.engine_a.runtime.hard_blocked", value=hard_block_count, triggered_no_trade=True),
        )
    if status == "rejected_ranking":
        ranking_score = None
        if scoring_audit is not None and scoring_audit.selection_entry is not None:
            ranking_score = scoring_audit.selection_entry.ranking_score
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.SCORING, code="scoring.engine_a.runtime.rejected_ranking", value=ranking_score, triggered_no_trade=True),
        )
    if status == "rejected_portfolio":
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.PORTFOLIO, code="portfolio.engine_a.runtime.rejected_portfolio", triggered_no_trade=True),
        )
    if status == "risk_rejected":
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.HARD_BLOCK, code="hard_block.engine_a.runtime.risk_rejected", triggered_no_trade=True),
        )
    if status == "risk_reduced":
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code="engine_internal.engine_a.runtime.risk_reduced"),
        )
    if status == "risk_observe_only":
        return (
            _conditioning_record(timestamp_ms=timestamp_ms, family=ConditioningFamily.ENGINE_INTERNAL, code="engine_internal.engine_a.runtime.risk_observe_only"),
        )
    return ()


def _resolve_forecast_economics(
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
) -> _EngineAForecastEconomics:
    volatility_scale, volatility_proxy_reason_code, volatility_proxy_conditioning_code = _resolve_volatility_proxy(
        engine_inputs
    )
    normalization = normalize_forecast(
        expected_return=max(0.0, engine_inputs.expected_gain - engine_output.expected_cost),
        volatility_scale=volatility_scale,
        forecast_scalar=_ENGINE_A_FORECAST_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_ENGINE_A_FORECAST_NORMALIZER_CONFIG,
    )
    return _EngineAForecastEconomics(
        normalization=normalization,
        break_even_decision=_build_additive_break_even_decision(engine_inputs, engine_output),
        volatility_proxy_reason_code=volatility_proxy_reason_code,
        volatility_proxy_conditioning_code=volatility_proxy_conditioning_code,
    )


def _resolve_volatility_proxy(
    engine_inputs: EngineAInput,
) -> tuple[float, str, str]:
    if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
        return (
            engine_inputs.realized_vol_current,
            "engine_a.forecast.volatility_proxy.realized_vol_current",
            "engine_internal.engine_a.forecast.volatility_proxy.realized_vol_current",
        )
    if engine_inputs.realized_kernel_vol_scale is not None and engine_inputs.realized_kernel_vol_scale > 0.0:
        return (
            engine_inputs.realized_kernel_vol_scale,
            "engine_a.forecast.volatility_proxy.realized_kernel_scale",
            "engine_internal.engine_a.forecast.volatility_proxy.realized_kernel_scale",
        )
    return (
        max(engine_inputs.delta_safe, 1e-6),
        "engine_a.forecast.volatility_proxy.delta_safe_fallback",
        "engine_internal.engine_a.forecast.volatility_proxy.delta_safe_fallback",
    )


def _build_additive_break_even_decision(
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
) -> BreakEvenFilterDecision:
    return evaluate_break_even_filter(
        expected_gain=engine_inputs.expected_gain,
        expected_cost=engine_output.expected_cost,
        candidate_size=engine_inputs.candidate_size,
        delta_safe=engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        ce_min=engine_inputs.ce_min,
        config=_ENGINE_A_BREAK_EVEN_FILTER_CONFIG,
    )


def _resolve_break_even_reason_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_a.economics.break_even_cleared"
    return f"engine_a.economics.{decision.reason_code.lower()}"


def _resolve_break_even_conditioning_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_internal.engine_a.break_even.cleared"
    return f"engine_internal.engine_a.break_even.{decision.reason_code.lower()}"


def _resolve_runtime_economics_reason_codes(
    *,
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
) -> tuple[str, ...]:
    if not _has_additive_economics_context(engine_inputs, engine_output):
        return ()
    decision = _build_additive_break_even_decision(engine_inputs, engine_output)
    if decision.allowed:
        return ()
    return (_resolve_break_even_reason_code(decision),)


def _has_additive_economics_context(
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
) -> bool:
    if engine_inputs.candidate_size <= 0.0:
        return False
    return (
        engine_output.expected_cost > 0.0
        or engine_output.ce_expected > 0.0
        or not math.isclose(engine_output.ev_net, 0.0)
    )


def _extract_log_reason_codes(
    log_entries: tuple[EngineALogEntry, ...],
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
    "_annotate_forecast_signal_candidate_for_runtime_status",
    "_build_forecast_signal_candidate",
    "_build_runtime_refusal_record",
    "_build_signal_candidate",
    "_require_scoring_version",
    "_resolve_hook_blocked_reason_codes",
    "_resolve_runtime_now",
    "_resolve_scoring_audit",
]
