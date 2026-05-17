from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cockpit.state import read_pair_selector
from cockpit.state_data_quality import read_data_quality_live

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir, write_json


def test_data_quality_marks_fresh_snapshot_ok() -> None:
    scratch = scratch_dir("data_quality_ok")
    try:
        paths = build_paths(scratch)
        capture_dir = paths.service_dir.parent / "live_captures" / "2026-04-27"
        capture_dir.mkdir(parents=True, exist_ok=True)
        now_ms = int(datetime.now(tz=UTC).timestamp() * 1000.0)
        write_json(
            capture_dir / "live_websocket_snapshot_batch.json",
            [
                {
                    "event_type": "snapshot",
                    "event": {
                        "timestamp_ms": now_ms,
                        "pair": "BTCUSDT",
                        "last_price": 10.0,
                        "bid": 9.9,
                        "ask": 10.1,
                    },
                }
            ],
        )
        write_json(capture_dir / "live_time_sync_offsets.json", {"time_sync_offsets_ms": [10.0]})
        snapshot = read_data_quality_live(paths, pairs=read_pair_selector(paths))
        assert snapshot.pairs[0].status == "ok"
    finally:
        cleanup_scratch(scratch)


def test_data_quality_marks_stale_and_missing_depth() -> None:
    scratch = scratch_dir("data_quality_stale")
    try:
        paths = build_paths(scratch)
        capture_dir = paths.service_dir.parent / "live_captures" / "2026-04-27"
        capture_dir.mkdir(parents=True, exist_ok=True)
        old_ms = int((datetime.now(tz=UTC) - timedelta(minutes=10)).timestamp() * 1000.0)
        write_json(
            capture_dir / "live_websocket_snapshot_batch.json",
            [
                {"event_type": "snapshot", "event": {"timestamp_ms": old_ms, "pair": "BTCUSDT", "last_price": 10.0}},
            ],
        )
        snapshot = read_data_quality_live(paths, pairs=read_pair_selector(paths))
        assert snapshot.pairs[0].status == "stale"
    finally:
        cleanup_scratch(scratch)
