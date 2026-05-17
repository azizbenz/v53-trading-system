"""Cockpit reader for Strategy Ladder IA Lab ML handoff artifacts."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from cockpit.action_support import CockpitBacktestJobKind, CockpitBacktestJobRecord
from cockpit.form_state_support import LabMlHandoffFormState
from interface_contracts import MlAntiLeakageProofArtifact, MlLiveDriftSnapshot, MlModelArtifact


_TRAINING_SOURCE_MODULE = "src/local_replay_runtime/strategy_ladder_expected_edge_training.py"
_HANDOFF_SOURCE_MODULE = "src/local_replay_runtime/strategy_ladder_ml_lab_handoff.py"
_GOVERNANCE_SOURCE_MODULE = "src/local_replay_runtime/ml_governance_sidecars.py"
_TRANSPORT_SOURCE_MODULE = "src/local_replay_runtime/ml_model_transport.py"
_ROLLING_PLANNER_SOURCE_MODULE = (
    "src/local_replay_runtime/strategy_ladder_rolling_ml_window_planner.py"
)
_COCKPIT_ROUTE_MODULE = "src/cockpit/server.py"
_HANDOFF_CLI_MODULE = "scripts/run_strategy_ladder_ml_lab_handoff.py"
_SCIENTIFIC_STATUS = "EXPLICIT_CODE_EQUATION"
DEFAULT_ROLLING_TRAIN_DAYS = 180
DEFAULT_ROLLING_VALIDATION_DAYS = 30
DEFAULT_ROLLING_FRESHNESS_DAYS = 30
DEFAULT_ROLLING_CHUNK_DAYS = 30

_FEATURE_REGISTRY: dict[str, dict[str, str]] = {
    "close_return": {
        "family": "return_proxy",
        "equation_id": "strategy_ladder.expected_edge.feature.close_return.v1",
        "expression": "(close - open) / open",
    },
    "high_low_range": {
        "family": "range_proxy",
        "equation_id": "strategy_ladder.expected_edge.feature.high_low_range.v1",
        "expression": "(high - low) / open",
    },
    "volume": {
        "family": "volume_profile",
        "equation_id": "strategy_ladder.expected_edge.feature.volume_identity.v1",
        "expression": "volume",
    },
}


class StrategyLadderMlHandoffFeatureRow(BaseModel, frozen=True):
    """One feature exposed to the IA Lab operator with explicit provenance."""

    feature_name: str = Field(..., min_length=1)
    source_kind: str = Field(default="kline_ohlcv", min_length=1)
    family: str = Field(default="", min_length=1)
    equation_id: str = Field(default="", min_length=1)
    expression: str = Field(default="", min_length=1)
    source_module: str = Field(default=_TRAINING_SOURCE_MODULE, min_length=1)
    scientific_status: str = Field(default=_SCIENTIFIC_STATUS, min_length=1)


class StrategyLadderMlHandoffEquationRow(BaseModel, frozen=True):
    """One explicit quant / governance equation displayed on the IA Lab page."""

    equation_id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    expression: str = Field(..., min_length=1)
    source_module: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)


class StrategyLadderMlHandoffModuleRow(BaseModel, frozen=True):
    """One module materially participating in the current ML handoff rail."""

    module_id: str = Field(..., min_length=1)
    module_path: str = Field(..., min_length=1)
    responsibility: str = Field(..., min_length=1)
    interface_surface: str = Field(..., min_length=1)


class StrategyLadderRollingMlWindowChunk(BaseModel, frozen=True):
    chunk_index: int = Field(..., ge=1)
    backtest_chunk_start: str
    backtest_chunk_end: str
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    artifact_stale_after: str
    artifact_required: bool = True
    artifact_id_expected: str
    max_valid_backtest_end: str
    status: str = "CHUNK_READY"


class StrategyLadderRollingMlWindowPlan(BaseModel, frozen=True):
    status: str = ""
    backtest_end_date: str = ""
    required_artifact_count: int = 0
    effective_chunk_days: int = 0
    chunks: tuple[StrategyLadderRollingMlWindowChunk, ...] = ()


class StrategyLadderMlHandoffDashboardSummary(BaseModel, frozen=True):
    """Expanded IA Lab dashboard surface for the governed expected-edge handoff."""

    source_status: str = "missing"
    job_id: str = ""
    artifact_id: str = ""
    status: str = "STRATEGY_LADDER_ML_LAB_HANDOFF_NOT_RUN"
    ready: bool = False
    pair: str = ""
    timeframe: str = ""
    calibration_version: str = ""
    kline_root: str = ""
    label_store_dataset_path: str = ""
    label_store_summary_path: str = ""
    label_store_quality_report_path: str = ""
    train_start: str = ""
    train_end: str = ""
    trainer_train_row_count: int = 0
    trainer_validation_row_count: int = 0
    training_row_count: int = 0
    kline_file_count: int = 0
    requested_backtest_start: str = ""
    requested_backtest_end: str = ""
    artifact_stale_after: str = ""
    max_valid_backtest_end: str = ""
    artifact_hash: str = ""
    feature_hash: str = ""
    dataset_hash: str = ""
    feature_names: tuple[str, ...] = ()
    source_artifact_ref: str = ""
    transport_artifact_ref: str = ""
    transport_summary_ref: str = ""
    training_report_ref: str = ""
    handoff_report_ref: str = ""
    backtest_input_ref: str = ""
    anti_leakage_proof_ref: str = ""
    live_drift_snapshot_ref: str = ""
    backtest_cli_args: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    sample_stride_minutes: int = 0
    target_horizon_minutes: int = 0
    training_seed: int = 0
    optuna_trials_used: int = 0
    bagging_folds_used: int = 0
    first_training_timestamp: str = ""
    last_training_timestamp: str = ""
    target_policy: str = ""
    label_source: str = ""
    label_fidelity: str = ""
    walkforward_status: str = ""
    feature_source: str = ""
    replay_grounded_label_count: int = 0
    proxy_execution_label_count: int = 0
    replay_backed_label_coverage: float | None = None
    net_positive_rate: float | None = None
    break_even_clearance_rate: float | None = None
    mfe_availability_rate: float | None = None
    mae_availability_rate: float | None = None
    purge_window_minutes: int = 0
    embargo_window_minutes: int = 0
    artifact_train_window_start: str = ""
    artifact_train_window_end: str = ""
    artifact_validation_window_start: str = ""
    artifact_validation_window_end: str = ""
    promotion_state: str = ""
    oos_sharpe: float | None = None
    backtest_sharpe: float | None = None
    ks_test_features_pvalue: float | None = None
    drift_baseline_sample_count: int = 0
    drift_baseline_win_rate: float | None = None
    drift_baseline_ce_mean: float | None = None
    drift_baseline_feature_ks_reference_pvalue: float | None = None
    anti_leakage_status: str = "NO_FUTURE_DATA_LEAK_NOT_PROVEN"
    anti_leakage_alignment_status: str = "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
    anti_leakage_random_split_forbidden: bool = True
    anti_leakage_promotion_ready: bool = False
    live_drift_status: str = "LIVE_DRIFT_SOURCE_NOT_PROVEN"
    live_drift_stage: str = ""
    live_drift_stale: bool = False
    live_drift_promotion_ready: bool = False
    live_drift_expires_at: str = ""
    rolling_ml_window_plan_status: str = ""
    rolling_ml_window_plan_ref: str = ""
    rolling_ml_window_plan_markdown_ref: str = ""
    rolling_ml_required_artifact_count: int = 0
    rolling_ml_effective_chunk_days: int = 0
    rolling_train_days: int = DEFAULT_ROLLING_TRAIN_DAYS
    rolling_validation_days: int = DEFAULT_ROLLING_VALIDATION_DAYS
    rolling_freshness_days: int = DEFAULT_ROLLING_FRESHNESS_DAYS
    rolling_chunk_days: int = DEFAULT_ROLLING_CHUNK_DAYS
    rolling_plan_chunks: tuple[StrategyLadderRollingMlWindowChunk, ...] = ()
    best_params_json: str = ""
    feature_rows: tuple[StrategyLadderMlHandoffFeatureRow, ...] = ()
    equation_rows: tuple[StrategyLadderMlHandoffEquationRow, ...] = ()
    module_rows: tuple[StrategyLadderMlHandoffModuleRow, ...] = ()


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    raw = payload.get(key)
    if isinstance(raw, list):
        return tuple(str(item) for item in raw if str(item).strip())
    return ()


def _candidate_report_paths(
    jobs: tuple[CockpitBacktestJobRecord, ...],
) -> tuple[tuple[str, Path], ...]:
    candidates: list[tuple[str, Path]] = []
    for job in jobs:
        if job.job_kind != CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF:
            continue
        if not job.output_root:
            continue
        path = Path(job.output_root) / "strategy_ladder_ml_lab_handoff_report.json"
        if path.is_file():
            candidates.append((job.job_id, path))
    return tuple(candidates)


def _load_model(path_ref: str, model_type: type[BaseModel]) -> BaseModel | None:
    path_text = (path_ref or "").strip()
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_file():
        return None
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError):
        return None


def _string(payload: dict[str, object], key: str) -> str:
    return str(payload.get(key) or "")


def _int(payload: dict[str, object], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _metric_str(metrics: dict[str, object], key: str) -> str:
    return str(metrics.get(key) or "")


def _metric_int(metrics: dict[str, object], key: str) -> int:
    try:
        return int(metrics.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _parse_date(raw_value: str) -> date:
    value = (raw_value or "").strip().replace("Z", "+00:00")
    if "T" not in value and " " not in value:
        return date.fromisoformat(value)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def _artifact_id_expected(
    *,
    chunk_index: int,
    backtest_start: date,
    backtest_end: date,
    train_start: date,
    train_end: date,
    validation_start: date,
    validation_end: date,
) -> str:
    return (
        "strategy_ladder_expected_edge"
        f".chunk{chunk_index:02d}"
        f".bt_{backtest_start.isoformat()}_{backtest_end.isoformat()}"
        f".train_{train_start.isoformat()}_{train_end.isoformat()}"
        f".val_{validation_start.isoformat()}_{validation_end.isoformat()}"
    )


def _build_preview_rolling_plan(
    *,
    backtest_start_date: str,
    backtest_days: int,
    train_days: int,
    validation_days: int,
    freshness_days: int,
    chunk_days: int,
) -> StrategyLadderRollingMlWindowPlan:
    backtest_start = _parse_date(backtest_start_date)
    backtest_end = backtest_start + timedelta(days=backtest_days - 1)
    effective_chunk_days = min(chunk_days, freshness_days)
    cursor = backtest_start
    chunk_index = 1
    chunks: list[StrategyLadderRollingMlWindowChunk] = []
    while cursor <= backtest_end:
        chunk_end = min(
            cursor + timedelta(days=effective_chunk_days - 1),
            backtest_end,
        )
        validation_end = cursor - timedelta(days=1)
        validation_start = validation_end - timedelta(days=validation_days - 1)
        train_end = validation_start - timedelta(days=1)
        train_start = train_end - timedelta(days=train_days - 1)
        artifact_stale_after = validation_end + timedelta(days=freshness_days)
        chunks.append(
            StrategyLadderRollingMlWindowChunk(
                chunk_index=chunk_index,
                backtest_chunk_start=cursor.isoformat(),
                backtest_chunk_end=chunk_end.isoformat(),
                train_start=train_start.isoformat(),
                train_end=train_end.isoformat(),
                validation_start=validation_start.isoformat(),
                validation_end=validation_end.isoformat(),
                artifact_stale_after=artifact_stale_after.isoformat(),
                artifact_required=True,
                artifact_id_expected=_artifact_id_expected(
                    chunk_index=chunk_index,
                    backtest_start=cursor,
                    backtest_end=chunk_end,
                    train_start=train_start,
                    train_end=train_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                ),
                max_valid_backtest_end=artifact_stale_after.isoformat(),
                status="CHUNK_READY",
            )
        )
        cursor = chunk_end + timedelta(days=1)
        chunk_index += 1
    required_artifact_count = len(chunks)
    return StrategyLadderRollingMlWindowPlan(
        status=(
            "ROLLING_PLAN_READY"
            if required_artifact_count == 1
            else f"ROLLING_PLAN_REQUIRES_{required_artifact_count}_ARTIFACTS"
        ),
        backtest_end_date=backtest_end.isoformat(),
        required_artifact_count=required_artifact_count,
        effective_chunk_days=effective_chunk_days,
        chunks=tuple(chunks),
    )


def _load_rolling_plan(path_ref: str) -> StrategyLadderRollingMlWindowPlan | None:
    path_text = (path_ref or "").strip()
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return StrategyLadderRollingMlWindowPlan.model_validate(payload)
    except ValueError:
        return None


def _preview_rolling_plan(
    form_state: LabMlHandoffFormState | None,
) -> StrategyLadderRollingMlWindowPlan | None:
    if form_state is None or not form_state.requested_backtest_start:
        return None
    try:
        return _build_preview_rolling_plan(
                backtest_start_date=form_state.requested_backtest_start,
                backtest_days=max(int(form_state.requested_backtest_days), 1),
                train_days=max(int(form_state.train_days), 1),
                validation_days=max(int(form_state.validation_days), 1),
                freshness_days=max(int(form_state.freshness_days), 1),
                chunk_days=max(int(form_state.chunk_days), 1),
        )
    except ValueError:
        return None


def _feature_row(feature_name: str) -> StrategyLadderMlHandoffFeatureRow:
    registry = _FEATURE_REGISTRY.get(feature_name, {})
    return StrategyLadderMlHandoffFeatureRow(
        feature_name=feature_name,
        family=str(registry.get("family") or "custom_feature"),
        equation_id=str(
            registry.get("equation_id")
            or f"strategy_ladder.expected_edge.feature.{feature_name}.unmapped"
        ),
        expression=str(registry.get("expression") or "not_explicitly_registered"),
    )


def _build_feature_rows(feature_names: tuple[str, ...]) -> tuple[StrategyLadderMlHandoffFeatureRow, ...]:
    return tuple(_feature_row(name) for name in feature_names if name.strip())


def _build_equation_rows(
    feature_names: tuple[str, ...],
) -> tuple[StrategyLadderMlHandoffEquationRow, ...]:
    rows: list[StrategyLadderMlHandoffEquationRow] = [
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.target.abs_forward_close_return.v1",
            category="target",
            expression="abs((future.close - current.close) / current.close)",
            source_module=_TRAINING_SOURCE_MODULE,
            purpose="Current expected-edge label used by the governed trainer.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.guard.backtest_start.v1",
            category="governance",
            expression="validation_end + guard_days_after_validation",
            source_module=_HANDOFF_SOURCE_MODULE,
            purpose="Forbid overlap between validation and requested backtest windows.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.guard.backtest_end.v1",
            category="governance",
            expression="requested_backtest_start + requested_backtest_days - 1",
            source_module=_HANDOFF_SOURCE_MODULE,
            purpose="Deterministic OOS window construction surfaced to operators.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.guard.max_valid_backtest_end.v1",
            category="governance",
            expression="artifact.stale_after.date() or validation_end.date()",
            source_module=_HANDOFF_SOURCE_MODULE,
            purpose="Fail closed when the requested backtest exceeds artifact validity.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.rolling.validation_end.v1",
            category="rolling_plan",
            expression="validation_end = backtest_chunk_start - 1 day",
            source_module=_ROLLING_PLANNER_SOURCE_MODULE,
            purpose="Anchor every chunk to the immediately preceding validation window.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.rolling.train_start.v1",
            category="rolling_plan",
            expression="train_start = (validation_start - 1 day) - train_days + 1",
            source_module=_ROLLING_PLANNER_SOURCE_MODULE,
            purpose="Build the causal training span without random train/test mixing.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.rolling.staleness.v1",
            category="rolling_plan",
            expression="artifact_stale_after = validation_end + freshness_days",
            source_module=_ROLLING_PLANNER_SOURCE_MODULE,
            purpose="Forbid one frozen artifact from covering more OOS days than freshness allows.",
        ),
        StrategyLadderMlHandoffEquationRow(
            equation_id="strategy_ladder.expected_edge.anti_leakage.window_ordering.v1",
            category="anti_leakage",
            expression="train_end < validation_start <= validation_end < test_start",
            source_module=_GOVERNANCE_SOURCE_MODULE,
            purpose="Required ordering used by the anti-leakage proof sidecar.",
        ),
    ]
    rows.extend(
        StrategyLadderMlHandoffEquationRow(
            equation_id=_feature_row(name).equation_id,
            category="feature",
            expression=_feature_row(name).expression,
            source_module=_TRAINING_SOURCE_MODULE,
            purpose=f"Feature derivation for `{name}` from raw kline columns.",
        )
        for name in feature_names
        if name.strip()
    )
    return tuple(rows)


def _module_rows() -> tuple[StrategyLadderMlHandoffModuleRow, ...]:
    return (
        StrategyLadderMlHandoffModuleRow(
            module_id="cockpit.lab.route",
            module_path=_COCKPIT_ROUTE_MODULE,
            responsibility="Collect operator inputs, persist IA Lab form state, and launch or preview the governed handoff.",
            interface_surface="POST /lab/strategy-ladder-ml-handoff",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="cockpit.lab.cli",
            module_path=_HANDOFF_CLI_MODULE,
            responsibility="Stable CLI entry point for the Strategy Ladder ML handoff worker.",
            interface_surface="run_strategy_ladder_ml_lab_handoff.py",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="strategy_ladder.ml_handoff",
            module_path=_HANDOFF_SOURCE_MODULE,
            responsibility="Train, package, and fail-close the frozen expected-edge artifact for backtest.",
            interface_surface="StrategyLadderMlLabHandoffRequest -> report JSON",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="strategy_ladder.rolling_ml_planner",
            module_path=_ROLLING_PLANNER_SOURCE_MODULE,
            responsibility="Compute contiguous train/validation/backtest ML chunks and emit the rolling coverage plan.",
            interface_surface="StrategyLadderRollingMlWindowPlannerRequest -> rolling_ml_window_plan.json/.md",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="strategy_ladder.expected_edge.training",
            module_path=_TRAINING_SOURCE_MODULE,
            responsibility="Build kline-derived features/labels and train the bounded LightGBM artifact.",
            interface_surface="StrategyLadderExpectedEdgeTrainingRequest -> training report + artifact",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="ml.governance.sidecars",
            module_path=_GOVERNANCE_SOURCE_MODULE,
            responsibility="Emit anti-leakage and live-drift governance sidecars next to the trained artifact.",
            interface_surface="MlAntiLeakageProofArtifact + MlLiveDriftSnapshot",
        ),
        StrategyLadderMlHandoffModuleRow(
            module_id="ml.transport",
            module_path=_TRANSPORT_SOURCE_MODULE,
            responsibility="Package the source artifact and supplementary refs into the governed transport rail.",
            interface_surface="transport artifact + transport summary",
        ),
    )


def read_strategy_ladder_ml_handoff_dashboard_summary(
    jobs: tuple[CockpitBacktestJobRecord, ...],
    *,
    form_state: LabMlHandoffFormState | None = None,
) -> StrategyLadderMlHandoffDashboardSummary:
    """Read the latest Strategy Ladder ML handoff report produced by IA Lab."""

    candidates = _candidate_report_paths(jobs)
    if not candidates:
        preview_plan = _preview_rolling_plan(form_state)
        feature_names = (
            _csv_tuple(form_state.feature_names)
            if form_state is not None
            else ()
        )
        return StrategyLadderMlHandoffDashboardSummary(
            source_status=("preview" if preview_plan is not None else "missing"),
            status="STRATEGY_LADDER_ML_LAB_HANDOFF_NOT_RUN",
            pair=("" if form_state is None else form_state.pair),
            timeframe=("" if form_state is None else form_state.timeframe),
            train_start=("" if form_state is None else form_state.train_start),
            train_end=("" if form_state is None else form_state.train_end),
            requested_backtest_start=(
                "" if form_state is None else form_state.requested_backtest_start
            ),
            requested_backtest_end=(
                "" if preview_plan is None else preview_plan.backtest_end_date
            ),
            rolling_ml_window_plan_status=(
                "" if preview_plan is None else preview_plan.status
            ),
            rolling_ml_required_artifact_count=(
                0 if preview_plan is None else preview_plan.required_artifact_count
            ),
            rolling_ml_effective_chunk_days=(
                0 if preview_plan is None else preview_plan.effective_chunk_days
            ),
            rolling_train_days=(
                DEFAULT_ROLLING_TRAIN_DAYS if form_state is None else form_state.train_days
            ),
            rolling_validation_days=(
                DEFAULT_ROLLING_VALIDATION_DAYS
                if form_state is None
                else form_state.validation_days
            ),
            rolling_freshness_days=(
                DEFAULT_ROLLING_FRESHNESS_DAYS
                if form_state is None
                else form_state.freshness_days
            ),
            rolling_chunk_days=(
                DEFAULT_ROLLING_CHUNK_DAYS if form_state is None else form_state.chunk_days
            ),
            rolling_plan_chunks=(
                () if preview_plan is None else preview_plan.chunks
            ),
            feature_names=feature_names,
            feature_rows=_build_feature_rows(feature_names),
            equation_rows=_build_equation_rows(feature_names),
            module_rows=_module_rows(),
        )
    job_id, report_path = max(
        candidates,
        key=lambda item: item[1].stat().st_mtime,
    )
    payload = _load_json(report_path)
    if not payload:
        return StrategyLadderMlHandoffDashboardSummary(
            source_status="invalid",
            job_id=job_id,
            handoff_report_ref=str(report_path.resolve()),
            module_rows=_module_rows(),
        )

    training_report_payload = _load_json(Path(_string(payload, "training_report_ref")))
    artifact = _load_model(_string(payload, "source_artifact_ref"), MlModelArtifact)
    anti_leakage = _load_model(
        _string(payload, "anti_leakage_proof_ref"),
        MlAntiLeakageProofArtifact,
    )
    live_drift = _load_model(_string(payload, "live_drift_snapshot_ref"), MlLiveDriftSnapshot)
    rolling_plan = _load_rolling_plan(
        _string(payload, "rolling_ml_window_plan_ref")
    )
    artifact_metrics = (
        dict(artifact.training_metrics)
        if isinstance(artifact, MlModelArtifact) and isinstance(artifact.training_metrics, dict)
        else {}
    )
    feature_names = _string_tuple(payload, "feature_names") or (
        artifact.feature_names if isinstance(artifact, MlModelArtifact) else ()
    )
    best_params_json = ""
    if training_report_payload.get("best_params"):
        try:
            best_params_json = json.dumps(
                training_report_payload.get("best_params"),
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
        except TypeError:
            best_params_json = ""
    return StrategyLadderMlHandoffDashboardSummary(
        source_status="ok",
        job_id=job_id,
        artifact_id=_string(payload, "artifact_id"),
        status=_string(payload, "status"),
        ready=bool(payload.get("ready")),
        pair=_string(payload, "pair"),
        timeframe=_string(payload, "timeframe"),
        calibration_version=(
            _string(training_report_payload, "calibration_version")
            or (artifact.calibration_version if isinstance(artifact, MlModelArtifact) else "")
        ),
        kline_root=_string(training_report_payload, "kline_root"),
        label_store_dataset_path=_string(training_report_payload, "label_store_dataset_path"),
        label_store_summary_path=_string(training_report_payload, "label_store_summary_path"),
        label_store_quality_report_path=_string(
            training_report_payload,
            "label_store_quality_report_path",
        ),
        train_start=_string(payload, "train_start"),
        train_end=_string(payload, "train_end"),
        trainer_train_row_count=_int(payload, "trainer_train_row_count"),
        trainer_validation_row_count=_int(payload, "trainer_validation_row_count"),
        training_row_count=_int(training_report_payload, "training_row_count"),
        kline_file_count=_int(training_report_payload, "kline_file_count"),
        requested_backtest_start=_string(payload, "requested_backtest_start"),
        requested_backtest_end=_string(payload, "requested_backtest_end"),
        artifact_stale_after=_string(payload, "artifact_stale_after"),
        max_valid_backtest_end=_string(payload, "max_valid_backtest_end"),
        artifact_hash=_string(payload, "artifact_hash"),
        feature_hash=_string(payload, "feature_hash"),
        dataset_hash=_string(payload, "dataset_hash"),
        feature_names=feature_names,
        source_artifact_ref=_string(payload, "source_artifact_ref"),
        transport_artifact_ref=_string(payload, "transport_artifact_ref"),
        transport_summary_ref=_string(payload, "transport_summary_ref"),
        training_report_ref=_string(payload, "training_report_ref"),
        handoff_report_ref=_string(payload, "handoff_report_ref") or str(report_path.resolve()),
        backtest_input_ref=_string(payload, "backtest_input_ref"),
        anti_leakage_proof_ref=_string(payload, "anti_leakage_proof_ref"),
        live_drift_snapshot_ref=_string(payload, "live_drift_snapshot_ref"),
        backtest_cli_args=_string_tuple(payload, "backtest_cli_args"),
        blocking_reasons=_string_tuple(payload, "blocking_reasons"),
        sample_stride_minutes=_int(training_report_payload, "sample_stride_minutes"),
        target_horizon_minutes=_int(training_report_payload, "target_horizon_minutes"),
        training_seed=_int(training_report_payload, "training_seed"),
        optuna_trials_used=_int(training_report_payload, "optuna_trials_used"),
        bagging_folds_used=_int(training_report_payload, "bagging_folds_used"),
        first_training_timestamp=_string(training_report_payload, "first_training_timestamp"),
        last_training_timestamp=_string(training_report_payload, "last_training_timestamp"),
        target_policy=_metric_str(artifact_metrics, "strategy_ladder_target_policy"),
        label_source=(
            _string(training_report_payload, "label_source_type")
            or _metric_str(artifact_metrics, "strategy_ladder_label_source")
        ),
        label_fidelity=(
            _string(training_report_payload, "label_fidelity")
            or _metric_str(artifact_metrics, "strategy_ladder_label_fidelity")
        ),
        walkforward_status=_metric_str(artifact_metrics, "strategy_ladder_walkforward_status"),
        feature_source=(
            _string(training_report_payload, "feature_source")
            or _metric_str(artifact_metrics, "strategy_ladder_feature_source")
        ),
        replay_grounded_label_count=_int(
            training_report_payload,
            "replay_grounded_label_count",
        ),
        proxy_execution_label_count=_int(
            training_report_payload,
            "proxy_execution_label_count",
        ),
        replay_backed_label_coverage=(
            float(training_report_payload["replay_backed_label_coverage"])
            if training_report_payload.get("replay_backed_label_coverage") is not None
            else None
        ),
        net_positive_rate=(
            float(training_report_payload["net_positive_rate"])
            if training_report_payload.get("net_positive_rate") is not None
            else None
        ),
        break_even_clearance_rate=(
            float(training_report_payload["break_even_clearance_rate"])
            if training_report_payload.get("break_even_clearance_rate") is not None
            else None
        ),
        mfe_availability_rate=(
            float(training_report_payload["mfe_availability_rate"])
            if training_report_payload.get("mfe_availability_rate") is not None
            else None
        ),
        mae_availability_rate=(
            float(training_report_payload["mae_availability_rate"])
            if training_report_payload.get("mae_availability_rate") is not None
            else None
        ),
        purge_window_minutes=_metric_int(artifact_metrics, "strategy_ladder_purge_window_minutes"),
        embargo_window_minutes=_metric_int(
            artifact_metrics,
            "strategy_ladder_embargo_window_minutes",
        ),
        artifact_train_window_start=(
            artifact.train_window.start_at.isoformat()
            if isinstance(artifact, MlModelArtifact)
            else ""
        ),
        artifact_train_window_end=(
            artifact.train_window.end_at.isoformat()
            if isinstance(artifact, MlModelArtifact)
            else ""
        ),
        artifact_validation_window_start=(
            artifact.validation_window.start_at.isoformat()
            if isinstance(artifact, MlModelArtifact)
            else ""
        ),
        artifact_validation_window_end=(
            artifact.validation_window.end_at.isoformat()
            if isinstance(artifact, MlModelArtifact)
            else ""
        ),
        promotion_state=artifact.promotion_state.value if isinstance(artifact, MlModelArtifact) else "",
        oos_sharpe=artifact.oos_sharpe if isinstance(artifact, MlModelArtifact) else None,
        backtest_sharpe=(
            artifact.backtest_sharpe if isinstance(artifact, MlModelArtifact) else None
        ),
        ks_test_features_pvalue=(
            artifact.ks_test_features_pvalue if isinstance(artifact, MlModelArtifact) else None
        ),
        drift_baseline_sample_count=(
            0
            if not isinstance(artifact, MlModelArtifact) or artifact.drift_baseline is None
            else artifact.drift_baseline.sample_count
        ),
        drift_baseline_win_rate=(
            None
            if not isinstance(artifact, MlModelArtifact) or artifact.drift_baseline is None
            else artifact.drift_baseline.win_rate
        ),
        drift_baseline_ce_mean=(
            None
            if not isinstance(artifact, MlModelArtifact) or artifact.drift_baseline is None
            else artifact.drift_baseline.ce_mean
        ),
        drift_baseline_feature_ks_reference_pvalue=(
            None
            if not isinstance(artifact, MlModelArtifact) or artifact.drift_baseline is None
            else artifact.drift_baseline.feature_ks_reference_pvalue
        ),
        anti_leakage_status=(
            anti_leakage.no_future_data_leak_status
            if isinstance(anti_leakage, MlAntiLeakageProofArtifact)
            else "NO_FUTURE_DATA_LEAK_NOT_PROVEN"
        ),
        anti_leakage_alignment_status=(
            anti_leakage.feature_timestamp_alignment_status
            if isinstance(anti_leakage, MlAntiLeakageProofArtifact)
            else "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
        ),
        anti_leakage_random_split_forbidden=(
            True
            if not isinstance(anti_leakage, MlAntiLeakageProofArtifact)
            else anti_leakage.random_split_forbidden
        ),
        anti_leakage_promotion_ready=(
            False
            if not isinstance(anti_leakage, MlAntiLeakageProofArtifact)
            else anti_leakage.promotion_ready_proof
        ),
        live_drift_status=(
            live_drift.source_status
            if isinstance(live_drift, MlLiveDriftSnapshot)
            else "LIVE_DRIFT_SOURCE_NOT_PROVEN"
        ),
        live_drift_stage=(
            live_drift.stage if isinstance(live_drift, MlLiveDriftSnapshot) else ""
        ),
        live_drift_stale=(
            False
            if not isinstance(live_drift, MlLiveDriftSnapshot)
            else live_drift.is_stale()
        ),
        live_drift_promotion_ready=(
            False
            if not isinstance(live_drift, MlLiveDriftSnapshot)
            else live_drift.promotion_ready_snapshot
        ),
        live_drift_expires_at=(
            live_drift.expires_at.isoformat()
            if isinstance(live_drift, MlLiveDriftSnapshot) and live_drift.expires_at is not None
            else ""
        ),
        rolling_ml_window_plan_status=(
            rolling_plan.status
            if isinstance(rolling_plan, StrategyLadderRollingMlWindowPlan)
            else _string(payload, "rolling_ml_window_plan_status")
        ),
        rolling_ml_window_plan_ref=_string(payload, "rolling_ml_window_plan_ref"),
        rolling_ml_window_plan_markdown_ref=_string(
            payload,
            "rolling_ml_window_plan_markdown_ref",
        ),
        rolling_ml_required_artifact_count=(
            rolling_plan.required_artifact_count
            if isinstance(rolling_plan, StrategyLadderRollingMlWindowPlan)
            else _int(payload, "rolling_ml_required_artifact_count")
        ),
        rolling_ml_effective_chunk_days=(
            rolling_plan.effective_chunk_days
            if isinstance(rolling_plan, StrategyLadderRollingMlWindowPlan)
            else 0
        ),
        rolling_train_days=_int(payload, "train_days") or DEFAULT_ROLLING_TRAIN_DAYS,
        rolling_validation_days=(
            _int(payload, "validation_days") or DEFAULT_ROLLING_VALIDATION_DAYS
        ),
        rolling_freshness_days=(
            _int(payload, "freshness_days") or DEFAULT_ROLLING_FRESHNESS_DAYS
        ),
        rolling_chunk_days=_int(payload, "chunk_days") or DEFAULT_ROLLING_CHUNK_DAYS,
        rolling_plan_chunks=(
            ()
            if not isinstance(rolling_plan, StrategyLadderRollingMlWindowPlan)
            else rolling_plan.chunks
        ),
        best_params_json=best_params_json,
        feature_rows=_build_feature_rows(feature_names),
        equation_rows=_build_equation_rows(feature_names),
        module_rows=_module_rows(),
    )


__all__ = [
    "StrategyLadderMlHandoffDashboardSummary",
    "StrategyLadderMlHandoffEquationRow",
    "StrategyLadderMlHandoffFeatureRow",
    "StrategyLadderMlHandoffModuleRow",
    "read_strategy_ladder_ml_handoff_dashboard_summary",
]
