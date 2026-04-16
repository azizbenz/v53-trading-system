"""
Build-6 / engine_a / engine_a_runner
Canonical orchestrator for Engine A.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from data_backbone import resolve_delta_confirmation
from engines.engine_a.context_validator_a import (
    ContextInput,
    ContextResult,
    ContextVerdict,
    validate_context,
)
from engines.engine_a.conviction_builder_a import (
    ConvictionInput,
    ConvictionLevel,
    ConvictionResult,
    ENGINE_A_CONVICTION_CALIBRATION_STATUS,
    ENGINE_A_CONVICTION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TierSuggestion,
    build_conviction,
)
from engines.engine_a.cost_feasibility_a import (
    CostInput,
    CostResult,
    CostVerdict,
    check_cost_feasibility,
)
from engines.engine_a.invalidation_mapper_a import InvalidationMap, build_invalidation
from engines.engine_a.signal_reporter_a import NoTradeReason, SignalDecision
from engines.engine_a.structure_detector_a import (
    StructureInput,
    StructureResult,
    StructureVerdict,
    detect_structure,
)


class EngineADecision(StrEnum):
    """Engine A final decision."""

    EMIT = "emit"
    NO_TRADE = "no_trade"


class EngineALogEntry(BaseModel, frozen=True):
    """Structured log entry for Engine A."""

    event: str
    pair: str
    regime: str = ""
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    conviction: str = ""
    tier: str = ""
    invalidation: str = ""
    holding_hours: float = 0.0
    reasons: tuple[str, ...] = ()
    scoring_version: str = ""
    calibration_profile_id: str = ENGINE_A_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_A_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS


class EngineAOutput(BaseModel, frozen=True):
    """Complete canonical Engine A output."""

    pair: str
    engine_id: str = "engine_a"
    decision: EngineADecision
    raw_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevel = ConvictionLevel.NONE
    tier_suggestion: TierSuggestion = TierSuggestion.NO_TRADE
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    invalidation: InvalidationMap | None = None
    holding_hours: float = 0.0
    scoring_version: str = ""
    calibration_profile_id: str = ENGINE_A_CONVICTION_PROFILE_ID
    calibration_status: str = ENGINE_A_CONVICTION_CALIBRATION_STATUS
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS
    no_trade_reasons: tuple[NoTradeReason, ...] = ()
    structure_verdict: StructureVerdict = StructureVerdict.UNFAVORABLE
    context_verdict: ContextVerdict = ContextVerdict.FATAL
    cost_verdict: CostVerdict = CostVerdict.INFEASIBLE
    log_entries: tuple[EngineALogEntry, ...] = ()


class EngineAInput(BaseModel, frozen=True):
    """All inputs needed for a single Engine A evaluation."""

    pair: str
    direction_score: float
    continuation_score: float
    structure_quality: float
    zone_proximity: float
    trend_stability: float
    regime: str = ""
    regime_favorability: float = 0.5
    regime_confidence: float = 0.5
    pair_health: float = 0.5
    data_freshness: float = 0.5
    flow_coherence: float = 0.5
    flow_score: float = 0.0
    cost_preference_score: float = 0.0
    delta_confirmation: float | None = Field(default=None, ge=0.0, le=1.0)
    delta_proxy_soft_value: float | None = None
    delta_proxy_sign_value: float | None = None
    delta_proxy_reference_volume: float | None = Field(default=None, gt=0.0)
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    competition_density: float = 0.5
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 4.0
    delta_safe: float = 0.0005
    ce_min: float = 0.0001
    entry_price: float = 0.0
    atr: float = 0.0
    scoring_version: str = ""


_ENGINE_A_RUNNER_DEFAULT_FIELD_NAMES = (
    "regime",
    "regime_favorability",
    "regime_confidence",
    "pair_health",
    "data_freshness",
    "flow_coherence",
    "flow_score",
    "cost_preference_score",
    "delta_confirmation",
    "delta_proxy_soft_value",
    "delta_proxy_sign_value",
    "delta_proxy_reference_volume",
    "execution_fragility",
    "market_toxicity",
    "spread_regime_penalty",
    "competition_density",
    "expected_gain",
    "expected_cost",
    "candidate_size",
    "holding_period",
    "delta_safe",
    "ce_min",
    "entry_price",
    "atr",
    "scoring_version",
)

ENGINE_A_RUNNER_INPUT_DEFAULTS: dict[str, float | str | None] = {
    field_name: EngineAInput.model_fields[field_name].default
    for field_name in _ENGINE_A_RUNNER_DEFAULT_FIELD_NAMES
}


def _append_engine_a_log(
    logs: list[EngineALogEntry],
    *,
    event: str,
    pair: str,
    regime: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    expected_cost: float = 0.0,
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
        EngineALogEntry(
            event=event,
            pair=pair,
            regime=regime,
            raw_score=raw_score,
            penalized_score=penalized_score,
            block_scores={} if block_scores is None else block_scores,
            expected_cost=expected_cost,
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


def _build_engine_a_no_trade_output(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
    no_trade_reasons: list[NoTradeReason],
    *,
    raw_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    conviction: ConvictionLevel = ConvictionLevel.NONE,
    tier_suggestion: TierSuggestion = TierSuggestion.NO_TRADE,
    structure_verdict: StructureVerdict = StructureVerdict.UNFAVORABLE,
    context_verdict: ContextVerdict = ContextVerdict.FATAL,
    cost_verdict: CostVerdict = CostVerdict.INFEASIBLE,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
) -> EngineAOutput:
    return EngineAOutput(
        pair=inputs.pair,
        decision=EngineADecision.NO_TRADE,
        raw_score=raw_score,
        block_scores={} if block_scores is None else block_scores,
        conviction=conviction,
        tier_suggestion=tier_suggestion,
        structure_verdict=structure_verdict,
        context_verdict=context_verdict,
        cost_verdict=cost_verdict,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        no_trade_reasons=tuple(no_trade_reasons),
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )


def _early_exit_no_trade(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
    no_trade_reasons: list[NoTradeReason],
    *,
    reason: NoTradeReason,
    log_reasons: tuple[str, ...] | None = None,
    raw_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    conviction: ConvictionLevel = ConvictionLevel.NONE,
    tier_suggestion: TierSuggestion = TierSuggestion.NO_TRADE,
    structure_verdict: StructureVerdict = StructureVerdict.UNFAVORABLE,
    context_verdict: ContextVerdict = ContextVerdict.FATAL,
    cost_verdict: CostVerdict = CostVerdict.INFEASIBLE,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
) -> EngineAOutput:
    no_trade_reasons.append(reason)
    _append_engine_a_log(
        logs,
        event="engine_a_no_trade",
        pair=inputs.pair,
        regime=inputs.regime,
        reasons=(
            tuple(str(recorded_reason) for recorded_reason in no_trade_reasons)
            if log_reasons is None
            else log_reasons
        ),
    )
    return _build_engine_a_no_trade_output(
        inputs,
        logs,
        no_trade_reasons,
        raw_score=raw_score,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier_suggestion,
        structure_verdict=structure_verdict,
        context_verdict=context_verdict,
        cost_verdict=cost_verdict,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
    )


def _evaluate_structure_stage(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
) -> StructureResult:
    structure = detect_structure(
        StructureInput(
            pair=inputs.pair,
            direction_score=inputs.direction_score,
            continuation_score=inputs.continuation_score,
            structure_quality=inputs.structure_quality,
            zone_proximity=inputs.zone_proximity,
            trend_stability=inputs.trend_stability,
        )
    )
    _append_engine_a_log(
        logs,
        event="engine_a_structure_evaluated",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=structure.structure_score,
        reasons=(structure.reason,) if structure.reason else (),
    )
    return structure


def _evaluate_context_stage(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
) -> ContextResult:
    context = validate_context(
        ContextInput(
            pair=inputs.pair,
            regime_favorability=inputs.regime_favorability,
            regime_confidence=inputs.regime_confidence,
            pair_health=inputs.pair_health,
            data_freshness=inputs.data_freshness,
            flow_coherence=inputs.flow_coherence,
        )
    )
    _append_engine_a_log(
        logs,
        event="engine_a_context_evaluated",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=context.context_score,
        reasons=(context.reason,) if context.reason else (),
    )
    return context


def _evaluate_cost_stage(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
) -> CostResult:
    cost = check_cost_feasibility(
        CostInput(
            pair=inputs.pair,
            expected_gain=inputs.expected_gain,
            expected_cost=inputs.expected_cost,
            candidate_size=inputs.candidate_size,
            holding_period=inputs.holding_period,
            delta_safe=inputs.delta_safe,
            ce_min=inputs.ce_min,
        )
    )
    _append_engine_a_log(
        logs,
        event="engine_a_cost_checked",
        pair=inputs.pair,
        regime=inputs.regime,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        reasons=(cost.reason,) if cost.reason else (),
    )
    return cost


def _evaluate_conviction_stage(
    inputs: EngineAInput,
    structure: StructureResult,
    context: ContextResult,
    logs: list[EngineALogEntry],
) -> ConvictionResult:
    delta_confirmation = resolve_delta_confirmation(
        delta_confirmation=inputs.delta_confirmation,
        delta_proxy_soft_value=inputs.delta_proxy_soft_value,
        delta_proxy_sign_value=inputs.delta_proxy_sign_value,
        reference_volume=inputs.delta_proxy_reference_volume,
    )
    conviction = build_conviction(
        ConvictionInput(
            pair=inputs.pair,
            structure_score=structure.structure_score,
            context_score=context.context_score,
            flow_score=inputs.flow_score,
            cost_preference_score=inputs.cost_preference_score,
            delta_confirmation=delta_confirmation,
            execution_fragility=inputs.execution_fragility,
            market_toxicity=inputs.market_toxicity,
            spread_regime_penalty=inputs.spread_regime_penalty,
            competition_density=inputs.competition_density,
            scoring_version=inputs.scoring_version,
        )
    )
    _append_engine_a_log(
        logs,
        event="engine_a_conviction_built",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=conviction.raw_score,
        penalized_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
    )
    return conviction


def _evaluate_invalidation_stage(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
) -> InvalidationMap:
    invalidation = build_invalidation(
        pair=inputs.pair,
        direction_score=inputs.direction_score,
        entry_price=inputs.entry_price,
        atr=inputs.atr,
        holding_hours=inputs.holding_period,
    )
    _append_engine_a_log(
        logs,
        event="engine_a_invalidation_built",
        pair=inputs.pair,
        regime=inputs.regime,
        invalidation=invalidation.primary_invalidation,
        holding_hours=invalidation.expected_holding_hours,
    )
    return invalidation


def _build_engine_a_emit_output(
    inputs: EngineAInput,
    structure: StructureResult,
    context: ContextResult,
    cost: CostResult,
    conviction: ConvictionResult,
    invalidation: InvalidationMap,
    logs: list[EngineALogEntry],
) -> EngineAOutput:
    _append_engine_a_log(
        logs,
        event="engine_a_signal_emitted",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=conviction.raw_score,
        penalized_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
        invalidation=invalidation.primary_invalidation,
        holding_hours=invalidation.expected_holding_hours,
        scoring_version=inputs.scoring_version,
    )
    return EngineAOutput(
        pair=inputs.pair,
        decision=EngineADecision.EMIT,
        raw_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction,
        tier_suggestion=conviction.tier_suggestion,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        invalidation=invalidation,
        holding_hours=invalidation.expected_holding_hours,
        structure_verdict=structure.verdict,
        context_verdict=context.verdict,
        cost_verdict=cost.verdict,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )


def run_engine_a(inputs: EngineAInput) -> EngineAOutput:
    """Execute the full Engine A pipeline and produce canonical output."""

    logs: list[EngineALogEntry] = []
    no_trade_reasons: list[NoTradeReason] = []

    if inputs.direction_score <= 0:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=NoTradeReason.NON_LONG_DIRECTION,
            log_reasons=(f"direction_score={inputs.direction_score:.3f} <= 0 - long-only",),
        )

    structure = _evaluate_structure_stage(inputs, logs)
    if structure.verdict == StructureVerdict.UNFAVORABLE:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=NoTradeReason.STRUCTURE_UNFAVORABLE,
            structure_verdict=structure.verdict,
        )

    context = _evaluate_context_stage(inputs, logs)
    if context.verdict == ContextVerdict.FATAL:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=NoTradeReason.CONTEXT_FATAL,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
        )

    cost = _evaluate_cost_stage(inputs, logs)
    if cost.verdict == CostVerdict.INFEASIBLE:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=NoTradeReason.COST_INFEASIBLE,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            cost_verdict=cost.verdict,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
        )

    conviction = _evaluate_conviction_stage(inputs, structure, context, logs)
    if conviction.conviction == ConvictionLevel.NONE:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=NoTradeReason.CONVICTION_NONE,
            raw_score=conviction.raw_score,
            block_scores=conviction.block_scores,
            conviction=conviction.conviction,
            tier_suggestion=conviction.tier_suggestion,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            cost_verdict=cost.verdict,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
        )

    invalidation = _evaluate_invalidation_stage(inputs, logs)
    return _build_engine_a_emit_output(
        inputs,
        structure,
        context,
        cost,
        conviction,
        invalidation,
        logs,
    )


__all__ = [
    "EngineADecision",
    "EngineALogEntry",
    "EngineAOutput",
    "EngineAInput",
    "ENGINE_A_RUNNER_INPUT_DEFAULTS",
    "run_engine_a",
]
