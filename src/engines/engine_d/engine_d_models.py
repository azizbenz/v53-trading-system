"""Shared typed models for the canonical Engine D runner/runtime."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .cost_feasibility_d import ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE


class EngineDDecision(StrEnum):
    EMIT = "emit"
    NO_TRADE = "no_trade"


class NoTradeReasonD(StrEnum):
    INVALID_ENTRY_PRICE = "invalid_entry_price"
    INVALID_CANDIDATE_SIZE = "invalid_candidate_size"
    INVALID_HOLDING_PERIOD = "invalid_holding_period"
    INVALID_REENTRY_ANCHOR = "invalid_reentry_anchor"
    INVALID_ATR = "invalid_atr"
    ANTI_REVENGE_BLOCKED = "anti_revenge_blocked"
    HISTORY_WEAK = "history_weak"
    REFORMATION_WEAK = "reformation_weak"
    MARGINAL_EDGE_TOO_LOW = "marginal_edge_too_low"
    MARGINAL_GAIN_TOO_LOW = "marginal_gain_too_low"
    DUPLICATION_BLOCKED = "duplication_blocked"
    CONCENTRATION_BLOCKED = "concentration_blocked"
    COST_INFEASIBLE = "cost_infeasible"
    CONVICTION_TOO_LOW = "conviction_too_low"


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
    reference_source: str = ""


class EngineDLogEntry(BaseModel, frozen=True):
    event: str
    pair: str
    regime: str = ""
    origin_context_id: str = ""
    origin_trade_id: str = ""
    link_type: str = ""
    structure_reformed_detected: bool = False
    first_episode_id: str = ""
    first_episode_engine_id: str = ""
    first_episode_close_reason: str = ""
    consecutive_stop_count: int = 0
    last_stop_at_ns: int | None = None
    last_fresh_a_detection_at_ns: int | None = None
    anti_revenge_state: str = ""
    anti_revenge_blocked: bool = False
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
    duplication_blocked: bool = False
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
    first_episode_id: str = ""
    first_episode_engine_id: str = ""
    first_episode_close_reason: str = ""
    consecutive_stop_count: int = 0
    last_stop_at_ns: int | None = None
    last_fresh_a_detection_at_ns: int | None = None
    anti_revenge_state: str = ""
    anti_revenge_blocked: bool = False
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
    duplication_blocked: bool = False
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    invalidation: EngineDInvalidation | None = None
    holding_hours: float = 0.0
    scoring_version: str = ""
    reason_codes: tuple[str, ...] = ()
    no_trade_reasons: tuple[NoTradeReasonD, ...] = ()
    log_entries: tuple[EngineDLogEntry, ...] = ()


class EngineDInput(BaseModel, frozen=True):
    pair: str
    origin_context_id: str = ""
    origin_trade_id: str = ""
    link_type: str = "prior_trade"
    first_episode_id: str = ""
    first_episode_engine_id: str = ""
    first_episode_close_reason: str = ""
    consecutive_stop_count: int = Field(default=0, ge=0)
    last_stop_at_ns: int | None = Field(default=None, ge=1_000_000_000_000_000_000, le=9_999_999_999_999_999_999)
    last_fresh_a_detection_at_ns: int | None = Field(
        default=None,
        ge=1_000_000_000_000_000_000,
        le=9_999_999_999_999_999_999,
    )
    anti_revenge_state: str = ""
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
    ce_min: float = ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE.ce_min
    delta_safe: float = ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE.delta_safe
    entry_price: float = 0.0
    reentry_anchor_price: float = 0.0
    realized_vol_current: float | None = Field(default=None, ge=0.0)
    realized_vol_post_close: float | None = Field(default=None, ge=0.0)
    # Legacy overlay only. Central forecast / invalidation logic must consume
    # the governed realized-vol seam instead of ATR.
    atr: float = 0.0
    duplication_overlap_with_engine_a: float = 0.0
    marginal_portfolio_gain: float = 0.0
    covered_share_by_engine_a: float = 0.0
    scoring_version: str = ""


__all__ = [
    "ConvictionLevelD",
    "EngineDDecision",
    "EngineDInput",
    "EngineDInvalidation",
    "EngineDLogEntry",
    "EngineDOutput",
    "NoTradeReasonD",
    "TierSuggestionD",
]
