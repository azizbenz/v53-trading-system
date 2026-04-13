#!/usr/bin/env python3
"""Run the autonomous long-running VPS Shadow service."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from protocols import (  # noqa: E402
    ShadowVpsCampaignSummary,
    ShadowLiveWebSocketConfig,
    ShadowLiveWebSocketCaptureResult,
    ShadowDailyPlanSlot,
    ShadowDailyOrchestrator,
    ShadowVpsServiceEvent,
    ShadowVpsRawInputConfig,
    ShadowVpsRawInputSlot,
    ShadowVpsRuntimeEvidenceBundle,
    build_binance_execution_runtime_bootstrap_bundle,
    ShadowVpsWebsocketInputSlot,
    ShadowVpsServiceStatus,
    ShadowVpsServiceStore,
    build_snapshot_batch_from_injected_websocket_stream,
    capture_live_websocket_snapshot_batch,
)
from alerting import (  # noqa: E402
    TelegramAlerter,
    load_telegram_alerter_config_from_file,
)
from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from interface_contracts.binance_contracts import BinanceCredentials  # noqa: E402
from interface_contracts.shadow_vps_service_contracts import (  # noqa: E402
    ShadowVpsExecutionRuntimeBootstrapSummary,
    ShadowVpsServiceState,
)
from protocols.shadow_vps_service_telegram_alerting import (  # noqa: E402
    build_shadow_vps_service_alert_record,
)
from local_replay_runtime.local_lab_execution_telemetry_artifact import (  # noqa: E402
    build_local_lab_execution_telemetry_artifact_for_export,
    load_local_lab_execution_telemetry_archive,
)
from monitoring import (  # noqa: E402
    sample_disk_usage,
    ProcessMetricsSampler,
    build_shadow_vps_service_recent_events_summary,
    build_shadow_vps_service_monitoring_payload,
    build_shadow_vps_service_observability_export,
    build_shadow_vps_service_prometheus_file_sd,
    build_shadow_vps_service_scrape_manifest,
    write_node_exporter_textfile_payload,
    write_observability_text_payload,
)
from venue_adapters.binance_spot import BinanceAdapterConfig  # noqa: E402


TelegramPostFunc = Callable[[str, dict[str, object], float], tuple[int, str]]


@dataclass(frozen=True)
class ShadowVpsServiceMonitoringConfig:
    node_exporter_textfile_dir: Path | None
    scrape_host: str
    vps_id: str
    node_exporter_port: int
    node_exporter_scheme: str
    node_exporter_metrics_path: str
    prometheus_job_name: str


@dataclass(frozen=True)
class ShadowVpsServiceRuntimeContext:
    service_dir: Path
    resolved_orchestrator_output_dir: Path
    resolved_shadow_output_dir: Path
    resolved_live_captures_root: Path
    resolved_auto_snapshots_root: Path
    resolved_auto_exports_root: Path
    exports_root: Path | None
    raw_inputs_root: Path | None
    websocket_streams_root: Path | None
    live_websocket_config_path: Path | None
    execution_time_sync_offsets_path: Path | None
    execution_runtime_projection_path: Path | None
    regime_lite_assessment_path: Path | None
    regime_lite_safing_recommendation_path: Path | None
    info_stress_assessment_path: Path | None
    resolved_telegram_alert_config_path: Path | None
    resolved_telegram_alert_config_source: str
    resolved_telegram_alert_key_path: Path | None
    resolved_telegram_alert_key_source: str
    bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary
    bootstrap_summary_path: Path | None
    store: ShadowVpsServiceStore
    process_metrics_sampler: ProcessMetricsSampler
    telegram_alerter: TelegramAlerter | None
    launcher: ModuleType
    monitoring: ShadowVpsServiceMonitoringConfig


@dataclass(frozen=True)
class ShadowVpsCycleSelection:
    raw_slot: ShadowVpsRawInputSlot | None
    websocket_slot: ShadowVpsWebsocketInputSlot | None
    next_slot: ShadowDailyPlanSlot | None
    live_capture_dir: Path | None
    auto_snapshot_dir: Path | None
    auto_export_dir: Path | None
    resolved_execution_runtime_projection_path: Path | None
    resolved_execution_runtime_projection_source: str
    resolved_regime_lite_assessment_path: Path | None
    resolved_regime_lite_assessment_source: str
    resolved_regime_lite_safing_recommendation_path: Path | None
    resolved_regime_lite_safing_recommendation_source: str
    resolved_info_stress_assessment_path: Path | None
    resolved_info_stress_assessment_source: str


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _append_service_event(
    *,
    store: ShadowVpsServiceStore,
    event: ShadowVpsServiceEvent,
    telegram_alerter: TelegramAlerter | None,
) -> None:
    store.append_event(event)
    if telegram_alerter is None or event.event_type.startswith("telegram_alert_"):
        return
    alert = build_shadow_vps_service_alert_record(event)
    if alert is None:
        return
    result = telegram_alerter.send(alert)
    store.state.last_telegram_alert_delivery_status = (
        "skipped"
        if result.skipped
        else "sent"
        if result.delivered
        else "failed"
    )
    store.state.last_telegram_alert_delivery_event_type = event.event_type
    store.state.last_telegram_alert_delivery_error = (
        "" if result.delivered or result.skipped else result.reason
    )
    store.persist()
    if result.skipped:
        return
    store.append_event(
        ShadowVpsServiceEvent(
            event_type=(
                "telegram_alert_sent" if result.delivered else "telegram_alert_failed"
            ),
            message=(
                f"Telegram alert delivered for {event.event_type}."
                if result.delivered
                else f"Telegram alert failed for {event.event_type}: {result.reason}"
            ),
            session_date=event.session_date,
            export_dir_ref=event.export_dir_ref,
            error="" if result.delivered else result.reason,
        )
    )


def _load_script_module(script_name: str, module_name: str) -> ModuleType:
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_daily_orchestrator_module() -> ModuleType:
    return _load_script_module(
        "run_shadow_daily_orchestrator.py",
        "shadow_vps_service_daily_orchestrator",
    )


def _load_local_replay_export_module() -> ModuleType:
    return _load_script_module(
        "run_local_replay_export.py",
        "shadow_vps_service_local_replay_export",
    )


def _read_last_run(orchestrator_output_dir: Path) -> dict:
    last_run_path = orchestrator_output_dir / "shadow_daily_orchestrator.last_run.json"
    return json.loads(last_run_path.read_text(encoding="utf-8"))


def _read_optional_json(path_ref: str) -> dict:
    if not path_ref:
        return {}
    try:
        return json.loads(Path(path_ref).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _read_runtime_evidence_bundle(
    bundle_path_ref: str,
) -> ShadowVpsRuntimeEvidenceBundle | None:
    if not bundle_path_ref:
        return None
    bundle_path = Path(bundle_path_ref)
    if not bundle_path.is_file():
        return None
    try:
        return ShadowVpsRuntimeEvidenceBundle.model_validate_json(
            bundle_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        return None


def _read_campaign_summary(
    summary_path_ref: str,
) -> ShadowVpsCampaignSummary | None:
    if not summary_path_ref:
        return None
    summary_path = Path(summary_path_ref)
    if not summary_path.is_file():
        return None
    try:
        return ShadowVpsCampaignSummary.model_validate_json(
            summary_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        return None


def _read_live_capture_result(
    live_capture_dir: Path | None,
) -> ShadowLiveWebSocketCaptureResult | None:
    if live_capture_dir is None:
        return None
    summary_path = live_capture_dir / "live_websocket_capture_summary.json"
    snapshot_batch_path = live_capture_dir / "live_websocket_snapshot_batch.json"
    if not summary_path.is_file() or not snapshot_batch_path.is_file():
        return None
    try:
        return ShadowLiveWebSocketCaptureResult.model_validate_json(
            summary_path.read_text(encoding="utf-8")
        )
    except (TypeError, ValueError):
        payload = _read_optional_json(str(summary_path))
        try:
            return ShadowLiveWebSocketCaptureResult(
                session_date=live_capture_dir.name,
                live_capture_dir_ref=str(live_capture_dir.resolve()),
                snapshot_batch_path_ref=str(snapshot_batch_path.resolve()),
                summary_path_ref=str(summary_path.resolve()),
                emitted_message_count=int(payload.get("emitted_message_count", 0)),
                accepted_message_count=int(payload.get("accepted_message_count", 0)),
                ignored_message_count=int(payload.get("ignored_message_count", 0)),
                rejected_message_count=int(payload.get("rejected_message_count", 0)),
                pair_scope=tuple(str(value) for value in payload.get("pair_scope", ())),
                event_types=tuple(str(value) for value in payload.get("event_types", ())),
                time_sync_offsets_path_ref=str(
                    payload.get("time_sync_offsets_path_ref", "")
                ),
                time_sync_sample_count=int(payload.get("time_sync_sample_count", 0)),
                time_sync_probe_error=str(payload.get("time_sync_probe_error", "")),
                user_data_summary_path_ref=str(
                    payload.get("user_data_summary_path_ref", "")
                ),
                user_data_events_path_ref=str(
                    payload.get("user_data_events_path_ref", "")
                ),
                user_data_authenticated=bool(
                    payload.get("user_data_authenticated", False)
                ),
                user_data_subscription_id=(
                    int(payload["user_data_subscription_id"])
                    if payload.get("user_data_subscription_id") is not None
                    else None
                ),
                user_data_event_count=int(payload.get("user_data_event_count", 0)),
                user_data_event_types=tuple(
                    str(value) for value in payload.get("user_data_event_types", ())
                ),
            )
        except (TypeError, ValueError):
            return None


def _read_raw_input_config(config_path: Path | None) -> ShadowVpsRawInputConfig:
    if config_path is None or not config_path.is_file():
        return ShadowVpsRawInputConfig()
    return ShadowVpsRawInputConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _read_live_websocket_config(config_path: Path) -> ShadowLiveWebSocketConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing live websocket config: {config_path}")
    return ShadowLiveWebSocketConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _resolve_live_websocket_artifact_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    ref: str,
) -> tuple[Path | None, str]:
    if explicit_path is not None:
        return explicit_path, "cli"
    resolved_ref = ref.strip()
    if not resolved_ref:
        return None, "not_configured"
    candidate = Path(resolved_ref)
    if candidate.is_absolute() or live_websocket_config_path is None:
        return candidate, "live_websocket_config"
    return (
        (live_websocket_config_path.parent / candidate).resolve(),
        "live_websocket_config",
    )


def _resolve_execution_runtime_projection_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.execution_runtime_projection_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_execution_runtime_bootstrap_enabled(
    *,
    explicit_enabled: bool,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[bool, str]:
    if explicit_enabled:
        return True, "cli"
    if live_config is not None and live_config.execution_runtime_bootstrap_enabled:
        return True, "live_websocket_config"
    return False, "not_configured"


def _resolve_execution_runtime_gatekeeper_audit_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.execution_runtime_gatekeeper_audit_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_regime_lite_assessment_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.regime_lite_assessment_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_regime_lite_safing_recommendation_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.regime_lite_safing_recommendation_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_info_stress_assessment_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.info_stress_assessment_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_telegram_alert_config_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.telegram_alert_config_path_ref
            if live_config is not None
            else ""
        ),
    )


def _resolve_telegram_alert_key_path(
    *,
    explicit_path: Path | None,
    live_websocket_config_path: Path | None,
    live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[Path | None, str]:
    return _resolve_live_websocket_artifact_path(
        explicit_path=explicit_path,
        live_websocket_config_path=live_websocket_config_path,
        ref=(
            live_config.telegram_alert_key_path_ref if live_config is not None else ""
        ),
    )


def _pin_auto_export_session_date(auto_export_dir: Path, session_date: str) -> None:
    manifest_path = auto_export_dir / "replay_run_manifest.json"
    if not manifest_path.is_file():
        return
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return
    governed_timeframe_scope = f"{session_date}/{session_date}"
    if payload.get("timeframe_scope") == governed_timeframe_scope:
        return
    payload["timeframe_scope"] = governed_timeframe_scope
    manifest_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _write_execution_runtime_bootstrap_summary(
    *,
    service_dir: Path,
    bootstrap_enabled: bool,
    bootstrap_source: str,
    live_config: ShadowLiveWebSocketConfig | None,
    execution_runtime_projection_path: Path | None,
    execution_runtime_projection_source: str,
    gatekeeper_audit_path: Path | None,
    gatekeeper_audit_source: str,
) -> tuple[ShadowVpsExecutionRuntimeBootstrapSummary, Path | None]:
    if not bootstrap_enabled:
        return ShadowVpsExecutionRuntimeBootstrapSummary(), None

    summary_path = service_dir / "execution_runtime_bootstrap.summary.json"
    bootstrap_config = live_config or ShadowLiveWebSocketConfig()
    gatekeeper_audit_ref = (
        str(gatekeeper_audit_path.resolve()) if gatekeeper_audit_path is not None else ""
    )
    try:
        api_key = os.getenv(bootstrap_config.user_data_api_key_env_var, "").strip()
        api_secret = os.getenv(
            bootstrap_config.user_data_api_secret_env_var,
            "",
        ).strip()
        if not api_key or not api_secret:
            raise ValueError(
                "execution runtime bootstrap requires Binance API credentials in the configured env vars"
            )

        bundle = build_binance_execution_runtime_bootstrap_bundle(
            credentials=BinanceCredentials(
                api_key=api_key,
                secret_key=api_secret,
                label="shadow_vps_service",
            ),
            config=BinanceAdapterConfig(
                rest_base_url=bootstrap_config.time_sync_rest_base_url,
                timeout_s=bootstrap_config.time_sync_rest_timeout_s,
                recv_window_ms=bootstrap_config.user_data_recv_window_ms,
                websocket_endpoint=bootstrap_config.endpoint,
                user_data_websocket_endpoint=bootstrap_config.user_data_endpoint,
                user_data_connect_timeout_s=bootstrap_config.connect_timeout_s,
                user_data_recv_timeout_s=bootstrap_config.recv_timeout_s,
            ),
            execution_runtime_projection_path=execution_runtime_projection_path,
            gatekeeper_audit_path=gatekeeper_audit_path,
            reconciliation_boot_now=time.time(),
            user_data_stream_enabled=bootstrap_config.user_data_stream_enabled,
        )
        boot_result = bundle.reconciliation_boot_result
        summary = ShadowVpsExecutionRuntimeBootstrapSummary(
            status="ready",
            source=bootstrap_source,
            execution_runtime_projection_ref=(
                str(execution_runtime_projection_path.resolve())
                if execution_runtime_projection_path is not None
                else ""
            ),
            execution_runtime_projection_source=(
                execution_runtime_projection_source
                if execution_runtime_projection_path is not None
                else "not_configured"
            ),
            gatekeeper_audit_ref=gatekeeper_audit_ref,
            gatekeeper_audit_source=(
                gatekeeper_audit_source
                if gatekeeper_audit_path is not None
                else "not_configured"
            ),
            user_data_stream_enabled=bootstrap_config.user_data_stream_enabled,
            reconciliation_boot_executed=bool(
                boot_result is not None and boot_result.executed
            ),
            reconciliation_boot_trading_blocked=bool(
                boot_result is not None and boot_result.trading_blocked
            ),
            reconciliation_boot_circuit_breaker_tripped=bool(
                boot_result is not None and boot_result.circuit_breaker_tripped
            ),
            reconciliation_boot_detail=(
                boot_result.detail if boot_result is not None else ""
            ),
            reconciliation_boot_recovery_action=(
                boot_result.recovery_action if boot_result is not None else ""
            ),
            reconciliation_boot_divergence_count=(
                int(boot_result.divergence_count) if boot_result is not None else 0
            ),
        )
    except Exception as exc:
        summary = ShadowVpsExecutionRuntimeBootstrapSummary(
            status="failed",
            source=bootstrap_source,
            execution_runtime_projection_ref=(
                str(execution_runtime_projection_path.resolve())
                if execution_runtime_projection_path is not None
                else ""
            ),
            execution_runtime_projection_source=(
                execution_runtime_projection_source
                if execution_runtime_projection_path is not None
                else "not_configured"
            ),
            gatekeeper_audit_ref=gatekeeper_audit_ref,
            gatekeeper_audit_source=(
                gatekeeper_audit_source
                if gatekeeper_audit_path is not None
                else "not_configured"
            ),
            user_data_stream_enabled=bootstrap_config.user_data_stream_enabled,
            error=str(exc),
        )

    atomic_write_json(summary_path, summary.model_dump(mode="json"))
    return summary, summary_path


def _discover_raw_input_slot(raw_inputs_root: Path, session_date: str) -> ShadowVpsRawInputSlot:
    raw_input_dir = raw_inputs_root / session_date
    if not raw_input_dir.is_dir():
        raise FileNotFoundError(
            f"Missing raw input directory for session_date={session_date}: {raw_input_dir}"
        )
    dataset_candidates = (
        "replay_dataset.json",
        "replay_dataset.jsonl",
        "replay_dataset.csv",
        "dataset.json",
        "dataset.jsonl",
        "dataset.csv",
    )
    snapshot_candidates = (
        "snapshot_batch.json",
        "snapshot_batch.jsonl",
        "snapshot_batch.csv",
        "snapshots.json",
        "snapshots.jsonl",
        "snapshots.csv",
    )
    dataset_path = next(
        (raw_input_dir / candidate for candidate in dataset_candidates if (raw_input_dir / candidate).is_file()),
        None,
    )
    snapshot_path = next(
        (raw_input_dir / candidate for candidate in snapshot_candidates if (raw_input_dir / candidate).is_file()),
        None,
    )
    config_path = raw_input_dir / "shadow_input_config.json"
    return ShadowVpsRawInputSlot(
        session_date=session_date,
        raw_input_dir_ref=str(raw_input_dir.resolve()),
        dataset_path_ref=str(dataset_path.resolve()) if dataset_path is not None else "",
        snapshot_path_ref=str(snapshot_path.resolve()) if snapshot_path is not None else "",
        config_path_ref=str(config_path.resolve()) if config_path.is_file() else "",
        config=_read_raw_input_config(config_path if config_path.is_file() else None),
    )


def _select_next_raw_input_slot(
    raw_inputs_root: Path,
    orchestrator: ShadowDailyOrchestrator,
) -> ShadowVpsRawInputSlot | None:
    if not raw_inputs_root.exists():
        return None
    completed_dates = set(orchestrator.completed_session_dates())
    dated_dirs = sorted(
        item
        for item in raw_inputs_root.iterdir()
        if item.is_dir()
    )
    for item in dated_dirs:
        try:
            session_date = date.fromisoformat(item.name).isoformat()
        except ValueError:
            continue
        if session_date in completed_dates:
            continue
        return _discover_raw_input_slot(raw_inputs_root, session_date)
    return None


def _discover_websocket_input_slot(
    websocket_streams_root: Path,
    session_date: str,
) -> ShadowVpsWebsocketInputSlot:
    websocket_input_dir = websocket_streams_root / session_date
    if not websocket_input_dir.is_dir():
        raise FileNotFoundError(
            f"Missing websocket input directory for session_date={session_date}: "
            f"{websocket_input_dir}"
        )
    stream_candidates = (
        "websocket_stream.jsonl",
        "websocket_stream.json",
        "websocket_frames.jsonl",
        "websocket_frames.json",
    )
    stream_path = next(
        (
            websocket_input_dir / candidate
            for candidate in stream_candidates
            if (websocket_input_dir / candidate).is_file()
        ),
        None,
    )
    if stream_path is None:
        raise FileNotFoundError(
            f"Missing websocket stream file in {websocket_input_dir}"
        )
    config_path = websocket_input_dir / "shadow_input_config.json"
    return ShadowVpsWebsocketInputSlot(
        session_date=session_date,
        websocket_input_dir_ref=str(websocket_input_dir.resolve()),
        stream_path_ref=str(stream_path.resolve()),
        config_path_ref=str(config_path.resolve()) if config_path.is_file() else "",
        config=_read_raw_input_config(config_path if config_path.is_file() else None),
    )


def _select_next_websocket_input_slot(
    websocket_streams_root: Path,
    orchestrator: ShadowDailyOrchestrator,
) -> ShadowVpsWebsocketInputSlot | None:
    if not websocket_streams_root.exists():
        return None
    completed_dates = set(orchestrator.completed_session_dates())
    dated_dirs = sorted(item for item in websocket_streams_root.iterdir() if item.is_dir())
    for item in dated_dirs:
        try:
            session_date = date.fromisoformat(item.name).isoformat()
        except ValueError:
            continue
        if session_date in completed_dates:
            continue
        return _discover_websocket_input_slot(websocket_streams_root, session_date)
    return None


def _ensure_auto_export_from_raw_slot(
    raw_slot: ShadowVpsRawInputSlot,
    *,
    auto_exports_root: Path,
) -> Path:
    auto_export_dir = auto_exports_root / raw_slot.session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-native-{raw_slot.session_date}",
        "--strategy-id",
        raw_slot.config.strategy_id,
        "--strategy-classification",
        raw_slot.config.strategy_classification,
        "--strategy-version",
        raw_slot.config.strategy_version,
        "--lineage-version",
        raw_slot.config.lineage_version,
        "--performance-mode",
        raw_slot.config.performance_mode,
    ]
    if raw_slot.dataset_path_ref:
        argv.extend(["--dataset-path", raw_slot.dataset_path_ref])
    if raw_slot.snapshot_path_ref:
        argv.extend(["--snapshot-path", raw_slot.snapshot_path_ref])
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return auto_export_dir


def _ensure_auto_export_from_websocket_slot(
    websocket_slot: ShadowVpsWebsocketInputSlot,
    *,
    auto_snapshots_root: Path,
    auto_exports_root: Path,
) -> tuple[Path, Path]:
    auto_snapshot_dir = auto_snapshots_root / websocket_slot.session_date
    auto_snapshot_path = auto_snapshot_dir / "websocket_snapshot_batch.json"
    auto_summary_path = auto_snapshot_dir / "websocket_snapshot_ingest.json"
    if not auto_snapshot_path.is_file() or not auto_summary_path.is_file():
        auto_snapshot_dir.mkdir(parents=True, exist_ok=True)
        build_snapshot_batch_from_injected_websocket_stream(
            Path(websocket_slot.stream_path_ref),
            snapshot_batch_path=auto_snapshot_path,
            summary_path=auto_summary_path,
        )

    auto_export_dir = auto_exports_root / websocket_slot.session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return auto_snapshot_dir, auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-websocket-{websocket_slot.session_date}",
        "--strategy-id",
        websocket_slot.config.strategy_id,
        "--strategy-classification",
        websocket_slot.config.strategy_classification,
        "--strategy-version",
        websocket_slot.config.strategy_version,
        "--lineage-version",
        websocket_slot.config.lineage_version,
        "--performance-mode",
        websocket_slot.config.performance_mode,
        "--snapshot-path",
        str(auto_snapshot_path),
    ]
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return auto_snapshot_dir, auto_export_dir


def _ensure_auto_export_from_live_websocket(
    live_config: ShadowLiveWebSocketConfig,
    *,
    live_captures_root: Path,
    auto_exports_root: Path,
) -> tuple[Path, Path]:
    session_date = live_config.session_date_override or date.today().isoformat()
    live_capture_dir = live_captures_root / session_date
    capture_summary_path = live_capture_dir / "live_websocket_capture_summary.json"
    snapshot_batch_path = live_capture_dir / "live_websocket_snapshot_batch.json"
    if not capture_summary_path.is_file() or not snapshot_batch_path.is_file():
        capture_live_websocket_snapshot_batch(
            live_config,
            output_dir=live_capture_dir,
        )

    auto_export_dir = auto_exports_root / session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return live_capture_dir, auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-live-{session_date}",
        "--strategy-id",
        live_config.config.strategy_id,
        "--strategy-classification",
        live_config.config.strategy_classification,
        "--strategy-version",
        live_config.config.strategy_version,
        "--lineage-version",
        live_config.config.lineage_version,
        "--performance-mode",
        live_config.config.performance_mode,
        "--snapshot-path",
        str(snapshot_batch_path),
    ]
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return live_capture_dir, auto_export_dir


def _resolve_acquisition_mode(
    *,
    raw_slot: ShadowVpsRawInputSlot | None,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_dir: Path | None,
    export_dir_ref: str,
) -> str:
    if live_capture_dir is not None:
        return "native_live_websocket_auto_export"
    if websocket_slot is not None:
        return "websocket_stream_auto_export"
    if raw_slot is not None:
        return "raw_input_auto_export"
    if export_dir_ref:
        return "dated_export"
    return "demo"


def _last_run_str(last_run: dict, key: str, default: str = "") -> str:
    return str(last_run.get(key, default))


def _last_run_bool(last_run: dict, key: str, default: bool = False) -> bool:
    return bool(last_run.get(key, default))


def _last_run_int(last_run: dict, key: str, default: int = 0) -> int:
    return int(last_run.get(key, default))


def _last_run_str_tuple(
    last_run: dict,
    key: str,
    default: tuple[str, ...] = (),
) -> tuple[str, ...]:
    return tuple(str(value) for value in last_run.get(key, default))


def _build_runtime_evidence_input_fields(
    *,
    session_date: str,
    raw_slot: ShadowVpsRawInputSlot | None,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    last_run: dict,
) -> dict[str, object]:
    return {
        "session_date": session_date,
        "acquisition_mode": _resolve_acquisition_mode(
            raw_slot=raw_slot,
            websocket_slot=websocket_slot,
            live_capture_dir=Path(live_capture_result.live_capture_dir_ref)
            if live_capture_result is not None
            else None,
            export_dir_ref=_last_run_str(last_run, "export_dir_ref"),
        ),
        "raw_input_dir_ref": raw_slot.raw_input_dir_ref if raw_slot is not None else "",
        "websocket_input_dir_ref": (
            websocket_slot.websocket_input_dir_ref if websocket_slot is not None else ""
        ),
        "live_capture_dir_ref": (
            live_capture_result.live_capture_dir_ref if live_capture_result is not None else ""
        ),
        "live_capture_snapshot_batch_ref": (
            live_capture_result.snapshot_batch_path_ref if live_capture_result is not None else ""
        ),
        "live_capture_summary_ref": (
            live_capture_result.summary_path_ref if live_capture_result is not None else ""
        ),
        "live_capture_emitted_message_count": (
            live_capture_result.emitted_message_count if live_capture_result is not None else 0
        ),
        "live_capture_accepted_message_count": (
            live_capture_result.accepted_message_count if live_capture_result is not None else 0
        ),
        "live_capture_ignored_message_count": (
            live_capture_result.ignored_message_count if live_capture_result is not None else 0
        ),
        "live_capture_rejected_message_count": (
            live_capture_result.rejected_message_count if live_capture_result is not None else 0
        ),
        "live_capture_pair_scope": (
            live_capture_result.pair_scope if live_capture_result is not None else ()
        ),
        "live_capture_event_types": (
            live_capture_result.event_types if live_capture_result is not None else ()
        ),
        "live_capture_time_sync_offsets_ref": (
            live_capture_result.time_sync_offsets_path_ref
            if live_capture_result is not None
            else ""
        ),
        "live_capture_time_sync_sample_count": (
            live_capture_result.time_sync_sample_count if live_capture_result is not None else 0
        ),
        "live_capture_time_sync_probe_error": (
            live_capture_result.time_sync_probe_error if live_capture_result is not None else ""
        ),
        "live_user_data_summary_ref": (
            live_capture_result.user_data_summary_path_ref
            if live_capture_result is not None
            else ""
        ),
        "live_user_data_events_ref": (
            live_capture_result.user_data_events_path_ref
            if live_capture_result is not None
            else ""
        ),
        "live_user_data_authenticated": (
            live_capture_result.user_data_authenticated
            if live_capture_result is not None
            else False
        ),
        "live_user_data_subscription_id": (
            live_capture_result.user_data_subscription_id
            if live_capture_result is not None
            else None
        ),
        "live_user_data_event_count": (
            live_capture_result.user_data_event_count if live_capture_result is not None else 0
        ),
        "live_user_data_event_types": (
            live_capture_result.user_data_event_types if live_capture_result is not None else ()
        ),
    }


def _build_runtime_evidence_execution_fields(last_run: dict) -> dict[str, object]:
    return {
        "execution_telemetry_status": _last_run_str(
            last_run, "execution_telemetry_status", "not_configured"
        ),
        "telegram_alert_delivery_status": _last_run_str(
            last_run, "telegram_alert_delivery_status", "not_configured"
        ),
        "telegram_alert_delivery_event_type": _last_run_str(
            last_run, "telegram_alert_delivery_event_type"
        ),
        "telegram_alert_delivery_error": _last_run_str(
            last_run, "telegram_alert_delivery_error"
        ),
        "telegram_alert_config_ref": _last_run_str(last_run, "telegram_alert_config_ref"),
        "telegram_alert_config_source": _last_run_str(
            last_run, "telegram_alert_config_source", "not_configured"
        ),
        "telegram_alert_key_ref": _last_run_str(last_run, "telegram_alert_key_ref"),
        "telegram_alert_key_source": _last_run_str(
            last_run, "telegram_alert_key_source", "not_configured"
        ),
        "execution_runtime_bootstrap_ref": _last_run_str(
            last_run, "execution_runtime_bootstrap_ref"
        ),
        "execution_runtime_bootstrap_status": _last_run_str(
            last_run, "execution_runtime_bootstrap_status", "not_configured"
        ),
        "execution_runtime_bootstrap_source": _last_run_str(
            last_run, "execution_runtime_bootstrap_source", "not_configured"
        ),
        "execution_runtime_gatekeeper_audit_ref": _last_run_str(
            last_run, "execution_runtime_gatekeeper_audit_ref"
        ),
        "execution_runtime_gatekeeper_audit_source": _last_run_str(
            last_run, "execution_runtime_gatekeeper_audit_source", "not_configured"
        ),
        "execution_runtime_bootstrap_user_data_stream_enabled": _last_run_bool(
            last_run, "execution_runtime_bootstrap_user_data_stream_enabled"
        ),
        "execution_runtime_bootstrap_reconciliation_boot_executed": _last_run_bool(
            last_run, "execution_runtime_bootstrap_reconciliation_boot_executed"
        ),
        "execution_runtime_bootstrap_reconciliation_boot_trading_blocked": (
            _last_run_bool(last_run, "execution_runtime_bootstrap_reconciliation_boot_trading_blocked")
        ),
        "execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped": (
            _last_run_bool(
                last_run,
                "execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped",
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_detail": _last_run_str(
            last_run, "execution_runtime_bootstrap_reconciliation_boot_detail"
        ),
        "execution_runtime_bootstrap_reconciliation_boot_recovery_action": (
            _last_run_str(last_run, "execution_runtime_bootstrap_reconciliation_boot_recovery_action")
        ),
        "execution_runtime_bootstrap_reconciliation_boot_divergence_count": _last_run_int(
            last_run, "execution_runtime_bootstrap_reconciliation_boot_divergence_count"
        ),
    }


def _build_runtime_evidence_projection_fields(last_run: dict) -> dict[str, object]:
    return {
        "execution_runtime_projection_ref": _last_run_str(
            last_run, "execution_runtime_projection_ref"
        ),
        "execution_runtime_projection_source": _last_run_str(
            last_run, "execution_runtime_projection_source", "not_configured"
        ),
        "execution_runtime_projection_status": _last_run_str(
            last_run, "execution_runtime_projection_status", "not_configured"
        ),
        "execution_runtime_projection_ready": _last_run_bool(
            last_run, "execution_runtime_projection_ready"
        ),
        "execution_runtime_projection_consumer_count": _last_run_int(
            last_run, "execution_runtime_projection_consumer_count"
        ),
        "execution_runtime_projection_ready_consumer_count": _last_run_int(
            last_run, "execution_runtime_projection_ready_consumer_count"
        ),
        "execution_runtime_projection_partial_consumer_count": _last_run_int(
            last_run, "execution_runtime_projection_partial_consumer_count"
        ),
        "execution_runtime_projection_blocked_consumer_count": _last_run_int(
            last_run, "execution_runtime_projection_blocked_consumer_count"
        ),
        "execution_runtime_projection_bridge_status": _last_run_str(
            last_run, "execution_runtime_projection_bridge_status", "planned"
        ),
        "execution_runtime_projection_bridge_loaded": _last_run_bool(
            last_run, "execution_runtime_projection_bridge_loaded"
        ),
        "execution_runtime_projection_rate_limit_model_loaded": _last_run_bool(
            last_run, "execution_runtime_projection_rate_limit_model_loaded"
        ),
        "execution_runtime_projection_spread_guard_model_loaded": _last_run_bool(
            last_run, "execution_runtime_projection_spread_guard_model_loaded"
        ),
        "execution_runtime_projection_slippage_model_loaded": _last_run_bool(
            last_run, "execution_runtime_projection_slippage_model_loaded"
        ),
    }


def _build_runtime_evidence_regime_fields(last_run: dict) -> dict[str, object]:
    return {
        "regime_lite_assessment_ref": _last_run_str(last_run, "regime_lite_assessment_ref"),
        "regime_lite_assessment_source": _last_run_str(
            last_run, "regime_lite_assessment_source", "not_configured"
        ),
        "regime_lite_safing_recommendation_ref": _last_run_str(
            last_run, "regime_lite_safing_recommendation_ref"
        ),
        "regime_lite_safing_recommendation_source": _last_run_str(
            last_run, "regime_lite_safing_recommendation_source", "not_configured"
        ),
        "regime_lite_governance_status": _last_run_str(
            last_run, "regime_lite_governance_status", "not_configured"
        ),
        "regime_lite_state": _last_run_str(last_run, "regime_lite_state", "not_configured"),
        "regime_lite_candidate_state": _last_run_str(
            last_run, "regime_lite_candidate_state", "not_configured"
        ),
        "regime_lite_state_changed": _last_run_bool(last_run, "regime_lite_state_changed"),
        "regime_lite_entries_blocked": _last_run_bool(last_run, "regime_lite_entries_blocked"),
        "regime_lite_sudden_event": _last_run_bool(last_run, "regime_lite_sudden_event"),
        "regime_lite_safing_severity": _last_run_str(
            last_run, "regime_lite_safing_severity", "not_configured"
        ),
        "regime_lite_safing_should_block_new_entries": _last_run_bool(
            last_run, "regime_lite_safing_should_block_new_entries"
        ),
        "regime_lite_safing_should_exit_all": _last_run_bool(
            last_run, "regime_lite_safing_should_exit_all"
        ),
        "regime_lite_safing_recommended_operator_action": _last_run_str(
            last_run, "regime_lite_safing_recommended_operator_action"
        ),
        "regime_lite_safing_operator_safing_request_action": _last_run_str(
            last_run, "regime_lite_safing_operator_safing_request_action"
        ),
        "regime_lite_safing_operator_safing_request_source_runtime_mode": (
            _last_run_str(last_run, "regime_lite_safing_operator_safing_request_source_runtime_mode")
        ),
        "regime_lite_safing_reason_codes": _last_run_str_tuple(
            last_run, "regime_lite_safing_reason_codes"
        ),
        "regime_lite_safing_detail": _last_run_str(last_run, "regime_lite_safing_detail"),
    }


def _build_runtime_evidence_info_stress_fields(last_run: dict) -> dict[str, object]:
    return {
        "info_stress_assessment_ref": _last_run_str(last_run, "info_stress_assessment_ref"),
        "info_stress_assessment_source": _last_run_str(
            last_run, "info_stress_assessment_source", "not_configured"
        ),
        "info_stress_governance_status": _last_run_str(
            last_run, "info_stress_governance_status", "not_configured"
        ),
        "info_stress_level": _last_run_str(last_run, "info_stress_level", "not_configured"),
        "info_stress_alert_count": _last_run_int(last_run, "info_stress_alert_count"),
        "info_stress_entries_blocked": _last_run_bool(last_run, "info_stress_entries_blocked"),
        "info_stress_entries_blocked_until_ts": _last_run_int(
            last_run, "info_stress_entries_blocked_until_ts"
        ),
        "info_stress_reason_codes": _last_run_str_tuple(
            last_run, "info_stress_reason_codes"
        ),
        "info_stress_detail": _last_run_str(last_run, "info_stress_detail"),
    }


def _build_runtime_evidence_artifact_fields(
    *,
    auto_snapshot_dir: Path | None,
    auto_export_dir: Path | None,
    runtime_evidence_payload: dict,
    last_run: dict,
) -> dict[str, object]:
    return {
        "auto_snapshot_dir_ref": (
            str(auto_snapshot_dir.resolve()) if auto_snapshot_dir is not None else ""
        ),
        "auto_export_dir_ref": (
            str(auto_export_dir.resolve()) if auto_export_dir is not None else ""
        ),
        "export_dir_ref": _last_run_str(last_run, "export_dir_ref"),
        "local_replay_evidence_ref": _last_run_str(last_run, "local_replay_evidence_ref"),
        "shadow_runtime_evidence_ref": _last_run_str(last_run, "shadow_runtime_evidence_ref"),
        "shadow_summary_ref": _last_run_str(last_run, "shadow_summary_ref"),
        "shadow_report_ref": _last_run_str(last_run, "shadow_report_ref"),
        "shadow_session_summary_ref": _last_run_str(
            last_run, "shadow_session_summary_ref"
        ),
        "shadow_session_registry_ref": _last_run_str(
            last_run, "shadow_session_registry_ref"
        ),
        "orchestrator_state_ref": _last_run_str(last_run, "state_path"),
        "runtime_data_source": str(runtime_evidence_payload.get("data_source", "unknown")),
        "runtime_evidence_summary": str(
            runtime_evidence_payload.get(
                "evidence_summary",
                "No real runtime evidence recorded",
            )
        ),
        "accepted": _last_run_bool(last_run, "accepted"),
        "consecutive_days": _last_run_int(last_run, "consecutive_days"),
        "remaining_days": _last_run_int(last_run, "remaining_days"),
    }


def _write_runtime_evidence_bundle(
    *,
    service_dir: Path,
    session_date: str,
    raw_slot: ShadowVpsRawInputSlot | None,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    auto_snapshot_dir: Path | None,
    auto_export_dir: Path | None,
    last_run: dict,
) -> Path:
    bundle_dir = service_dir / "runtime_evidence"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / f"{session_date}.shadow_vps_runtime_evidence.json"
    runtime_evidence_payload = _read_optional_json(
        _last_run_str(last_run, "shadow_runtime_evidence_ref")
    )
    bundle_fields: dict[str, object] = {}
    bundle_fields.update(
        _build_runtime_evidence_input_fields(
            session_date=session_date,
            raw_slot=raw_slot,
            websocket_slot=websocket_slot,
            live_capture_result=live_capture_result,
            last_run=last_run,
        )
    )
    bundle_fields.update(_build_runtime_evidence_execution_fields(last_run))
    bundle_fields.update(_build_runtime_evidence_projection_fields(last_run))
    bundle_fields.update(_build_runtime_evidence_regime_fields(last_run))
    bundle_fields.update(_build_runtime_evidence_info_stress_fields(last_run))
    bundle_fields.update(
        _build_runtime_evidence_artifact_fields(
            auto_snapshot_dir=auto_snapshot_dir,
            auto_export_dir=auto_export_dir,
            runtime_evidence_payload=runtime_evidence_payload,
            last_run=last_run,
        )
    )
    bundle = ShadowVpsRuntimeEvidenceBundle(**bundle_fields)
    bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return bundle_path


def _campaign_bundle_value(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
    field_name: str,
    default: object,
) -> object:
    return getattr(bundle, field_name) if bundle is not None else default


def _campaign_bundle_or_fallback(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
    field_name: str,
    fallback: object,
) -> object:
    if bundle is None:
        return fallback
    value = getattr(bundle, field_name)
    return fallback if value in ("", None) else value


def _build_campaign_summary_core_fields(
    state: ShadowVpsServiceState,
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    accepted = bool(_campaign_bundle_value(bundle, "accepted", False))
    remaining_days = int(_campaign_bundle_value(bundle, "remaining_days", 0))
    return {
        "service_status": state.service_status,
        "loop_count": state.loop_count,
        "success_count": state.success_count,
        "idle_count": state.idle_count,
        "failure_count": state.failure_count,
        "resumed": state.resumed,
        "last_selected_session_date": state.last_selected_session_date,
        "last_completed_session_date": state.last_completed_session_date,
        "acquisition_mode": _campaign_bundle_value(bundle, "acquisition_mode", ""),
        "accepted": accepted,
        "consecutive_days": _campaign_bundle_value(bundle, "consecutive_days", 0),
        "remaining_days": remaining_days,
        "promotion_gate_passed": accepted and remaining_days == 0,
        "runtime_data_source": _campaign_bundle_value(
            bundle,
            "runtime_data_source",
            "unknown",
        ),
        "runtime_evidence_summary": _campaign_bundle_value(
            bundle,
            "runtime_evidence_summary",
            "No real runtime evidence recorded",
        ),
        "execution_telemetry_status": state.last_execution_telemetry_status,
        "telegram_alert_delivery_status": state.last_telegram_alert_delivery_status,
        "telegram_alert_delivery_event_type": (
            state.last_telegram_alert_delivery_event_type
        ),
        "telegram_alert_delivery_error": state.last_telegram_alert_delivery_error,
        "runtime_evidence_bundle_ref": state.last_runtime_evidence_bundle_ref,
        "shadow_report_ref": state.last_shadow_report_ref,
        "shadow_session_summary_ref": state.last_shadow_session_summary_ref,
        "shadow_session_registry_ref": state.last_shadow_session_registry_ref,
        "orchestrator_state_ref": state.last_orchestrator_state_ref,
    }


def _build_campaign_summary_live_capture_fields(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "live_capture_summary_ref": _campaign_bundle_value(
            bundle,
            "live_capture_summary_ref",
            "",
        ),
        "live_capture_emitted_message_count": _campaign_bundle_value(
            bundle,
            "live_capture_emitted_message_count",
            0,
        ),
        "live_capture_accepted_message_count": _campaign_bundle_value(
            bundle,
            "live_capture_accepted_message_count",
            0,
        ),
        "live_capture_ignored_message_count": _campaign_bundle_value(
            bundle,
            "live_capture_ignored_message_count",
            0,
        ),
        "live_capture_rejected_message_count": _campaign_bundle_value(
            bundle,
            "live_capture_rejected_message_count",
            0,
        ),
        "live_capture_pair_scope": _campaign_bundle_value(
            bundle,
            "live_capture_pair_scope",
            (),
        ),
        "live_capture_event_types": _campaign_bundle_value(
            bundle,
            "live_capture_event_types",
            (),
        ),
        "live_capture_time_sync_offsets_ref": _campaign_bundle_value(
            bundle,
            "live_capture_time_sync_offsets_ref",
            "",
        ),
        "live_capture_time_sync_sample_count": _campaign_bundle_value(
            bundle,
            "live_capture_time_sync_sample_count",
            0,
        ),
        "live_capture_time_sync_probe_error": _campaign_bundle_value(
            bundle,
            "live_capture_time_sync_probe_error",
            "",
        ),
        "live_user_data_summary_ref": _campaign_bundle_value(
            bundle,
            "live_user_data_summary_ref",
            "",
        ),
        "live_user_data_authenticated": _campaign_bundle_value(
            bundle,
            "live_user_data_authenticated",
            False,
        ),
        "live_user_data_subscription_id": _campaign_bundle_value(
            bundle,
            "live_user_data_subscription_id",
            None,
        ),
        "live_user_data_event_count": _campaign_bundle_value(
            bundle,
            "live_user_data_event_count",
            0,
        ),
        "live_user_data_event_types": _campaign_bundle_value(
            bundle,
            "live_user_data_event_types",
            (),
        ),
    }


def _build_campaign_summary_delivery_and_bootstrap_fields(
    state: ShadowVpsServiceState,
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "telegram_alert_config_ref": _campaign_bundle_or_fallback(
            bundle, "telegram_alert_config_ref", state.last_telegram_alert_config_ref
        ),
        "telegram_alert_config_source": _campaign_bundle_or_fallback(
            bundle,
            "telegram_alert_config_source",
            state.last_telegram_alert_config_source or "not_configured",
        ),
        "telegram_alert_key_ref": _campaign_bundle_or_fallback(
            bundle, "telegram_alert_key_ref", state.last_telegram_alert_key_ref
        ),
        "telegram_alert_key_source": _campaign_bundle_or_fallback(
            bundle,
            "telegram_alert_key_source",
            state.last_telegram_alert_key_source or "not_configured",
        ),
        "execution_runtime_bootstrap_ref": _campaign_bundle_or_fallback(
            bundle,
            "execution_runtime_bootstrap_ref",
            state.last_execution_runtime_bootstrap_ref,
        ),
        "execution_runtime_bootstrap_status": _campaign_bundle_or_fallback(
            bundle,
            "execution_runtime_bootstrap_status",
            state.last_execution_runtime_bootstrap_status,
        ),
        "execution_runtime_bootstrap_source": _campaign_bundle_or_fallback(
            bundle,
            "execution_runtime_bootstrap_source",
            state.last_execution_runtime_bootstrap_source or "not_configured",
        ),
        "execution_runtime_gatekeeper_audit_ref": _campaign_bundle_or_fallback(
            bundle,
            "execution_runtime_gatekeeper_audit_ref",
            state.last_execution_runtime_gatekeeper_audit_ref,
        ),
        "execution_runtime_gatekeeper_audit_source": _campaign_bundle_or_fallback(
            bundle,
            "execution_runtime_gatekeeper_audit_source",
            state.last_execution_runtime_gatekeeper_audit_source
            or "not_configured",
        ),
        "execution_runtime_bootstrap_user_data_stream_enabled": _campaign_bundle_value(
            bundle, "execution_runtime_bootstrap_user_data_stream_enabled", False
        ),
        "execution_runtime_bootstrap_reconciliation_boot_executed": (
            _campaign_bundle_value(
                bundle,
                "execution_runtime_bootstrap_reconciliation_boot_executed",
                False,
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_trading_blocked": (
            _campaign_bundle_value(
                bundle,
                "execution_runtime_bootstrap_reconciliation_boot_trading_blocked",
                False,
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped": (
            _campaign_bundle_value(
                bundle,
                "execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped",
                False,
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_detail": (
            _campaign_bundle_value(
                bundle, "execution_runtime_bootstrap_reconciliation_boot_detail", ""
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_recovery_action": (
            _campaign_bundle_value(
                bundle,
                "execution_runtime_bootstrap_reconciliation_boot_recovery_action",
                "",
            )
        ),
        "execution_runtime_bootstrap_reconciliation_boot_divergence_count": (
            _campaign_bundle_value(
                bundle,
                "execution_runtime_bootstrap_reconciliation_boot_divergence_count",
                0,
            )
        ),
    }


def _build_campaign_summary_projection_fields(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_ref": _campaign_bundle_value(
            bundle, "execution_runtime_projection_ref", ""
        ),
        "execution_runtime_projection_source": _campaign_bundle_value(
            bundle, "execution_runtime_projection_source", "not_configured"
        ),
        "execution_runtime_projection_status": _campaign_bundle_value(
            bundle, "execution_runtime_projection_status", "not_configured"
        ),
        "execution_runtime_projection_ready": _campaign_bundle_value(
            bundle, "execution_runtime_projection_ready", False
        ),
        "execution_runtime_projection_consumer_count": _campaign_bundle_value(
            bundle, "execution_runtime_projection_consumer_count", 0
        ),
        "execution_runtime_projection_ready_consumer_count": _campaign_bundle_value(
            bundle, "execution_runtime_projection_ready_consumer_count", 0
        ),
        "execution_runtime_projection_partial_consumer_count": _campaign_bundle_value(
            bundle, "execution_runtime_projection_partial_consumer_count", 0
        ),
        "execution_runtime_projection_blocked_consumer_count": _campaign_bundle_value(
            bundle, "execution_runtime_projection_blocked_consumer_count", 0
        ),
        "execution_runtime_projection_bridge_status": _campaign_bundle_value(
            bundle, "execution_runtime_projection_bridge_status", "planned"
        ),
        "execution_runtime_projection_bridge_loaded": _campaign_bundle_value(
            bundle, "execution_runtime_projection_bridge_loaded", False
        ),
        "execution_runtime_projection_rate_limit_model_loaded": (
            _campaign_bundle_value(
                bundle, "execution_runtime_projection_rate_limit_model_loaded", False
            )
        ),
        "execution_runtime_projection_spread_guard_model_loaded": (
            _campaign_bundle_value(
                bundle, "execution_runtime_projection_spread_guard_model_loaded", False
            )
        ),
        "execution_runtime_projection_slippage_model_loaded": _campaign_bundle_value(
            bundle, "execution_runtime_projection_slippage_model_loaded", False
        ),
    }


def _build_campaign_summary_execution_fields(
    state: ShadowVpsServiceState,
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    fields: dict[str, object] = {}
    fields.update(_build_campaign_summary_delivery_and_bootstrap_fields(state, bundle))
    fields.update(_build_campaign_summary_projection_fields(bundle))
    return fields


def _build_campaign_summary_regime_fields(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "regime_lite_assessment_ref": _campaign_bundle_value(
            bundle,
            "regime_lite_assessment_ref",
            "",
        ),
        "regime_lite_assessment_source": _campaign_bundle_value(
            bundle,
            "regime_lite_assessment_source",
            "not_configured",
        ),
        "regime_lite_safing_recommendation_ref": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_recommendation_ref",
            "",
        ),
        "regime_lite_safing_recommendation_source": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_recommendation_source",
            "not_configured",
        ),
        "regime_lite_governance_status": _campaign_bundle_value(
            bundle,
            "regime_lite_governance_status",
            "not_configured",
        ),
        "regime_lite_state": _campaign_bundle_value(
            bundle,
            "regime_lite_state",
            "not_configured",
        ),
        "regime_lite_candidate_state": _campaign_bundle_value(
            bundle,
            "regime_lite_candidate_state",
            "not_configured",
        ),
        "regime_lite_state_changed": _campaign_bundle_value(
            bundle,
            "regime_lite_state_changed",
            False,
        ),
        "regime_lite_entries_blocked": _campaign_bundle_value(
            bundle,
            "regime_lite_entries_blocked",
            False,
        ),
        "regime_lite_sudden_event": _campaign_bundle_value(
            bundle,
            "regime_lite_sudden_event",
            False,
        ),
        "regime_lite_safing_severity": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_severity",
            "not_configured",
        ),
        "regime_lite_safing_should_block_new_entries": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_should_block_new_entries",
            False,
        ),
        "regime_lite_safing_should_exit_all": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_should_exit_all",
            False,
        ),
        "regime_lite_safing_recommended_operator_action": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_recommended_operator_action",
            "",
        ),
        "regime_lite_safing_operator_safing_request_action": (
            _campaign_bundle_value(
                bundle,
                "regime_lite_safing_operator_safing_request_action",
                "",
            )
        ),
        "regime_lite_safing_operator_safing_request_source_runtime_mode": (
            _campaign_bundle_value(
                bundle,
                "regime_lite_safing_operator_safing_request_source_runtime_mode",
                "",
            )
        ),
        "regime_lite_safing_reason_codes": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_reason_codes",
            (),
        ),
        "regime_lite_safing_detail": _campaign_bundle_value(
            bundle,
            "regime_lite_safing_detail",
            "",
        ),
    }


def _build_campaign_summary_info_stress_fields(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "info_stress_assessment_ref": _campaign_bundle_value(
            bundle, "info_stress_assessment_ref", ""
        ),
        "info_stress_assessment_source": _campaign_bundle_value(
            bundle, "info_stress_assessment_source", "not_configured"
        ),
        "info_stress_governance_status": _campaign_bundle_value(
            bundle, "info_stress_governance_status", "not_configured"
        ),
        "info_stress_level": _campaign_bundle_value(bundle, "info_stress_level", "not_configured"),
        "info_stress_alert_count": _campaign_bundle_value(bundle, "info_stress_alert_count", 0),
        "info_stress_entries_blocked": _campaign_bundle_value(bundle, "info_stress_entries_blocked", False),
        "info_stress_entries_blocked_until_ts": _campaign_bundle_value(
            bundle, "info_stress_entries_blocked_until_ts", 0
        ),
        "info_stress_reason_codes": _campaign_bundle_value(bundle, "info_stress_reason_codes", ()),
        "info_stress_detail": _campaign_bundle_value(bundle, "info_stress_detail", ""),
    }


def _build_campaign_summary_regime_and_info_fields(
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    fields: dict[str, object] = {}
    fields.update(_build_campaign_summary_regime_fields(bundle))
    fields.update(_build_campaign_summary_info_stress_fields(bundle))
    return fields


def _write_campaign_summary(
    *,
    service_dir: Path,
    state: ShadowVpsServiceState,
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> Path:
    summary_path = service_dir / "shadow_vps_service.campaign_summary.json"
    summary_fields: dict[str, object] = {}
    summary_fields.update(_build_campaign_summary_core_fields(state, bundle))
    summary_fields.update(_build_campaign_summary_live_capture_fields(bundle))
    summary_fields.update(_build_campaign_summary_execution_fields(state, bundle))
    summary_fields.update(_build_campaign_summary_regime_and_info_fields(bundle))
    summary = ShadowVpsCampaignSummary(**summary_fields)
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary_path


def _write_execution_telemetry_artifacts(
    *,
    service_dir: Path,
    session_date: str,
    last_run: dict,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    execution_time_sync_offsets_path: Path | None,
) -> tuple[Path, Path]:
    archive_path = service_dir / "shadow_vps_service_execution_telemetry.archive.json"
    artifact_path = service_dir / "shadow_vps_service_execution_telemetry.json"
    export_dir_ref = str(last_run.get("export_dir_ref", "")).strip()
    if not export_dir_ref:
        raise ValueError(
            "Shadow VPS execution telemetry requires export_dir_ref after successful orchestration"
        )
    resolved_time_sync_offsets_path: Path | None = None
    if execution_time_sync_offsets_path is not None and execution_time_sync_offsets_path.is_file():
        resolved_time_sync_offsets_path = execution_time_sync_offsets_path
    elif (
        live_capture_result is not None
        and live_capture_result.time_sync_offsets_path_ref
        and Path(live_capture_result.time_sync_offsets_path_ref).is_file()
    ):
        resolved_time_sync_offsets_path = Path(
            live_capture_result.time_sync_offsets_path_ref
        )
    existing_archive = load_local_lab_execution_telemetry_archive(archive_path)
    updated_archive, artifact = build_local_lab_execution_telemetry_artifact_for_export(
        export_dir=Path(export_dir_ref),
        session_date=session_date,
        websocket_stream_path=(
            Path(websocket_slot.stream_path_ref)
            if websocket_slot is not None and websocket_slot.stream_path_ref
            else None
        ),
        snapshot_batch_path=(
            Path(live_capture_result.snapshot_batch_path_ref)
            if live_capture_result is not None and live_capture_result.snapshot_batch_path_ref
            else None
        ),
        time_sync_offsets_path=resolved_time_sync_offsets_path,
        existing_archive=existing_archive,
    )
    atomic_write_json(
        archive_path,
        updated_archive.model_dump(mode="json"),
    )
    atomic_write_json(
        artifact_path,
        artifact.model_dump(mode="json"),
    )
    return archive_path, artifact_path


def _resolve_monitoring_artifact_paths(
    *,
    service_dir: Path,
    node_exporter_textfile_dir: Path | None,
    scrape_host: str,
) -> tuple[Path, Path | None, Path | None, Path | None]:
    recent_events_summary_path = service_dir / "shadow_vps_service_recent_events.json"
    node_exporter_textfile_path = (
        node_exporter_textfile_dir / "v53_shadow_vps_service.prom"
        if node_exporter_textfile_dir is not None
        else None
    )
    scrape_manifest_path = (
        service_dir / "shadow_vps_service_scrape_manifest.json"
        if scrape_host
        else None
    )
    prometheus_file_sd_path = (
        service_dir / "shadow_vps_service_prometheus_file_sd.json"
        if scrape_host
        else None
    )
    return (
        recent_events_summary_path,
        node_exporter_textfile_path,
        scrape_manifest_path,
        prometheus_file_sd_path,
    )


def _write_monitoring_artifacts(
    *,
    service_dir: Path,
    store: ShadowVpsServiceStore,
    sampler: ProcessMetricsSampler,
    node_exporter_textfile_dir: Path | None = None,
    scrape_host: str = "",
    vps_id: str = "",
    node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http",
    node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps",
) -> tuple[Path, Path, Path, Path, Path | None, Path | None, Path | None]:
    state = store.state
    timestamp_ms = int(time.time() * 1000.0)
    (
        recent_events_summary_path,
        node_exporter_textfile_path,
        scrape_manifest_path,
        prometheus_file_sd_path,
    ) = _resolve_monitoring_artifact_paths(
        service_dir=service_dir,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host,
    )
    payload = build_shadow_vps_service_monitoring_payload(
        timestamp_ms=timestamp_ms,
        state=state,
        process=sampler.sample(),
        disk=sample_disk_usage(service_dir),
        campaign_summary=_read_campaign_summary(state.last_campaign_summary_ref),
        runtime_evidence_bundle=_read_runtime_evidence_bundle(
            state.last_runtime_evidence_bundle_ref
        ),
        state_path=str(store.state_path.resolve()),
        events_path=str(store.events_path.resolve()),
        recent_events_summary_ref=str(recent_events_summary_path.resolve()),
        node_exporter_textfile_ref=(
            str(node_exporter_textfile_path.resolve())
            if node_exporter_textfile_path is not None
            else ""
        ),
        scrape_manifest_ref=(
            str(scrape_manifest_path.resolve()) if scrape_manifest_path is not None else ""
        ),
        prometheus_file_sd_ref=(
            str(prometheus_file_sd_path.resolve()) if prometheus_file_sd_path is not None else ""
        ),
    )
    backend_payload_path = service_dir / "shadow_vps_service_monitoring_backend_payload.json"
    observability_export_path = (
        service_dir / "shadow_vps_service_observability_export.json"
    )
    observability_text_path = service_dir / "shadow_vps_service_observability.prom"
    atomic_write_json(
        backend_payload_path,
        payload.model_dump(mode="json"),
    )
    observability_export = build_shadow_vps_service_observability_export(payload)
    atomic_write_json(
        observability_export_path,
        observability_export.model_dump(mode="json"),
    )
    write_observability_text_payload(
        observability_export,
        observability_text_path,
    )
    if node_exporter_textfile_dir is not None:
        write_node_exporter_textfile_payload(
            observability_export,
            node_exporter_textfile_dir,
            filename="v53_shadow_vps_service.prom",
        )
    atomic_write_json(
        recent_events_summary_path,
        build_shadow_vps_service_recent_events_summary(
            store.events_path,
            max_events=20,
            timestamp_ms=timestamp_ms,
        ).model_dump(mode="json"),
    )
    if scrape_manifest_path is not None and prometheus_file_sd_path is not None:
        scrape_manifest = build_shadow_vps_service_scrape_manifest(
            payload,
            scrape_host=scrape_host,
            vps_id=vps_id or scrape_host,
            node_exporter_port=node_exporter_port,
            node_exporter_scheme=node_exporter_scheme,
            node_exporter_metrics_path=node_exporter_metrics_path,
            prometheus_job_name=prometheus_job_name,
            monitoring_backend_payload_ref=str(backend_payload_path.resolve()),
            observability_export_ref=str(observability_export_path.resolve()),
        )
        atomic_write_json(
            scrape_manifest_path,
            scrape_manifest.model_dump(mode="json"),
        )
        atomic_write_json(
            prometheus_file_sd_path,
            [
                entry.model_dump(mode="json")
                for entry in build_shadow_vps_service_prometheus_file_sd(scrape_manifest)
            ],
        )
    return (
        backend_payload_path,
        observability_export_path,
        observability_text_path,
        recent_events_summary_path,
        node_exporter_textfile_path.resolve()
        if node_exporter_textfile_path is not None
        else None,
        scrape_manifest_path.resolve() if scrape_manifest_path is not None else None,
        prometheus_file_sd_path.resolve()
        if prometheus_file_sd_path is not None
        else None,
    )


def _write_service_monitoring(context: ShadowVpsServiceRuntimeContext) -> None:
    _write_monitoring_artifacts(
        service_dir=context.service_dir,
        store=context.store,
        sampler=context.process_metrics_sampler,
        node_exporter_textfile_dir=context.monitoring.node_exporter_textfile_dir,
        scrape_host=context.monitoring.scrape_host,
        vps_id=context.monitoring.vps_id,
        node_exporter_port=context.monitoring.node_exporter_port,
        node_exporter_scheme=context.monitoring.node_exporter_scheme,
        node_exporter_metrics_path=context.monitoring.node_exporter_metrics_path,
        prometheus_job_name=context.monitoring.prometheus_job_name,
    )


def _resolve_shadow_vps_service_runtime_dirs(
    *,
    service_dir: Path,
    orchestrator_output_dir: Path | None,
    shadow_output_dir: Path | None,
    live_captures_root: Path | None,
    auto_snapshots_root: Path | None,
    auto_exports_root: Path | None,
) -> tuple[Path, Path, Path, Path, Path]:
    service_dir.mkdir(parents=True, exist_ok=True)
    return (
        orchestrator_output_dir or (service_dir / "orchestrator"),
        shadow_output_dir or (service_dir / "shadow_session"),
        live_captures_root or (service_dir / "live_captures"),
        auto_snapshots_root or (service_dir / "auto_snapshots"),
        auto_exports_root or (service_dir / "auto_exports"),
    )


def _build_shadow_vps_service_runtime_context(
    *,
    service_dir: Path,
    orchestrator_output_dir: Path | None, shadow_output_dir: Path | None,
    exports_root: Path | None, raw_inputs_root: Path | None,
    websocket_streams_root: Path | None, live_websocket_config_path: Path | None,
    live_captures_root: Path | None, auto_snapshots_root: Path | None,
    auto_exports_root: Path | None, execution_time_sync_offsets_path: Path | None,
    execution_runtime_bootstrap_enabled: bool,
    execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None,
    telegram_alert_config_path: Path | None, telegram_alert_key_path: Path | None,
    telegram_post_func: TelegramPostFunc | None,
    node_exporter_textfile_dir: Path | None, scrape_host: str, vps_id: str,
    node_exporter_port: int, node_exporter_scheme: str, node_exporter_metrics_path: str, prometheus_job_name: str,
) -> ShadowVpsServiceRuntimeContext:
    (
        resolved_orchestrator_output_dir,
        resolved_shadow_output_dir,
        resolved_live_captures_root,
        resolved_auto_snapshots_root,
        resolved_auto_exports_root,
    ) = _resolve_shadow_vps_service_runtime_dirs(
        service_dir=service_dir,
        orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir,
        live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root,
        auto_exports_root=auto_exports_root,
    )
    startup_live_config = (
        _read_live_websocket_config(live_websocket_config_path)
        if live_websocket_config_path is not None
        else None
    )
    bootstrap_enabled, bootstrap_source = _resolve_execution_runtime_bootstrap_enabled(
        explicit_enabled=execution_runtime_bootstrap_enabled,
        live_config=startup_live_config,
    )
    gatekeeper_audit_path, gatekeeper_audit_source = (
        _resolve_execution_runtime_gatekeeper_audit_path(
            explicit_path=execution_runtime_gatekeeper_audit_path,
            live_websocket_config_path=live_websocket_config_path,
            live_config=startup_live_config,
        )
    )
    projection_path, projection_source = _resolve_execution_runtime_projection_path(
        explicit_path=execution_runtime_projection_path,
        live_websocket_config_path=live_websocket_config_path,
        live_config=startup_live_config,
    )
    resolved_telegram_alert_config_path, resolved_telegram_alert_config_source = (
        _resolve_telegram_alert_config_path(
            explicit_path=telegram_alert_config_path,
            live_websocket_config_path=live_websocket_config_path,
            live_config=startup_live_config,
        )
    )
    resolved_telegram_alert_key_path, resolved_telegram_alert_key_source = (
        _resolve_telegram_alert_key_path(
            explicit_path=telegram_alert_key_path,
            live_websocket_config_path=live_websocket_config_path,
            live_config=startup_live_config,
        )
    )
    telegram_alerter = (
        TelegramAlerter(
            load_telegram_alerter_config_from_file(
                resolved_telegram_alert_config_path,
                key_path=resolved_telegram_alert_key_path,
            ),
            post_func=telegram_post_func,
        )
        if resolved_telegram_alert_config_path is not None
        else None
    )
    bootstrap_summary, bootstrap_summary_path = _write_execution_runtime_bootstrap_summary(
        service_dir=service_dir,
        bootstrap_enabled=bootstrap_enabled,
        bootstrap_source=bootstrap_source,
        live_config=startup_live_config,
        execution_runtime_projection_path=projection_path,
        execution_runtime_projection_source=projection_source,
        gatekeeper_audit_path=gatekeeper_audit_path,
        gatekeeper_audit_source=gatekeeper_audit_source,
    )
    return _create_shadow_vps_service_runtime_context(
        service_dir=service_dir,
        resolved_orchestrator_output_dir=resolved_orchestrator_output_dir,
        resolved_shadow_output_dir=resolved_shadow_output_dir,
        resolved_live_captures_root=resolved_live_captures_root,
        resolved_auto_snapshots_root=resolved_auto_snapshots_root,
        resolved_auto_exports_root=resolved_auto_exports_root,
        exports_root=exports_root,
        raw_inputs_root=raw_inputs_root,
        websocket_streams_root=websocket_streams_root,
        live_websocket_config_path=live_websocket_config_path,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        resolved_telegram_alert_config_path=resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source=resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path=resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source=resolved_telegram_alert_key_source,
        bootstrap_summary=bootstrap_summary,
        bootstrap_summary_path=bootstrap_summary_path,
        telegram_alerter=telegram_alerter,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host,
        vps_id=vps_id,
        node_exporter_port=node_exporter_port,
        node_exporter_scheme=node_exporter_scheme,
        node_exporter_metrics_path=node_exporter_metrics_path,
        prometheus_job_name=prometheus_job_name,
    )


def _create_shadow_vps_service_runtime_context(
    *,
    service_dir: Path,
    resolved_orchestrator_output_dir: Path,
    resolved_shadow_output_dir: Path,
    resolved_live_captures_root: Path,
    resolved_auto_snapshots_root: Path,
    resolved_auto_exports_root: Path,
    exports_root: Path | None,
    raw_inputs_root: Path | None,
    websocket_streams_root: Path | None,
    live_websocket_config_path: Path | None,
    execution_time_sync_offsets_path: Path | None,
    execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None,
    resolved_telegram_alert_config_path: Path | None,
    resolved_telegram_alert_config_source: str,
    resolved_telegram_alert_key_path: Path | None,
    resolved_telegram_alert_key_source: str,
    bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary,
    bootstrap_summary_path: Path | None,
    telegram_alerter: TelegramAlerter | None,
    node_exporter_textfile_dir: Path | None,
    scrape_host: str,
    vps_id: str,
    node_exporter_port: int,
    node_exporter_scheme: str,
    node_exporter_metrics_path: str,
    prometheus_job_name: str,
) -> ShadowVpsServiceRuntimeContext:
    return ShadowVpsServiceRuntimeContext(
        service_dir=service_dir,
        resolved_orchestrator_output_dir=resolved_orchestrator_output_dir,
        resolved_shadow_output_dir=resolved_shadow_output_dir,
        resolved_live_captures_root=resolved_live_captures_root,
        resolved_auto_snapshots_root=resolved_auto_snapshots_root,
        resolved_auto_exports_root=resolved_auto_exports_root,
        exports_root=exports_root,
        raw_inputs_root=raw_inputs_root,
        websocket_streams_root=websocket_streams_root,
        live_websocket_config_path=live_websocket_config_path,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        resolved_telegram_alert_config_path=resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source=resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path=resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source=resolved_telegram_alert_key_source,
        bootstrap_summary=bootstrap_summary,
        bootstrap_summary_path=bootstrap_summary_path,
        store=ShadowVpsServiceStore(service_dir),
        process_metrics_sampler=ProcessMetricsSampler(),
        telegram_alerter=telegram_alerter,
        launcher=_load_daily_orchestrator_module(),
        monitoring=ShadowVpsServiceMonitoringConfig(
            node_exporter_textfile_dir=node_exporter_textfile_dir,
            scrape_host=scrape_host,
            vps_id=vps_id,
            node_exporter_port=node_exporter_port,
            node_exporter_scheme=node_exporter_scheme,
            node_exporter_metrics_path=node_exporter_metrics_path,
            prometheus_job_name=prometheus_job_name,
        ),
    )


def _apply_shadow_vps_startup_state(context: ShadowVpsServiceRuntimeContext) -> None:
    state = context.store.state
    state.resumed = state.loop_count > 0
    if state.started_at is None:
        state.started_at = time.time()
    state.service_status = ShadowVpsServiceStatus.RUNNING
    state.last_error = ""
    state.last_telegram_alert_delivery_status = "not_configured"
    state.last_telegram_alert_delivery_event_type = ""
    state.last_telegram_alert_delivery_error = ""
    state.last_telegram_alert_config_ref = (
        str(context.resolved_telegram_alert_config_path.resolve())
        if context.resolved_telegram_alert_config_path is not None
        else ""
    )
    state.last_telegram_alert_config_source = (
        context.resolved_telegram_alert_config_source
        if context.resolved_telegram_alert_config_path is not None
        else "not_configured"
    )
    state.last_telegram_alert_key_ref = (
        str(context.resolved_telegram_alert_key_path.resolve())
        if context.resolved_telegram_alert_key_path is not None
        else ""
    )
    state.last_telegram_alert_key_source = (
        context.resolved_telegram_alert_key_source
        if context.resolved_telegram_alert_key_path is not None
        else "not_configured"
    )
    state.last_execution_runtime_bootstrap_ref = (
        str(context.bootstrap_summary_path.resolve())
        if context.bootstrap_summary_path is not None
        else ""
    )
    state.last_execution_runtime_bootstrap_status = context.bootstrap_summary.status
    state.last_execution_runtime_bootstrap_source = (
        context.bootstrap_summary.source
        if context.bootstrap_summary.status != "not_configured"
        else ""
    )
    state.last_execution_runtime_gatekeeper_audit_ref = (
        context.bootstrap_summary.gatekeeper_audit_ref
    )
    state.last_execution_runtime_gatekeeper_audit_source = (
        context.bootstrap_summary.gatekeeper_audit_source
        if context.bootstrap_summary.gatekeeper_audit_ref
        else ""
    )
    context.store.persist()


def _emit_shadow_vps_startup_events(context: ShadowVpsServiceRuntimeContext) -> None:
    state = context.store.state
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="service_started",
            message=(
                "Shadow VPS service resumed"
                if state.resumed
                else "Shadow VPS service started"
            ),
        ),
    )
    if context.bootstrap_summary.status == "ready":
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="execution_runtime_bootstrap_ready",
                message=(
                    "Bounded execution runtime bootstrap completed: "
                    f"{context.bootstrap_summary.reconciliation_boot_detail or 'ready'}"
                ),
            ),
        )
    elif context.bootstrap_summary.status == "failed":
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="execution_runtime_bootstrap_failed",
                message=(
                    "Bounded execution runtime bootstrap failed: "
                    f"{context.bootstrap_summary.error}"
                ),
                error=context.bootstrap_summary.error,
            ),
        )


def _initialize_shadow_vps_service_runtime(
    *,
    service_dir: Path,
    orchestrator_output_dir: Path | None,
    shadow_output_dir: Path | None,
    exports_root: Path | None,
    raw_inputs_root: Path | None,
    websocket_streams_root: Path | None,
    live_websocket_config_path: Path | None,
    live_captures_root: Path | None,
    auto_snapshots_root: Path | None,
    auto_exports_root: Path | None,
    execution_time_sync_offsets_path: Path | None,
    execution_runtime_bootstrap_enabled: bool,
    execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None,
    telegram_alert_config_path: Path | None,
    telegram_alert_key_path: Path | None,
    telegram_post_func: TelegramPostFunc | None,
    node_exporter_textfile_dir: Path | None,
    scrape_host: str,
    vps_id: str,
    node_exporter_port: int,
    node_exporter_scheme: str,
    node_exporter_metrics_path: str,
    prometheus_job_name: str,
) -> ShadowVpsServiceRuntimeContext:
    context = _build_shadow_vps_service_runtime_context(
        service_dir=service_dir,
        orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir,
        exports_root=exports_root,
        raw_inputs_root=raw_inputs_root,
        websocket_streams_root=websocket_streams_root,
        live_websocket_config_path=live_websocket_config_path,
        live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root,
        auto_exports_root=auto_exports_root,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        telegram_post_func=telegram_post_func,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host,
        vps_id=vps_id,
        node_exporter_port=node_exporter_port,
        node_exporter_scheme=node_exporter_scheme,
        node_exporter_metrics_path=node_exporter_metrics_path,
        prometheus_job_name=prometheus_job_name,
    )
    _apply_shadow_vps_startup_state(context)
    _emit_shadow_vps_startup_events(context)
    _write_service_monitoring(context)
    return context


def _resolve_shadow_vps_cycle_selection(
    context: ShadowVpsServiceRuntimeContext,
) -> ShadowVpsCycleSelection:
    daily_orchestrator = ShadowDailyOrchestrator(context.resolved_orchestrator_output_dir)
    completed_session_dates = set(daily_orchestrator.completed_session_dates())
    raw_slot = (
        _select_next_raw_input_slot(context.raw_inputs_root, daily_orchestrator)
        if context.raw_inputs_root is not None
        else None
    )
    websocket_slot = (
        _select_next_websocket_input_slot(
            context.websocket_streams_root,
            daily_orchestrator,
        )
        if context.websocket_streams_root is not None
        else None
    )
    live_config = (
        _read_live_websocket_config(context.live_websocket_config_path)
        if context.live_websocket_config_path is not None
        else None
    )
    projection_path, projection_source = _resolve_execution_runtime_projection_path(
        explicit_path=context.execution_runtime_projection_path,
        live_websocket_config_path=context.live_websocket_config_path,
        live_config=live_config,
    )
    regime_assessment_path, regime_assessment_source = _resolve_regime_lite_assessment_path(
        explicit_path=context.regime_lite_assessment_path,
        live_websocket_config_path=context.live_websocket_config_path,
        live_config=live_config,
    )
    regime_safing_path, regime_safing_source = (
        _resolve_regime_lite_safing_recommendation_path(
            explicit_path=context.regime_lite_safing_recommendation_path,
            live_websocket_config_path=context.live_websocket_config_path,
            live_config=live_config,
        )
    )
    info_stress_path, info_stress_source = _resolve_info_stress_assessment_path(
        explicit_path=context.info_stress_assessment_path,
        live_websocket_config_path=context.live_websocket_config_path,
        live_config=live_config,
    )
    live_session_date = (
        live_config.session_date_override or date.today().isoformat()
        if live_config is not None
        else ""
    )
    auto_export_dir: Path | None = None
    auto_snapshot_dir: Path | None = None
    live_capture_dir: Path | None = None
    if raw_slot is not None:
        auto_export_dir = _ensure_auto_export_from_raw_slot(
            raw_slot,
            auto_exports_root=context.resolved_auto_exports_root,
        )
        _pin_auto_export_session_date(auto_export_dir, raw_slot.session_date)
        next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
    elif websocket_slot is not None:
        auto_snapshot_dir, auto_export_dir = _ensure_auto_export_from_websocket_slot(
            websocket_slot,
            auto_snapshots_root=context.resolved_auto_snapshots_root,
            auto_exports_root=context.resolved_auto_exports_root,
        )
        _pin_auto_export_session_date(auto_export_dir, websocket_slot.session_date)
        next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
    elif live_config is not None:
        if live_session_date in completed_session_dates:
            next_slot = None
        else:
            live_capture_dir, auto_export_dir = _ensure_auto_export_from_live_websocket(
                live_config,
                live_captures_root=context.resolved_live_captures_root,
                auto_exports_root=context.resolved_auto_exports_root,
            )
            _pin_auto_export_session_date(auto_export_dir, live_session_date)
            next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
    else:
        next_slot = (
            daily_orchestrator.select_next_slot(context.exports_root)
            if context.exports_root is not None
            else daily_orchestrator.next_demo_slot()
        )
    return ShadowVpsCycleSelection(
        raw_slot=raw_slot,
        websocket_slot=websocket_slot,
        next_slot=next_slot,
        live_capture_dir=live_capture_dir,
        auto_snapshot_dir=auto_snapshot_dir,
        auto_export_dir=auto_export_dir,
        resolved_execution_runtime_projection_path=projection_path,
        resolved_execution_runtime_projection_source=projection_source,
        resolved_regime_lite_assessment_path=regime_assessment_path,
        resolved_regime_lite_assessment_source=regime_assessment_source,
        resolved_regime_lite_safing_recommendation_path=regime_safing_path,
        resolved_regime_lite_safing_recommendation_source=regime_safing_source,
        resolved_info_stress_assessment_path=info_stress_path,
        resolved_info_stress_assessment_source=info_stress_source,
    )


def _record_shadow_vps_idle_cycle(context: ShadowVpsServiceRuntimeContext) -> None:
    state = context.store.state
    state.idle_count += 1
    state.service_status = ShadowVpsServiceStatus.IDLE
    context.store.persist()
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="idle_no_pending_export",
            message="No pending governed Shadow export directory was found.",
        ),
    )
    _write_service_monitoring(context)


def _prepare_shadow_vps_selected_cycle(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
) -> ShadowLiveWebSocketCaptureResult | None:
    if selection.next_slot is None:
        raise ValueError("selected cycle requires a governed slot")
    state = context.store.state
    state.last_selected_session_date = selection.next_slot.session_date
    state.last_raw_input_dir_ref = (
        selection.raw_slot.raw_input_dir_ref if selection.raw_slot is not None else ""
    )
    state.last_websocket_input_dir_ref = (
        selection.websocket_slot.websocket_input_dir_ref
        if selection.websocket_slot is not None
        else ""
    )
    live_capture_result = _read_live_capture_result(selection.live_capture_dir)
    state.last_live_capture_dir_ref = (
        live_capture_result.live_capture_dir_ref if live_capture_result is not None else ""
    )
    state.last_live_capture_snapshot_batch_ref = (
        live_capture_result.snapshot_batch_path_ref if live_capture_result is not None else ""
    )
    state.last_live_capture_summary_ref = (
        live_capture_result.summary_path_ref if live_capture_result is not None else ""
    )
    state.last_live_capture_time_sync_offsets_ref = (
        live_capture_result.time_sync_offsets_path_ref
        if live_capture_result is not None
        else ""
    )
    state.last_live_user_data_summary_ref = (
        live_capture_result.user_data_summary_path_ref if live_capture_result is not None else ""
    )
    state.last_auto_snapshot_dir_ref = (
        str(selection.auto_snapshot_dir.resolve())
        if selection.auto_snapshot_dir is not None
        else ""
    )
    state.last_auto_export_dir_ref = (
        str(selection.auto_export_dir.resolve())
        if selection.auto_export_dir is not None
        else ""
    )
    context.store.persist()
    if selection.raw_slot is not None and selection.auto_export_dir is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from raw VPS input.",
                session_date=selection.raw_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )
    if selection.websocket_slot is not None and selection.auto_snapshot_dir is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_snapshot_completed",
                message="Historical snapshot batch was auto-generated from injected websocket stream.",
                session_date=selection.websocket_slot.session_date,
                export_dir_ref=str(selection.auto_snapshot_dir.resolve()),
            ),
        )
    if selection.websocket_slot is not None and selection.auto_export_dir is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from injected websocket stream.",
                session_date=selection.websocket_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )
    if selection.live_capture_dir is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="live_capture_completed",
                message="Native live_websocket capture completed.",
                session_date=selection.next_slot.session_date,
                export_dir_ref=str(selection.live_capture_dir.resolve()),
                live_capture_summary_ref=(
                    live_capture_result.summary_path_ref if live_capture_result is not None else ""
                ),
                emitted_message_count=(
                    live_capture_result.emitted_message_count if live_capture_result is not None else None
                ),
                accepted_message_count=(
                    live_capture_result.accepted_message_count if live_capture_result is not None else None
                ),
                ignored_message_count=(
                    live_capture_result.ignored_message_count if live_capture_result is not None else None
                ),
                rejected_message_count=(
                    live_capture_result.rejected_message_count if live_capture_result is not None else None
                ),
                pair_scope=live_capture_result.pair_scope if live_capture_result is not None else (),
                event_types=live_capture_result.event_types if live_capture_result is not None else (),
            ),
        )
    if selection.live_capture_dir is not None and selection.auto_export_dir is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from native live_websocket capture.",
                session_date=selection.next_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )
    return live_capture_result


def _augment_last_run_with_operated_metadata(
    *,
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    last_run: dict,
) -> None:
    last_run["execution_runtime_projection_source"] = (
        selection.resolved_execution_runtime_projection_source
        if selection.resolved_execution_runtime_projection_path is not None
        else "not_configured"
    )
    last_run["regime_lite_assessment_ref"] = (
        str(selection.resolved_regime_lite_assessment_path.resolve())
        if selection.resolved_regime_lite_assessment_path is not None
        else ""
    )
    last_run["regime_lite_assessment_source"] = (
        selection.resolved_regime_lite_assessment_source
        if selection.resolved_regime_lite_assessment_path is not None
        else "not_configured"
    )
    last_run["regime_lite_safing_recommendation_ref"] = (
        str(selection.resolved_regime_lite_safing_recommendation_path.resolve())
        if selection.resolved_regime_lite_safing_recommendation_path is not None
        else ""
    )
    last_run["regime_lite_safing_recommendation_source"] = (
        selection.resolved_regime_lite_safing_recommendation_source
        if selection.resolved_regime_lite_safing_recommendation_path is not None
        else "not_configured"
    )
    last_run["info_stress_assessment_ref"] = (
        str(selection.resolved_info_stress_assessment_path.resolve())
        if selection.resolved_info_stress_assessment_path is not None
        else ""
    )
    last_run["info_stress_assessment_source"] = (
        selection.resolved_info_stress_assessment_source
        if selection.resolved_info_stress_assessment_path is not None
        else "not_configured"
    )
    last_run["telegram_alert_config_ref"] = (
        str(context.resolved_telegram_alert_config_path.resolve())
        if context.resolved_telegram_alert_config_path is not None
        else ""
    )
    last_run["telegram_alert_config_source"] = (
        context.resolved_telegram_alert_config_source
        if context.resolved_telegram_alert_config_path is not None
        else "not_configured"
    )
    last_run["telegram_alert_key_ref"] = (
        str(context.resolved_telegram_alert_key_path.resolve())
        if context.resolved_telegram_alert_key_path is not None
        else ""
    )
    last_run["telegram_alert_key_source"] = (
        context.resolved_telegram_alert_key_source
        if context.resolved_telegram_alert_key_path is not None
        else "not_configured"
    )
    last_run["execution_runtime_bootstrap_ref"] = (
        str(context.bootstrap_summary_path.resolve())
        if context.bootstrap_summary_path is not None
        else ""
    )
    last_run["execution_runtime_bootstrap_status"] = context.bootstrap_summary.status
    last_run["execution_runtime_bootstrap_source"] = (
        context.bootstrap_summary.source
        if context.bootstrap_summary.status != "not_configured"
        else "not_configured"
    )
    last_run["execution_runtime_gatekeeper_audit_ref"] = (
        context.bootstrap_summary.gatekeeper_audit_ref
    )
    last_run["execution_runtime_gatekeeper_audit_source"] = (
        context.bootstrap_summary.gatekeeper_audit_source
        if context.bootstrap_summary.gatekeeper_audit_ref
        else "not_configured"
    )
    last_run["execution_runtime_bootstrap_user_data_stream_enabled"] = bool(
        context.bootstrap_summary.user_data_stream_enabled
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_executed"] = bool(
        context.bootstrap_summary.reconciliation_boot_executed
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_trading_blocked"] = bool(
        context.bootstrap_summary.reconciliation_boot_trading_blocked
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped"] = bool(
        context.bootstrap_summary.reconciliation_boot_circuit_breaker_tripped
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_detail"] = (
        context.bootstrap_summary.reconciliation_boot_detail
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_recovery_action"] = (
        context.bootstrap_summary.reconciliation_boot_recovery_action
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_divergence_count"] = int(
        context.bootstrap_summary.reconciliation_boot_divergence_count
    )
    if not str(last_run.get("export_dir_ref", "")).strip() and selection.auto_export_dir is not None:
        last_run["export_dir_ref"] = str(selection.auto_export_dir.resolve())


def _run_shadow_vps_daily_orchestrator(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
) -> dict:
    if selection.next_slot is None:
        raise ValueError("selected cycle requires a governed slot")
    exit_code = context.launcher.orchestrate_one_shadow_day(
        context.resolved_orchestrator_output_dir,
        shadow_output_dir=context.resolved_shadow_output_dir,
        export_dir=Path(selection.next_slot.export_dir_ref)
        if selection.next_slot.export_dir_ref
        else None,
        session_date=selection.next_slot.session_date,
        execution_runtime_projection_path=selection.resolved_execution_runtime_projection_path,
        regime_lite_assessment_path=selection.resolved_regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=(
            selection.resolved_regime_lite_safing_recommendation_path
        ),
        info_stress_assessment_path=selection.resolved_info_stress_assessment_path,
    )
    if exit_code != 0:
        raise RuntimeError(
            f"Daily Shadow orchestrator returned non-zero exit code {exit_code}"
        )
    last_run = _read_last_run(context.resolved_orchestrator_output_dir)
    _augment_last_run_with_operated_metadata(
        context=context,
        selection=selection,
        last_run=last_run,
    )
    return last_run


def _apply_last_run_to_shadow_vps_state(
    context: ShadowVpsServiceRuntimeContext,
    last_run: dict,
    runtime_evidence_bundle_path: Path,
) -> None:
    state = context.store.state
    state.last_export_dir_ref = _last_run_str(last_run, "export_dir_ref")
    state.last_local_replay_evidence_ref = _last_run_str(
        last_run, "local_replay_evidence_ref"
    )
    state.last_shadow_runtime_evidence_ref = _last_run_str(
        last_run, "shadow_runtime_evidence_ref"
    )
    state.last_runtime_evidence_bundle_ref = str(runtime_evidence_bundle_path.resolve())
    state.last_execution_runtime_projection_ref = _last_run_str(
        last_run, "execution_runtime_projection_ref"
    )
    state.last_execution_runtime_projection_source = _last_run_str(
        last_run, "execution_runtime_projection_source", "not_configured"
    )
    state.last_regime_lite_assessment_ref = _last_run_str(
        last_run, "regime_lite_assessment_ref"
    )
    state.last_regime_lite_assessment_source = _last_run_str(
        last_run, "regime_lite_assessment_source", "not_configured"
    )
    state.last_regime_lite_safing_recommendation_ref = _last_run_str(
        last_run, "regime_lite_safing_recommendation_ref"
    )
    state.last_regime_lite_safing_recommendation_source = _last_run_str(
        last_run,
        "regime_lite_safing_recommendation_source",
        "not_configured",
    )
    state.last_info_stress_assessment_ref = _last_run_str(
        last_run, "info_stress_assessment_ref"
    )
    state.last_info_stress_assessment_source = _last_run_str(
        last_run, "info_stress_assessment_source", "not_configured"
    )
    state.last_telegram_alert_config_ref = _last_run_str(
        last_run, "telegram_alert_config_ref"
    )
    state.last_telegram_alert_config_source = _last_run_str(
        last_run, "telegram_alert_config_source", "not_configured"
    )
    state.last_telegram_alert_key_ref = _last_run_str(last_run, "telegram_alert_key_ref")
    state.last_telegram_alert_key_source = _last_run_str(
        last_run, "telegram_alert_key_source", "not_configured"
    )
    state.last_execution_runtime_bootstrap_ref = _last_run_str(
        last_run, "execution_runtime_bootstrap_ref"
    )
    state.last_execution_runtime_bootstrap_status = _last_run_str(
        last_run, "execution_runtime_bootstrap_status", "not_configured"
    )
    state.last_execution_runtime_bootstrap_source = _last_run_str(
        last_run, "execution_runtime_bootstrap_source", "not_configured"
    )
    state.last_execution_runtime_gatekeeper_audit_ref = _last_run_str(
        last_run, "execution_runtime_gatekeeper_audit_ref"
    )
    state.last_execution_runtime_gatekeeper_audit_source = _last_run_str(
        last_run, "execution_runtime_gatekeeper_audit_source", "not_configured"
    )
    state.last_orchestrator_state_ref = last_run["state_path"]
    state.last_shadow_report_ref = last_run["shadow_report_ref"]
    state.last_shadow_session_summary_ref = last_run["shadow_session_summary_ref"]
    state.last_shadow_session_registry_ref = last_run["shadow_session_registry_ref"]
    context.store.persist()


def _write_shadow_vps_cycle_execution_telemetry(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    last_run: dict,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> tuple[str, Path | None]:
    if str(last_run.get("export_dir_ref", "")).strip():
        try:
            _, artifact_path = _write_execution_telemetry_artifacts(
                service_dir=context.service_dir,
                session_date=last_run["session_date"],
                last_run=last_run,
                websocket_slot=selection.websocket_slot,
                live_capture_result=live_capture_result,
                execution_time_sync_offsets_path=context.execution_time_sync_offsets_path,
            )
        except Exception as exc:
            context.store.state.last_execution_telemetry_status = "failed"
            context.store.persist()
            raise RuntimeError(
                "Shadow VPS execution telemetry artifact write failed"
            ) from exc
        return "written", artifact_path
    return "skipped", None


def _complete_shadow_vps_successful_cycle(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    last_run: dict,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    execution_telemetry_status: str,
    execution_telemetry_artifact_path: Path | None,
) -> None:
    if selection.next_slot is None:
        raise ValueError("selected cycle requires a governed slot")
    state = context.store.state
    state.success_count += 1
    state.service_status = ShadowVpsServiceStatus.RUNNING
    state.last_completed_session_date = last_run["session_date"]
    state.last_live_capture_dir_ref = (
        str(selection.live_capture_dir.resolve())
        if selection.live_capture_dir is not None
        else state.last_live_capture_dir_ref
    )
    state.last_auto_snapshot_dir_ref = (
        str(selection.auto_snapshot_dir.resolve())
        if selection.auto_snapshot_dir is not None
        else state.last_auto_snapshot_dir_ref
    )
    state.last_auto_export_dir_ref = (
        str(selection.auto_export_dir.resolve())
        if selection.auto_export_dir is not None
        else state.last_auto_export_dir_ref
    )
    state.last_execution_telemetry_ref = (
        str(execution_telemetry_artifact_path.resolve())
        if execution_telemetry_artifact_path is not None
        else ""
    )
    state.last_execution_telemetry_status = execution_telemetry_status
    state.last_error = ""
    bundle = _read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
    campaign_summary_path = _write_campaign_summary(
        service_dir=context.service_dir,
        state=state,
        bundle=bundle,
    )
    state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
    context.store.persist()
    _write_service_monitoring(context)
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="runtime_evidence_bundle_written",
            message="Durable Build-11 runtime evidence bundle was written.",
            session_date=last_run["session_date"],
            export_dir_ref=state.last_runtime_evidence_bundle_ref,
        ),
    )
    if execution_telemetry_artifact_path is not None:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="execution_telemetry_written",
                message="Durable Local IA Lab execution telemetry sidecar was written.",
                session_date=last_run["session_date"],
                export_dir_ref=str(execution_telemetry_artifact_path.resolve()),
            ),
        )
    else:
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="execution_telemetry_skipped",
                message=(
                    "Local IA Lab execution telemetry sidecar was skipped "
                    "because no governed export_dir_ref was available for this run."
                ),
                session_date=last_run["session_date"],
            ),
        )
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="shadow_day_completed",
            message="Governed Shadow day completed.",
            session_date=last_run["session_date"],
            export_dir_ref=_last_run_str(last_run, "export_dir_ref"),
            accepted=bool(last_run["accepted"]),
            consecutive_days=int(last_run["consecutive_days"]),
            remaining_days=int(last_run["remaining_days"]),
        ),
    )


def _record_shadow_vps_failed_cycle(
    context: ShadowVpsServiceRuntimeContext,
    exc: Exception,
) -> None:
    state = context.store.state
    state.failure_count += 1
    state.service_status = ShadowVpsServiceStatus.DEGRADED
    state.last_error = str(exc)
    context.store.persist()
    _write_service_monitoring(context)
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="shadow_day_failed",
            message="Governed Shadow day failed.",
            session_date=state.last_selected_session_date,
            export_dir_ref=state.last_export_dir_ref,
            error=str(exc),
        ),
    )


def _run_shadow_vps_service_cycle(
    context: ShadowVpsServiceRuntimeContext,
    *,
    continue_on_error: bool,
) -> str:
    state = context.store.state
    state.loop_count += 1
    state.last_heartbeat_at = time.time()
    state.service_status = ShadowVpsServiceStatus.RUNNING
    context.store.persist()
    _write_service_monitoring(context)
    try:
        selection = _resolve_shadow_vps_cycle_selection(context)
        if selection.next_slot is None:
            _record_shadow_vps_idle_cycle(context)
            return "sleep"
        live_capture_result = _prepare_shadow_vps_selected_cycle(context, selection)
        last_run = _run_shadow_vps_daily_orchestrator(context, selection)
        runtime_evidence_bundle_path = _write_runtime_evidence_bundle(
            service_dir=context.service_dir,
            session_date=last_run["session_date"],
            raw_slot=selection.raw_slot,
            websocket_slot=selection.websocket_slot,
            live_capture_result=live_capture_result,
            auto_snapshot_dir=selection.auto_snapshot_dir,
            auto_export_dir=selection.auto_export_dir,
            last_run=last_run,
        )
        _apply_last_run_to_shadow_vps_state(
            context,
            last_run,
            runtime_evidence_bundle_path,
        )
        execution_telemetry_status, execution_telemetry_artifact_path = (
            _write_shadow_vps_cycle_execution_telemetry(
                context,
                selection,
                last_run,
                live_capture_result,
            )
        )
        _complete_shadow_vps_successful_cycle(
            context,
            selection,
            last_run,
            live_capture_result,
            execution_telemetry_status,
            execution_telemetry_artifact_path,
        )
        return "next"
    except Exception as exc:
        _record_shadow_vps_failed_cycle(context, exc)
        return "sleep" if continue_on_error else "break"


def _finalize_shadow_vps_service_runtime(
    context: ShadowVpsServiceRuntimeContext,
) -> None:
    state = context.store.state
    if state.service_status != ShadowVpsServiceStatus.DEGRADED:
        state.service_status = ShadowVpsServiceStatus.STOPPED
    state.last_heartbeat_at = time.time()
    final_bundle = _read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
    if state.last_runtime_evidence_bundle_ref:
        campaign_summary_path = _write_campaign_summary(
            service_dir=context.service_dir,
            state=state,
            bundle=final_bundle,
        )
        state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
    context.store.persist()
    _write_service_monitoring(context)
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="service_stopped",
            message="Shadow VPS service stopped.",
            session_date=state.last_completed_session_date,
        ),
    )
    if state.last_runtime_evidence_bundle_ref:
        final_bundle = _read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
        campaign_summary_path = _write_campaign_summary(
            service_dir=context.service_dir,
            state=state,
            bundle=final_bundle,
        )
        state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
        context.store.persist()
    _write_service_monitoring(context)


def run_shadow_vps_service(
    service_dir: Path,
    *,
    orchestrator_output_dir: Path | None = None,
    shadow_output_dir: Path | None = None,
    exports_root: Path | None = None,
    raw_inputs_root: Path | None = None,
    websocket_streams_root: Path | None = None,
    live_websocket_config_path: Path | None = None,
    live_captures_root: Path | None = None,
    auto_snapshots_root: Path | None = None,
    auto_exports_root: Path | None = None,
    execution_time_sync_offsets_path: Path | None = None,
    execution_runtime_bootstrap_enabled: bool = False,
    execution_runtime_gatekeeper_audit_path: Path | None = None,
    execution_runtime_projection_path: Path | None = None,
    regime_lite_assessment_path: Path | None = None,
    regime_lite_safing_recommendation_path: Path | None = None,
    info_stress_assessment_path: Path | None = None,
    telegram_alert_config_path: Path | None = None,
    telegram_alert_key_path: Path | None = None,
    telegram_post_func: TelegramPostFunc | None = None,
    node_exporter_textfile_dir: Path | None = None,
    scrape_host: str = "",
    vps_id: str = "",
    node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http",
    node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps",
    poll_interval_s: float = 5.0,
    max_cycles: int | None = None,
    continue_on_error: bool = True,
) -> int:
    context = _initialize_shadow_vps_service_runtime(
        service_dir=service_dir,
        orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir,
        exports_root=exports_root,
        raw_inputs_root=raw_inputs_root,
        websocket_streams_root=websocket_streams_root,
        live_websocket_config_path=live_websocket_config_path,
        live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root,
        auto_exports_root=auto_exports_root,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        telegram_post_func=telegram_post_func,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host,
        vps_id=vps_id,
        node_exporter_port=node_exporter_port,
        node_exporter_scheme=node_exporter_scheme,
        node_exporter_metrics_path=node_exporter_metrics_path,
        prometheus_job_name=prometheus_job_name,
    )
    _run_shadow_vps_service_main_loop(
        context,
        poll_interval_s=poll_interval_s,
        max_cycles=max_cycles,
        continue_on_error=continue_on_error,
    )
    _finalize_shadow_vps_service_runtime(context)
    _emit_output_lines(
        _build_service_output_lines(
            store=context.store,
            service_dir=context.service_dir,
            resolved_orchestrator_output_dir=context.resolved_orchestrator_output_dir,
            resolved_shadow_output_dir=context.resolved_shadow_output_dir,
            scrape_host=context.monitoring.scrape_host,
            node_exporter_textfile_dir=context.monitoring.node_exporter_textfile_dir,
        )
    )
    return 0


def _run_shadow_vps_service_main_loop(
    context: ShadowVpsServiceRuntimeContext,
    *,
    poll_interval_s: float,
    max_cycles: int | None,
    continue_on_error: bool,
) -> None:
    cycle_index = 0
    while max_cycles is None or cycle_index < max_cycles:
        cycle_index += 1
        action = _run_shadow_vps_service_cycle(
            context,
            continue_on_error=continue_on_error,
        )
        if action == "break":
            break
        if action == "sleep" and (max_cycles is None or cycle_index < max_cycles):
            time.sleep(max(0.0, poll_interval_s))

def _emit_output_lines(lines: tuple[str, ...]) -> None:
    for line in lines:
        sys.stdout.write(f"{line}\n")


def _build_service_output_lines(
    *,
    store: ShadowVpsServiceStore,
    service_dir: Path,
    resolved_orchestrator_output_dir: Path,
    resolved_shadow_output_dir: Path,
    scrape_host: str,
    node_exporter_textfile_dir: Path | None,
) -> tuple[str, ...]:
    state = store.state
    lines = [
        f"Shadow VPS service state JSON: {store.state_path}",
        f"Shadow VPS service events JSONL: {store.events_path}",
        (
            "Shadow daily orchestrator state JSON: "
            f"{resolved_orchestrator_output_dir / 'shadow_daily_orchestrator.state.json'}"
        ),
        (
            "Shadow session summary JSON: "
            f"{resolved_shadow_output_dir / 'local_replay_shadow.shadow_session_summary.json'}"
        ),
        (
            "Shadow VPS monitoring backend JSON: "
            f"{service_dir / 'shadow_vps_service_monitoring_backend_payload.json'}"
        ),
        (
            "Shadow VPS observability export JSON: "
            f"{service_dir / 'shadow_vps_service_observability_export.json'}"
        ),
        (
            "Shadow VPS observability text PROM: "
            f"{service_dir / 'shadow_vps_service_observability.prom'}"
        ),
        (
            "Shadow VPS recent events summary JSON: "
            f"{service_dir / 'shadow_vps_service_recent_events.json'}"
        ),
    ]
    if scrape_host:
        lines.extend(
            [
                (
                    "Shadow VPS scrape manifest JSON: "
                    f"{service_dir / 'shadow_vps_service_scrape_manifest.json'}"
                ),
                (
                    "Shadow VPS Prometheus file_sd JSON: "
                    f"{service_dir / 'shadow_vps_service_prometheus_file_sd.json'}"
                ),
            ]
        )
    if node_exporter_textfile_dir is not None:
        lines.append(
            "Shadow VPS node_exporter textfile PROM: "
            f"{node_exporter_textfile_dir / 'v53_shadow_vps_service.prom'}"
        )
    if state.last_campaign_summary_ref:
        lines.append(
            f"Shadow VPS campaign summary JSON: {state.last_campaign_summary_ref}"
        )
    if state.last_runtime_evidence_bundle_ref:
        lines.append(
            "Shadow runtime evidence bundle JSON: "
            f"{state.last_runtime_evidence_bundle_ref}"
        )
    if state.last_execution_telemetry_ref:
        lines.append(
            f"Shadow execution telemetry JSON: {state.last_execution_telemetry_ref}"
        )
    if state.last_execution_runtime_bootstrap_ref:
        lines.append(
            "Shadow execution runtime bootstrap summary JSON: "
            f"{state.last_execution_runtime_bootstrap_ref}"
        )
    return tuple(lines)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the autonomous VPS Shadow service that keeps polling and processing governed Shadow days."
        ),
    )
    _add_service_path_arguments(parser)
    _add_execution_runtime_arguments(parser)
    _add_monitoring_arguments(parser)
    _add_runtime_loop_arguments(parser)
    return parser


def _add_service_path_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--service-dir",
        type=Path,
        default=REPO_ROOT / "build" / "shadow_vps_service",
        help="Directory used to persist the VPS Shadow service state and logs.",
    )
    parser.add_argument(
        "--orchestrator-output-dir",
        type=Path,
        default=None,
        help="Optional directory used for the external daily orchestrator state.",
    )
    parser.add_argument(
        "--shadow-output-dir",
        type=Path,
        default=None,
        help="Optional directory used for the long-lived Shadow session artifacts.",
    )
    parser.add_argument(
        "--exports-root",
        type=Path,
        default=None,
        help="Optional root containing daily export directories named YYYY-MM-DD.",
    )
    parser.add_argument(
        "--raw-inputs-root",
        type=Path,
        default=None,
        help=(
            "Optional root containing daily raw input directories named YYYY-MM-DD. "
            "Each dated directory must contain a replay_dataset.* or snapshot_batch.* file."
        ),
    )
    parser.add_argument(
        "--websocket-streams-root",
        type=Path,
        default=None,
        help=(
            "Optional root containing daily injected websocket directories named YYYY-MM-DD. "
            "Each dated directory must contain websocket_stream.json(.l) or websocket_frames.json(.l)."
        ),
    )
    parser.add_argument(
        "--live-websocket-config",
        type=Path,
        default=None,
        help=(
            "Optional JSON config used to capture a bounded native live_websocket window "
            "directly from the VPS."
        ),
    )
    parser.add_argument(
        "--live-captures-root",
        type=Path,
        default=None,
        help=(
            "Optional root where native live_websocket captures will be written before "
            "governed export."
        ),
    )
    parser.add_argument(
        "--auto-snapshots-root",
        type=Path,
        default=None,
        help=(
            "Optional root where historical snapshot batches auto-generated from "
            "--websocket-streams-root will be written."
        ),
    )
    parser.add_argument(
        "--auto-exports-root",
        type=Path,
        default=None,
        help=(
            "Optional root where governed exports auto-generated from --raw-inputs-root "
            "will be written."
        ),
    )


def _add_execution_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--execution-time-sync-offsets-path",
        type=Path,
        default=None,
        help=(
            "Optional JSON list/mapping carrying THR-X01 time-sync offsets for the current "
            "service cycle. When omitted, the service falls back to a native live-capture "
            "`live_time_sync_offsets.json` sidecar when present; otherwise the execution "
            "telemetry sidecar remains explicit partial for THR-X01."
        ),
    )
    parser.add_argument(
        "--execution-runtime-bootstrap-enabled",
        action="store_true",
        help=(
            "Enable the bounded Binance execution runtime bootstrap seam at service "
            "startup. This is inspection/bootstrap only, not order submission."
        ),
    )
    parser.add_argument(
        "--execution-runtime-gatekeeper-audit-path",
        type=Path,
        default=None,
        help=(
            "Optional JSONL audit path for the bounded execution gatekeeper audit "
            "logger used by the startup bootstrap seam."
        ),
    )
    parser.add_argument(
        "--execution-runtime-projection-path",
        type=Path,
        default=None,
        help=(
            "Optional Local IA Lab execution runtime projection artifact forwarded to "
            "the governed daily Shadow orchestrator."
        ),
    )
    parser.add_argument(
        "--regime-lite-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite assessment JSON forwarded to the governed "
            "daily Shadow orchestrator."
        ),
    )
    parser.add_argument(
        "--regime-lite-safing-recommendation-path",
        type=Path,
        default=None,
        help=(
            "Optional typed regime_lite safing recommendation JSON forwarded to the "
            "governed daily Shadow orchestrator."
        ),
    )
    parser.add_argument(
        "--info-stress-assessment-path",
        type=Path,
        default=None,
        help=(
            "Optional typed info_stress assessment JSON forwarded to the governed "
            "daily Shadow orchestrator."
        ),
    )
    parser.add_argument(
        "--telegram-alert-config-path",
        type=Path,
        default=None,
        help=(
            "Optional JSON/YAML or sealed Telegram bot config used to send bounded "
            "Shadow service alerts."
        ),
    )
    parser.add_argument(
        "--telegram-alert-key-path",
        type=Path,
        default=None,
        help=(
            "Optional master-key path required when --telegram-alert-config-path "
            "targets a sealed secret mapping."
        ),
    )


def _add_monitoring_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--node-exporter-textfile-dir",
        type=Path,
        default=None,
        help=(
            "Optional node_exporter textfile collector directory where the compact "
            "Shadow VPS `.prom` export will be mirrored."
        ),
    )
    parser.add_argument(
        "--scrape-host",
        default="",
        help=(
            "Optional reachable host or IP used to materialize a local-PC Prometheus "
            "scrape manifest for this VPS."
        ),
    )
    parser.add_argument(
        "--vps-id",
        default="",
        help="Optional stable VPS identifier written into the local scrape manifest.",
    )
    parser.add_argument(
        "--node-exporter-port",
        type=int,
        default=9100,
        help="Port used for the node_exporter endpoint on the VPS.",
    )
    parser.add_argument(
        "--node-exporter-scheme",
        default="http",
        help="Scheme used for the node_exporter endpoint on the VPS.",
    )
    parser.add_argument(
        "--node-exporter-metrics-path",
        default="/metrics",
        help="Metrics path used for the node_exporter endpoint on the VPS.",
    )
    parser.add_argument(
        "--prometheus-job-name",
        default="v53_shadow_vps",
        help="Job label written into the Prometheus file_sd entry for this VPS.",
    )


def _add_runtime_loop_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--poll-interval-s",
        type=float,
        default=5.0,
        help="Sleep duration between cycles when the service stays alive.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Optional maximum number of service cycles. Useful for tests and smoke runs.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the service immediately on the first orchestration error.",
    )


def _validate_input_root_selection(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    selected_input_roots = (
        int(args.exports_root is not None)
        + int(args.raw_inputs_root is not None)
        + int(args.websocket_streams_root is not None)
        + int(args.live_websocket_config is not None)
    )
    if selected_input_roots > 1:
        parser.error(
            "--exports-root, --raw-inputs-root, --websocket-streams-root, and --live-websocket-config are mutually exclusive"
        )


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    _validate_input_root_selection(parser, args)
    return run_shadow_vps_service(
        args.service_dir,
        orchestrator_output_dir=args.orchestrator_output_dir,
        shadow_output_dir=args.shadow_output_dir,
        exports_root=args.exports_root,
        raw_inputs_root=args.raw_inputs_root,
        websocket_streams_root=args.websocket_streams_root,
        live_websocket_config_path=args.live_websocket_config,
        live_captures_root=args.live_captures_root,
        auto_snapshots_root=args.auto_snapshots_root,
        auto_exports_root=args.auto_exports_root,
        execution_time_sync_offsets_path=args.execution_time_sync_offsets_path,
        execution_runtime_bootstrap_enabled=args.execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=(
            args.execution_runtime_gatekeeper_audit_path
        ),
        execution_runtime_projection_path=args.execution_runtime_projection_path,
        regime_lite_assessment_path=args.regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=(
            args.regime_lite_safing_recommendation_path
        ),
        info_stress_assessment_path=args.info_stress_assessment_path,
        telegram_alert_config_path=args.telegram_alert_config_path,
        telegram_alert_key_path=args.telegram_alert_key_path,
        node_exporter_textfile_dir=args.node_exporter_textfile_dir,
        scrape_host=args.scrape_host,
        vps_id=args.vps_id,
        node_exporter_port=args.node_exporter_port,
        node_exporter_scheme=args.node_exporter_scheme,
        node_exporter_metrics_path=args.node_exporter_metrics_path,
        prometheus_job_name=args.prometheus_job_name,
        poll_interval_s=max(0.0, args.poll_interval_s),
        max_cycles=args.max_cycles,
        continue_on_error=not args.stop_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
