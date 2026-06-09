"""Governed cockpit actions and audited local backtest job helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    RuntimeMode,
)
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
)
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A1,
    PHASE_A2,
    PHASE_B1,
    PHASE_B_ML,
    PHASE_B2,
    PHASE_STATUS_BML_BLOCKED,
    PHASE_STATUS_BML_READY,
    PHASE_STATUS_DATA_FACTORY_BLOCKED,
    PHASE_STATUS_DATA_FACTORY_READY,
    PHASE_STATUS_DISCOVERY_BLOCKED,
    PHASE_STATUS_DISCOVERY_READY,
    PHASE_STATUS_PROOF_BLOCKED,
    PHASE_STATUS_PROMOTION_BLOCKED,
    PHASE_STATUS_REPLAY_READY,
    PHASE_STATUS_STORAGE_BLOCKED,
    ensure_workflow_manifest,
    upsert_workflow_phase,
    workflow_manifest_path,
    workflow_phase_dirname,
)
from cockpit.queue_support import (
    initialize_dashboard_command_queue,
    write_dashboard_command_request,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
_logger = logging.getLogger(__name__)
_LEGACY_EXPECTED_EDGE_FEATURE_NAME_SET = frozenset(
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
)
# A2-materializable governed feature set (= DEFAULT u REPLAY_MICROSTRUCTURE u
# EXTENDED, mirrors strategy_ladder_data_factory._A2_MATERIALIZABLE_FEATURES and
# run_chunked_backtest._A2_GOVERNED_FEATURE_NAMES). Used to upgrade a legacy-only
# selection on the chunked (governed) rail so gold materializes microstructure.
_A2_GOVERNED_FEATURE_NAMES_CSV = ",".join(
    (
        *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
        *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
        *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    )
)


def _scoped_chunked_feature_names_csv(feature_names_csv: str) -> str:
    """Resolve the ``--feature-names`` CSV for the chunked (governed) rail.

    Honors an explicit microstructure selection unchanged; upgrades a legacy-only
    or empty selection to the A2-materializable governed set so chunked gold
    materializes microstructure (vpin / cumulative_ofi / queue_pressure /
    kyle_lambda / realized_vol_*) instead of silently degrading to the 3 legacy
    features. Profile discipline: only the chunked rail upgrades; LIGHT/other
    paths keep their explicit selection.
    """

    selected = tuple(
        token.strip()
        for token in (feature_names_csv or "").split(",")
        if token.strip()
    )
    has_microstructure = any(
        name not in _LEGACY_EXPECTED_EDGE_FEATURE_NAME_SET for name in selected
    )
    if has_microstructure:
        return ",".join(selected)
    return _A2_GOVERNED_FEATURE_NAMES_CSV


class CockpitBacktestJobStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    JOB_CREATED = "JOB_CREATED"
    JOB_RUNNING = "JOB_RUNNING"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_COMPLETED_WITH_BLOCKERS = "JOB_COMPLETED_WITH_BLOCKERS"
    JOB_FAILED = "JOB_FAILED"
    JOB_BLOCKED = "JOB_BLOCKED"
    JOB_CANCELLED = "JOB_CANCELLED"
    # Patch 6 batch 2 — Cancel button safety states.
    JOB_CANCELLING = "JOB_CANCELLING"
    JOB_KILLED = "JOB_KILLED"
    JOB_CANCEL_FAILED = "JOB_CANCEL_FAILED"
    JOB_NOT_RUNNING = "JOB_NOT_RUNNING"
    JOB_NOT_PROVEN = "JOB_NOT_PROVEN"


# Patch 6 batch 2 — Cancel-flow blockers and reason codes.
PID_NOT_FOUND = "PID_NOT_FOUND"
JOB_ID_NOT_FOUND = "JOB_ID_NOT_FOUND"
CANCEL_REQUEST_FILENAME = "cancel_request.json"
JOB_RECORD_STALE_PID_DEAD = "JOB_RECORD_STALE_PID_DEAD"
JOB_PROCESS_EXITED_WITHOUT_MANIFESTS = "JOB_PROCESS_EXITED_WITHOUT_MANIFESTS"
JOB_TERMINAL_ARTIFACT_STALL_RECOVERED = "JOB_TERMINAL_ARTIFACT_STALL_RECOVERED"
COCKPIT_JOB_TERMINAL_SENTINEL_ENV = "COCKPIT_JOB_TERMINAL_SENTINEL_PATH"


PAIR_ARG_INVALID_PATH = "PAIR_ARG_INVALID_PATH"
RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE = "RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE"
PAIR_UNIVERSE_AMBIGUOUS = "PAIR_UNIVERSE_AMBIGUOUS"

# Patch 6 output-root selector — explicit blocker codes for fail-closed routing.
OUTPUT_ROOT_READY = "OUTPUT_ROOT_READY"
OUTPUT_ROOT_DEFAULTED = "OUTPUT_ROOT_DEFAULTED"
OUTPUT_ROOT_INVALID_PATH = "OUTPUT_ROOT_INVALID_PATH"
OUTPUT_ROOT_INSIDE_RAW_ROOT = "OUTPUT_ROOT_INSIDE_RAW_ROOT"
OUTPUT_ROOT_NOT_WRITABLE = "OUTPUT_ROOT_NOT_WRITABLE"
OUTPUT_ROOT_EXISTS_NON_EMPTY = "OUTPUT_ROOT_EXISTS_NON_EMPTY"

# Hard-coded sensitive raw-data prefixes that must never host the output root.
_PROTECTED_RAW_PREFIXES: tuple[str, ...] = (
    "l:\\trades",
    "l:\\klines",
    "l:\\ordre book",
    "l:\\orderbook",
)

_DEFAULT_ENGINE_NATIVE_SAMPLE_SIZE = 10
_STRATEGY_LADDER_POSTRUN_STALL_SECONDS = 30.0
_RUNNING_JOB_STATUSES: tuple[CockpitBacktestJobStatus, ...] = (
    CockpitBacktestJobStatus.REQUESTED,
    CockpitBacktestJobStatus.RUNNING,
    CockpitBacktestJobStatus.JOB_CREATED,
    CockpitBacktestJobStatus.JOB_RUNNING,
    CockpitBacktestJobStatus.JOB_CANCELLING,
)
_TERMINAL_JOB_STATUSES: tuple[CockpitBacktestJobStatus, ...] = (
    CockpitBacktestJobStatus.COMPLETED,
    CockpitBacktestJobStatus.FAILED,
    CockpitBacktestJobStatus.JOB_COMPLETED,
    CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS,
    CockpitBacktestJobStatus.JOB_FAILED,
    CockpitBacktestJobStatus.JOB_BLOCKED,
    CockpitBacktestJobStatus.JOB_CANCELLED,
    CockpitBacktestJobStatus.JOB_KILLED,
    CockpitBacktestJobStatus.JOB_CANCEL_FAILED,
    CockpitBacktestJobStatus.JOB_NOT_RUNNING,
)


def _is_path_inside(child: Path, parent: Path) -> bool:
    """Return True when ``child`` resolves to ``parent`` or a descendant."""

    try:
        child_resolved = child.resolve()
        parent_resolved = parent.resolve()
    except OSError:
        return False
    if child_resolved == parent_resolved:
        return True
    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError:
        return False
    return True


def resolve_output_root(
    *,
    operator_output_root: str,
    default_output_root: Path,
    raw_roots: tuple[Path, ...] = (),
    allow_resume: bool = False,
) -> tuple[Path, str, str]:
    """Validate operator-supplied output_root or fall back to default.

    Returns ``(resolved_path, status_code, blocker_reason)`` where
    ``blocker_reason`` is empty string on success and a typed code otherwise.
    The caller is responsible for honouring the blocker (skipping subprocess).
    """

    candidate = (operator_output_root or "").strip().strip('"').strip("'")
    if not candidate:
        return default_output_root, OUTPUT_ROOT_DEFAULTED, ""

    try:
        candidate_path = Path(candidate).expanduser()
    except (TypeError, ValueError):
        return default_output_root, OUTPUT_ROOT_INVALID_PATH, OUTPUT_ROOT_INVALID_PATH
    try:
        resolved = candidate_path.resolve(strict=False)
    except OSError:
        return default_output_root, OUTPUT_ROOT_INVALID_PATH, OUTPUT_ROOT_INVALID_PATH

    # Reject paths that overlap any raw root or hard-coded sensitive prefix.
    lowered = str(resolved).lower()
    for prefix in _PROTECTED_RAW_PREFIXES:
        if lowered.startswith(prefix):
            return default_output_root, OUTPUT_ROOT_INSIDE_RAW_ROOT, OUTPUT_ROOT_INSIDE_RAW_ROOT
    for raw_root in raw_roots:
        if not raw_root:
            continue
        if _is_path_inside(resolved, raw_root):
            return default_output_root, OUTPUT_ROOT_INSIDE_RAW_ROOT, OUTPUT_ROOT_INSIDE_RAW_ROOT

    # Parent must exist or be creatable (write the parent only — never the
    # output_root itself, since that would race the existing-non-empty guard).
    parent = resolved.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return default_output_root, OUTPUT_ROOT_INVALID_PATH, OUTPUT_ROOT_INVALID_PATH

    # Writable check on the parent (or the directory itself if it exists).
    probe = resolved if resolved.exists() else parent
    import os as _os

    if not _os.access(str(probe), _os.W_OK):
        return default_output_root, OUTPUT_ROOT_NOT_WRITABLE, OUTPUT_ROOT_NOT_WRITABLE

    # Existing non-empty directory blocks unless explicit resume.
    if resolved.exists() and any(resolved.iterdir()) and not allow_resume:
        return default_output_root, OUTPUT_ROOT_EXISTS_NON_EMPTY, OUTPUT_ROOT_EXISTS_NON_EMPTY

    return resolved, OUTPUT_ROOT_READY, ""


# Typical-duration table per job kind, used to compute a coarse percentage
# progress bar and a remaining-time estimate (in minutes) without depending
# on any internal stage-summary parsing. Values are conservative upper-bounds.
_TYPICAL_JOB_DURATION_MINUTES: dict[str, float] = {
    "local_lab_analysis_bundle": 3.0,
    "local_lab_post_trade_review": 2.0,
    "edge_gate_calibration": 2.0,
    "strategy_ladder_runner": 12.0,
    "strategy_ladder_data_factory": 4.0,
    "strategy_ladder_first_controlled_run": 8.0,
    "strategy_ladder_ml_lab_handoff": 6.0,
    "strategy_ladder_b_ml_label_factory": 5.0,
}


def is_valid_raw_source_manifest_path(value: str) -> bool:
    """Return True only when the cockpit-supplied manifest path is a ``.json`` file.

    Folders, ``.data``, ``.csv``, ``.jsonl`` and any non-``.json`` extension
    are rejected. The check is purely lexical because the cockpit may run
    on a host that does not see L:/ drive paths during validation.
    """

    candidate = (value or "").strip().strip('"').strip("'")
    if not candidate:
        return False
    if candidate.endswith(("/", "\\")):
        return False
    suffix = Path(candidate).suffix.lower()
    return suffix == ".json"


def is_path_like_pair_token(token: str) -> bool:
    """Return True when a candidate ``--pairs`` token contains a filesystem path."""

    candidate = (token or "").strip()
    if not candidate:
        return False
    if ":\\" in candidate or ":/" in candidate:
        return True
    if candidate.startswith("/") or candidate.startswith("\\"):
        return True
    if "/" in candidate or "\\" in candidate:
        return True
    return False


def estimate_job_progress(
    *,
    job_kind: str,
    status: str,
    started_at_iso: str,
    finished_at_iso: str,
) -> tuple[int, float]:
    """Return (progress_pct 0–100, eta_minutes).

    ETA uses elapsed-vs-typical-duration per ``job_kind``. Completed/failed/blocked
    jobs return (100, 0.0). Jobs not yet started return (0, typical).
    """

    typical_minutes = _TYPICAL_JOB_DURATION_MINUTES.get(job_kind, 5.0)
    if status in {
        "JOB_COMPLETED",
        "JOB_COMPLETED_WITH_BLOCKERS",
        "JOB_FAILED",
        "JOB_BLOCKED",
        "JOB_CANCELLED",
        "completed",
        "failed",
    }:
        return 100, 0.0
    start_dt = _parse_iso(started_at_iso)
    if start_dt is None:
        return 0, typical_minutes
    end_dt = _parse_iso(finished_at_iso) or datetime.now(tz=UTC)
    elapsed_minutes = max((end_dt - start_dt).total_seconds() / 60.0, 0.0)
    if typical_minutes <= 0:
        return 50, 0.0
    raw_pct = elapsed_minutes / typical_minutes
    # Clamp running progress to 95 so the bar never reaches 100% before completion.
    pct = int(max(0.0, min(raw_pct, 0.95)) * 100)
    eta_minutes = max(typical_minutes - elapsed_minutes, 0.0)
    return pct, round(eta_minutes, 1)


def infer_pair_universe_from_paths(paths: tuple[str, ...]) -> tuple[tuple[str, ...], bool]:
    """Infer market symbols from a tuple of input paths.

    Returns (symbols, ambiguous) where ``ambiguous`` is True when more than one
    distinct symbol is inferred. Empty/non-symbol paths contribute nothing and
    do not create ambiguity.
    """

    inferred: list[str] = []
    for raw in paths:
        symbol = infer_pair_symbol_from_path(raw)
        if symbol and symbol not in inferred:
            inferred.append(symbol)
    return tuple(inferred), len(inferred) > 1


def infer_pair_symbol_from_path(raw: str) -> str:
    """Best-effort extraction of a market symbol from a filesystem-style path token."""

    candidate = (raw or "").strip().strip('"').strip("'")
    if not candidate:
        return ""
    normalized = candidate.replace("\\", "/").rstrip("/")
    if not normalized:
        return ""
    parts = [part for part in normalized.split("/") if part]
    # Walk leaf -> root, breaking on the first segment that looks like a market symbol
    for segment in reversed(parts):
        for token in segment.replace(".", "_").split("_"):
            cleaned = token.strip().upper()
            if (
                cleaned
                and cleaned.isalnum()
                and 4 <= len(cleaned) <= 20
                and any(ch.isalpha() for ch in cleaned)
                and any(ch.isdigit() is False and ch.isalpha() for ch in cleaned)
                and (
                    cleaned.endswith("USDT")
                    or cleaned.endswith("USDC")
                    or cleaned.endswith("BUSD")
                    or cleaned.endswith("BTC")
                    or cleaned.endswith("ETH")
                    or cleaned.endswith("USD")
                )
            ):
                return cleaned
    return ""


class CockpitBacktestJobKind(StrEnum):
    LOCAL_LAB_ANALYSIS_BUNDLE = "local_lab_analysis_bundle"
    LOCAL_LAB_POST_TRADE_REVIEW = "local_lab_post_trade_review"
    EDGE_GATE_CALIBRATION = "edge_gate_calibration"
    STRATEGY_LADDER_RUNNER = "strategy_ladder_runner"
    STRATEGY_LADDER_DATA_FACTORY = "strategy_ladder_data_factory"
    STRATEGY_LADDER_FIRST_CONTROLLED_RUN = "strategy_ladder_first_controlled_run"
    STRATEGY_LADDER_ML_LAB_HANDOFF = "strategy_ladder_ml_lab_handoff"
    STRATEGY_LADDER_B_ML_LABEL_FACTORY = "strategy_ladder_b_ml_label_factory"
    STRATEGY_LADDER_CHUNKED = "strategy_ladder_chunked"


class StrategyLadderControlAction(StrEnum):
    PHASE_A1_PREVIEW = "PHASE_A1_PREVIEW"
    PHASE_A2_DATA_FACTORY = "PHASE_A2_DATA_FACTORY"
    PHASE_B1_CANDIDATE_DISCOVERY = "PHASE_B1_CANDIDATE_DISCOVERY"
    PHASE_B_ML_LABEL_FACTORY = "PHASE_B_ML_LABEL_FACTORY"
    PHASE_B2_DETAILED_REPLAY = "PHASE_B2_DETAILED_REPLAY"
    DATA_FACTORY_DRY_RUN = "DATA_FACTORY_DRY_RUN"
    DATA_FACTORY_SMALL_SCOPE_RUN = "DATA_FACTORY_SMALL_SCOPE_RUN"
    FIRST_CONTROLLED_RUN_DRY_RUN = "FIRST_CONTROLLED_RUN_DRY_RUN"
    FIRST_CONTROLLED_RUN_SMALL_SCOPE = "FIRST_CONTROLLED_RUN_SMALL_SCOPE"


class CockpitBacktestJobRecord(BaseModel, frozen=True):
    """Bounded audited local job record used by the cockpit backtest surface."""

    job_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    job_kind: CockpitBacktestJobKind
    status: CockpitBacktestJobStatus
    requested_at_iso: str = Field(..., min_length=1)
    started_at_iso: str = ""
    finished_at_iso: str = ""
    export_dir: str = ""
    baseline_export_dir: str = ""
    output_root: str = ""
    record_path: str = ""
    stdout_log_path: str = ""
    command: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    error_summary: str = ""
    action_name: str = ""
    phase_id: str = ""
    workflow_run_id: str = ""
    phase_run_id: str = ""
    parent_workflow_ref: str = ""
    preview_id: str = ""
    request_hash: str = ""
    command_preview: str = ""
    job_request_path: str = ""
    job_status_path: str = ""
    stage_statuses: dict[str, str] = Field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    artifact_inventory_path: str = ""
    stage_summary_path: str = ""
    allow_broad_run: bool = False
    ml_mode_status: str = "ML_MODE_OFF"
    frozen_ml_artifact_path: str = ""
    frozen_ml_artifact_hash: str = ""
    rolling_ml_window_plan_path: str = ""
    ml_artifact_freshness_days: int = 30
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    engine_native_sample_size: int = _DEFAULT_ENGINE_NATIVE_SAMPLE_SIZE
    backtest_timeframes: tuple[str, ...] = ("1m",)
    b1_5_policy_mode: str = "conservative_hard_only"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    silver_storage_mode: str = "jsonl_debug"
    consumed_artifact_refs: dict[str, str] = Field(default_factory=dict)
    produced_artifact_refs: dict[str, str] = Field(default_factory=dict)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    # Patch 6 batch 2 — cancel-flow telemetry.
    pid: int = 0
    cancel_requested_at: str = ""
    cancelled_at: str = ""
    cancel_reason: str = ""
    termination_method: str = ""

    @property
    def output_ref_count(self) -> int:
        return len(self.output_refs)

    @property
    def stdout_log_size_kb(self) -> float:
        if not self.stdout_log_path:
            return 0.0
        try:
            return Path(self.stdout_log_path).stat().st_size / 1024.0
        except OSError:
            return 0.0

    @property
    def produced_file_count(self) -> int:
        if self.output_refs:
            return len(self.output_refs)
        inventory_path = Path(self.artifact_inventory_path) if self.artifact_inventory_path else None
        if inventory_path is not None:
            payload = _read_json_payload(inventory_path)
            refs = payload.get("artifact_refs") if payload else None
            if isinstance(refs, dict):
                return len(
                    [
                        key
                        for key, value in refs.items()
                        if key and isinstance(value, str) and value
                    ]
                )
        output_root = Path(self.output_root) if self.output_root else None
        if output_root is not None:
            return _count_existing_output_files(output_root)
        return 0

    @property
    def duration_seconds(self) -> float | None:
        start = _parse_iso(self.started_at_iso)
        if start is None:
            return None
        end = _parse_iso(self.finished_at_iso)
        if end is None and self.status in _RUNNING_JOB_STATUSES:
            end = datetime.now(tz=UTC)
        if end is None:
            return None
        return max((end - start).total_seconds(), 0.0)

    @property
    def latest_activity_iso(self) -> str:
        timestamps: list[datetime] = []
        for raw_value in (
            self.finished_at_iso,
            self.started_at_iso,
            self.requested_at_iso,
            self.latest_output_activity_iso,
        ):
            parsed = _parse_iso(raw_value)
            if parsed is not None:
                timestamps.append(parsed)
        if not timestamps:
            return ""
        return max(timestamps).isoformat()

    @property
    def latest_output_activity_iso(self) -> str:
        candidates: list[Path] = []
        for raw_path in (
            self.stdout_log_path,
            self.artifact_inventory_path,
            self.stage_summary_path,
            self.job_status_path,
            self.record_path,
        ):
            path = Path(raw_path) if raw_path else None
            if path is not None and path.is_file():
                candidates.append(path)
        output_root = Path(self.output_root) if self.output_root else None
        if output_root is not None and output_root.is_dir():
            for filename in (
                "a2_microstructure_performance_report.json",
                "a2_microstructure_cache_manifest.json",
                "a2_feature_equivalence_report.json",
                "gold_feature_manifest.json",
                "data_factory_manifest.json",
                "data_quality_report.json",
                "silver_index.json",
                "job_status.json",
            ):
                path = output_root / filename
                if path.is_file():
                    candidates.append(path)
        if not candidates:
            return ""
        try:
            latest_mtime = max(path.stat().st_mtime for path in candidates)
        except OSError:
            return ""
        return datetime.fromtimestamp(latest_mtime, tz=UTC).isoformat()

    @property
    def pid_alive(self) -> bool:
        return _pid_is_alive(self.pid)

    @property
    def progress_pct(self) -> int:
        """Coarse 0–100 progress for the cockpit progress bar."""

        pct, _ = estimate_job_progress(
            job_kind=self.job_kind.value,
            status=self.status.value,
            started_at_iso=self.started_at_iso,
            finished_at_iso=self.finished_at_iso,
        )
        return pct

    @property
    def eta_minutes(self) -> float:
        """Estimated remaining minutes; 0.0 once the job is finished."""

        _, eta = estimate_job_progress(
            job_kind=self.job_kind.value,
            status=self.status.value,
            started_at_iso=self.started_at_iso,
            finished_at_iso=self.finished_at_iso,
        )
        return eta

    @property
    def progress_health_status(self) -> str:
        if self.status not in _RUNNING_JOB_STATUSES:
            return "JOB_NOT_RUNNING"
        duration = self.duration_seconds or 0.0
        produced_count = self.produced_file_count
        if self.progress_pct >= 95 and produced_count == 0 and duration >= 900.0:
            return "RUNNING_AT_95_WITHOUT_ARTIFACTS"
        latest_activity = _parse_iso(self.latest_activity_iso)
        if latest_activity is not None:
            age_s = (datetime.now(tz=UTC) - latest_activity).total_seconds()
            if age_s >= 900.0:
                return "RUNNING_NO_RECENT_ARTIFACT_ACTIVITY"
        if produced_count > 0:
            return "RUNNING_WITH_ARTIFACT_ACTIVITY"
        return "RUNNING_WAITING_FOR_FIRST_ARTIFACT"

    @property
    def progress_health_message(self) -> str:
        status = self.progress_health_status
        if status == "RUNNING_AT_95_WITHOUT_ARTIFACTS":
            return "Progress is clamped at 95%; no artifacts are visible yet. Inspect stdout and A2 reports before waiting longer."
        if status == "RUNNING_NO_RECENT_ARTIFACT_ACTIVITY":
            return "The process is still marked running, but no recent artifact activity is visible."
        if status == "RUNNING_WITH_ARTIFACT_ACTIVITY":
            return "Artifacts are being produced; use latest activity and report links for real progress."
        if status == "RUNNING_WAITING_FOR_FIRST_ARTIFACT":
            return "The job is running and waiting for the first visible artifact."
        return "The job is not running."


class CockpitQueuedCommandSummary(BaseModel, frozen=True):
    """Short ack returned to the cockpit after enqueueing a governed request."""

    request_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    command_kind: str = Field(..., min_length=1)
    queue_path: str = Field(..., min_length=1)


def stage_artifact_upload(
    *,
    ingress_root: Path,
    filename: str,
    payload: bytes,
    artifact_kind: DashboardArtifactKind,
    artifact_id: str = "",
    feature_set_version: str = "",
    feature_profile: str = "",
    lineage_version: str = "",
    review_state: str = "",
    validation_status: str = "",
) -> DashboardArtifactTransferManifest:
    """Persist a browser-uploaded artifact bundle into a service-owned ingress area."""

    timestamp_ms = _timestamp_ms()
    safe_name = _safe_filename(filename)
    target_dir = ingress_root / f"{timestamp_ms}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name
    target_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    return DashboardArtifactTransferManifest(
        artifact_hash=digest,
        artifact_kind=artifact_kind,
        artifact_id=artifact_id,
        feature_set_version=feature_set_version,
        feature_profile=feature_profile,
        lineage_version=lineage_version,
        review_state=review_state,
        validation_status=validation_status,
        source_ref=str(target_path.resolve()),
    )


def enqueue_artifact_command(
    *,
    queue_root: Path,
    command_kind: DashboardGovernedCommandKind,
    requested_by: str,
    operator_reason: str,
    artifact_manifest: DashboardArtifactTransferManifest | None = None,
) -> CockpitQueuedCommandSummary:
    """Write one governed artifact transfer/export request into the canonical queue."""

    request = _build_governed_request(
        command_kind=command_kind,
        requested_by=requested_by,
        operator_reason=operator_reason,
        artifact_manifest=artifact_manifest,
    )
    initialize_dashboard_command_queue(queue_root)
    queue_path = write_dashboard_command_request(queue_root, request)
    return CockpitQueuedCommandSummary(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        command_kind=request.command_kind.value,
        queue_path=str(queue_path.resolve()),
    )


def enqueue_pair_command(
    *,
    queue_root: Path,
    command_kind: DashboardGovernedCommandKind,
    target_pair: str,
    requested_by: str,
    operator_reason: str,
) -> CockpitQueuedCommandSummary:
    """Write one governed pair-control request into the canonical queue."""

    request = _build_governed_request(
        command_kind=command_kind,
        requested_by=requested_by,
        operator_reason=operator_reason,
        target_pair=target_pair,
    )
    initialize_dashboard_command_queue(queue_root)
    queue_path = write_dashboard_command_request(queue_root, request)
    return CockpitQueuedCommandSummary(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        command_kind=request.command_kind.value,
        queue_path=str(queue_path.resolve()),
    )


def launch_backtest_job(
    *,
    jobs_root: Path,
    job_kind: CockpitBacktestJobKind,
    export_dir: Path,
    b2_run_root: Path | None = None,
    label_store_dataset_path: Path | None = None,
    baseline_export_dir: Path | None = None,
    signed_by: str = "cockpit_operator",
    python_executable: str | None = None,
    action_name: str = "",
    phase_id: str = "",
    preview_id: str = "",
    request_hash: str = "",
    raw_source_manifest_path: Path | None = None,
    historical_metadata_root: Path | None = None,
    raw_roots: tuple[Path, ...] = (),
    pairs: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    allow_broad_run: bool = False,
    blocked_reason: str = "",
    ml_mode_status: str = "ML_MODE_OFF",
    frozen_ml_artifact_path: Path | None = None,
    frozen_ml_artifact_hash: str = "",
    expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY",
    rolling_ml_window_plan_path: Path | None = None,
    ml_artifact_freshness_days: int = 30,
    operator_output_root: str = "",
    engine_native_mode: bool = False,
    engine_native_sample_size: int = _DEFAULT_ENGINE_NATIVE_SAMPLE_SIZE,
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG",
    b1_5_policy_mode: str = "conservative_hard_only",
    preselected_only: bool = True,
    diagnostic_full_replay: bool = False,
    small_scope_enabled: bool = True,
    full_scan_enabled: bool = False,
    no_full_scan_enabled: bool = True,
    silver_storage_mode: str = "jsonl_debug",
    debug_storage_override: bool = False,
    workflow_run_id: str = "",
    feature_store_root: Path | None = None,
    silver_index_path: Path | None = None,
    candidate_events_path: Path | None = None,
    consumed_artifact_refs: dict[str, str] | None = None,
    calibration_version: str = "strategy_ladder_expected_edge.v1",
    timeframe: str = "1m",
    backtest_timeframes: tuple[str, ...] = (),
    requested_backtest_start: str = "",
    requested_backtest_days: int = 130,
    train_days: int = 180,
    validation_days: int = 30,
    freshness_days: int = 30,
    chunk_days: int = 30,
    feature_names_csv: str = "close_return,high_low_range,volume",
    sample_stride_minutes: int = 60,
    target_horizon_minutes: int = 1,
    training_seed: int = 5307,
    max_optuna_trials: int = 0,
    min_training_rows: int = 210,
    shap_summary_ref: str = "",
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
) -> CockpitBacktestJobRecord:
    """Create one audited local job record and execute the real launcher asynchronously."""

    timestamp_ms = _timestamp_ms()
    job_id = f"{job_kind.value}-{timestamp_ms}"
    correlation_id = f"cockpit-backtest-{timestamp_ms}"
    phase_run_id = f"{(phase_id or 'phase').lower()}-{timestamp_ms}"
    job_dir = jobs_root / job_id
    default_output_root = job_dir / "output"
    is_patch6_job = bool(action_name) or job_kind in {
        CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
        CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY,
    }
    is_workflow_phase_job = (
        phase_id in {PHASE_A1, PHASE_A2, PHASE_B1, PHASE_B_ML, PHASE_B2}
        or action_name
        in {
            StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
            StrategyLadderControlAction.PHASE_A2_DATA_FACTORY.value,
            StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value,
            StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY.value,
            StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value,
        }
        or bool(workflow_run_id.strip())
    )
    effective_workflow_run_id = workflow_run_id.strip() or (
        f"strategy_ladder_workflow-{(request_hash or str(timestamp_ms))[:16]}"
        if is_workflow_phase_job
        else job_id
    )
    workflow_root = (
        (Path(operator_output_root).expanduser() / "runs" / effective_workflow_run_id)
        if is_workflow_phase_job and (operator_output_root or "").strip()
        else (jobs_root / "workflows" / effective_workflow_run_id)
    )
    operator_output_root_candidate = (operator_output_root or "").strip()
    if is_workflow_phase_job:
        operator_output_root_candidate = str(
            (workflow_root / workflow_phase_dirname(phase_id or PHASE_A2)).resolve()
        )
    elif operator_output_root_candidate:
        operator_output_root_candidate = str(
            (Path(operator_output_root_candidate).expanduser() / "runs" / job_id).resolve()
        )
    output_root, output_root_status, output_root_blocker = resolve_output_root(
        operator_output_root=operator_output_root_candidate,
        default_output_root=default_output_root,
        raw_roots=raw_roots,
        allow_resume=(is_workflow_phase_job and (phase_id or PHASE_A2) == PHASE_A2),
    )
    if not blocked_reason and output_root_blocker:
        blocked_reason = output_root_blocker
    # Always create the resolved output root unless the operator path is being
    # rejected (in which case we still create the default for log placement).
    if output_root_blocker:
        default_output_root.mkdir(parents=True, exist_ok=True)
        output_root = default_output_root
    else:
        output_root.mkdir(parents=True, exist_ok=True)
    record_path = job_dir / "job.json"
    job_request_path = job_dir / "job_request.json"
    job_status_path = job_dir / "job_status.json"
    stdout_log_path = job_dir / "stdout.log"
    invalid_pair_tokens = tuple(
        token for token in pairs if is_path_like_pair_token(token)
    )
    if invalid_pair_tokens and not blocked_reason:
        blocked_reason = PAIR_ARG_INVALID_PATH
    if (
        raw_source_manifest_path is not None
        and not is_valid_raw_source_manifest_path(str(raw_source_manifest_path))
        and not blocked_reason
    ):
        blocked_reason = RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE
    if blocked_reason in {
        PAIR_ARG_INVALID_PATH,
        RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE,
        OUTPUT_ROOT_INVALID_PATH,
        OUTPUT_ROOT_INSIDE_RAW_ROOT,
        OUTPUT_ROOT_NOT_WRITABLE,
        OUTPUT_ROOT_EXISTS_NON_EMPTY,
    }:
        command = (
            python_executable or sys.executable,
            "blocked",
            "--reason",
            blocked_reason,
        )
    else:
        command = _build_backtest_command(
            job_id=job_id,
            job_kind=job_kind,
            cancel_file=job_dir / CANCEL_REQUEST_FILENAME,
            export_dir=export_dir,
            b2_run_root=b2_run_root,
            label_store_dataset_path=label_store_dataset_path,
            output_root=output_root,
            baseline_export_dir=baseline_export_dir,
            signed_by=signed_by,
            python_executable=python_executable or sys.executable,
            action_name=action_name,
            raw_source_manifest_path=raw_source_manifest_path,
            historical_metadata_root=historical_metadata_root,
            raw_roots=raw_roots,
            pairs=pairs,
            start=start,
            end=end,
            allow_broad_run=allow_broad_run,
            ml_mode_status=ml_mode_status,
            frozen_ml_artifact_path=frozen_ml_artifact_path,
            frozen_ml_artifact_hash=frozen_ml_artifact_hash,
            expected_edge_artifact_mode=expected_edge_artifact_mode,
            rolling_ml_window_plan_path=rolling_ml_window_plan_path,
            ml_artifact_freshness_days=ml_artifact_freshness_days,
            engine_native_mode=engine_native_mode,
            engine_native_sample_size=engine_native_sample_size,
            candidate_discovery_mode=candidate_discovery_mode,
            b1_5_policy_mode=b1_5_policy_mode,
            preselected_only=preselected_only,
            diagnostic_full_replay=diagnostic_full_replay,
            small_scope_enabled=small_scope_enabled,
            full_scan_enabled=full_scan_enabled,
            no_full_scan_enabled=no_full_scan_enabled,
            silver_storage_mode=silver_storage_mode,
            debug_storage_override=debug_storage_override,
            workflow_run_id=effective_workflow_run_id,
            phase_run_id=phase_run_id,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            feature_store_root=feature_store_root,
            silver_index_path=silver_index_path,
            candidate_events_path=candidate_events_path,
            calibration_version=calibration_version,
            timeframe=timeframe,
            backtest_timeframes=backtest_timeframes,
            requested_backtest_start=requested_backtest_start,
            requested_backtest_days=requested_backtest_days,
            train_days=train_days,
            validation_days=validation_days,
            freshness_days=freshness_days,
            chunk_days=chunk_days,
            feature_names_csv=feature_names_csv,
            sample_stride_minutes=sample_stride_minutes,
            target_horizon_minutes=target_horizon_minutes,
            training_seed=training_seed,
            max_optuna_trials=max_optuna_trials,
            min_training_rows=min_training_rows,
            shap_summary_ref=shap_summary_ref,
            bml_candidate_sampler_mode=bml_candidate_sampler_mode,
        )
    record = CockpitBacktestJobRecord(
        job_id=job_id,
        correlation_id=correlation_id,
        job_kind=job_kind,
        status=(
            CockpitBacktestJobStatus.JOB_BLOCKED
            if blocked_reason
            else (
                CockpitBacktestJobStatus.JOB_CREATED
                if is_patch6_job
                else CockpitBacktestJobStatus.REQUESTED
            )
        ),
        requested_at_iso=_utc_now_iso(),
        export_dir=str(export_dir.resolve()),
        baseline_export_dir=(
            str(baseline_export_dir.resolve())
            if baseline_export_dir is not None
            else ""
        ),
        output_root=str(output_root.resolve()),
        record_path=str(record_path.resolve()),
        stdout_log_path=str(stdout_log_path.resolve()),
        command=command,
        action_name=action_name,
        phase_id=phase_id,
        workflow_run_id=(effective_workflow_run_id if is_workflow_phase_job else ""),
        phase_run_id=(phase_run_id if is_workflow_phase_job else ""),
        parent_workflow_ref=(
            str(workflow_manifest_path(workflow_root).resolve())
            if is_workflow_phase_job
            else ""
        ),
        preview_id=preview_id,
        request_hash=request_hash,
        command_preview=" ".join(command),
        job_request_path=str(job_request_path.resolve()),
        job_status_path=str(job_status_path.resolve()),
        blockers=((blocked_reason,) if blocked_reason else ()),
        artifact_inventory_path=str(
            (
                output_root / "first_run_artifact_inventory.json"
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN
                else (output_root / "silver_index.json")
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
                else (
                    output_root
                    / "backtest_strategy_ladder"
                    / effective_workflow_run_id
                    / "fast_candidates"
                    / "candidate_summary.json"
                )
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
                else (output_root / "strategy_ladder_backtest_ml_input.json")
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF
                else (output_root / "labels" / "b_ml_label_store.jsonl")
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY
                else (output_root / "silver_index.json")
            ).resolve()
        ),
        stage_summary_path=str(
            (
                output_root / "first_run_stage_summary.json"
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN
                else (output_root / "strategy_ladder_ml_lab_handoff_report.json")
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF
                else (output_root / "reports" / "b_ml_training_dataset_audit.json")
                if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY
                else (
                    output_root / "data_factory_manifest.json"
                    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
                    else (
                        output_root
                        / "backtest_strategy_ladder"
                        / (
                            effective_workflow_run_id
                            if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
                            else job_id
                        )
                        / "reports"
                        / "strategy_ladder_summary.json"
                    )
                )
            ).resolve()
        ),
        allow_broad_run=allow_broad_run,
        ml_mode_status=ml_mode_status,
        frozen_ml_artifact_path=(
            str(frozen_ml_artifact_path.resolve())
            if frozen_ml_artifact_path is not None
            else ""
        ),
        frozen_ml_artifact_hash=frozen_ml_artifact_hash,
        rolling_ml_window_plan_path=(
            str(rolling_ml_window_plan_path.resolve())
            if rolling_ml_window_plan_path is not None
            else ""
        ),
        ml_artifact_freshness_days=max(int(ml_artifact_freshness_days), 1),
        candidate_discovery_mode=candidate_discovery_mode,
        bml_candidate_sampler_mode=bml_candidate_sampler_mode,
        engine_native_sample_size=engine_native_sample_size,
        backtest_timeframes=backtest_timeframes or ("1m",),
        b1_5_policy_mode=b1_5_policy_mode,
        preselected_only=preselected_only,
        diagnostic_full_replay=diagnostic_full_replay,
        small_scope_enabled=small_scope_enabled,
        full_scan_enabled=full_scan_enabled,
        no_full_scan_enabled=no_full_scan_enabled,
        silver_storage_mode=silver_storage_mode,
        consumed_artifact_refs=dict(consumed_artifact_refs or {}),
    )
    if is_workflow_phase_job:
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id=effective_workflow_run_id,
            request_hash=request_hash,
            phase_id=phase_id or PHASE_A2,
            pairs=pairs,
            start=start,
            end=end,
            ml_mode=ml_mode_status,
            candidate_discovery_mode=candidate_discovery_mode,
            engine_native_sample_size=engine_native_sample_size,
            b1_5_policy_mode=b1_5_policy_mode,
            preselected_only=preselected_only,
            diagnostic_full_replay=diagnostic_full_replay,
            engine_count=4,
            allow_broad_run=allow_broad_run,
            small_scope_enabled=small_scope_enabled,
            full_scan_enabled=full_scan_enabled,
            no_full_scan_enabled=no_full_scan_enabled,
            silver_storage_mode_requested=silver_storage_mode,
            silver_storage_mode_effective=silver_storage_mode,
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id=effective_workflow_run_id,
            phase_id=phase_id or PHASE_A2,
            phase_run_id=phase_run_id,
            phase_output_root=output_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            job_id=job_id,
            request_hash=request_hash,
            phase_status=_initial_phase_status(
                phase_id=phase_id or PHASE_A2,
                blocked_reason=blocked_reason,
            ),
            blocker_codes=((blocked_reason,) if blocked_reason else ()),
            error_code=blocked_reason if blocked_reason else "",
            stderr_ref=str(stdout_log_path.resolve()),
            consumed_artifact_refs=dict(consumed_artifact_refs or {}),
        )
    _write_backtest_job_record(record_path, record)
    _write_patch6_job_request(
        job_request_path,
        record=record,
        raw_source_manifest_path=raw_source_manifest_path,
        historical_metadata_root=historical_metadata_root,
        raw_roots=raw_roots,
        pairs=pairs,
        start=start,
        end=end,
        b2_run_root=b2_run_root,
        label_store_dataset_path=label_store_dataset_path,
        calibration_version=calibration_version,
        timeframe=timeframe,
        backtest_timeframes=backtest_timeframes,
        requested_backtest_start=requested_backtest_start,
        requested_backtest_days=requested_backtest_days,
        train_days=train_days,
        validation_days=validation_days,
        freshness_days=freshness_days,
        chunk_days=chunk_days,
        feature_names_csv=feature_names_csv,
        sample_stride_minutes=sample_stride_minutes,
        target_horizon_minutes=target_horizon_minutes,
        training_seed=training_seed,
        max_optuna_trials=max_optuna_trials,
        min_training_rows=min_training_rows,
        shap_summary_ref=shap_summary_ref,
        engine_native_mode=engine_native_mode,
        engine_native_sample_size=engine_native_sample_size,
        frozen_ml_artifact_path=frozen_ml_artifact_path,
        frozen_ml_artifact_hash=frozen_ml_artifact_hash,
        rolling_ml_window_plan_path=rolling_ml_window_plan_path,
        ml_artifact_freshness_days=ml_artifact_freshness_days,
        b1_5_policy_mode=b1_5_policy_mode,
        preselected_only=preselected_only,
        diagnostic_full_replay=diagnostic_full_replay,
        feature_store_root=feature_store_root,
        silver_index_path=silver_index_path,
        candidate_events_path=candidate_events_path,
    )
    _write_patch6_job_status(job_status_path, record)
    if blocked_reason:
        return record
    worker = threading.Thread(
        target=_run_backtest_job,
        kwargs={"record_path": record_path, "record": record},
        name=f"cockpit-backtest-{job_id}",
        daemon=True,
    )
    worker.start()
    return record


def request_job_cancel(
    *,
    jobs_root: Path,
    job_id: str,
    requested_by: str = "cockpit_operator",
    operator_reason: str = "operator_requested_cancel",
) -> tuple[str, str]:
    """Write the ``cancel_request.json`` sidecar for a running job.

    Returns ``(status_code, blocker_reason)``. Status codes:
      - ``JOB_CANCELLING``      — request was written, worker will pick it up
      - ``JOB_NOT_RUNNING``     — record exists but job is already in a terminal state
      - ``JOB_CANCEL_FAILED``   — record missing, pid unknown, or write error
    """

    if not jobs_root.is_dir():
        return CockpitBacktestJobStatus.JOB_CANCEL_FAILED.value, JOB_ID_NOT_FOUND
    job_dir = jobs_root / job_id
    record_path = job_dir / "job.json"
    if not record_path.is_file():
        return CockpitBacktestJobStatus.JOB_CANCEL_FAILED.value, JOB_ID_NOT_FOUND
    try:
        record = CockpitBacktestJobRecord.model_validate_json(
            record_path.read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError):
        return CockpitBacktestJobStatus.JOB_CANCEL_FAILED.value, JOB_ID_NOT_FOUND
    # Reject non-running jobs explicitly.
    if record.status in _TERMINAL_JOB_STATUSES:
        return CockpitBacktestJobStatus.JOB_NOT_RUNNING.value, ""
    if not record.pid:
        return CockpitBacktestJobStatus.JOB_CANCEL_FAILED.value, PID_NOT_FOUND
    cancel_path = job_dir / CANCEL_REQUEST_FILENAME
    payload = {
        "job_id": job_id,
        "pid": record.pid,
        "requested_at": _utc_now_iso(),
        "requested_by": requested_by,
        "reason": operator_reason,
    }
    try:
        atomic_write_json(cancel_path, payload, indent=2)
    except OSError:
        return CockpitBacktestJobStatus.JOB_CANCEL_FAILED.value, "CANCEL_REQUEST_WRITE_FAILED"
    return CockpitBacktestJobStatus.JOB_CANCELLING.value, ""


def load_backtest_job_records(
    jobs_root: Path,
    *,
    limit: int = 8,
) -> tuple[CockpitBacktestJobRecord, ...]:
    """Return the most recent bounded set of cockpit backtest jobs."""

    if not jobs_root.is_dir():
        return ()
    records: list[CockpitBacktestJobRecord] = []
    for path in jobs_root.glob("*/job.json"):
        try:
            record = CockpitBacktestJobRecord.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, TypeError, ValueError):
            continue
        records.append(_reconcile_stale_job_record(path, record))
    records.sort(
        key=lambda record: _parse_iso(record.latest_activity_iso)
        or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    return tuple(records[:limit])


def _build_governed_request(
    *,
    command_kind: DashboardGovernedCommandKind,
    requested_by: str,
    operator_reason: str,
    artifact_manifest: DashboardArtifactTransferManifest | None = None,
    target_pair: str = "",
) -> DashboardGovernedCommandRequest:
    timestamp_ms = _timestamp_ms()
    request_id = f"cockpit-{command_kind.value}-{timestamp_ms}"
    correlation_id = f"cockpit-governed-{timestamp_ms}"
    return DashboardGovernedCommandRequest(
        timestamp_ms=timestamp_ms,
        correlation_id=correlation_id,
        request_id=request_id,
        command_kind=command_kind,
        source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
        target_runtime_mode=RuntimeMode.SHADOW,
        requested_by=requested_by,
        operator_reason=operator_reason,
        target_pair=target_pair,
        artifact_manifest=artifact_manifest,
    )


def _csv_feature_names(raw_value: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            part.strip() for part in (raw_value or "").split(",") if part.strip()
        )
    )


def _build_backtest_command(
    *,
    job_id: str,
    job_kind: CockpitBacktestJobKind,
    cancel_file: Path | None = None,
    export_dir: Path,
    b2_run_root: Path | None = None,
    label_store_dataset_path: Path | None = None,
    output_root: Path,
    baseline_export_dir: Path | None,
    signed_by: str,
    python_executable: str,
    action_name: str,
    raw_source_manifest_path: Path | None,
    historical_metadata_root: Path | None = None,
    raw_roots: tuple[Path, ...],
    pairs: tuple[str, ...],
    start: str,
    end: str,
    allow_broad_run: bool,
    ml_mode_status: str,
    frozen_ml_artifact_path: Path | None = None,
    frozen_ml_artifact_hash: str = "",
    expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY",
    rolling_ml_window_plan_path: Path | None = None,
    ml_artifact_freshness_days: int = 30,
    engine_native_mode: bool,
    engine_native_sample_size: int,
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG",
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
    b1_5_policy_mode: str = "conservative_hard_only",
    preselected_only: bool = True,
    diagnostic_full_replay: bool = False,
    small_scope_enabled: bool = True,
    full_scan_enabled: bool = False,
    no_full_scan_enabled: bool = True,
    silver_storage_mode: str = "jsonl_debug",
    debug_storage_override: bool = False,
    workflow_run_id: str = "",
    phase_run_id: str = "",
    parent_workflow_ref: str = "",
    feature_store_root: Path | None = None,
    silver_index_path: Path | None = None,
    candidate_events_path: Path | None = None,
    calibration_version: str = "strategy_ladder_expected_edge.v1",
    timeframe: str = "1m",
    backtest_timeframes: tuple[str, ...] = (),
    requested_backtest_start: str = "",
    requested_backtest_days: int = 130,
    train_days: int = 180,
    validation_days: int = 30,
    freshness_days: int = 30,
    chunk_days: int = 30,
    feature_names_csv: str = "close_return,high_low_range,volume",
    sample_stride_minutes: int = 60,
    target_horizon_minutes: int = 1,
    training_seed: int = 5307,
    max_optuna_trials: int = 0,
    min_training_rows: int = 210,
    shap_summary_ref: str = "",
) -> tuple[str, ...]:
    invalid_pair_tokens = tuple(token for token in pairs if is_path_like_pair_token(token))
    if invalid_pair_tokens:
        raise ValueError(
            f"{PAIR_ARG_INVALID_PATH}: refused to emit --pairs containing filesystem path(s): "
            + ", ".join(invalid_pair_tokens)
        )
    if raw_source_manifest_path is not None and not is_valid_raw_source_manifest_path(
        str(raw_source_manifest_path)
    ):
        raise ValueError(
            f"{RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE}: --raw-source-manifest must point "
            f"to a .json file, got: {raw_source_manifest_path}"
        )
    if job_kind == CockpitBacktestJobKind.LOCAL_LAB_ANALYSIS_BUNDLE:
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_local_lab_analysis_bundle.py"),
            "--export-dir",
            str(export_dir.resolve()),
            "--signed-by",
            signed_by,
            "--output-root",
            str(output_root.resolve()),
        ]
        if baseline_export_dir is not None:
            command.extend(
                ["--baseline-export-dir", str(baseline_export_dir.resolve())]
            )
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.LOCAL_LAB_POST_TRADE_REVIEW:
        return (
            python_executable,
            str(REPO_ROOT / "scripts" / "run_local_lab_post_trade_review.py"),
            "--export-dir",
            str(export_dir.resolve()),
            "--correlation-id",
            f"cockpit-review-{_timestamp_ms()}",
            "--output-dir",
            str(output_root.resolve()),
        )
    if job_kind == CockpitBacktestJobKind.EDGE_GATE_CALIBRATION:
        return (
            python_executable,
            str(REPO_ROOT / "scripts" / "run_edge_gate_calibration.py"),
            "--export-dir",
            str(export_dir.resolve()),
            "--output-path",
            str((output_root / "edge_gate.yml").resolve()),
            "--signed-by",
            signed_by,
        )
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF:
        pair = pairs[0] if pairs else "BTCUSDT"
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_strategy_ladder_ml_lab_handoff.py"),
            "--artifact-id",
            job_id,
            "--calibration-version",
            calibration_version,
            "--kline-root",
            str(export_dir.resolve()),
            "--export-dir",
            str(output_root.resolve()),
            "--pair",
            pair,
            "--timeframe",
            timeframe or "1m",
            "--train-start",
            start,
            "--train-end",
            end,
            "--requested-backtest-days",
            str(max(int(requested_backtest_days), 1)),
            "--train-days",
            str(max(int(train_days), 1)),
            "--validation-days",
            str(max(int(validation_days), 1)),
            "--freshness-days",
            str(max(int(freshness_days), 1)),
            "--chunk-days",
            str(max(int(chunk_days), 1)),
            "--feature-names",
            feature_names_csv or "close_return,high_low_range,volume",
            "--sample-stride-minutes",
            str(max(int(sample_stride_minutes), 1)),
            "--target-horizon-minutes",
            str(max(int(target_horizon_minutes), 1)),
            "--training-seed",
            str(int(training_seed)),
            "--max-optuna-trials",
            str(max(int(max_optuna_trials), 0)),
            "--min-training-rows",
            str(max(int(min_training_rows), 10)),
        ]
        if b2_run_root is not None:
            command.extend(["--b2-run-root", str(b2_run_root.resolve())])
        if label_store_dataset_path is not None:
            command.extend(
                [
                    "--label-store-dataset-path",
                    str(label_store_dataset_path.resolve()),
                ]
            )
        if requested_backtest_start:
            command.extend(["--requested-backtest-start", requested_backtest_start])
        if (shap_summary_ref or "").strip():
            command.extend(["--shap-summary-ref", shap_summary_ref.strip()])
        # Patch P2b (2026-05-22) — when admin selected ≥ 2 pairs in Lab UI,
        # propagate them so the handoff emits a MULTI_PAIR_C1 manifest.
        if len(pairs) >= 2:
            command.extend(["--selected-pairs", ",".join(pairs)])
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY:
        a2_run_root = (
            feature_store_root.parent.resolve()
            if feature_store_root is not None and feature_store_root.name == "gold"
            else feature_store_root.resolve()
            if feature_store_root is not None
            else output_root.resolve().parent / "phase_a2_data_factory"
        )
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_strategy_ladder_b_ml_label_factory.py"),
            "--workflow-run-id",
            workflow_run_id or job_id,
            "--a2-run-root",
            str(a2_run_root),
            "--output-root",
            str(output_root.resolve()),
            "--pairs",
            ",".join(pairs) if pairs else "BTCUSDT",
            "--timeframes",
            ",".join(backtest_timeframes or (timeframe or "1m",)),
            "--start",
            start,
            "--end",
            end,
            "--label-horizons",
            "5m,15m,1h",
            "--capital-buckets",
            "400,500,1500,4000",
            "--feature-names",
            feature_names_csv or "close_return,high_low_range,volume",
            "--candidate-sampler-mode",
            bml_candidate_sampler_mode or "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
        ]
        if candidate_events_path is not None:
            command.extend(["--b1-candidate-events-path", str(candidate_events_path.resolve())])
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_CHUNKED:
        # Phase 3 chunked rail (2026-06-05): the monolithic A2->B1->B2 run is
        # executed as a per-day chunk map by run_chunked_backtest.py (RAM-safe,
        # resumable). The run lands at ``output_root`` (chunks/<label>/...,
        # chunk_index.json) and is observed read-only on /backtest/chunked.
        resolved_run_root = output_root.resolve()
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_chunked_backtest.py"),
            "--run-id",
            resolved_run_root.name,
            "--output-root",
            str(resolved_run_root.parent),
            "--start",
            start,
            "--end",
            end,
            "--chunk",
            "1d",
            "--engine-native-sample-size",
            str(max(engine_native_sample_size, 0)),
            "--candidate-discovery-mode",
            candidate_discovery_mode or "TEMPORAL_STRATIFIED",
            "--candidate-sample-cap",
            str(max(engine_native_sample_size, 0)),
            "--b1-5-policy-mode",
            b1_5_policy_mode,
            "--storage-format",
            (
                "jsonl-gz"
                if silver_storage_mode == "jsonl_gz"
                else "parquet"
                if silver_storage_mode == "parquet"
                else "jsonl"
            ),
            "--ml-mode",
            ml_mode_status,
            "--max-workers",
            "1",
        ]
        if pairs:
            command.extend(["--pairs", ",".join(pairs)])
        if backtest_timeframes:
            command.extend(["--timeframes", ",".join(backtest_timeframes)])
        # Scoped governed default (2026-06-08): the chunked rail materializes A2
        # gold for the whole run, so a legacy-only selection is upgraded to the
        # governed microstructure set (explicit microstructure picks honored).
        command.extend(
            ["--feature-names", _scoped_chunked_feature_names_csv(feature_names_csv)]
        )
        for raw_root in raw_roots:
            command.extend(["--raw-root", str(raw_root.resolve())])
        if raw_source_manifest_path is not None:
            command.extend(["--raw-source-manifest", str(raw_source_manifest_path.resolve())])
        if historical_metadata_root is not None:
            command.extend(["--historical-metadata-root", str(historical_metadata_root.resolve())])
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER:
        resolved_candidate_sample_cap = (
            0
            if str(candidate_discovery_mode or "").strip().upper() == "FULL_DISCOVERY"
            and full_scan_enabled
            else max(engine_native_sample_size, 0)
        )
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_backtest_strategy_ladder.py"),
            "--run-id",
            workflow_run_id or job_id,
            "--input-root",
            str(output_root.resolve()),
            "--output-root",
            str(output_root.resolve()),
            "--workflow-run-id",
            workflow_run_id or job_id,
            "--ml-mode",
            ml_mode_status,
            "--engine-native-mode",
            "--engine-native-sample-size",
            str(max(engine_native_sample_size, 0)),
            "--candidate-discovery-mode",
            candidate_discovery_mode,
            "--candidate-sample-cap",
            str(resolved_candidate_sample_cap),
            "--b1-5-policy-mode",
            b1_5_policy_mode,
        ]
        if ml_mode_status == "ML_MODE_OVERLAY_FROZEN":
            if frozen_ml_artifact_path is not None:
                command.extend(
                    ["--frozen-ml-artifact-path", str(frozen_ml_artifact_path.resolve())]
                )
            if frozen_ml_artifact_hash:
                command.extend(["--frozen-ml-artifact-hash", frozen_ml_artifact_hash])
            if rolling_ml_window_plan_path is not None:
                command.extend(
                    [
                        "--rolling-ml-window-plan-path",
                        str(rolling_ml_window_plan_path.resolve()),
                    ]
                )
            command.extend(
                [
                    "--ml-artifact-freshness-days",
                    str(max(int(ml_artifact_freshness_days), 1)),
                ]
            )
            # Patch P3 (2026-05-22) — always emit explicit mode (default safe).
            command.extend(
                [
                    "--expected-edge-artifact-mode",
                    expected_edge_artifact_mode or "MONO_PAIR_LEGACY",
                ]
            )
        if preselected_only and not diagnostic_full_replay:
            command.append("--preselected-only")
        if diagnostic_full_replay:
            command.extend(["--no-preselected-only", "--diagnostic-full-replay"])
        if phase_run_id:
            command.extend(["--phase-run-id", phase_run_id])
        if parent_workflow_ref:
            command.extend(["--parent-workflow-ref", parent_workflow_ref])
        if small_scope_enabled:
            command.append("--small-scope-enabled")
        if full_scan_enabled:
            command.append("--full-scan-enabled")
        if no_full_scan_enabled:
            command.append("--no-full-scan-enabled")
        if feature_store_root is not None:
            command.extend(["--feature-store-root", str(feature_store_root.resolve())])
        if silver_index_path is not None:
            command.extend(["--silver-index-path", str(silver_index_path.resolve())])
        for raw_root in raw_roots:
            command.extend(["--raw-root", str(raw_root.resolve())])
        if raw_source_manifest_path is not None:
            command.extend(["--raw-source-manifest", str(raw_source_manifest_path.resolve())])
        if pairs:
            command.extend(["--pairs", ",".join(pairs)])
        if backtest_timeframes:
            command.extend(["--timeframes", ",".join(backtest_timeframes)])
        if (feature_names_csv or "").strip():
            command.extend(["--feature-names", feature_names_csv.strip()])
        if start:
            command.extend(["--start", start])
        if end:
            command.extend(["--end", end])
        if action_name == StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value:
            command.append("--fast-only")
            command.extend(["--raw-window-mode", "REFS_ONLY"])
        if action_name == StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value:
            command.extend(["--detailed-only", "--resume"])
            if candidate_events_path is not None:
                command.extend(["--candidate-events-path", str(candidate_events_path.resolve())])
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY:
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_strategy_ladder_data_factory.py"),
            "--run-id",
            workflow_run_id or job_id,
            "--output-root",
            str(output_root.resolve()),
            "--silver-root",
            str((output_root / "silver").resolve()),
            "--gold-root",
            str((output_root / "gold").resolve()),
            "--storage-format",
            (
                "jsonl-gz"
                if silver_storage_mode == "jsonl_gz"
                else "parquet"
                if silver_storage_mode == "parquet"
                else "jsonl"
            ),
        ]
        for raw_root in raw_roots:
            command.extend(["--raw-root", str(raw_root.resolve())])
        if raw_source_manifest_path is not None:
            command.extend(["--raw-source-manifest", str(raw_source_manifest_path.resolve())])
        if historical_metadata_root is not None:
            command.extend(["--historical-metadata-root", str(historical_metadata_root.resolve())])
        if pairs:
            command.extend(["--pairs", ",".join(pairs)])
        if backtest_timeframes:
            command.extend(["--timeframes", ",".join(backtest_timeframes)])
        if (feature_names_csv or "").strip():
            command.extend(["--feature-names", feature_names_csv.strip()])
        if start:
            command.extend(["--start", start])
        if end:
            command.extend(["--end", end])
        if small_scope_enabled:
            command.append("--small-scope")
        if allow_broad_run:
            command.append("--allow-broad-run")
        if debug_storage_override:
            command.append("--debug-storage-override")
        if cancel_file is not None:
            # Patch GOLD-CANCEL (2026-06-01) — the gold build polls this sidecar
            # (the same cancel_request.json request_job_cancel writes) and stops
            # within seconds of an operator cancel.
            command.extend(["--cancel-file", str(cancel_file)])
        if action_name in {
            StrategyLadderControlAction.DATA_FACTORY_DRY_RUN.value,
            StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
        }:
            command.append("--dry-run")
        return tuple(command)
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN:
        command = [
            python_executable,
            str(REPO_ROOT / "scripts" / "run_strategy_ladder_first_controlled_run.py"),
            "--run-id",
            workflow_run_id or job_id,
            "--input-root",
            str(output_root.resolve()),
            "--output-root",
            str(output_root.resolve()),
            "--silver-root",
            str((output_root / "silver").resolve()),
            "--gold-root",
            str((output_root / "gold").resolve()),
            "--ml-mode",
            ml_mode_status,
            "--silver-storage-mode",
            silver_storage_mode,
        ]
        if ml_mode_status == "ML_MODE_OVERLAY_FROZEN":
            if frozen_ml_artifact_path is not None:
                command.extend(
                    ["--frozen-ml-artifact-path", str(frozen_ml_artifact_path.resolve())]
                )
            if frozen_ml_artifact_hash:
                command.extend(["--frozen-ml-artifact-hash", frozen_ml_artifact_hash])
        if small_scope_enabled:
            command.append("--small-scope")
        if no_full_scan_enabled:
            command.append("--no-full-scan")
        if engine_native_mode:
            command.extend(
                [
                    "--engine-native-mode",
                    "--engine-native-sample-size",
                    str(max(engine_native_sample_size, 0)),
                ]
            )
        for raw_root in raw_roots:
            command.extend(["--raw-root", str(raw_root.resolve())])
        if raw_source_manifest_path is not None:
            command.extend(["--raw-source-manifest", str(raw_source_manifest_path.resolve())])
        if historical_metadata_root is not None:
            command.extend(["--historical-metadata-root", str(historical_metadata_root.resolve())])
        if pairs:
            command.extend(["--pairs", ",".join(pairs)])
        if (feature_names_csv or "").strip():
            command.extend(["--feature-names", feature_names_csv.strip()])
        if start:
            command.extend(["--start", start])
        if end:
            command.extend(["--end", end])
        if allow_broad_run:
            command.append("--allow-broad-run")
        if debug_storage_override:
            command.append("--debug-storage-override")
        if action_name == StrategyLadderControlAction.FIRST_CONTROLLED_RUN_DRY_RUN.value:
            command.append("--dry-run")
        return tuple(command)
    raise ValueError(f"Unsupported cockpit backtest job kind: {job_kind}")


def _initial_phase_status(
    *,
    phase_id: str,
    blocked_reason: str,
) -> str:
    if not blocked_reason:
        return "PHASE_JOB_CREATED"
    if phase_id == PHASE_A2:
        if blocked_reason == "SILVER_STORAGE_BLOAT_BLOCKER":
            return PHASE_STATUS_STORAGE_BLOCKED
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
    if phase_id == PHASE_B1:
        return PHASE_STATUS_DISCOVERY_BLOCKED
    if phase_id == PHASE_B_ML:
        return PHASE_STATUS_BML_BLOCKED
    if phase_id == PHASE_B2:
        if blocked_reason == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY":
            return PHASE_STATUS_PROMOTION_BLOCKED
        return PHASE_STATUS_PROOF_BLOCKED
    return "PHASE_JOB_BLOCKED"


def _cancel_request_path_for(record: CockpitBacktestJobRecord) -> Path:
    """Return the cancel_request.json sidecar path for a given job record."""

    job_dir = Path(record.record_path).parent if record.record_path else Path()
    return job_dir / CANCEL_REQUEST_FILENAME


def _terminal_sentinel_path_for(record: CockpitBacktestJobRecord) -> Path:
    job_dir = Path(record.record_path).parent if record.record_path else Path()
    return job_dir / "terminal_sentinel.json"


def _read_cancel_request(record: CockpitBacktestJobRecord) -> dict[str, object]:
    path = _cancel_request_path_for(record)
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _run_backtest_job(
    *,
    record_path: Path,
    record: CockpitBacktestJobRecord,
) -> None:
    running = record
    stdout_log_path = Path(record.stdout_log_path)
    stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
    # Patch 6 batch 2 — Popen-based execution with cooperative cancel polling.
    # subprocess.run was blocking which made the cockpit Cancel button
    # impossible. Polling at 0.5 s is cheap relative to multi-minute backtests.
    cancel_observed = False
    cancel_reason = ""
    termination_method = ""
    cancelled_at = ""
    postrun_stall_recovered = False
    handle = stdout_log_path.open("w", encoding="utf-8")
    try:
        popen_kwargs: dict[str, object] = {
            "cwd": str(REPO_ROOT),
            "stdin": subprocess.DEVNULL,
            "stdout": handle,
            "stderr": subprocess.STDOUT,
            "text": True,
            "env": os.environ.copy(),
        }
        if record.job_kind in {
            CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        }:
            popen_kwargs["env"][COCKPIT_JOB_TERMINAL_SENTINEL_ENV] = str(
                _terminal_sentinel_path_for(record).resolve()
            )
        if os.name == "nt":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        else:
            popen_kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(record.command, **popen_kwargs)
        except OSError as exc:
            handle.write(f"JOB_PROCESS_START_FAILED: {exc.__class__.__name__}: {exc}\n")
            handle.flush()
            failed = record.model_copy(
                update={
                    "status": (
                        CockpitBacktestJobStatus.JOB_FAILED
                        if record.status == CockpitBacktestJobStatus.JOB_CREATED
                        else CockpitBacktestJobStatus.FAILED
                    ),
                    "started_at_iso": _utc_now_iso(),
                    "finished_at_iso": _utc_now_iso(),
                    "error_summary": f"process_start_failed:{exc.__class__.__name__}",
                    "blockers": tuple(
                        dict.fromkeys((*record.blockers, "JOB_PROCESS_START_FAILED"))
                    ),
                }
            )
            _write_backtest_job_record(record_path, failed)
            if failed.job_status_path:
                _write_patch6_job_status(Path(failed.job_status_path), failed)
            if failed.workflow_run_id and failed.parent_workflow_ref:
                workflow_root = Path(failed.parent_workflow_ref).parent
                upsert_workflow_phase(
                    workflow_root=workflow_root,
                    workflow_run_id=failed.workflow_run_id,
                    phase_id=failed.phase_id or PHASE_A2,
                    phase_run_id=failed.phase_run_id or failed.job_id,
                    phase_output_root=Path(failed.output_root),
                    parent_workflow_ref=failed.parent_workflow_ref,
                    job_id=failed.job_id,
                    request_hash=failed.request_hash,
                    phase_status=_phase_status_from_finished_record(failed),
                    blocker_codes=failed.blockers,
                    error_code=_phase_error_code_from_record(failed),
                    stderr_ref=failed.stdout_log_path,
                    consumed_artifact_refs=dict(failed.consumed_artifact_refs),
                    produced_artifact_refs=dict(failed.produced_artifact_refs),
                    artifact_hashes=dict(failed.artifact_hashes),
                    phase_started_at=failed.started_at_iso,
                    phase_completed_at=failed.finished_at_iso,
                )
            return
        running = record.model_copy(
            update={
                "status": (
                    CockpitBacktestJobStatus.JOB_RUNNING
                    if record.status == CockpitBacktestJobStatus.JOB_CREATED
                    else CockpitBacktestJobStatus.RUNNING
                ),
                "started_at_iso": _utc_now_iso(),
                "pid": process.pid,
            }
        )
        _write_backtest_job_record(record_path, running)
        if running.job_status_path:
            _write_patch6_job_status(Path(running.job_status_path), running)
        return_code: int | None = None
        while True:
            try:
                return_code = process.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                pass
            cancel_payload = _read_cancel_request(running)
            if cancel_payload and not cancel_observed:
                cancel_observed = True
                cancel_reason = str(cancel_payload.get("reason") or "operator_cancel")
                cancelled_at = _utc_now_iso()
                # Mark JOB_CANCELLING in the record so the UI can update.
                cancelling = running.model_copy(
                    update={
                        "status": CockpitBacktestJobStatus.JOB_CANCELLING,
                        "cancel_requested_at": str(
                            cancel_payload.get("requested_at") or _utc_now_iso()
                        ),
                        "cancel_reason": cancel_reason,
                    }
                )
                _write_backtest_job_record(record_path, cancelling)
                if running.job_status_path:
                    _write_patch6_job_status(Path(running.job_status_path), cancelling)
                # Try a graceful terminate first.
                try:
                    process.terminate()
                    termination_method = "SIGTERM"
                except OSError:
                    termination_method = "SIGTERM_FAILED"
                try:
                    return_code = process.wait(timeout=10.0)
                    break
                except subprocess.TimeoutExpired:
                    # Force kill.
                    try:
                        process.kill()
                        termination_method = "SIGKILL"
                    except OSError:
                        termination_method = "SIGKILL_FAILED"
                    try:
                        return_code = process.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        return_code = -1
                    break
            if _should_recover_strategy_ladder_postrun_stall(running):
                try:
                    process.terminate()
                    termination_method = "POSTRUN_TERMINATE"
                except OSError:
                    termination_method = "POSTRUN_TERMINATE_FAILED"
                try:
                    return_code = process.wait(timeout=10.0)
                    postrun_stall_recovered = True
                    break
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                        termination_method = "POSTRUN_KILL"
                    except OSError:
                        termination_method = "POSTRUN_KILL_FAILED"
                    try:
                        return_code = process.wait(timeout=5.0)
                        postrun_stall_recovered = True
                    except subprocess.TimeoutExpired:
                        return_code = -1
                    break
        completed_returncode = return_code if return_code is not None else -1
    finally:
        handle.close()

    output_root = Path(running.output_root)
    output_refs = _collect_output_refs(output_root)
    harvested_blockers, harvested_stage_statuses = harvest_manifest_blockers(output_root)
    merged_blockers = tuple(
        dict.fromkeys((*running.blockers, *harvested_blockers))
    )
    merged_stage_statuses = {**running.stage_statuses, **harvested_stage_statuses}
    if cancel_observed:
        if termination_method == "SIGKILL":
            final_status = CockpitBacktestJobStatus.JOB_KILLED
        else:
            final_status = CockpitBacktestJobStatus.JOB_CANCELLED
    elif postrun_stall_recovered:
        final_status = _terminal_status_from_record_artifacts(
            record=running,
            blockers=merged_blockers,
            stage_statuses=merged_stage_statuses,
        )
    else:
        final_status = (
            (
                (
                    CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS
                    if merged_blockers
                    else CockpitBacktestJobStatus.JOB_COMPLETED
                )
                if completed_returncode == 0
                else (
                    CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS
                    if merged_blockers
                    else CockpitBacktestJobStatus.JOB_FAILED
                )
            )
            if running.status == CockpitBacktestJobStatus.JOB_RUNNING
            else (
                CockpitBacktestJobStatus.COMPLETED
                if completed_returncode == 0
                else CockpitBacktestJobStatus.FAILED
            )
        )
    error_summary = ""
    if cancel_observed:
        error_summary = f"cancelled:{cancel_reason}"
    elif postrun_stall_recovered:
        error_summary = JOB_TERMINAL_ARTIFACT_STALL_RECOVERED
    elif completed_returncode != 0:
        error_summary = f"exit_code={completed_returncode}"
    finished = running.model_copy(
        update={
            "status": final_status,
            "finished_at_iso": (
                _finished_at_from_artifacts(running)
                if postrun_stall_recovered
                else _utc_now_iso()
            ),
            "output_refs": output_refs,
            "error_summary": error_summary,
            "blockers": merged_blockers,
            "stage_statuses": merged_stage_statuses,
            "produced_artifact_refs": {
                Path(ref).name: ref for ref in output_refs
            },
            "artifact_hashes": {
                Path(ref).name: _sha256_path(Path(ref))
                for ref in output_refs
                if Path(ref).is_file()
            },
            # Patch 6 batch 2 — cancel telemetry.
            "cancelled_at": cancelled_at,
            "cancel_reason": cancel_reason,
            "termination_method": termination_method,
        }
    )
    _write_backtest_job_record(record_path, finished)
    if finished.job_status_path:
        _write_patch6_job_status(Path(finished.job_status_path), finished)
    if finished.workflow_run_id and finished.parent_workflow_ref:
        workflow_root = Path(finished.parent_workflow_ref).parent
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id=finished.workflow_run_id,
            phase_id=finished.phase_id or PHASE_A2,
            phase_run_id=finished.phase_run_id or finished.job_id,
            phase_output_root=output_root,
            parent_workflow_ref=finished.parent_workflow_ref,
            job_id=finished.job_id,
            request_hash=finished.request_hash,
            phase_status=_phase_status_from_finished_record(finished),
            blocker_codes=finished.blockers,
            error_code=_phase_error_code_from_record(finished),
            stderr_ref=finished.stdout_log_path,
            consumed_artifact_refs=dict(finished.consumed_artifact_refs),
            produced_artifact_refs=dict(finished.produced_artifact_refs),
            artifact_hashes=dict(finished.artifact_hashes),
            phase_started_at=finished.started_at_iso,
            phase_completed_at=finished.finished_at_iso,
        )


_MANIFEST_BLOCKER_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("data_factory_manifest.json", ("blocker_codes", "blockers")),
    ("first_run_manifest.json", ("blocker_codes", "blockers")),
    ("first_run_stage_summary.json", ("blockers", "blocker_codes")),
    ("first_run_blockers.json", ("blockers", "blocker_codes")),
    ("raw_window_failure_report.json", ("blocker_codes", "blockers")),
    ("pair_universe_report.json", ("blockers", "blocker_codes")),
    ("gold_feature_manifest.json", ("blockers", "blocker_codes")),
    ("silver_index.json", ("blockers", "blocker_codes")),
    ("data_quality_report.json", ("blockers", "blocker_codes")),
    ("strategy_ladder_ml_lab_handoff_report.json", ("blocking_reasons", "blockers", "blocker_codes")),
    ("reports/b_ml_training_dataset_audit.json", ("blockers", "blocker_codes")),
    ("manifests/b_ml_label_factory_manifest.json", ("blockers", "blocker_codes")),
)


def _read_json_payload(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


_A2_RESEARCH_ACCEPTABLE_BLOCKERS: frozenset[str] = frozenset(
    {
        "RAW_SOURCE_TYPE_INFERRED",
        "CURRENT_METADATA_PROXY",
        "SINGLE_PAIR_RESEARCH_ONLY",
        "SILVER_STORAGE_AUTO_COMPRESSED_FOR_BROAD_RUN",
        "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE",
    }
)


def is_a2_research_acceptable_blocker(blocker_code: str) -> bool:
    code = str(blocker_code or "").strip()
    if not code:
        return False
    if code in _A2_RESEARCH_ACCEPTABLE_BLOCKERS:
        return True
    if code.startswith("OHLCV_") and code.endswith("_PARTIAL_DAY_ACCEPTED"):
        return True
    if code.startswith("BRONZE_GAP_") and code.endswith("_PROMOTION_TOLERANCE"):
        return True
    return False


def _resolve_a2_phase_status_from_manifest(output_root: Path) -> str:
    payload = _read_json_payload(output_root / "data_factory_manifest.json")
    if not payload:
        return ""
    status = str(payload.get("data_factory_status") or "").strip()
    blockers = tuple(
        str(item).strip()
        for item in (payload.get("blocker_codes") or ())
        if str(item).strip()
    )
    if status.startswith("DATA_FACTORY_BLOCKED_BY") or status == "DATA_FACTORY_BLOCKED":
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
    if blockers and any(not is_a2_research_acceptable_blocker(code) for code in blockers):
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
    if status in {"DATA_FACTORY_READY", "DATA_FACTORY_PARTIAL"}:
        return PHASE_STATUS_DATA_FACTORY_READY
    return ""


def _harvest_pair_universe_blockers(report_path: Path) -> tuple[str, ...]:
    payload = _read_json_payload(report_path)
    if not payload:
        return ()
    out: list[str] = []
    available = payload.get("available_pairs")
    if isinstance(available, list) and len(available) == 0:
        out.append("PAIR_UNIVERSE_EMPTY")
    missing = payload.get("missing_pairs")
    if isinstance(missing, list) and missing:
        out.append("PAIR_UNIVERSE_MISSING_REQUESTED")
    return tuple(out)


def harvest_manifest_blockers(
    output_root: Path,
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Read manifest files under ``output_root`` and return blockers + stage statuses."""

    if not output_root.is_dir():
        return (), {}
    blockers: list[str] = []
    stage_statuses: dict[str, str] = {}
    for filename, blocker_keys in _MANIFEST_BLOCKER_SOURCES:
        payload = _read_json_payload(output_root / filename)
        if not payload:
            continue
        for key in blocker_keys:
            raw_blockers = payload.get(key)
            if isinstance(raw_blockers, list):
                for item in raw_blockers:
                    code = str(item).strip()
                    if code and code not in blockers:
                        blockers.append(code)
        stages = payload.get("stage_statuses")
        if isinstance(stages, dict):
            for key, value in stages.items():
                stage_statuses[str(key)] = str(value)
        for status_key in (
            "data_factory_status",
            "raw_source_status",
            "pair_universe_status",
            "silver_index_status",
            "gold_feature_store_status",
            "first_run_status",
            "feature_store_status",
            "candidate_export_status",
            "raw_window_status",
            "raw_window_extraction_status",
            "detailed_replay_status",
            "capital_profile_status",
            "capital_profile_generation_status",
            "promotion_artifact_status",
            "sample_size_survival_status",
            "ml_mode_status",
            "orderbook_schema_status",
            "trade_schema_status",
            "kline_schema_status",
            "compression_status",
            "status",
        ):
            value = payload.get(status_key)
            if isinstance(value, str) and value and status_key not in stage_statuses:
                stage_statuses[status_key] = value
    blockers.extend(_harvest_pair_universe_blockers(output_root / "pair_universe_report.json"))
    deduped: list[str] = []
    for code in blockers:
        if code and code not in deduped:
            deduped.append(code)
    return tuple(deduped), stage_statuses


