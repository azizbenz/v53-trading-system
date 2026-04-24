"""LAB_ONLY projection from ML backtest contracts into trainer-ready rows."""

from __future__ import annotations

from datetime import UTC, datetime

from calibration_methods.ml_trainer import MlTrainingRow
from interface_contracts import (
    MlBacktestTrainingDataset,
    MlBacktestTrainingSample,
)


def project_ml_training_row_from_ml_backtest_sample(
    sample: MlBacktestTrainingSample,
    *,
    include_route_features: bool = True,
) -> MlTrainingRow:
    """Project one governed ML backtest sample into a trainer-ready row."""

    return MlTrainingRow(
        timestamp=datetime.fromtimestamp(sample.timestamp_ms / 1000.0, tz=UTC),
        pair=sample.pair,
        features=sample.trainer_feature_values(include_route_features=include_route_features),
        target=sample.target_return_fraction,
    )


def project_ml_training_rows_from_backtest_dataset(
    dataset: MlBacktestTrainingDataset,
    *,
    include_route_features: bool = True,
) -> tuple[MlTrainingRow, ...]:
    """Project governed ML backtest dataset contracts into trainer-ready rows."""

    return tuple(
        project_ml_training_row_from_ml_backtest_sample(
            sample,
            include_route_features=include_route_features,
        )
        for sample in dataset.samples
    )


__all__ = [
    "project_ml_training_row_from_ml_backtest_sample",
    "project_ml_training_rows_from_backtest_dataset",
]
