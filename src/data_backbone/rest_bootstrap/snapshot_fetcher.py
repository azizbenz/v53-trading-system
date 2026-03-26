"""
5.5.1 — Snapshot Fetcher: retrieve initial snapshots via REST.
5.5.4 — Snapshot Age Validator: reject stale snapshots.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SnapshotStatus(StrEnum):
    VALID = "valid"
    TOO_OLD = "too_old"
    FETCH_ERROR = "fetch_error"


class Snapshot(BaseModel, frozen=True):
    """A fetched REST snapshot with age tracking."""

    pair: str
    data_type: str  # "orderbook" | "trades" | "ticker"
    payload: dict
    fetch_time: float
    exchange_time: float | None = None
    age_s: float = 0.0
    status: SnapshotStatus = SnapshotStatus.VALID


def validate_snapshot_age(
    snapshot: Snapshot,
    max_age_s: float,
    now: float,
) -> Snapshot:
    """Validate a snapshot's age. Mark as TOO_OLD if stale.

    Spec: Δ_snap = t_now - t_snapshot ≤ Δ_snap,max.
    """
    ref_time = snapshot.exchange_time if snapshot.exchange_time else snapshot.fetch_time
    age = now - ref_time

    if age > max_age_s:
        return Snapshot(
            pair=snapshot.pair,
            data_type=snapshot.data_type,
            payload=snapshot.payload,
            fetch_time=snapshot.fetch_time,
            exchange_time=snapshot.exchange_time,
            age_s=age,
            status=SnapshotStatus.TOO_OLD,
        )
    return Snapshot(
        pair=snapshot.pair,
        data_type=snapshot.data_type,
        payload=snapshot.payload,
        fetch_time=snapshot.fetch_time,
        exchange_time=snapshot.exchange_time,
        age_s=age,
        status=SnapshotStatus.VALID,
    )
