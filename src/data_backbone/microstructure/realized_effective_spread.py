"""
V5.3 - REALIZED / EFFECTIVE SPREAD
Canonical live execution spread diagnostics.
"""

from __future__ import annotations

from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from interface_contracts.domain_types import Side


REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION = "realized_effective_spread.live.v1"
REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH = sha256(
    REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION.encode("utf-8")
).hexdigest()
DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS = 300.0


class LiveSpreadObservation(BaseModel):
    """Single execution observation for quoted/effective/realized spread diagnostics."""

    timestamp_ns: int = Field(..., ge=1)
    bid_price: float = Field(..., gt=0.0)
    ask_price: float = Field(..., gt=0.0)
    execution_price: float = Field(..., gt=0.0)
    side: Side
    future_mid_price: float = Field(..., gt=0.0)
    future_mid_timestamp_ns: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def _validate_book(self) -> "LiveSpreadObservation":
        if self.ask_price < self.bid_price:
            raise ValueError("ask_price must be >= bid_price")
        return self


class RealizedEffectiveSpreadRecord(BaseModel):
    """Audit-ready quoted/effective/realized spread record."""

    quoted_spread: float = Field(..., ge=0.0)
    effective_spread: float = Field(..., ge=0.0)
    realized_spread: float
    midpoint: float = Field(..., gt=0.0)
    future_midpoint: float = Field(..., gt=0.0)
    realized_horizon_seconds: float = Field(..., gt=0.0)
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


def _hash_input(pair: str, observation: LiveSpreadObservation) -> str:
    payload = {
        "pair": pair,
        "observation": observation.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_realized_effective_spread(
    observation: LiveSpreadObservation,
    *,
    pair: str,
    realized_horizon_seconds: float = DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS,
    computed_at_ns: int | None = None,
) -> RealizedEffectiveSpreadRecord:
    """Compute quoted, effective, and realized spread for one execution observation."""

    if realized_horizon_seconds <= 0.0:
        raise ValueError("realized_horizon_seconds must be > 0")
    midpoint = (observation.bid_price + observation.ask_price) / 2.0
    direction = 1.0 if observation.side is Side.BUY else -1.0
    quoted_spread = observation.ask_price - observation.bid_price
    effective_spread = 2.0 * abs(observation.execution_price - midpoint)
    realized_spread = 2.0 * direction * (
        observation.execution_price - observation.future_mid_price
    )
    eval_floor_ns = (
        observation.future_mid_timestamp_ns
        if observation.future_mid_timestamp_ns is not None
        else observation.timestamp_ns
    )
    eval_time_ns = eval_floor_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < eval_floor_ns:
        raise ValueError("computed_at_ns must be >= latest timestamp used")
    observed_horizon_seconds = realized_horizon_seconds
    derived_input_warning: str | None = None
    if observation.future_mid_timestamp_ns is not None:
        observed_horizon_seconds = (
            observation.future_mid_timestamp_ns - observation.timestamp_ns
        ) / 1_000_000_000.0
    else:
        derived_input_warning = "future_mid_timestamp_ns_not_provided"
    return RealizedEffectiveSpreadRecord(
        quoted_spread=quoted_spread,
        effective_spread=effective_spread,
        realized_spread=realized_spread,
        midpoint=midpoint,
        future_midpoint=observation.future_mid_price,
        realized_horizon_seconds=observed_horizon_seconds,
        derived_input_warning=derived_input_warning,
        window_used=(1, observed_horizon_seconds),
        n_events_used=1,
        method_version_hash=REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair, observation),
    )


__all__ = [
    "REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION",
    "REALIZED_EFFECTIVE_SPREAD_METHOD_VERSION_HASH",
    "DEFAULT_REALIZED_SPREAD_HORIZON_SECONDS",
    "LiveSpreadObservation",
    "RealizedEffectiveSpreadRecord",
    "compute_realized_effective_spread",
]
