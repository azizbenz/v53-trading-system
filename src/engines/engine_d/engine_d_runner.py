"""Canonical Engine D runner."""

from __future__ import annotations

from .context_resolver_d import resolve_engine_d_context
from .engine_d_models import (
    EngineDDecision,
    EngineDInput,
    EngineDInvalidation,
    EngineDLogEntry,
    EngineDOutput,
    NoTradeReasonD,
)
from .engine_d_runner_late_stages import (
    _build_engine_d_emit_output,
    _evaluate_conviction_stage,
    _evaluate_cost_stage,
)
from .engine_d_runner_support import (
    append_engine_d_log as _append_engine_d_log,
    build_engine_d_gate_reason_codes,
    build_engine_d_no_trade_output as _build_engine_d_no_trade_output,
)
from .marginal_value_estimator_d import (
    ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A,
    marginal_value_floor_cleared,
)
from .signal_math_d import (
    compute_context_score,
    compute_history_score,
    compute_marginal_value_score,
    compute_reformation_score,
)

EngineDContext = dict[str, float | str | bool]

_HISTORY_MIN = 0.55
_REFORMATION_MIN = 0.58
_CONCENTRATION_MAX = 0.64


def run_engine_d(inputs: EngineDInput) -> EngineDOutput:
    logs: list[EngineDLogEntry] = []
    no_trade_reasons: list[NoTradeReasonD] = []
    context = resolve_engine_d_context(inputs)

    no_trade_output = _evaluate_guard_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
    )
    if no_trade_output is not None:
        return no_trade_output

    no_trade_output = _evaluate_anti_revenge_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
    )
    if no_trade_output is not None:
        return no_trade_output

    history_score, no_trade_output = _evaluate_history_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
    )
    if no_trade_output is not None:
        return no_trade_output

    context_score, reformation_score, no_trade_output = _evaluate_reformation_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
        history_score=history_score,
    )
    if no_trade_output is not None:
        return no_trade_output

    marginal_value_score, concentration_risk, no_trade_output = _evaluate_marginal_value_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
        history_score=history_score,
        reformation_score=reformation_score,
    )
    if no_trade_output is not None:
        return no_trade_output

    cost_metrics, no_trade_output = _evaluate_cost_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
    )
    if no_trade_output is not None:
        return no_trade_output

    conviction_result, no_trade_output = _evaluate_conviction_stage(
        inputs,
        context,
        logs,
        no_trade_reasons,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        cost_metrics=cost_metrics,
    )
    if no_trade_output is not None:
        return no_trade_output

    return _build_engine_d_emit_output(
        inputs,
        context,
        logs,
        history_score=history_score,
        context_score=context_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        cost_metrics=cost_metrics,
        conviction_result=conviction_result,
    )

def _evaluate_guard_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
) -> EngineDOutput | None:
    if inputs.entry_price <= 0.0:
        no_trade_reasons.append(NoTradeReasonD.INVALID_ENTRY_PRICE)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=("entry_price must be positive for re-entry invalidation",),
        )
        return _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.input.invalid_entry_price",),
                detailed_reason_codes=("engine_d.no_trade.invalid_entry_price",),
            ),
        )
    if inputs.candidate_size <= 0.0:
        no_trade_reasons.append(NoTradeReasonD.INVALID_CANDIDATE_SIZE)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=("candidate_size must be strictly positive for Engine D emission",),
        )
        return _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.input.invalid_candidate_size",),
                detailed_reason_codes=("engine_d.no_trade.invalid_candidate_size",),
            ),
        )
    if inputs.holding_period <= 0.0:
        no_trade_reasons.append(NoTradeReasonD.INVALID_HOLDING_PERIOD)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=("holding_period must be strictly positive for marginal CE",),
        )
        return _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.input.invalid_holding_period",),
                detailed_reason_codes=("engine_d.no_trade.invalid_holding_period",),
            ),
        )
    if inputs.reentry_anchor_price <= 0.0:
        no_trade_reasons.append(NoTradeReasonD.INVALID_REENTRY_ANCHOR)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=("reentry_anchor_price must be positive for stop placement",),
        )
        return _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.input.invalid_reentry_anchor",),
                detailed_reason_codes=("engine_d.no_trade.invalid_reentry_anchor",),
            ),
        )
    if inputs.atr < 0.0:
        no_trade_reasons.append(NoTradeReasonD.INVALID_ATR)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            reasons=("atr must be non-negative for Engine D invalidation",),
        )
        return _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("hard_block.engine_d.input.invalid_atr",),
                detailed_reason_codes=("engine_d.no_trade.invalid_atr",),
            ),
        )
    return None


def _evaluate_anti_revenge_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
) -> EngineDOutput | None:
    if not bool(context["anti_revenge_blocked"]):
        return None
    no_trade_reasons.append(NoTradeReasonD.ANTI_REVENGE_BLOCKED)
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_no_trade",
        reasons=(
            "anti_revenge_state requires fresh structural support before re-entry",
        ),
    )
    return _build_engine_d_no_trade_output(
        inputs,
        context,
        logs,
        no_trade_reasons,
        reason_codes=build_engine_d_gate_reason_codes(
            gate_reason_codes=("hard_block.engine_d.anti_revenge.blocked",),
            detailed_reason_codes=("engine_d.no_trade.anti_revenge_blocked",),
        ),
    )


