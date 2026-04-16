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
    ENGINE_B_CONVICTION_CALIBRATION_STATUS,
    ENGINE_B_CONVICTION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TierSuggestionB,
)
from engines.engine_b.cost_feasibility_b import CostVerdictB
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
    structure_is_range: float = 0.5
    recent_expansion: float = 0.0
    regime: str = ""
    regime_trend_strength: float = 0.0
    volume_anomaly: float = 0.0
    structural_break: float = 0.0
    continuation_momentum: float = 0.0
    microstructure_breakout_confirmation: float = 0.0
    sweep_score: float = 0.5
    absorption_score: float = 0.5
    poc_reversion_score: float = 0.5
    false_breakout_score: float = 0.5
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    regime_favorability: float = 0.5
    pair_health: float = 0.5
    data_freshness: float = 0.5
    flow_coherence: float = 0.5
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 2.0
    delta_safe: float = 0.0008
    ce_min: float = 0.0002
    scoring_version: str = ""


ENGINE_B_RUNNER_INPUT_DEFAULTS: dict[str, float | str] = {
    "structure_is_range": 0.5,
    "recent_expansion": 0.0,
    "regime": "",
    "regime_trend_strength": 0.0,
    "volume_anomaly": 0.0,
    "structural_break": 0.0,
    "continuation_momentum": 0.0,
    "microstructure_breakout_confirmation": 0.0,
    "sweep_score": 0.5,
    "absorption_score": 0.5,
    "poc_reversion_score": 0.5,
    "false_breakout_score": 0.5,
    "execution_fragility": 0.0,
    "market_toxicity": 0.0,
    "spread_regime_penalty": 0.0,
    "regime_favorability": 0.5,
    "pair_health": 0.5,
    "data_freshness": 0.5,
    "flow_coherence": 0.5,
    "expected_gain": 0.0,
    "expected_cost": 0.0,
    "candidate_size": 0.0,
    "holding_period": 2.0,
    "delta_safe": 0.0008,
    "ce_min": 0.0002,
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
    _resolve_breakout_penalty,
)


def run_engine_b(inputs: EngineBInput) -> EngineBOutput:
    """Execute the full Engine B pipeline and produce canonical output."""

    logs: list[EngineBLogEntry] = []
    no_trade_reasons: list[NoTradeReasonB] = []

    mean_result = _estimate_local_mean_stage(inputs, logs)
    if not mean_result.valid:
        no_trade_reasons.append(NoTradeReasonB.INVALID_DISPERSION)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=("invalid dispersion",))
        return _build_engine_b_no_trade_output(inputs, logs, no_trade_reasons, z_score=mean_result.z_score)

    if mean_result.z_score > 0:
        no_trade_reasons.append(NoTradeReasonB.NON_LONG_DIRECTION)
        _append_engine_b_log(
            logs,
            event="engine_b_no_trade",
            pair=inputs.pair,
            z_score=mean_result.z_score,
            reasons=(f"z_score={mean_result.z_score:.3f} > 0 - long-only, cannot short",),
        )
        return _build_engine_b_no_trade_output(inputs, logs, no_trade_reasons, z_score=mean_result.z_score)

    excess = _evaluate_excess_stage(inputs, mean_result, logs)
    if excess.verdict in (ExcessVerdict.NO_EXCESS, ExcessVerdict.INVALID):
        no_trade_reasons.append(NoTradeReasonB.NO_EXCESS)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=tuple(str(reason) for reason in no_trade_reasons))
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, z_score=mean_result.z_score, excess_score=excess.excess_score, excess_verdict=excess.verdict
        )

    breakout = _evaluate_breakout_stage(inputs, logs)
    if breakout.verdict == BreakoutVerdict.BLOCKED:
        no_trade_reasons.append(NoTradeReasonB.BREAKOUT_BLOCKED)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=tuple(str(reason) for reason in no_trade_reasons))
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, z_score=mean_result.z_score, excess_score=excess.excess_score, breakout_score=breakout.breakout_score,
            excess_verdict=excess.verdict, breakout_verdict=breakout.verdict
        )

    cost = _evaluate_cost_stage(inputs, logs)
    if cost.verdict == CostVerdictB.INFEASIBLE:
        no_trade_reasons.append(NoTradeReasonB.COST_INFEASIBLE)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=tuple(str(reason) for reason in no_trade_reasons))
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, z_score=mean_result.z_score, excess_score=excess.excess_score, breakout_score=breakout.breakout_score,
            expected_cost=cost.expected_cost, ce_expected=cost.ce_expected, ev_net=cost.ev_net,
            excess_verdict=excess.verdict, breakout_verdict=breakout.verdict, cost_verdict=cost.verdict
        )

    conviction = _evaluate_conviction_stage(inputs, excess, logs)
    if conviction.conviction == ConvictionLevelB.NONE:
        no_trade_reasons.append(NoTradeReasonB.CONVICTION_NONE)
        _append_engine_b_log(logs, event="engine_b_no_trade", pair=inputs.pair, reasons=tuple(str(reason) for reason in no_trade_reasons))
        return _build_engine_b_no_trade_output(
            inputs, logs, no_trade_reasons, raw_score=conviction.raw_score, block_scores=conviction.block_scores,
            conviction=conviction.conviction, tier_suggestion=conviction.tier_suggestion, z_score=mean_result.z_score,
            excess_score=excess.excess_score, breakout_score=breakout.breakout_score, expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected, ev_net=cost.ev_net, excess_verdict=excess.verdict, breakout_verdict=breakout.verdict,
            cost_verdict=cost.verdict
        )

    penalized_score = conviction.raw_score - _resolve_breakout_penalty(inputs, conviction, breakout, logs)
    invalidation = _evaluate_invalidation_stage(inputs, logs)
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