def _collect_output_refs(output_root: Path) -> tuple[str, ...]:
    if not output_root.is_dir():
        return ()
    refs: list[str] = []
    seen: set[str] = set()
    preferred_paths = (
        output_root / "job_status.json",
        output_root / "backtest_proof_matrix.json",
        output_root / "data_factory_manifest.json",
        output_root / "a2_microstructure_performance_report.json",
        output_root / "a2_microstructure_cache_manifest.json",
        output_root / "a2_feature_equivalence_report.json",
        output_root / "first_run_manifest.json",
        output_root / "first_run_stage_summary.json",
        output_root / "raw_window_failure_report.json",
        output_root / "pair_universe_report.json",
        output_root / "strategy_ladder_ml_lab_handoff_report.json",
        output_root / "strategy_ladder_backtest_ml_input.json",
        output_root / "strategy_ladder_expected_edge_ml_model_artifact.json",
        output_root / "strategy_ladder_expected_edge_ml_model_artifact.summary.json",
        output_root / "rolling_ml_window_plan.json",
        output_root / "rolling_ml_window_plan.md",
    )
    for path in preferred_paths:
        if path.is_file():
            resolved = str(path.resolve())
            if resolved not in seen:
                refs.append(resolved)
                seen.add(resolved)
            if len(refs) >= 12:
                return tuple(refs)
    for path in output_root.rglob("*.json"):
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        refs.append(resolved)
        seen.add(resolved)
        if len(refs) >= 12:
            break
    if len(refs) < 12:
        for path in output_root.rglob("*.yml"):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            refs.append(resolved)
            seen.add(resolved)
            if len(refs) >= 12:
                break
    return tuple(refs)


