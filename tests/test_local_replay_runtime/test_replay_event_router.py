"""Tests for routing raw historical events into replay opportunities."""

from __future__ import annotations

from local_replay_runtime import (
    HistoricalSnapshotBatch,
    route_snapshot_batch_to_dataset,
)


def _snapshot_batch() -> HistoricalSnapshotBatch:
    return HistoricalSnapshotBatch.from_records(
        source_path="inmemory://raw_events",
        records=(
            {
                "event_type": "snapshot",
                "event": {
                    "timestamp_ms": 1_700_000_000_000,
                    "pair": "BTCUSDT",
                    "last_price": 43250.0,
                    "bid": 43249.0,
                    "ask": 43251.0,
                    "volume_24h": 1200000.0,
                    "funding_rate": 0.0001,
                },
                "route_hint": {
                    "route_id": "route-btc-1",
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
                    "feature_values": {"custom_signal": 1.0},
                },
            },
            {
                "event_type": "depth",
                "event": {
                    "timestamp_ms": 1_700_000_000_000,
                    "pair": "BTCUSDT",
                    "bids": [{"price": 43249.0, "quantity": 1.2}],
                    "asks": [{"price": 43251.0, "quantity": 1.1}],
                },
                "route_hint": {
                    "route_id": "route-btc-1",
                    "engine_id": "engine_a",
                    "raw_score": 0.91,
                    "expected_edge_bps": 17.0,
                },
            },
            {
                "event_type": "trade",
                "event": {
                    "timestamp_ms": 1_700_000_030_000,
                    "pair": "BTCUSDT",
                    "price": 43250.5,
                    "quantity": 0.25,
                    "side": "buy",
                    "trade_id": "trade-1",
                    "is_maker": False,
                },
                "route_hint": {
                    "route_id": "route-btc-1",
                    "engine_id": "engine_a",
                    "raw_score": 0.91,
                    "expected_edge_bps": 17.0,
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
            },
        ),
    )


def test_route_snapshot_batch_to_dataset_materializes_replay_opportunity():
    dataset = route_snapshot_batch_to_dataset(
        _snapshot_batch(),
        dataset_id="dataset-routed-1",
    )

    assert dataset.record_count == 1
    assert dataset.rows[0].pair == "BTCUSDT"
    assert dataset.rows[0].engine_id == "engine_a"
    assert dataset.rows[0].close_price == 43270.0
    assert dataset.rows[0].spread_bps > 0.0
    assert dataset.rows[0].feature_values["custom_signal"] == 1.0
    assert dataset.rows[0].feature_values["snapshot_last_price"] == 43250.0
    assert dataset.rows[0].feature_values["kline_close_price"] == 43270.0
