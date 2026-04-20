"""Build-6 / engine_a / engine_a_runner: canonical orchestrator for Engine A."""

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
    ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE,
    check_cost_feasibility,
)
from engines.engine_a.invalidation_mapper_a import InvalidationMap, build_invalidation
from engines.engine_a.signal_reporter_a import NoTradeReason, SignalDecision
from engines.engine_a.engine_a_runner_support import (
    append_engine_a_log as _append_engine_a_log_impl,
    build_engine_a_branch_log_reasons,
    build_engine_a_cost_log_reasons,
    build_engine_a_emit_reason_codes,
    build_engine_a_gate_reason_codes,
    build_engine_a_guard_log_reasons,
    build_engine_a_no_trade_output as _build_engine_a_no_trade_output_impl,
    early_exit_engine_a_no_trade as _early_exit_no_trade_impl,
)
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
    reason_codes: tuple[str, ...] = ()
    structure_verdict: StructureVerdict = StructureVerdict.UNFAVORABLE
    context_verdict: ContextVerdict = ContextVerdict.FATAL
    cost_verdict: CostVerdict = CostVerdict.INFEASIBLE
    log_entries: tuple[EngineALogEntry, ...] = ()


class EngineAInput(BaseModel, frozen=True):
    """All inputs needed for a single Engine A evaluation."""

    pair: str
    direction_score: float = Field(..., ge=-1.0, le=1.0)
    continuation_score: float = Field(..., ge=0.0, le=1.0)
    structure_quality: float = Field(..., ge=0.0, le=1.0)
    zone_proximity: float = Field(..., ge=0.0, le=1.0)
    trend_stability: float = Field(..., ge=0.0, le=1.0)
    # Canonical microstructure provenance seam: these additive fields must be
    # populated upstream from the shared package, not recomputed inside Engine A.
    realized_kernel_vol_scale: float | None = Field(default=None, ge=0.0, le=1.0)
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    regime: str = ""
    regime_favorability: float = Field(default=0.5, ge=0.0, le=1.0)
    regime_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    pair_health: float = Field(default=0.5, ge=0.0, le=1.0)
    data_freshness: float = Field(default=0.5, ge=0.0, le=1.0)
    flow_coherence: float = Field(default=0.5, ge=0.0, le=1.0)
    flow_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ofi_flow_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_preference_score: float = Field(default=0.0, ge=0.0, le=1.0)
    delta_confirmation: float | None = Field(default=None, ge=0.0, le=1.0)
    delta_proxy_soft_value: float | None = None
    delta_proxy_sign_value: float | None = None
    delta_proxy_reference_volume: float | None = Field(default=None, gt=0.0)
    execution_fragility: float = Field(default=0.0, ge=0.0, le=1.0)
    market_toxicity: float = Field(default=0.0, ge=0.0, le=1.0)
    spread_regime_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    competition_density: float = Field(default=0.5, ge=0.0, le=1.0)
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    kyle_lambda_cost_uplift: float = Field(default=0.0, ge=0.0)
    candidate_size: float = 0.0
    holding_period: float = ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.holding_period
    delta_safe: float = ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.delta_safe
    ce_min: float = ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.ce_min
    entry_price: float = 0.0
    # Legacy overlay only. Central forecast / invalidation logic must consume
    # the governed realized-vol seam instead of ATR.
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
    "ofi_flow_score",
    "realized_kernel_vol_scale",
    "realized_vol_current",
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
    "kyle_lambda_cost_uplift",
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


def _append_engine_a_log(logs: list[EngineALogEntry], **kwargs: object) -> None:
    _append_engine_a_log_impl(logs, EngineALogEntry, **kwargs)


