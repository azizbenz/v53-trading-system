"""
V5.3 - HAWKES INTENSITY
Canonical univariate exponential-kernel Hawkes intensity evaluator.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import exp

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HAWKES_METHOD_VERSION = "hawkes_intensity.exponential_univariate.v1"
HAWKES_METHOD_VERSION_HASH = sha256(HAWKES_METHOD_VERSION.encode("utf-8")).hexdigest()
DEFAULT_HAWKES_WINDOW_EVENTS = 1000


class HawkesParameterEstimate(BaseModel):
    """Estimated Hawkes parameters from an external calibration step."""

    mu: float = Field(..., ge=0.0)
    alpha: float = Field(..., ge=0.0)
    beta: float = Field(..., gt=0.0)
    estimation_source: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("estimation_source")
    @classmethod
    def _normalize_source(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("estimation_source must not be blank")
        return normalized


class HawkesEventPoint(BaseModel):
    """Observed event time used by the intensity evaluator."""

    timestamp_ns: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")


class HawkesIntensityRecord(BaseModel):
    """Audit-ready Hawkes intensity result."""

    value: float = Field(..., ge=0.0)
    branching_ratio: float = Field(..., ge=0.0)
    partial_window: bool = False
    low_sample_confidence: bool = False
    parameter_warning: str | None = None
    parameter_source: str = Field(..., min_length=1)
    n_events_received: int = Field(..., ge=1)
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
    pair: str,
    estimate: HawkesParameterEstimate,
    events: list[HawkesEventPoint],
    computed_at_ns: int,
) -> str:
    payload = {
        "pair": pair,
        "computed_at_ns": computed_at_ns,
        "estimate": estimate.model_dump(),
        "events": [event.timestamp_ns for event in events],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def compute_hawkes_intensity(
    estimate: HawkesParameterEstimate,
    events: list[HawkesEventPoint],
    *,
    pair: str,
    window_events: int = DEFAULT_HAWKES_WINDOW_EVENTS,
    computed_at_ns: int | None = None,
) -> HawkesIntensityRecord:
    """Evaluate lambda(t) = mu + sum alpha * exp(-beta * dt)."""

    if len(events) < 1:
        raise ValueError("at least 1 event is required")
    if window_events < 1:
        raise ValueError("window_events must be >= 1")
    for previous, current in zip(events, events[1:]):
        if current.timestamp_ns <= previous.timestamp_ns:
            raise ValueError("events must be strictly ordered by timestamp_ns")

    resolved_window = min(window_events, len(events))
    recent_events = events[-resolved_window:]
    eval_time_ns = recent_events[-1].timestamp_ns if computed_at_ns is None else computed_at_ns
    if eval_time_ns < recent_events[-1].timestamp_ns:
        raise ValueError("computed_at_ns must be >= latest event timestamp")

    intensity = estimate.mu
    for event in recent_events:
        dt_seconds = (eval_time_ns - event.timestamp_ns) / 1_000_000_000.0
        intensity += estimate.alpha * exp(-estimate.beta * dt_seconds)

    branching_ratio = estimate.alpha / estimate.beta
    parameter_warning: str | None = None
    if branching_ratio >= 1.0:
        parameter_warning = "supercritical_branching_ratio"
    elif branching_ratio >= 0.95:
        parameter_warning = "near_critical_branching_ratio"

    observed_window_seconds = (
        recent_events[-1].timestamp_ns - recent_events[0].timestamp_ns
    ) / 1_000_000_000.0
    return HawkesIntensityRecord(
        value=intensity,
        branching_ratio=branching_ratio,
        partial_window=resolved_window < window_events,
        low_sample_confidence=resolved_window < 5,
        parameter_warning=parameter_warning,
        parameter_source=estimate.estimation_source,
        n_events_received=len(events),
        window_used=(resolved_window, observed_window_seconds),
        n_events_used=resolved_window,
        method_version_hash=HAWKES_METHOD_VERSION_HASH,
        pair=pair,
        computed_at_ns=eval_time_ns,
        input_data_hash=_hash_input(pair, estimate, recent_events, eval_time_ns),
    )


__all__ = [
    "DEFAULT_HAWKES_WINDOW_EVENTS",
    "HAWKES_METHOD_VERSION",
    "HAWKES_METHOD_VERSION_HASH",
    "HawkesEventPoint",
    "HawkesIntensityRecord",
    "HawkesParameterEstimate",
    "compute_hawkes_intensity",
]