def _count_existing_output_files(output_root: Path, *, limit: int = 10_000) -> int:
    if not output_root.is_dir():
        return 0
    count = 0
    try:
        for path in output_root.rglob("*"):
            if path.is_file():
                count += 1
                if count >= limit:
                    return count
    except OSError:
        return count
    return count


def _write_backtest_job_record(
    record_path: Path,
    record: CockpitBacktestJobRecord,
) -> None:
    atomic_write_json(record_path, record.model_dump(mode="json"), indent=2)


def _write_patch6_job_request(
    path: Path,
    *,
    record: CockpitBacktestJobRecord,
    raw_source_manifest_path: Path | None,
    historical_metadata_root: Path | None,
    raw_roots: tuple[Path, ...],
    pairs: tuple[str, ...],
    start: str,
    end: str,
    engine_native_mode: bool,
    engine_native_sample_size: int,
    frozen_ml_artifact_path: Path | None,
    frozen_ml_artifact_hash: str,
    rolling_ml_window_plan_path: Path | None,
    ml_artifact_freshness_days: int,
    b1_5_policy_mode: str,
    preselected_only: bool,
    diagnostic_full_replay: bool,
    feature_store_root: Path | None = None,
    silver_index_path: Path | None = None,
    candidate_events_path: Path | None = None,
    b2_run_root: Path | None = None,
    label_store_dataset_path: Path | None = None,
    calibration_version: str = "strategy_ladder_expected_edge.v1",
    timeframe: str = "1m",
    backtest_timeframes: tuple[str, ...] = (),
    requested_backtest_start: str = "",
    requested_backtest_days: int = 130,
    train_days: int = 180,
    validation_days: int = 30,
    freshness_days: int = 30,
    chunk_days: int = 30,
    feature_names_csv: str = "close_return,high_low_range,volume",
    sample_stride_minutes: int = 60,
    target_horizon_minutes: int = 1,
    training_seed: int = 5307,
    max_optuna_trials: int = 0,
    min_training_rows: int = 210,
    shap_summary_ref: str = "",
) -> None:
    requested_feature_names = _csv_feature_names(feature_names_csv)
    requested_non_legacy_feature_names = tuple(
        name
        for name in requested_feature_names
        if name not in _LEGACY_EXPECTED_EDGE_FEATURE_NAME_SET
    )
    atomic_write_json(
        path,
        {
            "job_id": record.job_id,
            "job_kind": record.job_kind.value,
            "action_name": record.action_name,
            "phase_id": record.phase_id,
            "workflow_run_id": record.workflow_run_id,
            "phase_run_id": record.phase_run_id,
            "parent_workflow_ref": record.parent_workflow_ref,
            "workflow_run_id": record.workflow_run_id,
            "phase_run_id": record.phase_run_id,
            "parent_workflow_ref": record.parent_workflow_ref,
            "preview_id": record.preview_id,
            "request_hash": record.request_hash,
            "requested_at": record.requested_at_iso,
            "status": record.status.value,
            "command_preview": record.command_preview,
            "output_root": record.output_root,
            "stage_statuses": record.stage_statuses,
            "blockers": list(record.blockers),
            "artifact_inventory_path": record.artifact_inventory_path,
            "log_path": record.stdout_log_path,
            "raw_source_manifest_path": (
                str(raw_source_manifest_path.resolve())
                if raw_source_manifest_path is not None
                else ""
            ),
            "historical_metadata_root": (
                str(historical_metadata_root.resolve())
                if historical_metadata_root is not None
                else ""
            ),
            "raw_roots": [str(path.resolve()) for path in raw_roots],
            "pairs": list(pairs),
            "start": start,
            "end": end,
            "b2_run_root": (
                str(b2_run_root.resolve()) if b2_run_root is not None else ""
            ),
            "label_store_dataset_path": (
                str(label_store_dataset_path.resolve())
                if label_store_dataset_path is not None
                else ""
            ),
            "calibration_version": calibration_version,
            "timeframe": timeframe,
            "backtest_timeframes": list(backtest_timeframes or ()),
            "requested_backtest_start": requested_backtest_start,
            "requested_backtest_days": max(int(requested_backtest_days), 1),
            "train_days": max(int(train_days), 1),
            "validation_days": max(int(validation_days), 1),
            "freshness_days": max(int(freshness_days), 1),
            "chunk_days": max(int(chunk_days), 1),
            "feature_names_csv": feature_names_csv,
            "requested_feature_names": list(requested_feature_names),
            "requested_feature_count": len(requested_feature_names),
            "requested_non_legacy_feature_names": list(
                requested_non_legacy_feature_names
            ),
            "requested_non_legacy_feature_count": len(
                requested_non_legacy_feature_names
            ),
            "requires_replay_grounding": bool(requested_non_legacy_feature_names),
            "b2_run_root_present": b2_run_root is not None,
            "label_store_dataset_path_present": label_store_dataset_path is not None,
            "replay_grounding_source_present": (
                b2_run_root is not None or label_store_dataset_path is not None
            ),
            "replay_grounding_source_status": (
                "B2_AND_LABEL_STORE"
                if b2_run_root is not None and label_store_dataset_path is not None
                else (
                    "LABEL_STORE_DATASET"
                    if label_store_dataset_path is not None
                    else ("B2_RUN_ROOT" if b2_run_root is not None else "NONE")
                )
            ),
            "sample_stride_minutes": max(int(sample_stride_minutes), 1),
            "target_horizon_minutes": max(int(target_horizon_minutes), 1),
            "training_seed": int(training_seed),
            "max_optuna_trials": max(int(max_optuna_trials), 0),
            "min_training_rows": max(int(min_training_rows), 10),
            "shap_summary_ref": shap_summary_ref,
            "engine_native_mode": engine_native_mode,
            "engine_native_sample_size": engine_native_sample_size,
            "frozen_ml_artifact_path": (
                str(frozen_ml_artifact_path.resolve())
                if frozen_ml_artifact_path is not None
                else ""
            ),
            "frozen_ml_artifact_hash": frozen_ml_artifact_hash,
            "rolling_ml_window_plan_path": (
                str(rolling_ml_window_plan_path.resolve())
                if rolling_ml_window_plan_path is not None
                else ""
            ),
            "ml_artifact_freshness_days": max(int(ml_artifact_freshness_days), 1),
            "b1_5_policy_mode": b1_5_policy_mode,
            "preselected_only": preselected_only,
            "diagnostic_full_replay": diagnostic_full_replay,
            "candidate_discovery_mode": record.candidate_discovery_mode,
            "bml_candidate_sampler_mode": record.bml_candidate_sampler_mode,
            "small_scope_enabled": record.small_scope_enabled,
            "full_scan_enabled": record.full_scan_enabled,
            "no_full_scan_enabled": record.no_full_scan_enabled,
            "silver_storage_mode": record.silver_storage_mode,
            "feature_store_root": (
                str(feature_store_root.resolve())
                if feature_store_root is not None
                else ""
            ),
            "silver_index_path": (
                str(silver_index_path.resolve())
                if silver_index_path is not None
                else ""
            ),
            "candidate_events_path": (
                str(candidate_events_path.resolve())
                if candidate_events_path is not None
                else ""
            ),
            "ml_mode_status": record.ml_mode_status,
            "frozen_ml_artifact_path": record.frozen_ml_artifact_path,
            "frozen_ml_artifact_hash": record.frozen_ml_artifact_hash,
            "rolling_ml_window_plan_path": record.rolling_ml_window_plan_path,
            "ml_artifact_freshness_days": record.ml_artifact_freshness_days,
            "allow_broad_run": record.allow_broad_run,
            "candidate_discovery_mode": record.candidate_discovery_mode,
            "bml_candidate_sampler_mode": record.bml_candidate_sampler_mode,
            "engine_native_sample_size": record.engine_native_sample_size,
            "b1_5_policy_mode": record.b1_5_policy_mode,
            "preselected_only": record.preselected_only,
            "diagnostic_full_replay": record.diagnostic_full_replay,
            "small_scope_enabled": record.small_scope_enabled,
            "full_scan_enabled": record.full_scan_enabled,
            "no_full_scan_enabled": record.no_full_scan_enabled,
            "silver_storage_mode": record.silver_storage_mode,
            "consumed_artifact_refs": dict(record.consumed_artifact_refs),
            "produced_artifact_refs": dict(record.produced_artifact_refs),
            "artifact_hashes": dict(record.artifact_hashes),
            "consumed_artifact_refs": dict(record.consumed_artifact_refs),
        },
        indent=2,
    )


