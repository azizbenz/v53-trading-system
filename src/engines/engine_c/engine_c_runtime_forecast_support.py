"""Forecast and downstream truthfulness helpers for the Engine C runtime."""

from __future__ import annotations

from dataclasses import dataclass
import math

from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    SignalCandidate,
)
from interface_contracts.forecast_contracts import build_scoring_conditioning_records, merge_reason_codes
from risk_backbone.risk_runtime import RiskEvaluation
from scoring_backbone import (
    BreakEvenFilterConfig,
    BreakEvenFilterDecision,
    ForecastNormalizationResult,
    ForecastNormalizerConfig,
    evaluate_break_even_filter,
    normalize_forecast,
)
from scoring_backbone.scoring_runtime import ScoringCandidateAudit

from .engine_c_runner import EngineCInput, EngineCOutput

_ENGINE_C_FORECAST_NORMALIZER_CONFIG = ForecastNormalizerConfig(max_abs_forecast=15.0)
_ENGINE_C_BREAK_EVEN_FILTER_CONFIG = BreakEvenFilterConfig()


@dataclass(frozen=True)
class _EngineCForecastEconomics:
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


def build_forecast_signal_candidate(
    *,
    strategy_id: str | None,
    timestamp_ms: int,
    engine_inputs: EngineCInput,
    engine_output: EngineCOutput,
    signal_candidate: SignalCandidate,
    scoring_audit: ScoringCandidateAudit,
) -> ForecastSignalCandidate | None:
    if strategy_id is None:
        return None
    forecast_economics = _resolve_forecast_economics(engine_inputs, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id,
        forecast_direction=1.0 if signal_candidate.side.value == "buy" else -1.0,
        forecast_strength=abs(forecast_economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_forecast_horizon_class(engine_inputs, signal_candidate),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=BetStructure.BREAKOUT,
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
        versions=_build_forecast_versions(engine_inputs, engine_output),
        confidence_band=signal_candidate.confidence,
    )


def _build_conditioning_state(
    *,
    timestamp_ms: int,
    engine_output: EngineCOutput,
    scoring_audit: ScoringCandidateAudit,
    forecast_economics: _EngineCForecastEconomics,
) -> tuple[ConditioningRecord, ...]:
    runtime_penalized_score = max(
        0.0,
        scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
    )
    if engine_output.microstructure_missing:
        microstructure_code = "engine_internal.engine_c.microstructure.missing"
    elif engine_output.microstructure_contradictory:
        microstructure_code = "engine_internal.engine_c.microstructure.contradictory"
    elif engine_output.microstructure_gate_applied:
        microstructure_code = "engine_internal.engine_c.microstructure.confirmed"
    elif engine_output.microstructure_required:
        microstructure_code = "engine_internal.engine_c.microstructure.required"
    else:
        microstructure_code = "engine_internal.engine_c.microstructure.not_applied"
    records = [
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_c.conviction.{engine_output.conviction.value}",
            value=engine_output.penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_c.score.engine_local",
            value=engine_output.penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_c.score.runtime_downstream",
            value=runtime_penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_resolve_raw_score_parity_conditioning_code(engine_output, scoring_audit),
            value=_resolve_raw_score_parity_delta(engine_output, scoring_audit),
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_c.tier.{engine_output.tier_suggestion.value}",
            value=engine_output.penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_c.breakout.{engine_output.breakout_type or 'unknown'}",
            value=engine_output.breakout_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_c.continuation.{engine_output.continuation_context or 'unknown'}",
            value=engine_output.continuation_score,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=microstructure_code,
            value=1.0 if engine_output.microstructure_gate_applied or engine_output.microstructure_required else 0.0,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=forecast_economics.volatility_proxy_conditioning_code,
            value=forecast_economics.normalization.raw_forecast,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_c.forecast.normalized_strength",
            value=forecast_economics.normalization.normalized_forecast,
        ),
        _conditioning_record(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_resolve_break_even_conditioning_code(forecast_economics.break_even_decision),
            value=forecast_economics.break_even_decision.expected_break_even,
            triggered_no_trade=not forecast_economics.break_even_decision.allowed,
        ),
    ]
    if engine_output.invalidation is not None:
        records.append(
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_c.invalidation.present",
                value=1.0,
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
    engine_output: EngineCOutput,
    scoring_audit: ScoringCandidateAudit,
    *,
    forecast_economics: _EngineCForecastEconomics,
) -> tuple[str, ...]:
    microstructure_code = (
        "engine_c.microstructure.missing"
        if engine_output.microstructure_missing
        else "engine_c.microstructure.contradictory"
        if engine_output.microstructure_contradictory
        else "engine_c.microstructure.confirmed"
        if engine_output.microstructure_gate_applied
        else "engine_c.microstructure.required"
        if engine_output.microstructure_required
        else "engine_c.microstructure.not_applied"
    )
    additive_reason_codes = [
        microstructure_code,
        forecast_economics.volatility_proxy_reason_code,
        _resolve_break_even_reason_code(forecast_economics.break_even_decision),
    ]
    if forecast_economics.normalization.clipped:
        additive_reason_codes.append("engine_c.forecast.normalized_forecast_clipped")
    return merge_reason_codes(
        engine_output.reason_codes,
        additive_reason_codes,
        (f"scoring.penalty.{penalty.penalty_id}" for penalty in scoring_audit.score_penalty_result.penalties),
    )


