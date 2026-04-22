"""Tests for injected websocket ingestion used by the Shadow VPS service."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from local_replay_runtime import load_historical_snapshot_batch
from protocols import build_snapshot_batch_from_injected_websocket_stream


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_websocket_ingest_tests", label)


def test_injected_websocket_stream_builds_snapshot_batch_and_ignores_heartbeat():
    output_dir = _scratch_dir("snapshot_batch")
    try:
        stream_path = output_dir / "websocket_stream.jsonl"
        stream_path.write_text(
            "\n".join(
                (
                    json.dumps(
                        {
                            "endpoint": "wss://shadow.injected",
                            "pair": "BTCUSDT",
                            "stream_type": "snapshot",
                            "payload": {
                                "snapshot_type": "ticker",
                                "last_price": 43250.0,
                                "bid": 43249.5,
                                "ask": 43250.5,
                                "volume_24h": 125000.0,
                            },
                            "recv_time": 1700000000.0,
                            "source": "binance",
                            "route_hint": {
                                "route_id": "btc-ws-1",
                                "engine_id": "engine_a",
                                "raw_score": 0.91,
                                "penalized_score": 0.88,
                                "final_score": 0.86,
                                "expected_edge_bps": 17.0,
                                "target_decision_state": "executed",
                                "production_decision_state": "executed",
                                "production_final_score": 0.86,
                                "production_expected_cost": 0.00086,
                                "candidate_size": 1.0,
                                "final_size": 1.0,
                                "gross_return_bps": 21.0,
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "endpoint": "wss://shadow.injected",
                            "pair": "BTCUSDT",
                            "stream_type": "heartbeat",
                            "payload": {"event": "heartbeat"},
                            "recv_time": 1700000001.0,
                            "source": "binance",
                        }
                    ),
                    json.dumps(
                        {
                            "endpoint": "wss://shadow.injected",
                            "pair": "ETHUSDT",
                            "stream_type": "snapshot",
                            "payload": {
                                "snapshot_type": "ticker",
                                "last_price": 2280.0,
                                "bid": 2279.8,
                                "ask": 2280.2,
                                "volume_24h": 98000.0,
                            },
                            "recv_time": 1700000060.0,
                            "source": "binance",
                            "route_hint": {
                                "route_id": "eth-ws-1",
                                "engine_id": "engine_b",
                                "raw_score": 0.81,
                                "penalized_score": 0.79,
                                "final_score": 0.76,
                                "expected_edge_bps": 7.0,
                                "ranking_position": 3,
                                "target_decision_state": "rejected_ranking",
                                "production_decision_state": "rejected_ranking",
                                "production_final_score": 0.76,
                                "production_expected_cost": 0.00094,
                                "primary_reason": "rank_cutoff",
                                "gross_return_bps": -4.0,
                            },
                        }
                    ),
                )
            ),
            encoding="utf-8",
        )
        snapshot_batch_path = output_dir / "websocket_snapshot_batch.json"
        summary_path = output_dir / "websocket_snapshot_ingest.json"

        result = build_snapshot_batch_from_injected_websocket_stream(
            stream_path,
            snapshot_batch_path=snapshot_batch_path,
            summary_path=summary_path,
        )
        batch = load_historical_snapshot_batch(snapshot_batch_path)

        assert result.emitted_message_count == 3
        assert result.accepted_message_count == 2
        assert result.ignored_message_count == 1
        assert result.rejected_message_count == 0
        assert result.route_count == 2
        assert batch.event_count == 2
        assert batch.route_scope == ("btc-ws-1", "eth-ws-1")
        assert batch.event_types == ("snapshot",)
        assert batch.pair_scope == ("BTCUSDT", "ETHUSDT")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
