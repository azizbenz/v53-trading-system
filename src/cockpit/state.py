"""Read-only adapters and composite view-models for the V5.3 cockpit."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import V53_MULTIPAIR_7
from interface_contracts.pair_catalog import V53_PAIR_CATALOG
from cockpit.backtest_preflight import (
    BacktestPreflightPreview,
    load_patch6_preflight_preview,
)
from cockpit.backtest_state_support import (
    action_name_for_phase,
    BacktestMlChainState,
    BacktestPreviewManifest,
    canonicalize_workflow_identity,
    CockpitPatch6State,
    CockpitStateConsistency,
    Patch6NormalizedRequest,
    build_patch6_normalized_request,
    build_patch6_state,
    build_state_consistency,
    phase_id_for_action,
    phase_label_for_action,
    read_current_form_state,
    read_backtest_ml_chain_state,
    read_launch_request_state,
    read_preview_manifest,
    read_source_preview_state,
    request_hash_for_normalized_request,
)
from cockpit.form_state_support import (
    BacktestFormState,
    LabMlHandoffFormState,
    read_backtest_form_state,
    read_lab_ml_handoff_form_state,
)
from cockpit.runtime_support import CockpitAlert, CockpitRuntimeSurfaces, read_runtime_surfaces
from cockpit.state_calibration import (
    CalibrationThresholdsSnapshot,
    read_calibration_thresholds,
)
from cockpit.state_build1_core_health import (
    Build1CoreHealthSnapshot,
    read_build1_core_health,
)
from cockpit.state_capacity_guard import CapacityGuardSnapshot, read_capacity_guard
from cockpit.state_data_quality import DataQualitySnapshot, read_data_quality_live
from cockpit.state_decision_trace import DecisionTraceSnapshot, read_decision_trace
from cockpit.state_disk_growth import DiskGrowthSnapshot, read_disk_growth
from cockpit.state_economic_sterilization import (
    EconomicSterilizationSnapshot,
    read_economic_sterilization,
)
from cockpit.state_engines import EnginesGridSnapshot, build_engines_grid
from cockpit.state_engine_why import EngineWhySnapshot, read_engine_why_state
from cockpit.state_feature_bridge import FeatureBridgeSnapshot, read_feature_bridge
from cockpit.state_freshness import SourceFreshnessSnapshot, read_source_freshness
from cockpit.state_kill_proof import KillProofSnapshot, read_kill_proof
from cockpit.state_lab_review import LabReviewSummary, read_lab_review
from cockpit.state_lab_vps_transfer import LabVpsTransferSnapshot, read_lab_vps_transfer
from cockpit.state_model_risk import (
    ModelRiskRegisterSnapshot,
    read_model_risk_register,
)
from cockpit.state_multiple_testing import (
    MultipleTestingGuardSnapshot,
    read_multiple_testing_guard,
)
from cockpit.state_refusal_journal import (
    RefusalJournalSnapshot,
    read_refusal_journal,
)
from cockpit.state_replay_metrics import ReplayMetricsSnapshot, read_replay_metrics
from cockpit.state_run_comparison import RunComparisonSnapshot, read_run_comparison
from cockpit.state_queue_trace import QueueConsumptionTraceSnapshot, read_queue_trace
from cockpit.state_service_liveness import ServiceLivenessSnapshot, read_service_liveness
from cockpit.state_sizing_chain import SizingChainSnapshot, read_sizing_chain
from cockpit.state_system_flow import SystemFlowSnapshot, read_system_flow
from cockpit.state_tail_risk import TailRiskSnapshot, read_tail_risk
from cockpit.state_warmup_explainer import (
    WarmupExplainerSnapshot,
    read_warmup_explainer,
)
from monitoring.contracts import ShadowVpsServiceLogQuery


_logger = logging.getLogger(__name__)


class CockpitPaths(BaseModel, frozen=True):
    """Resolved filesystem paths the cockpit reads from."""

    service_dir: Path
    pid_file: Path
    log_file: Path
    auto_exports_root: Path
    live_websocket_config: Path
    calibration_thresholds: Path | None = None
    build_root: Path | None = None
    dashboard_command_queue_root: Path | None = None
    observability_output_dir: Path | None = None
    backtest_jobs_root: Path | None = None
    artifact_ingress_root: Path | None = None

    @property
    def warmup_summary(self) -> Path:
        return self.service_dir / "vps_warmup_run.summary.json"

    @property
    def snapshot_batch(self) -> Path:
        return self.service_dir.parent / "live_captures"

    @property
    def observability_export(self) -> Path:
        return self.service_dir / "shadow_vps_service_observability_export.json"

    @property
    def service_state(self) -> Path:
        return self.service_dir / "shadow_vps_service.state.json"


class ServiceStatus(BaseModel, frozen=True):
    """High-level liveness signal for the Shadow service."""

    running: bool
    pid: int | None = None
    pid_file_path: str
    runtime_mode: str = "unknown"


class WarmupCheck(BaseModel, frozen=True):
    """One row of the warmup readiness report."""

    check_id: str
    status: str
    reasons: tuple[str, ...] = ()


class WarmupSummary(BaseModel, frozen=True):
    """Subset of ``vps_warmup_run.summary.json`` rendered on the dashboard."""

    runtime_mode: str
    final_state: str
    eligible_to_trade: bool
    blocking_reasons: tuple[str, ...] = ()
    checks: tuple[WarmupCheck, ...] = ()


class PairMetric(BaseModel, frozen=True):
    """Latest price and 24h change for one trading pair."""

    pair: str
    price: float | None = None
    change_24h_pct: float | None = None
    last_update_ts: float | None = None
    source: str = ""


class PairSelector(BaseModel, frozen=True):
    """Enumerated pairs configured for the active Shadow campaign."""

    configured_pairs: tuple[str, ...]
    default_pair: str = "BTCUSDT"
    active_pairs: tuple[str, ...] = ()
    suspended_pairs: tuple[str, ...] = ()
    source_status: str = "ok"


class ArtefactExportEntry(BaseModel, frozen=True):
    """One artifact file inside an export day directory."""

    name: str
    relative_path: str
    size_bytes: int
    mtime_iso: str


class ArtefactExportDay(BaseModel, frozen=True):
    """All artifacts captured on a given trading day."""

    date: str = Field(..., min_length=10, max_length=10)
    files: tuple[ArtefactExportEntry, ...]


def read_pid(pid_file: Path) -> int | None:
    """Return the live PID from the tracker file, or ``None`` if absent/invalid."""

    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        _logger.warning("PID file unreadable %s: %s", pid_file, exc)
        return None
    try:
        return int(raw)
    except ValueError:
        _logger.warning("PID file %s contains non-integer payload %r", pid_file, raw)
        return None


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_service_status(paths: CockpitPaths) -> ServiceStatus:
    """Return the current Shadow service status as observed via PID file."""

    pid = read_pid(paths.pid_file)
    running = pid is not None and _pid_is_alive(pid)
    runtime_mode = "unknown"
    summary = read_warmup_summary(paths)
    if summary is not None:
        runtime_mode = summary.runtime_mode
    return ServiceStatus(
        running=running,
        pid=pid if running else None,
        pid_file_path=str(paths.pid_file),
        runtime_mode=runtime_mode,
    )


def read_warmup_summary(paths: CockpitPaths) -> WarmupSummary | None:
    """Parse ``vps_warmup_run.summary.json`` into a typed view-model."""

    path = paths.warmup_summary
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse warmup summary %s: %s", path, exc)
        return None

    report = payload.get("report") or {}
    raw_checks = report.get("checks") or []
    checks: list[WarmupCheck] = []
    for item in raw_checks:
        if not isinstance(item, dict):
            continue
        checks.append(
            WarmupCheck(
                check_id=str(item.get("check_id", "")),
                status=str(item.get("status", "")),
                reasons=tuple(str(reason) for reason in item.get("reasons") or ()),
            )
        )
    return WarmupSummary(
        runtime_mode=str(payload.get("runtime_mode", "unknown")),
        final_state=str(payload.get("final_state", "unknown")),
        eligible_to_trade=bool(payload.get("eligible_to_trade", False)),
        blocking_reasons=tuple(
            str(reason) for reason in payload.get("blocking_reasons") or ()
        ),
        checks=tuple(checks),
    )


def _read_json_with_bom(path: Path) -> object | None:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    except OSError as exc:
        _logger.warning("Cannot read %s: %s", path, exc)
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        _logger.warning("Cannot parse JSON %s: %s", path, exc)
        return None


def read_pair_selector(paths: CockpitPaths) -> PairSelector:
    """Read the configured pairs from ``live_websocket_config.json``."""

    canonical_pairs = _canonical_pair_fallback()
    payload = _read_json_with_bom(paths.live_websocket_config)
    if not isinstance(payload, dict):
        return PairSelector(
            configured_pairs=canonical_pairs,
            default_pair=canonical_pairs[0],
            active_pairs=canonical_pairs,
            source_status="missing",
        )
    raw = payload.get("pairs")
    if not isinstance(raw, list) or not raw:
        return PairSelector(
            configured_pairs=canonical_pairs,
            default_pair=canonical_pairs[0],
            active_pairs=canonical_pairs,
            source_status="missing",
        )
    pairs = tuple(str(pair).upper() for pair in raw if isinstance(pair, str))
    if not pairs:
        return PairSelector(
            configured_pairs=canonical_pairs,
            default_pair=canonical_pairs[0],
            active_pairs=canonical_pairs,
            source_status="missing",
        )
    return PairSelector(
        configured_pairs=pairs,
        default_pair=pairs[0],
        active_pairs=pairs,
        source_status="ok",
    )


def _canonical_pair_fallback() -> tuple[str, ...]:
    return tuple(
        entry.symbol
        for entry in V53_PAIR_CATALOG.entries
        if entry.symbol in V53_MULTIPAIR_7
    )


def _latest_snapshot_batch_path(paths: CockpitPaths) -> Path | None:
    captures_root = paths.snapshot_batch
    if not captures_root.is_dir():
        return None
    candidates: list[Path] = []
    try:
        for day_dir in captures_root.iterdir():
            if not day_dir.is_dir():
                continue
            candidate = day_dir / "live_websocket_snapshot_batch.json"
            if candidate.is_file():
                candidates.append(candidate)
    except OSError as exc:
        _logger.warning("Cannot scan captures root %s: %s", captures_root, exc)
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: candidate.stat().st_mtime, reverse=True)
    return candidates[0]


def read_pair_metrics(paths: CockpitPaths) -> tuple[PairMetric, ...]:
    """Build per-pair metric cards from the latest WebSocket snapshot batch."""

    selector = read_pair_selector(paths)
    snapshot_path = _latest_snapshot_batch_path(paths)
    metrics: dict[str, PairMetric] = {
        pair: PairMetric(pair=pair, source="no_capture_yet")
        for pair in selector.configured_pairs
    }
    if snapshot_path is None:
        return tuple(metrics[pair] for pair in selector.configured_pairs)

    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse snapshot batch %s: %s", snapshot_path, exc)
        return tuple(metrics[pair] for pair in selector.configured_pairs)

    if isinstance(payload, list):
        frames: list[object] = payload
    elif isinstance(payload, dict):
        candidate = payload.get("frames") or payload.get("snapshots") or []
        frames = candidate if isinstance(candidate, list) else []
    else:
        frames = []
    if not frames:
        return tuple(metrics[pair] for pair in selector.configured_pairs)

    last_seen: dict[str, tuple[float | None, float | None, float | None]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        event = frame.get("event")
        if isinstance(event, dict):
            pair = str(event.get("pair") or event.get("symbol") or "").upper()
            price_raw = event.get("price") or event.get("last_price") or event.get("c")
            change_raw = event.get("change_24h_pct") or event.get("P")
            ts_raw = event.get("timestamp_ms") or event.get("event_time_ms")
        else:
            pair = str(frame.get("pair") or frame.get("symbol") or "").upper()
            price_raw = frame.get("price") or frame.get("c")
            change_raw = frame.get("change_24h_pct") or frame.get("P")
            ts_raw = frame.get("timestamp_ms") or frame.get("recv_time_s")
        if pair not in metrics:
            continue
        try:
            price = float(price_raw) if price_raw is not None else None
        except (TypeError, ValueError):
            price = None
        try:
            change = float(change_raw) if change_raw is not None else None
        except (TypeError, ValueError):
            change = None
        try:
            timestamp = float(ts_raw) if ts_raw is not None else None
            if timestamp is not None and timestamp > 1e12:
                timestamp = timestamp / 1000.0
        except (TypeError, ValueError):
            timestamp = None
        previous = last_seen.get(pair)
        if previous is not None and timestamp is not None and previous[2] is not None:
            if timestamp < previous[2]:
                continue
        last_seen[pair] = (price, change, timestamp)

    for pair, (price, change, timestamp) in last_seen.items():
        metrics[pair] = PairMetric(
            pair=pair,
            price=price,
            change_24h_pct=change,
            last_update_ts=timestamp,
            source=str(snapshot_path),
        )
    return tuple(metrics[pair] for pair in selector.configured_pairs)


def list_artefact_exports(paths: CockpitPaths) -> tuple[ArtefactExportDay, ...]:
    """Scan ``auto_exports/<date>/`` and return one entry per trading day."""

    root = paths.auto_exports_root
    if not root.is_dir():
        return ()
    days: list[ArtefactExportDay] = []
    try:
        date_dirs = [directory for directory in root.iterdir() if directory.is_dir()]
    except OSError as exc:
        _logger.warning("Cannot scan auto exports root %s: %s", root, exc)
        return ()
    date_dirs.sort(key=lambda directory: directory.name, reverse=True)
    for date_dir in date_dirs:
        files = _scan_export_files(date_dir, root)
        if not files:
            continue
        days.append(ArtefactExportDay(date=date_dir.name, files=files))
    return tuple(days)


def _scan_export_files(date_dir: Path, root: Path) -> tuple[ArtefactExportEntry, ...]:
    entries: list[ArtefactExportEntry] = []
    try:
        children = sorted(date_dir.iterdir(), key=lambda child: child.name)
    except OSError:
        return ()
    for child in children:
        if not child.is_file():
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        entries.append(
            ArtefactExportEntry(
                name=child.name,
                relative_path=child.relative_to(root).as_posix(),
                size_bytes=int(stat.st_size),
                mtime_iso=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            )
        )
    return tuple(entries)


@dataclass(frozen=True)
class DashboardViewModel:
    """Composite view-model passed to the Jinja templates."""

    welcome_message: str
    service: ServiceStatus
    warmup: WarmupSummary | None
    pairs: PairSelector
    metrics: tuple[PairMetric, ...]
    artefacts: tuple[ArtefactExportDay, ...]
    grafana_url: str
    prometheus_url: str
    selected_pair: str
    rendered_at_iso: str
    current_page: str
    notice_message: str
    notice_status: str
    runtime: CockpitRuntimeSurfaces
    selected_form: BacktestFormState
    lab_ml_handoff_form: LabMlHandoffFormState
    backtest_preflight: BacktestPreflightPreview
    current_form_state: CockpitPatch6State | None
    source_preview_state: CockpitPatch6State | None
    launch_request_state: CockpitPatch6State | None
    latest_job_state: CockpitPatch6State | None
    latest_canonical_summary_state: CockpitPatch6State | None
    cockpit_state_consistency: CockpitStateConsistency
    engines: EnginesGridSnapshot
    replay: ReplayMetricsSnapshot
    feature_bridge: FeatureBridgeSnapshot
    sizing_chain: SizingChainSnapshot
    lab_review: LabReviewSummary
    tail_risk: TailRiskSnapshot
    multiple_testing: MultipleTestingGuardSnapshot
    capacity_guard: CapacityGuardSnapshot
    calibration: CalibrationThresholdsSnapshot
    model_risk: ModelRiskRegisterSnapshot
    refusal_journal: RefusalJournalSnapshot
    operational_proof: "OperationalProofSnapshot"
    # Patch P2 (2026-05-22) — capability discovery for the IA Lab multi-pair UI.
    # Empty tuple when no kline_root yet ; template falls back to mono input.
    # Element type is `local_replay_runtime.pair_capability_discovery.PairCapability`
    # (kept as object to avoid a top-level cockpit/state import cycle risk).
    lab_discovered_pair_capabilities: tuple[object, ...] = field(default_factory=tuple)
    # Patch P3 (2026-05-22) — same surface for the Backtest page (paths come from
    # BacktestFormState.{klines_path,trades_path,orderbook_path}).
    backtest_discovered_pair_capabilities: tuple[object, ...] = field(default_factory=tuple)
    supported_expected_edge_feature_names: tuple[str, ...] = field(default_factory=tuple)
    supported_expected_edge_feature_groups: tuple[tuple[str, tuple[str, ...]], ...] = field(
        default_factory=tuple
    )
    lab_feature_governance: tuple[object, ...] = field(default_factory=tuple)
    lab_effective_selected_features: tuple[str, ...] = field(default_factory=tuple)
    lab_selected_demoted_features: tuple[str, ...] = field(default_factory=tuple)
    lab_feature_selection_source: str = "NONE"
    lab_requested_non_legacy_features: tuple[str, ...] = field(default_factory=tuple)
    lab_replay_grounding_required: bool = False
    lab_replay_grounding_ready: bool = False
    backtest_feature_governance: tuple[object, ...] = field(default_factory=tuple)
    backtest_effective_selected_features: tuple[str, ...] = field(default_factory=tuple)
    backtest_selected_demoted_features: tuple[str, ...] = field(default_factory=tuple)
    backtest_feature_selection_source: str = "NONE"
    backtest_feature_picker_read_only: bool = False
    backtest_ml_chain_state: BacktestMlChainState | None = None


class OperationalProofSnapshot(BaseModel, frozen=True):
    """Read-only operational proof surfaces for Phase 2.5."""

    freshness: SourceFreshnessSnapshot
    run_comparison: RunComparisonSnapshot
    system_flow: SystemFlowSnapshot
    queue_trace: QueueConsumptionTraceSnapshot
    service_liveness: ServiceLivenessSnapshot
    warmup_explainer: WarmupExplainerSnapshot
    engine_why: EngineWhySnapshot
    decision_trace: DecisionTraceSnapshot
    economic_sterilization: EconomicSterilizationSnapshot
    lab_vps_transfer: LabVpsTransferSnapshot
    kill_proof: KillProofSnapshot
    data_quality: DataQualitySnapshot
    disk_growth: DiskGrowthSnapshot


def _build_operational_alerts(
    *,
    warmup: WarmupExplainerSnapshot,
    service_liveness: ServiceLivenessSnapshot,
    queue_trace: QueueConsumptionTraceSnapshot,
    engine_why: EngineWhySnapshot,
    feature_bridge: FeatureBridgeSnapshot,
    refusal_journal: RefusalJournalSnapshot,
    data_quality: DataQualitySnapshot,
    disk_growth: DiskGrowthSnapshot,
) -> tuple[CockpitAlert, ...]:
    alerts: list[CockpitAlert] = []
    if warmup.final_state != "unknown" and not warmup.eligible_to_trade:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:eligible_to_trade_false",
                severity="critical",
                category="readiness",
                message=(
                    "Warmup is not eligible to trade "
                    f"(final_state={warmup.final_state})."
                ),
            )
        )
    if warmup.final_state != "unknown" and warmup.readiness_status != "passed":
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:warmup_blocked",
                severity="critical",
                category="readiness",
                message=(
                    "Warmup is blocked for operator readiness: "
                    + ", ".join(warmup.blocking_reasons or ("check statuses unresolved",))
                ),
            )
        )
    if not service_liveness.control_ready:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:service_degraded_not_control_ready",
                severity="critical",
                category="infra",
                message=(
                    "Shadow service is not control-ready "
                    f"(status={service_liveness.service_status})."
                ),
            )
        )
    if queue_trace.consumption_status == "queue_only":
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:queue_only_not_consumed",
                severity="warning",
                category="queue",
                message="Governed queue is visible, but service consumption is not proven.",
            )
        )
    if queue_trace.queue_backlog_stalled:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:queue_backlog_stalled",
                severity="warning",
                category="queue",
                message="Queue backlog is pending without visible service progress.",
            )
        )
    dormant_targets = tuple(
        row.engine_id
        for row in engine_why.engines
        if row.engine_id in {"engine_c", "engine_d"} and row.status == "dormant"
    )
    if dormant_targets:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:engine_cd_dormant",
                severity="warning",
                category="engines",
                message=(
                    "Canonical engines remain dormant without replay records: "
                    + ", ".join(dormant_targets)
                ),
            )
        )
    if feature_bridge.lineage_lock_status not in {"locked", "valid", "present"}:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:lineage_lock_missing",
                severity="warning",
                category="audit",
                message="Feature bridge lineage lock is missing or not validated.",
            )
        )
    if refusal_journal.source_status != "ok":
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:refusal_journal_missing",
                severity="warning",
                category="audit",
                message="Refusal Journal is not yet persisted to disk.",
            )
        )
    if any(row.status == "stale" for row in data_quality.pairs):
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:data_quality_stale",
                severity="warning",
                category="data",
                message="Live data quality is stale for one or more configured pairs.",
            )
        )
    if disk_growth.disk_used_percent >= 85.0:
        severity = "critical"
    elif disk_growth.disk_used_percent >= 75.0:
        severity = "warning"
    else:
        severity = ""
    if severity:
        alerts.append(
            CockpitAlert(
                alert_id="cockpit:disk_usage_watch",
                severity=severity,
                category="infra",
                message=f"Disk usage is {disk_growth.disk_used_percent:.1f}%.",
            )
        )
    return tuple(alerts)


def _build_ephemeral_current_form_state(
    selected_form: BacktestFormState,
    preview_state: CockpitPatch6State | None,
) -> CockpitPatch6State:
    normalized_request, _ = canonicalize_workflow_identity(
        build_patch6_normalized_request(selected_form)
    )
    return build_patch6_state(
        state_name="current_form_state",
        normalized_request=normalized_request,
        request_hash=request_hash_for_normalized_request(normalized_request),
        detected_pairs=(),
        active_pairs_after_pruning=(),
        status="FORM_STATE_LOADED",
        preview_id=preview_state.preview_id if preview_state is not None else "",
        output_root_effective=(
            preview_state.output_root_effective if preview_state is not None else ""
        ),
        blockers=(),
    )


def _align_preview_context_with_current_form(
    *,
    selected_form: BacktestFormState,
    source_preview_state: CockpitPatch6State | None,
    preview_manifest: BacktestPreviewManifest | None,
) -> tuple[CockpitPatch6State | None, BacktestPreviewManifest | None]:
    if source_preview_state is None and preview_manifest is None:
        return None, None
    normalized_request, _ = canonicalize_workflow_identity(
        build_patch6_normalized_request(selected_form)
    )
    current_workflow_run_id = (
        (selected_form.workflow_run_id or "").strip()
        or normalized_request.workflow_run_id
    )
    preview_workflow_run_id = ""
    if source_preview_state is not None and source_preview_state.workflow_run_id:
        preview_workflow_run_id = source_preview_state.workflow_run_id
    elif preview_manifest is not None and preview_manifest.workflow_run_id:
        preview_workflow_run_id = preview_manifest.workflow_run_id
    if (
        current_workflow_run_id
        and preview_workflow_run_id
        and current_workflow_run_id != preview_workflow_run_id
    ):
        return None, None
    if (
        preview_manifest is not None
        and preview_manifest.workflow_run_id
        and current_workflow_run_id
        and preview_manifest.workflow_run_id != current_workflow_run_id
    ):
        return None, None
    return source_preview_state, preview_manifest


def _build_ephemeral_latest_job_state(
    runtime: CockpitRuntimeSurfaces,
    fallback_action_name: str,
) -> CockpitPatch6State | None:
    if not runtime.backtest_jobs:
        return None
    latest_job = runtime.backtest_jobs[0]
    normalized_request = Patch6NormalizedRequest(
        phase_id=phase_id_for_action(latest_job.action_name or fallback_action_name),
        phase_label=phase_label_for_action(
            latest_job.action_name or fallback_action_name
        ),
        action_name=latest_job.action_name or fallback_action_name,
        workflow_run_id=latest_job.workflow_run_id,
        dry_run=(latest_job.phase_id or "") in {"PHASE_A1", "PHASE_1A", "PHASE_2A"},
        ml_mode=latest_job.ml_mode_status,
        candidate_discovery_mode=latest_job.candidate_discovery_mode,
        engine_native_sample_size=latest_job.engine_native_sample_size,
        allow_broad_run=latest_job.allow_broad_run,
        small_scope_enabled=latest_job.small_scope_enabled,
        full_scan_enabled=latest_job.full_scan_enabled,
        no_full_scan_enabled=latest_job.no_full_scan_enabled,
        silver_storage_mode=latest_job.silver_storage_mode,
        output_root_selected=latest_job.output_root,
    )
    return build_patch6_state(
        state_name="latest_job_state",
        normalized_request=normalized_request,
        request_hash=latest_job.request_hash or "",
        detected_pairs=(),
        active_pairs_after_pruning=(),
        status=latest_job.status.value,
        preview_id=latest_job.preview_id,
        job_id=latest_job.job_id,
        output_root_effective=latest_job.output_root,
        blockers=latest_job.blockers,
    )


def _build_ephemeral_latest_canonical_summary_state(
    runtime: CockpitRuntimeSurfaces,
    fallback_action_name: str,
) -> CockpitPatch6State | None:
    summary = runtime.strategy_ladder_summary
    if summary.source_status != "ok":
        return None
    normalized_request = Patch6NormalizedRequest(
        phase_id=summary.phase_id or phase_id_for_action(fallback_action_name),
        phase_label=summary.phase_label or phase_label_for_action(fallback_action_name),
        action_name=action_name_for_phase(
            summary.phase_id,
            fallback=fallback_action_name,
        ),
        workflow_run_id=summary.workflow_run_id,
        dry_run=(summary.phase_id or "") in {"PHASE_A1", "PHASE_1A", "PHASE_2A"},
        ml_mode=summary.ml_mode_status,
        candidate_discovery_mode=summary.candidate_discovery_mode,
        engine_native_sample_size=summary.effective_engine_native_sample_size,
        allow_broad_run=False,
        small_scope_enabled=summary.small_scope_enabled,
        full_scan_enabled=summary.full_scan_enabled,
        no_full_scan_enabled=summary.no_full_scan_enabled,
        silver_storage_mode=summary.silver_storage_mode_effective,
        pair_subset=summary.active_pairs_after_pruning,
        output_root_selected=summary.output_root,
    )
    return build_patch6_state(
        state_name="latest_canonical_summary_state",
        normalized_request=normalized_request,
        request_hash=summary.request_hash or "",
        detected_pairs=summary.metadata_pairs_covered,
        active_pairs_after_pruning=summary.active_pairs_after_pruning,
        status=summary.final_status or summary.overall_backtest_proof_status,
        preview_id=summary.preview_id,
        job_id=summary.job_id,
        run_id=summary.run_id,
        output_root_effective=summary.output_root,
        blockers=summary.blocker_codes,
    )


def build_dashboard_view_model(
    paths: CockpitPaths,
    *,
    welcome_message: str,
    grafana_url: str,
    prometheus_url: str,
    selected_pair: str | None = None,
    selected_candidate_id: str = "",
    current_page: str = "overview",
    notice_message: str = "",
    notice_status: str = "info",
    log_query: ShadowVpsServiceLogQuery | None = None,
    pinned_run_id: str = "",
) -> DashboardViewModel:
    """Compose all cockpit view-models in one call."""

    service = read_service_status(paths)
    warmup = read_warmup_summary(paths)
    pairs = read_pair_selector(paths)
    metrics = read_pair_metrics(paths)
    artefacts = list_artefact_exports(paths)
    selected_form = read_backtest_form_state(paths.backtest_jobs_root)
    lab_ml_handoff_form = read_lab_ml_handoff_form_state(paths.backtest_jobs_root)
    # Patch P2/P3 (2026-05-22) — discover pairs from filesystem for both Lab + Backtest UI.
    from cockpit.strategy_ladder_ml_handoff_support import (
        discover_backtest_feature_governance,
        discover_lab_feature_governance,
        discover_backtest_pair_capabilities,
        discover_lab_pair_capabilities,
        resolve_backtest_feature_picker_defaults,
        resolve_backtest_selected_feature_names,
        resolve_lab_feature_picker_defaults,
        selected_demoted_lab_features,
        selected_demoted_backtest_features,
    )
    from local_replay_runtime.strategy_ladder_expected_edge_training import (
        ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
        BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES,
        DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
        ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
        EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
        REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
        SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
    )
    lab_discovered_pair_capabilities = discover_lab_pair_capabilities(lab_ml_handoff_form)
    backtest_discovered_pair_capabilities = discover_backtest_pair_capabilities(selected_form)
    lab_feature_governance = discover_lab_feature_governance(
        lab_ml_handoff_form,
        registry_path=(
            paths.backtest_jobs_root / "feature_promotion_registry.json"
            if paths.backtest_jobs_root is not None
            else None
        ),
    )
    if lab_feature_governance:
        lab_ml_handoff_form = lab_ml_handoff_form.model_copy(
            update={"discovered_feature_governance": lab_feature_governance}
        )
    supported_expected_edge_feature_groups = (
        ("LEGACY", DEFAULT_EXPECTED_EDGE_FEATURE_NAMES),
        ("REPLAY_MICROSTRUCTURE", REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES),
        ("EXTENDED_MICROSTRUCTURE", EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES),
        ("BUILD14_OBSERVED", BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES),
        ("ENGINE_D_GOVERNANCE", ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES),
        ("ANTI_REVENGE", ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES),
    )
    lab_effective_selected_features = resolve_lab_feature_picker_defaults(
        form_state=lab_ml_handoff_form,
        governance_entries=lab_feature_governance,
        supported_feature_names=SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
    )
    lab_selected_demoted_features = selected_demoted_lab_features(
        selected_feature_names=lab_effective_selected_features,
        governance_entries=lab_feature_governance,
    )
    lab_feature_selection_source = (
        "FORM_SELECTED"
        if lab_ml_handoff_form.selected_features
        else (
            "FORM_CSV"
            if (lab_ml_handoff_form.feature_names or "").strip()
            else "NONE"
        )
    )
    lab_requested_non_legacy_features = tuple(
        name
        for name in lab_effective_selected_features
        if name not in DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    )
    lab_replay_grounding_required = bool(lab_requested_non_legacy_features)
    lab_replay_grounding_ready = bool(
        (lab_ml_handoff_form.b2_run_root or "").strip()
        or (lab_ml_handoff_form.label_store_dataset_path or "").strip()
    )
    backtest_preflight = load_patch6_preflight_preview(
        selected_form=selected_form,
        preview_manifest=None,
        jobs_root=paths.backtest_jobs_root,
    )
    artifact_feature_names = tuple(backtest_preflight.ml_overlay_intake.feature_names)
    backtest_feature_governance = discover_backtest_feature_governance(
        selected_form,
        registry_path=(
            paths.backtest_jobs_root / "feature_promotion_registry.json"
            if paths.backtest_jobs_root is not None
            else None
        ),
    )
    authoritative_frozen_artifact = bool(
        selected_form.ml_mode == "ML_MODE_OVERLAY_FROZEN"
        and backtest_preflight.ml_overlay_intake.ready
        and artifact_feature_names
    )
    backtest_effective_selected_features = (
        resolve_backtest_selected_feature_names(
            selected_form,
            lab_form_state=lab_ml_handoff_form,
            artifact_feature_names=artifact_feature_names,
        )
        if authoritative_frozen_artifact
        else resolve_backtest_feature_picker_defaults(
            form_state=selected_form,
            lab_form_state=lab_ml_handoff_form,
            governance_entries=backtest_feature_governance,
            supported_feature_names=SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
            artifact_feature_names=(),
        )
    )
    backtest_selected_demoted_features = selected_demoted_backtest_features(
        selected_feature_names=backtest_effective_selected_features,
        governance_entries=backtest_feature_governance,
    )
    backtest_feature_selection_source = (
        "FROZEN_ARTIFACT"
        if authoritative_frozen_artifact
        else (
            "FORM_SELECTED"
            if selected_form.selected_features
            else (
                "FORM_EMPTY_SELECTION"
                if str(selected_form.feature_picker_enabled or "").strip().lower()
                in {"1", "true", "yes", "on"}
                else (
                    "FORM_CSV"
                    if (selected_form.feature_names or "").strip()
                    and not selected_form.selected_features
                    else (
                        "LAB_SELECTED"
                        if lab_ml_handoff_form.selected_features
                        else "GOVERNED_DEFAULTS"
                    )
                )
            )
        )
    )
    backtest_feature_picker_read_only = authoritative_frozen_artifact
    runtime = read_runtime_surfaces(
        service_dir=paths.service_dir,
        queue_root=paths.dashboard_command_queue_root,
        observability_output_dir=paths.observability_output_dir,
        backtest_jobs_root=paths.backtest_jobs_root,
        selected_candidate_id=selected_candidate_id,
        active_feature_names=backtest_effective_selected_features,
        artifact_feature_names=artifact_feature_names,
        include_candidate_feature_audits=False,
        log_query=log_query,
        pinned_run_id=pinned_run_id,
    )
    current_form_state = read_current_form_state(paths.backtest_jobs_root)
    source_preview_state = read_source_preview_state(paths.backtest_jobs_root)
    preview_manifest = (
        read_preview_manifest(paths.backtest_jobs_root, source_preview_state.preview_id)
        if source_preview_state is not None and source_preview_state.preview_id
        else None
    )
    if (
        source_preview_state is None
        and preview_manifest is None
        and current_form_state is not None
        and current_form_state.preview_id
    ):
        preview_manifest = read_preview_manifest(
            paths.backtest_jobs_root,
            current_form_state.preview_id,
        )
        if preview_manifest is not None:
            source_preview_state = current_form_state.model_copy(
                update={"state_name": "source_preview_state"},
            )
    source_preview_state, preview_manifest = _align_preview_context_with_current_form(
        selected_form=selected_form,
        source_preview_state=source_preview_state,
        preview_manifest=preview_manifest,
    )
    backtest_preflight = load_patch6_preflight_preview(
        selected_form=selected_form,
        preview_manifest=preview_manifest,
        jobs_root=paths.backtest_jobs_root,
    )
    if current_form_state is None:
        current_form_state = _build_ephemeral_current_form_state(
            selected_form,
            source_preview_state,
        )
    latest_job_state = _build_ephemeral_latest_job_state(
        runtime,
        backtest_preflight.action_name,
    )
    latest_canonical_summary_state = _build_ephemeral_latest_canonical_summary_state(
        runtime,
        backtest_preflight.action_name,
    )
    launch_request_state = read_launch_request_state(paths.backtest_jobs_root)
    backtest_ml_chain_state = read_backtest_ml_chain_state(paths.backtest_jobs_root)
    cockpit_state_consistency = build_state_consistency(
        current_form_state=current_form_state,
        source_preview_state=source_preview_state,
        launch_request_state=launch_request_state,
        latest_canonical_summary_state=latest_canonical_summary_state,
    )
    suspended_pairs = tuple(
        pair
        for pair in (
            () if runtime.service_state is None else runtime.service_state.dashboard_control_suspended_pairs
        )
        if pair in pairs.configured_pairs
    )
    active_pairs = tuple(pair for pair in pairs.configured_pairs if pair not in suspended_pairs)
    pairs = pairs.model_copy(
        update={
            "active_pairs": active_pairs or pairs.configured_pairs,
            "suspended_pairs": suspended_pairs,
            "default_pair": (active_pairs or pairs.configured_pairs)[0],
        }
    )
    chosen = (
        selected_pair.upper()
        if selected_pair and selected_pair.upper() in pairs.active_pairs
        else pairs.default_pair
    )

    replay = read_replay_metrics(paths.auto_exports_root)
    feature_bridge = read_feature_bridge(paths.auto_exports_root)
    sizing_chain = read_sizing_chain(paths.auto_exports_root)
    engines = build_engines_grid(
        replay=replay,
        feature_bridge=feature_bridge,
        service_state_path=paths.service_state,
    )
    build_root = paths.build_root or paths.service_dir.parent.parent
    build1_core_health = read_build1_core_health(build_root)
    lab_review = read_lab_review(build_root)
    tail_risk = read_tail_risk(build_root)
    multiple_testing = read_multiple_testing_guard(build_root)
    capacity_guard = read_capacity_guard(
        build_root=build_root,
        observability_export_path=paths.observability_export,
    )
    if paths.calibration_thresholds is not None:
        calibration = read_calibration_thresholds(paths.calibration_thresholds)
    else:
        calibration = CalibrationThresholdsSnapshot(source_status="missing")
    model_risk = read_model_risk_register(paths.service_dir)
    refusal_journal = read_refusal_journal(paths.service_dir)
    freshness = read_source_freshness(paths)
    queue_trace = read_queue_trace(paths, runtime=runtime)
    service_liveness = read_service_liveness(paths, runtime=runtime)
    warmup_explainer = read_warmup_explainer(paths, warmup=warmup)
    engine_why = read_engine_why_state(
        replay=replay,
        feature_bridge=feature_bridge,
        engines=engines,
    )
    decision_trace = read_decision_trace(paths.auto_exports_root)
    economic_sterilization = read_economic_sterilization(replay)
    lab_vps_transfer = read_lab_vps_transfer(paths)
    kill_proof = read_kill_proof(paths)
    data_quality = read_data_quality_live(paths, pairs=pairs)
    disk_growth = read_disk_growth(paths)
    run_comparison = read_run_comparison(
        paths.auto_exports_root,
        runtime=runtime,
        warmup=warmup,
    )
    system_flow = read_system_flow(
        build1_core_health=build1_core_health,
        freshness=freshness,
        warmup=warmup_explainer,
        service_liveness=service_liveness,
        queue_trace=queue_trace,
        engine_why=engine_why,
        economics=economic_sterilization,
        feature_bridge=feature_bridge,
        refusal_journal=refusal_journal,
        kill_proof=kill_proof,
        data_quality=data_quality,
    )
    runtime = runtime.model_copy(
        update={
            "alerts": runtime.alerts
            + _build_operational_alerts(
                warmup=warmup_explainer,
                service_liveness=service_liveness,
                queue_trace=queue_trace,
                engine_why=engine_why,
                feature_bridge=feature_bridge,
                refusal_journal=refusal_journal,
                data_quality=data_quality,
                disk_growth=disk_growth,
            )
        }
    )
    operational_proof = OperationalProofSnapshot(
        freshness=freshness,
        run_comparison=run_comparison,
        system_flow=system_flow,
        queue_trace=queue_trace,
        service_liveness=service_liveness,
        warmup_explainer=warmup_explainer,
        engine_why=engine_why,
        decision_trace=decision_trace,
        economic_sterilization=economic_sterilization,
        lab_vps_transfer=lab_vps_transfer,
        kill_proof=kill_proof,
        data_quality=data_quality,
        disk_growth=disk_growth,
    )

    effective_grafana_url = runtime.observability.grafana_url or grafana_url
    effective_prometheus_url = (
        runtime.observability.prometheus_url or prometheus_url
    )

    return DashboardViewModel(
        welcome_message=welcome_message,
        service=service,
        warmup=warmup,
        pairs=pairs,
        metrics=metrics,
        artefacts=artefacts[:5],
        grafana_url=effective_grafana_url,
        prometheus_url=effective_prometheus_url,
        selected_pair=chosen,
        rendered_at_iso=datetime.now(tz=UTC).isoformat(),
        current_page=current_page,
        notice_message=notice_message,
        notice_status=notice_status,
        runtime=runtime,
        selected_form=selected_form,
        lab_ml_handoff_form=lab_ml_handoff_form,
        lab_discovered_pair_capabilities=lab_discovered_pair_capabilities,
        backtest_discovered_pair_capabilities=backtest_discovered_pair_capabilities,
        supported_expected_edge_feature_names=SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
        supported_expected_edge_feature_groups=supported_expected_edge_feature_groups,
        lab_feature_governance=lab_feature_governance,
        lab_effective_selected_features=lab_effective_selected_features,
        lab_selected_demoted_features=lab_selected_demoted_features,
        lab_feature_selection_source=lab_feature_selection_source,
        lab_requested_non_legacy_features=lab_requested_non_legacy_features,
        lab_replay_grounding_required=lab_replay_grounding_required,
        lab_replay_grounding_ready=lab_replay_grounding_ready,
        backtest_feature_governance=backtest_feature_governance,
        backtest_effective_selected_features=backtest_effective_selected_features,
        backtest_selected_demoted_features=backtest_selected_demoted_features,
        backtest_feature_selection_source=backtest_feature_selection_source,
        backtest_feature_picker_read_only=backtest_feature_picker_read_only,
        backtest_ml_chain_state=backtest_ml_chain_state,
        backtest_preflight=backtest_preflight,
        current_form_state=current_form_state,
        source_preview_state=source_preview_state,
        launch_request_state=launch_request_state,
        latest_job_state=latest_job_state,
        latest_canonical_summary_state=latest_canonical_summary_state,
        cockpit_state_consistency=cockpit_state_consistency,
        engines=engines,
        replay=replay,
        feature_bridge=feature_bridge,
        sizing_chain=sizing_chain,
        lab_review=lab_review,
        tail_risk=tail_risk,
        multiple_testing=multiple_testing,
        capacity_guard=capacity_guard,
        calibration=calibration,
        model_risk=model_risk,
        refusal_journal=refusal_journal,
        operational_proof=operational_proof,
    )


__all__ = [
    "ArtefactExportDay",
    "ArtefactExportEntry",
    "Build1CoreHealthSnapshot",
    "CockpitPaths",
    "DashboardViewModel",
    "OperationalProofSnapshot",
    "PairMetric",
    "PairSelector",
    "ServiceStatus",
    "WarmupCheck",
    "WarmupSummary",
    "build_dashboard_view_model",
    "list_artefact_exports",
    "read_pair_metrics",
    "read_pair_selector",
    "read_pid",
    "read_service_status",
    "read_warmup_summary",
]
