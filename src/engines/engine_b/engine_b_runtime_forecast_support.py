"""Forecast and downstream truthfulness helpers for the Engine B runtime."""

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
    Side,
    SignalCandidate as DecisionSignalCandidate,
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
from scoring_backbone.scoring_runtime import ScoringCandidateAudit

from .engine_b_runner import EngineBInput, EngineBOutput
from .engine_b_runtime import EngineBRuntimeInput

_ENGINE_B_FORECAST_NORMALIZER_CONFIG = ForecastNormalizerConfig(max_abs_forecast=15.0)
_ENGINE_B_BREAK_EVEN_FILTER_CONFIG = BreakEvenFilterConfig()


@dataclass(frozen=True)
class _EngineBForecastEconomics:
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
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    signal_candidate: DecisionSignalCandidate,
    scoring_audit: ScoringCandidateAudit,
) -> ForecastSignalCandidate | None:
    if runtime_input.strategy_id is None:
        return None
    forecast_economics = _resolve_forecast_economics(runtime_input, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=runtime_input.strategy_id,
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=abs(forecast_economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_forecast_horizon_class(signal_candidate),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=BetStructure.MEAN_REVERT,
        conditioning_state=_build_conditioning_state(
            runtime_input,
            engine_output,
            scoring_audit,
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
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
    scoring_audit: ScoringCandidateAudit,
    *,
    forecast_economics: _EngineBForecastEconomics,
) -> tuple[ConditioningRecord, ...]:
    records = [
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.conviction.{engine_output.conviction.value}",
            value=engine_output.penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.tier.{engine_output.tier_suggestion.value}",
            value=engine_output.penalized_score,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.excess.{engine_output.excess_verdict.value}",
            value=engine_output.excess_score,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.breakout.{engine_output.breakout_verdict.value}",
            value=engine_output.breakout_score,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.cost.{engine_output.cost_verdict.value}",
            value=engine_output.ce_expected,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=forecast_economics.volatility_proxy_conditioning_code,
            value=forecast_economics.normalization.raw_forecast,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_b.forecast.normalized_strength",
            value=forecast_economics.normalization.normalized_forecast,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_resolve_break_even_conditioning_code(forecast_economics.break_even_decision),
            value=forecast_economics.break_even_decision.expected_break_even,
            triggered_no_trade=not forecast_economics.break_even_decision.allowed,
        ),
        _conditioning_record(
            timestamp_ms=runtime_input.timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_resolve_raw_score_parity_conditioning_code(engine_output, scoring_audit),
            value=_resolve_raw_score_parity_delta(engine_output, scoring_audit),
        ),
    ]
    if engine_output.invalidation is not None:
        records.append(
            _conditioning_record(
                timestamp_ms=runtime_input.timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.invalidation.present",
                value=1.0,
            )
        )
    if "b.toxic_flow_fade" in engine_output.reason_codes:
        records.append(
            _conditioning_record(
                timestamp_ms=runtime_input.timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.toxic_flow_fade.active",
                value=1.0,
            )
        )
    if "b.toxic_flow_fade_suppressed.correlation" in engine_output.reason_codes:
        records.append(
            _conditioning_record(
                timestamp_ms=runtime_input.timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.toxic_flow_fade.suppressed.correlation",
                value=1.0,
            )
        )
    records.extend(
        build_scoring_conditioning_records(
            timestamp_ms=runtime_input.timestamp_ms,
            penalties=((penalty.penalty_id, penalty.value) for penalty in scoring_audit.score_penalty_result.penalties),
        )
    )
    return tuple(records)


def _build_forecast_reason_codes(
    engine_output: EngineBOutput,
    scoring_audit: ScoringCandidateAudit,
    *,
    forecast_economics: _EngineBForecastEconomics,
) -> tuple[str, ...]:
    additive_reason_codes: list[str] = [
        f"engine_b.conviction.{engine_output.conviction.value}",
        f"engine_b.excess.{engine_output.excess_verdict.value}",
        f"engine_b.breakout.{engine_output.breakout_verdict.value}",
        f"engine_b.cost.{engine_output.cost_verdict.value}",
        forecast_economics.volatility_proxy_reason_code,
        _resolve_break_even_reason_code(forecast_economics.break_even_decision),
    ]
    if forecast_economics.normalization.clipped:
        additive_reason_codes.append("engine_b.forecast.normalized_forecast_clipped")
    return merge_reason_codes(
        additive_reason_codes,
        engine_output.reason_codes,
        (f"scoring.penalty.{penalty.penalty_id}" for penalty in scoring_audit.score_penalty_result.penalties),
    )


def _build_forecast_versions(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
) -> dict[str, str]:
    scoring_version = engine_output.scoring_version or runtime_input.engine_inputs.scoring_version
    return build_forecast_versions(
        scoring_version=scoring_version,
        calibration_profile_id=engine_output.calibration_profile_id,
        calibration_status=engine_output.calibration_status,
        physics_calibration_profile_id=engine_output.physics_calibration_profile_id,
        physics_calibration_status=engine_output.physics_calibration_status,
    )


def _resolve_invalidation_ref(engine_output: EngineBOutput) -> str | None:
    invalidation = engine_output.invalidation
    if invalidation is None:
        return None
    primary = invalidation.primary_invalidation.strip()
    if primary:
        return primary
    return None


def _resolve_forecast_economics(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
) -> _EngineBForecastEconomics:
    volatility_scale, volatility_proxy_reason_code, volatility_proxy_conditioning_code = _resolve_volatility_proxy(
        runtime_input.engine_inputs
    )
    normalization = normalize_forecast(
        expected_return=max(0.0, runtime_input.engine_inputs.expected_gain - engine_output.expected_cost),
        volatility_scale=volatility_scale,
        forecast_scalar=_ENGINE_B_FORECAST_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_ENGINE_B_FORECAST_NORMALIZER_CONFIG,
    )
    return _EngineBForecastEconomics(
        normalization=normalization,
        break_even_decision=_build_additive_break_even_decision(runtime_input, engine_output),
        volatility_proxy_reason_code=volatility_proxy_reason_code,
        volatility_proxy_conditioning_code=volatility_proxy_conditioning_code,
    )


def _resolve_volatility_proxy(
    engine_inputs: EngineBInput,
) -> tuple[float, str, str]:
    if engine_inputs.local_std > 0.0 and engine_inputs.current_price > 0.0:
        return (
            engine_inputs.local_std / engine_inputs.current_price,
            "engine_b.forecast.volatility_proxy.local_std_relative",
            "engine_internal.engine_b.forecast.volatility_proxy.local_std_relative",
        )
    return (
        max(engine_inputs.delta_safe, 1e-6),
        "engine_b.forecast.volatility_proxy.delta_safe_fallback",
        "engine_internal.engine_b.forecast.volatility_proxy.delta_safe_fallback",
    )


def _build_additive_break_even_decision(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
) -> BreakEvenFilterDecision:
    return evaluate_break_even_filter(
        expected_gain=runtime_input.engine_inputs.expected_gain,
        expected_cost=engine_output.expected_cost,
        candidate_size=runtime_input.engine_inputs.candidate_size,
        delta_safe=runtime_input.engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        ce_min=runtime_input.engine_inputs.ce_min,
        config=_ENGINE_B_BREAK_EVEN_FILTER_CONFIG,
    )


def _resolve_break_even_reason_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_b.economics.break_even_cleared"
    return f"engine_b.economics.{decision.reason_code.lower()}"


def _resolve_break_even_conditioning_code(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_internal.engine_b.break_even.cleared"
    return f"engine_internal.engine_b.break_even.{decision.reason_code.lower()}"


def _resolve_raw_score_parity_conditioning_code(
    engine_output: EngineBOutput,
    scoring_audit: ScoringCandidateAudit,
) -> str:
    # base_matches_runner is the nominal expectation once the runtime rebuilds
    # the full runner feature space. Parity is evaluated on the runner-equivalent
    # base score because the runner clips its raw score to [0, 1] while the
    # scoring backbone keeps the unclipped linear sum in base_raw_score.
    if math.isclose(
        _resolve_runner_equivalent_base_raw_score(scoring_audit),
        engine_output.raw_score,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return "engine_internal.engine_b.runtime.raw_score.base_matches_runner"
    return "engine_internal.engine_b.runtime.raw_score.base_differs_from_runner"


def _resolve_raw_score_parity_delta(
    engine_output: EngineBOutput,
    scoring_audit: ScoringCandidateAudit,
) -> float:
    return _resolve_runner_equivalent_base_raw_score(scoring_audit) - engine_output.raw_score


def _resolve_runner_equivalent_base_raw_score(
    scoring_audit: ScoringCandidateAudit,
) -> float:
    return max(0.0, min(1.0, scoring_audit.raw_score_result.base_raw_score))


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
            "conditioning_state": forecast_signal_candidate.conditioning_state + downstream_conditioning_state,
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
            ("engine_b.runtime.hard_blocked",),
            (
                reason.code
                for reason in (() if scoring_audit is None else scoring_audit.hard_block_decision.reasons)
                if reason.code.strip()
            ),
        )
    if status == "rejected_ranking":
        return ("scoring.engine_b.runtime.rejected_ranking", "engine_b.runtime.rejected_ranking")
    if status == "rejected_portfolio":
        if scoring_audit is not None and scoring_audit.portfolio_result is not None:
            return (
                "portfolio.engine_b.runtime.rejected_portfolio",
                "engine_b.runtime.rejected_portfolio",
                f"portfolio.engine_b.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
                f"engine_b.runtime.rejected_portfolio.{scoring_audit.portfolio_result.verdict.value}",
            )
        return ("portfolio.engine_b.runtime.rejected_portfolio", "engine_b.runtime.rejected_portfolio")
    if status == "risk_rejected":
        return merge_reason_codes(
            ("engine_b.runtime.risk_rejected",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_reduced":
        return merge_reason_codes(
            ("engine_b.runtime.risk_reduced",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    if status == "risk_observe_only":
        return merge_reason_codes(
            ("engine_b.runtime.risk_observe_only",),
            _resolve_runtime_risk_reason_codes(risk_evaluation),
        )
    return ()


def _resolve_runtime_risk_reason_codes(
    risk_evaluation: RiskEvaluation | None,
) -> tuple[str, ...]:
    if risk_evaluation is None:
        return ()
    if risk_evaluation.reason_details:
        return tuple(detail.code for detail in risk_evaluation.reason_details if detail.code.strip())
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
                code="hard_block.engine_b.runtime.hard_blocked",
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
                code="scoring.engine_b.runtime.rejected_ranking",
                value=ranking_score,
                triggered_no_trade=True,
            ),
        )
    if status == "rejected_portfolio":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.PORTFOLIO,
                code="portfolio.engine_b.runtime.rejected_portfolio",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_rejected":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.engine_b.runtime.risk_rejected",
                triggered_no_trade=True,
            ),
        )
    if status == "risk_reduced":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.runtime.risk_reduced",
            ),
        )
    if status == "risk_observe_only":
        return (
            _conditioning_record(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.runtime.risk_observe_only",
            ),
        )
    return ()