def _evaluate_history_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
) -> tuple[float, EngineDOutput | None]:
    history_score = compute_history_score(inputs)
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_history_checked",
        raw_score=history_score,
        history_score=history_score,
    )
    if history_score < _HISTORY_MIN:
        no_trade_reasons.append(NoTradeReasonD.HISTORY_WEAK)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            history_score=history_score,
            reasons=("prior context too weak for re-entry",),
        )
        return history_score, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("engine_internal.engine_d.history.weak",),
                detailed_reason_codes=("engine_d.no_trade.history_weak",),
            ),
        )
    return history_score, None


def _evaluate_reformation_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
    *,
    history_score: float,
) -> tuple[float, float, EngineDOutput | None]:
    context_score = compute_context_score(inputs)
    reformation_score = compute_reformation_score(inputs, context_score=context_score)
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_reformation_checked",
        raw_score=reformation_score,
        history_score=history_score,
        reformation_score=reformation_score,
    )
    if not inputs.structure_reformed_detected:
        no_trade_reasons.append(NoTradeReasonD.REFORMATION_WEAK)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            history_score=history_score,
            reformation_score=reformation_score,
            reasons=("fresh structural support is required for Engine D re-entry",),
        )
        return context_score, reformation_score, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("engine_internal.engine_d.reformation.not_detected",),
                detailed_reason_codes=("engine_d.no_trade.reformation_weak",),
            ),
        )
    if reformation_score < _REFORMATION_MIN:
        no_trade_reasons.append(NoTradeReasonD.REFORMATION_WEAK)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            history_score=history_score,
            reformation_score=reformation_score,
            reasons=("reformation too weak for second chance entry",),
        )
        return context_score, reformation_score, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("engine_internal.engine_d.reformation.weak",),
                detailed_reason_codes=("engine_d.no_trade.reformation_weak",),
            ),
        )
    return context_score, reformation_score, None


def _evaluate_marginal_value_stage(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
    *,
    history_score: float,
    reformation_score: float,
) -> tuple[float, float, EngineDOutput | None]:
    marginal_value_score = compute_marginal_value_score(inputs)
    concentration_risk = float(context["concentration_risk"])
    penalized_score = max(0.0, marginal_value_score - max(0.0, concentration_risk - 0.30))
    _append_engine_d_log(
        logs,
        inputs,
        context,
        event="engine_d_marginal_value_checked",
        raw_score=marginal_value_score,
        penalized_score=penalized_score,
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
    )
    if not marginal_value_floor_cleared(marginal_value_score):
        no_trade_reasons.append(NoTradeReasonD.MARGINAL_EDGE_TOO_LOW)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reasons=(
                "re-entry adds insufficient marginal value "
                f"(score floor={ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A.marginal_value_score_min:.2f})",
            ),
        )
        return marginal_value_score, concentration_risk, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("engine_internal.engine_d.marginal_value.below_floor",),
                detailed_reason_codes=("engine_d.no_trade.marginal_edge_too_low",),
            ),
        )
    if float(context["marginal_portfolio_gain"]) <= 0.0:
        no_trade_reasons.append(
            NoTradeReasonD.DUPLICATION_BLOCKED if bool(context["duplication_blocked"]) else NoTradeReasonD.MARGINAL_GAIN_TOO_LOW
        )
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reasons=(
                "portfolio comparison says Engine D adds no incremental value"
                if not bool(context["duplication_blocked"])
                else "Engine A already covers this re-entry and marginal portfolio gain is non-positive",
            ),
        )
        return marginal_value_score, concentration_risk, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=(
                    "engine_internal.engine_d.duplication.blocked"
                    if bool(context["duplication_blocked"])
                    else "engine_internal.engine_d.marginal_gain.non_positive",
                ),
                detailed_reason_codes=(
                    "engine_d.no_trade.duplication_blocked",
                )
                if bool(context["duplication_blocked"])
                else ("engine_d.no_trade.marginal_gain_too_low",),
            ),
        )
    if concentration_risk >= _CONCENTRATION_MAX:
        no_trade_reasons.append(NoTradeReasonD.CONCENTRATION_BLOCKED)
        _append_engine_d_log(
            logs,
            inputs,
            context,
            event="engine_d_no_trade",
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reasons=("concentration or lateness risk too high",),
        )
        return marginal_value_score, concentration_risk, _build_engine_d_no_trade_output(
            inputs,
            context,
            logs,
            no_trade_reasons,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            reason_codes=build_engine_d_gate_reason_codes(
                gate_reason_codes=("engine_internal.engine_d.concentration.blocked",),
                detailed_reason_codes=("engine_d.no_trade.concentration_blocked",),
            ),
        )
    return marginal_value_score, concentration_risk, None