def _build_engine_a_no_trade_output(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
    no_trade_reasons: list[NoTradeReason],
    *,
    reason_codes: tuple[str, ...] = (),
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
    return _build_engine_a_no_trade_output_impl(
        EngineAOutput,
        decision_no_trade=EngineADecision.NO_TRADE,
        inputs=inputs,
        logs=logs,
        no_trade_reasons=no_trade_reasons,
        reason_codes=reason_codes,
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


def _early_exit_no_trade(
    inputs: EngineAInput,
    logs: list[EngineALogEntry],
    no_trade_reasons: list[NoTradeReason],
    *,
    reason: NoTradeReason,
    reason_codes: tuple[str, ...] = (),
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
    return _early_exit_no_trade_impl(
        EngineAOutput,
        EngineALogEntry,
        decision_no_trade=EngineADecision.NO_TRADE,
        inputs=inputs,
        logs=logs,
        no_trade_reasons=no_trade_reasons,
        reason=reason,
        reason_codes=reason_codes,
        log_reasons=log_reasons,
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
            realized_kernel_vol_scale=inputs.realized_kernel_vol_scale,
        )
    )
    _append_engine_a_log(
        logs,
        event="engine_a_structure_evaluated",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=structure.structure_score,
        block_scores=structure.block_scores,
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
            kyle_lambda_cost_uplift=inputs.kyle_lambda_cost_uplift,
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
        reasons=build_engine_a_cost_log_reasons(
            reason_codes=cost.reason_codes,
            reason=cost.reason,
            kyle_lambda_cost_uplift=cost.kyle_lambda_cost_uplift,
        ),
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
            ofi_flow_score=inputs.ofi_flow_score,
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
        realized_vol_current=inputs.realized_vol_current,
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
    reason_codes = build_engine_a_emit_reason_codes(
        structure_verdict=structure.verdict.value,
        context_verdict=context.verdict.value,
        cost_verdict=cost.verdict.value,
        conviction=conviction.conviction.value,
    )
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
        reasons=reason_codes,
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
        reason_codes=reason_codes,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )
def run_engine_a(inputs: EngineAInput) -> EngineAOutput:
    """Execute the full Engine A pipeline and produce canonical output."""

    logs: list[EngineALogEntry] = []
    no_trade_reasons: list[NoTradeReason] = []
    def _guard_exit(
        reason: NoTradeReason,
        gate_reason_code: str,
        detail_code: str,
        detail: str,
    ) -> EngineAOutput:
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=reason,
            reason_codes=build_engine_a_gate_reason_codes(
                gate_reason_codes=(gate_reason_code,),
                detailed_reason_codes=(detail_code,),
            ),
            log_reasons=build_engine_a_guard_log_reasons(detail_code, detail),
        )

    def _semantic_exit(
        reason: NoTradeReason,
        gate_reason_code: str,
        detailed_reason_codes: tuple[str, ...],
        *,
        detail: str | None = None,
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
        reason_codes = build_engine_a_gate_reason_codes(
            gate_reason_codes=(gate_reason_code,),
            detailed_reason_codes=detailed_reason_codes,
        )
        return _early_exit_no_trade(
            inputs,
            logs,
            no_trade_reasons,
            reason=reason,
            reason_codes=reason_codes,
            log_reasons=build_engine_a_branch_log_reasons(reason_codes, detail) if detail is not None else None,
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

    if inputs.direction_score <= 0:
        return _guard_exit(
            NoTradeReason.NON_LONG_DIRECTION,
            "engine_internal.engine_a.direction.non_long",
            "engine_a.input.non_long_direction",
            f"direction_score={inputs.direction_score:.3f} <= 0 - long-only",
        )
    if inputs.candidate_size <= 0:
        return _guard_exit(
            NoTradeReason.INVALID_CANDIDATE_SIZE,
            "hard_block.engine_a.input.invalid_candidate_size",
            "engine_a.input.invalid_candidate_size",
            f"candidate_size={inputs.candidate_size:.6f} <= 0",
        )
    if inputs.holding_period <= 0:
        return _guard_exit(
            NoTradeReason.INVALID_HOLDING_PERIOD,
            "hard_block.engine_a.input.invalid_holding_period",
            "engine_a.input.invalid_holding_period",
            f"holding_period={inputs.holding_period:.6f} <= 0",
        )
    if inputs.entry_price <= 0:
        return _guard_exit(
            NoTradeReason.INVALID_ENTRY_PRICE,
            "hard_block.engine_a.input.invalid_entry_price",
            "engine_a.input.invalid_entry_price",
            f"entry_price={inputs.entry_price:.6f} <= 0",
        )
    if inputs.atr < 0:
        return _guard_exit(
            NoTradeReason.INVALID_ATR,
            "hard_block.engine_a.input.invalid_atr",
            "engine_a.input.invalid_atr",
            f"atr={inputs.atr:.6f} < 0",
        )

    structure = _evaluate_structure_stage(inputs, logs)
    if structure.verdict == StructureVerdict.UNFAVORABLE:
        return _semantic_exit(
            NoTradeReason.STRUCTURE_UNFAVORABLE,
            "engine_internal.engine_a.structure.unfavorable",
            ("engine_a.structure.unfavorable",),
            detail=structure.reason,
            structure_verdict=structure.verdict,
        )

    context = _evaluate_context_stage(inputs, logs)
    if context.verdict == ContextVerdict.FATAL:
        return _semantic_exit(
            NoTradeReason.CONTEXT_FATAL,
            "engine_internal.engine_a.context.fatal",
            ("engine_a.context.fatal",),
            detail=context.reason,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
        )

    cost = _evaluate_cost_stage(inputs, logs)
    if cost.verdict == CostVerdict.INFEASIBLE:
        return _semantic_exit(
            NoTradeReason.COST_INFEASIBLE,
            "economics.engine_a.cost.infeasible",
            ("engine_a.cost.infeasible", *cost.reason_codes),
            detail=cost.reason,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            cost_verdict=cost.verdict,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
        )
    if not cost.is_emittable:
        return _semantic_exit(
            NoTradeReason.COST_MARGINAL,
            "economics.engine_a.cost.marginal",
            ("engine_a.cost.marginal", *cost.reason_codes),
            detail=cost.reason,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            cost_verdict=cost.verdict,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
        )

    conviction = _evaluate_conviction_stage(inputs, structure, context, logs)
    if conviction.conviction == ConvictionLevel.NONE:
        return _semantic_exit(
            NoTradeReason.CONVICTION_NONE,
            "scoring.engine_a.conviction.none",
            ("engine_a.conviction.none",),
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
    if not conviction.is_emittable:
        return _semantic_exit(
            NoTradeReason.LOW_CONVICTION,
            "scoring.engine_a.conviction.low_non_emittable",
            ("engine_a.conviction.low_non_emittable",),
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

    try:
        invalidation = _evaluate_invalidation_stage(inputs, logs)
    except ValueError as exc:
        return _semantic_exit(
            NoTradeReason.INVALID_INVALIDATION,
            "hard_block.engine_a.invalidation.invalid_contract",
            ("engine_a.invalidation.invalid_contract",),
            detail=str(exc),
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
