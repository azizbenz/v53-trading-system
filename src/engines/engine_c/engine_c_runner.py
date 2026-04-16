"""Canonical Engine C runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .continuation_validator_c import (
    EngineCContinuationValidationInput,
    validate_continuation_c,
)
from .conviction_builder_c import ConvictionResultC, build_conviction_c
from .cost_feasibility_c import CostMetricsC, evaluate_cost_feasibility_c
from .invalidation_mapper_c import InvalidationLevelsC, build_invalidation_levels_c
from .output_payload_builder_c import build_engine_c_output_payload
from .signal_math_c import (
    compute_breakout_score,
    compute_context_score,
    compute_fake_breakout_risk,
)
from .structure_resolver_c import build_engine_c_log_context, resolve_engine_c_structure

EngineCStructure = dict[str, float | str | bool]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class EngineCDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonC(StrEnum):
    NON_LONG_BREAKOUT = "non_long_breakout"
    BREAKOUT_UNSTRUCTURED = "breakout_unstructured"
    CONTINUATION_NOT_VIABLE = "continuation_not_viable"
    MICROSTRUCTURE_UNCONFIRMED = "microstructure_unconfirmed"
    FAKE_BREAKOUT_BLOCKED = "fake_breakout_blocked"
    COST_INFEASIBLE = "cost_infeasible"


class ConvictionLevelC(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TierSuggestionC(StrEnum):
    NO_TRADE = "no_trade"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"


class EngineCInvalidation(BaseModel, frozen=True):
    stop_price: float = Field(..., gt=0.0)
    target_price: float = Field(..., gt=0.0)
    risk_multiple: float = Field(..., gt=0.0)


class EngineCLogEntry(BaseModel, frozen=True):
    event: str
    pair: str
    regime: str = ""
    range_low: float = 0.0
    range_high: float = 0.0
    range_width_pct: float = 0.0
    breakout_type: str = ""
    continuation_context: str = ""
    distance_to_breakout_pct: float = 0.0
    raw_score: float = 0.0
    penalized_score: float = 0.0
    breakout_score: float = 0.0
    continuation_score: float = 0.0
    cumulative_ofi: float | None = None
    queue_pressure: float | None = None
    vpin: float | None = None
    kyle_lambda: float | None = None
    microstructure_gate_applied: bool = False
    fake_breakout_risk: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    duplication_possible_with_engine_a: bool = False
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    keff_contribution: float = 0.0
    conviction: str = ""
    tier: str = ""
    holding_hours: float = 0.0
    reasons: tuple[str, ...] = ()
    scoring_version: str = ""


class EngineCOutput(BaseModel, frozen=True):
    pair: str
    engine_id: str = "engine_c"
    decision: EngineCDecision
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelC = ConvictionLevelC.NONE
    tier_suggestion: TierSuggestionC = TierSuggestionC.NO_TRADE
    range_low: float = 0.0
    range_high: float = 0.0
    range_width_pct: float = 0.0
    breakout_type: str = ""
    continuation_context: str = ""
    distance_to_breakout_pct: float = 0.0
    breakout_score: float = 0.0
    continuation_score: float = 0.0
    cumulative_ofi: float | None = None
    queue_pressure: float | None = None
    vpin: float | None = None
    kyle_lambda: float | None = None
    microstructure_gate_applied: bool = False
    fake_breakout_risk: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    duplication_possible_with_engine_a: bool = False
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    keff_contribution: float = 0.0
    invalidation: EngineCInvalidation | None = None
    holding_hours: float = 0.0
    scoring_version: str = ""
    no_trade_reasons: tuple[NoTradeReasonC, ...] = ()
    log_entries: tuple[EngineCLogEntry, ...] = ()


class EngineCInput(BaseModel, frozen=True):
    pair: str
    breakout_strength: float
    range_quality: float
    compression_quality: float
    volume_confirmation: float
    followthrough_room: float
    extension_pct: float
    retrace_risk: float = 0.0
    rejection_wick_ratio: float = 0.0
    regime: str = ""
    regime_favorability: float = 0.5
    pair_health: float = 0.5
    data_freshness: float = 0.5
    flow_coherence: float = 0.5
    cumulative_ofi: float | None = None
    queue_pressure: float | None = Field(default=None, ge=-1.0, le=1.0)
    vpin: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda: float | None = None
    continuation_ofi_min: float = 0.0
    continuation_queue_min: float = 0.0
    continuation_vpin_max: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 3.0
    ce_min: float = 0.00015
    delta_safe: float = 0.0005
    entry_price: float = 0.0
    breakout_level: float = 0.0
    range_low: float = 0.0
    range_high: float = 0.0
    atr: float = 0.0
    engine_a_overlap_ratio: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    keff_contribution: float = 0.0
    scoring_version: str = ""


def run_engine_c(inputs: EngineCInput) -> EngineCOutput:
    logs: list[EngineCLogEntry] = []
    no_trade_reasons: list[NoTradeReasonC] = []
    structure = resolve_engine_c_structure(inputs)
    breakout_score, no_trade_output = _evaluate_breakout_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
    )
    if no_trade_output is not None:
        return no_trade_output

    (
        context_score,
        continuation_score,
        microstructure_gate_applied,
        no_trade_output,
    ) = _evaluate_continuation_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
    )
    if no_trade_output is not None:
        return no_trade_output

    fake_breakout_risk, no_trade_output = _evaluate_fake_breakout_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        microstructure_gate_applied=microstructure_gate_applied,
    )
    if no_trade_output is not None:
        return no_trade_output

    cost_metrics, no_trade_output = _evaluate_cost_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        microstructure_gate_applied=microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
    )
    if no_trade_output is not None:
        return no_trade_output

    return _build_engine_c_emit_output(
        inputs,
        structure,
        logs,
        breakout_score=breakout_score,
        context_score=context_score,
        continuation_score=continuation_score,
        microstructure_gate_applied=microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        cost_metrics=cost_metrics,
    )


def _append_engine_c_log(
    logs: list[EngineCLogEntry],
    inputs: EngineCInput,
    structure: EngineCStructure,
    *,
    event: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    breakout_score: float = 0.0,
    continuation_score: float = 0.0,
    microstructure_gate_applied: bool = False,
    cumulative_ofi: float | None = None,
    queue_pressure: float | None = None,
    vpin: float | None = None,
    kyle_lambda: float | None = None,
    fake_breakout_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    holding_hours: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        EngineCLogEntry(
            event=event,
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            raw_score=raw_score,
            penalized_score=penalized_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            cumulative_ofi=inputs.cumulative_ofi if cumulative_ofi is None else cumulative_ofi,
            queue_pressure=inputs.queue_pressure if queue_pressure is None else queue_pressure,
            vpin=inputs.vpin if vpin is None else vpin,
            kyle_lambda=inputs.kyle_lambda if kyle_lambda is None else kyle_lambda,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction,
            tier=tier,
            holding_hours=holding_hours,
            reasons=reasons,
            scoring_version=inputs.scoring_version,
        )
    )


def _build_engine_c_no_trade_output(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float = 0.0,
    continuation_score: float = 0.0,
    microstructure_gate_applied: bool = False,
    fake_breakout_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
) -> EngineCOutput:
    return EngineCOutput(
        pair=inputs.pair,
        decision=EngineCDecision.NO_TRADE,
        **build_engine_c_output_payload(
            structure=structure,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            cumulative_ofi=inputs.cumulative_ofi,
            queue_pressure=inputs.queue_pressure,
            vpin=inputs.vpin,
            kyle_lambda=inputs.kyle_lambda,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            no_trade_reasons=tuple(no_trade_reasons),
        ),
    )


def _evaluate_breakout_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
) -> tuple[float, EngineCOutput | None]:
    if inputs.breakout_strength <= 0:
        no_trade_reasons.append(NoTradeReasonC.NON_LONG_BREAKOUT)
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            reasons=(f"breakout_strength={inputs.breakout_strength:.3f} <= 0",),
        )
        return 0.0, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
        )

    breakout_score = compute_breakout_score(inputs)
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_breakout_evaluated",
        breakout_score=breakout_score,
        raw_score=breakout_score,
    )
    if breakout_score < 0.62 or inputs.breakout_strength < 0.55 or inputs.range_quality < 0.50:
        no_trade_reasons.append(NoTradeReasonC.BREAKOUT_UNSTRUCTURED)
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            breakout_score=breakout_score,
            reasons=("breakout structure insufficient",),
        )
        return breakout_score, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
        )
    return breakout_score, None


def _evaluate_continuation_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
) -> tuple[float, float, bool, EngineCOutput | None]:
    context_score = compute_context_score(inputs)
    continuation_validation = validate_continuation_c(
        EngineCContinuationValidationInput(
            followthrough_room=inputs.followthrough_room,
            extension_pct=inputs.extension_pct,
            context_score=context_score,
            cumulative_ofi=inputs.cumulative_ofi,
            queue_pressure=inputs.queue_pressure,
            vpin=inputs.vpin,
            kyle_lambda=inputs.kyle_lambda,
            ofi_min=inputs.continuation_ofi_min,
            queue_min=inputs.continuation_queue_min,
            vpin_max=inputs.continuation_vpin_max,
        )
    )
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_continuation_checked",
        raw_score=continuation_validation.continuation_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        cumulative_ofi=continuation_validation.cumulative_ofi,
        queue_pressure=continuation_validation.queue_pressure,
        vpin=continuation_validation.vpin,
        kyle_lambda=continuation_validation.kyle_lambda,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        reasons=continuation_validation.reason_codes,
    )
    if not continuation_validation.accepted:
        no_trade_reasons.append(
            NoTradeReasonC.CONTINUATION_NOT_VIABLE
            if not continuation_validation.continuation_viable
            else NoTradeReasonC.MICROSTRUCTURE_UNCONFIRMED
        )
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            breakout_score=breakout_score,
            continuation_score=continuation_validation.continuation_score,
            cumulative_ofi=continuation_validation.cumulative_ofi,
            queue_pressure=continuation_validation.queue_pressure,
            vpin=continuation_validation.vpin,
            kyle_lambda=continuation_validation.kyle_lambda,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            reasons=continuation_validation.reason_codes,
        )
        return (
            context_score,
            continuation_validation.continuation_score,
            continuation_validation.microstructure_gate_applied,
            _build_engine_c_no_trade_output(
                inputs,
                structure,
                logs,
                no_trade_reasons,
                breakout_score=breakout_score,
                continuation_score=continuation_validation.continuation_score,
                microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            ),
        )
    return (
        context_score,
        continuation_validation.continuation_score,
        continuation_validation.microstructure_gate_applied,
        None,
    )


def _evaluate_fake_breakout_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    continuation_score: float,
    microstructure_gate_applied: bool,
) -> tuple[float, EngineCOutput | None]:
    fake_breakout_risk = compute_fake_breakout_risk(inputs)
    penalized_score = max(0.0, breakout_score - max(0.0, fake_breakout_risk - 0.35))
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_fake_breakout_checked",
        raw_score=breakout_score,
        penalized_score=penalized_score,
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        fake_breakout_risk=fake_breakout_risk,
    )
    if fake_breakout_risk >= 0.65:
        no_trade_reasons.append(NoTradeReasonC.FAKE_BREAKOUT_BLOCKED)
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            reasons=("fake breakout risk too high",),
        )
        return fake_breakout_risk, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
        )
    return fake_breakout_risk, None


def _evaluate_cost_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    continuation_score: float,
    microstructure_gate_applied: bool,
    fake_breakout_risk: float,
) -> tuple[CostMetricsC, EngineCOutput | None]:
    cost_metrics = evaluate_cost_feasibility_c(
        expected_gain=inputs.expected_gain,
        expected_cost=inputs.expected_cost,
        candidate_size=inputs.candidate_size,
        holding_period=inputs.holding_period,
        delta_safe=inputs.delta_safe,
        ce_min=inputs.ce_min,
    )
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_cost_checked",
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
    )
    if not cost_metrics.is_feasible:
        no_trade_reasons.append(NoTradeReasonC.COST_INFEASIBLE)
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            reasons=("breakout edge does not survive costs",),
        )
        return cost_metrics, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
        )
    return cost_metrics, None


def _build_engine_c_emit_output(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    *,
    breakout_score: float,
    context_score: float,
    continuation_score: float,
    microstructure_gate_applied: bool,
    fake_breakout_risk: float,
    cost_metrics: CostMetricsC,
) -> EngineCOutput:
    conviction_result = build_conviction_c(
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        context_score=context_score,
        ce_expected=cost_metrics.ce_expected,
        ce_min=inputs.ce_min,
        fake_breakout_risk=fake_breakout_risk,
    )
    conviction = ConvictionLevelC(conviction_result.conviction_name)
    tier = TierSuggestionC(conviction_result.tier_name)
    invalidation = _build_engine_c_invalidation(
        inputs,
        build_invalidation_levels_c(
            entry_price=inputs.entry_price,
            breakout_level=inputs.breakout_level,
            atr=inputs.atr,
            expected_gain=inputs.expected_gain,
        ),
    )
    block_scores = {
        "breakout": breakout_score,
        "continuation": continuation_score,
        "context": context_score,
        "cost_preference": cost_metrics.cost_preference_score,
    }
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_emit",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        microstructure_gate_applied=microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction.value,
        tier=tier.value,
        holding_hours=inputs.holding_period,
    )
    return EngineCOutput(
        pair=inputs.pair,
        decision=EngineCDecision.EMIT,
        **build_engine_c_output_payload(
            structure=structure,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            block_scores=block_scores,
            conviction=conviction,
            tier_suggestion=tier,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            cumulative_ofi=inputs.cumulative_ofi,
            queue_pressure=inputs.queue_pressure,
            vpin=inputs.vpin,
            kyle_lambda=inputs.kyle_lambda,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            invalidation=invalidation,
            holding_hours=inputs.holding_period,
        ),
    )


def _build_engine_c_invalidation(
    inputs: EngineCInput,
    invalidation_levels: InvalidationLevelsC,
) -> EngineCInvalidation:
    return EngineCInvalidation(
        stop_price=invalidation_levels.stop_price,
        target_price=invalidation_levels.target_price,
        risk_multiple=invalidation_levels.risk_multiple,
    )
