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
    delta_confirmation: float = 0.5
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
    conviction = build_conviction(ConvictionInput(
        pair=inputs.pair,
        structure_score=structure.structure_score,
        context_score=context.context_score,
        flow_score=inputs.flow_score,
        cost_preference_score=inputs.cost_preference_score,
        delta_confirmation=inputs.delta_confirmation,
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
