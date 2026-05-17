"""IA Lab handoff for Strategy Ladder expected-edge artifacts.

The handoff stays deliberately thin: training remains LAB_ONLY, the artifact is
packaged through the existing governed ML transport rail, and backtest receives
only a frozen artifact path/hash pair.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from interface_contracts import MlModelArtifact
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.ml_governance_sidecars import (
    build_ml_anti_leakage_proof_artifact,
    build_ml_live_drift_snapshot,
    write_ml_governance_sidecars,
)
from local_replay_runtime.ml_model_transport import package_ml_model_artifact_for_transport
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
    StrategyLadderExpectedEdgeTrainingReport,
    StrategyLadderExpectedEdgeTrainingRequest,
    train_strategy_ladder_expected_edge_artifact,
)
from local_replay_runtime.strategy_ladder_rolling_ml_window_planner import (
    DEFAULT_ROLLING_CHUNK_DAYS,
    DEFAULT_ROLLING_FRESHNESS_DAYS,
    DEFAULT_ROLLING_TRAIN_DAYS,
    DEFAULT_ROLLING_VALIDATION_DAYS,
    ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY,
    StrategyLadderRollingMlWindowPlan,
    StrategyLadderRollingMlWindowPlannerRequest,
    write_strategy_ladder_rolling_ml_window_plan,
)


DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS = 130
STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME = "strategy_ladder_backtest_ml_input.json"
STRATEGY_LADDER_ML_HANDOFF_REPORT_FILENAME = "strategy_ladder_ml_lab_handoff_report.json"
STRATEGY_LADDER_ML_TRANSPORT_ARTIFACT_FILENAME = "strategy_ladder_expected_edge_ml_model_artifact.json"
STRATEGY_LADDER_ML_TRANSPORT_SUMMARY_FILENAME = (
    "strategy_ladder_expected_edge_ml_model_artifact.summary.json"
)


class StrategyLadderMlLabHandoffRequest(BaseModel, frozen=True):
    """Train/export one governed Strategy Ladder expected-edge artifact."""

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    kline_root: Path
    b2_run_root: Path | None = None
    export_dir: Path
    pair: str = Field(default="BTCUSDT", min_length=1)
    timeframe: str = Field(default="1m", min_length=1)
    train_start: str = Field(..., min_length=1)
    train_end: str = Field(..., min_length=1)
    requested_backtest_start: str | None = None
    requested_backtest_days: int = Field(default=DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS, ge=1)
    guard_days_after_validation: int = Field(default=1, ge=1)
    train_days: int = Field(default=DEFAULT_ROLLING_TRAIN_DAYS, ge=1)
    validation_days: int = Field(default=DEFAULT_ROLLING_VALIDATION_DAYS, ge=1)
    freshness_days: int = Field(default=DEFAULT_ROLLING_FRESHNESS_DAYS, ge=1)
    chunk_days: int = Field(default=DEFAULT_ROLLING_CHUNK_DAYS, ge=1)
    sample_stride_minutes: int = Field(default=60, ge=1)
    target_horizon_minutes: int = Field(default=1, ge=1)
    training_seed: int = 5307
    max_optuna_trials: int = Field(default=0, ge=0)
    min_training_rows: int = Field(default=210, ge=10)
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    shap_summary_ref: str | None = None

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        unsupported = tuple(
            item for item in normalized if item not in DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
        )
        if unsupported:
            raise ValueError(f"unsupported Strategy Ladder expected-edge features: {unsupported}")
        if not normalized:
            raise ValueError("feature_names must not be empty")
        return normalized


class StrategyLadderMlBacktestInput(BaseModel, frozen=True):
    """Backtest-consumable frozen ML input sidecar."""

    schema_version: str = "strategy_ladder.backtest_ml_input.v1"
    status: str
    ml_mode: str = "ML_MODE_OVERLAY_FROZEN"
    frozen_ml_artifact_path: str
    frozen_ml_artifact_hash: str
    artifact_summary_ref: str
    source_artifact_ref: str
    training_report_ref: str
    pair: str
    timeframe: str
    target_policy: str = STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY
    requested_backtest_start: str
    requested_backtest_end: str
    artifact_stale_after: str
    max_valid_backtest_end: str
    rolling_ml_window_plan_ref: str = ""
    rolling_ml_window_plan_markdown_ref: str = ""
    rolling_ml_window_plan_status: str = ""
    rolling_ml_required_artifact_count: int = 0
    train_days: int = DEFAULT_ROLLING_TRAIN_DAYS
    validation_days: int = DEFAULT_ROLLING_VALIDATION_DAYS
    freshness_days: int = DEFAULT_ROLLING_FRESHNESS_DAYS
    chunk_days: int = DEFAULT_ROLLING_CHUNK_DAYS
    backtest_cli_args: tuple[str, ...]


class StrategyLadderMlLabHandoffReport(BaseModel, frozen=True):
    """Audit-ready report for the IA Lab -> backtest ML handoff."""

    schema_version: str = "strategy_ladder.ml_lab_handoff.v1"
    artifact_id: str
    status: str
    ready: bool = False
    pair: str
    timeframe: str
    export_dir: str
    source_artifact_ref: str | None = None
    transport_artifact_ref: str | None = None
    transport_summary_ref: str | None = None
    training_report_ref: str | None = None
    handoff_report_ref: str | None = None
    backtest_input_ref: str | None = None
    anti_leakage_proof_ref: str | None = None
    live_drift_snapshot_ref: str | None = None
    artifact_hash: str | None = None
    feature_hash: str | None = None
    dataset_hash: str | None = None
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    train_start: str
    train_end: str
    trainer_train_row_count: int = 0
    trainer_validation_row_count: int = 0
    requested_backtest_start: str | None = None
    requested_backtest_end: str | None = None
    artifact_stale_after: str | None = None
    max_valid_backtest_end: str | None = None
    rolling_ml_window_plan_ref: str | None = None
    rolling_ml_window_plan_markdown_ref: str | None = None
    rolling_ml_window_plan_status: str = ""
    rolling_ml_required_artifact_count: int = 0
    train_days: int = DEFAULT_ROLLING_TRAIN_DAYS
    validation_days: int = DEFAULT_ROLLING_VALIDATION_DAYS
    freshness_days: int = DEFAULT_ROLLING_FRESHNESS_DAYS
    chunk_days: int = DEFAULT_ROLLING_CHUNK_DAYS
    backtest_cli_args: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()


def _parse_date(raw_value: str) -> date:
    value = raw_value.strip().replace("Z", "+00:00")
    if "T" not in value and " " not in value:
        return date.fromisoformat(value)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def _utc_datetime(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _date_from_datetime(value: datetime) -> date:
    return _utc_datetime(value).astimezone(UTC).date()


def _write_report(report: StrategyLadderMlLabHandoffReport, path: Path) -> StrategyLadderMlLabHandoffReport:
    final_report = report.model_copy(update={"handoff_report_ref": str(path)})
    atomic_write_json(path, final_report.model_dump(mode="json"), indent=2)
    return final_report


def _blocked_report(
    request: StrategyLadderMlLabHandoffRequest,
    *,
    status: str,
    training_report: StrategyLadderExpectedEdgeTrainingReport | None = None,
    blocking_reasons: tuple[str, ...],
) -> StrategyLadderMlLabHandoffReport:
    return StrategyLadderMlLabHandoffReport(
        artifact_id=request.artifact_id,
        status=status,
        ready=False,
        pair=request.pair,
        timeframe=request.timeframe,
        export_dir=str(request.export_dir),
        source_artifact_ref=None if training_report is None else training_report.artifact_path,
        training_report_ref=None if training_report is None else training_report.training_report_path,
        artifact_hash=None if training_report is None else training_report.artifact_hash,
        feature_hash=None if training_report is None else training_report.feature_hash,
        dataset_hash=None if training_report is None else training_report.dataset_hash,
        feature_names=request.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        trainer_train_row_count=0 if training_report is None else training_report.trainer_train_row_count,
        trainer_validation_row_count=(
            0 if training_report is None else training_report.trainer_validation_row_count
        ),
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        blocking_reasons=blocking_reasons,
    )


def _load_artifact(path: str | None) -> MlModelArtifact:
    if not path:
        raise ValueError("TRAINING_ARTIFACT_PATH_MISSING")
    artifact_path = Path(path)
    if not artifact_path.is_file():
        raise ValueError("TRAINING_ARTIFACT_PATH_NOT_FOUND")
    return MlModelArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8-sig"))


def _requested_backtest_window(
    request: StrategyLadderMlLabHandoffRequest,
    artifact: MlModelArtifact,
) -> tuple[date, date, date, tuple[str, ...]]:
    validation_end = _date_from_datetime(artifact.validation_window.end_at)
    default_start = validation_end + timedelta(days=request.guard_days_after_validation)
    requested_start = (
        _parse_date(request.requested_backtest_start)
        if request.requested_backtest_start
        else default_start
    )
    requested_end = requested_start + timedelta(days=request.requested_backtest_days - 1)
    blocking_reasons: list[str] = []
    if requested_start < default_start:
        blocking_reasons.append("BACKTEST_START_OVERLAPS_VALIDATION_OR_GUARD")
    if artifact.stale_after is None:
        max_valid_end = validation_end
        blocking_reasons.append("ARTIFACT_STALE_AFTER_MISSING")
    else:
        max_valid_end = _date_from_datetime(artifact.stale_after)
        if requested_end > max_valid_end:
            blocking_reasons.append("BACKTEST_WINDOW_EXCEEDS_ARTIFACT_STALE_AFTER")
    return requested_start, requested_end, max_valid_end, tuple(blocking_reasons)


def _rolling_plan(
    request: StrategyLadderMlLabHandoffRequest,
    *,
    export_dir: Path,
    requested_start: date,
) -> StrategyLadderRollingMlWindowPlan:
    return write_strategy_ladder_rolling_ml_window_plan(
        export_dir,
        StrategyLadderRollingMlWindowPlannerRequest(
            backtest_start_date=requested_start.isoformat(),
            backtest_days=request.requested_backtest_days,
            train_days=request.train_days,
            validation_days=request.validation_days,
            freshness_days=request.freshness_days,
            chunk_days=request.chunk_days,
            timezone="UTC",
        ),
    )


def _backtest_cli_args(
    artifact_path: str,
    artifact_hash: str,
    rolling_plan: StrategyLadderRollingMlWindowPlan,
) -> tuple[str, ...]:
    args = [
        "--ml-mode",
        "ML_MODE_OVERLAY_FROZEN",
        "--frozen-ml-artifact-path",
        artifact_path,
        "--frozen-ml-artifact-hash",
        artifact_hash,
        "--ml-artifact-freshness-days",
        str(rolling_plan.freshness_days),
    ]
    if rolling_plan.json_ref:
        args.extend(["--rolling-ml-window-plan-path", rolling_plan.json_ref])
    return tuple(args)


def _train_expected_edge_artifact(
    request: StrategyLadderMlLabHandoffRequest,
    training_output_dir: Path,
) -> StrategyLadderExpectedEdgeTrainingReport:
    return train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id=request.artifact_id,
            calibration_version=request.calibration_version,
            kline_root=request.kline_root,
            b2_run_root=request.b2_run_root,
            output_dir=training_output_dir,
            pair=request.pair,
            timeframe=request.timeframe,
            train_start=request.train_start,
            train_end=request.train_end,
            sample_stride_minutes=request.sample_stride_minutes,
            target_horizon_minutes=request.target_horizon_minutes,
            training_seed=request.training_seed,
            max_optuna_trials=request.max_optuna_trials,
            min_training_rows=request.min_training_rows,
            feature_names=request.feature_names,
            shap_summary_ref=request.shap_summary_ref,
        )
    )


def run_strategy_ladder_ml_lab_handoff(
    request: StrategyLadderMlLabHandoffRequest,
) -> StrategyLadderMlLabHandoffReport:
    """Train, package, and emit a frozen ML input sidecar for backtest."""

    export_dir = request.export_dir.resolve()
    training_output_dir = export_dir / "strategy_ladder_expected_edge_training"
    report_path = export_dir / STRATEGY_LADDER_ML_HANDOFF_REPORT_FILENAME
    training_report = _train_expected_edge_artifact(request, training_output_dir)
    if not training_report.ready or not training_report.artifact_path or not training_report.artifact_hash:
        reasons = training_report.blocking_reasons or ("TRAINING_ARTIFACT_NOT_READY",)
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_report=training_report,
            blocking_reasons=reasons,
        )
        return _write_report(report, report_path)

    try:
        artifact = _load_artifact(training_report.artifact_path)
    except ValueError as exc:
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_report=training_report,
            blocking_reasons=(str(exc),),
        )
        return _write_report(report, report_path)

    requested_start, requested_end, max_valid_end, window_blockers = _requested_backtest_window(
        request,
        artifact,
    )
    rolling_plan = _rolling_plan(
        request,
        export_dir=export_dir,
        requested_start=requested_start,
    )
    rolling_plan_blockers: list[str] = list(window_blockers)
    if rolling_plan.required_artifact_count > 1:
        rolling_plan_blockers.append(rolling_plan.status)
    if rolling_plan.status == ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY:
        rolling_plan_blockers.append(rolling_plan.status)
    if window_blockers:
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_report=training_report,
            blocking_reasons=tuple(dict.fromkeys(rolling_plan_blockers)),
        ).model_copy(
            update={
                "requested_backtest_start": requested_start.isoformat(),
                "requested_backtest_end": requested_end.isoformat(),
                "artifact_stale_after": (
                    None if artifact.stale_after is None else artifact.stale_after.isoformat()
                ),
                "max_valid_backtest_end": max_valid_end.isoformat(),
                "rolling_ml_window_plan_ref": rolling_plan.json_ref,
                "rolling_ml_window_plan_markdown_ref": rolling_plan.markdown_ref,
                "rolling_ml_window_plan_status": rolling_plan.status,
                "rolling_ml_required_artifact_count": rolling_plan.required_artifact_count,
            }
        )
        return _write_report(report, report_path)
    if (
        rolling_plan.required_artifact_count > 1
        or rolling_plan.status == ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY
    ):
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_report=training_report,
            blocking_reasons=tuple(dict.fromkeys(rolling_plan_blockers)),
        ).model_copy(
            update={
                "requested_backtest_start": requested_start.isoformat(),
                "requested_backtest_end": requested_end.isoformat(),
                "artifact_stale_after": (
                    None if artifact.stale_after is None else artifact.stale_after.isoformat()
                ),
                "max_valid_backtest_end": max_valid_end.isoformat(),
                "rolling_ml_window_plan_ref": rolling_plan.json_ref,
                "rolling_ml_window_plan_markdown_ref": rolling_plan.markdown_ref,
                "rolling_ml_window_plan_status": rolling_plan.status,
                "rolling_ml_required_artifact_count": rolling_plan.required_artifact_count,
            }
        )
        return _write_report(report, report_path)

    anti_leakage_proof = build_ml_anti_leakage_proof_artifact(
        artifact,
        test_start=requested_start,
        test_end=requested_end,
    )
    live_drift_snapshot = build_ml_live_drift_snapshot(artifact)
    sidecar_refs = write_ml_governance_sidecars(
        Path(training_report.artifact_path).resolve().parent,
        anti_leakage_proof=anti_leakage_proof,
        live_drift_snapshot=live_drift_snapshot,
    )
    transport = package_ml_model_artifact_for_transport(
        export_dir,
        source_artifact_ref=training_report.artifact_path,
        artifact_filename=STRATEGY_LADDER_ML_TRANSPORT_ARTIFACT_FILENAME,
        summary_filename=STRATEGY_LADDER_ML_TRANSPORT_SUMMARY_FILENAME,
    )
    cli_args = _backtest_cli_args(
        transport.transport_artifact_ref,
        artifact.artifact_hash,
        rolling_plan,
    )
    backtest_input = StrategyLadderMlBacktestInput(
        status="STRATEGY_LADDER_BACKTEST_ML_INPUT_READY",
        frozen_ml_artifact_path=transport.transport_artifact_ref,
        frozen_ml_artifact_hash=artifact.artifact_hash,
        artifact_summary_ref=transport.summary_ref,
        source_artifact_ref=training_report.artifact_path,
        training_report_ref=training_report.training_report_path or "",
        pair=request.pair,
        timeframe=request.timeframe,
        requested_backtest_start=requested_start.isoformat(),
        requested_backtest_end=requested_end.isoformat(),
        artifact_stale_after=artifact.stale_after.isoformat() if artifact.stale_after else "",
        max_valid_backtest_end=max_valid_end.isoformat(),
        rolling_ml_window_plan_ref=rolling_plan.json_ref or "",
        rolling_ml_window_plan_markdown_ref=rolling_plan.markdown_ref or "",
        rolling_ml_window_plan_status=rolling_plan.status,
        rolling_ml_required_artifact_count=rolling_plan.required_artifact_count,
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        backtest_cli_args=cli_args,
    )
    backtest_input_path = export_dir / STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME
    atomic_write_json(backtest_input_path, backtest_input.model_dump(mode="json"), indent=2)

    report = StrategyLadderMlLabHandoffReport(
        artifact_id=request.artifact_id,
        status="STRATEGY_LADDER_ML_LAB_HANDOFF_READY",
        ready=True,
        pair=request.pair,
        timeframe=request.timeframe,
        export_dir=str(export_dir),
        source_artifact_ref=training_report.artifact_path,
        transport_artifact_ref=transport.transport_artifact_ref,
        transport_summary_ref=transport.summary_ref,
        training_report_ref=training_report.training_report_path,
        backtest_input_ref=str(backtest_input_path),
        anti_leakage_proof_ref=sidecar_refs.anti_leakage_proof_ref,
        live_drift_snapshot_ref=sidecar_refs.live_drift_snapshot_ref,
        artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        dataset_hash=artifact.dataset_hash,
        feature_names=artifact.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        trainer_train_row_count=training_report.trainer_train_row_count,
        trainer_validation_row_count=training_report.trainer_validation_row_count,
        requested_backtest_start=requested_start.isoformat(),
        requested_backtest_end=requested_end.isoformat(),
        artifact_stale_after=artifact.stale_after.isoformat() if artifact.stale_after else None,
        max_valid_backtest_end=max_valid_end.isoformat(),
        rolling_ml_window_plan_ref=rolling_plan.json_ref,
        rolling_ml_window_plan_markdown_ref=rolling_plan.markdown_ref,
        rolling_ml_window_plan_status=rolling_plan.status,
        rolling_ml_required_artifact_count=rolling_plan.required_artifact_count,
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        backtest_cli_args=cli_args,
    )
    return _write_report(report, report_path)


__all__ = [
    "DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS",
    "STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME",
    "STRATEGY_LADDER_ML_HANDOFF_REPORT_FILENAME",
    "StrategyLadderMlBacktestInput",
    "StrategyLadderMlLabHandoffReport",
    "StrategyLadderMlLabHandoffRequest",
    "run_strategy_ladder_ml_lab_handoff",
]
