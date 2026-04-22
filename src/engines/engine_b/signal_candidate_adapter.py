from __future__ import annotations

from dataclasses import dataclass

from interface_contracts.decision_contracts import SignalCandidate as DecisionSignalCandidate
from interface_contracts.domain_types import Side
from interface_contracts.forecast_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    build_forecast_versions,
    merge_reason_codes,
)
from engines.engine_b.engine_b_runner import EngineBDecision, EngineBInput, EngineBOutput
from scoring_backbone.break_even_filter import (
    BreakEvenFilterConfig,
    BreakEvenFilterDecision,
    evaluate_break_even_filter,
)
from scoring_backbone.forecast_normalizer import (
    ForecastNormalizationResult,
    ForecastNormalizerConfig,
    normalize_forecast,
)

_NORMALIZER_CONFIG = ForecastNormalizerConfig(max_abs_forecast=15.0)
_BREAK_EVEN_CONFIG = BreakEvenFilterConfig()


@dataclass(frozen=True)
class _ForecastEconomicsB:
    normalization: ForecastNormalizationResult
    break_even_decision: BreakEvenFilterDecision
    volatility_proxy_reason_code: str
    volatility_proxy_conditioning_code: str


def build_signal_candidate_b(
    engine_output: EngineBOutput,
    signal_candidate: DecisionSignalCandidate,
    *,
    strategy_id: str,
    engine_inputs: EngineBInput,
    timestamp_ms: int,
) -> ForecastSignalCandidate | None:
    if strategy_id is None or not strategy_id.strip():
        return None
    if engine_output.decision != EngineBDecision.EMIT:
        return None

    economics = _resolve_forecast_economics_b(engine_inputs, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id.strip(),
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=abs(economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_horizon_class_b(signal_candidate),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=BetStructure.MEAN_REVERT,
        conditioning_state=_build_conditioning_state_b(
            timestamp_ms=timestamp_ms,
            engine_output=engine_output,
            economics=economics,
        ),
        expected_cost=engine_output.expected_cost,
        expected_break_even=economics.break_even_decision.expected_break_even,
        expected_ce=engine_output.ce_expected,
        expected_gain=engine_inputs.expected_gain,
        invalidation_ref=_resolve_invalidation_ref_b(engine_output),
        reason_codes=_build_reason_codes_b(engine_output, economics),
        versions=build_forecast_versions(
            scoring_version=engine_output.scoring_version or engine_inputs.scoring_version,
            calibration_profile_id=engine_output.calibration_profile_id,
            calibration_status=engine_output.calibration_status,
            physics_calibration_profile_id=engine_output.physics_calibration_profile_id,
            physics_calibration_status=engine_output.physics_calibration_status,
        ),
        confidence_band=signal_candidate.confidence,
    )


def _resolve_forecast_economics_b(
    engine_inputs: EngineBInput,
    engine_output: EngineBOutput,
) -> _ForecastEconomicsB:
    vol_scale, reason_code, conditioning_code = _resolve_volatility_proxy_b(engine_inputs)
    normalization = normalize_forecast(
        expected_return=max(0.0, engine_inputs.expected_gain - engine_output.expected_cost),
        volatility_scale=vol_scale,
        forecast_scalar=_NORMALIZER_CONFIG.target_mean_abs_forecast,
        config=_NORMALIZER_CONFIG,
    )
    break_even = evaluate_break_even_filter(
        expected_gain=engine_inputs.expected_gain,
        expected_cost=engine_output.expected_cost,
        candidate_size=engine_inputs.candidate_size,
        delta_safe=engine_inputs.delta_safe,
        expected_ce=engine_output.ce_expected,
        ce_min=engine_inputs.ce_min,
        config=_BREAK_EVEN_CONFIG,
    )
    return _ForecastEconomicsB(
        normalization=normalization,
        break_even_decision=break_even,
        volatility_proxy_reason_code=reason_code,
        volatility_proxy_conditioning_code=conditioning_code,
    )


def _resolve_volatility_proxy_b(
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


def _resolve_horizon_class_b(
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


def _build_conditioning_state_b(
    *,
    timestamp_ms: int,
    engine_output: EngineBOutput,
    economics: _ForecastEconomicsB,
) -> tuple[ConditioningRecord, ...]:
    records = [
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.conviction.{engine_output.conviction.value}",
            value=engine_output.penalized_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.tier.{engine_output.tier_suggestion.value}",
            value=engine_output.penalized_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.excess.{engine_output.excess_verdict.value}",
            value=engine_output.excess_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.breakout.{engine_output.breakout_verdict.value}",
            value=engine_output.breakout_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_b.cost.{engine_output.cost_verdict.value}",
            value=engine_output.ce_expected,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=economics.volatility_proxy_conditioning_code,
            value=economics.normalization.raw_forecast,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code="engine_internal.engine_b.forecast.normalized_strength",
            value=economics.normalization.normalized_forecast,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_break_even_conditioning_code_b(economics.break_even_decision),
            value=economics.break_even_decision.expected_break_even,
            triggered_no_trade=not economics.break_even_decision.allowed,
        ),
    ]
    if _resolve_invalidation_ref_b(engine_output) is not None:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.invalidation.present",
                value=1.0,
            )
        )
    if "b.toxic_flow_fade" in engine_output.reason_codes:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.toxic_flow_fade.active",
                value=1.0,
            )
        )
    if "b.toxic_flow_fade_suppressed.correlation" in engine_output.reason_codes:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_b.toxic_flow_fade.suppressed.correlation",
                value=1.0,
            )
        )
    return tuple(records)


def _build_reason_codes_b(
    engine_output: EngineBOutput,
    economics: _ForecastEconomicsB,
) -> tuple[str, ...]:
    additive = [
        f"engine_b.conviction.{engine_output.conviction.value}",
        f"engine_b.excess.{engine_output.excess_verdict.value}",
        f"engine_b.breakout.{engine_output.breakout_verdict.value}",
        f"engine_b.cost.{engine_output.cost_verdict.value}",
        economics.volatility_proxy_reason_code,
        _break_even_reason_code_b(economics.break_even_decision),
    ]
    if economics.normalization.clipped:
        additive.append("engine_b.forecast.normalized_forecast_clipped")
    return merge_reason_codes(additive, engine_output.reason_codes)


def _break_even_reason_code_b(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_b.economics.break_even_cleared"
    return f"engine_b.economics.{decision.reason_code.lower()}"


def _break_even_conditioning_code_b(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_internal.engine_b.break_even.cleared"
    return f"engine_internal.engine_b.break_even.{decision.reason_code.lower()}"


def _resolve_invalidation_ref_b(engine_output: EngineBOutput) -> str | None:
    if engine_output.invalidation is None:
        return None
    primary = engine_output.invalidation.primary_invalidation.strip()
    if primary:
        return primary
    return None
