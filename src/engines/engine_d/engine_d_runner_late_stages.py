"""Late-stage helpers for the canonical Engine D runner."""

from __future__ import annotations

from .conviction_builder_d import ConvictionResultD, build_conviction_d
from .cost_feasibility_d import CostMetricsD, evaluate_cost_feasibility_d
from .engine_d_models import (
    ConvictionLevelD,
    EngineDDecision,
    EngineDInput,
    EngineDLogEntry,
    EngineDOutput,
    NoTradeReasonD,
    TierSuggestionD,
)
from .engine_d_runner_support import (
    append_engine_d_log as _append_engine_d_log,
    build_engine_d_gate_reason_codes,
    build_engine_d_invalidation as _build_engine_d_invalidation,
    build_engine_d_no_trade_output as _build_engine_d_no_trade_output,
)
from .invalidation_mapper_d import build_invalidation_levels_d
from .output_payload_builder_d import build_engine_d_output_payload

EngineDContext = dict[str, float | str | bool]


def _evaluate_cost_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
    *,
    history_score: float,
    reformation_score: float,
    marginal_value_score: float,
    concentration_risk: float,
) -> tuple[CostMetricsD, EngineDOutput | None]:
    try:
        cost_metrics = evaluate_cost_feasibility_d(
            expected_gain=inputs.expected_gain,
            expected_cost=inputs.expected_cost,
            candidate_size=inputs.candidate_size,
            holding_period=inputs.holding_period,
            delta_safe=inputs.delta_safe,
            ce_min=inputs.ce_min,
        )
    except ValueError as exc:
        no_trade_reasons.append(NoTradeReasonD.COST_INFEASIBLE)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=(str(exc),),
        )
        fallback_metrics = CostMetricsD(
            expected_cost=max(0.0, inputs.expected_cost),
            ce_expected=0.0,
            ev_net=0.0,
            is_feasible=False,
            cost_preference_score=0.0,
            reason_codes=(),
        )
        return fallback_metrics, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.cost.invalid_input",),
                detailed_reason_codes=("engine_d.cost.invalid_input",),
            ),
        )
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_cost_checked",
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
    )
    if not cost_metrics.is_feasible:
        no_trade_reasons.append(NoTradeReasonD.COST_INFEASIBLE)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            reasons=tuple(str(reason) for reason in cost_metrics.reason_codes)
            or ("re-entry edge does not survive costs",),
        )
        return cost_metrics, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("economics.engine_d.cost.infeasible",),
                detailed_reason_codes=(
                    "engine_d.no_trade.cost_infeasible",
                    *(
                        tuple(
                            str(reason)
                            for reason in cost_metrics.reason_codes
                            if str(reason).strip()
                        )
                        or ("engine_d.cost.infeasible",)
                    ),
                ),
            ),
        )
    return cost_metrics, None


def _evaluate_conviction_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
    *,
    history_score: float,
    reformation_score: float,
    marginal_value_score: float,
    concentration_risk: float,
    cost_metrics: CostMetricsD,
) -> tuple[ConvictionResultD, EngineDOutput | None]:
    conviction_result = build_conviction_d(
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        ce_expected=cost_metrics.ce_expected,
        ce_min=inputs.ce_min,
        concentration_risk=concentration_risk,
    )
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_conviction_checked",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction_result.conviction_name,
        tier=conviction_result.tier_name,
        holding_hours=inputs.holding_period,
    )
    if conviction_result.is_emittable:
        return conviction_result, None
    no_trade_reasons.append(NoTradeReasonD.CONVICTION_TOO_LOW)
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_no_trade",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction_result.conviction_name,
        tier=conviction_result.tier_name,
        reasons=("conviction below minimum emission tier for Engine D",),
    )
    return conviction_result, _build_engine_d_no_trade_output(
        inputs,
        context,
        logs,
        no_trade_reasons,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        reason_codes=build_engine_d_gate_reason_codes(
            gate_reason_codes=("scoring.engine_d.conviction.too_low",),
            detailed_reason_codes=("engine_d.no_trade.conviction_too_low",),
        ),
    )


def _build_engine_d_emit_output(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    *,
    history_score: float,
    context_score: float,
    reformation_score: float,
    marginal_value_score: float,
    concentration_risk: float,
    cost_metrics: CostMetricsD,
    conviction_result: ConvictionResultD,
) -> EngineDOutput:
    conviction = ConvictionLevelD(conviction_result.conviction_name)
    tier = TierSuggestionD(conviction_result.tier_name)
    invalidation = _build_engine_d_invalidation(
        build_invalidation_levels_d(
            entry_price=inputs.entry_price,
            reentry_anchor_price=inputs.reentry_anchor_price,
            realized_vol_current=inputs.realized_vol_current,
            realized_vol_post_close=inputs.realized_vol_post_close,
            expected_gain=inputs.expected_gain,
        )
    )
    block_scores = {
        "history": history_score,
        "reformation": reformation_score,
        "marginal_value": marginal_value_score,
        "cost_preference": cost_metrics.cost_preference_score,
    }
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_emit",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction.value,
        tier=tier.value,
        holding_hours=inputs.holding_period,
    )
    return EngineDOutput(
        pair=inputs.pair,
        decision=EngineDDecision.EMIT,
        **build_engine_d_output_payload(
            context=context,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            block_scores=block_scores,
            conviction=conviction,
            tier_suggestion=tier,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            invalidation=invalidation,
            holding_hours=inputs.holding_period,
            reason_codes=(
                f"scoring.engine_d.conviction.{conviction.value}",
                f"engine_internal.engine_d.link_type.{inputs.link_type or 'unknown'}",
                f"engine_internal.engine_d.anti_revenge.{str(context['anti_revenge_state']) or 'unknown'}",
                "engine_internal.engine_d.reformation.detected"
                if inputs.structure_reformed_detected
                else "engine_internal.engine_d.reformation.not_detected",
                "economics.engine_d.cost.feasible",
                f"engine_d.conviction.{conviction.value}",
                f"engine_d.link_type.{inputs.link_type or 'unknown'}",
                f"engine_d.anti_revenge.{str(context['anti_revenge_state']) or 'unknown'}",
                "engine_d.reformation.detected"
                if inputs.structure_reformed_detected
                else "engine_d.reformation.not_detected",
            ),
        ),
    )
