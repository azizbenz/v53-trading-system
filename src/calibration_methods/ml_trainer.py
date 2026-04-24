"""LAB_ONLY LightGBM trainer for the bounded V5.3 ML confidence layer."""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import math
import random
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from calibration_methods.ks_test import compute_ks_2sample
from interface_contracts.ml_model_artifact import MlModelArtifact, MlModelDriftBaseline, MlModelWindow


class MlTrainerError(RuntimeError):
    """Base error for the LAB_ONLY ML trainer."""


class MlTrainerDependencyError(MlTrainerError):
    """Raised when LightGBM is unavailable for local training."""


class MlTrainerDataError(MlTrainerError):
    """Raised when the provided training dataset is invalid."""


class MlTrainingRow(BaseModel, frozen=True):
    """Single Local-Lab row used for deterministic LightGBM training."""

    timestamp: datetime
    pair: str = Field(..., min_length=1)
    features: dict[str, float]
    target: float

    @field_validator("features")
    @classmethod
    def _validate_features(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("MlTrainingRow features must not be empty")
        normalized: dict[str, float] = {}
        for key, item in value.items():
            if not key.strip():
                raise ValueError("MlTrainingRow feature names must not be blank")
            if not math.isfinite(item):
                raise ValueError("MlTrainingRow feature values must be finite")
            normalized[key] = float(item)
        return normalized

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("MlTrainingRow target must be finite")
        return float(value)


class MlTrainerRequest(BaseModel, frozen=True):
    """LAB_ONLY bounded LightGBM training request."""

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    rows: tuple[MlTrainingRow, ...]
    training_seed: int
    max_optuna_trials: int = 100
    walk_forward_train_days: int = 180
    walk_forward_test_days: int = 30
    bagging_folds: int = 5
    early_stopping_rounds: int = 50
    max_depth: int = 6
    shap_summary_ref: str | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "MlTrainerRequest":
        if len(self.rows) < 10:
            raise ValueError("MlTrainerRequest requires at least 10 rows")
        if self.walk_forward_train_days != 180:
            raise ValueError("MlTrainerRequest requires walk_forward_train_days == 180")
        if self.walk_forward_test_days != 30:
            raise ValueError("MlTrainerRequest requires walk_forward_test_days == 30")
        if self.bagging_folds != 5:
            raise ValueError("MlTrainerRequest requires bagging_folds == 5")
        if self.early_stopping_rounds != 50:
            raise ValueError("MlTrainerRequest requires early_stopping_rounds == 50")
        if self.max_depth != 6:
            raise ValueError("MlTrainerRequest requires max_depth == 6")
        return self


class MlTrainerResult(BaseModel, frozen=True):
    """Final deterministic LightGBM training output."""

    artifact: MlModelArtifact
    train_row_count: int = Field(..., ge=1)
    validation_row_count: int = Field(..., ge=1)
    bagging_folds_used: int = Field(..., ge=1)
    optuna_trials_used: int = Field(..., ge=0)
    best_params: dict[str, float | int | str | bool] = Field(default_factory=dict)


def _load_lightgbm() -> Any:  # noqa: Any
    try:
        return importlib.import_module("lightgbm")
    except ImportError as exc:
        raise MlTrainerDependencyError("lightgbm is required for LAB_ONLY ML training") from exc


def _load_optuna() -> Any | None:  # noqa: Any
    try:
        return importlib.import_module("optuna")
    except ImportError:
        return None


def _hash_json_payload(payload: Any) -> str:  # noqa: Any
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _resolve_feature_names(rows: tuple[MlTrainingRow, ...]) -> tuple[str, ...]:
    feature_names = tuple(sorted(rows[0].features))
    if not feature_names:
        raise MlTrainerDataError("MlTrainerRequest requires non-empty features")
    for row in rows:
        if tuple(sorted(row.features)) != feature_names:
            raise MlTrainerDataError("MlTrainerRequest feature schemas must match across rows")
    return feature_names


def _dataset_hash(rows: tuple[MlTrainingRow, ...]) -> str:
    return _hash_json_payload(
        [
            {
                "timestamp": row.timestamp.isoformat(),
                "pair": row.pair,
                "features": row.features,
                "target": row.target,
            }
            for row in sorted(rows, key=lambda item: (item.timestamp, item.pair))
        ]
    )


def _feature_hash(feature_names: tuple[str, ...]) -> str:
    return _hash_json_payload(list(feature_names))


def _split_walk_forward(
    rows: tuple[MlTrainingRow, ...],
    *,
    train_days: int,
    validation_days: int,
) -> tuple[tuple[MlTrainingRow, ...], tuple[MlTrainingRow, ...], MlModelWindow, MlModelWindow]:
    sorted_rows = tuple(sorted(rows, key=lambda row: row.timestamp))
    validation_end = sorted_rows[-1].timestamp
    validation_start = validation_end - timedelta(days=validation_days - 1)
    train_start = validation_start - timedelta(days=train_days)
    train_rows = tuple(
        row for row in sorted_rows if train_start <= row.timestamp < validation_start
    )
    validation_rows = tuple(
        row for row in sorted_rows if validation_start <= row.timestamp <= validation_end
    )
    if not train_rows:
        raise MlTrainerDataError("MlTrainerRequest produced an empty 180d train window")
    if not validation_rows:
        raise MlTrainerDataError("MlTrainerRequest produced an empty 30d validation window")
    return (
        train_rows,
        validation_rows,
        MlModelWindow(start_at=train_rows[0].timestamp, end_at=train_rows[-1].timestamp),
        MlModelWindow(start_at=validation_rows[0].timestamp, end_at=validation_rows[-1].timestamp),
    )


def _rows_to_matrix(
    rows: tuple[MlTrainingRow, ...],
    feature_names: tuple[str, ...],
) -> tuple[list[list[float]], list[float]]:
    matrix = [[float(row.features[name]) for name in feature_names] for row in rows]
    targets = [float(row.target) for row in rows]
    return matrix, targets


def _bootstrap_bags(
    row_count: int,
    *,
    folds: int,
    seed: int,
) -> tuple[tuple[int, ...], ...]:
    if row_count < 2:
        raise MlTrainerDataError("MlTrainerRequest requires at least two training rows")
    bag_size = max(1, row_count - 1)
    bags: list[tuple[int, ...]] = []
    for bag_index in range(folds):
        rng = random.Random(seed + bag_index)
        bags.append(tuple(rng.randrange(0, row_count) for _ in range(bag_size)))
    return tuple(bags)


def _strategy_sharpe(predictions: list[float], targets: list[float]) -> float:
    realized = [prediction * target for prediction, target in zip(predictions, targets, strict=True)]
    if len(realized) < 2 or all(value == realized[0] for value in realized):
        return 0.0
    stdev = statistics.pstdev(realized)
    if stdev == 0.0:
        return 0.0
    return statistics.mean(realized) / stdev


def _evaluate_feature_drift(
    train_rows: tuple[MlTrainingRow, ...],
    validation_rows: tuple[MlTrainingRow, ...],
    feature_names: tuple[str, ...],
) -> float:
    pvalues: list[float] = []
    for feature_name in feature_names:
        train_values = [row.features[feature_name] for row in train_rows]
        validation_values = [row.features[feature_name] for row in validation_rows]
        result = compute_ks_2sample(train_values, validation_values)
        pvalues.append(result.p_value)
    return min(pvalues)


def _train_booster(
    lightgbm: Any,  # noqa: Any
    *,
    params: dict[str, Any],  # noqa: Any
    train_matrix: list[list[float]],
    train_targets: list[float],
    valid_matrix: list[list[float]],
    valid_targets: list[float],
    feature_names: tuple[str, ...],
    early_stopping_rounds: int,
) -> Any:  # noqa: Any
    train_set = lightgbm.Dataset(
        train_matrix,
        label=train_targets,
        feature_name=list(feature_names),
        free_raw_data=False,
    )
    valid_set = lightgbm.Dataset(
        valid_matrix,
        label=valid_targets,
        feature_name=list(feature_names),
        free_raw_data=False,
        reference=train_set,
    )
    callbacks: list[Any] = []
    if hasattr(lightgbm, "early_stopping"):
        callbacks.append(lightgbm.early_stopping(early_stopping_rounds))
    return lightgbm.train(
        params,
        train_set,
        num_boost_round=200,
        valid_sets=[valid_set],
        callbacks=callbacks,
    )


def _evaluate_params_with_bagging(
    lightgbm: Any,  # noqa: Any
    *,
    params: dict[str, Any],  # noqa: Any
    train_rows: tuple[MlTrainingRow, ...],
    validation_rows: tuple[MlTrainingRow, ...],
    feature_names: tuple[str, ...],
    bagging_folds: int,
    seed: int,
    early_stopping_rounds: int,
) -> float:
    bags = _bootstrap_bags(len(train_rows), folds=bagging_folds, seed=seed)
    validation_matrix, validation_targets = _rows_to_matrix(validation_rows, feature_names)
    bag_scores: list[float] = []
    for bag in bags:
        bag_rows = tuple(train_rows[index] for index in bag)
        train_matrix, train_targets = _rows_to_matrix(bag_rows, feature_names)
        booster = _train_booster(
            lightgbm,
            params=params,
            train_matrix=train_matrix,
            train_targets=train_targets,
            valid_matrix=validation_matrix,
            valid_targets=validation_targets,
            feature_names=feature_names,
            early_stopping_rounds=early_stopping_rounds,
        )
        predictions = list(booster.predict(validation_matrix))
        bag_scores.append(_strategy_sharpe(predictions, validation_targets))
    return statistics.mean(bag_scores) if bag_scores else 0.0


def _default_lightgbm_params(request: MlTrainerRequest) -> dict[str, Any]:  # noqa: Any
    return {
        "objective": "regression",
        "metric": "l2",
        "verbosity": -1,
        "seed": request.training_seed,
        "feature_fraction_seed": request.training_seed,
        "bagging_seed": request.training_seed,
        "data_random_seed": request.training_seed,
        "max_depth": request.max_depth,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 16,
    }


def _resolve_best_params(
    request: MlTrainerRequest,
    *,
    train_rows: tuple[MlTrainingRow, ...],
    validation_rows: tuple[MlTrainingRow, ...],
    feature_names: tuple[str, ...],
) -> tuple[dict[str, Any], int]:  # noqa: Any
    lightgbm = _load_lightgbm()
    optuna = _load_optuna()
    base_params = _default_lightgbm_params(request)
    trial_count = max(0, min(request.max_optuna_trials, 100))
    if optuna is None or trial_count == 0:
        return base_params, 0

    study = optuna.create_study(direction="maximize")

    def objective(trial: Any) -> float:  # noqa: Any
        params = dict(base_params)
        params["learning_rate"] = trial.suggest_float("learning_rate", 0.01, 0.1)
        params["num_leaves"] = trial.suggest_int("num_leaves", 16, 63)
        params["min_data_in_leaf"] = trial.suggest_int("min_data_in_leaf", 8, 32)
        return _evaluate_params_with_bagging(
            lightgbm,
            params=params,
            train_rows=train_rows,
            validation_rows=validation_rows,
            feature_names=feature_names,
            bagging_folds=request.bagging_folds,
            seed=request.training_seed,
            early_stopping_rounds=request.early_stopping_rounds,
        )

    study.optimize(objective, n_trials=trial_count)
    tuned_params = dict(base_params)
    tuned_params.update(getattr(study, "best_params", {}))
    return tuned_params, trial_count


def train_lightgbm_ml_artifact(
    request: MlTrainerRequest,
) -> MlTrainerResult:
    """Train a deterministic Local-Lab-only LightGBM model and emit its artifact."""

    feature_names = _resolve_feature_names(request.rows)
    dataset_hash = _dataset_hash(request.rows)
    feature_hash = _feature_hash(feature_names)
    train_rows, validation_rows, train_window, validation_window = _split_walk_forward(
        request.rows,
        train_days=request.walk_forward_train_days,
        validation_days=request.walk_forward_test_days,
    )
    best_params, optuna_trials_used = _resolve_best_params(
        request,
        train_rows=train_rows,
        validation_rows=validation_rows,
        feature_names=feature_names,
    )
    lightgbm = _load_lightgbm()
    train_matrix, train_targets = _rows_to_matrix(train_rows, feature_names)
    validation_matrix, validation_targets = _rows_to_matrix(validation_rows, feature_names)
    booster = _train_booster(
        lightgbm,
        params=best_params,
        train_matrix=train_matrix,
        train_targets=train_targets,
        valid_matrix=validation_matrix,
        valid_targets=validation_targets,
        feature_names=feature_names,
        early_stopping_rounds=request.early_stopping_rounds,
    )
    train_predictions = list(booster.predict(train_matrix))
    validation_predictions = list(booster.predict(validation_matrix))
    training_metrics: dict[str, float | int | str | bool] = {
        "optuna_trials_used": optuna_trials_used,
        "bagging_folds_used": request.bagging_folds,
        "train_row_count": len(train_rows),
        "validation_row_count": len(validation_rows),
        "feature_count": len(feature_names),
        "dataset_hash": dataset_hash,
    }
    artifact = MlModelArtifact.create(
        model_family="lightgbm",
        feature_names=feature_names,
        feature_hash=feature_hash,
        pair_universe=tuple(sorted({row.pair for row in request.rows})),
        train_window=train_window,
        validation_window=validation_window,
        oos_sharpe=_strategy_sharpe(validation_predictions, validation_targets),
        backtest_sharpe=_strategy_sharpe(train_predictions, train_targets),
        ks_test_features_pvalue=_evaluate_feature_drift(train_rows, validation_rows, feature_names),
        shadow_diff_pct=None,
        training_seed=request.training_seed,
        created_at=validation_window.end_at.astimezone(UTC),
        calibration_version=request.calibration_version,
        dataset_hash=dataset_hash,
        model_bytes_b64=base64.b64encode(booster.model_to_string().encode("utf-8")).decode("ascii"),
        model_path_ref=None,
        shap_summary_ref=request.shap_summary_ref,
        training_metrics=training_metrics,
        drift_baseline=MlModelDriftBaseline(
            forecast_mean=(statistics.mean(train_predictions) if train_predictions else 0.0),
            win_rate=(
                sum(1 for target in train_targets if target > 0.0) / len(train_targets)
                if train_targets
                else None
            ),
            ce_mean=(statistics.mean(train_targets) if train_targets else 0.0),
            feature_ks_reference_pvalue=None,
            sample_count=len(train_rows),
        ),
        stale_after=validation_window.end_at + timedelta(days=request.walk_forward_test_days),
    )
    return MlTrainerResult(
        artifact=artifact,
        train_row_count=len(train_rows),
        validation_row_count=len(validation_rows),
        bagging_folds_used=request.bagging_folds,
        optuna_trials_used=optuna_trials_used,
        best_params={
            key: value
            for key, value in best_params.items()
            if isinstance(value, (float, int, str, bool))
        },
    )


__all__ = [
    "MlTrainerError",
    "MlTrainerDependencyError",
    "MlTrainerDataError",
    "MlTrainingRow",
    "MlTrainerRequest",
    "MlTrainerResult",
    "train_lightgbm_ml_artifact",
]
