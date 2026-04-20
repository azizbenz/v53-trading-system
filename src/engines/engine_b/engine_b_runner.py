"""
Build-7 / engine_b / engine_b_runner
Canonical orchestrator for Engine B.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from engines.engine_b.anti_breakout_filter_b import BreakoutVerdict
from engines.engine_b.conviction_builder_b import (
    ConvictionLevelB,
    ENGINE_B_CONVICTION_INPUT_DEFAULTS,
    ENGINE_B_CONVICTION_CALIBRATION_STATUS,
    ENGINE_B_CONVICTION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TierSuggestionB,
)
from engines.engine_b.cost_feasibility_b import (
    ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE,
    CostVerdictB,
)
from engines.engine_b.excess_detector_b import ExcessVerdict
from engines.engine_b.invalidation_mapper_b import InvalidationMapB
from engines.engine_b.signal_reporter_b import NoTradeReasonB


class EngineBDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class EngineBLogEntry(BaseModel, frozen=True):
    """Structured log entry for Engine B."""

    event: str
    pair: str
    regime: str = ""
    local_mean: float = 0.0
    local_std: float = 0.0
    z_score: float = 0.0
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    expected_cost: float = 0.0
    expected_duration: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    conviction: str = ""
    tier: str = ""
    invalidation: str = ""
    holding_hours: float = 0.0
    reasons: tuple[str, ...] = ()
    scoring_version: str = ""
    calibration_profile_id: str = ENGINE_B_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_B_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS


class EngineBOutput(BaseModel, frozen=True):
    """Complete canonical Engine B output."""

    pair: str
    engine_id: str = "engine_b"
    decision: EngineBDecision
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelB = ConvictionLevelB.NONE
    tier_suggestion: TierSuggestionB = TierSuggestionB.NO_TRADE
    z_score: float = 0.0
    excess_score: float = 0.0
    breakout_score: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    expected_holding_hours: float = 0.0
    invalidation: InvalidationMapB | None = None
    scoring_version: str = ""
    reason_codes: tuple[str, ...] = ()
    calibration_profile_id: str = ENGINE_B_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_B_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS
    no_trade_reasons: tuple[NoTradeReasonB, ...] = ()
    excess_verdict: ExcessVerdict = ExcessVerdict.NO_EXCESS
    breakout_verdict: BreakoutVerdict = BreakoutVerdict.CLEAR
    cost_verdict: CostVerdictB = CostVerdictB.INFEASIBLE
    log_entries: tuple[EngineBLogEntry, ...] = ()


class EngineBInput(BaseModel, frozen=True):
    """All inputs needed for a single Engine B evaluation."""

    pair: str
    current_price: float
    local_mean: float
    local_std: float
    structure_is_range: float = Field(default=0.5, ge=0.0, le=1.0)
    recent_expansion: float = Field(default=0.0, ge=0.0, le=1.0)
    regime: str = ""
    regime_trend_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_anomaly: float = Field(default=0.0, ge=0.0, le=1.0)
    structural_break: float = Field(default=0.0, ge=0.0, le=1.0)
    continuation_momentum: float = Field(default=0.0, ge=0.0, le=1.0)
    microstructure_breakout_confirmation: float = Field(default=0.0, ge=0.0, le=1.0)
    sweep_score: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["sweep_score"], ge=0.0, le=1.0)
    absorption_score: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["absorption_score"], ge=0.0, le=1.0)
    poc_reversion_score: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["poc_reversion_score"], ge=0.0, le=1.0)
    false_breakout_score: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["false_breakout_score"], ge=0.0, le=1.0)
    execution_fragility: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["execution_fragility"], ge=0.0, le=1.0)
    market_toxicity: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["market_toxicity"], ge=0.0, le=1.0)
    spread_regime_penalty: float = Field(default=ENGINE_B_CONVICTION_INPUT_DEFAULTS["spread_regime_penalty"], ge=0.0, le=1.0)
    regime_favorability: float = Field(default=0.5, ge=0.0, le=1.0)
    pair_health: float = Field(default=0.5, ge=0.0, le=1.0)
    data_freshness: float = Field(default=0.5, ge=0.0, le=1.0)
    flow_coherence: float = Field(default=0.5, ge=0.0, le=1.0)
    vpin_current: float | None = Field(default=None, ge=0.0, le=1.0)
    toxic_flow_correlation: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_gain: float = Field(default=0.0, ge=0.0)
    expected_cost: float = Field(default=0.0, ge=0.0)
    candidate_size: float = Field(default=0.0, ge=0.0)
    holding_period: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.holding_period, ge=0.0)
    delta_safe: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.delta_safe, ge=0.0)
    ce_min: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.ce_min, ge=0.0)
    scoring_version: str = ""


# TO_CALIBRATE: runner-facing defaults remain here only as a single consolidation
# seam until CalibrationLoader owns the full Engine B parameter surface.
ENGINE_B_RUNNER_INPUT_DEFAULTS: dict[str, float | str] = {
    "structure_is_range": 0.5,
    "recent_expansion": 0.0,
    "regime": "",
    "regime_trend_strength": 0.0,
    "volume_anomaly": 0.0,
    "structural_break": 0.0,
    "continuation_momentum": 0.0,
    "microstructure_breakout_confirmation": 0.0,
    "sweep_score": ENGINE_B_CONVICTION_INPUT_DEFAULTS["sweep_score"],
    "absorption_score": ENGINE_B_CONVICTION_INPUT_DEFAULTS["absorption_score"],
    "poc_reversion_score": ENGINE_B_CONVICTION_INPUT_DEFAULTS["poc_reversion_score"],
    "false_breakout_score": ENGINE_B_CONVICTION_INPUT_DEFAULTS["false_breakout_score"],
    "execution_fragility": ENGINE_B_CONVICTION_INPUT_DEFAULTS["execution_fragility"],
    "market_toxicity": ENGINE_B_CONVICTION_INPUT_DEFAULTS["market_toxicity"],
    "spread_regime_penalty": ENGINE_B_CONVICTION_INPUT_DEFAULTS["spread_regime_penalty"],
    "regime_favorability": 0.5,
    "pair_health": 0.5,
    "data_freshness": 0.5,
    "flow_coherence": 0.5,
    "vpin_current": None,
    "toxic_flow_correlation": None,
    "expected_gain": 0.0,
    "expected_cost": 0.0,
    "candidate_size": 0.0,
    "holding_period": ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.holding_period,
    "delta_safe": ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.delta_safe,
    "ce_min": ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.ce_min,
    "scoring_version": "",
}
ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT = 4.0
ENGINE_B_RUNNER_COST_RATIO_EPSILON = 1e-9
ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT = 0.30

EngineBInput.model_fields["structure_is_range"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["structure_is_range"]
EngineBInput.model_fields["recent_expansion"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["recent_expansion"]
EngineBInput.model_fields["regime"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime"]
EngineBInput.model_fields["regime_trend_strength"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime_trend_strength"]
EngineBInput.model_fields["volume_anomaly"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["volume_anomaly"]
EngineBInput.model_fields["structural_break"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["structural_break"]
EngineBInput.model_fields["continuation_momentum"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["continuation_momentum"]
EngineBInput.model_fields["microstructure_breakout_confirmation"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["microstructure_breakout_confirmation"]
EngineBInput.model_fields["sweep_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["sweep_score"]
EngineBInput.model_fields["absorption_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["absorption_score"]
EngineBInput.model_fields["poc_reversion_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["poc_reversion_score"]
EngineBInput.model_fields["false_breakout_score"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["false_breakout_score"]
EngineBInput.model_fields["execution_fragility"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["execution_fragility"]
EngineBInput.model_fields["market_toxicity"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["market_toxicity"]
EngineBInput.model_fields["spread_regime_penalty"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["spread_regime_penalty"]
EngineBInput.model_fields["regime_favorability"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["regime_favorability"]
EngineBInput.model_fields["pair_health"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["pair_health"]
EngineBInput.model_fields["data_freshness"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["data_freshness"]
EngineBInput.model_fields["flow_coherence"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["flow_coherence"]
EngineBInput.model_fields["vpin_current"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["vpin_current"]
EngineBInput.model_fields["toxic_flow_correlation"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["toxic_flow_correlation"]
EngineBInput.model_fields["expected_gain"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["expected_gain"]
EngineBInput.model_fields["expected_cost"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["expected_cost"]
EngineBInput.model_fields["candidate_size"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["candidate_size"]
EngineBInput.model_fields["holding_period"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["holding_period"]
EngineBInput.model_fields["delta_safe"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["delta_safe"]
EngineBInput.model_fields["ce_min"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["ce_min"]
EngineBInput.model_fields["scoring_version"].default = ENGINE_B_RUNNER_INPUT_DEFAULTS["scoring_version"]

from .engine_b_runner_support import (
    _append_engine_b_log,
    _build_engine_b_emit_output,
    _build_engine_b_no_trade_output,
    _estimate_local_mean_stage,
    _evaluate_breakout_stage,
    _evaluate_conviction_stage,
    _evaluate_cost_stage,
    _evaluate_excess_stage,
    _evaluate_invalidation_stage,
    _resolve_input_preconditions,
    _resolve_breakout_penalty,
    _resolve_invalidation_error_reason_codes,
    build_engine_b_gate_reason_codes,
)


def run_engine_b(inputs: EngineBInput) -> EngineBOutput:
    """Execute the full Engine B pipeline and produce canonical output."""

    logs: list[EngineBLogEntry] = []
    no_trade_reasons: list[NoTradeReasonB] = []

    input_reason_codes, input_errors = _resolve_input_preconditions(inputs)
    if input_errors:
        no_trade_reasons.append(NoTradeReasonB.INVALID_INPUT)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=input_reason_codes)
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            reason_codes=build_engine_b_gate_reason_codes(
                gate_reason_codes=tuple(
                    f"hard_block.engine_b.input.{reason.value}"
                    for reason in no_trade_reasons
                ),
                detailed_reason_codes=input_reason_codes,
            ),
        )

    mean_result = _estimate_local_mean_stage(inputs, logs)
    if not mean_result.valid:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=("hard_block.engine_b.local_mean.invalid_dispersion",),
            detailed_reason_codes=("engine_b.local_mean.invalid_dispersion",),
        )
        no_trade_reasons.append(NoTradeReasonB.INVALID_DISPERSION)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            z_score=mean_result.z_score,
            reason_codes=reason_codes,
        )

    if mean_result.z_score > 0:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=("engine_internal.engine_b.direction.non_long",),
            detailed_reason_codes=("engine_b.direction.non_long",),
        )
        no_trade_reasons.append(NoTradeReasonB.NON_LONG_DIRECTION)
        _append_engine_b_log(
            logs,
            event="engine_b_no_trade",
            pair=inputs.pair,
            z_score=mean_result.z_score,
            reasons=reason_codes,
        )
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            z_score=mean_result.z_score,
            reason_codes=reason_codes,
        )

    excess = _evaluate_excess_stage(inputs, mean_result, logs)
    if excess.verdict in (ExcessVerdict.NO_EXCESS, ExcessVerdict.INVALID):
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=(f"engine_internal.engine_b.excess.{excess.verdict.value}",),
            detailed_reason_codes=tuple(
                dict.fromkeys(
                    (
                        f"engine_b.excess.{excess.verdict.value}",
                        *excess.active_reason_codes,
                        *excess.suppressed_reason_codes,
                    )
                )
            ),
        )
        no_trade_reasons.append(NoTradeReasonB.NO_EXCESS)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            excess_verdict=excess.verdict,
            reason_codes=reason_codes,
        )

    breakout = _evaluate_breakout_stage(inputs, logs)
    if breakout.verdict == BreakoutVerdict.BLOCKED:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=("engine_internal.engine_b.breakout.blocked",),
            detailed_reason_codes=("engine_b.breakout.blocked",),
        )
        no_trade_reasons.append(NoTradeReasonB.BREAKOUT_BLOCKED)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            breakout_score=breakout.breakout_score,
            excess_verdict=excess.verdict,
            breakout_verdict=breakout.verdict,
            reason_codes=reason_codes,
        )

    cost = _evaluate_cost_stage(inputs, logs)
    if not cost.is_emittable:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=(f"economics.engine_b.cost.{cost.verdict.value}",),
            detailed_reason_codes=tuple(reason.value for reason in cost.reason_codes),
        )
        no_trade_reasons.append(
            NoTradeReasonB.COST_MARGINAL if cost.verdict == CostVerdictB.MARGINAL else NoTradeReasonB.COST_INFEASIBLE
        )
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, z_score=mean_result.z_score, excess_score=excess.excess_score, breakout_score=breakout.breakout_score,
            expected_cost=cost.expected_cost, ce_expected=cost.ce_expected, ev_net=cost.ev_net,
            excess_verdict=excess.verdict, breakout_verdict=breakout.verdict, cost_verdict=cost.verdict,
            reason_codes=reason_codes,
        )

    conviction = _evaluate_conviction_stage(inputs, excess, logs)
    if not conviction.is_emittable:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=(f"scoring.engine_b.conviction.{conviction.conviction.value}",),
            detailed_reason_codes=(f"engine_b.conviction.{conviction.conviction.value}",),
        )
        no_trade_reasons.append(
            NoTradeReasonB.CONVICTION_LOW if conviction.conviction == ConvictionLevelB.LOW else NoTradeReasonB.CONVICTION_NONE
        )
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, raw_score=conviction.raw_score, block_scores=conviction.block_scores,
            conviction=conviction.conviction, tier_suggestion=conviction.tier_suggestion, z_score=mean_result.z_score,
            excess_score=excess.excess_score, breakout_score=breakout.breakout_score, expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected, ev_net=cost.ev_net, excess_verdict=excess.verdict, breakout_verdict=breakout.verdict,
            cost_verdict=cost.verdict, reason_codes=reason_codes
        )

    penalized_score = conviction.raw_score - _resolve_breakout_penalty(inputs, conviction, breakout, logs)
    try:
        invalidation = _evaluate_invalidation_stage(inputs, logs)
    except ValueError as exc:
        reason_codes = build_engine_b_gate_reason_codes(
            gate_reason_codes=("hard_block.engine_b.invalidation.invalid_contract",),
            detailed_reason_codes=_resolve_invalidation_error_reason_codes(exc),
        )
        no_trade_reasons.append(NoTradeReasonB.INVALID_INVALIDATION)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=reason_codes)
        return _build_engine_b_no_trade_output(
            inputs,
            logs,
            no_trade_reasons,
            raw_score=conviction.raw_score,
            block_scores=conviction.block_scores,
            conviction=conviction.conviction,
            tier_suggestion=conviction.tier_suggestion,
            z_score=mean_result.z_score,
            excess_score=excess.excess_score,
            breakout_score=breakout.breakout_score,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
            excess_verdict=excess.verdict,
            breakout_verdict=breakout.verdict,
            cost_verdict=cost.verdict,
            reason_codes=reason_codes,
        )
    return _build_engine_b_emit_output(
        inputs, mean_result, excess, breakout, cost, conviction, invalidation, logs, penalized_score=penalized_score
    )


__all__ = [
    "EngineBDecision",
    "EngineBLogEntry",
    "EngineBOutput",
    "EngineBInput",
    "ENGINE_B_RUNNER_INPUT_DEFAULTS",
    "ENGINE_B_RUNNER_CONTEXT_COMPONENT_COUNT",
    "ENGINE_B_RUNNER_COST_RATIO_EPSILON",
    "ENGINE_B_RUNNER_WARNING_PENALTY_WEIGHT",
    "run_engine_b",
]