def _write_patch6_job_status(path: Path, record: CockpitBacktestJobRecord) -> None:
    atomic_write_json(
        path,
        {
            "job_id": record.job_id,
            "job_kind": record.job_kind.value,
            "phase_id": record.phase_id,
            "workflow_run_id": record.workflow_run_id,
            "phase_run_id": record.phase_run_id,
            "parent_workflow_ref": record.parent_workflow_ref,
            "preview_id": record.preview_id,
            "request_hash": record.request_hash,
            "requested_at": record.requested_at_iso,
            "started_at": record.started_at_iso,
            "finished_at": record.finished_at_iso,
            "status": record.status.value,
            "command_preview": record.command_preview,
            "output_root": record.output_root,
            "stage_statuses": record.stage_statuses,
            "blockers": list(record.blockers),
            "artifact_inventory_path": record.artifact_inventory_path,
            "log_path": record.stdout_log_path,
            "stage_summary_path": record.stage_summary_path,
            "ml_mode_status": record.ml_mode_status,
            "frozen_ml_artifact_path": record.frozen_ml_artifact_path,
            "frozen_ml_artifact_hash": record.frozen_ml_artifact_hash,
            "rolling_ml_window_plan_path": record.rolling_ml_window_plan_path,
            "ml_artifact_freshness_days": record.ml_artifact_freshness_days,
            "allow_broad_run": record.allow_broad_run,
            "candidate_discovery_mode": record.candidate_discovery_mode,
            "bml_candidate_sampler_mode": record.bml_candidate_sampler_mode,
            "engine_native_sample_size": record.engine_native_sample_size,
            "b1_5_policy_mode": record.b1_5_policy_mode,
            "preselected_only": record.preselected_only,
            "diagnostic_full_replay": record.diagnostic_full_replay,
            "small_scope_enabled": record.small_scope_enabled,
            "full_scan_enabled": record.full_scan_enabled,
            "no_full_scan_enabled": record.no_full_scan_enabled,
            "silver_storage_mode": record.silver_storage_mode,
            "consumed_artifact_refs": dict(record.consumed_artifact_refs),
            "produced_artifact_refs": dict(record.produced_artifact_refs),
            "artifact_hashes": dict(record.artifact_hashes),
            "error_code": _phase_error_code_from_record(record),
            "stderr_ref": record.stdout_log_path,
            # Patch 6 batch 2 — cancel telemetry.
            "pid": record.pid,
            "cancel_requested_at": record.cancel_requested_at,
            "cancelled_at": record.cancelled_at,
            "cancel_reason": record.cancel_reason,
            "termination_method": record.termination_method,
        },
        indent=2,
    )


