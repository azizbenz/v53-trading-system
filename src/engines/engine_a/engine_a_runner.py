"""
Build-6 / engine_a / engine_a_runner
Canonical orchestrator for Engine A — assembles all sub-components
into a single auditable output.

This is the single entry point for Engine A evaluation.
Produces EngineAOutput: a complete, audit-ready object consumed
by scoring_backbone, portfolio, and meta modules.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from data_backbone import resolve_delta_confirmation
from engines.engine_a.structure_detector_a import (
    StructureInput,
    StructureVerdict,
    detect_structure,
)
from engines.engine_a.context_validator_a import (
    ContextInput,
    ContextVerdict,
    validate_context,
)
from engines.engine_a.cost_feasibility_a import (
    CostInput,
    CostVerdict,
    check_cost_feasibility,
)
from engines.engine_a.conviction_builder_a import (
    ConvictionInput,
    ConvictionLevel,
    ENGINE_A_CONVICTION_CALIBRATION_STATUS,
    ENGINE_A_CONVICTION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TierSuggestion,
    build_conviction,
)
from engines.engine_a.invalidation_mapper_a import (
    InvalidationMap,
    build_invalidation,
)
from engines.engine_a.signal_reporter_a import (
    SignalDecision,
    NoTradeReason,
)


class EngineADecision(StrEnum):
    """Engine A final decision."""
    EMIT = "emit"
    NO_TRADE = "no_trade"


class EngineALogEntry(BaseModel, frozen=True):
    """Structured log entry for Engine A — spec section 19."""
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
    """Complete canonical Engine A output — consumed by scoring/portfolio/meta.

    This is the audit-ready object produced by the runner.
    Every field is explicit and typed for downstream consumption.
    """
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
    # Structure inputs
    pair: str
    direction_score: float
    continuation_score: float
    structure_quality: float
    zone_proximity: float
    trend_stability: float
    # Context inputs
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
    # Cost inputs
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 4.0
    delta_safe: float = 0.0005
    ce_min: float = 0.0001
    # Invalidation inputs
    entry_price: float = 0.0
    atr: float = 0.0
    # Meta
    scoring_version: str = ""


ENGINE_A_RUNNER_INPUT_DEFAULTS: dict[str, float | str | None] = {
    "regime": "",
    "regime_favorability": 0.5,
    "regime_confidence": 0.5,
    "pair_health": 0.5,
    "data_freshness": 0.5,
    "flow_coherence": 0.5,
    "flow_score": 0.0,
    "cost_preference_score": 0.0,
    "delta_confirmation": None,
    "delta_proxy_soft_value": None,
    "delta_proxy_sign_value": None,
    "delta_proxy_reference_volume": None,
    "execution_fragility": 0.0,
    "market_toxicity": 0.0,
    "spread_regime_penalty": 0.0,
    "competition_density": 0.5,
    "expected_gain": 0.0,
    "expected_cost": 0.0,
    "candidate_size": 0.0,
    "holding_period": 4.0,
    "delta_safe": 0.0005,
    "ce_min": 0.0001,
    "entry_price": 0.0,
    "atr": 0.0,
    "scoring_version": "",
}

EngineAInput.model_fields["regime"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["regime"]
EngineAInput.model_fields["regime_favorability"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["regime_favorability"]
EngineAInput.model_fields["regime_confidence"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["regime_confidence"]
EngineAInput.model_fields["pair_health"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["pair_health"]
EngineAInput.model_fields["data_freshness"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["data_freshness"]
EngineAInput.model_fields["flow_coherence"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["flow_coherence"]
EngineAInput.model_fields["flow_score"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["flow_score"]
EngineAInput.model_fields["cost_preference_score"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["cost_preference_score"]
EngineAInput.model_fields["delta_confirmation"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["delta_confirmation"]
EngineAInput.model_fields["delta_proxy_soft_value"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["delta_proxy_soft_value"]
EngineAInput.model_fields["delta_proxy_sign_value"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["delta_proxy_sign_value"]
EngineAInput.model_fields["delta_proxy_reference_volume"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["delta_proxy_reference_volume"]
EngineAInput.model_fields["execution_fragility"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["execution_fragility"]
EngineAInput.model_fields["market_toxicity"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["market_toxicity"]
EngineAInput.model_fields["spread_regime_penalty"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["spread_regime_penalty"]
EngineAInput.model_fields["competition_density"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["competition_density"]
EngineAInput.model_fields["expected_gain"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["expected_gain"]
EngineAInput.model_fields["expected_cost"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["expected_cost"]
EngineAInput.model_fields["candidate_size"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["candidate_size"]
EngineAInput.model_fields["holding_period"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["holding_period"]
EngineAInput.model_fields["delta_safe"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["delta_safe"]
EngineAInput.model_fields["ce_min"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["ce_min"]
EngineAInput.model_fields["entry_price"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["entry_price"]
EngineAInput.model_fields["atr"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["atr"]
EngineAInput.model_fields["scoring_version"].default = ENGINE_A_RUNNER_INPUT_DEFAULTS["scoring_version"]


def run_engine_a(inputs: EngineAInput) -> EngineAOutput:
    """Execute the full Engine A pipeline and produce canonical output.

    Pipeline:
    1. Structure detection
    2. Context validation (skip if structure unfavorable)
    3. Cost feasibility (skip if context fatal)
    4. Conviction building (skip if cost infeasible)
    5. Invalidation mapping (only if emitting)
    6. Assemble canonical output + structured logs
    """
    logs: list[EngineALogEntry] = []
    no_trade_reasons: list[NoTradeReason] = []

    # ── 0. Long-only guard (spot-halal profile) ──
    if inputs.direction_score <= 0:
        no_trade_reasons.append(NoTradeReason.NON_LONG_DIRECTION)
        logs.append(EngineALogEntry(
            event="engine_a_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            reasons=(f"direction_score={inputs.direction_score:.3f} <= 0 — long-only",),
        ))
        return EngineAOutput(
            pair=inputs.pair,
            decision=EngineADecision.NO_TRADE,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 1. Structure detection ──
    structure = detect_structure(StructureInput(
        pair=inputs.pair,
        direction_score=inputs.direction_score,
        continuation_score=inputs.continuation_score,
        structure_quality=inputs.structure_quality,
        zone_proximity=inputs.zone_proximity,
        trend_stability=inputs.trend_stability,
    ))
    logs.append(EngineALogEntry(
        event="engine_a_structure_evaluated",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=structure.structure_score,
        reasons=(structure.reason,) if structure.reason else (),
    ))

    if structure.verdict == StructureVerdict.UNFAVORABLE:
        no_trade_reasons.append(NoTradeReason.STRUCTURE_UNFAVORABLE)
        logs.append(EngineALogEntry(
            event="engine_a_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineAOutput(
            pair=inputs.pair,
            decision=EngineADecision.NO_TRADE,
            structure_verdict=structure.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 2. Context validation ──
    context = validate_context(ContextInput(
        pair=inputs.pair,
        regime_favorability=inputs.regime_favorability,
        regime_confidence=inputs.regime_confidence,
        pair_health=inputs.pair_health,
        data_freshness=inputs.data_freshness,
        flow_coherence=inputs.flow_coherence,
    ))
    logs.append(EngineALogEntry(
        event="engine_a_context_evaluated",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=context.context_score,
        reasons=(context.reason,) if context.reason else (),
    ))

    if context.verdict == ContextVerdict.FATAL:
        no_trade_reasons.append(NoTradeReason.CONTEXT_FATAL)
        logs.append(EngineALogEntry(
            event="engine_a_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineAOutput(
            pair=inputs.pair,
            decision=EngineADecision.NO_TRADE,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 3. Cost feasibility ──
    cost = check_cost_feasibility(CostInput(
        pair=inputs.pair,
        expected_gain=inputs.expected_gain,
        expected_cost=inputs.expected_cost,
        candidate_size=inputs.candidate_size,
        holding_period=inputs.holding_period,
        delta_safe=inputs.delta_safe,
        ce_min=inputs.ce_min,
    ))
    logs.append(EngineALogEntry(
        event="engine_a_cost_checked",
        pair=inputs.pair,
        regime=inputs.regime,
        expected_cost=cost.expected_cost,
        ce_expected=cost.ce_expected,
        ev_net=cost.ev_net,
        reasons=(cost.reason,) if cost.reason else (),
    ))

    if cost.verdict == CostVerdict.INFEASIBLE:
        no_trade_reasons.append(NoTradeReason.COST_INFEASIBLE)
        logs.append(EngineALogEntry(
            event="engine_a_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineAOutput(
            pair=inputs.pair,
            decision=EngineADecision.NO_TRADE,
            structure_verdict=structure.verdict,
            context_verdict=context.verdict,
            cost_verdict=cost.verdict,
            expected_cost=cost.expected_cost,
            ce_expected=cost.ce_expected,
            ev_net=cost.ev_net,
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 4. Conviction building ──
    delta_confirmation = resolve_delta_confirmation(
        delta_confirmation=inputs.delta_confirmation,
        delta_proxy_soft_value=inputs.delta_proxy_soft_value,
        delta_proxy_sign_value=inputs.delta_proxy_sign_value,
        reference_volume=inputs.delta_proxy_reference_volume,
    )
    conviction = build_conviction(ConvictionInput(
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
    ))
    logs.append(EngineALogEntry(
        event="engine_a_conviction_built",
        pair=inputs.pair,
        regime=inputs.regime,
        raw_score=conviction.raw_score,
        penalized_score=conviction.raw_score,
        block_scores=conviction.block_scores,
        conviction=conviction.conviction.value,
        tier=conviction.tier_suggestion.value,
    ))

    if conviction.conviction == ConvictionLevel.NONE:
        no_trade_reasons.append(NoTradeReason.CONVICTION_NONE)
        logs.append(EngineALogEntry(
            event="engine_a_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            reasons=tuple(str(r) for r in no_trade_reasons),
        ))
        return EngineAOutput(
            pair=inputs.pair,
            decision=EngineADecision.NO_TRADE,
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
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    # ── 5. Invalidation mapping ──
    inv = build_invalidation(
        pair=inputs.pair,
        direction_score=inputs.direction_score,
        entry_price=inputs.entry_price,
        atr=inputs.atr,
        holding_hours=inputs.holding_period,
    )
    logs.append(EngineALogEntry(
        event="engine_a_invalidation_built",
        pair=inputs.pair,
        regime=inputs.regime,
        invalidation=inv.primary_invalidation,
        holding_hours=inv.expected_holding_hours,
    ))

    # ── 6. EMIT ──
    logs.append(EngineALogEntry(
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
        invalidation=inv.primary_invalidation,
        holding_hours=inv.expected_holding_hours,
        scoring_version=inputs.scoring_version,
    ))

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
        invalidation=inv,
        holding_hours=inv.expected_holding_hours,
        structure_verdict=structure.verdict,
        context_verdict=context.verdict,
        cost_verdict=cost.verdict,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )
