from __future__ import annotations

from types import SimpleNamespace

import pytest

from calibration_methods import (
    REGIME_DETECTOR_EXTENDED_V2_FEATURES,
)
from interface_contracts import RegimeDetectorFeatureSetVersion
from local_replay_runtime import (
    HistoricalSnapshotBatch,
    build_local_lab_regime_detector_artifact_training_report,
)

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
                {"price": 99.7, "quantity": 12.0},
                {"price": 99.6, "quantity": 10.0},
            ],
            "asks": [
                {"price": 100.1, "quantity": ask_best_size},
                {"price": 100.2, "quantity": 20.0},
                {"price": 100.3, "quantity": 15.0},
                {"price": 100.4, "quantity": 12.0},
                {"price": 100.5, "quantity": 10.0},
            ],
        },
        "route_hint": {"route_id": "btc-route-1", "engine_id": "engine_a"},
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
        "route_hint": {"route_id": "btc-route-1", "engine_id": "engine_a"},
    }


def _batch_with_regime_shift() -> HistoricalSnapshotBatch:
    records: list[dict[str, object]] = []
    for offset in range(0, 260):
        day_base_ms = 1_000 + (offset * 86_400_000)
        transition = offset % 3 == 0
        records.extend(
            (
                _depth_record(
                    day_base_ms + 1_000,
                    bid_best_size=120.0,
                    ask_best_size=20.0,
                ),
                _depth_record(
                    day_base_ms + 2_000,
                    bid_best_size=115.0,
                    ask_best_size=20.0,
                ),
                _depth_record(
                    day_base_ms + 3_000,
                    bid_best_size=110.0,
                    ask_best_size=22.0,
                ),
                _depth_record(
                    day_base_ms + 4_000,
                    bid_best_size=22.0 if transition else 105.0,
                    ask_best_size=145.0 if transition else 24.0,
                ),
                _depth_record(
                    day_base_ms + 5_000,
                    bid_best_size=18.0 if transition else 100.0,
                    ask_best_size=6.0 if transition else 25.0,
                ),
                _depth_record(
                    day_base_ms + 6_000,
                    bid_best_size=17.0 if transition else 98.0,
                    ask_best_size=5.0 if transition else 26.0,
                ),
                _depth_record(
                    day_base_ms + 7_000,
                    bid_best_size=16.0 if transition else 96.0,
                    ask_best_size=5.0 if transition else 26.0,
                ),
            )
        )
        if transition:
            records.append(
                _trade_record(
                    day_base_ms + 2_500,
                    side="sell",
                    price=100.0,
                    quantity=60.0,
                    trade_id=f"t-{offset}",
                )
            )
    return HistoricalSnapshotBatch.from_records(
        source_path="build/tests/local_lab_regime_detector_batch.json",
        records=tuple(records),
        source="historical_snapshot_batch",
    )


class _FakeDataset:
    def __init__(
        self,
        data: list[list[float]],
        *,
        label: list[int],
        feature_name: list[str],
        free_raw_data: bool,
        reference: object | None = None,
    ) -> None:
        self.data = data
        self.label = label
        self.feature_name = feature_name
        self.free_raw_data = free_raw_data
        self.reference = reference


class _FakeBooster:
    def __init__(self, params: dict[str, object]) -> None:
        self.params = params

    def predict(self, matrix: list[list[float]]) -> list[float]:
        return [0.8 if sum(row) > 1.0 else 0.2 for row in matrix]

    def model_to_string(self) -> str:
        return "fake-regime-detector-model-v2"


def _fake_lightgbm() -> SimpleNamespace:
    def train(
        params: dict[str, object],
        train_set: _FakeDataset,
        *,
        num_boost_round: int,
        valid_sets: list[_FakeDataset],
        callbacks: list[object],
    ) -> _FakeBooster:
        assert params["objective"] == "binary"
        assert num_boost_round == 200
        assert valid_sets
        assert callbacks
        assert train_set.feature_name
        return _FakeBooster(params)

    return SimpleNamespace(
        Dataset=_FakeDataset,
        early_stopping=lambda rounds: ("early_stopping", rounds),
        train=train,
    )


def test_local_lab_regime_detector_training_report_uses_extended_v2_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "calibration_methods.regime_detector_trainer.importlib.import_module",
        lambda name: _fake_lightgbm() if name == "lightgbm" else None,
    )

    report = build_local_lab_regime_detector_artifact_training_report(
        batch=_batch_with_regime_shift(),
        artifact_id="regime-detector-v2",
        calibration_version="lob-regime.v2",
        training_seed=17,
        feature_profile="extended_v2",
        max_optuna_trials=0,
    )

    assert report.ready is True
    assert report.status == "trained"
    assert report.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert report.feature_profile == "extended_v2"
    assert report.selected_feature_names == REGIME_DETECTOR_EXTENDED_V2_FEATURES
    assert report.selected_feature_count == len(REGIME_DETECTOR_EXTENDED_V2_FEATURES)
    assert report.artifact is not None
    assert report.artifact.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert report.artifact.feature_names == REGIME_DETECTOR_EXTENDED_V2_FEATURES


def test_local_lab_regime_detector_training_report_fails_closed_on_missing_samples() -> None:
    batch = HistoricalSnapshotBatch.from_records(
        source_path="build/tests/local_lab_regime_detector_batch_short.json",
        records=(
            _depth_record(1_000, bid_best_size=100.0, ask_best_size=20.0),
            _depth_record(2_000, bid_best_size=95.0, ask_best_size=21.0),
        ),
        source="historical_snapshot_batch",
    )

    report = build_local_lab_regime_detector_artifact_training_report(
        batch=batch,
        artifact_id="regime-detector-v2",
        calibration_version="lob-regime.v2",
        training_seed=17,
    )

    assert report.ready is False
    assert report.status == "dataset_unavailable"
