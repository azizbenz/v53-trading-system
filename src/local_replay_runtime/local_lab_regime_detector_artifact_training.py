"""Governed Local-IA-Lab RegimeDetector artifact training from historical LOB events."""

from __future__ import annotations

from pydantic import BaseModel, Field

from calibration_methods import (
    RegimeDetectorFeatureProfile,
    RegimeDetectorTrainerDataError,
    RegimeDetectorTrainerDependencyError,
    RegimeDetectorTrainerRequest,
    RegimeDetectorTrainerResult,
    project_regime_detector_training_rows,
)
from interface_contracts import (
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorLabelConfig,
    RegimeDetectorTrainingDataset,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch
from local_replay_runtime.regime_detector_dataset_builder import (
    build_regime_detector_training_dataset,
)
from calibration_methods.regime_detector_feature_calibration import (
    resolve_regime_detector_feature_set,
)
from calibration_methods.regime_detector_trainer import (
    train_lightgbm_regime_detector_artifact,
)


class LocalLabRegimeDetectorArtifactTrainingReport(BaseModel, frozen=True):
    """Audit-ready Local-Lab regime-detector training result."""

    dataset_id: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    ready: bool = False
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    feature_profile: str = Field(..., min_length=1)
    sample_count: int = Field(default=0, ge=0)
    training_row_count: int = Field(default=0, ge=0)
    selected_feature_count: int = Field(default=0, ge=0)
    selected_feature_names: tuple[str, ...] = ()
    pair_scope: tuple[str, ...] = ()
    artifact: RegimeDetectorArtifact | None = None
    artifact_hash: str | None = None
    blocking_reasons: tuple[str, ...] = ()


def _failed_report(
    *,
    dataset_id: str,
    feature_set_version: RegimeDetectorFeatureSetVersion,
    feature_profile: RegimeDetectorFeatureProfile,
    sample_count: int,
    pair_scope: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
    status: str,
) -> LocalLabRegimeDetectorArtifactTrainingReport:
    return LocalLabRegimeDetectorArtifactTrainingReport(
        dataset_id=dataset_id,
        status=status,
        feature_set_version=feature_set_version,
        feature_profile=feature_profile,
        sample_count=sample_count,
        pair_scope=pair_scope,
        blocking_reasons=blocking_reasons,
    )


def _build_trainer_request(
    *,
    artifact_id: str,
    calibration_version: str,
    dataset: RegimeDetectorTrainingDataset,
    training_seed: int,
    feature_profile: RegimeDetectorFeatureProfile,
    max_optuna_trials: int,
) -> tuple[RegimeDetectorTrainerRequest, tuple[str, ...]]:
    selected_feature_names = resolve_regime_detector_feature_set(feature_profile)
    rows = project_regime_detector_training_rows(
        dataset,
        feature_profile=feature_profile,
    )
    return (
        RegimeDetectorTrainerRequest(
            artifact_id=artifact_id,
            calibration_version=calibration_version,
            rows=rows,
            training_seed=training_seed,
            max_optuna_trials=max_optuna_trials,
        ),
        selected_feature_names,
    )


def build_local_lab_regime_detector_artifact_training_report(
    *,
    batch: HistoricalSnapshotBatch,
    artifact_id: str,
    calibration_version: str,
    training_seed: int,
    dataset_id: str | None = None,
    label_config: RegimeDetectorLabelConfig | None = None,
    pair_scope: tuple[str, ...] | None = None,
    feature_profile: RegimeDetectorFeatureProfile = "extended_v2",
    max_optuna_trials: int = 100,
) -> LocalLabRegimeDetectorArtifactTrainingReport:
    """Train a bounded Local-Lab RegimeDetector artifact from governed LOB history."""

    try:
        dataset = build_regime_detector_training_dataset(
            batch,
            dataset_id=dataset_id,
            label_config=label_config,
            pair_scope=pair_scope,
        )
    except ValueError as exc:
        resolved_dataset_id = dataset_id or batch.source_path
        return _failed_report(
            dataset_id=resolved_dataset_id,
            feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
            feature_profile=feature_profile,
            sample_count=0,
            pair_scope=pair_scope or (),
            blocking_reasons=(str(exc),),
            status="dataset_unavailable",
        )

    try:
        request, selected_feature_names = _build_trainer_request(
            artifact_id=artifact_id,
            calibration_version=calibration_version,
            dataset=dataset,
            training_seed=training_seed,
            feature_profile=feature_profile,
            max_optuna_trials=max_optuna_trials,
        )
        result = train_lightgbm_regime_detector_artifact(request)
    except (RegimeDetectorTrainerDependencyError, RegimeDetectorTrainerDataError, ValueError) as exc:
        return _failed_report(
            dataset_id=dataset.dataset_id,
            feature_set_version=dataset.feature_set_version,
            feature_profile=feature_profile,
            sample_count=len(dataset.samples),
            pair_scope=dataset.pair_scope,
            blocking_reasons=(str(exc),),
            status="training_failed",
        )

    return LocalLabRegimeDetectorArtifactTrainingReport(
        dataset_id=dataset.dataset_id,
        status="trained",
        ready=True,
        feature_set_version=dataset.feature_set_version,
        feature_profile=feature_profile,
        sample_count=len(dataset.samples),
        training_row_count=result.train_row_count + result.validation_row_count,
        selected_feature_count=len(selected_feature_names),
        selected_feature_names=selected_feature_names,
        pair_scope=dataset.pair_scope,
        artifact=result.artifact,
        artifact_hash=result.artifact.artifact_hash,
    )


__all__ = [
    "LocalLabRegimeDetectorArtifactTrainingReport",
    "build_local_lab_regime_detector_artifact_training_report",
]
