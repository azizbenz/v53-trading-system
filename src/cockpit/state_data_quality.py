"""Phase 2.5 adapter - live data freshness, spread, and time-sync visibility."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from statistics import mean
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths, PairSelector


class DataQualityPairRow(BaseModel, frozen=True):
    pair: str = Field(..., min_length=1)
    last_price: float | None = None
    last_trade_timestamp: str | None = None
    age_ms: float | None = None
    spread_bps: float | None = None
    depth_available: bool = False
    ws_gap_seconds: float | None = None
    time_sync_offset_ms: float | None = None
    stale_flag: bool = False
    status: str = "unknown"


class DataQualitySnapshot(OperationalSourceSnapshot):
    pairs: tuple[DataQualityPairRow, ...] = ()


def read_data_quality_live(
    paths: CockpitPaths,
    *,
    pairs: PairSelector,
) -> DataQualitySnapshot:
    """Read pair-level live data quality from the latest snapshot batch."""

    capture_root = paths.snapshot_batch
    snapshot_path = _latest_capture_file(capture_root, "live_websocket_snapshot_batch.json")
    if snapshot_path is None or not snapshot_path.is_file():
        return DataQualitySnapshot(
            source_status="missing",
            source_file=str(snapshot_path) if snapshot_path is not None else None,
            last_modified_at=None,
            age_seconds=None,
            reason_codes=("live_snapshot_batch_missing",),
            pairs=tuple(
                DataQualityPairRow(pair=pair, status="unknown") for pair in pairs.configured_pairs
            ),
        )
    stamp = source_stamp(path=snapshot_path, stale_after_seconds=300.0)
    time_sync_path = _latest_capture_file(capture_root, "live_time_sync_offsets.json")
    offsets = _read_time_sync_offsets(time_sync_path)
    stale_after_ms = _stale_threshold_ms(paths)
    payload = _read_snapshot_batch(snapshot_path)
    rows = []
    for pair in pairs.configured_pairs:
        rows.append(_pair_row(pair, payload, offsets, stale_after_ms))
    reason_codes = list(stamp["reason_codes"])
    if not offsets:
        reason_codes.append("time_sync_offsets_missing")
    return DataQualitySnapshot(
        source_status=stamp["source_status"],
        source_file=str(snapshot_path),
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        pairs=tuple(rows),
    )


def _pair_row(
    pair: str,
    payload: list[dict[str, object]],
    offsets: list[float],
    stale_after_ms: float,
) -> DataQualityPairRow:
    events = [row for row in payload if _pair_name(row) == pair]
    if not events:
        return DataQualityPairRow(pair=pair, status="unknown")
    latest = max(events, key=lambda row: _timestamp_ms(row))
    timestamps = sorted((_timestamp_ms(row) for row in events if _timestamp_ms(row) is not None))
    latest_ts = timestamps[-1] if timestamps else None
    previous_ts = timestamps[-2] if len(timestamps) >= 2 else None
    age_ms = None
    if latest_ts is not None:
        age_ms = max((datetime.now(tz=UTC).timestamp() * 1000.0) - latest_ts, 0.0)
    bid = _float(_nested(latest, "event", "bid"))
    ask = _float(_nested(latest, "event", "ask"))
    spread_bps = _compute_spread_bps(bid, ask)
    if spread_bps is None:
        spread_bps = _float(_nested(latest, "route_hint", "feature_values", "spread_bps"))
    depth_available = bid is not None and ask is not None
    stale_flag = bool(age_ms is not None and age_ms > stale_after_ms)
    if stale_flag:
        status = "stale"
    elif not depth_available:
        status = "missing_depth"
    else:
        status = "ok"
    latest_price = _float(_nested(latest, "event", "last_price"))
    if latest_price is None:
        latest_price = _float(_nested(latest, "event", "price"))
    return DataQualityPairRow(
        pair=pair,
        last_price=latest_price,
        last_trade_timestamp=_iso_ms(latest_ts),
        age_ms=age_ms,
        spread_bps=spread_bps,
        depth_available=depth_available,
        ws_gap_seconds=((latest_ts - previous_ts) / 1000.0 if latest_ts and previous_ts else None),
        time_sync_offset_ms=(mean(offsets) if offsets else None),
        stale_flag=stale_flag,
        status=status,
    )


def _compute_spread_bps(bid: float | None, ask: float | None) -> float | None:
    if bid is None or ask is None:
        return None
    mid = (bid + ask) / 2.0
    if mid <= 0:
        return None
    return ((ask - bid) / mid) * 10000.0


def _pair_name(row: dict[str, object]) -> str:
    return str(_nested(row, "event", "pair") or _nested(row, "event", "symbol") or "")


def _timestamp_ms(row: dict[str, object]) -> float | None:
    value = _nested(row, "event", "timestamp_ms")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _nested(payload: dict[str, object], *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso_ms(timestamp_ms: float | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).isoformat()


def _read_snapshot_batch(path: Path) -> list[dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def _latest_capture_file(capture_root: Path, filename: str) -> Path | None:
    if not capture_root.is_dir():
        return None
    candidates: list[Path] = []
    try:
        for directory in capture_root.iterdir():
            if not directory.is_dir():
                continue
            candidate = directory / filename
            if candidate.is_file():
                candidates.append(candidate)
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_time_sync_offsets(path: Path | None) -> list[float]:
    if path is None or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("time_sync_offsets_ms") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    values: list[float] = []
    for item in raw:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            continue
    return values


def _stale_threshold_ms(paths: CockpitPaths) -> float:
    thresholds_path = paths.calibration_thresholds
    if thresholds_path is None or not thresholds_path.is_file():
        return 30_000.0
    try:
        text = thresholds_path.read_text(encoding="utf-8")
    except OSError:
        return 30_000.0
    for line in text.splitlines():
        if "value:" in line and "30.0" in line:
            return 30_000.0
    return 30_000.0


__all__ = ["DataQualityPairRow", "DataQualitySnapshot", "read_data_quality_live"]
