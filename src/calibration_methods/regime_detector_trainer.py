"""LAB_ONLY LightGBM trainer for VPS-shadow LOB RegimeDetectorML artifacts."""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import math
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from calibration_methods.ks_test import compute_ks_2sample
from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorWindow,
    RegimeDurationBucket,
)


class RegimeDetectorTrainerError(RuntimeError):
    """Base error for the LAB_ONLY RegimeDetector trainer."""


class RegimeDetectorTrainerDependencyError(RegimeDetectorTrainerError):
    """Raised when LightGBM is unavailable for Local IA Lab training."""


class RegimeDetectorTrainerDataError(RegimeDetectorTrainerError):
    """Raised when the regime detector training dataset is invalid."""


class RegimeDetectorTrainingRow(BaseModel, frozen=True):
    """Single Local-Lab LOB row for regime-transition classification."""

    timestamp: datetime
    pair: str = Field(..., min_length=1)
    features: dict[str, float]
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    transition_next_window: int = Field(..., ge=0, le=1)
    duration_bucket: RegimeDurationBucket
    toxicity_bucket: Literal["nominal", "elevated", "critical"]

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("RegimeDetectorTrainingRow pair must not be blank")
        return normalized

    @field_validator("features")
    @classmethod
    def _validate_features(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("RegimeDetectorTrainingRow features must not be empty")
        normalized: dict[str, float] = {}
        for key, item in value.items():
            if not key.strip():
                raise ValueError("RegimeDetectorTrainingRow feature names must not be blank")
            if not math.isfinite(item):
                raise ValueError("RegimeDetectorTrainingRow feature values must be finite")
            normalized[key] = float(item)
        return normalized


class RegimeDetectorTrainerRequest(BaseModel, frozen=True):
    """LAB_ONLY bounded LightGBM training request for the LOB RegimeDetector."""

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    rows: tuple[RegimeDetectorTrainingRow, ...]
    training_seed: int
    max_optuna_trials: int = Field(default=100, ge=0, le=100)
    walk_forward_train_days: int = 180
    walk_forward_test_days: int = 30
    bagging_folds: int = 5
    early_stopping_rounds: int = 50
    max_depth: int = 6

    @model_validator(mode="after")
    def validate_request(self) -> "RegimeDetectorTrainerRequest":
        if len(self.rows) < 10:
            raise ValueError("RegimeDetectorTrainerRequest requires at least 10 rows")
        if self.walk_forward_train_days != 180:
            raise ValueError("RegimeDetectorTrainerRequest requires walk_forward_train_days == 180")
        if self.walk_forward_test_days != 30:
            raise ValueError("RegimeDetectorTrainerRequest requires walk_forward_test_days == 30")
        if self.bagging_folds != 5:
            raise ValueError("RegimeDetectorTrainerRequest requires bagging_folds == 5")
        if self.early_stopping_rounds != 50:
            raise ValueError("RegimeDetectorTrainerRequest requires early_stopping_rounds == 50")
        if self.max_depth != 6:
            raise ValueError("RegimeDetectorTrainerRequest requires max_depth == 6")
        return self


class RegimeDetectorTrainerResult(BaseModel, frozen=True):
    """Final deterministic RegimeDetector training output."""

    artifact: RegimeDetectorArtifact
    train_row_count: int = Field(..., ge=1)
    validation_row_count: int = Field(..., ge=1)
    bagging_folds_used: int = Field(..., ge=1)
    optuna_trials_used: int = Field(..., ge=0)
    best_params: dict[str, float | int | str | bool] = Field(default_factory=dict)


def _load_lightgbm() -> Any:  # noqa: Any
    try:
        return importlib.import_module("lightgbm")
    except ImportError as exc:
        raise RegimeDetectorTrainerDependencyError(
            "lightgbm is required for LAB_ONLY RegimeDetector training"
        ) from exc


def _hash_json_payload(payload: Any) -> str:  # noqa: Any
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _resolve_feature_schema(
    rows: tuple[RegimeDetectorTrainingRow, ...],
) -> tuple[tuple[str, ...], RegimeDetectorFeatureSetVersion]:
    feature_names = tuple(rows[0].features)
    if not feature_names:
        raise RegimeDetectorTrainerDataError("RegimeDetectorTrainerRequest requires features")
    feature_set_version = rows[0].feature_set_version
    for row in rows:
        if tuple(row.features) != feature_names:
            raise RegimeDetectorTrainerDataError(
                "RegimeDetectorTrainerRequest feature schemas must match across rows"
            )
        if row.feature_set_version != feature_set_version:
            raise RegimeDetectorTrainerDataError(
                "RegimeDetectorTrainerRequest feature_set_version must stay stable"
            )
    return feature_names, feature_set_version


def _dataset_hash(rows: tuple[RegimeDetectorTrainingRow, ...]) -> str:
    return _hash_json_payload(
        [
            {
                "timestamp": row.timestamp.isoformat(),
                "pair": row.pair,
                "features": row.features,
                "transition_next_window": row.transition_next_window,
                "duration_bucket": row.duration_bucket.value,
                "toxicity_bucket": row.toxicity_bucket,
            }
            for row in sorted(rows, key=lambda item: (item.timestamp, item.pair))
        ]
    )


def _split_walk_forward(
    rows: tuple[RegimeDetectorTrainingRow, ...],
    *,
    train_days: int,
    validation_days: int,
) -> tuple[
    tuple[RegimeDetectorTrainingRow, ...],
    tuple[RegimeDetectorTrainingRow, ...],
    RegimeDetectorWindow,
    RegimeDetectorWindow,
]:
    sorted_rows = tuple(sorted(rows, key=lambda row: row.timestamp))
    validation_end = sorted_rows[-1].timestamp
    validation_start = validation_end - timedelta(days=validation_days - 1)
    train_start = validation_start - timedelta(days=train_days)
    train_rows = tuple(row for row in sorted_rows if train_start <= row.timestamp < validation_start)
    validation_rows = tuple(
        row for row in sorted_rows if validation_start <= row.timestamp <= validation_end
    )
    if not train_rows:
        raise RegimeDetectorTrainerDataError("RegimeDetectorRequest produced empty train window")
    if not validation_rows:
        raise RegimeDetectorTrainerDataError("RegimeDetectorRequest produced empty validation window")
    return (
        train_rows,
        validation_rows,
        RegimeDetectorWindow(start_at=train_rows[0].timestamp, end_at=train_rows[-1].timestamp),
        RegimeDetectorWindow(
            start_at=validation_rows[0].timestamp,
            end_at=validation_rows[-1].timestamp,
        ),
    )


def _rows_to_matrix(
    rows: tuple[RegimeDetectorTrainingRow, ...],
    feature_names: tuple[str, ...],
) -> tuple[list[list[float]], list[int]]:
    matrix = [[float(row.features[name]) for name in feature_names] for row in rows]
    targets = [int(row.transition_next_window) for row in rows]
    return matrix, targets


def _default_params(request: RegimeDetectorTrainerRequest) -> dict[str, Any]:  # noqa: Any
    return {
        "objective": "binary",
        "metric": "binary_logloss",
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


def _train_booster(
    lightgbm: Any,  # noqa: Any
    *,
    params: dict[str, Any],  # noqa: Any
    train_matrix: list[list[float]],
    train_targets: list[int],
    valid_matrix: list[list[float]],
    valid_targets: list[int],
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


def _binary_accuracy(predictions: list[float], targets: list[int]) -> float:
    if not predictions:
        return 0.0
    correct = sum(
        1
        for prediction, target in zip(predictions, targets, strict=True)
        if int(prediction >= 0.5) == target
    )
    return correct / len(predictions)


def _brier_score(predictions: list[float], targets: list[int]) -> float:
    if not predictions:
        return 0.0
    return statistics.fmean(
        (float(prediction) - float(target)) ** 2
        for prediction, target in zip(predictions, targets, strict=True)
    )


def _feature_ks_min_pvalue(
    train_rows: tuple[RegimeDetectorTrainingRow, ...],
    validation_rows: tuple[RegimeDetectorTrainingRow, ...],
    feature_names: tuple[str, ...],
) -> float:
    pvalues: list[float] = []
    for feature_name in feature_names:
        train_values = [row.features[feature_name] for row in train_rows]
        validation_values = [row.features[feature_name] for row in validation_rows]
        pvalues.append(compute_ks_2sample(train_values, validation_values).p_value)
    return min(pvalues) if pvalues else 0.0


def train_lightgbm_regime_detector_artifact(
    request: RegimeDetectorTrainerRequest,
) -> RegimeDetectorTrainerResult:
    """Train a Local-Lab-only LightGBM classifier and emit a RegimeDetector artifact."""

    feature_names, feature_set_version = _resolve_feature_schema(request.rows)
    train_rows, validation_rows, train_window, validation_window = _split_walk_forward(
        request.rows,
        train_days=request.walk_forward_train_days,
        validation_days=request.walk_forward_test_days,
    )
    lightgbm = _load_lightgbm()
    train_matrix, train_targets = _rows_to_matrix(train_rows, feature_names)
    validation_matrix, validation_targets = _rows_to_matrix(validation_rows, feature_names)
    best_params = _default_params(request)
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
    validation_predictions = [float(value) for value in booster.predict(validation_matrix)]
    dataset_hash = _dataset_hash(request.rows)
    feature_hash = _hash_json_payload(
        {
            "feature_set_version": feature_set_version.value,
            "feature_names": list(feature_names),
        }
    )
    oos_metrics: dict[str, float | int | str | bool] = {
        "transition_accuracy": _binary_accuracy(validation_predictions, validation_targets),
        "transition_brier_score": _brier_score(validation_predictions, validation_targets),
        "validation_positive_rate": statistics.fmean(validation_targets),
        "feature_ks_min_pvalue": _feature_ks_min_pvalue(train_rows, validation_rows, feature_names),
        "train_row_count": len(train_rows),
        "validation_row_count": len(validation_rows),
        "feature_count": len(feature_names),
        "optuna_trials_used": 0,
        "bagging_folds_used": request.bagging_folds,
    }
    artifact = RegimeDetectorArtifact.create(
        model_family="lightgbm",
        feature_set_version=feature_set_version,
        feature_names=feature_names,
        feature_hash=feature_hash,
        pair_universe=tuple(sorted({row.pair for row in request.rows})),
        train_window=train_window,
        validation_window=validation_window,
        regime_labels=("calm", "transition", "toxic"),
        duration_bucket_scheme=tuple(RegimeDurationBucket),
        oos_metrics=oos_metrics,
        shadow_metrics={},
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=request.training_seed,
        created_at=validation_window.end_at.astimezone(UTC),
        calibration_version=request.calibration_version,
        dataset_hash=dataset_hash,
        model_bytes_b64=base64.b64encode(booster.model_to_string().encode("utf-8")).decode("ascii"),
        stale_after=validation_window.end_at + timedelta(days=request.walk_forward_test_days),
    )
    return RegimeDetectorTrainerResult(
        artifact=artifact,
        train_row_count=len(train_rows),
        validation_row_count=len(validation_rows),
        bagging_folds_used=request.bagging_folds,
        optuna_trials_used=0,
        best_params={key: value for key, value in best_params.items() if isinstance(value, (float, int, str, bool))},
    )


__all__ = [
    "RegimeDetectorTrainerError",
    "RegimeDetectorTrainerDependencyError",
    "RegimeDetectorTrainerDataError",
    "RegimeDetectorTrainingRow",
    "RegimeDetectorTrainerRequest",
    "RegimeDetectorTrainerResult",
    "train_lightgbm_regime_detector_artifact",
]
