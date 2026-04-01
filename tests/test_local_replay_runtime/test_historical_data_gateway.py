"""Tests for the historical dataset gateway used by LOCAL_REPLAY."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from local_replay_runtime import build_feature_bridge_payload, load_historical_replay_dataset


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "historical_data_gateway_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_load_historical_replay_dataset_normalizes_and_sorts_records():
    scratch = _scratch_dir("json")
    dataset_path = scratch / "sample_dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "opportunity_id": "later",
                        "timestamp_ms": 1_700_000_060_000,
                        "pair": "ETHUSDT",
                        "engine_id": "engine_b",
                        "raw_score": 0.7,
                        "feature_values": {"spread_bps": 4.0},
                    },
                    {
                        "opportunity_id": "earlier",
                        "timestamp_ms": 1_700_000_000_000,
                        "pair": "BTCUSDT",
                        "engine_id": "engine_a",
                        "raw_score": 0.8,
                        "feature_values": {"spread_bps": 3.0, "imbalance": 0.2},
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        dataset = load_historical_replay_dataset(dataset_path)
        payload = build_feature_bridge_payload(dataset)

        assert dataset.dataset_id == "sample_dataset"
        assert dataset.rows[0].opportunity_id == "earlier"
        assert dataset.record_count == 2
        assert dataset.pair_scope == ("BTCUSDT", "ETHUSDT")
        assert dataset.engine_scope == ("engine_a", "engine_b")
        assert payload["bridge_status"] == "ok"
        assert payload["rows_with_features"] == 2
        assert payload["feature_keys"] == ["imbalance", "spread_bps"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