def resolve_runtime_economics_reason_codes(
    *,
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
) -> tuple[str, ...]:
    if not _has_additive_economics_context(runtime_input, engine_output):
        return ()
    decision = _build_additive_break_even_decision(runtime_input, engine_output)
    if decision.allowed:
        return ()
    return (_resolve_break_even_reason_code(decision),)


def _has_additive_economics_context(
    runtime_input: EngineBRuntimeInput,
    engine_output: EngineBOutput,
) -> bool:
    if runtime_input.engine_inputs.candidate_size <= 0.0:
        return False
    return (
        engine_output.expected_cost > 0.0
        or engine_output.ce_expected > 0.0
        or not math.isclose(engine_output.ev_net, 0.0)
    )


def resolve_hook_blocked_reason_codes(reason_codes: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(code.strip() for code in reason_codes if code.strip())
    if normalized:
        return normalized
    return ("engine_b.runtime.hook_blocked",)


def _resolve_forecast_horizon_class(
    signal_candidate: DecisionSignalCandidate,
) -> ForecastHorizonClass:
    max_hold_ms = signal_candidate.max_hold_ms
    if max_hold_ms is None:
        return ForecastHorizonClass.MEDIUM
    if max_hold_ms < 60_000:
        return ForecastHorizonClass.INTRABAR
    if max_hold_ms <= 15 * 60_000:
        return ForecastHorizonClass.SHORT
    if max_hold_ms <= 4 * 60 * 60_000:
        return ForecastHorizonClass.MEDIUM
    return ForecastHorizonClass.LONG


__all__ = [
    "annotate_forecast_signal_candidate_for_runtime_status",
    "build_forecast_signal_candidate",
    "resolve_hook_blocked_reason_codes",
    "resolve_runtime_economics_reason_codes",
]
