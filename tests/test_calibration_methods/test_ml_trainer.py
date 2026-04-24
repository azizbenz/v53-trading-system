from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from calibration_methods import (
    MlTrainerDataError,
    MlTrainerRequest,
    MlTrainingRow,
    train_lightgbm_ml_artifact,
)


def _rows() -> tuple[MlTrainingRow, ...]:
    start = datetime(2025, 8, 25, tzinfo=UTC)
    rows: list[MlTrainingRow] = []
    for index in range(240):
        timestamp = start + timedelta(days=index)
        feature_a = ((index % 10) - 5) / 10.0
        feature_b = ((index * 3) % 14) / 10.0
        target = 0.25 * feature_a - 0.12 * feature_b + ((index % 7) - 3) / 50.0
        rows.append(
            MlTrainingRow(
                timestamp=timestamp,
                pair="BTCUSDT" if index % 2 == 0 else "ETHUSDT",
                features={"feature_a": feature_a, "feature_b": feature_b},
                target=target,
            )
        )
    return tuple(rows)


def _request(*, seed: int = 17, max_optuna_trials: int = 150) -> MlTrainerRequest:
    return MlTrainerRequest(
        artifact_id="ml-artifact-1",
        calibration_version="cal.v1",
        rows=_rows(),
        training_seed=seed,
        max_optuna_trials=max_optuna_trials,
    )


def _fake_lightgbm_module() -> SimpleNamespace:
    class FakeDataset:
        def __init__(
            self,
            data: list[list[float]],
            *,
            label: list[float],
            feature_name: list[str],
            free_raw_data: bool,
            reference: object | None = None,
        ) -> None:
            self.data = data
            self.label = label
            self.feature_name = feature_name
            self.free_raw_data = free_raw_data
            self.reference = reference

    class FakeBooster:
        def __init__(self, *, params: dict[str, float | int | str | bool]) -> None:
            self.params = params

        def predict(self, matrix: list[list[float]]) -> list[float]:
            learning_rate = float(self.params["learning_rate"])
            num_leaves = float(self.params["num_leaves"])
            min_data_in_leaf = float(self.params["min_data_in_leaf"])
            bias = learning_rate + (num_leaves / 200.0) - (min_data_in_leaf / 500.0)
            return [
                (sum(row) / len(row)) + bias + ((index % 5) - 2) / 50.0
                for index, row in enumerate(matrix)
            ]

        def model_to_string(self) -> str:
            return json.dumps({"params": self.params}, sort_keys=True)

    def train(
        params: dict[str, float | int | str | bool],
        train_set: FakeDataset,
        *,
        num_boost_round: int,
        valid_sets: list[FakeDataset],
        callbacks: list[object],
    ) -> FakeBooster:
        assert num_boost_round == 200
        assert callbacks
        assert valid_sets
        return FakeBooster(params=params)

    def early_stopping(rounds: int) -> dict[str, int]:
        return {"rounds": rounds}

    return SimpleNamespace(Dataset=FakeDataset, train=train, early_stopping=early_stopping)


def _fake_optuna_module() -> SimpleNamespace:
    class FakeTrial:
        def __init__(self, number: int) -> None:
            self.number = number
            self.params: dict[str, float | int] = {}

        def suggest_float(self, name: str, low: float, high: float) -> float:
            span = high - low
            value = low + span * ((self.number % 5) / 4.0)
            self.params[name] = value
            return value

        def suggest_int(self, name: str, low: int, high: int) -> int:
            value = low + (self.number % (high - low + 1))
            self.params[name] = value
            return value

    class FakeStudy:
        def __init__(self) -> None:
            self.best_params: dict[str, float | int] = {}

        def optimize(self, objective: Callable[[FakeTrial], float], n_trials: int) -> None:
            best_value: float | None = None
            for number in range(n_trials):
                trial = FakeTrial(number)
                value = float(objective(trial))
                if best_value is None or value > best_value:
                    best_value = value
                    self.best_params = dict(trial.params)

    def create_study(*, direction: str) -> FakeStudy:
        assert direction == "maximize"
        return FakeStudy()

    return SimpleNamespace(create_study=create_study)


def test_ml_trainer_is_deterministic_for_same_seed_and_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("calibration_methods.ml_trainer._load_lightgbm", _fake_lightgbm_module)
    monkeypatch.setattr("calibration_methods.ml_trainer._load_optuna", _fake_optuna_module)
    request = _request(seed=23)

    first = train_lightgbm_ml_artifact(request)
    second = train_lightgbm_ml_artifact(request)

    assert first.artifact.artifact_hash == second.artifact.artifact_hash
    assert first.artifact.model_bytes_b64 == second.artifact.model_bytes_b64
    assert first.best_params == second.best_params


def test_ml_trainer_populates_artifact_fields_and_respects_walk_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("calibration_methods.ml_trainer._load_lightgbm", _fake_lightgbm_module)
    monkeypatch.setattr("calibration_methods.ml_trainer._load_optuna", _fake_optuna_module)

    result = train_lightgbm_ml_artifact(_request())

    assert result.artifact.model_family.value == "lightgbm"
    assert len(result.artifact.artifact_hash) == 64
    assert len(result.artifact.dataset_hash) == 64
    assert result.artifact.training_metrics["feature_count"] == 2
    assert result.train_row_count == 180
    assert result.validation_row_count == 30
    assert result.artifact.train_window.end_at < result.artifact.validation_window.start_at
    assert result.optuna_trials_used == 100


def test_ml_trainer_rejects_invalid_dataset_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("calibration_methods.ml_trainer._load_lightgbm", _fake_lightgbm_module)
    monkeypatch.setattr("calibration_methods.ml_trainer._load_optuna", _fake_optuna_module)
    rows = list(_rows())
    rows[-1] = rows[-1].model_copy(update={"features": {"feature_a": 1.0}})
    request = MlTrainerRequest(
        artifact_id="ml-artifact-2",
        calibration_version="cal.v1",
        rows=tuple(rows),
        training_seed=17,
    )

    with pytest.raises(MlTrainerDataError, match="feature schemas must match"):
        train_lightgbm_ml_artifact(request)


def test_ml_training_row_rejects_empty_features() -> None:
    with pytest.raises(ValidationError, match="features must not be empty"):
        MlTrainingRow(
            timestamp=datetime(2026, 4, 22, tzinfo=UTC),
            pair="BTCUSDT",
            features={},
            target=0.1,
        )
