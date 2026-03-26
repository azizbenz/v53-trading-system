"""
6.5.2 — Timestamp Enricher: add recv_time, transport exchange_time, compute drift.

Invariant: every enriched event has recv_time. Drift is explicit when computable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .schema_mapper import NormalizedEvent


class TimestampEnrichment(BaseModel, frozen=True):
    """Result of timestamp enrichment."""

    recv_time: float
    exchange_time: float | None = None
    drift_s: float | None = None  # recv_time - exchange_time (if both available)
    latency_s: float | None = None  # alias for drift when positive


def compute_drift(recv_time: float, exchange_time: float | None) -> float | None:
    """Compute clock drift between local reception and exchange timestamp.

    Lat_u = t_recv,u - t_exch,u
    """
    if exchange_time is None:
        return None
    return recv_time - exchange_time


def enrich_timestamp(
    event: NormalizedEvent,
    now: float | None = None,
) -> TimestampEnrichment:
    """Produce timestamp enrichment data for an event.

    Uses event's recv_time and exchange_time. Optionally computes
    additional latency relative to 'now'.
    """
    drift = compute_drift(event.recv_time, event.exchange_time)

    latency = None
    if now is not None:
        latency = now - event.recv_time

    return TimestampEnrichment(
        recv_time=event.recv_time,
        exchange_time=event.exchange_time,
        drift_s=drift,
        latency_s=latency,
    )
