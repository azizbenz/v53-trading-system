"""Private helper functions for the Engine B runner facade."""

from __future__ import annotations

from engines.engine_b.anti_breakout_filter_b import BreakoutInput, BreakoutResult, BreakoutVerdict, evaluate_breakout_risk
from engines.engine_b.conviction_builder_b import ConvictionInputB, ConvictionLevelB, ConvictionResultB, TierSuggestionB, build_conviction_b
from engines.engine_b.cost_feasibility_b import CostInputB, CostResultB, CostVerdictB, check_cost_feasibility_b
from engines.engine_b.excess_detector_b import ExcessInput, ExcessResult, ExcessVerdict, detect_excess
from engines.engine_b.invalidation_mapper_b import InvalidationMapB, build_invalidation_b
from engines.engine_b.local_mean_estimator_b import LocalMeanInput, LocalMeanResult, estimate_local_mean

from .engine_b_runner import (
    ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT,
    ENGINE_B_RUNNER_COST_RATIO_EPSILON,
    ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT,
    EngineBDecision,
    EngineBInput,
    EngineBLogEntry,
    EngineBOutput,
)


def _resolve_input_preconditions(inputs: EngineBInput) -> tuple[tuple[str, ...], tuple[str, ...]]:
    reason_codes: list[str] = []
    reasons: list[str] = []
    if inputs.current_price <= 0.0:
        reason_codes.append("engine_b.input.current_price_non_positive")
        reasons.append("current_price must be > 0")
    if inputs.local_mean <= 0.0:
        reason_codes.append("engine_b.input.local_mean_non_positive")
        reasons.append("local_mean must be > 0")
    if inputs.candidate_size <= 0.0:
        reason_codes.append("engine_b.input.candidate_size_non_positive")
        reasons.append("candidate_size must be > 0")
    if inputs.holding_period <= 0.0:
        reason_codes.append("engine_b.input.holding_period_non_positive")
        reasons.append("holding_period must be > 0")
    return tuple(reason_codes), tuple(reasons)


def _merge_reason_codes(*reason_code_groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            code
            for group in reason_code_groups
            for code in group
            if code
        )
    )


