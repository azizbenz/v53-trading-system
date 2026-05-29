"""IA Lab handoff for Strategy Ladder expected-edge artifacts.

The handoff stays deliberately thin: training remains LAB_ONLY, the artifact is
packaged through the existing governed ML transport rail, and backtest receives
only a frozen artifact path/hash pair.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from interface_contracts import MlModelArtifact
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.feature_grounding_registry import (
    FEATURE_GROUNDING_CONTRACT_REPORT_FILENAME,
    FEATURE_GROUNDING_REGISTRY_FILENAME,
    build_feature_grounding_contract_report,
    write_feature_grounding_contract_report,
    write_feature_grounding_registry,
)
from local_replay_runtime.ml_label_leakage_guards import (
    ML_FEATURE_INPUT_LABEL_LEAKAGE_REPORT_FILENAME,
    build_ml_feature_input_label_leakage_report,
    write_ml_feature_input_label_leakage_report,
)
from local_replay_runtime.ml_overlay_authority_contract import (
    ML_OVERLAY_AUTHORITY_CONTRACT_REPORT_FILENAME,
    build_ml_overlay_authority_contract_report,
    write_ml_overlay_authority_contract_report,
)
from local_replay_runtime.ml_governance_sidecars import (
    build_ml_anti_leakage_proof_artifact,
    build_ml_live_drift_snapshot,
    write_ml_governance_sidecars,
)
from local_replay_runtime.ml_model_transport import package_ml_model_artifact_for_transport
from local_replay_runtime.strategy_ladder_multiframe_ml_bundle import (
    StrategyLadderMlMultiTimeframeBundle,
    StrategyLadderMlTimeframeSlice,
    normalize_timeframe_scope,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
    StrategyLadderExpectedEdgeTrainingReport,
    StrategyLadderExpectedEdgeTrainingRequest,
    BML_LABEL_STORE_DATASET_FILENAME,
    normalize_supported_expected_edge_feature_names,
    train_strategy_ladder_expected_edge_artifact,
)
# Patch P2b (2026-05-22) — multi-pair C1 manifest emitter (lazy import in writer
# helper to avoid runtime cycles).
from local_replay_runtime.strategy_ladder_multi_pair_handoff_writer import (
    maybe_emit_multi_pair_c1_handoff_manifest,
)
from local_replay_runtime.training_source_contract import (
    ML_TRAIN_EVAL_OVERLAP_REPORT_FILENAME,
    TRAINING_SOURCE_CONTRACT_REPORT_FILENAME,
    ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED,
    BACKTEST_START_TOO_EARLY,
    DATE_PARSE_FAILED,
    build_training_source_contract_report,
    write_training_source_contract_report,
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
STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME = (
    "strategy_ladder_expected_edge_ml_model_bundle.json"
)
STRATEGY_LADDER_ML_MULTIFRAME_SUMMARY_FILENAME = (
    "strategy_ladder_expected_edge_ml_model_bundle.summary.json"
)
REPORTS_DIRNAME = "reports"


class StrategyLadderMlLabHandoffRequest(BaseModel, frozen=True):
    """Train/export one governed Strategy Ladder expected-edge artifact."""

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    kline_root: Path
    b2_run_root: Path | None = None
    label_store_dataset_path: Path | None = None
    export_dir: Path
    pair: str = Field(default="BTCUSDT", min_length=1)
    # Patch P2b (2026-05-22) — optional multi-pair tuple. When len >= 2, the
    # handoff orchestrator emits an additional MULTI_PAIR_C1_EXPECTED_EDGE
    # manifest alongside the standard mono-pair artifacts. Empty preserves
    # the mono-pair behaviour 100%.
    selected_pairs: tuple[str, ...] = ()
    timeframe: str = Field(default="1m", min_length=1)
    timeframe_scope: tuple[str, ...] = ()
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

    @model_validator(mode="before")
    @classmethod
    def _normalize_timeframes(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        scope = normalize_timeframe_scope(data.get("timeframe_scope") or data.get("timeframe"))
        if not scope:
            scope = ("1m",)
        data["timeframe_scope"] = scope
        data["timeframe"] = scope[0] if len(scope) == 1 else ",".join(scope)
        return data

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return normalize_supported_expected_edge_feature_names(value)

    @model_validator(mode="after")
    def _validate_microstructure_source(self) -> "StrategyLadderMlLabHandoffRequest":
        requested_microstructure_features = tuple(
            name for name in self.feature_names if name not in DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
        )
        if (
            requested_microstructure_features
            and self.b2_run_root is None
            and self.label_store_dataset_path is None
        ):
            raise ValueError(
                "Strategy Ladder microstructure expected-edge features require "
                "b2_run_root or label_store_dataset_path"
            )
        return self


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
    timeframe_scope: tuple[str, ...] = ()
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
    feature_grounding_contract_report_ref: str = ""
    training_source_contract_report_ref: str = ""
    ml_overlay_authority_contract_report_ref: str = ""
    ml_train_eval_overlap_report_ref: str = ""
    ml_feature_input_label_leakage_report_ref: str = ""
    backtest_cli_args: tuple[str, ...]


class StrategyLadderMlLabHandoffReport(BaseModel, frozen=True):
    """Audit-ready report for the IA Lab -> backtest ML handoff."""

    schema_version: str = "strategy_ladder.ml_lab_handoff.v1"
    artifact_id: str
    status: str
    ready: bool = False
    pair: str
    timeframe: str
    timeframe_scope: tuple[str, ...] = ()
    export_dir: str
    source_artifact_ref: str | None = None
    transport_artifact_ref: str | None = None
    transport_summary_ref: str | None = None
    training_report_ref: str | None = None
    handoff_report_ref: str | None = None
    backtest_input_ref: str | None = None
    anti_leakage_proof_ref: str | None = None
    live_drift_snapshot_ref: str | None = None
    feature_grounding_contract_report_ref: str | None = None
    training_source_contract_report_ref: str | None = None
    ml_overlay_authority_contract_report_ref: str | None = None
    ml_train_eval_overlap_report_ref: str | None = None
    ml_feature_input_label_leakage_report_ref: str | None = None
    feature_grounding_registry_ref: str | None = None
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
    timeframe_training_reports: tuple[StrategyLadderExpectedEdgeTrainingReport, ...] = ()
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


def _source_type(request: StrategyLadderMlLabHandoffRequest) -> str:
    if request.label_store_dataset_path is not None:
        return (
            "B_ML_LABEL_STORE_DATASET"
            if request.label_store_dataset_path.name == BML_LABEL_STORE_DATASET_FILENAME
            else "LABEL_STORE_DATASET"
        )
    return (
        "B2_REPLAY_GROUNDED_LABEL_STORE"
        if request.b2_run_root is not None
        else "A2_KLINE_GROUNDED"
    )


def _label_store_manifest_root(dataset_path: Path) -> Path:
    resolved = dataset_path.resolve()
    parent = resolved.parent
    candidate_roots: list[Path] = []
    if parent.name.lower() == "labels":
        candidate_roots.append(parent.parent)
    candidate_roots.append(parent)
    for candidate in candidate_roots:
        if (candidate / "manifest.json").is_file():
            return candidate
    return candidate_roots[0]


def _training_manifest_root(request: StrategyLadderMlLabHandoffRequest) -> Path:
    if request.label_store_dataset_path is not None:
        return _label_store_manifest_root(request.label_store_dataset_path)
    return request.b2_run_root if request.b2_run_root is not None else request.kline_root


def _write_static_contract_reports(
    *,
    request: StrategyLadderMlLabHandoffRequest,
    reports_dir: Path,
) -> dict[str, str]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    feature_grounding_report_path = reports_dir / FEATURE_GROUNDING_CONTRACT_REPORT_FILENAME
    training_source_report_path = reports_dir / TRAINING_SOURCE_CONTRACT_REPORT_FILENAME
    overlap_report_path = reports_dir / ML_TRAIN_EVAL_OVERLAP_REPORT_FILENAME
    authority_report_path = reports_dir / ML_OVERLAY_AUTHORITY_CONTRACT_REPORT_FILENAME
    leakage_report_path = reports_dir / ML_FEATURE_INPUT_LABEL_LEAKAGE_REPORT_FILENAME
    registry_path = reports_dir / FEATURE_GROUNDING_REGISTRY_FILENAME

    feature_grounding_report = build_feature_grounding_contract_report(
        request.feature_names,
        b2_run_root_present=(
            request.b2_run_root is not None
            or request.label_store_dataset_path is not None
        ),
        execution_replay_available=(
            request.b2_run_root is not None
            or request.label_store_dataset_path is not None
        ),
    )
    leakage_report = build_ml_feature_input_label_leakage_report(request.feature_names)
    authority_report = build_ml_overlay_authority_contract_report()
    training_source_report = build_training_source_contract_report(
        manifest_root_or_path=_training_manifest_root(request),
        source_type=_source_type(request),
        train_start=request.train_start,
        train_end=request.train_end,
        backtest_start=request.requested_backtest_start or "",
    )

    write_feature_grounding_contract_report(
        feature_grounding_report_path,
        feature_grounding_report,
    )
    write_training_source_contract_report(training_source_report_path, training_source_report)
    write_training_source_contract_report(overlap_report_path, training_source_report)
    write_ml_overlay_authority_contract_report(authority_report_path, authority_report)
    write_ml_feature_input_label_leakage_report(leakage_report_path, leakage_report)
    write_feature_grounding_registry(registry_path)
    return {
        "feature_grounding_contract_report_ref": str(feature_grounding_report_path),
        "training_source_contract_report_ref": str(training_source_report_path),
        "ml_overlay_authority_contract_report_ref": str(authority_report_path),
        "ml_train_eval_overlap_report_ref": str(overlap_report_path),
        "ml_feature_input_label_leakage_report_ref": str(leakage_report_path),
        "feature_grounding_registry_ref": str(registry_path),
    }


def _write_training_source_window_contract(
    *,
    request: StrategyLadderMlLabHandoffRequest,
    reports_dir: Path,
    artifacts_by_timeframe: tuple[tuple[str, MlModelArtifact], ...],
    requested_start: date,
    requested_end: date,
) -> tuple[dict[str, str], tuple[str, ...]]:
    primary_artifact = artifacts_by_timeframe[0][1]
    report = build_training_source_contract_report(
        manifest_root_or_path=_training_manifest_root(request),
        source_type=_source_type(request),
        train_start=primary_artifact.train_window.start_at.date().isoformat(),
        train_end=primary_artifact.train_window.end_at.date().isoformat(),
        validation_start=primary_artifact.validation_window.start_at.date().isoformat(),
        validation_end=primary_artifact.validation_window.end_at.date().isoformat(),
        backtest_start=requested_start.isoformat(),
        backtest_end=requested_end.isoformat(),
    )
    training_source_report_path = reports_dir / TRAINING_SOURCE_CONTRACT_REPORT_FILENAME
    overlap_report_path = reports_dir / ML_TRAIN_EVAL_OVERLAP_REPORT_FILENAME
    write_training_source_contract_report(training_source_report_path, report)
    write_training_source_contract_report(overlap_report_path, report)
    blocking_reasons = tuple(
        reason
        for reason in report.blocker_reasons
        if reason
        in {
            ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED,
            BACKTEST_START_TOO_EARLY,
            DATE_PARSE_FAILED,
        }
    )
    return (
        {
            "training_source_contract_report_ref": str(training_source_report_path),
            "ml_train_eval_overlap_report_ref": str(overlap_report_path),
        },
        blocking_reasons,
    )


def _blocked_report(
    request: StrategyLadderMlLabHandoffRequest,
    *,
    status: str,
    training_reports: tuple[StrategyLadderExpectedEdgeTrainingReport, ...] = (),
    blocking_reasons: tuple[str, ...],
) -> StrategyLadderMlLabHandoffReport:
    primary_training_report = training_reports[0] if training_reports else None
    return StrategyLadderMlLabHandoffReport(
        artifact_id=request.artifact_id,
        status=status,
        ready=False,
        pair=request.pair,
        timeframe=request.timeframe,
        timeframe_scope=request.timeframe_scope,
        export_dir=str(request.export_dir),
        source_artifact_ref=(
            None if primary_training_report is None else primary_training_report.artifact_path
        ),
        training_report_ref=(
            None
            if primary_training_report is None
            else primary_training_report.training_report_path
        ),
        artifact_hash=(
            None if primary_training_report is None else primary_training_report.artifact_hash
        ),
        feature_hash=(
            None if primary_training_report is None else primary_training_report.feature_hash
        ),
        dataset_hash=(
            None if primary_training_report is None else primary_training_report.dataset_hash
        ),
        feature_names=request.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        trainer_train_row_count=(
            0
            if primary_training_report is None
            else primary_training_report.trainer_train_row_count
        ),
        trainer_validation_row_count=(
            0
            if primary_training_report is None
            else primary_training_report.trainer_validation_row_count
        ),
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        timeframe_training_reports=training_reports,
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
    artifacts_by_timeframe: tuple[tuple[str, MlModelArtifact], ...],
) -> tuple[date, date, date, tuple[str, ...]]:
    if not artifacts_by_timeframe:
        raise ValueError("at least one artifact is required")
    default_starts: list[date] = []
    max_valid_candidates: list[date] = []
    blocking_reasons: list[str] = []
    for timeframe, artifact in artifacts_by_timeframe:
        validation_end = _date_from_datetime(artifact.validation_window.end_at)
        default_starts.append(validation_end + timedelta(days=request.guard_days_after_validation))
        if artifact.stale_after is None:
            max_valid_candidates.append(validation_end)
            blocking_reasons.append(f"ARTIFACT_STALE_AFTER_MISSING:{timeframe}")
        else:
            max_valid_candidates.append(_date_from_datetime(artifact.stale_after))
    default_start = max(default_starts)
    requested_start = (
        _parse_date(request.requested_backtest_start)
        if request.requested_backtest_start
        else default_start
    )
    requested_end = requested_start + timedelta(days=request.requested_backtest_days - 1)
    if requested_start < default_start:
        blocking_reasons.append("BACKTEST_START_OVERLAPS_VALIDATION_OR_GUARD")
    max_valid_end = min(max_valid_candidates)
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
    *,
    timeframe: str,
    artifact_id: str,
) -> StrategyLadderExpectedEdgeTrainingReport:
    return train_strategy_ladder_expected_edge_artifact(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id=artifact_id,
            calibration_version=request.calibration_version,
            kline_root=request.kline_root,
            b2_run_root=(
                None if request.label_store_dataset_path is not None else request.b2_run_root
            ),
            label_store_dataset_path=request.label_store_dataset_path,
            output_dir=training_output_dir,
            pair=request.pair,
            timeframe=timeframe,
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


def _timeframe_artifact_id(base_artifact_id: str, timeframe: str) -> str:
    suffix = timeframe.strip().replace("/", "_").replace(",", "_")
    return f"{base_artifact_id}.{suffix}"


def _timeframe_output_dir(base_output_dir: Path, timeframe: str) -> Path:
    suffix = timeframe.strip().replace("/", "_").replace(",", "_")
    return base_output_dir / f"timeframe_{suffix}"


def _bundle_summary_payload(
    *,
    request: StrategyLadderMlLabHandoffRequest,
    bundle: StrategyLadderMlMultiTimeframeBundle,
    training_reports: tuple[StrategyLadderExpectedEdgeTrainingReport, ...],
) -> dict[str, object]:
    training_report_map = {report.timeframe: report for report in training_reports}
    return {
        "schema_version": "strategy_ladder.ml_multiframe_bundle_summary.v1",
        "artifact_id": request.artifact_id,
        "pair": request.pair,
        "timeframe_scope": list(bundle.timeframe_scope),
        "feature_names": list(bundle.feature_names),
        "artifact_hash": bundle.artifact_hash,
        "feature_hash": bundle.feature_hash,
        "calibration_version": request.calibration_version,
        "bundle_ref": str(request.export_dir.resolve() / STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME),
        "slices": [
            {
                "timeframe": item.timeframe,
                "artifact_ref": item.artifact_ref,
                "artifact_hash": item.artifact_hash,
                "feature_hash": item.feature_hash,
                "training_report_ref": item.training_report_ref,
                "anti_leakage_proof_ref": item.anti_leakage_proof_ref,
                "live_drift_snapshot_ref": item.live_drift_snapshot_ref,
                "artifact_stale_after": (
                    None if item.artifact_stale_after is None else item.artifact_stale_after.isoformat()
                ),
                "trainer_train_row_count": training_report_map[item.timeframe].trainer_train_row_count,
                "trainer_validation_row_count": training_report_map[item.timeframe].trainer_validation_row_count,
            }
            for item in bundle.slices
        ],
    }


def _aggregate_dataset_hash(
    training_reports: tuple[StrategyLadderExpectedEdgeTrainingReport, ...],
) -> str:
    payload = [
        {
            "timeframe": report.timeframe,
            "dataset_hash": report.dataset_hash,
        }
        for report in training_reports
    ]
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_strategy_ladder_ml_lab_handoff(
    request: StrategyLadderMlLabHandoffRequest,
) -> StrategyLadderMlLabHandoffReport:
    """Train, package, and emit a frozen ML input sidecar for backtest."""

    export_dir = request.export_dir.resolve()
    report_path = export_dir / STRATEGY_LADDER_ML_HANDOFF_REPORT_FILENAME
    reports_dir = export_dir / REPORTS_DIRNAME
    contract_report_refs = _write_static_contract_reports(
        request=request,
        reports_dir=reports_dir,
    )
    training_reports: list[StrategyLadderExpectedEdgeTrainingReport] = []
    artifacts_by_timeframe: list[tuple[str, MlModelArtifact]] = []
    bundle_summary_path = export_dir / STRATEGY_LADDER_ML_MULTIFRAME_SUMMARY_FILENAME
    multiframe_requested = len(request.timeframe_scope) > 1
    training_blockers: list[str] = []

    for timeframe in request.timeframe_scope:
        training_output_dir = (
            export_dir / "strategy_ladder_expected_edge_training"
            if not multiframe_requested
            else _timeframe_output_dir(export_dir / "strategy_ladder_expected_edge_training", timeframe)
        )
        training_report = _train_expected_edge_artifact(
            request,
            training_output_dir,
            timeframe=timeframe,
            artifact_id=(
                request.artifact_id
                if not multiframe_requested
                else _timeframe_artifact_id(request.artifact_id, timeframe)
            ),
        )
        training_reports.append(training_report)
        if not training_report.ready or not training_report.artifact_path or not training_report.artifact_hash:
            reasons = training_report.blocking_reasons or ("TRAINING_ARTIFACT_NOT_READY",)
            training_blockers.extend(
                tuple(f"TIMEFRAME_{timeframe}:{reason}" for reason in reasons)
                if multiframe_requested
                else reasons
            )
            continue

        try:
            artifact = _load_artifact(training_report.artifact_path)
        except ValueError as exc:
            training_blockers.extend(
                (f"TIMEFRAME_{timeframe}:{exc}",)
                if multiframe_requested
                else (str(exc),)
            )
            continue
        artifacts_by_timeframe.append((timeframe, artifact))

    if training_blockers:
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_reports=tuple(training_reports),
            blocking_reasons=tuple(dict.fromkeys(training_blockers)),
        ).model_copy(
            update=contract_report_refs
        )
        return _write_report(report, report_path)

    # Patch P2b (2026-05-22) — when admin selected ≥ 2 pairs, write a multi-pair
    # C1 manifest per timeframe alongside the mono artifacts. The manifest
    # references the mono training_report artifact_path as model_path_ref ; a
    # subsequent real C1.3.C orchestrator pass (P2c) is required to produce a
    # true multi-pair LightGBM booster. The manifest is loadable by P1 provider
    # but predictions remain mono-equivalent until P2c lands.
    if len(request.selected_pairs) >= 2:
        for timeframe, _artifact in artifacts_by_timeframe:
            timeframe_training_report = next(
                (r for r in training_reports if r.timeframe == timeframe),
                training_reports[0],
            )
            mono_artifact_ref = (
                str(Path(timeframe_training_report.artifact_path).resolve())
                if timeframe_training_report.artifact_path
                else ""
            )
            if not mono_artifact_ref:
                continue
            try:
                maybe_emit_multi_pair_c1_handoff_manifest(
                    selected_pairs=request.selected_pairs,
                    artifact_id=(
                        request.artifact_id
                        if not multiframe_requested
                        else _timeframe_artifact_id(request.artifact_id, timeframe)
                    ),
                    calibration_version=request.calibration_version,
                    timeframe=timeframe,
                    feature_names=request.feature_names,
                    model_path_ref=mono_artifact_ref,
                    train_start=request.train_start,
                    train_end=request.train_end,
                    export_dir=(
                        export_dir
                        if not multiframe_requested
                        else _timeframe_output_dir(
                            export_dir / "strategy_ladder_expected_edge_training",
                            timeframe,
                        )
                    ),
                )
            except (OSError, ValueError):
                # Fail-soft : manifest emission is additive, never block mono path.
                continue

    primary_training_report = training_reports[0]
    requested_start, requested_end, max_valid_end, window_blockers = _requested_backtest_window(
        request,
        tuple(artifacts_by_timeframe),
    )
    training_source_refs, training_source_blockers = _write_training_source_window_contract(
        request=request,
        reports_dir=reports_dir,
        artifacts_by_timeframe=tuple(artifacts_by_timeframe),
        requested_start=requested_start,
        requested_end=requested_end,
    )
    contract_report_refs.update(training_source_refs)
    effective_artifact_stale_after = min(
        (
            artifact.stale_after
            for _timeframe, artifact in artifacts_by_timeframe
            if artifact.stale_after is not None
        ),
        default=None,
    )
    rolling_plan = _rolling_plan(
        request,
        export_dir=export_dir,
        requested_start=requested_start,
    )
    rolling_plan_blockers: list[str] = [*window_blockers, *training_source_blockers]
    if rolling_plan.required_artifact_count > 1:
        rolling_plan_blockers.append(rolling_plan.status)
    if rolling_plan.status == ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY:
        rolling_plan_blockers.append(rolling_plan.status)
    if window_blockers or training_source_blockers:
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_reports=tuple(training_reports),
            blocking_reasons=tuple(dict.fromkeys(rolling_plan_blockers)),
        ).model_copy(
            update={
                "requested_backtest_start": requested_start.isoformat(),
                "requested_backtest_end": requested_end.isoformat(),
                "artifact_stale_after": (
                    None
                    if effective_artifact_stale_after is None
                    else effective_artifact_stale_after.isoformat()
                ),
                "max_valid_backtest_end": max_valid_end.isoformat(),
                "rolling_ml_window_plan_ref": rolling_plan.json_ref,
                "rolling_ml_window_plan_markdown_ref": rolling_plan.markdown_ref,
                "rolling_ml_window_plan_status": rolling_plan.status,
                "rolling_ml_required_artifact_count": rolling_plan.required_artifact_count,
            }
            | contract_report_refs
        )
        return _write_report(report, report_path)
    if (
        rolling_plan.required_artifact_count > 1
        or rolling_plan.status == ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY
    ):
        report = _blocked_report(
            request,
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_BLOCKED",
            training_reports=tuple(training_reports),
            blocking_reasons=tuple(dict.fromkeys(rolling_plan_blockers)),
        ).model_copy(
            update={
                "requested_backtest_start": requested_start.isoformat(),
                "requested_backtest_end": requested_end.isoformat(),
                "artifact_stale_after": (
                    None
                    if effective_artifact_stale_after is None
                    else effective_artifact_stale_after.isoformat()
                ),
                "max_valid_backtest_end": max_valid_end.isoformat(),
                "rolling_ml_window_plan_ref": rolling_plan.json_ref,
                "rolling_ml_window_plan_markdown_ref": rolling_plan.markdown_ref,
                "rolling_ml_window_plan_status": rolling_plan.status,
                "rolling_ml_required_artifact_count": rolling_plan.required_artifact_count,
            }
            | contract_report_refs
        )
        return _write_report(report, report_path)

    multiframe_slices: list[StrategyLadderMlTimeframeSlice] = []
    for timeframe, artifact in artifacts_by_timeframe:
        matching_report = next(report for report in training_reports if report.timeframe == timeframe)
        anti_leakage_proof = build_ml_anti_leakage_proof_artifact(
            artifact,
            test_start=requested_start,
            test_end=requested_end,
        )
        live_drift_snapshot = build_ml_live_drift_snapshot(artifact)
        sidecar_refs = write_ml_governance_sidecars(
            Path(matching_report.artifact_path or "").resolve().parent,
            anti_leakage_proof=anti_leakage_proof,
            live_drift_snapshot=live_drift_snapshot,
        )
        multiframe_slices.append(
            StrategyLadderMlTimeframeSlice(
                timeframe=timeframe,
                artifact_ref=matching_report.artifact_path or "",
                artifact_hash=artifact.artifact_hash,
                feature_hash=artifact.feature_hash,
                feature_names=artifact.feature_names,
                training_report_ref=matching_report.training_report_path or "",
                anti_leakage_proof_ref=sidecar_refs.anti_leakage_proof_ref,
                live_drift_snapshot_ref=sidecar_refs.live_drift_snapshot_ref,
                artifact_stale_after=artifact.stale_after,
            )
        )

    if multiframe_requested:
        bundle = StrategyLadderMlMultiTimeframeBundle.create(
            pair=request.pair,
            timeframe_scope=request.timeframe_scope,
            feature_names=tuple(multiframe_slices[0].feature_names),
            calibration_version=request.calibration_version,
            created_at=datetime.now(tz=UTC),
            slices=tuple(multiframe_slices),
        )
        bundle_path = export_dir / STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME
        atomic_write_json(bundle_path, bundle.model_dump(mode="json"), indent=2)
        bundle_summary_payload = _bundle_summary_payload(
            request=request,
            bundle=bundle,
            training_reports=tuple(training_reports),
        )
        atomic_write_json(bundle_summary_path, bundle_summary_payload, indent=2)
        transport_artifact_ref = str(bundle_path)
        transport_summary_ref = str(bundle_summary_path)
        frozen_artifact_hash = bundle.artifact_hash
        backtest_timeframe = request.timeframe
        report_feature_hash = bundle.feature_hash
        source_artifact_ref = str(bundle_path)
        training_report_ref_value = str(bundle_summary_path)
        anti_leakage_ref = str(bundle_summary_path)
        live_drift_ref = str(bundle_summary_path)
        feature_names = bundle.feature_names
        artifact_stale_after = effective_artifact_stale_after
        dataset_hash = _aggregate_dataset_hash(tuple(training_reports))
    else:
        artifact = artifacts_by_timeframe[0][1]
        transport = package_ml_model_artifact_for_transport(
            export_dir,
            source_artifact_ref=primary_training_report.artifact_path or "",
            artifact_filename=STRATEGY_LADDER_ML_TRANSPORT_ARTIFACT_FILENAME,
            summary_filename=STRATEGY_LADDER_ML_TRANSPORT_SUMMARY_FILENAME,
        )
        transport_artifact_ref = transport.transport_artifact_ref
        transport_summary_ref = transport.summary_ref
        frozen_artifact_hash = artifact.artifact_hash
        backtest_timeframe = request.timeframe
        report_feature_hash = artifact.feature_hash
        source_artifact_ref = primary_training_report.artifact_path or ""
        training_report_ref_value = primary_training_report.training_report_path or ""
        anti_leakage_ref = multiframe_slices[0].anti_leakage_proof_ref
        live_drift_ref = multiframe_slices[0].live_drift_snapshot_ref
        feature_names = artifact.feature_names
        artifact_stale_after = artifact.stale_after
        dataset_hash = primary_training_report.dataset_hash
    cli_args = _backtest_cli_args(
        transport_artifact_ref,
        frozen_artifact_hash,
        rolling_plan,
    )
    backtest_input = StrategyLadderMlBacktestInput(
        status="STRATEGY_LADDER_BACKTEST_ML_INPUT_READY",
        frozen_ml_artifact_path=transport_artifact_ref,
        frozen_ml_artifact_hash=frozen_artifact_hash,
        artifact_summary_ref=transport_summary_ref,
        source_artifact_ref=source_artifact_ref,
        training_report_ref=training_report_ref_value,
        pair=request.pair,
        timeframe=backtest_timeframe,
        timeframe_scope=request.timeframe_scope,
        requested_backtest_start=requested_start.isoformat(),
        requested_backtest_end=requested_end.isoformat(),
        artifact_stale_after=(
            artifact_stale_after.isoformat()
            if artifact_stale_after is not None
            else max_valid_end.isoformat()
        ),
        max_valid_backtest_end=max_valid_end.isoformat(),
        rolling_ml_window_plan_ref=rolling_plan.json_ref or "",
        rolling_ml_window_plan_markdown_ref=rolling_plan.markdown_ref or "",
        rolling_ml_window_plan_status=rolling_plan.status,
        rolling_ml_required_artifact_count=rolling_plan.required_artifact_count,
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        feature_grounding_contract_report_ref=contract_report_refs[
            "feature_grounding_contract_report_ref"
        ],
        training_source_contract_report_ref=contract_report_refs[
            "training_source_contract_report_ref"
        ],
        ml_overlay_authority_contract_report_ref=contract_report_refs[
            "ml_overlay_authority_contract_report_ref"
        ],
        ml_train_eval_overlap_report_ref=contract_report_refs[
            "ml_train_eval_overlap_report_ref"
        ],
        ml_feature_input_label_leakage_report_ref=contract_report_refs[
            "ml_feature_input_label_leakage_report_ref"
        ],
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
        timeframe_scope=request.timeframe_scope,
        export_dir=str(export_dir),
        source_artifact_ref=source_artifact_ref,
        transport_artifact_ref=transport_artifact_ref,
        transport_summary_ref=transport_summary_ref,
        training_report_ref=training_report_ref_value,
        backtest_input_ref=str(backtest_input_path),
        anti_leakage_proof_ref=anti_leakage_ref,
        live_drift_snapshot_ref=live_drift_ref,
        feature_grounding_contract_report_ref=contract_report_refs[
            "feature_grounding_contract_report_ref"
        ],
        training_source_contract_report_ref=contract_report_refs[
            "training_source_contract_report_ref"
        ],
        ml_overlay_authority_contract_report_ref=contract_report_refs[
            "ml_overlay_authority_contract_report_ref"
        ],
        ml_train_eval_overlap_report_ref=contract_report_refs[
            "ml_train_eval_overlap_report_ref"
        ],
        ml_feature_input_label_leakage_report_ref=contract_report_refs[
            "ml_feature_input_label_leakage_report_ref"
        ],
        feature_grounding_registry_ref=contract_report_refs[
            "feature_grounding_registry_ref"
        ],
        artifact_hash=frozen_artifact_hash,
        feature_hash=report_feature_hash,
        dataset_hash=dataset_hash,
        feature_names=feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        trainer_train_row_count=sum(report.trainer_train_row_count for report in training_reports),
        trainer_validation_row_count=sum(
            report.trainer_validation_row_count for report in training_reports
        ),
        requested_backtest_start=requested_start.isoformat(),
        requested_backtest_end=requested_end.isoformat(),
        artifact_stale_after=(
            artifact_stale_after.isoformat()
            if artifact_stale_after is not None
            else max_valid_end.isoformat()
        ),
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
        timeframe_training_reports=tuple(training_reports),
    )
    return _write_report(report, report_path)


__all__ = [
    "DEFAULT_STRATEGY_LADDER_BACKTEST_OOS_DAYS",
    "STRATEGY_LADDER_ML_BACKTEST_INPUT_FILENAME",
    "STRATEGY_LADDER_ML_HANDOFF_REPORT_FILENAME",
    "STRATEGY_LADDER_ML_MULTIFRAME_ARTIFACT_FILENAME",
    "StrategyLadderMlBacktestInput",
    "StrategyLadderMlLabHandoffReport",
    "StrategyLadderMlLabHandoffRequest",
    "run_strategy_ladder_ml_lab_handoff",
]
