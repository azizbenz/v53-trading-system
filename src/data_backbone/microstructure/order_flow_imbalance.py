"""
V5.3 - ORDER FLOW IMBALANCE
Canonical best-bid / best-ask event-driven OFI calculator.
"""

from __future__ import annotations

from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ORDER_FLOW_IMBALANCE_METHOD_VERSION = "order_flow_imbalance.cont_kukanov.v1"
ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH = sha256(
    ORDER_FLOW_IMBALANCE_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_OFI_WINDOW_EVENTS = 200
MAX_OFI_WINDOW_EVENTS = 2_000


class OrderBookTopLevelPoint(BaseModel):
    """Top-of-book snapshot at one event."""

    timestamp_ns: int = Field(..., ge=1)
    bid_price: float = Field(..., gt=0.0)
    bid_size: float = Field(..., ge=0.0)
    ask_price: float = Field(..., gt=0.0)
    ask_size: float = Field(..., ge=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _validate_book(self) -> "OrderBookTopLevelPoint":
        if self.ask_price < self.bid_price:
            raise ValueError("ask_price must be >= bid_price")
        return self


class OrderFlowImbalanceRecord(BaseModel):
    """Audit-ready cumulative OFI record."""

    value: float
    partial_window: bool = False
    low_sample_confidence: bool = False
    n_events_received: int = Field(..., ge=2)
    window_used: tuple[int | None, float | None]
    n_events_used: int = Field(..., ge=2)
    method_version_hash: str = Field(..., min_length=8)
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    input_data_hash: str = Field(..., min_length=8)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized


def compute_order_book_event_contribution(
    previous: OrderBookTopLevelPoint,
    current: OrderBookTopLevelPoint,
) -> float:
    """Cont-Kukanov-Stoikov event contribution."""

    bid_up_or_same = 1.0 if current.bid_price >= previous.bid_price else 0.0
    bid_down_or_same = 1.0 if current.bid_price <= previous.bid_price else 0.0
    ask_down_or_same = 1.0 if current.ask_price <= previous.ask_price else 0.0
    ask_up_or_same = 1.0 if current.ask_price >= previous.ask_price else 0.0
    return (
        (bid_up_or_same * current.bid_size)
        - (bid_down_or_same * previous.bid_size)
        - (ask_down_or_same * current.ask_size)
        + (ask_up_or_same * previous.ask_size)
    )


def _hash_input(
    *,
    pair: str,
    window_events: int,
    points: list[OrderBookTopLevelPoint],
) -> str:
    payload = {
        "pair": pair,
        "window_events": window_events,
        "points": [
            {
                "timestamp_ns": point.timestamp_ns,
                "bid_price": point.bid_price,
                "bid_size": point.bid_size,
                "ask_price": point.ask_price,
                "ask_size": point.ask_size,
            }
            for point in points
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_order_flow_imbalance(
    points: list[OrderBookTopLevelPoint],
    *,
    pair: str,
    window_events: int = DEFAULT_OFI_WINDOW_EVENTS,
    computed_at_ns: int | None = None,
) -> OrderFlowImbalanceRecord:
    """Compute cumulative OFI over the last N top-of-book events."""

    if len(points) < 2:
        raise ValueError("at least 2 top-of-book points are required")
    if not 1 <= window_events <= MAX_OFI_WINDOW_EVENTS:
        raise ValueError(
            f"window_events must be in [1, {MAX_OFI_WINDOW_EVENTS}]"
        )
    for previous, current in zip(points, points[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("points must be non-decreasing in timestamp_ns")

    contributions = [
        compute_order_book_event_contribution(previous, current)
        for previous, current in zip(points, points[1:])
    ]
    resolved_window = min(window_events, len(contributions))
    recent_contributions = contributions[-resolved_window:]
    recent_points = points[-(resolved_window + 1):]
    eval_time_ns = recent_points[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < recent_points[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest point timestamp")
    observed_window_seconds = (
        recent_points[-1].timestamp_ns - recent_points[0].timestamp_ns
    ) / 1_000_000_000.0
    return OrderFlowImbalanceRecord(
        value=sum(recent_contributions),
        partial_window=resolved_window < window_events,
        low_sample_confidence=resolved_window < 3,
        n_events_received=len(points),
        window_used=(resolved_window, observed_window_seconds),
        n_events_used=len(recent_points),
        method_version_hash=ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(
            pair=pair,
            window_events=resolved_window,
            points=recent_points,
        ),
    )


__all__ = [
    "DEFAULT_OFI_WINDOW_EVENTS",
    "MAX_OFI_WINDOW_EVENTS",
    "ORDER_FLOW_IMBALANCE_METHOD_VERSION",
    "ORDER_FLOW_IMBALANCE_METHOD_VERSION_HASH",
    "OrderBookTopLevelPoint",
    "OrderFlowImbalanceRecord",
    "compute_order_book_event_contribution",
    "compute_order_flow_imbalance",
]
