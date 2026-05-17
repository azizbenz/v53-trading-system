"""Canonical Engine C runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .continuation_validator_c import (
    ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE,
    EngineCContinuationValidationInput,
    EngineCContinuationValidationResult,
    validate_continuation_c,
)
from .conviction_builder_c import ConvictionResultC, build_conviction_c
from .cost_feasibility_c import (
    ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE,
    CostMetricsC,
    evaluate_cost_feasibility_c,
)
from .invalidation_mapper_c import build_invalidation_levels_c
from .output_payload_builder_c import build_engine_c_output_payload
from .signal_math_c import (
    compute_breakout_score,
    compute_context_score,
    compute_fake_breakout_risk,
)
from .structure_resolver_c import resolve_engine_c_structure

EngineCStructure = dict[str, float | str | bool]

class EngineCDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonC(StrEnum):
    NON_LONG_BREAKOUT = "non_long_breakout"
    INVALID_ENTRY_PRICE = "invalid_entry_price"
    INVALID_CANDIDATE_SIZE = "invalid_candidate_size"
    INVALID_HOLDING_PERIOD = "invalid_holding_period"
    INVALID_BREAKOUT_LEVEL = "invalid_breakout_level"
    INVALID_STOP_GE_ENTRY = "invalid_stop_ge_entry"
    INVALID_TARGET_LE_ENTRY = "invalid_target_le_entry"
    INVALID_RISK_MULTIPLE = "invalid_risk_multiple"
    INVALID_ATR = "invalid_atr"
    BREAKOUT_UNSTRUCTURED = "breakout_unstructured"
    CONTINUATION_NOT_VIABLE = "continuation_not_viable"
    MICROSTRUCTURE_UNCONFIRMED = "microstructure_unconfirmed"
    FAKE_BREAKOUT_BLOCKED = "fake_breakout_blocked"
    COST_INFEASIBLE = "cost_infeasible"
    DUPLICATION_BLOCKED = "duplication_blocked"
    LOW_CONVICTION = "low_conviction"


class ConvictionLevelC(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TierSuggestionC(StrEnum):
    NO_TRADE = "no_trade"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"

ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE: dict[str, float | str] = {
    "calibration_status": "TO_CALIBRATE",
    "breakout_score_min": 0.62,
    "breakout_strength_min": 0.55,
    "range_quality_min": 0.50,
    "fake_breakout_risk_max": 0.65,
}


class EngineCRunnerThresholds(BaseModel, frozen=True):
    breakout_score_min: float = Field(default=ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE["breakout_score_min"], ge=0.0, le=1.0)
    breakout_strength_min: float = Field(default=ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE["breakout_strength_min"], ge=0.0, le=1.0)
    range_quality_min: float = Field(default=ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE["range_quality_min"], ge=0.0, le=1.0)
    fake_breakout_risk_max: float = Field(default=ENGINE_C_RUNNER_THRESHOLDS_TO_CALIBRATE["fake_breakout_risk_max"], ge=0.0, le=1.0)


ENGINE_C_THRESHOLDS = EngineCRunnerThresholds()
ENGINE_C_INPUT_DEFAULTS_TO_CALIBRATE: dict[str, float | str] = {
    "calibration_status": "TO_CALIBRATE",
    "holding_period": 3.0,
    "ce_min": ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE.ce_min,
    "delta_safe": ENGINE_C_COST_CALLER_THRESHOLDS_TO_CALIBRATE.delta_safe,
}

class EngineCInvalidation(BaseModel, frozen=True):
    stop_price: float = Field(..., gt=0.0)
    target_price: float = Field(..., gt=0.0)
    risk_multiple: float = Field(..., gt=0.0)
    reference_source: str = ""


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
    local_duplication_policy_triggered: bool = False
    duplication_blocked: bool = False
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
    microstructure_required: bool = False
    microstructure_missing: bool = False
    microstructure_contradictory: bool = False
    fake_breakout_risk: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    duplication_possible_with_engine_a: bool = False
    duplication_overlap_with_engine_a: float = 0.0
    local_duplication_policy_triggered: bool = False
    duplication_blocked: bool = False
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    keff_contribution: float = 0.0
    invalidation: EngineCInvalidation | None = None
    holding_hours: float = 0.0
    scoring_version: str = ""
    reason_codes: tuple[str, ...] = ()
    no_trade_reasons: tuple[NoTradeReasonC, ...] = ()
    log_entries: tuple[EngineCLogEntry, ...] = ()


class EngineCInput(BaseModel, frozen=True):
    pair: str
    breakout_strength: float = Field(..., ge=0.0, le=1.0)
    range_quality: float = Field(..., ge=0.0, le=1.0)
    compression_quality: float = Field(..., ge=0.0, le=1.0)
    volume_confirmation: float = Field(..., ge=0.0, le=1.0)
    followthrough_room: float = Field(..., ge=0.0, le=1.0)
    extension_pct: float = Field(..., ge=0.0, le=1.0)
    retrace_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_wick_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    regime: str = ""
    regime_favorability: float = Field(default=0.5, ge=0.0, le=1.0)
    pair_health: float = Field(default=0.5, ge=0.0, le=1.0)
    data_freshness: float = Field(default=0.5, ge=0.0, le=1.0)
    flow_coherence: float = Field(default=0.5, ge=0.0, le=1.0)
    # Canonical microstructure provenance seam: continuation logic consumes
    # upstream shared-package evidence through these additive fields.
    cumulative_ofi: float | None = None
    queue_pressure: float | None = Field(default=None, ge=-1.0, le=1.0)
    vpin: float | None = Field(default=None, ge=0.0, le=1.0)
    kyle_lambda: float | None = Field(default=None, ge=0.0)
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    realized_vol_at_break: float | None = Field(default=None, ge=0.0)
    continuation_ofi_min: float = ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.ofi_min
    continuation_queue_min: float = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.queue_min,
        ge=-1.0,
        le=1.0,
    )
    continuation_vpin_max: float | None = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.vpin_max,
        ge=0.0,
        le=1.0,
    )
    continuation_kyle_lambda_max: float | None = Field(
        default=ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE.kyle_lambda_max,
        ge=0.0,
    )
    expected_gain: float = Field(default=0.0, ge=0.0)
    expected_cost: float = Field(default=0.0, ge=0.0)
    candidate_size: float = Field(default=0.0, ge=0.0)
    holding_period: float = Field(default=ENGINE_C_INPUT_DEFAULTS_TO_CALIBRATE["holding_period"], ge=0.0)
    ce_min: float = Field(default=ENGINE_C_INPUT_DEFAULTS_TO_CALIBRATE["ce_min"], ge=0.0)
    delta_safe: float = Field(default=ENGINE_C_INPUT_DEFAULTS_TO_CALIBRATE["delta_safe"], ge=0.0)
    entry_price: float = Field(default=0.0, ge=0.0)
    breakout_level: float = Field(default=0.0, ge=0.0)
    range_low: float = 0.0
    range_high: float = 0.0
    # Legacy overlay only. Central forecast / invalidation / structure logic must
    # not consume ATR on the doctrinal rail.
    atr: float = Field(default=0.0, ge=0.0)
    engine_a_overlap_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = Field(default=0.0, ge=0.0, le=1.0)
    keff_contribution: float = Field(default=0.0, ge=0.0, le=1.0)
    scoring_version: str = ""


from .engine_c_runner_support import (  # noqa: E402
    append_engine_c_log as _append_engine_c_log,
    build_engine_c_emit_output as _build_engine_c_emit_output,
    build_engine_c_invalidation as _build_engine_c_invalidation,
    build_engine_c_no_trade_output as _build_engine_c_no_trade_output,
    build_engine_c_reason_codes as _build_engine_c_reason_codes,
    evaluate_engine_c_duplication_policy as _evaluate_portfolio_awareness_stage,
    evaluate_engine_c_input_guards as _evaluate_input_guards_stage,
)


def run_engine_c(inputs: EngineCInput) -> EngineCOutput:
    logs: list[EngineCLogEntry] = []
    no_trade_reasons: list[NoTradeReasonC] = []
    structure = resolve_engine_c_structure(inputs)
    context_score, continuation_preview = _prepare_continuation_preview(inputs)
    no_trade_output = _evaluate_input_guards_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        continuation_validation=continuation_preview,
        continuation_score=continuation_preview.continuation_score,
    )
    if no_trade_output is not None:
        return no_trade_output
    breakout_score, no_trade_output = _evaluate_breakout_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        context_score=context_score,
        continuation_validation=continuation_preview,
    )
    if no_trade_output is not None:
        return no_trade_output
    context_score, continuation_validation, no_trade_output = _evaluate_continuation_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        context_score=context_score,
        continuation_validation=continuation_preview,
    )
    if no_trade_output is not None:
        return no_trade_output
    fake_breakout_risk, no_trade_output = _evaluate_fake_breakout_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        microstructure_required=continuation_validation.microstructure_required,
        microstructure_missing=continuation_validation.microstructure_missing,
        microstructure_contradictory=continuation_validation.microstructure_contradictory,
    )
    if no_trade_output is not None:
        return no_trade_output
    cost_metrics, no_trade_output = _evaluate_cost_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        continuation_validation=continuation_validation,
        fake_breakout_risk=fake_breakout_risk,
        microstructure_required=continuation_validation.microstructure_required,
        microstructure_missing=continuation_validation.microstructure_missing,
        microstructure_contradictory=continuation_validation.microstructure_contradictory,
    )
    if no_trade_output is not None:
        return no_trade_output
    no_trade_output = _evaluate_portfolio_awareness_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        continuation_validation=continuation_validation,
        fake_breakout_risk=fake_breakout_risk,
        cost_metrics=cost_metrics,
        microstructure_required=continuation_validation.microstructure_required,
        microstructure_missing=continuation_validation.microstructure_missing,
        microstructure_contradictory=continuation_validation.microstructure_contradictory,
    )
    if no_trade_output is not None:
        return no_trade_output
    conviction_result, no_trade_output = _evaluate_conviction_stage(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        breakout_score=breakout_score,
        context_score=context_score,
        continuation_validation=continuation_validation,
        fake_breakout_risk=fake_breakout_risk,
        cost_metrics=cost_metrics,
    )
    if no_trade_output is not None:
        return no_trade_output
    return _build_engine_c_emit_output(
        inputs,
        structure,
        logs,
        breakout_score=breakout_score,
        context_score=context_score,
        continuation_validation=continuation_validation,
        fake_breakout_risk=fake_breakout_risk,
        cost_metrics=cost_metrics,
        conviction_result=conviction_result,
    )


def _prepare_continuation_preview(
    inputs: EngineCInput,
) -> tuple[float, EngineCContinuationValidationResult]:
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
            kyle_lambda_max=inputs.continuation_kyle_lambda_max,
        )
    )
    return context_score, continuation_validation


def _evaluate_breakout_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    context_score: float,
    continuation_validation: EngineCContinuationValidationResult,
) -> tuple[float, EngineCOutput | None]:
    if inputs.breakout_strength <= 0.0:
        no_trade_reasons.append(NoTradeReasonC.NON_LONG_BREAKOUT)
        _append_engine_c_log(
            logs,
            inputs,
            structure,
            event="engine_c_no_trade",
            continuation_score=continuation_validation.continuation_score,
            cumulative_ofi=continuation_validation.cumulative_ofi,
            queue_pressure=continuation_validation.queue_pressure,
            vpin=continuation_validation.vpin,
            kyle_lambda=continuation_validation.kyle_lambda,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            reasons=(f"breakout_strength={inputs.breakout_strength:.3f} <= 0",),
        )
        return 0.0, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            continuation_score=continuation_validation.continuation_score,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            microstructure_required=continuation_validation.microstructure_required,
            microstructure_missing=continuation_validation.microstructure_missing,
            microstructure_contradictory=continuation_validation.microstructure_contradictory,
        )
    breakout_score = compute_breakout_score(inputs)
    _append_engine_c_log(logs, inputs, structure, event="engine_c_breakout_evaluated", breakout_score=breakout_score, raw_score=breakout_score)
    if (
        breakout_score < ENGINE_C_THRESHOLDS.breakout_score_min
        or inputs.breakout_strength < ENGINE_C_THRESHOLDS.breakout_strength_min
        or inputs.range_quality < ENGINE_C_THRESHOLDS.range_quality_min
    ):
        no_trade_reasons.append(NoTradeReasonC.BREAKOUT_UNSTRUCTURED)
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
            reasons=("breakout structure insufficient",),
        )
        return breakout_score, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
            continuation_score=continuation_validation.continuation_score,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            microstructure_required=continuation_validation.microstructure_required,
            microstructure_missing=continuation_validation.microstructure_missing,
            microstructure_contradictory=continuation_validation.microstructure_contradictory,
        )
    return breakout_score, None


def _evaluate_continuation_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    context_score: float,
    continuation_validation: EngineCContinuationValidationResult,
) -> tuple[float, EngineCContinuationValidationResult, EngineCOutput | None]:
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
            NoTradeReasonC.CONTINUATION_NOT_VIABLE if not continuation_validation.continuation_viable else NoTradeReasonC.MICROSTRUCTURE_UNCONFIRMED
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
        return context_score, continuation_validation, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
            continuation_score=continuation_validation.continuation_score,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            microstructure_required=continuation_validation.microstructure_required,
            microstructure_missing=continuation_validation.microstructure_missing,
            microstructure_contradictory=continuation_validation.microstructure_contradictory,
        )
    return context_score, continuation_validation, None


def _evaluate_fake_breakout_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    continuation_score: float,
    microstructure_gate_applied: bool,
    microstructure_required: bool = False,
    microstructure_missing: bool = False,
    microstructure_contradictory: bool = False,
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
    if fake_breakout_risk >= ENGINE_C_THRESHOLDS.fake_breakout_risk_max:
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
            raw_score=breakout_score,
            penalized_score=penalized_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            microstructure_gate_applied=microstructure_gate_applied,
            microstructure_required=microstructure_required,
            microstructure_missing=microstructure_missing,
            microstructure_contradictory=microstructure_contradictory,
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
    continuation_validation: EngineCContinuationValidationResult,
    fake_breakout_risk: float,
    microstructure_required: bool,
    microstructure_missing: bool,
    microstructure_contradictory: bool,
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
        reasons=tuple(reason.value for reason in cost_metrics.reason_codes),
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
            reasons=tuple(reason.value for reason in cost_metrics.reason_codes),
        )
        return cost_metrics, _build_engine_c_no_trade_output(
            inputs,
            structure,
            logs,
            no_trade_reasons,
            breakout_score=breakout_score,
            continuation_score=continuation_validation.continuation_score,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            microstructure_required=microstructure_required,
            microstructure_missing=microstructure_missing,
            microstructure_contradictory=microstructure_contradictory,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            cost_feasible=False,
        )
    return cost_metrics, None


def _evaluate_conviction_stage(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    context_score: float,
    continuation_validation: EngineCContinuationValidationResult,
    fake_breakout_risk: float,
    cost_metrics: CostMetricsC,
) -> tuple[ConvictionResultC, EngineCOutput | None]:
    conviction_result = build_conviction_c(
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        context_score=context_score,
        ce_expected=cost_metrics.ce_expected,
        ce_min=inputs.ce_min,
        fake_breakout_risk=fake_breakout_risk,
    )
    if conviction_result.is_emittable:
        return conviction_result, None
    no_trade_reasons.append(NoTradeReasonC.LOW_CONVICTION)
    _append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_no_trade",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction_result.conviction_name,
        tier=conviction_result.tier_name,
        reasons=("conviction below minimum emit threshold",),
    )
    return conviction_result, _build_engine_c_no_trade_output(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        microstructure_required=continuation_validation.microstructure_required,
        microstructure_missing=continuation_validation.microstructure_missing,
        microstructure_contradictory=continuation_validation.microstructure_contradictory,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction_result.conviction_name,
        tier=conviction_result.tier_name,
        cost_feasible=True,
    )


__all__ = ["ConvictionLevelC", "EngineCDecision", "EngineCInput", "EngineCInvalidation", "EngineCLogEntry", "EngineCOutput", "EngineCRunnerThresholds", "NoTradeReasonC", "TierSuggestionC", "run_engine_c"]
