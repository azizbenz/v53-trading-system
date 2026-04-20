"""
V5.3 - CORWIN-SCHULTZ SPREAD
Canonical high-low spread estimator.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import exp, log, sqrt

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CORWIN_SCHULTZ_METHOD_VERSION = "corwin_schultz_spread.corwin_schultz.v1"
CORWIN_SCHULTZ_METHOD_VERSION_HASH = sha256(
    CORWIN_SCHULTZ_METHOD_VERSION.encode("utf-8")
).hexdigest()
_CS_DENOMINATOR = 3.0 - (2.0 * sqrt(2.0))


class CorwinSchultzBarPoint(BaseModel):
    """High-low bar used by the Corwin-Schultz estimator."""

    timestamp_ns: int = Field(..., ge=1)
    high_price: float = Field(..., gt=0.0)
    low_price: float = Field(..., gt=0.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _validate_range(self) -> "CorwinSchultzBarPoint":
        if self.high_price < self.low_price:
            raise ValueError("high_price must be >= low_price")
        return self


class CorwinSchultzSpreadRecord(BaseModel):
    """Audit-ready Corwin-Schultz spread estimate."""

    value: float = Field(..., ge=0.0)
    beta: float = Field(..., ge=0.0)
    gamma: float = Field(..., ge=0.0)
    alpha: float
    low_sample_confidence: bool = True
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


def _log_range(bar: CorwinSchultzBarPoint) -> float:
    return log(bar.high_price / bar.low_price)


def _hash_input(pair: str, bars: list[CorwinSchultzBarPoint]) -> str:
    payload = {
        "pair": pair,
        "bars": [
            {
                "timestamp_ns": bar.timestamp_ns,
                "high_price": bar.high_price,
                "low_price": bar.low_price,
            }
            for bar in bars
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_corwin_schultz_spread(
    bars: list[CorwinSchultzBarPoint],
    *,
    pair: str,
    computed_at_ns: int | None = None,
) -> CorwinSchultzSpreadRecord:
    """Compute Corwin-Schultz spread on the last two ordered bars."""

    if len(bars) < 2:
        raise ValueError("at least 2 bars are required")
    for previous, current in zip(bars, bars[1:]):
        if current.timestamp_ns < previous.timestamp_ns:
            raise ValueError("bars must be non-decreasing in timestamp_ns")
    eval_time_ns = bars[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < bars[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest bar timestamp")

    recent_bars = bars[-2:]
    first, second = recent_bars
    log_range_first = _log_range(first)
    log_range_second = _log_range(second)
    beta = (log_range_first ** 2) + (log_range_second ** 2)
    two_day_high = max(first.high_price, second.high_price)
    two_day_low = min(first.low_price, second.low_price)
    gamma = log(two_day_high / two_day_low) ** 2
    alpha = (
        ((sqrt(2.0 * beta) - sqrt(beta)) / _CS_DENOMINATOR)
        - sqrt(gamma / _CS_DENOMINATOR)
    )
    spread = 2.0 * (exp(alpha) - 1.0) / (1.0 + exp(alpha))
    observed_window_seconds = (
        recent_bars[-1].timestamp_ns - recent_bars[0].timestamp_ns
    ) / 1_000_000_000.0
    return CorwinSchultzSpreadRecord(
        value=max(0.0, spread),
        beta=beta,
        gamma=gamma,
        alpha=alpha,
        low_sample_confidence=True,
        n_events_received=len(bars),
        window_used=(2, observed_window_seconds),
        n_events_used=2,
        method_version_hash=CORWIN_SCHULTZ_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair, recent_bars),
    )


__all__ = [
    "CORWIN_SCHULTZ_METHOD_VERSION",
    "CORWIN_SCHULTZ_METHOD_VERSION_HASH",
    "CorwinSchultzBarPoint",
    "CorwinSchultzSpreadRecord",
    "compute_corwin_schultz_spread",
]
