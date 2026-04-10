"""Canonical Engine D runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .context_resolver_d import build_engine_d_log_context, resolve_engine_d_context
from .conviction_builder_d import build_conviction_d
from .cost_feasibility_d import evaluate_cost_feasibility_d
from .invalidation_mapper_d import build_invalidation_levels_d
from .output_payload_builder_d import build_engine_d_output_payload
from .signal_math_d import (
    compute_context_score,
    compute_history_score,
    compute_marginal_value_score,
    compute_reformation_score,
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class EngineDDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonD(StrEnum):
    HISTORY_WEAK = "history_weak"
    REFORMATION_WEAK = "reformation_weak"
    MARGINAL_EDGE_TOO_LOW = "marginal_edge_too_low"
    CONCENTRATION_BLOCKED = "concentration_blocked"
    COST_INFEASIBLE = "cost_infeasible"


class ConvictionLevelD(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TierSuggestionD(StrEnum):
    NO_TRADE = "no_trade"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"


class EngineDInvalidation(BaseModel, frozen=True):
    stop_price: float = Field(..., gt=0.0)
    target_price: float = Field(..., gt=0.0)
    risk_multiple: float = Field(..., gt=0.0)


class EngineDLogEntry(BaseModel, frozen=True):
    event: str
    pair: str
    regime: str = ""
    origin_context_id: str = ""
    origin_trade_id: str = ""
    link_type: str = ""
    structure_reformed_detected: bool = False
    raw_score: float = 0.0
    penalized_score: float = 0.0
    history_score: float = 0.0
    reformation_score: float = 0.0
    marginal_value_score: float = 0.0
    concentration_risk: float = 0.0
    marginal_concentration: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    duplication_possible_with_engine_a: bool = False
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    conviction: str = ""
    tier: str = ""
    holding_hours: float = 0.0
    reasons: tuple[str, ...] = ()
    scoring_version: str = ""


class EngineDOutput(BaseModel, frozen=True):
    pair: str
    engine_id: str = "engine_d"
    decision: EngineDDecision
    raw_score: float = 0.0
    penalized_score: float = 0.0
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelD = ConvictionLevelD.NONE
    tier_suggestion: TierSuggestionD = TierSuggestionD.NO_TRADE
    origin_context_id: str = ""
    origin_trade_id: str = ""
    link_type: str = ""
    structure_reformed_detected: bool = False
    history_score: float = 0.0
    reformation_score: float = 0.0
    marginal_value_score: float = 0.0
    concentration_risk: float = 0.0
    marginal_concentration: float = 0.0
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    ev_net: float = 0.0
    duplication_possible_with_engine_a: bool = False
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    invalidation: EngineDInvalidation | None = None
    holding_hours: float = 0.0
    scoring_version: str = ""
    no_trade_reasons: tuple[NoTradeReasonD, ...] = ()
    log_entries: tuple[EngineDLogEntry, ...] = ()


class EngineDInput(BaseModel, frozen=True):
    pair: str
    origin_context_id: str = ""
    origin_trade_id: str = ""
    link_type: str = "prior_trade"
    prior_trade_quality: float
    reformation_quality: float
    pullback_quality: float
    continuation_room: float
    concentration_headroom: float
    marginal_edge: float
    reentry_lateness: float
    structure_reformed_detected: bool = True
    regime: str = ""
    regime_favorability: float = 0.5
    pair_health: float = 0.5
    data_freshness: float = 0.5
    flow_coherence: float = 0.5
    expected_gain: float = 0.0
    expected_cost: float = 0.0
    candidate_size: float = 0.0
    holding_period: float = 2.0
    ce_min: float = 0.00012
    delta_safe: float = 0.0005
    entry_price: float = 0.0
    reentry_anchor_price: float = 0.0
    atr: float = 0.0
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    scoring_version: str = ""


def run_engine_d(inputs: EngineDInput) -> EngineDOutput:
    logs: list[EngineDLogEntry] = []
    no_trade_reasons: list[NoTradeReasonD] = []
    context = resolve_engine_d_context(inputs)

    # BS-104 guard: entry_price=0 would cause Pydantic ValidationError
    # when building EngineDInvalidation(stop_price=..., gt=0.0)
    if inputs.entry_price <= 0.0:
        no_trade_reasons.append(NoTradeReasonD.COST_INFEASIBLE)
        logs.append(EngineDLogEntry(
            event="engine_d_no_trade",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            reasons=("entry_price must be positive for re-entry invalidation",),
        ))
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    history_score = compute_history_score(inputs)
    logs.append(
        EngineDLogEntry(
            event="engine_d_history_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            history_score=history_score,
            raw_score=history_score,
        )
    )
    if history_score < 0.55:
        no_trade_reasons.append(NoTradeReasonD.HISTORY_WEAK)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_d_log_context(context),
                history_score=history_score,
                reasons=("prior context too weak for re-entry",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                history_score=history_score,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    context_score = compute_context_score(inputs)
    reformation_score = compute_reformation_score(inputs, context_score=context_score)
    logs.append(
        EngineDLogEntry(
            event="engine_d_reformation_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            history_score=history_score,
            reformation_score=reformation_score,
            raw_score=reformation_score,
        )
    )
    if reformation_score < 0.58:
        no_trade_reasons.append(NoTradeReasonD.REFORMATION_WEAK)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_d_log_context(context),
                history_score=history_score,
                reformation_score=reformation_score,
                reasons=("reformation too weak for second chance entry",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                history_score=history_score,
                reformation_score=reformation_score,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    marginal_value_score = compute_marginal_value_score(inputs)
    concentration_risk = context["marginal_concentration"]
    penalized_score = max(0.0, marginal_value_score - max(0.0, concentration_risk - 0.30))
    logs.append(
        EngineDLogEntry(
            event="engine_d_marginal_value_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            raw_score=marginal_value_score,
            penalized_score=penalized_score,
        )
    )
    if marginal_value_score < 0.56:
        no_trade_reasons.append(NoTradeReasonD.MARGINAL_EDGE_TOO_LOW)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_d_log_context(context),
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                reasons=("re-entry adds insufficient marginal value",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                history_score=history_score,
                reformation_score=reformation_score,
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )
    if concentration_risk >= 0.64:
        no_trade_reasons.append(NoTradeReasonD.CONCENTRATION_BLOCKED)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_d_log_context(context),
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                reasons=("concentration or lateness risk too high",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                history_score=history_score,
                reformation_score=reformation_score,
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    cost_metrics = evaluate_cost_feasibility_d(
        expected_gain=inputs.expected_gain,
        expected_cost=inputs.expected_cost,
        candidate_size=inputs.candidate_size,
        holding_period=inputs.holding_period,
        delta_safe=inputs.delta_safe,
        ce_min=inputs.ce_min,
    )
    logs.append(
        EngineDLogEntry(
            event="engine_d_cost_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
        )
    )
    if not cost_metrics.is_feasible:
        no_trade_reasons.append(NoTradeReasonD.COST_INFEASIBLE)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **build_engine_d_log_context(context),
                expected_cost=cost_metrics.expected_cost,
                ce_expected=cost_metrics.ce_expected,
                ev_net=cost_metrics.ev_net,
                reasons=("re-entry edge does not survive costs",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            **build_engine_d_output_payload(
                context=context,
                scoring_version=inputs.scoring_version,
                log_entries=tuple(logs),
                history_score=history_score,
                reformation_score=reformation_score,
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                expected_cost=cost_metrics.expected_cost,
                ce_expected=cost_metrics.ce_expected,
                ev_net=cost_metrics.ev_net,
                no_trade_reasons=tuple(no_trade_reasons),
            ),
        )

    conviction_result = build_conviction_d(
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        ce_expected=cost_metrics.ce_expected,
        ce_min=inputs.ce_min,
        concentration_risk=concentration_risk,
    )
    conviction = ConvictionLevelD(conviction_result.conviction_name)
    tier = TierSuggestionD(conviction_result.tier_name)

    invalidation_levels = build_invalidation_levels_d(
        entry_price=inputs.entry_price,
        reentry_anchor_price=inputs.reentry_anchor_price,
        atr=inputs.atr,
        expected_gain=inputs.expected_gain,
    )
    invalidation = EngineDInvalidation(
        stop_price=invalidation_levels.stop_price,
        target_price=invalidation_levels.target_price,
        risk_multiple=invalidation_levels.risk_multiple,
    )
    block_scores = {
        "history": history_score,
        "reformation": reformation_score,
        "marginal_value": marginal_value_score,
        "cost_preference": cost_metrics.cost_preference_score,
    }
    logs.append(
        EngineDLogEntry(
            event="engine_d_emit",
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            conviction=conviction.value,
            tier=tier.value,
            holding_hours=inputs.holding_period,
            scoring_version=inputs.scoring_version,
        )
    )
    return EngineDOutput(
        pair=inputs.pair,
        decision=EngineDDecision.EMIT,
        **build_engine_d_output_payload(
            context=context,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            block_scores=block_scores,
            conviction=conviction,
            tier_suggestion=tier,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            invalidation=invalidation,
            holding_hours=inputs.holding_period,
        ),
    )
