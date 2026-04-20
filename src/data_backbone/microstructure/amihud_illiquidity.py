"""
V5.3 - AMIHUD ILLIQUIDITY
Canonical rolling Amihud illiquidity estimator.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import log

from pydantic import BaseModel, ConfigDict, Field, field_validator


AMIHUD_METHOD_VERSION = "amihud_illiquidity.amihud.v1"
AMIHUD_METHOD_VERSION_HASH = sha256(AMIHUD_METHOD_VERSION.encode("utf-8")).hexdigest()
DEFAULT_AMIHUD_WINDOW_SECONDS = 86_400.0


class AmihudBarPoint(BaseModel):
    """Bar-level close and dollar-volume input."""

    timestamp_ns: int = Field(..., ge=1)
    close_price: float = Field(..., gt=0.0)
    dollar_volume: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class AmihudIlliquidityRecord(BaseModel):
    """Audit-ready rolling Amihud estimator."""

    value: float = Field(..., ge=0.0)
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


def _hash_input(pair: str, bars: list[AmihudBarPoint], window_seconds: float) -> str:
    payload = {
        "pair": pair,
        "window_seconds": window_seconds,
        "bars": [
            {
                "timestamp_ns": bar.timestamp_ns,
                "close_price": bar.close_price,
                "dollar_volume": bar.dollar_volume,
            }
            for bar in bars
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_amihud_illiquidity(
    bars: list[AmihudBarPoint],
    *,
    pair: str,
    window_seconds: float = DEFAULT_AMIHUD_WINDOW_SECONDS,
    computed_at_ns: int | None = None,
) -> AmihudIlliquidityRecord:
    """Compute rolling Amihud illiquidity on ordered bars."""

    if len(bars) < 2:
        raise ValueError("at least 2 bars are required")
    if window_seconds <= 0.0:
        raise ValueError("window_seconds must be > 0")
    for previous, current in zip(bars, bars[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("bars must be non-decreasing in timestamp_ns")

    eval_time_ns = bars[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < bars[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest bar timestamp")
    window_start = eval_time_ns - int(window_seconds * 1_000_000_000.0)
    recent_bars = [bar for bar in bars if bar.timestamp_ns >= window_start]
    if len(recent_bars) < 2:
        recent_bars = bars[-2:]

    ratios: list[float] = []
    for previous, current in zip(recent_bars, recent_bars[1:]):
        absolute_return = abs(log(current.close_price) - log(previous.close_price))
        ratios.append(absolute_return / current.dollar_volume)

    observed_window_seconds = (
        recent_bars[-1].timestamp_ns - recent_bars[0].timestamp_ns
    ) / 1_000_000_000.0
    available_window_seconds = (
        bars[-1].timestamp_ns - bars[0].timestamp_ns
    ) / 1_000_000_000.0
    return AmihudIlliquidityRecord(
        value=sum(ratios) / len(ratios),
        partial_window=available_window_seconds < window_seconds,
        low_sample_confidence=len(recent_bars) < 4,
        n_events_received=len(bars),
        window_used=(None, observed_window_seconds),
        n_events_used=len(recent_bars),
        method_version_hash=AMIHUD_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair, recent_bars, window_seconds),
    )


__all__ = [
    "AMIHUD_METHOD_VERSION",
    "AMIHUD_METHOD_VERSION_HASH",
    "DEFAULT_AMIHUD_WINDOW_SECONDS",
    "AmihudBarPoint",
    "AmihudIlliquidityRecord",
    "compute_amihud_illiquidity",
]
