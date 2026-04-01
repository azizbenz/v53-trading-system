"""
6.5.2 - Timestamp Enricher: add recv_time, transport exchange_time, compute drift.

Invariant: every enriched event has recv_time. Drift is explicit when computable.
"""

from __future__ import annotations

import time as _time

from pydantic import BaseModel

from .schema_mapper import NormalizedEvent

DEFAULT_MAX_LATENCY_S = 60.0


class TimestampEnrichment(BaseModel, frozen=True):
    """Result of timestamp enrichment."""

    recv_time: float
    exchange_time: float | None = None
    drift_s: float | None = None
    latency_s: float | None = None


def compute_drift(recv_time: float, exchange_time: float | None) -> float | None:
    """Compute clock drift between local reception and exchange timestamp."""
    if exchange_time is None:
        return None
    return recv_time - exchange_time


def monotonic_now() -> float:
    """Canonical monotonic clock for Build-2 latency measurements."""
    return _time.monotonic()


def compute_latency(
    recv_time: float,
    now: float,
    *,
    max_latency_s: float = DEFAULT_MAX_LATENCY_S,
) -> float | None:
    """Compute latency while filtering negative or aberrant values."""
    latency = now - recv_time
    if latency < 0:
        return None
    if latency > max_latency_s:
        return None
    return latency


def enrich_timestamp(
    event: NormalizedEvent,
    now: float | None = None,
    *,
    max_latency_s: float = DEFAULT_MAX_LATENCY_S,
) -> TimestampEnrichment:
    """Produce timestamp enrichment data for an event."""
    drift = compute_drift(event.recv_time, event.exchange_time)

    latency = None
    if now is not None:
        latency = compute_latency(event.recv_time, now, max_latency_s=max_latency_s)

    return TimestampEnrichment(
        recv_time=event.recv_time,
        exchange_time=event.exchange_time,
        drift_s=drift,
        latency_s=latency,
    )
