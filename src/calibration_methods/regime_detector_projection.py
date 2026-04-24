"""Projection from Local-Lab regime datasets into trainer rows."""

from __future__ import annotations

from datetime import UTC, datetime

from calibration_methods.regime_detector_trainer import RegimeDetectorTrainingRow
from calibration_methods.regime_detector_feature_calibration import (
    RegimeDetectorFeatureProfile,
    resolve_regime_detector_feature_set,
)
from interface_contracts import RegimeDetectorDatasetSample, RegimeDetectorTrainingDataset


def _resolve_selected_feature_names(
    *,
    available_feature_names: tuple[str, ...],
    selected_feature_names: tuple[str, ...] | None,
    feature_profile: RegimeDetectorFeatureProfile | None,
) -> tuple[str, ...]:
    if selected_feature_names is not None and feature_profile is not None:
        raise ValueError("selected_feature_names and feature_profile are mutually exclusive")
    if selected_feature_names is not None:
        return selected_feature_names
    if feature_profile is not None:
        return resolve_regime_detector_feature_set(feature_profile)
    return available_feature_names


def project_regime_detector_training_row(
    sample: RegimeDetectorDatasetSample,
    *,
    selected_feature_names: tuple[str, ...] | None = None,
    feature_profile: RegimeDetectorFeatureProfile | None = None,
) -> RegimeDetectorTrainingRow:
    """Project one regime dataset sample into the trainer row contract."""

    feature_names = _resolve_selected_feature_names(
        available_feature_names=sample.feature_names,
        selected_feature_names=selected_feature_names,
        feature_profile=feature_profile,
    )
    missing = tuple(feature_id for feature_id in feature_names if feature_id not in sample.feature_values)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing regime training feature(s): {joined}")
    return RegimeDetectorTrainingRow(
        timestamp=datetime.fromtimestamp(sample.anchor_timestamp_ns / 1_000_000_000, tz=UTC),
        pair=sample.pair,
        features={feature_id: sample.feature_values[feature_id] for feature_id in feature_names},
        feature_set_version=sample.feature_set_version,
        transition_next_window=sample.transition_next_window,
        duration_bucket=sample.duration_bucket,
        toxicity_bucket=sample.toxicity_bucket.value,
    )


def project_regime_detector_training_rows(
    dataset: RegimeDetectorTrainingDataset,
    *,
    selected_feature_names: tuple[str, ...] | None = None,
    feature_profile: RegimeDetectorFeatureProfile | None = None,
) -> tuple[RegimeDetectorTrainingRow, ...]:
    """Project all dataset samples into trainer rows with a stable feature schema."""

    feature_names = _resolve_selected_feature_names(
        available_feature_names=dataset.feature_names,
        selected_feature_names=selected_feature_names,
        feature_profile=feature_profile,
    )
    return tuple(
        project_regime_detector_training_row(
            sample,
            selected_feature_names=feature_names,
        )
        for sample in dataset.samples
    )


__all__ = [
    "project_regime_detector_training_row",
    "project_regime_detector_training_rows",
]
