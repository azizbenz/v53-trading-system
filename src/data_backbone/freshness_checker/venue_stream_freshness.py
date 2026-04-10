"""Bounded freshness hook for venue websocket streams."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VenueStreamFreshnessStatus(BaseModel, frozen=True):
    """Freshness view for a single venue stream."""

    age_s: float = Field(..., ge=0.0)
    stale_threshold_s: float = Field(..., ge=0.0)
    is_stale: bool = False
    reason: str = ""


def evaluate_venue_stream_freshness(
    *,
    last_update_time: float | None,
    now: float,
    stale_threshold_s: float,
) -> VenueStreamFreshnessStatus:
    """Evaluate websocket freshness without mutating runtime state."""

    if stale_threshold_s < 0.0:
        raise ValueError("stale_threshold_s must be >= 0")
    if last_update_time is None:
        return VenueStreamFreshnessStatus(
            age_s=0.0,
            stale_threshold_s=stale_threshold_s,
            is_stale=True,
            reason="no_message_yet",
        )
    age_s = max(0.0, now - last_update_time)
    return VenueStreamFreshnessStatus(
        age_s=age_s,
        stale_threshold_s=stale_threshold_s,
        is_stale=age_s > stale_threshold_s,
        reason="heartbeat_silent" if age_s > stale_threshold_s else "",
    )


__all__ = ["VenueStreamFreshnessStatus", "evaluate_venue_stream_freshness"]