def _build_forecast_versions(
    engine_inputs: EngineCInput,
    engine_output: EngineCOutput,
) -> dict[str, str]:
    return {
        "scoring_version": engine_output.scoring_version or engine_inputs.scoring_version,
        "runtime_adapter_version": "engine_c.forecast_adapter.v1",
    }


def _resolve_invalidation_ref(engine_output: EngineCOutput) -> str | None:
    if engine_output.invalidation is None:
        return None
    invalidation = engine_output.invalidation
    return (
        f"engine_c.invalidation.{invalidation.reference_source or 'unknown'}"
        f".stop.{invalidation.stop_price:.8f}"
        f".target.{invalidation.target_price:.8f}"
        f".risk_multiple.{invalidation.risk_multiple:.6f}"
    )


def _resolve_forecast_economics(
    engine_inputs: EngineCInput,
    engine_output: EngineCOutput,
) -> _EngineCForecastEconomics:
    volatility_scale, volatility_proxy_reason_code, volatility_proxy_conditioning_code = _resolve_volatility_proxy(
        engine_inputs
    )
    normalization = normalize_forecast(
        expected_return=max(0.0, engine_inputs.expected_gain - engine_output.expected_cost),
        volatility_scale=volatility_scale,
        forecast_scalar=_ENGINE_C_FORECAST_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_ENGINE_C_FORECAST_NORMALIZER_CONFIG,
    )
    return _EngineCForecastEconomics(
        normalization=normalization,
        break_even_decision=_build_additive_break_even_decision(engine_inputs, engine_output),
        volatility_proxy_reason_code=volatility_proxy_reason_code,
        volatility_proxy_conditioning_code=volatility_proxy_conditioning_code,
    )


def _resolve_volatility_proxy(
    engine_inputs: EngineCInput,
) -> tuple[float, str, str]:
    if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
        return (
            engine_inputs.realized_vol_current,
            "engine_c.forecast.volatility_proxy.realized_vol_current",
            "engine_internal.engine_c.forecast.volatility_proxy.realized_vol_current",
        )
    if engine_inputs.realized_vol_at_break is not None and engine_inputs.realized_vol_at_break > 0.0:
        return (
            engine_inputs.realized_vol_at_break,
            "engine_c.forecast.volatility_proxy.realized_vol_at_break_fallback",
            "engine_internal.engine_c.forecast.volatility_proxy.realized_vol_at_break_fallback",
        )
    return (
        max(engine_inputs.delta_safe, 1e-6),
        "engine_c.forecast.volatility_proxy.delta_safe_fallback",
        "engine_internal.engine_c.forecast.volatility_proxy.delta_safe_fallback",
    )


def _build_additive_break_even_decision(
    engine_inputs: EngineCInput,
    engine_output: EngineCOutput,
) -> BreakEvenFilterDecision:
    return evaluate_break_even_filter(
        expected_gain=engine_inputs.expected_gain,
        expected_cost=engine_output.expected_cost,
        candidate_size=engine_inputs.candidate_size,
        delta_safe=engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        ce_min=engine_inputs.ce_min,
        config=_ENGINE_C_BREAK_EVEN_FILTER_CONFIG,
    )


