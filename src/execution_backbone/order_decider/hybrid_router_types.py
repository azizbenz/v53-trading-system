"""Typed contracts for the Build-3 hybrid router."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HybridRoutingAction(str, Enum):
    NO_TRADE = "NO_TRADE"
    LIMIT_MAKER = "LIMIT_MAKER"
    MARKET_TAKER = "MARKET_TAKER"


class HybridFallbackAction(str, Enum):
    CANCEL = "CANCEL"
    CONVERT_TO_MARKET = "CONVERT_TO_MARKET"


@dataclass(frozen=True)
class HybridRoutingDecision:
    action: HybridRoutingAction
    ev_maker_bps: float
    ev_taker_bps: float
    p_fill_proxy: float
    participation_ratio: float
    expected_wait_s: float
    expected_miss_cost_bps: float
    expected_adverse_selection_bps: float
    expected_taker_slippage_bps: float
    capital_opportunity_cost_bps: float
    expected_latency_staleness_bps: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class HybridRoutingPlan:
    decision: HybridRoutingDecision
    maker_timeout_s: float
    max_signal_age_for_fallback_s: float
    maker_min_fill_progress_ratio: float
    inv003_max_participation_ratio: float
    shadow_only: bool


def build_routing_trace_payload(
    decision: HybridRoutingDecision,
    *,
    shadow_only: bool,
) -> dict[str, object]:
    return {
        "action": decision.action.value,
        "ev_maker_bps": decision.ev_maker_bps,
        "ev_taker_bps": decision.ev_taker_bps,
        "p_fill_proxy": decision.p_fill_proxy,
        "participation_ratio": decision.participation_ratio,
        "expected_wait_s": decision.expected_wait_s,
        "expected_miss_cost_bps": decision.expected_miss_cost_bps,
        "expected_adverse_selection_bps": decision.expected_adverse_selection_bps,
        "expected_taker_slippage_bps": decision.expected_taker_slippage_bps,
        "capital_opportunity_cost_bps": decision.capital_opportunity_cost_bps,
        "expected_latency_staleness_bps": decision.expected_latency_staleness_bps,
        "reason_codes": decision.reason_codes,
        "shadow_only": shadow_only,
    }


__all__ = [
    "HybridFallbackAction",
    "HybridRoutingAction",
    "HybridRoutingDecision",
    "HybridRoutingPlan",
    "build_routing_trace_payload",
]
