"""Governed Local-Lab ML artifact training from replay/backtest evidence."""

from __future__ import annotations

from pydantic import BaseModel, Field

from calibration_methods import (
    MlTrainerDataError,
    MlTrainerDependencyError,
    MlTrainerRequest,
    MlTrainerResult,
    MlTrainingRow,
    project_ml_training_rows_from_backtest_dataset,
    train_lightgbm_ml_artifact,
)
from interface_contracts import (
    ML_BACKTEST_REALIZED_TARGET_POLICY,
    ML_BACKTEST_TARGET_POLICY,
    MlBacktestTrainingDataset,
    MlModelArtifact,
)
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from local_replay_runtime.local_lab_scope_matrix import LocalLabScopeAnalysisMatrix
from local_replay_runtime.ml_backtest_projection import (
    build_ml_backtest_training_dataset,
    build_ml_backtest_training_dataset_from_replay_and_dtr,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabMlArtifactTrainingReport(BaseModel, frozen=True):
    """Audit-ready Local-Lab ML training result."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    ready: bool = False
    target_policy: str = Field(default=ML_BACKTEST_TARGET_POLICY, min_length=1)
    route_target_fallback_used: bool = False
    replay_sample_count: int = Field(default=0, ge=0)
    aligned_dtr_count: int = Field(default=0, ge=0)
    training_row_count: int = Field(default=0, ge=0)
    recognized_feature_key_count: int = Field(default=0, ge=0)
    pair_scope: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    include_route_features: bool = True
    artifact: MlModelArtifact | None = None
    artifact_hash: str | None = None
    oos_sharpe: float | None = None
    backtest_sharpe: float | None = None
    ks_test_features_pvalue: float | None = None
    best_params: dict[str, float | int | str | bool] = Field(default_factory=dict)
    blocking_reasons: tuple[str, ...] = ()


def build_local_lab_ml_artifact_training_report(
    *,
    correlation_id: str,
    export_dir: str,
    dataset: HistoricalReplayDataset,
    artifact_id: str,
    calibration_version: str,
    training_seed: int,
    dtr_records: tuple[DTRRecord, ...] = (),
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None,
    selected_pair: str | None = None,
    selected_engine_id: str | None = None,
    allowed_feature_keys: tuple[str, ...] | None = None,
    include_route_features: bool = True,
    max_optuna_trials: int = 100,
    shap_summary_ref: str | None = None,
    min_training_rows: int = 10,
) -> LocalLabMlArtifactTrainingReport:
    """Train a bounded Local-Lab ML artifact from governed replay/backtest inputs."""

    prepared_run = _prepare_training_run(
        correlation_id=correlation_id,
        export_dir=export_dir,
        dataset=dataset,
        dtr_records=dtr_records,
        scope_matrix=scope_matrix,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        allowed_feature_keys=allowed_feature_keys,
        include_route_features=include_route_features,
        min_training_rows=min_training_rows,
    )
    if isinstance(prepared_run, LocalLabMlArtifactTrainingReport):
        return prepared_run

    trainer_result = _run_training_request(
        correlation_id=correlation_id,
        export_dir=export_dir,
        artifact_id=artifact_id,
        calibration_version=calibration_version,
        training_seed=training_seed,
        max_optuna_trials=max_optuna_trials,
        shap_summary_ref=shap_summary_ref,
        include_route_features=include_route_features,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        prepared_run=prepared_run,
    )
    if isinstance(trainer_result, LocalLabMlArtifactTrainingReport):
        return trainer_result

    return _build_success_report(
        correlation_id=correlation_id,
        export_dir=export_dir,
        target_policy=prepared_run.ml_dataset.target_policy,
        route_target_fallback_used=prepared_run.route_target_fallback_used,
        scoped_dataset=prepared_run.scoped_context.scoped_dataset,
        scoped_dtr_records=prepared_run.scoped_context.scoped_dtr_records,
        training_rows=prepared_run.training_rows,
        recognized_feature_key_count=len(prepared_run.ml_dataset.recognized_feature_keys),
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        include_route_features=include_route_features,
        result=trainer_result,
    )


class _ScopedTrainingContext(BaseModel, frozen=True):
    scoped_dataset: HistoricalReplayDataset
    scoped_dtr_records: tuple[DTRRecord, ...]


class _PreparedTrainingRun(BaseModel, frozen=True):
    scoped_context: _ScopedTrainingContext
    ml_dataset: MlBacktestTrainingDataset
    route_target_fallback_used: bool
    training_rows: tuple[MlTrainingRow, ...]


def _build_scoped_training_context(
    *,
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> _ScopedTrainingContext | None:
    scoped_rows = _filter_dataset_rows(
        dataset.rows,
        scope_matrix=scope_matrix,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
    )
    if not scoped_rows:
        return None
    scoped_dataset = HistoricalReplayDataset.from_records(
        dataset_id=dataset.dataset_id,
        source_path=dataset.source_path,
        records=scoped_rows,
        source=dataset.source,
    )
    scoped_dtr_records = _filter_dtr_records(
        dtr_records,
        scope_matrix=scope_matrix,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
    )
    return _ScopedTrainingContext(
        scoped_dataset=scoped_dataset,
        scoped_dtr_records=scoped_dtr_records,
    )


def _build_ml_dataset_for_training(
    *,
    scoped_dataset: HistoricalReplayDataset,
    scoped_dtr_records: tuple[DTRRecord, ...],
    allowed_feature_keys: tuple[str, ...] | None,
) -> tuple[MlBacktestTrainingDataset, bool]:
    if scoped_dtr_records:
        return (
            build_ml_backtest_training_dataset_from_replay_and_dtr(
                scoped_dataset,
                scoped_dtr_records,
                allowed_feature_keys=allowed_feature_keys,
            ),
            False,
        )
    return (
        build_ml_backtest_training_dataset(
            scoped_dataset,
            allowed_feature_keys=allowed_feature_keys,
        ),
        True,
    )


def _build_trainer_request(
    *,
    artifact_id: str,
    calibration_version: str,
    training_rows: tuple,
    training_seed: int,
    max_optuna_trials: int,
    shap_summary_ref: str | None,
) -> MlTrainerRequest:
    return MlTrainerRequest(
        artifact_id=artifact_id,
        calibration_version=calibration_version,
        rows=training_rows,
        training_seed=training_seed,
        max_optuna_trials=max_optuna_trials,
        shap_summary_ref=shap_summary_ref,
    )


def _prepare_training_run(
    *,
    correlation_id: str,
    export_dir: str,
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    selected_pair: str | None,
    selected_engine_id: str | None,
    allowed_feature_keys: tuple[str, ...] | None,
    include_route_features: bool,
    min_training_rows: int,
) -> LocalLabMlArtifactTrainingReport | _PreparedTrainingRun:
    scoped_context = _build_scoped_training_context(
        dataset=dataset,
        dtr_records=dtr_records,
        scope_matrix=scope_matrix,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
    )
    if scoped_context is None:
        return LocalLabMlArtifactTrainingReport(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="no_scopes",
            selected_pair=selected_pair,
            selected_engine_id=selected_engine_id,
            blocking_reasons=("NO_SCOPED_REPLAY_ROWS",),
        )

    try:
        ml_dataset, route_target_fallback_used = _build_ml_dataset_for_training(
            scoped_dataset=scoped_context.scoped_dataset,
            scoped_dtr_records=scoped_context.scoped_dtr_records,
            allowed_feature_keys=allowed_feature_keys,
        )
    except ValueError as exc:
        return LocalLabMlArtifactTrainingReport(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="missing_replay_dtr_alignment",
            selected_pair=selected_pair,
            selected_engine_id=selected_engine_id,
            replay_sample_count=scoped_context.scoped_dataset.record_count,
            aligned_dtr_count=0,
            pair_scope=scoped_context.scoped_dataset.pair_scope,
            engine_scope=scoped_context.scoped_dataset.engine_scope,
            blocking_reasons=(str(exc),),
        )

    training_rows = project_ml_training_rows_from_backtest_dataset(
        ml_dataset,
        include_route_features=include_route_features,
    )
    if len(training_rows) < min_training_rows:
        return LocalLabMlArtifactTrainingReport(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status="insufficient_training_rows",
            target_policy=ml_dataset.target_policy,
            route_target_fallback_used=route_target_fallback_used,
            replay_sample_count=scoped_context.scoped_dataset.record_count,
            aligned_dtr_count=len(scoped_context.scoped_dtr_records),
            training_row_count=len(training_rows),
            recognized_feature_key_count=len(ml_dataset.recognized_feature_keys),
            pair_scope=ml_dataset.pair_scope,
            engine_scope=ml_dataset.engine_scope,
            selected_pair=selected_pair,
            selected_engine_id=selected_engine_id,
            include_route_features=include_route_features,
            blocking_reasons=("INSUFFICIENT_TRAINING_ROWS",),
        )

    return _PreparedTrainingRun(
        scoped_context=scoped_context,
        ml_dataset=ml_dataset,
        route_target_fallback_used=route_target_fallback_used,
        training_rows=training_rows,
    )


def _run_training_request(
    *,
    correlation_id: str,
    export_dir: str,
    artifact_id: str,
    calibration_version: str,
    training_seed: int,
    max_optuna_trials: int,
    shap_summary_ref: str | None,
    include_route_features: bool,
    selected_pair: str | None,
    selected_engine_id: str | None,
    prepared_run: _PreparedTrainingRun,
) -> LocalLabMlArtifactTrainingReport | MlTrainerResult:
    request = _build_trainer_request(
        artifact_id=artifact_id,
        calibration_version=calibration_version,
        training_rows=prepared_run.training_rows,
        training_seed=training_seed,
        max_optuna_trials=max_optuna_trials,
        shap_summary_ref=shap_summary_ref,
    )
    try:
        return train_lightgbm_ml_artifact(request)
    except (MlTrainerDependencyError, MlTrainerDataError) as exc:
        status = (
            "trainer_dependency_missing"
            if isinstance(exc, MlTrainerDependencyError)
            else "invalid_training_data"
        )
        return _build_failed_report(
            correlation_id=correlation_id,
            export_dir=export_dir,
            status=status,
            target_policy=prepared_run.ml_dataset.target_policy,
            route_target_fallback_used=prepared_run.route_target_fallback_used,
            scoped_dataset=prepared_run.scoped_context.scoped_dataset,
            scoped_dtr_records=prepared_run.scoped_context.scoped_dtr_records,
            training_rows=prepared_run.training_rows,
            recognized_feature_key_count=len(prepared_run.ml_dataset.recognized_feature_keys),
            selected_pair=selected_pair,
            selected_engine_id=selected_engine_id,
            include_route_features=include_route_features,
            blocking_reasons=(str(exc),),
        )


def _filter_dataset_rows(
    rows: tuple[HistoricalReplayOpportunity, ...],
    *,
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> tuple[HistoricalReplayOpportunity, ...]:
    if scope_matrix is not None and scope_matrix.scopes:
        allowed = {(row.pair, row.engine_id) for row in scope_matrix.scopes}
        rows = tuple(row for row in rows if (row.pair, row.engine_id) in allowed)
    if selected_pair is not None:
        rows = tuple(row for row in rows if row.pair == selected_pair)
    if selected_engine_id is not None:
        rows = tuple(row for row in rows if row.engine_id == selected_engine_id)
    return rows


def _filter_dtr_records(
    records: tuple[DTRRecord, ...],
    *,
    scope_matrix: LocalLabScopeAnalysisMatrix | None,
    selected_pair: str | None,
    selected_engine_id: str | None,
) -> tuple[DTRRecord, ...]:
    filtered = records
    if scope_matrix is not None and scope_matrix.scopes:
        allowed = {(row.pair, row.engine_id) for row in scope_matrix.scopes}
        filtered = tuple(record for record in filtered if (record.pair, record.engine_id) in allowed)
    if selected_pair is not None:
        filtered = tuple(record for record in filtered if record.pair == selected_pair)
    if selected_engine_id is not None:
        filtered = tuple(record for record in filtered if record.engine_id == selected_engine_id)
    return filtered


def _build_failed_report(
    *,
    correlation_id: str,
    export_dir: str,
    status: str,
    target_policy: str,
    route_target_fallback_used: bool,
    scoped_dataset: HistoricalReplayDataset,
    scoped_dtr_records: tuple[DTRRecord, ...],
    training_rows: tuple,
    recognized_feature_key_count: int,
    selected_pair: str | None,
    selected_engine_id: str | None,
    include_route_features: bool,
    blocking_reasons: tuple[str, ...],
) -> LocalLabMlArtifactTrainingReport:
    return LocalLabMlArtifactTrainingReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=status,
        target_policy=target_policy,
        route_target_fallback_used=route_target_fallback_used,
        replay_sample_count=scoped_dataset.record_count,
        aligned_dtr_count=len(scoped_dtr_records),
        training_row_count=len(training_rows),
        recognized_feature_key_count=recognized_feature_key_count,
        pair_scope=scoped_dataset.pair_scope,
        engine_scope=scoped_dataset.engine_scope,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        include_route_features=include_route_features,
        blocking_reasons=blocking_reasons,
    )


def _build_success_report(
    *,
    correlation_id: str,
    export_dir: str,
    target_policy: str,
    route_target_fallback_used: bool,
    scoped_dataset: HistoricalReplayDataset,
    scoped_dtr_records: tuple[DTRRecord, ...],
    training_rows: tuple,
    recognized_feature_key_count: int,
    selected_pair: str | None,
    selected_engine_id: str | None,
    include_route_features: bool,
    result: MlTrainerResult,
) -> LocalLabMlArtifactTrainingReport:
    return LocalLabMlArtifactTrainingReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status="trained",
        ready=True,
        target_policy=target_policy,
        route_target_fallback_used=route_target_fallback_used,
        replay_sample_count=scoped_dataset.record_count,
        aligned_dtr_count=len(scoped_dtr_records),
        training_row_count=len(training_rows),
        recognized_feature_key_count=recognized_feature_key_count,
        pair_scope=scoped_dataset.pair_scope,
        engine_scope=scoped_dataset.engine_scope,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        include_route_features=include_route_features,
        artifact=result.artifact,
        artifact_hash=result.artifact.artifact_hash,
        oos_sharpe=result.artifact.oos_sharpe,
        backtest_sharpe=result.artifact.backtest_sharpe,
        ks_test_features_pvalue=result.artifact.ks_test_features_pvalue,
        best_params=result.best_params,
    )


__all__ = [
    "LocalLabMlArtifactTrainingReport",
    "build_local_lab_ml_artifact_training_report",
]
