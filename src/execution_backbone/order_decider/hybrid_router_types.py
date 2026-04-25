"""Typed contracts for the Build-3 hybrid router V2."""

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
class SanitizedField:
    raw_value: float
    sanitized_value: float
    sanitization_action: str


@dataclass(frozen=True)
class HybridRoutingDecisionDiagnostics:
    market_toxicity: SanitizedField
    regime_transition_risk: SanitizedField
    regime_stability: SanitizedField
    short_window_volatility_z: SanitizedField
    composite_dir: float
    participation_ratio: float
    expected_wait_s: float
    alpha_decay_factor: float
    capital_opportunity_rate_bps_per_s: float
    capital_opportunity_cost_bps: float
    ev_maker_raw_bps: float
    ev_maker_weighted_bps: float
    ev_taker_bps: float
    ev_maker_raw_minus_taker_bps: float
    ev_maker_weighted_minus_taker_bps: float


@dataclass(frozen=True)
class HybridRoutingDecision:
    action: HybridRoutingAction
    p_fill_proxy: float
    ev_maker_bps: float
    ev_taker_bps: float
    expected_miss_cost_bps: float
    expected_adverse_selection_bps: float
    expected_taker_slippage_bps: float
    expected_latency_staleness_bps: float
    diagnostics: HybridRoutingDecisionDiagnostics
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class HybridRoutingPlan:
    decision: HybridRoutingDecision
    maker_timeout_s: float
    max_signal_age_for_fallback_s: float
    maker_min_fill_progress_ratio: float
    shadow_only: bool
    calibration_version: str


@dataclass(frozen=True)
class RoutingTraceCompact:
    action: str
    ev_maker_bps: float
    ev_taker_bps: float
    p_fill_proxy: float
    participation_ratio: float
    n_reason_codes: int
    calibration_version: str
    shadow_only: bool


@dataclass(frozen=True)
class RoutingTraceFull:
    compact: RoutingTraceCompact
    diagnostics: HybridRoutingDecisionDiagnostics
    reason_codes: tuple[str, ...]


def build_compact_routing_trace(
    decision: HybridRoutingDecision,
    *,
    calibration_version: str,
    shadow_only: bool,
) -> RoutingTraceCompact:
    diagnostics = decision.diagnostics
    return RoutingTraceCompact(
        action=decision.action.value,
        ev_maker_bps=decision.ev_maker_bps,
        ev_taker_bps=decision.ev_taker_bps,
        p_fill_proxy=decision.p_fill_proxy,
        participation_ratio=diagnostics.participation_ratio,
        n_reason_codes=len(decision.reason_codes),
        calibration_version=calibration_version,
        shadow_only=shadow_only,
    )


def build_full_routing_trace(
    decision: HybridRoutingDecision,
    *,
    calibration_version: str,
    shadow_only: bool,
) -> RoutingTraceFull:
    return RoutingTraceFull(
        compact=build_compact_routing_trace(
            decision,
            calibration_version=calibration_version,
            shadow_only=shadow_only,
        ),
        diagnostics=decision.diagnostics,
        reason_codes=decision.reason_codes,
    )


def build_compact_routing_trace_payload(
    decision: HybridRoutingDecision,
    *,
    calibration_version: str,
    shadow_only: bool,
) -> dict[str, object]:
    trace = build_compact_routing_trace(
        decision,
        calibration_version=calibration_version,
        shadow_only=shadow_only,
    )
    return trace.__dict__.copy()


def build_full_routing_trace_payload(
    decision: HybridRoutingDecision,
    *,
    calibration_version: str,
    shadow_only: bool,
) -> dict[str, object]:
    trace = build_full_routing_trace(
        decision,
        calibration_version=calibration_version,
        shadow_only=shadow_only,
    )
    diagnostics = trace.diagnostics
    return {
        "compact": trace.compact.__dict__.copy(),
        "diagnostics": {
            "market_toxicity": diagnostics.market_toxicity.__dict__,
            "regime_transition_risk": diagnostics.regime_transition_risk.__dict__,
            "regime_stability": diagnostics.regime_stability.__dict__,
            "short_window_volatility_z": diagnostics.short_window_volatility_z.__dict__,
            "composite_dir": diagnostics.composite_dir,
            "participation_ratio": diagnostics.participation_ratio,
            "expected_wait_s": diagnostics.expected_wait_s,
            "alpha_decay_factor": diagnostics.alpha_decay_factor,
            "capital_opportunity_rate_bps_per_s": diagnostics.capital_opportunity_rate_bps_per_s,
            "capital_opportunity_cost_bps": diagnostics.capital_opportunity_cost_bps,
            "ev_maker_raw_bps": diagnostics.ev_maker_raw_bps,
            "ev_maker_weighted_bps": diagnostics.ev_maker_weighted_bps,
            "ev_taker_bps": diagnostics.ev_taker_bps,
            "ev_maker_raw_minus_taker_bps": diagnostics.ev_maker_raw_minus_taker_bps,
            "ev_maker_weighted_minus_taker_bps": diagnostics.ev_maker_weighted_minus_taker_bps,
            "expected_miss_cost_bps": decision.expected_miss_cost_bps,
            "expected_adverse_selection_bps": decision.expected_adverse_selection_bps,
            "expected_taker_slippage_bps": decision.expected_taker_slippage_bps,
            "expected_latency_staleness_bps": decision.expected_latency_staleness_bps,
        },
        "reason_codes": trace.reason_codes,
    }


__all__ = [
    "HybridFallbackAction",
    "HybridRoutingAction",
    "HybridRoutingDecision",
    "HybridRoutingDecisionDiagnostics",
    "HybridRoutingPlan",
    "RoutingTraceCompact",
    "RoutingTraceFull",
    "SanitizedField",
    "build_compact_routing_trace",
    "build_compact_routing_trace_payload",
    "build_full_routing_trace",
    "build_full_routing_trace_payload",
]
