from __future__ import annotations

import pytest

from interface_contracts import (
    RegimeDetectorLabelConfig,
    RegimeDetectorFeatureSetVersion,
    RegimeDurationBucket,
    RegimeToxicityBucket,
)
from local_replay_runtime import HistoricalSnapshotBatch, build_regime_detector_training_dataset

_BASE_TS_MS = 1_700_000_000_000


def _depth_record(
    timestamp_ms: int,
    *,
    bid_best_size: float,
    ask_best_size: float,
) -> dict[str, object]:
    return {
        "event_type": "depth",
        "event": {
            "timestamp_ms": _BASE_TS_MS + timestamp_ms,
            "pair": "BTCUSDT",
            "bids": [
                {"price": 100.0, "quantity": bid_best_size},
                {"price": 99.9, "quantity": 20.0},
                {"price": 99.8, "quantity": 15.0},
            ],
            "asks": [
                {"price": 100.1, "quantity": ask_best_size},
                {"price": 100.2, "quantity": 20.0},
                {"price": 100.3, "quantity": 15.0},
            ],
        },
        "route_hint": {
            "route_id": "btc-route-1",
            "engine_id": "engine_a",
        },
    }


def _trade_record(
    timestamp_ms: int,
    *,
    side: str,
    price: float,
    quantity: float,
    trade_id: str,
) -> dict[str, object]:
    return {
        "event_type": "trade",
        "event": {
            "timestamp_ms": _BASE_TS_MS + timestamp_ms,
            "pair": "BTCUSDT",
            "price": price,
            "quantity": quantity,
            "side": side,
            "trade_id": trade_id,
            "is_maker": False,
        },
        "route_hint": {
            "route_id": "btc-route-1",
            "engine_id": "engine_a",
        },
    }


def _batch_with_regime_shift() -> HistoricalSnapshotBatch:
    return HistoricalSnapshotBatch.from_records(
        source_path="build/tests/regime_detector_batch.json",
        records=(
            _depth_record(1_000, bid_best_size=120.0, ask_best_size=20.0),
            _depth_record(2_000, bid_best_size=115.0, ask_best_size=20.0),
            _trade_record(2_500, side="sell", price=100.0, quantity=60.0, trade_id="t-1"),
            _depth_record(3_000, bid_best_size=110.0, ask_best_size=22.0),
            _depth_record(4_000, bid_best_size=22.0, ask_best_size=145.0),
            _depth_record(5_000, bid_best_size=18.0, ask_best_size=6.0),
            _depth_record(6_000, bid_best_size=17.0, ask_best_size=5.0),
            _depth_record(7_000, bid_best_size=16.0, ask_best_size=5.0),
        ),
        source="historical_snapshot_batch",
    )


def test_regime_detector_dataset_builder_emits_future_microstructure_labels() -> None:
    dataset = build_regime_detector_training_dataset(
        _batch_with_regime_shift(),
        label_config=RegimeDetectorLabelConfig(
            current_window_seconds=2.0,
            future_window_seconds=2.0,
            max_future_steps=2,
            touch_eps_bps=10.0,
        ),
    )

    sample = next(
        item
        for item in dataset.samples
        if item.anchor_timestamp_ns == (_BASE_TS_MS + 3_000) * 1_000_000
    )

    assert dataset.label_policy == "lob_future_regime_state.v1"
    assert dataset.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert sample.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert sample.transition_next_window == 1
    assert sample.toxicity_bucket in {
        RegimeToxicityBucket.ELEVATED,
        RegimeToxicityBucket.CRITICAL,
    }
    assert sample.duration_bucket in {
        RegimeDurationBucket.FRAGILE,
        RegimeDurationBucket.SHORT,
    }
    assert "real_wall_score_bid" in sample.feature_values
    assert "deceptive_liquidity_score" in sample.feature_values
    assert "observation_coverage_ratio" in sample.feature_values
    assert sample.future_steps_observed >= 1


def test_regime_detector_dataset_builder_fails_closed_without_future_window() -> None:
    batch = HistoricalSnapshotBatch.from_records(
        source_path="build/tests/regime_detector_batch_short.json",
        records=(
            _depth_record(1_000, bid_best_size=100.0, ask_best_size=20.0),
            _depth_record(2_000, bid_best_size=95.0, ask_best_size=21.0),
        ),
        source="historical_snapshot_batch",
    )

    with pytest.raises(ValueError, match="No eligible regime-detector training samples"):
        build_regime_detector_training_dataset(
            batch,
            label_config=RegimeDetectorLabelConfig(
                current_window_seconds=2.0,
                future_window_seconds=2.0,
                max_future_steps=2,
            ),
        )
