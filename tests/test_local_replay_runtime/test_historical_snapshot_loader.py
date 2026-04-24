"""Tests for loading raw historical snapshot batches."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

from local_replay_runtime import load_historical_snapshot_batch
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("historical_snapshot_loader_tests", label)


def test_load_historical_snapshot_batch_reads_typed_market_events():
    scratch = _scratch_dir("snapshot_batch")
    snapshot_path = scratch / "snapshot_batch.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "event_type": "snapshot",
                        "event": {
                            "timestamp_ms": 1_700_000_000_000,
                            "pair": "BTCUSDT",
                            "last_price": 43250.0,
                            "bid": 43249.5,
                            "ask": 43250.5,
                            "volume_24h": 1200000.0,
                        },
                        "route_hint": {
                            "route_id": "route-btc-1",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "expected_edge_bps": 18.0,
                        },
                    },
                    {
                        "event_type": "kline",
                        "event": {
                            "timestamp_ms": 1_700_000_060_000,
                            "pair": "BTCUSDT",
                            "timeframe": "1m",
                            "open_price": 43240.0,
                            "high_price": 43280.0,
                            "low_price": 43230.0,
                            "close_price": 43270.0,
                            "volume": 250.0,
                        },
                        "route_hint": {
                            "route_id": "route-btc-1",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "expected_edge_bps": 18.0,
                        },
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        batch = load_historical_snapshot_batch(snapshot_path)

        assert batch.event_count == 2
        assert batch.pair_scope == ("BTCUSDT",)
        assert batch.route_scope == ("route-btc-1",)
        assert batch.event_types == ("kline", "snapshot")
        assert batch.events[0].event_type == "snapshot"
        assert batch.events[1].event_type == "kline"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