def build_engine_b_gate_reason_codes(
    *,
    gate_reason_codes: tuple[str, ...],
    detailed_reason_codes: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return Engine B reason codes with explicit gate provenance first.

    Gate 0 = hard-block/runtime-invalid.
    Gate 1 = excess/fade/anti-breakout setup quality.
    Gate 2 = economics/cost feasibility.
    Gate 3 = downstream scoring/portfolio/risk runtime.
    """

    return _merge_reason_codes(gate_reason_codes, detailed_reason_codes)


def _resolve_invalidation_error_reason_codes(error: ValueError) -> tuple[str, ...]:
    return {
        "INVALID_STOP_GE_ENTRY": ("engine_b.invalidation.invalid_stop_ge_entry",),
        "INVALID_TARGET_LE_ENTRY": ("engine_b.invalidation.invalid_target_le_entry",),
        "INVALID_RISK_MULTIPLE": ("engine_b.invalidation.invalid_risk_multiple",),
    }.get(str(error), ("engine_b.invalidation.invalid_input",))


def _append_engine_b_log(
    logs: list[EngineBLogEntry],
    *,
    event: str,
    pair: str,
    regime: str = "",
    local_mean: float = 0.0,
    local_std: float = 0.0,
    z_score: float = 0.0,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    expected_cost: float = 0.0,
    expected_duration: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    invalidation: str = "",
    holding_hours: float = 0.0,
    reasons: tuple[str, ...] = (),
    scoring_version: str = "",
) -> None:
    logs.append(
        EngineBLogEntry(
            event=event,
            pair=pair,
            regime=regime,
            local_mean=local_mean,
            local_std=local_std,
            z_score=z_score,
            raw_score=raw_score,
            penalized_score=penalized_score,
            block_scores={} if block_scores is None else block_scores,
            expected_cost=expected_cost,
            expected_duration=expected_duration,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction,
            tier=tier,
            invalidation=invalidation,
            holding_hours=holding_hours,
            reasons=reasons,
            scoring_version=scoring_version,
        )
    )


def _build_engine_b_no_trade_output(
    inputs: EngineBInput,
    logs: list[EngineBLogEntry],
    no_trade_reasons: list,
    *,
    raw_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    conviction: ConvictionLevelB = ConvictionLevelB.NONE,
    tier_suggestion: TierSuggestionB = TierSuggestionB.NO_TRADE,
    z_score: float = 0.0,
    excess_score: float = 0.0,
    breakout_score: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    excess_verdict: ExcessVerdict = ExcessVerdict.NO_EXCESS,
    breakout_verdict: BreakoutVerdict = BreakoutVerdict.CLEAR,
    cost_verdict: CostVerdictB = CostVerdictB.INFEASIBLE,
    reason_codes: tuple[str, ...] = (),
) -> EngineBOutput:
    return EngineBOutput(
        pair=inputs.pair,
        decision=EngineBDecision.NO_TRADE,
        raw_score=raw_score,
        block_scores={} if block_scores is None else block_scores,
        conviction=conviction,
        tier_suggestion=tier_suggestion,
        z_score=z_score,
        excess_score=excess_score,
        breakout_score=breakout_score,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        excess_verdict=excess_verdict,
        breakout_verdict=breakout_verdict,
        cost_verdict=cost_verdict,
        reason_codes=reason_codes,
        no_trade_reasons=tuple(no_trade_reasons),
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )


def _estimate_local_mean_stage(inputs: EngineBInput, logs: list[EngineBLogEntry]) -> LocalMeanResult:
    mean_result = estimate_local_mean(
        LocalMeanInput(
            pair=inputs.pair,
            current_price=inputs.current_price,
            local_mean=inputs.local_mean,
            local_std=inputs.local_std,
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_mean_estimated",
        pair=inputs.pair,
        regime=inputs.regime,
        local_mean=mean_result.local_mean,
        local_std=mean_result.local_std,
        z_score=mean_result.z_score,
    )
    return mean_result


def _evaluate_excess_stage(inputs: EngineBInput, mean_result: LocalMeanResult, logs: list[EngineBLogEntry]) -> ExcessResult:
    excess = detect_excess(
        ExcessInput(
            pair=inputs.pair,
            z_score=mean_result.z_score,
            z_score_valid=mean_result.valid,
            structure_is_range=inputs.structure_is_range,
            recent_expansion=inputs.recent_expansion,
            vpin_current=inputs.vpin_current,
            toxic_flow_correlation=inputs.toxic_flow_correlation,
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_excess_evaluated",
        pair=inputs.pair,
        z_score=mean_result.z_score,
        raw_score=excess.excess_score,
        reasons=_merge_reason_codes(
            (f"engine_b.excess.{excess.verdict.value}",),
            excess.active_reason_codes,
            excess.suppressed_reason_codes,
        ),
    )
    return excess


def _evaluate_breakout_stage(inputs: EngineBInput, logs: list[EngineBLogEntry]) -> BreakoutResult:
    breakout = evaluate_breakout_risk(
        BreakoutInput(
            pair=inputs.pair,
            regime_trend_strength=inputs.regime_trend_strength,
            volume_anomaly=inputs.volume_anomaly,
            structural_break=inputs.structural_break,
            continuation_momentum=inputs.continuation_momentum,
            microstructure_breakout_confirmation=inputs.microstructure_breakout_confirmation,
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_breakout_evaluated",
        pair=inputs.pair,
        raw_score=breakout.breakout_score,
        reasons=() if breakout.verdict == BreakoutVerdict.CLEAR else (f"engine_b.breakout.{breakout.verdict.value}",),
    )
    return breakout


def _evaluate_cost_stage(inputs: EngineBInput, logs: list[EngineBLogEntry]) -> CostResultB:
    cost = check_cost_feasibility_b(
        CostInputB(
            pair=inputs.pair,
            expected_gain=inputs.expected_gain,
            expected_cost=inputs.expected_cost,
            candidate_size=inputs.candidate_size,
            holding_period=inputs.holding_period,
            delta_safe=inputs.delta_safe,
            ce_min=inputs.ce_min,
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_cost_checked",
        pair=inputs.pair,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        reasons=tuple(reason.value for reason in cost.reason_codes),
    )
    return cost


def _evaluate_conviction_stage(inputs: EngineBInput, excess: ExcessResult, logs: list[EngineBLogEntry]) -> ConvictionResultB:
    conviction = build_conviction_b(
        ConvictionInputB(
            pair=inputs.pair,
            excess_score=excess.excess_score,
            structure_score=inputs.structure_is_range,
            context_score=(
                inputs.regime_favorability + inputs.pair_health + inputs.data_freshness + inputs.flow_coherence
            ) / ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT,
            cost_preference_score=1.0 - min(
                inputs.expected_cost / max(inputs.expected_gain, ENGINE_B_RUNNER_COST_RATIO_EPSILON),
                1.0,
            ),
            sweep_score=inputs.sweep_score,
            absorption_score=inputs.absorption_score,
            poc_reversion_score=inputs.poc_reversion_score,
            false_breakout_score=inputs.false_breakout_score,
            execution_fragility=inputs.execution_fragility,
            market_toxicity=inputs.market_toxicity,
            spread_regime_penalty=inputs.spread_regime_penalty,
            scoring_version=inputs.scoring_version,
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_conviction_built",
        pair=inputs.pair,
        raw_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
    )
    return conviction


def _resolve_breakout_penalty(
    inputs: EngineBInput,
    conviction: ConvictionResultB,
    breakout: BreakoutResult,
    logs: list[EngineBLogEntry],
) -> float:
    if breakout.verdict != BreakoutVerdict.WARNING:
        return 0.0
    breakout_penalty = ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT * breakout.breakout_score
    _append_engine_b_log(
        logs,
        event="engine_b_breakout_penalty",
        pair=inputs.pair,
        raw_score=conviction.raw_score,
        penalized_score=conviction.raw_score - breakout_penalty,
        reasons=(
            f"WARNING penalty: -{breakout_penalty:.4f} "
            f"(weight={ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT} x score={breakout.breakout_score:.3f})",
        ),
    )
    return breakout_penalty


def _evaluate_invalidation_stage(inputs: EngineBInput, logs: list[EngineBLogEntry]) -> InvalidationMapB:
    invalidation = build_invalidation_b(
        pair=inputs.pair,
        entry_price=inputs.current_price,
        local_mean=inputs.local_mean,
        local_std=inputs.local_std,
        holding_hours=inputs.holding_period,
    )
    _append_engine_b_log(
        logs,
        event="engine_b_invalidation_built",
        pair=inputs.pair,
        invalidation=invalidation.primary_invalidation,
        holding_hours=invalidation.max_holding_hours,
    )
    return invalidation


def _build_engine_b_emit_output(
    inputs: EngineBInput,
    mean_result: LocalMeanResult,
    excess: ExcessResult,
    breakout: BreakoutResult,
    cost: CostResultB,
    conviction: ConvictionResultB,
    invalidation: InvalidationMapB,
    logs: list[EngineBLogEntry],
    *,
    penalized_score: float,
) -> EngineBOutput:
    reason_codes = tuple(
        dict.fromkeys(
            (
                f"scoring.engine_b.conviction.{conviction.conviction.value}",
                f"engine_internal.engine_b.excess.{excess.verdict.value}",
                f"economics.engine_b.cost.{cost.verdict.value}",
                f"engine_b.conviction.{conviction.conviction.value}",
                f"engine_b.excess.{excess.verdict.value}",
                *(("engine_b.breakout.warning",) if breakout.verdict == BreakoutVerdict.WARNING else ()),
                *(("engine_internal.engine_b.breakout.warning",) if breakout.verdict == BreakoutVerdict.WARNING else ()),
                *excess.active_reason_codes,
                *excess.suppressed_reason_codes,
            )
        )
    )
    _append_engine_b_log(
        logs,
        event="engine_b_signal_emitted",
        pair=inputs.pair,
        regime=inputs.regime,
        local_mean=mean_result.local_mean,
        local_std=mean_result.local_std,
        z_score=mean_result.z_score,
        raw_score=conviction.raw_score,
        penalized_score=penalized_score,
        block_scores=conviction.block_scores,
        expected_cost=cost.expected_cost,
        expected_duration=inputs.holding_period,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
        invalidation=invalidation.primary_invalidation,
        holding_hours=invalidation.max_holding_hours,
        scoring_version=inputs.scoring_version,
    )
    return EngineBOutput(
        pair=inputs.pair,
        decision=EngineBDecision.EMIT,
        raw_score=conviction.raw_score,
        penalized_score=penalized_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction,
        tier_suggestion=conviction.tier_suggestion,
        z_score=mean_result.z_score,
        excess_score=excess.excess_score,
        breakout_score=breakout.breakout_score,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        expected_holding_hours=invalidation.max_holding_hours,
        invalidation=invalidation,
        excess_verdict=excess.verdict,
        breakout_verdict=breakout.verdict,
        cost_verdict=cost.verdict,
        scoring_version=inputs.scoring_version,
        reason_codes=reason_codes,
        log_entries=tuple(logs),
    )
