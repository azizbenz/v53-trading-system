"""
V5.3 - QUEUE PRESSURE
Canonical top-k book-imbalance feature.
"""

from __future__ import annotations

from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


QUEUE_PRESSURE_METHOD_VERSION = "queue_pressure.book_imbalance.v1"
QUEUE_PRESSURE_METHOD_VERSION_HASH = sha256(
    QUEUE_PRESSURE_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_QUEUE_PRESSURE_TOP_K = 5


class QueuePressureBookPoint(BaseModel):
    """Top-k visible book sizes at one timestamp."""

    timestamp_ns: int = Field(..., ge=1)
    bid_sizes: tuple[float, ...] = Field(..., min_length=1)
    ask_sizes: tuple[float, ...] = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("bid_sizes", "ask_sizes")
    @classmethod
    def _validate_sizes(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not value:
            raise ValueError("book side must not be empty")
        normalized = tuple(float(size) for size in value)
        if any(size < 0.0 for size in normalized):
            raise ValueError("book sizes must be >= 0")
        return normalized


class QueuePressureRecord(BaseModel):
    """Audit-ready queue-pressure record."""

    value: float = Field(..., ge=-1.0, le=1.0)
    top_k_used: int = Field(..., ge=1)
    partial_window: bool = False
    low_sample_confidence: bool = False
    measurement_status: str = "MEASURED"
    reason_codes: tuple[str, ...] = ()
    bid_volume_used: float = Field(..., ge=0.0)
    ask_volume_used: float = Field(..., ge=0.0)
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


def _hash_input(
    *,
    pair: str,
    top_k: int,
    point: QueuePressureBookPoint,
) -> str:
    payload = {
        "pair": pair,
        "top_k": top_k,
        "timestamp_ns": point.timestamp_ns,
        "bid_sizes": list(point.bid_sizes),
        "ask_sizes": list(point.ask_sizes),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_queue_pressure(
    point: QueuePressureBookPoint,
    *,
    pair: str,
    top_k: int = DEFAULT_QUEUE_PRESSURE_TOP_K,
    computed_at_ns: int | None = None,
) -> QueuePressureRecord:
    """Compute book imbalance on the first K displayed levels."""

    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    resolved_top_k = min(top_k, len(point.bid_sizes), len(point.ask_sizes))
    bid_volume = sum(point.bid_sizes[:resolved_top_k])
    ask_volume = sum(point.ask_sizes[:resolved_top_k])
    denominator = bid_volume + ask_volume
    value = 0.0 if denominator <= 0.0 else (bid_volume - ask_volume) / denominator
    measurement_status = "MEASURED"
    reason_codes: tuple[str, ...] = ()
    if denominator <= 0.0:
        measurement_status = "QUEUE_PRESSURE_INSUFFICIENT_DEPTH"
        reason_codes = ("QUEUE_PRESSURE_INSUFFICIENT_DEPTH",)
    eval_time_ns = point.timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < point.timestamp_ns:
        raise ValueError("computed_at_ns must be >= point timestamp")
    return QueuePressureRecord(
        value=max(-1.0, min(1.0, value)),
        top_k_used=resolved_top_k,
        partial_window=resolved_top_k < top_k,
        low_sample_confidence=denominator <= 0.0,
        measurement_status=measurement_status,
        reason_codes=reason_codes,
        bid_volume_used=bid_volume,
        ask_volume_used=ask_volume,
        window_used=(1, None),
        n_events_used=1,
        method_version_hash=QUEUE_PRESSURE_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair=pair, top_k=resolved_top_k, point=point),
    )


__all__ = [
    "DEFAULT_QUEUE_PRESSURE_TOP_K",
    "QUEUE_PRESSURE_METHOD_VERSION",
    "QUEUE_PRESSURE_METHOD_VERSION_HASH",
    "QueuePressureBookPoint",
    "QueuePressureRecord",
    "compute_queue_pressure",
]
