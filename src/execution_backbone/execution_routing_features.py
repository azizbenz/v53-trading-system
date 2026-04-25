"""Typed live routing feature contracts for Build-3 hybrid routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Side = Literal["BUY", "SELL"]


class RoutingFeatureProjectionError(ValueError):
    """Raised when live routing features cannot be projected safely."""


@dataclass(frozen=True)
class ExecutionRoutingFeatureSnapshot:
    side: Side
    expected_edge_bps: float
    spread_bps: float
    candidate_notional: float
    final_size: float
    signal_age_s: float
    best_bid_price: float
    best_bid_size: float
    best_ask_price: float
    best_ask_size: float
    top_n_bid_notional: float
    top_n_ask_notional: float
    order_book_imbalance: float
    microprice_pressure: float
    aggressive_trade_imbalance: float
    short_window_volatility: float
    short_window_volatility_z: float
    observation_coverage_ratio: float
    market_toxicity_score: float
    regime_transition_risk: float
    regime_stability_score: float
    expected_duration_bucket: str
    maker_fee_bps: float
    taker_fee_bps: float


@dataclass(frozen=True)
class ExecutionRoutingTopOfBookSnapshot:
    best_bid_price: float
    best_bid_size: float
    best_ask_price: float
    best_ask_size: float
    top_n_bid_notional: float
    top_n_ask_notional: float
    captured_at_ns: int


@dataclass(frozen=True)
class ExecutionRoutingVenueFees:
    maker_fee_bps: float
    taker_fee_bps: float


def attach_snapshot_reason_codes(
    snapshot: ExecutionRoutingFeatureSnapshot,
    reason_codes: tuple[str, ...],
) -> ExecutionRoutingFeatureSnapshot:
    object.__setattr__(snapshot, "_reason_codes", tuple(reason_codes))
    return snapshot


def snapshot_reason_codes(snapshot: ExecutionRoutingFeatureSnapshot) -> tuple[str, ...]:
    value = getattr(snapshot, "_reason_codes", ())
    if not isinstance(value, tuple):
        return ()
    return tuple(str(item) for item in value)


__all__ = [
    "ExecutionRoutingFeatureSnapshot",
    "ExecutionRoutingTopOfBookSnapshot",
    "ExecutionRoutingVenueFees",
    "RoutingFeatureProjectionError",
    "Side",
    "attach_snapshot_reason_codes",
    "snapshot_reason_codes",
]