def _resolve_break_even_reason_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_c.economics.break_even_cleared"
    return f"engine_c.economics.{decision.reason_code.lower()}"


def _resolve_break_even_conditioning_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_internal.engine_c.break_even.cleared"
    return f"engine_internal.engine_c.break_even.{decision.reason_code.lower()}"


def _resolve_forecast_horizon_class(
    engine_inputs: EngineCInput,
    signal_candidate: SignalCandidate,
) -> ForecastHorizonClass:
    max_hold_ms = signal_candidate.max_hold_ms
    if max_hold_ms is None:
        max_hold_ms = int(engine_inputs.holding_period * 3600 * 1000)
    if max_hold_ms < 60_000:
        return ForecastHorizonClass.INTRABAR
    if max_hold_ms <= 15 * 60_000:
        return ForecastHorizonClass.SHORT
    if max_hold_ms <= 4 * 60 * 60_000:
        return ForecastHorizonClass.MEDIUM
    return ForecastHorizonClass.LONG


def _resolve_raw_score_parity_conditioning_code(
    engine_output: EngineCOutput,
    scoring_audit: ScoringCandidateAudit,
) -> str:
    if math.isclose(
        scoring_audit.raw_score_result.base_raw_score,
        engine_output.penalized_score,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return "engine_internal.engine_c.runtime.raw_score.base_matches_runner"
    return "engine_internal.engine_c.runtime.raw_score.base_differs_from_runner"


def _resolve_raw_score_parity_delta(
    engine_output: EngineCOutput,
    scoring_audit: ScoringCandidateAudit,
) -> float:
    return scoring_audit.raw_score_result.base_raw_score - engine_output.penalized_score


def resolve_hook_blocked_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(code.strip() for code in reason_codes if code.strip())
    if normalized:
        return normalized
    return ("engine_c.runtime.hook_blocked",)


def annotate_forecast_signal_candidate_for_runtime_status(
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


def _resolve_runtime_forecast_reason_codes(
    *,
    status: str,
    scoring_audit: ScoringCandidateAudit | None,
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if status == "hard_blocked":
        return merge_reason_codes(
            ("engine_c.runtime.hard_blocked",),
            (
                reason.code
                for reason in (() if scoring_audit is None else scoring_audit.hard_block_decision.reasons)
                if reason.code.strip()
            ),
        )
    if status == "rejected_ranking":
        return ("scoring.engine_c.runtime.rejected_ranking", "engine_c.runtime.rejected_ranking")
    if status == "rejected_portfolio":
        if scoring_audit is not None and scoring_audit.portfolio_result is not None:
            return (
                "portfolio.engine_c.runtime.rejected_portfolio",
                "engine_c.runtime.rejected_portfolio",
                f"portfolio.engine_c.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
                f"engine_c.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
            )
        return ("portfolio.engine_c.runtime.rejected_portfolio", "engine_c.runtime.rejected_portfolio")
    if status == "risk_rejected":
        return merge_reason_codes(
            ("engine_c.runtime.risk_rejected",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_reduced":
        return merge_reason_codes(
            ("engine_c.runtime.risk_reduced",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_observe_only":
        return merge_reason_codes(
            ("engine_c.runtime.risk_observe_only",),
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
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.engine_c.runtime.hard_blocked",
                value=hard_block_count,
                triggered_no_trade=True,
            ),
        )
    if status == "rejected_ranking":
        ranking_score = None
        if scoring_audit is not None and scoring_audit.selection_entry is not None:
            ranking_score = scoring_audit.selection_entry.ranking_score
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.SCORING,
                code="scoring.engine_c.runtime.rejected_ranking",
                value=ranking_score,
                triggered_no_trade=True,
            ),
        )
    if status == "rejected_portfolio":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.PORTFOLIO,
                code="portfolio.engine_c.runtime.rejected_portfolio",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_rejected":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.engine_c.runtime.risk_rejected",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_reduced":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_c.runtime.risk_reduced",
            ),
        )
    if status == "risk_observe_only":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_c.runtime.risk_observe_only",
            ),
        )
    return ()


__all__ = [
    "annotate_forecast_signal_candidate_for_runtime_status",
    "build_forecast_signal_candidate",
    "resolve_hook_blocked_reason_codes",
]