def _safe_filename(filename: str) -> str:
    candidate = Path(filename or "artifact.bundle").name.strip() or "artifact.bundle"
    return "".join(char for char in candidate if char.isalnum() or char in "._-")


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_iso(raw_value: str) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _sha256_path(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _phase_status_from_finished_record(record: CockpitBacktestJobRecord) -> str:
    if record.phase_id == PHASE_A2:
        if "SILVER_STORAGE_BLOAT_BLOCKER" in record.blockers:
            return PHASE_STATUS_STORAGE_BLOCKED
        output_root = Path(record.output_root) if record.output_root else Path()
        manifest_phase_status = _resolve_a2_phase_status_from_manifest(output_root)
        if manifest_phase_status:
            return manifest_phase_status
        if record.blockers and any(
            not is_a2_research_acceptable_blocker(code) for code in record.blockers
        ):
            return PHASE_STATUS_DATA_FACTORY_BLOCKED
        if record.status.value in {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}:
            return PHASE_STATUS_DATA_FACTORY_READY
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
    if record.phase_id == PHASE_B1:
        if record.status.value in {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}:
            return PHASE_STATUS_DISCOVERY_READY
        return PHASE_STATUS_DISCOVERY_BLOCKED
    if record.phase_id == PHASE_B_ML:
        if record.status.value in {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}:
            return PHASE_STATUS_BML_READY
        return PHASE_STATUS_BML_BLOCKED
    if record.phase_id == PHASE_B2:
        if "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY" in record.blockers:
            return PHASE_STATUS_PROMOTION_BLOCKED
        if "BACKTEST_PROOF_BLOCKED" in record.blockers:
            return PHASE_STATUS_PROOF_BLOCKED
        if record.status.value in {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}:
            return PHASE_STATUS_REPLAY_READY
        return PHASE_STATUS_PROOF_BLOCKED
    return record.status.value


def _phase_error_code_from_record(record: CockpitBacktestJobRecord) -> str:
    if record.status.value in {
        "JOB_COMPLETED",
        "JOB_COMPLETED_WITH_BLOCKERS",
    }:
        return ""
    if record.error_summary.startswith("exit_code="):
        return record.error_summary.replace("=", "_").upper()
    if record.error_summary:
        return record.error_summary
    if record.blockers:
        return record.blockers[0]
    return record.status.value


def _strategy_ladder_terminal_artifact_paths(
    record: CockpitBacktestJobRecord,
) -> tuple[Path, ...]:
    if record.job_kind != CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER:
        return ()
    if not record.stage_summary_path or not record.stdout_log_path:
        return ()
    stage_summary_path = Path(record.stage_summary_path)
    stdout_log_path = Path(record.stdout_log_path)
    terminal_sentinel_path = _terminal_sentinel_path_for(record)
    if (
        not stage_summary_path.is_file()
        or not stdout_log_path.is_file()
        or not terminal_sentinel_path.is_file()
    ):
        return ()
    reports_dir = stage_summary_path.parent
    profitability_truth_path = reports_dir / "profitability_truth_verdict.json"
    decision_verdict_path = reports_dir / "backtest_decision_report_final_verdict.json"
    if not profitability_truth_path.is_file() or not decision_verdict_path.is_file():
        return ()
    if not _stdout_has_strategy_ladder_terminal_payload(stdout_log_path):
        return ()
    return (
        stage_summary_path,
        profitability_truth_path,
        decision_verdict_path,
        stdout_log_path,
        terminal_sentinel_path,
    )


def _data_factory_terminal_artifact_paths(
    record: CockpitBacktestJobRecord,
) -> tuple[Path, ...]:
    if record.job_kind != CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY:
        return ()
    if not record.stage_summary_path or not record.stdout_log_path:
        return ()
    data_factory_manifest_path = Path(record.stage_summary_path)
    stdout_log_path = Path(record.stdout_log_path)
    terminal_sentinel_path = _terminal_sentinel_path_for(record)
    if (
        not data_factory_manifest_path.is_file()
        or not stdout_log_path.is_file()
        or not terminal_sentinel_path.is_file()
    ):
        return ()
    report_root = data_factory_manifest_path.parent
    silver_index_path = report_root / "silver_index.json"
    gold_feature_manifest_path = report_root / "gold_feature_manifest.json"
    data_quality_path = report_root / "data_quality_report.json"
    progress_path = report_root / "a2_gold_progress_report.json"
    if not all(
        path.is_file()
        for path in (
            silver_index_path,
            gold_feature_manifest_path,
            data_quality_path,
            progress_path,
        )
    ):
        return ()
    progress_payload = _read_json_payload(progress_path)
    if str(progress_payload.get("status") or "") != "A2_COMPLETE":
        return ()
    if not _stdout_has_data_factory_terminal_payload(stdout_log_path):
        return ()
    return (
        data_factory_manifest_path,
        silver_index_path,
        gold_feature_manifest_path,
        data_quality_path,
        progress_path,
        stdout_log_path,
        terminal_sentinel_path,
    )


def _terminal_artifact_paths(record: CockpitBacktestJobRecord) -> tuple[Path, ...]:
    return (
        _strategy_ladder_terminal_artifact_paths(record)
        or _data_factory_terminal_artifact_paths(record)
    )


def _stdout_has_strategy_ladder_terminal_payload(stdout_log_path: Path) -> bool:
    if not stdout_log_path.is_file():
        return False
    try:
        text = stdout_log_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(
        marker in text
        for marker in (
            '"run_manifest_path"',
            '"summary_path"',
            '"final_status"',
            '"candidate_count"',
        )
    )


def _stdout_has_data_factory_terminal_payload(stdout_log_path: Path) -> bool:
    if not stdout_log_path.is_file():
        return False
    try:
        text = stdout_log_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(
        marker in text
        for marker in (
            '"data_factory_status"',
            '"silver_index_status"',
            '"gold_feature_store_status"',
            '"rows_processed"',
        )
    )


def _should_recover_strategy_ladder_postrun_stall(
    record: CockpitBacktestJobRecord,
) -> bool:
    terminal_paths = _terminal_artifact_paths(record)
    if not terminal_paths:
        return False
    latest_mtime = max(path.stat().st_mtime for path in terminal_paths)
    return (time.time() - latest_mtime) >= _STRATEGY_LADDER_POSTRUN_STALL_SECONDS


def _finished_at_from_artifacts(record: CockpitBacktestJobRecord) -> str:
    candidates: list[Path] = []
    for raw_path in (
        record.stdout_log_path,
        record.stage_summary_path,
        record.artifact_inventory_path,
        record.job_status_path,
    ):
        path = Path(raw_path) if raw_path else None
        if path is not None and path.is_file():
            candidates.append(path)
    candidates.extend(_terminal_artifact_paths(record))
    output_root = Path(record.output_root) if record.output_root else None
    if output_root is not None and output_root.is_dir():
        for filename in (
            "backtest_proof_matrix.json",
            "first_run_manifest.json",
            "first_run_stage_summary.json",
            "data_factory_manifest.json",
        ):
            path = output_root / filename
            if path.is_file():
                candidates.append(path)
    if not candidates:
        return _utc_now_iso()
    latest_mtime = max(path.stat().st_mtime for path in candidates)
    return datetime.fromtimestamp(latest_mtime, tz=UTC).isoformat()


def _terminal_status_from_record_artifacts(
    *,
    record: CockpitBacktestJobRecord,
    blockers: tuple[str, ...],
    stage_statuses: dict[str, str],
) -> CockpitBacktestJobStatus:
    if _terminal_artifact_paths(record):
        return (
            CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS
            if blockers
            else CockpitBacktestJobStatus.JOB_COMPLETED
        )
    output_root = Path(record.output_root) if record.output_root else Path()
    return _terminal_status_from_artifacts(
        output_root=output_root,
        blockers=blockers,
        stage_statuses=stage_statuses,
    )


def _terminal_status_from_artifacts(
    *,
    output_root: Path,
    blockers: tuple[str, ...],
    stage_statuses: dict[str, str],
) -> CockpitBacktestJobStatus:
    if blockers:
        return CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS
    if stage_statuses:
        if any(
            "BLOCKED" in value
            or value.endswith("_NOT_PROVEN")
            or value.endswith("_PARTIAL")
            or value == "DATA_FACTORY_PARTIAL"
            for value in stage_statuses.values()
        ):
            return CockpitBacktestJobStatus.JOB_COMPLETED_WITH_BLOCKERS
        return CockpitBacktestJobStatus.JOB_COMPLETED
    if output_root.is_dir():
        for filename in (
            "backtest_proof_matrix.json",
            "first_run_manifest.json",
            "data_factory_manifest.json",
            "silver_index.json",
        ):
            if (output_root / filename).is_file():
                return CockpitBacktestJobStatus.JOB_COMPLETED
    return CockpitBacktestJobStatus.JOB_FAILED


def _reconcile_stale_job_record(
    record_path: Path,
    record: CockpitBacktestJobRecord,
) -> CockpitBacktestJobRecord:
    if record.status not in _RUNNING_JOB_STATUSES:
        return record
    if record.pid and _pid_is_alive(record.pid):
        return record
    output_root = Path(record.output_root) if record.output_root else Path()
    harvested_blockers, harvested_stage_statuses = harvest_manifest_blockers(output_root)
    merged_blockers = tuple(dict.fromkeys((*record.blockers, *harvested_blockers)))
    merged_stage_statuses = {**record.stage_statuses, **harvested_stage_statuses}
    final_status = _terminal_status_from_record_artifacts(
        record=record,
        blockers=merged_blockers,
        stage_statuses=merged_stage_statuses,
    )
    stale_marker = (
        JOB_RECORD_STALE_PID_DEAD
        if final_status != CockpitBacktestJobStatus.JOB_FAILED
        else JOB_PROCESS_EXITED_WITHOUT_MANIFESTS
    )
    final_blockers = merged_blockers
    if stale_marker == JOB_PROCESS_EXITED_WITHOUT_MANIFESTS:
        final_blockers = tuple(dict.fromkeys((*merged_blockers, stale_marker)))
    output_refs = record.output_refs
    if not output_refs and record.artifact_inventory_path:
        inventory_payload = _read_json_payload(Path(record.artifact_inventory_path))
        inventory_refs = inventory_payload.get("artifact_refs") if inventory_payload else None
        if isinstance(inventory_refs, dict):
            output_refs = tuple(
                str(value)
                for value in inventory_refs.values()
                if isinstance(value, str) and value.strip()
            )
    if not output_refs and output_root.is_dir():
        output_refs = _collect_output_refs(output_root)
    reconciled = record.model_copy(
        update={
            "status": final_status,
            "finished_at_iso": _finished_at_from_artifacts(record),
            "blockers": final_blockers,
            "stage_statuses": merged_stage_statuses,
            "output_refs": output_refs,
            "error_summary": stale_marker,
        }
    )
    try:
        _write_backtest_job_record(record_path, reconciled)
    except OSError as exc:
        _logger.warning(
            "Failed to persist reconciled cockpit backtest job record during dashboard read: %s (%s)",
            record_path,
            exc,
        )
    if reconciled.job_status_path:
        try:
            _write_patch6_job_status(Path(reconciled.job_status_path), reconciled)
        except OSError as exc:
            _logger.warning(
                "Failed to persist reconciled cockpit patch6 job status during dashboard read: %s (%s)",
                reconciled.job_status_path,
                exc,
            )
    return reconciled


__all__ = [
    "CockpitBacktestJobKind",
    "CockpitBacktestJobRecord",
    "CockpitBacktestJobStatus",
    "CockpitQueuedCommandSummary",
    "CANCEL_REQUEST_FILENAME",
    "JOB_ID_NOT_FOUND",
    "OUTPUT_ROOT_DEFAULTED",
    "OUTPUT_ROOT_EXISTS_NON_EMPTY",
    "OUTPUT_ROOT_INSIDE_RAW_ROOT",
    "OUTPUT_ROOT_INVALID_PATH",
    "OUTPUT_ROOT_NOT_WRITABLE",
    "OUTPUT_ROOT_READY",
    "PAIR_ARG_INVALID_PATH",
    "PAIR_UNIVERSE_AMBIGUOUS",
    "PID_NOT_FOUND",
    "RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE",
    "StrategyLadderControlAction",
    "enqueue_artifact_command",
    "estimate_job_progress",
    "harvest_manifest_blockers",
    "infer_pair_symbol_from_path",
    "infer_pair_universe_from_paths",
    "is_path_like_pair_token",
    "is_a2_research_acceptable_blocker",
    "is_valid_raw_source_manifest_path",
    "launch_backtest_job",
    "request_job_cancel",
    "resolve_output_root",
    "load_backtest_job_records",
    "stage_artifact_upload",
]
