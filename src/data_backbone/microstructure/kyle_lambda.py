"""
V5.3 - KYLE LAMBDA
Canonical rolling OLS price-impact estimator.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KYLE_LAMBDA_METHOD_VERSION = "kyle_lambda.rolling_ols.v1"
KYLE_LAMBDA_METHOD_VERSION_HASH = sha256(
    KYLE_LAMBDA_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_KYLE_WINDOW_SECONDS = 3_600.0
MAX_KYLE_WINDOW_SECONDS = 14_400.0
DEFAULT_KYLE_BUCKET_SECONDS = 60.0
DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL = 1_000.0


class KyleTradePoint(BaseModel):
    """Trade print used for signed-volume bucketing."""

    timestamp_ns: int = Field(..., ge=1)
    price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)
    mid_price: float | None = Field(default=None, gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class KyleIntervalPoint(BaseModel):
    """One minute-style interval for rolling OLS."""

    start_timestamp_ns: int = Field(..., ge=1)
    end_timestamp_ns: int = Field(..., ge=1)
    signed_volume: float
    reference_price: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class KyleLambdaRecord(BaseModel):
    """Audit-ready Kyle lambda estimate."""

    value: float
    raw_kyle_lambda: float = 0.0
    normalized_value: float | None = None
    unit_status: str = "UNNORMALIZED_LOCAL_OLS_SLOPE"
    cross_pair_comparable: bool = False
    normalized_kyle_lambda_available: bool = False
    reference_mid_price: float | None = Field(default=None, gt=0.0)
    standard_quote_notional: float | None = Field(default=None, gt=0.0)
    normalized_kyle_impact_bps_for_standard_notional: float | None = None
    normalized_unit_status: str | None = None
    normalized_cross_pair_comparable: bool = False
    is_stale: bool
    stale_reason: str | None = Field(default=None)
    partial_window: bool = False
    low_sample_confidence: bool = False
    insufficient_variation: bool = False
    derived_input_warning: str | None = None
    n_events_received: int = Field(..., ge=2)
    n_intervals_used: int = Field(..., ge=1)
    n_intervals_effective: int = Field(..., ge=1)
    window_used: tuple[int | None, float | None]
    n_events_used: int = Field(..., ge=1)
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

    @model_validator(mode="after")
    def _align_raw_kyle_lambda(self) -> "KyleLambdaRecord":
        if self.raw_kyle_lambda == 0.0 and self.value != 0.0:
            object.__setattr__(self, "raw_kyle_lambda", self.value)
        return self


def classify_trade_direction(
    current: KyleTradePoint,
    *,
    previous_trade: KyleTradePoint | None,
    previous_sign: int = 0,
) -> int:
    """Lee-Ready first, tick-rule fallback."""

    if current.mid_price is not None:
        if current.price > current.mid_price:
            return 1
        if current.price < current.mid_price:
            return -1
    if previous_trade is None:
        return previous_sign
    if current.price > previous_trade.price:
        return 1
    if current.price < previous_trade.price:
        return -1
    return previous_sign


def build_kyle_intervals(
    trades: list[KyleTradePoint],
    *,
    bucket_seconds: float = DEFAULT_KYLE_BUCKET_SECONDS,
) -> tuple[KyleIntervalPoint, ...]:
    """Aggregate trades into fixed-width intervals with signed volume."""

    if len(trades) < 1:
        raise ValueError("at least 1 trade is required")
    if bucket_seconds <= 0.0:
        raise ValueError("bucket_seconds must be > 0")
    for previous, current in zip(trades, trades[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("trades must be non-decreasing in timestamp_ns")

    bucket_ns = int(bucket_seconds * 1_000_000_000.0)
    intervals: list[KyleIntervalPoint] = []
    bucket_start = trades[0].timestamp_ns
    bucket_end = bucket_start + bucket_ns
    bucket_signed_volume = 0.0
    bucket_reference_price: float | None = None
    previous_trade: KyleTradePoint | None = None
    previous_sign = 0

    def finalize_interval() -> None:
        nonlocal bucket_signed_volume, bucket_reference_price, bucket_start, bucket_end
        if bucket_reference_price is None:
            return
        intervals.append(
            KyleIntervalPoint(
                start_timestamp_ns=bucket_start,
                end_timestamp_ns=bucket_end,
                signed_volume=bucket_signed_volume,
                reference_price=bucket_reference_price,
            )
        )

    for trade in trades:
        while trade.timestamp_ns >= bucket_end:
            finalize_interval()
            bucket_start = bucket_end
            bucket_end = bucket_start + bucket_ns
            bucket_signed_volume = 0.0
            bucket_reference_price = None

        sign = classify_trade_direction(
            trade,
            previous_trade=previous_trade,
            previous_sign=previous_sign,
        )
        bucket_signed_volume += sign * trade.volume
        bucket_reference_price = trade.mid_price if trade.mid_price is not None else trade.price
        previous_trade = trade
        previous_sign = sign

    finalize_interval()
    return tuple(intervals)


def _ols_slope(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator <= 0.0:
        return None
    return numerator / denominator


def _hash_input(
    *,
    pair: str,
    window_seconds: float,
    bucket_seconds: float,
    computed_at_ns: int,
    derived_input_warning: str | None,
    trades: list[KyleTradePoint],
) -> str:
    payload = {
        "pair": pair,
        "window_seconds": window_seconds,
        "bucket_seconds": bucket_seconds,
        "computed_at_ns": computed_at_ns,
        "derived_input_warning": derived_input_warning,
        "trades": [
            {
                "timestamp_ns": trade.timestamp_ns,
                "price": trade.price,
                "volume": trade.volume,
                "mid_price": trade.mid_price,
            }
            for trade in trades
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def _select_effective_trades(
    trades: list[KyleTradePoint],
    *,
    window_start_ns: int,
) -> tuple[list[KyleTradePoint], list[KyleTradePoint], str | None]:
    recent_trades = [trade for trade in trades if trade.timestamp_ns >= window_start_ns]
    if len(recent_trades) < 2:
        recent_trades = trades[-2:]
    first_recent = recent_trades[0]
    first_recent_index = next(
        index
        for index, trade in enumerate(trades)
        if trade.timestamp_ns == first_recent.timestamp_ns
    )
    effective_trades = list(recent_trades)
    derived_input_warning: str | None = None
    if first_recent.mid_price is None and first_recent_index > 0:
        effective_trades = [trades[first_recent_index - 1], *recent_trades]
        derived_input_warning = "classification_seed_trade_used"
    return recent_trades, effective_trades, derived_input_warning


def compute_normalized_kyle_impact_bps(
    raw_kyle_lambda: float,
    *,
    mid_price: float,
    standard_quote_notional: float = DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
) -> float:
    """Project raw Kyle slope into bps impact for a fixed quote notional."""

    if mid_price <= 0.0:
        raise ValueError("mid_price must be > 0")
    if standard_quote_notional <= 0.0:
        raise ValueError("standard_quote_notional must be > 0")
    base_qty_standard = standard_quote_notional / mid_price
    predicted_price_move = raw_kyle_lambda * base_qty_standard
    return (predicted_price_move / mid_price) * 10_000.0


def compute_kyle_lambda(
    trades: list[KyleTradePoint],
    *,
    pair: str,
    window_seconds: float = DEFAULT_KYLE_WINDOW_SECONDS,
    bucket_seconds: float = DEFAULT_KYLE_BUCKET_SECONDS,
    standard_quote_notional: float = DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL,
    computed_at_ns: int | None = None,
) -> KyleLambdaRecord:
    """Compute rolling OLS Kyle lambda on recent fixed-width intervals."""

    if len(trades) < 2:
        raise ValueError("at least 2 trades are required")
    if not 0.0 < window_seconds <= MAX_KYLE_WINDOW_SECONDS:
        raise ValueError(
            f"window_seconds must be in (0, {MAX_KYLE_WINDOW_SECONDS}]"
        )
    if not 0.0 < bucket_seconds <= window_seconds:
        raise ValueError("bucket_seconds must be > 0 and <= window_seconds")
    eval_time_ns = trades[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < trades[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest trade timestamp")

    window_start = eval_time_ns - int(window_seconds * 1_000_000_000.0)
    recent_trades, effective_trades, derived_input_warning = _select_effective_trades(
        trades,
        window_start_ns=window_start,
    )
    intervals = build_kyle_intervals(effective_trades, bucket_seconds=bucket_seconds)
    if len(intervals) < 2:
        raise ValueError("at least 2 populated intervals are required")
    recent_intervals = [
        interval for interval in intervals if interval.end_timestamp_ns >= window_start
    ]
    if len(recent_intervals) < 2:
        recent_intervals = list(intervals[-2:])

    x_values = [interval.signed_volume for interval in recent_intervals[1:]]
    y_values = [
        current.reference_price - previous.reference_price
        for previous, current in zip(recent_intervals, recent_intervals[1:])
    ]
    slope = _ols_slope(x_values, y_values)
    stale_reason: str | None = None
    is_stale = False
    insufficient_variation = False
    if slope is None:
        slope = 0.0
        is_stale = True
        stale_reason = "zero_signed_volume_variance"
        insufficient_variation = True
    elif slope <= 0.0:
        is_stale = True
        stale_reason = "non_positive_lambda"

    observed_window_seconds = (
        recent_intervals[-1].end_timestamp_ns - recent_intervals[0].start_timestamp_ns
    ) / 1_000_000_000.0
    available_window_seconds = (
        trades[-1].timestamp_ns - trades[0].timestamp_ns
    ) / 1_000_000_000.0
    mean_reference_price = (
        sum(interval.reference_price for interval in recent_intervals) / len(recent_intervals)
    )
    normalized_value = None if mean_reference_price <= 0.0 else slope / mean_reference_price
    normalized_kyle_impact_bps = None
    normalized_cross_pair_comparable = False
    normalized_unit_status: str | None = None
    if mean_reference_price > 0.0 and standard_quote_notional > 0.0:
        normalized_kyle_impact_bps = compute_normalized_kyle_impact_bps(
            slope,
            mid_price=mean_reference_price,
            standard_quote_notional=standard_quote_notional,
        )
        normalized_cross_pair_comparable = True
        normalized_unit_status = "NORMALIZED_BPS_FOR_STANDARD_NOTIONAL"
    return KyleLambdaRecord(
        value=slope,
        raw_kyle_lambda=slope,
        normalized_value=normalized_value,
        is_stale=is_stale,
        stale_reason=stale_reason,
        reference_mid_price=(mean_reference_price if mean_reference_price > 0.0 else None),
        standard_quote_notional=(standard_quote_notional if standard_quote_notional > 0.0 else None),
        normalized_kyle_impact_bps_for_standard_notional=normalized_kyle_impact_bps,
        normalized_unit_status=normalized_unit_status,
        normalized_cross_pair_comparable=normalized_cross_pair_comparable,
        normalized_kyle_lambda_available=normalized_kyle_impact_bps is not None,
        partial_window=available_window_seconds < window_seconds,
        low_sample_confidence=len(recent_intervals) < 5,
        insufficient_variation=insufficient_variation,
        derived_input_warning=derived_input_warning,
        n_events_received=len(trades),
        n_intervals_used=len(recent_intervals),
        n_intervals_effective=len(recent_intervals) - 1,
        window_used=(None, observed_window_seconds),
        n_events_used=len(recent_trades),
        method_version_hash=KYLE_LAMBDA_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(
            pair=pair,
            window_seconds=window_seconds,
            bucket_seconds=bucket_seconds,
            computed_at_ns=eval_time_ns,
            derived_input_warning=derived_input_warning,
            trades=effective_trades,
        ),
    )


__all__ = [
    "DEFAULT_KYLE_BUCKET_SECONDS",
    "DEFAULT_KYLE_STANDARD_QUOTE_NOTIONAL",
    "DEFAULT_KYLE_WINDOW_SECONDS",
    "KYLE_LAMBDA_METHOD_VERSION",
    "KYLE_LAMBDA_METHOD_VERSION_HASH",
    "KyleIntervalPoint",
    "KyleLambdaRecord",
    "KyleTradePoint",
    "MAX_KYLE_WINDOW_SECONDS",
    "build_kyle_intervals",
    "classify_trade_direction",
    "compute_normalized_kyle_impact_bps",
    "compute_kyle_lambda",
]
