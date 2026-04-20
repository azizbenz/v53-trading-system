"""
V5.3 - VPIN
Canonical equal-volume VPIN estimator with bulk-volume classification.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import erf, sqrt

from pydantic import BaseModel, ConfigDict, Field, field_validator


VPIN_METHOD_VERSION = "vpin.easley_lopez_ohara.v1"
VPIN_METHOD_VERSION_HASH = sha256(VPIN_METHOD_VERSION.encode("utf-8")).hexdigest()
DEFAULT_VPIN_BUCKETS_PER_DAY = 50
MAX_VPIN_BUCKETS_PER_DAY = 100
DEFAULT_VPIN_WINDOW_BUCKETS = 50
MAX_VPIN_WINDOW_BUCKETS = 200


class VpinTradePoint(BaseModel):
    """Trade print used by equal-volume VPIN bucketing."""

    timestamp_ns: int = Field(..., ge=1)
    price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class VpinBucket(BaseModel):
    """One equal-volume bucket used for VPIN estimation."""

    start_timestamp_ns: int = Field(..., ge=1)
    end_timestamp_ns: int = Field(..., ge=1)
    total_volume: float = Field(..., gt=0.0)
    open_price: float = Field(..., gt=0.0)
    close_price: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @property
    def price_change(self) -> float:
        return self.close_price - self.open_price


class VpinRecord(BaseModel):
    """Audit-ready VPIN result."""

    value: float = Field(..., ge=0.0, le=1.0)
    bucket_volume: float = Field(..., gt=0.0)
    n_buckets_used: int = Field(..., ge=1)
    n_complete_buckets: int = Field(..., ge=1)
    n_events_received: int = Field(..., ge=1)
    partial_window: bool = False
    low_sample_confidence: bool = False
    insufficient_variation: bool = False
    derived_input_warning: str | None = None
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


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def build_equal_volume_buckets(
    trades: list[VpinTradePoint],
    *,
    bucket_volume: float,
) -> tuple[VpinBucket, ...]:
    """Split trades into complete equal-volume buckets, spilling volume across edges."""

    return tuple(bucket for bucket, _ in _build_equal_volume_buckets_with_trade_indices(
        trades,
        bucket_volume=bucket_volume,
    ))


def _build_equal_volume_buckets_with_trade_indices(
    trades: list[VpinTradePoint],
    *,
    bucket_volume: float,
) -> tuple[tuple[VpinBucket, tuple[int, ...]], ...]:
    """Build equal-volume buckets and retain exact contributing trade indices."""

    if len(trades) < 1:
        raise ValueError("at least 1 trade is required")
    if bucket_volume <= 0.0:
        raise ValueError("bucket_volume must be > 0")
    for previous, current in zip(trades, trades[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("trades must be non-decreasing in timestamp_ns")

    buckets: list[tuple[VpinBucket, tuple[int, ...]]] = []
    current_volume = 0.0
    current_start_ns: int | None = None
    current_open_price: float | None = None
    current_close_price: float | None = None
    current_end_ns: int | None = None
    current_trade_indices: set[int] = set()

    for trade_index, trade in enumerate(trades):
        remaining_trade_volume = trade.volume
        while remaining_trade_volume > 0.0:
            if current_start_ns is None:
                current_start_ns = trade.timestamp_ns
                current_open_price = trade.price
            current_trade_indices.add(trade_index)
            fill_volume = min(bucket_volume - current_volume, remaining_trade_volume)
            current_volume += fill_volume
            remaining_trade_volume -= fill_volume
            current_close_price = trade.price
            current_end_ns = trade.timestamp_ns

            if current_volume >= bucket_volume - 1e-12:
                buckets.append(
                    (
                        VpinBucket(
                            start_timestamp_ns=current_start_ns,
                            end_timestamp_ns=current_end_ns,
                            total_volume=bucket_volume,
                            open_price=(
                                current_open_price if current_open_price is not None else trade.price
                            ),
                            close_price=current_close_price,
                        ),
                        tuple(sorted(current_trade_indices)),
                    )
                )
                current_volume = 0.0
                current_start_ns = None
                current_open_price = None
                current_close_price = None
                current_end_ns = None
                current_trade_indices = set()

    return tuple(buckets)


def classify_bucket_buy_sell_volume(
    bucket: VpinBucket,
    *,
    sigma_delta_p: float,
) -> tuple[float, float]:
    """Bucket-level BVC classification following the V5.3 operational form."""

    delta_p = bucket.price_change
    if sigma_delta_p <= 0.0:
        if delta_p > 0.0:
            return bucket.total_volume, 0.0
        if delta_p < 0.0:
            return 0.0, bucket.total_volume
        half_volume = bucket.total_volume / 2.0
        return half_volume, half_volume

    buy_fraction = _normal_cdf(delta_p / sigma_delta_p)
    buy_volume = bucket.total_volume * buy_fraction
    sell_volume = bucket.total_volume - buy_volume
    return buy_volume, sell_volume


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(max(variance, 0.0))


def _hash_input(
    *,
    pair: str,
    buckets_per_day: int,
    window_buckets: int,
    daily_volume: float,
    derived_input_warning: str | None,
    trades: list[VpinTradePoint],
) -> str:
    payload = {
        "pair": pair,
        "buckets_per_day": buckets_per_day,
        "window_buckets": window_buckets,
        "daily_volume": daily_volume,
        "derived_input_warning": derived_input_warning,
        "trades": [
            {
                "timestamp_ns": trade.timestamp_ns,
                "price": trade.price,
                "volume": trade.volume,
            }
            for trade in trades
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_vpin(
    trades: list[VpinTradePoint],
    *,
    pair: str,
    buckets_per_day: int = DEFAULT_VPIN_BUCKETS_PER_DAY,
    window_buckets: int = DEFAULT_VPIN_WINDOW_BUCKETS,
    daily_volume: float | None = None,
    allow_derived_daily_volume: bool = False,
    computed_at_ns: int | None = None,
) -> VpinRecord:
    """Compute VPIN on equal-volume buckets using bucket-level BVC."""

    if len(trades) < 1:
        raise ValueError("at least 1 trade is required")
    if not 1 <= buckets_per_day <= MAX_VPIN_BUCKETS_PER_DAY:
        raise ValueError(
            f"buckets_per_day must be in [1, {MAX_VPIN_BUCKETS_PER_DAY}]"
        )
    if not 1 <= window_buckets <= MAX_VPIN_WINDOW_BUCKETS:
        raise ValueError(
            f"window_buckets must be in [1, {MAX_VPIN_WINDOW_BUCKETS}]"
        )

    derived_input_warning: str | None = None
    if daily_volume is None:
        if not allow_derived_daily_volume:
            raise ValueError(
                "daily_volume is required unless allow_derived_daily_volume=True"
            )
        resolved_daily_volume = sum(trade.volume for trade in trades)
        derived_input_warning = "derived_daily_volume_used"
    else:
        resolved_daily_volume = daily_volume
    if resolved_daily_volume <= 0.0:
        raise ValueError("daily_volume must be > 0")

    bucket_volume = resolved_daily_volume / buckets_per_day
    bucket_rows = _build_equal_volume_buckets_with_trade_indices(trades, bucket_volume=bucket_volume)
    if not bucket_rows:
        raise ValueError("at least 1 complete equal-volume bucket is required")

    resolved_window = min(window_buckets, len(bucket_rows))
    recent_bucket_rows = list(bucket_rows[-resolved_window:])
    recent_buckets = [bucket for bucket, _ in recent_bucket_rows]
    effective_trade_indices = sorted(
        {trade_index for _, bucket_trade_indices in recent_bucket_rows for trade_index in bucket_trade_indices}
    )
    effective_trades = [trades[index] for index in effective_trade_indices]
    delta_ps = [bucket.price_change for bucket in recent_buckets]
    sigma_delta_p = _stddev(delta_ps)
    buy_sell_volumes = [
        classify_bucket_buy_sell_volume(bucket, sigma_delta_p=sigma_delta_p)
        for bucket in recent_buckets
    ]
    numerator = sum(abs(buy_volume - sell_volume) for buy_volume, sell_volume in buy_sell_volumes)
    denominator = resolved_window * bucket_volume
    vpin_value = numerator / denominator if denominator > 0.0 else 0.0
    eval_time_ns = recent_buckets[-1].end_timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < recent_buckets[-1].end_timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest bucket timestamp")
    observed_window_seconds = (
        recent_buckets[-1].end_timestamp_ns - recent_buckets[0].start_timestamp_ns
    ) / 1_000_000_000.0
    return VpinRecord(
        value=max(0.0, min(1.0, vpin_value)),
        bucket_volume=bucket_volume,
        n_buckets_used=resolved_window,
        n_complete_buckets=len(bucket_rows),
        n_events_received=len(trades),
        partial_window=resolved_window < window_buckets,
        low_sample_confidence=(
            resolved_window < 5
            or resolved_window < window_buckets
            or derived_input_warning is not None
        ),
        insufficient_variation=sigma_delta_p <= 0.0,
        derived_input_warning=derived_input_warning,
        window_used=(resolved_window, observed_window_seconds),
        n_events_used=len(effective_trade_indices),
        method_version_hash=VPIN_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(
            pair=pair,
            buckets_per_day=buckets_per_day,
            window_buckets=resolved_window,
            daily_volume=resolved_daily_volume,
            derived_input_warning=derived_input_warning,
            trades=effective_trades,
        ),
    )


__all__ = [
    "DEFAULT_VPIN_BUCKETS_PER_DAY",
    "DEFAULT_VPIN_WINDOW_BUCKETS",
    "MAX_VPIN_BUCKETS_PER_DAY",
    "MAX_VPIN_WINDOW_BUCKETS",
    "VPIN_METHOD_VERSION",
    "VPIN_METHOD_VERSION_HASH",
    "VpinBucket",
    "VpinRecord",
    "VpinTradePoint",
    "build_equal_volume_buckets",
    "classify_bucket_buy_sell_volume",
    "compute_vpin",
]
