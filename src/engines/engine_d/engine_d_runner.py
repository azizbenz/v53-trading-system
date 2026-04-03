"""Canonical Engine D runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


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


def _resolve_engine_d_context(inputs: EngineDInput) -> dict[str, float | str | bool]:
    link_type = inputs.link_type.strip() or ("prior_trade" if inputs.origin_trade_id else "prior_context")
    duplication_overlap_with_engine_a = _clamp(inputs.duplication_overlap_with_engine_a)
    covered_share_by_engine_a = _clamp(
        inputs.covered_share_by_engine_a
        if inputs.covered_share_by_engine_a > 0.0
        else duplication_overlap_with_engine_a
    )
    duplication_possible_with_engine_a = (
        duplication_overlap_with_engine_a >= 0.65 or covered_share_by_engine_a >= 0.55
    )
    marginal_portfolio_gain = (
        inputs.marginal_portfolio_gain
        if inputs.marginal_portfolio_gain > 0.0
        else max(0.0, inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost))
    )
    concentration_risk = _clamp(0.60 * (1.0 - inputs.concentration_headroom) + 0.40 * inputs.reentry_lateness)
    return {
        "origin_context_id": inputs.origin_context_id or f"{inputs.pair}:prior_context",
        "origin_trade_id": inputs.origin_trade_id,
        "link_type": link_type,
        "structure_reformed_detected": inputs.structure_reformed_detected,
        "duplication_possible_with_engine_a": duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": duplication_overlap_with_engine_a,
        "marginal_portfolio_gain": marginal_portfolio_gain,
        "covered_share_by_engine_a": covered_share_by_engine_a,
        "marginal_concentration": concentration_risk,
    }


def _engine_d_log_context(context: dict[str, float | str | bool]) -> dict[str, float | str | bool]:
    return {
        "origin_context_id": context["origin_context_id"],
        "origin_trade_id": context["origin_trade_id"],
        "link_type": context["link_type"],
        "structure_reformed_detected": context["structure_reformed_detected"],
        "duplication_possible_with_engine_a": context["duplication_possible_with_engine_a"],
        "duplication_overlap_with_engine_a": context["duplication_overlap_with_engine_a"],
        "marginal_portfolio_gain": context["marginal_portfolio_gain"],
        "covered_share_by_engine_a": context["covered_share_by_engine_a"],
        "marginal_concentration": context["marginal_concentration"],
    }


def run_engine_d(inputs: EngineDInput) -> EngineDOutput:
    logs: list[EngineDLogEntry] = []
    no_trade_reasons: list[NoTradeReasonD] = []
    context = _resolve_engine_d_context(inputs)

    history_score = _clamp(
        0.55 * inputs.prior_trade_quality + 0.25 * inputs.pair_health + 0.20 * inputs.data_freshness
    )
    logs.append(
        EngineDLogEntry(
            event="engine_d_history_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_d_log_context(context),
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
                **_engine_d_log_context(context),
                history_score=history_score,
                reasons=("prior context too weak for re-entry",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            origin_context_id=context["origin_context_id"],
            origin_trade_id=context["origin_trade_id"],
            link_type=context["link_type"],
            structure_reformed_detected=context["structure_reformed_detected"],
            history_score=history_score,
            marginal_concentration=context["marginal_concentration"],
            duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=context["marginal_portfolio_gain"],
            covered_share_by_engine_a=context["covered_share_by_engine_a"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    context_score = _clamp(
        0.35 * inputs.regime_favorability
        + 0.25 * inputs.pair_health
        + 0.20 * inputs.data_freshness
        + 0.20 * inputs.flow_coherence
    )
    reformation_score = _clamp(
        0.45 * inputs.reformation_quality + 0.30 * inputs.pullback_quality + 0.25 * context_score
    )
    logs.append(
        EngineDLogEntry(
            event="engine_d_reformation_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_d_log_context(context),
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
                **_engine_d_log_context(context),
                history_score=history_score,
                reformation_score=reformation_score,
                reasons=("reformation too weak for second chance entry",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            origin_context_id=context["origin_context_id"],
            origin_trade_id=context["origin_trade_id"],
            link_type=context["link_type"],
            structure_reformed_detected=context["structure_reformed_detected"],
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_concentration=context["marginal_concentration"],
            duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=context["marginal_portfolio_gain"],
            covered_share_by_engine_a=context["covered_share_by_engine_a"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    marginal_value_score = _clamp(
        0.35 * inputs.marginal_edge
        + 0.30 * inputs.continuation_room
        + 0.20 * inputs.concentration_headroom
        + 0.15 * (1.0 - inputs.reentry_lateness)
    )
    concentration_risk = context["marginal_concentration"]
    penalized_score = max(0.0, marginal_value_score - max(0.0, concentration_risk - 0.30))
    logs.append(
        EngineDLogEntry(
            event="engine_d_marginal_value_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_d_log_context(context),
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
                **_engine_d_log_context(context),
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                reasons=("re-entry adds insufficient marginal value",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            origin_context_id=context["origin_context_id"],
            origin_trade_id=context["origin_trade_id"],
            link_type=context["link_type"],
            structure_reformed_detected=context["structure_reformed_detected"],
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            marginal_concentration=context["marginal_concentration"],
            duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=context["marginal_portfolio_gain"],
            covered_share_by_engine_a=context["covered_share_by_engine_a"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )
    if concentration_risk >= 0.64:
        no_trade_reasons.append(NoTradeReasonD.CONCENTRATION_BLOCKED)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **_engine_d_log_context(context),
                marginal_value_score=marginal_value_score,
                concentration_risk=concentration_risk,
                reasons=("concentration or lateness risk too high",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            origin_context_id=context["origin_context_id"],
            origin_trade_id=context["origin_trade_id"],
            link_type=context["link_type"],
            structure_reformed_detected=context["structure_reformed_detected"],
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            marginal_concentration=context["marginal_concentration"],
            duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=context["marginal_portfolio_gain"],
            covered_share_by_engine_a=context["covered_share_by_engine_a"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    ev_net = inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost)
    ce_expected = 0.0
    if inputs.holding_period > 0:
        ce_expected = (inputs.expected_gain - inputs.expected_cost) / inputs.holding_period
    logs.append(
        EngineDLogEntry(
            event="engine_d_cost_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_d_log_context(context),
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
        )
    )
    if inputs.expected_gain <= inputs.expected_cost + inputs.delta_safe or ce_expected < inputs.ce_min:
        no_trade_reasons.append(NoTradeReasonD.COST_INFEASIBLE)
        logs.append(
            EngineDLogEntry(
                event="engine_d_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **_engine_d_log_context(context),
                expected_cost=inputs.expected_cost,
                ce_expected=ce_expected,
                ev_net=ev_net,
                reasons=("re-entry edge does not survive costs",),
            )
        )
        return EngineDOutput(
            pair=inputs.pair,
            decision=EngineDDecision.NO_TRADE,
            origin_context_id=context["origin_context_id"],
            origin_trade_id=context["origin_trade_id"],
            link_type=context["link_type"],
            structure_reformed_detected=context["structure_reformed_detected"],
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            marginal_concentration=context["marginal_concentration"],
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=context["marginal_portfolio_gain"],
            covered_share_by_engine_a=context["covered_share_by_engine_a"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    raw_score = _clamp(
        0.30 * history_score
        + 0.30 * reformation_score
        + 0.25 * marginal_value_score
        + 0.15 * min(1.0, max(0.0, ce_expected / max(inputs.ce_min, 1e-6)))
    )
    conviction_score = max(0.0, raw_score - concentration_risk * 0.12)
    if conviction_score >= 0.80:
        conviction = ConvictionLevelD.HIGH
        tier = TierSuggestionD.TIER_2
    elif conviction_score >= 0.64:
        conviction = ConvictionLevelD.MEDIUM
        tier = TierSuggestionD.TIER_1
    else:
        conviction = ConvictionLevelD.LOW
        tier = TierSuggestionD.TIER_1

    stop_price = inputs.reentry_anchor_price - max(inputs.atr * 0.30, inputs.entry_price * 0.0035)
    if stop_price <= 0:
        stop_price = inputs.entry_price * 0.987
    target_price = inputs.entry_price + max(inputs.atr * 1.4, inputs.entry_price * max(inputs.expected_gain, 0.008))
    invalidation = EngineDInvalidation(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=(target_price - inputs.entry_price) / max(inputs.entry_price - stop_price, 1e-6),
    )
    block_scores = {
        "history": history_score,
        "reformation": reformation_score,
        "marginal_value": marginal_value_score,
        "cost_preference": _clamp((inputs.expected_gain - inputs.expected_cost) / max(inputs.expected_gain, inputs.delta_safe)),
    }
    logs.append(
        EngineDLogEntry(
            event="engine_d_emit",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_d_log_context(context),
            raw_score=raw_score,
            penalized_score=conviction_score,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction.value,
            tier=tier.value,
            holding_hours=inputs.holding_period,
            scoring_version=inputs.scoring_version,
        )
    )
    return EngineDOutput(
        pair=inputs.pair,
        decision=EngineDDecision.EMIT,
        raw_score=raw_score,
        penalized_score=conviction_score,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier,
        origin_context_id=context["origin_context_id"],
        origin_trade_id=context["origin_trade_id"],
        link_type=context["link_type"],
        structure_reformed_detected=context["structure_reformed_detected"],
        history_score=history_score,
        reformation_score=reformation_score,
        marginal_value_score=marginal_value_score,
        concentration_risk=concentration_risk,
        marginal_concentration=context["marginal_concentration"],
        expected_cost=inputs.expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        duplication_possible_with_engine_a=context["duplication_possible_with_engine_a"],
        duplication_overlap_with_engine_a=context["duplication_overlap_with_engine_a"],
        marginal_portfolio_gain=context["marginal_portfolio_gain"],
        covered_share_by_engine_a=context["covered_share_by_engine_a"],
        invalidation=invalidation,
        holding_hours=inputs.holding_period,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )
