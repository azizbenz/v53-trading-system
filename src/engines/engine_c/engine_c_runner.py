"""Canonical Engine C runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .conviction_builder_c import build_conviction_c
from .cost_feasibility_c import evaluate_cost_feasibility_c
from .invalidation_mapper_c import build_invalidation_levels_c
from .output_payload_builder_c import build_engine_c_output_payload
from .signal_math_c import (
    compute_breakout_score,
    compute_context_score,
    compute_continuation_score,
    compute_fake_breakout_risk,
)
from .structure_resolver_c import build_engine_c_log_context, resolve_engine_c_structure


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class EngineCDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonC(StrEnum):
    NON_LONG_BREAKOUT = "non_long_breakout"
    BREAKOUT_UNSTRUCTURED = "breakout_unstructured"
    CONTINUATION_NOT_VIABLE = "continuation_not_viable"
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

    if inputs.breakout_strength <= 0:
        no_trade_reasons.append(NoTradeReasonC.NON_LONG_BREAKOUT)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_c_log_context(structure),
                reasons=(f"breakout_strength={inputs.breakout_strength:.3f} <= 0",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            **build_engine_c_output_payload(
                structure=structure,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    breakout_score = compute_breakout_score(inputs)
    logs.append(
        EngineCLogEntry(
            event="engine_c_breakout_evaluated",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            breakout_score=breakout_score,
            raw_score=breakout_score,
        )
    )
    if breakout_score < 0.62 or inputs.breakout_strength < 0.55 or inputs.range_quality < 0.50:
        no_trade_reasons.append(NoTradeReasonC.BREAKOUT_UNSTRUCTURED)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_c_log_context(structure),
                breakout_score=breakout_score,
                reasons=("breakout structure insufficient",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            **build_engine_c_output_payload(
                structure=structure,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                breakout_score=breakout_score,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    context_score = compute_context_score(inputs)
    continuation_score = compute_continuation_score(inputs, context_score=context_score)
    logs.append(
        EngineCLogEntry(
            event="engine_c_continuation_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            raw_score=continuation_score,
        )
    )
    if continuation_score < 0.58 or inputs.extension_pct > 0.72:
        no_trade_reasons.append(NoTradeReasonC.CONTINUATION_NOT_VIABLE)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_c_log_context(structure),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                reasons=("continuation already too mature or too weak",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            **build_engine_c_output_payload(
                structure=structure,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    fake_breakout_risk = compute_fake_breakout_risk(inputs)
    penalized_score = max(0.0, breakout_score - max(0.0, fake_breakout_risk - 0.35))
    logs.append(
        EngineCLogEntry(
            event="engine_c_fake_breakout_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            raw_score=breakout_score,
            penalized_score=penalized_score,
        )
    )
    if fake_breakout_risk >= 0.65:
        no_trade_reasons.append(NoTradeReasonC.FAKE_BREAKOUT_BLOCKED)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_c_log_context(structure),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                fake_breakout_risk=fake_breakout_risk,
                reasons=("fake breakout risk too high",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            **build_engine_c_output_payload(
                structure=structure,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                fake_breakout_risk=fake_breakout_risk,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    cost_metrics = evaluate_cost_feasibility_c(
        expected_gain=inputs.expected_gain,
        expected_cost=inputs.expected_cost,
        candidate_size=inputs.candidate_size,
        holding_period=inputs.holding_period,
        delta_safe=inputs.delta_safe,
        ce_min=inputs.ce_min,
    )
    logs.append(
        EngineCLogEntry(
            event="engine_c_cost_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
        )
    )
    if not cost_metrics.is_feasible:
        no_trade_reasons.append(NoTradeReasonC.COST_INFEASIBLE)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_c_log_context(structure),
                expected_cost=cost_metrics.expected_cost,
                ce_expected=cost_metrics.ce_expected,
                ev_net=cost_metrics.ev_net,
                reasons=("breakout edge does not survive costs",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            **build_engine_c_output_payload(
                structure=structure,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                fake_breakout_risk=fake_breakout_risk,
                expected_cost=cost_metrics.expected_cost,
                ce_expected=cost_metrics.ce_expected,
                ev_net=cost_metrics.ev_net,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

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

    invalidation_levels = build_invalidation_levels_c(
        entry_price=inputs.entry_price,
        breakout_level=inputs.breakout_level,
        atr=inputs.atr,
        expected_gain=inputs.expected_gain,
    )
    invalidation = EngineCInvalidation(
        stop_price=invalidation_levels.stop_price,
        target_price=invalidation_levels.target_price,
        risk_multiple=invalidation_levels.risk_multiple,
    )
    block_scores = {
        "breakout": breakout_score,
        "continuation": continuation_score,
        "context": context_score,
        "cost_preference": cost_metrics.cost_preference_score,
    }
    logs.append(
        EngineCLogEntry(
            event="engine_c_emit",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            conviction=conviction.value,
            tier=tier.value,
            holding_hours=inputs.holding_period,
            scoring_version=inputs.scoring_version,
        )
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
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            invalidation=invalidation,
            holding_hours=inputs.holding_period,
        ),
    )
