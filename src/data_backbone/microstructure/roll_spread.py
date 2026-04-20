"""
V5.3 - ROLL SPREAD
Canonical Roll effective-spread estimator.
"""

from __future__ import annotations

from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


ROLL_SPREAD_METHOD_VERSION = "roll_spread.roll.v1"
ROLL_SPREAD_METHOD_VERSION_HASH = sha256(
    ROLL_SPREAD_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_ROLL_WINDOW_SECONDS = 3_600.0


class RollTradePoint(BaseModel):
    """Trade-print input for Roll spread."""

    timestamp_ns: int = Field(..., ge=1)
    price: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class RollSpreadRecord(BaseModel):
    """Audit-ready Roll spread estimate."""

    value: float = Field(..., ge=0.0)
    covariance: float
    is_stale: bool = False
    stale_reason: str | None = None
    partial_window: bool = False
    low_sample_confidence: bool = False
    n_events_received: int = Field(..., ge=3)
    window_used: tuple[int | None, float | None]
    n_events_used: int = Field(..., ge=3)
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


def _hash_input(pair: str, trades: list[RollTradePoint], window_seconds: float) -> str:
    payload = {
        "pair": pair,
        "window_seconds": window_seconds,
        "trades": [
            {"timestamp_ns": trade.timestamp_ns, "price": trade.price}
            for trade in trades
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _covariance_lag_one(price_changes: list[float]) -> float:
    if len(price_changes) < 2:
        raise ValueError("at least 2 price changes are required")
    leading = price_changes[1:]
    lagged = price_changes[:-1]
    mean_leading = sum(leading) / len(leading)
    mean_lagged = sum(lagged) / len(lagged)
    return sum(
        (current - mean_leading) * (previous - mean_lagged)
        for current, previous in zip(leading, lagged)
    ) / len(leading)


def compute_roll_spread(
    trades: list[RollTradePoint],
    *,
    pair: str,
    window_seconds: float = DEFAULT_ROLL_WINDOW_SECONDS,
    computed_at_ns: int | None = None,
) -> RollSpreadRecord:
    """Compute Roll spread from lag-one covariance of price changes."""

    if len(trades) < 3:
        raise ValueError("at least 3 trade prints are required")
    if window_seconds <= 0.0:
        raise ValueError("window_seconds must be > 0")
    for previous, current in zip(trades, trades[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("trades must be non-decreasing in timestamp_ns")

    eval_time_ns = trades[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < trades[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest trade timestamp")
    window_start = eval_time_ns - int(window_seconds * 1_000_000_000.0)
    recent_trades = [trade for trade in trades if trade.timestamp_ns >= window_start]
    if len(recent_trades) < 3:
        recent_trades = trades[-3:]

    price_changes = [
        current.price - previous.price
        for previous, current in zip(recent_trades, recent_trades[1:])
    ]
    covariance = _covariance_lag_one(price_changes)
    spread = 0.0 if covariance >= 0.0 else 2.0 * ((-covariance) ** 0.5)
    stale_reason: str | None = None
    if covariance >= 0.0:
        stale_reason = "non_negative_lag_covariance"
    observed_window_seconds = (
        recent_trades[-1].timestamp_ns - recent_trades[0].timestamp_ns
    ) / 1_000_000_000.0
    available_window_seconds = (
        trades[-1].timestamp_ns - trades[0].timestamp_ns
    ) / 1_000_000_000.0
    return RollSpreadRecord(
        value=spread,
        covariance=covariance,
        is_stale=stale_reason is not None,
        stale_reason=stale_reason,
        partial_window=available_window_seconds < window_seconds,
        low_sample_confidence=len(recent_trades) < 5,
        n_events_received=len(trades),
        window_used=(None, observed_window_seconds),
        n_events_used=len(recent_trades),
        method_version_hash=ROLL_SPREAD_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair, recent_trades, window_seconds),
    )


__all__ = [
    "DEFAULT_ROLL_WINDOW_SECONDS",
    "ROLL_SPREAD_METHOD_VERSION",
    "ROLL_SPREAD_METHOD_VERSION_HASH",
    "RollSpreadRecord",
    "RollTradePoint",
    "compute_roll_spread",
]
