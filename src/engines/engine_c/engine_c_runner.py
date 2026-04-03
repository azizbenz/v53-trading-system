"""Canonical Engine C runner."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


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


def _resolve_engine_c_structure(inputs: EngineCInput) -> dict[str, float | str | bool]:
    resolved_range_high = inputs.range_high if inputs.range_high > 0.0 else max(inputs.breakout_level, inputs.entry_price)
    if resolved_range_high <= 0.0:
        resolved_range_high = max(inputs.entry_price, 1.0)
    fallback_width = max(inputs.atr * 1.5, resolved_range_high * max(0.002, inputs.range_quality * 0.01))
    resolved_range_low = inputs.range_low if 0.0 < inputs.range_low < resolved_range_high else resolved_range_high - fallback_width
    resolved_range_low = max(0.0, resolved_range_low)
    range_width_pct = (resolved_range_high - resolved_range_low) / max(resolved_range_high, 1e-6)
    distance_to_breakout_pct = max(0.0, (inputs.entry_price - inputs.breakout_level) / max(inputs.breakout_level, 1e-6))
    if inputs.volume_confirmation >= 0.80 and inputs.compression_quality >= 0.75:
        breakout_type = "compression_release"
    elif inputs.range_quality >= 0.75:
        breakout_type = "range_expansion"
    else:
        breakout_type = "structured_breakout"
    if inputs.extension_pct <= 0.25:
        continuation_context = "fresh_breakout"
    elif inputs.extension_pct <= 0.55:
        continuation_context = "controlled_extension"
    else:
        continuation_context = "late_extension"
    duplication_overlap_with_engine_a = _clamp(inputs.engine_a_overlap_ratio)
    covered_share_by_engine_a = _clamp(
        inputs.covered_share_by_engine_a
        if inputs.covered_share_by_engine_a > 0.0
        else duplication_overlap_with_engine_a
    )
    duplication_possible_with_engine_a = (
        duplication_overlap_with_engine_a >= 0.65 or covered_share_by_engine_a >= 0.60
    )
    marginal_portfolio_gain = (
        inputs.marginal_portfolio_gain
        if inputs.marginal_portfolio_gain > 0.0
        else max(0.0, inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost))
    )
    keff_contribution = _clamp(
        inputs.keff_contribution
        if inputs.keff_contribution > 0.0
        else max(0.0, 1.0 - duplication_overlap_with_engine_a) * 0.5
    )
    return {
        "range_low": resolved_range_low,
        "range_high": resolved_range_high,
        "range_width_pct": range_width_pct,
        "breakout_type": breakout_type,
        "continuation_context": continuation_context,
        "distance_to_breakout_pct": distance_to_breakout_pct,
        "duplication_possible_with_engine_a": duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": duplication_overlap_with_engine_a,
        "marginal_portfolio_gain": marginal_portfolio_gain,
        "covered_share_by_engine_a": covered_share_by_engine_a,
        "keff_contribution": keff_contribution,
    }


def _engine_c_log_context(structure: dict[str, float | str | bool]) -> dict[str, float | str | bool]:
    return {
        "range_low": structure["range_low"],
        "range_high": structure["range_high"],
        "range_width_pct": structure["range_width_pct"],
        "breakout_type": structure["breakout_type"],
        "continuation_context": structure["continuation_context"],
        "distance_to_breakout_pct": structure["distance_to_breakout_pct"],
        "duplication_possible_with_engine_a": structure["duplication_possible_with_engine_a"],
        "duplication_overlap_with_engine_a": structure["duplication_overlap_with_engine_a"],
        "marginal_portfolio_gain": structure["marginal_portfolio_gain"],
        "covered_share_by_engine_a": structure["covered_share_by_engine_a"],
        "keff_contribution": structure["keff_contribution"],
    }


def run_engine_c(inputs: EngineCInput) -> EngineCOutput:
    logs: list[EngineCLogEntry] = []
    no_trade_reasons: list[NoTradeReasonC] = []
    structure = _resolve_engine_c_structure(inputs)

    if inputs.breakout_strength <= 0:
        no_trade_reasons.append(NoTradeReasonC.NON_LONG_BREAKOUT)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **_engine_c_log_context(structure),
                reasons=(f"breakout_strength={inputs.breakout_strength:.3f} <= 0",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            range_low=structure["range_low"],
            range_high=structure["range_high"],
            range_width_pct=structure["range_width_pct"],
            breakout_type=structure["breakout_type"],
            continuation_context=structure["continuation_context"],
            distance_to_breakout_pct=structure["distance_to_breakout_pct"],
            duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=structure["marginal_portfolio_gain"],
            covered_share_by_engine_a=structure["covered_share_by_engine_a"],
            keff_contribution=structure["keff_contribution"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    breakout_score = _clamp(
        0.35 * inputs.breakout_strength
        + 0.25 * inputs.range_quality
        + 0.20 * inputs.compression_quality
        + 0.20 * inputs.volume_confirmation
    )
    logs.append(
        EngineCLogEntry(
            event="engine_c_breakout_evaluated",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_c_log_context(structure),
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
                **_engine_c_log_context(structure),
                breakout_score=breakout_score,
                reasons=("breakout structure insufficient",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            range_low=structure["range_low"],
            range_high=structure["range_high"],
            range_width_pct=structure["range_width_pct"],
            breakout_type=structure["breakout_type"],
            continuation_context=structure["continuation_context"],
            distance_to_breakout_pct=structure["distance_to_breakout_pct"],
            breakout_score=breakout_score,
            duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=structure["marginal_portfolio_gain"],
            covered_share_by_engine_a=structure["covered_share_by_engine_a"],
            keff_contribution=structure["keff_contribution"],
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
    continuation_score = _clamp(
        0.45 * inputs.followthrough_room
        + 0.25 * (1.0 - inputs.extension_pct)
        + 0.30 * context_score
    )
    logs.append(
        EngineCLogEntry(
            event="engine_c_continuation_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_c_log_context(structure),
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
                **_engine_c_log_context(structure),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                reasons=("continuation already too mature or too weak",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            range_low=structure["range_low"],
            range_high=structure["range_high"],
            range_width_pct=structure["range_width_pct"],
            breakout_type=structure["breakout_type"],
            continuation_context=structure["continuation_context"],
            distance_to_breakout_pct=structure["distance_to_breakout_pct"],
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=structure["marginal_portfolio_gain"],
            covered_share_by_engine_a=structure["covered_share_by_engine_a"],
            keff_contribution=structure["keff_contribution"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    fake_breakout_risk = _clamp(
        0.45 * inputs.retrace_risk
        + 0.30 * inputs.rejection_wick_ratio
        + 0.25 * (1.0 - inputs.volume_confirmation)
    )
    penalized_score = max(0.0, breakout_score - max(0.0, fake_breakout_risk - 0.35))
    logs.append(
        EngineCLogEntry(
            event="engine_c_fake_breakout_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_c_log_context(structure),
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
                **_engine_c_log_context(structure),
                breakout_score=breakout_score,
                continuation_score=continuation_score,
                fake_breakout_risk=fake_breakout_risk,
                reasons=("fake breakout risk too high",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            range_low=structure["range_low"],
            range_high=structure["range_high"],
            range_width_pct=structure["range_width_pct"],
            breakout_type=structure["breakout_type"],
            continuation_context=structure["continuation_context"],
            distance_to_breakout_pct=structure["distance_to_breakout_pct"],
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=structure["marginal_portfolio_gain"],
            covered_share_by_engine_a=structure["covered_share_by_engine_a"],
            keff_contribution=structure["keff_contribution"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    ev_net = inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost)
    ce_expected = 0.0
    if inputs.holding_period > 0:
        ce_expected = (inputs.expected_gain - inputs.expected_cost) / inputs.holding_period
    logs.append(
        EngineCLogEntry(
            event="engine_c_cost_checked",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_c_log_context(structure),
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
        )
    )
    if inputs.expected_gain <= inputs.expected_cost + inputs.delta_safe or ce_expected < inputs.ce_min:
        no_trade_reasons.append(NoTradeReasonC.COST_INFEASIBLE)
        logs.append(
            EngineCLogEntry(
                event="engine_c_no_trade",
                pair=inputs.pair,
                regime=inputs.regime,
                **_engine_c_log_context(structure),
                expected_cost=inputs.expected_cost,
                ce_expected=ce_expected,
                ev_net=ev_net,
                reasons=("breakout edge does not survive costs",),
            )
        )
        return EngineCOutput(
            pair=inputs.pair,
            decision=EngineCDecision.NO_TRADE,
            range_low=structure["range_low"],
            range_high=structure["range_high"],
            range_width_pct=structure["range_width_pct"],
            breakout_type=structure["breakout_type"],
            continuation_context=structure["continuation_context"],
            distance_to_breakout_pct=structure["distance_to_breakout_pct"],
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
            duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
            marginal_portfolio_gain=structure["marginal_portfolio_gain"],
            covered_share_by_engine_a=structure["covered_share_by_engine_a"],
            keff_contribution=structure["keff_contribution"],
            no_trade_reasons=tuple(no_trade_reasons),
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
        )

    raw_score = _clamp(
        0.40 * breakout_score
        + 0.30 * continuation_score
        + 0.20 * context_score
        + 0.10 * min(1.0, max(0.0, ce_expected / max(inputs.ce_min, 1e-6)))
    )
    conviction_score = max(0.0, raw_score - fake_breakout_risk * 0.10)
    if conviction_score >= 0.82:
        conviction = ConvictionLevelC.HIGH
        tier = TierSuggestionC.TIER_2
    elif conviction_score >= 0.67:
        conviction = ConvictionLevelC.MEDIUM
        tier = TierSuggestionC.TIER_1
    else:
        conviction = ConvictionLevelC.LOW
        tier = TierSuggestionC.TIER_1

    stop_price = inputs.breakout_level - max(inputs.atr * 0.35, inputs.entry_price * 0.004)
    if stop_price <= 0:
        stop_price = inputs.entry_price * 0.985
    target_price = inputs.entry_price + max(inputs.atr * 1.8, inputs.entry_price * max(inputs.expected_gain, 0.01))
    invalidation = EngineCInvalidation(
        stop_price=stop_price,
        target_price=target_price,
        risk_multiple=(target_price - inputs.entry_price) / max(inputs.entry_price - stop_price, 1e-6),
    )
    block_scores = {
        "breakout": breakout_score,
        "continuation": continuation_score,
        "context": context_score,
        "cost_preference": _clamp((inputs.expected_gain - inputs.expected_cost) / max(inputs.expected_gain, inputs.delta_safe)),
    }
    logs.append(
        EngineCLogEntry(
            event="engine_c_emit",
            pair=inputs.pair,
            regime=inputs.regime,
            **_engine_c_log_context(structure),
            raw_score=raw_score,
            penalized_score=conviction_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=inputs.expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction.value,
            tier=tier.value,
            holding_hours=inputs.holding_period,
            scoring_version=inputs.scoring_version,
        )
    )
    return EngineCOutput(
        pair=inputs.pair,
        decision=EngineCDecision.EMIT,
        raw_score=raw_score,
        penalized_score=conviction_score,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier,
        range_low=structure["range_low"],
        range_high=structure["range_high"],
        range_width_pct=structure["range_width_pct"],
        breakout_type=structure["breakout_type"],
        continuation_context=structure["continuation_context"],
        distance_to_breakout_pct=structure["distance_to_breakout_pct"],
        breakout_score=breakout_score,
        continuation_score=continuation_score,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=inputs.expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        duplication_possible_with_engine_a=structure["duplication_possible_with_engine_a"],
        duplication_overlap_with_engine_a=structure["duplication_overlap_with_engine_a"],
        marginal_portfolio_gain=structure["marginal_portfolio_gain"],
        covered_share_by_engine_a=structure["covered_share_by_engine_a"],
        keff_contribution=structure["keff_contribution"],
        invalidation=invalidation,
        holding_hours=inputs.holding_period,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )
