from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from calibration_methods.regime_detector_trainer import (
    RegimeDetectorTrainerRequest,
    RegimeDetectorTrainingRow,
    train_lightgbm_regime_detector_artifact,
)
from interface_contracts import RegimeDurationBucket
from interface_contracts import RegimeDetectorFeatureSetVersion


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
        return "fake-regime-detector-model-v1"


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
        assert params["max_depth"] == 6
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


def _rows() -> tuple[RegimeDetectorTrainingRow, ...]:
    start = datetime(2025, 8, 1, tzinfo=UTC)
    rows: list[RegimeDetectorTrainingRow] = []
    for index in range(220):
        transition = int(index % 3 == 0)
        rows.append(
            RegimeDetectorTrainingRow(
                timestamp=start + timedelta(days=index),
                pair="BTCUSDT",
                features={
                    "spread_bps": float(index % 5) / 10.0,
                    "order_book_imbalance": 0.8 if transition else -0.2,
                    "spoof_like_suspicion_bid": 0.7 if transition else 0.1,
                    "observation_coverage_ratio": 0.9 if transition else 0.6,
                },
                feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
                transition_next_window=transition,
                duration_bucket=(
                    RegimeDurationBucket.SHORT
                    if transition
                    else RegimeDurationBucket.PERSISTENT
                ),
                toxicity_bucket="elevated" if transition else "nominal",
            )
        )
    return tuple(rows)


def _request(seed: int = 17) -> RegimeDetectorTrainerRequest:
    return RegimeDetectorTrainerRequest(
        artifact_id="regime-detector-v1",
        calibration_version="lob-regime.v1",
        rows=_rows(),
        training_seed=seed,
        max_optuna_trials=0,
    )


def test_regime_detector_trainer_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "calibration_methods.regime_detector_trainer.importlib.import_module",
        lambda name: _fake_lightgbm() if name == "lightgbm" else None,
    )

    first = train_lightgbm_regime_detector_artifact(_request())
    second = train_lightgbm_regime_detector_artifact(_request())

    assert first.artifact == second.artifact
    assert first.artifact.output_semantics == "lob_regime_detector.v1"
    assert first.artifact.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert first.artifact.oos_metrics["optuna_trials_used"] == 0
    assert first.artifact.shadow_metrics == {}
    assert first.train_row_count > 0
    assert first.validation_row_count > 0


def test_regime_detector_trainer_rejects_feature_schema_drift() -> None:
    rows = list(_rows())
    rows[-1] = rows[-1].model_copy(update={"features": {"spread_bps": 1.0}})
    request = RegimeDetectorTrainerRequest(
        artifact_id="regime-detector-v1",
        calibration_version="lob-regime.v1",
        rows=tuple(rows),
        training_seed=17,
        max_optuna_trials=0,
    )

    with pytest.raises(Exception, match="feature schemas"):
        train_lightgbm_regime_detector_artifact(request)


def test_regime_detector_trainer_rejects_feature_set_version_drift() -> None:
    rows = list(_rows())
    rows[-1] = rows[-1].model_copy(
        update={"feature_set_version": RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1}
    )
    request = RegimeDetectorTrainerRequest(
        artifact_id="regime-detector-v1",
        calibration_version="lob-regime.v2",
        rows=tuple(rows),
        training_seed=17,
        max_optuna_trials=0,
    )

    with pytest.raises(Exception, match="feature_set_version"):
        train_lightgbm_regime_detector_artifact(request)


def test_regime_detector_trainer_enforces_optuna_trial_cap() -> None:
    with pytest.raises(ValueError):
        RegimeDetectorTrainerRequest(
            artifact_id="regime-detector-v1",
            calibration_version="lob-regime.v1",
            rows=_rows(),
            training_seed=17,
            max_optuna_trials=101,
        )
