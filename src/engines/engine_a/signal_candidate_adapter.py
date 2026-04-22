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
from engines.engine_a.engine_a_runner import EngineADecision, EngineAInput, EngineAOutput
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

_NORMALIZER_CONFIG = ForecastNormalizerConfig()
_BREAK_EVEN_CONFIG = BreakEvenFilterConfig()


@dataclass(frozen=True)
class _ForecastEconomicsA:
    normalization: ForecastNormalizationResult
    break_even_decision: BreakEvenFilterDecision
    volatility_proxy_reason_code: str
    volatility_proxy_conditioning_code: str


def build_signal_candidate_a(
    engine_output: EngineAOutput,
    signal_candidate: DecisionSignalCandidate,
    *,
    strategy_id: str,
    engine_inputs: EngineAInput,
    timestamp_ms: int,
) -> ForecastSignalCandidate | None:
    if strategy_id is None or not strategy_id.strip():
        return None
    if engine_output.decision != EngineADecision.EMIT:
        return None

    economics = _resolve_forecast_economics_a(engine_inputs, engine_output)
    return ForecastSignalCandidate.from_decision_signal(
        signal_candidate,
        strategy_id=strategy_id.strip(),
        forecast_direction=1.0 if signal_candidate.side == Side.BUY else -1.0,
        forecast_strength=abs(economics.normalization.normalized_forecast),
        forecast_horizon_class=_resolve_horizon_class_a(signal_candidate, engine_inputs),
        forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        bet_structure=_resolve_bet_structure_a(signal_candidate.side),
        conditioning_state=_build_conditioning_state_a(
            timestamp_ms=timestamp_ms,
            engine_output=engine_output,
            economics=economics,
        ),
        expected_cost=engine_output.expected_cost,
        expected_break_even=economics.break_even_decision.expected_break_even,
        expected_ce=engine_output.ce_expected,
        expected_gain=engine_inputs.expected_gain,
        invalidation_ref=_resolve_invalidation_ref_a(engine_output),
        reason_codes=_build_reason_codes_a(engine_output, economics),
        versions=build_forecast_versions(
            scoring_version=engine_output.scoring_version or engine_inputs.scoring_version,
            calibration_profile_id=engine_output.calibration_profile_id,
            calibration_status=engine_output.calibration_status,
            physics_calibration_profile_id=engine_output.physics_calibration_profile_id,
            physics_calibration_status=engine_output.physics_calibration_status,
        ),
        confidence_band=signal_candidate.confidence,
    )


def _resolve_forecast_economics_a(
    engine_inputs: EngineAInput,
    engine_output: EngineAOutput,
) -> _ForecastEconomicsA:
    vol_scale, reason_code, conditioning_code = _resolve_volatility_proxy_a(engine_inputs)
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
    return _ForecastEconomicsA(
        normalization=normalization,
        break_even_decision=break_even,
        volatility_proxy_reason_code=reason_code,
        volatility_proxy_conditioning_code=conditioning_code,
    )


def _resolve_volatility_proxy_a(
    engine_inputs: EngineAInput,
) -> tuple[float, str, str]:
    if (
        engine_inputs.realized_vol_current is not None
        and engine_inputs.realized_vol_current > 0.0
    ):
        return (
            engine_inputs.realized_vol_current,
            "engine_a.forecast.volatility_proxy.realized_vol_current",
            "engine_internal.engine_a.forecast.volatility_proxy.realized_vol_current",
        )
    if (
        engine_inputs.realized_kernel_vol_scale is not None
        and engine_inputs.realized_kernel_vol_scale > 0.0
    ):
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


def _resolve_horizon_class_a(
    signal_candidate: DecisionSignalCandidate,
    engine_inputs: EngineAInput,
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


def _resolve_bet_structure_a(side: Side) -> BetStructure:
    if side == Side.BUY:
        return BetStructure.DIRECTIONAL_LONG
    return BetStructure.DIRECTIONAL_SHORT


def _build_conditioning_state_a(
    *,
    timestamp_ms: int,
    engine_output: EngineAOutput,
    economics: _ForecastEconomicsA,
) -> tuple[ConditioningRecord, ...]:
    records = [
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.conviction.{engine_output.conviction.value}",
            value=engine_output.raw_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.tier.{engine_output.tier_suggestion.value}",
            value=engine_output.raw_score,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.structure.{engine_output.structure_verdict.value}",
            value=engine_output.block_scores.get("structure", 0.0),
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.context.{engine_output.context_verdict.value}",
            value=engine_output.block_scores.get("context", 0.0),
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=f"engine_internal.engine_a.cost.{engine_output.cost_verdict.value}",
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
            code="engine_internal.engine_a.forecast.normalized_strength",
            value=economics.normalization.normalized_forecast,
        ),
        ConditioningRecord(
            timestamp_ms=timestamp_ms,
            family=ConditioningFamily.ENGINE_INTERNAL,
            code=_break_even_conditioning_code_a(economics.break_even_decision),
            value=economics.break_even_decision.expected_break_even,
            triggered_no_trade=not economics.break_even_decision.allowed,
        ),
    ]
    if _resolve_invalidation_ref_a(engine_output) is not None:
        records.append(
            ConditioningRecord(
                timestamp_ms=timestamp_ms,
                family=ConditioningFamily.ENGINE_INTERNAL,
                code="engine_internal.engine_a.invalidation.present",
                value=1.0,
            )
        )
    return tuple(records)


def _build_reason_codes_a(
    engine_output: EngineAOutput,
    economics: _ForecastEconomicsA,
) -> tuple[str, ...]:
    additive = [
        f"engine_a.structure.{engine_output.structure_verdict.value}",
        f"engine_a.context.{engine_output.context_verdict.value}",
        f"engine_a.cost.{engine_output.cost_verdict.value}",
        f"engine_a.conviction.{engine_output.conviction.value}",
        economics.volatility_proxy_reason_code,
        _break_even_reason_code_a(economics.break_even_decision),
    ]
    if economics.normalization.clipped:
        additive.append("engine_a.forecast.normalized_forecast_clipped")
    return merge_reason_codes(engine_output.reason_codes, additive)


def _break_even_reason_code_a(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_a.economics.break_even_cleared"
    return f"engine_a.economics.{decision.reason_code.lower()}"


def _break_even_conditioning_code_a(decision: BreakEvenFilterDecision) -> str:
    if decision.allowed:
        return "engine_internal.engine_a.break_even.cleared"
    return f"engine_internal.engine_a.break_even.{decision.reason_code.lower()}"


def _resolve_invalidation_ref_a(engine_output: EngineAOutput) -> str | None:
    if engine_output.invalidation is None:
        return None
    primary = engine_output.invalidation.primary_invalidation.strip()
    if primary:
        return primary
    return None
