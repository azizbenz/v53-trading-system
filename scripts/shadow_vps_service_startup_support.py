"""Shadow VPS service startup helpers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from alerting import TelegramAlerter, load_telegram_alerter_config_from_file
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsExecutionRuntimeBootstrapSummary,
)
from protocols import ShadowLiveWebSocketConfig, ShadowVpsServiceEvent, ShadowVpsServiceStatus
from shadow_vps_service_context_support import (
    _create_shadow_vps_service_runtime_context,
    _resolve_shadow_vps_service_runtime_dirs,
)
from shadow_vps_service_event_support import _append_service_event
from shadow_vps_service_io_support import (
    _read_live_websocket_config,
    _resolve_execution_runtime_bootstrap_enabled,
    _resolve_execution_runtime_gatekeeper_audit_path,
    _resolve_execution_runtime_projection_path,
    _resolve_telegram_alert_config_path,
    _resolve_telegram_alert_key_path,
    _write_execution_runtime_bootstrap_summary,
)
from shadow_vps_service_loader_support import _load_daily_orchestrator_module
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext
from shadow_vps_service_monitoring_support import _write_service_monitoring
from shadow_vps_service_recovery_support import _refresh_shadow_vps_recovery_artifacts


TelegramPostFunc = Callable[[str, dict[str, object], float], tuple[int, str]]


class _ShadowVpsRuntimeContextInputs:
    def __init__(
        self,
        *,
        resolved_orchestrator_output_dir: Path,
        resolved_shadow_output_dir: Path,
        resolved_live_captures_root: Path,
        resolved_auto_snapshots_root: Path,
        resolved_auto_exports_root: Path,
        resolved_telegram_alert_config_path: Path | None,
        resolved_telegram_alert_config_source: str,
        resolved_telegram_alert_key_path: Path | None,
        resolved_telegram_alert_key_source: str,
        telegram_alerter: TelegramAlerter | None,
        bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary,
        bootstrap_summary_path: Path | None,
    ) -> None:
        self.resolved_orchestrator_output_dir = resolved_orchestrator_output_dir
        self.resolved_shadow_output_dir = resolved_shadow_output_dir
        self.resolved_live_captures_root = resolved_live_captures_root
        self.resolved_auto_snapshots_root = resolved_auto_snapshots_root
        self.resolved_auto_exports_root = resolved_auto_exports_root
        self.resolved_telegram_alert_config_path = resolved_telegram_alert_config_path
        self.resolved_telegram_alert_config_source = resolved_telegram_alert_config_source
        self.resolved_telegram_alert_key_path = resolved_telegram_alert_key_path
        self.resolved_telegram_alert_key_source = resolved_telegram_alert_key_source
        self.telegram_alerter = telegram_alerter
        self.bootstrap_summary = bootstrap_summary
        self.bootstrap_summary_path = bootstrap_summary_path


def _resolve_runtime_dir_bundle(
    *,
    service_dir: Path,
    orchestrator_output_dir: Path | None,
    shadow_output_dir: Path | None,
    live_captures_root: Path | None,
    auto_snapshots_root: Path | None,
    auto_exports_root: Path | None,
) -> tuple[Path, Path, Path, Path, Path]:
    return _resolve_shadow_vps_service_runtime_dirs(
        service_dir=service_dir,
        orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir,
        live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root,
        auto_exports_root=auto_exports_root,
    )


def _resolve_startup_live_config(
    live_websocket_config_path: Path | None,
) -> ShadowLiveWebSocketConfig | None:
    if live_websocket_config_path is None:
        return None
    return _read_live_websocket_config(live_websocket_config_path)


def _resolve_bootstrap_inputs(
    *,
    execution_runtime_bootstrap_enabled: bool,
    execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None,
    live_websocket_config_path: Path | None,
    startup_live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[bool, str, Path | None, str, Path | None, str]:
    """Resolve bootstrap inputs and sources from CLI + live config."""
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
    return (
        bootstrap_enabled,
        bootstrap_source,
        gatekeeper_audit_path,
        gatekeeper_audit_source,
        projection_path,
        projection_source,
    )


def _resolve_bootstrap_summary(
    *,
    service_dir: Path,
    execution_runtime_bootstrap_enabled: bool,
    execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None,
    live_websocket_config_path: Path | None,
    startup_live_config: ShadowLiveWebSocketConfig | None,
) -> tuple[ShadowVpsExecutionRuntimeBootstrapSummary, Path | None]:
    (
        bootstrap_enabled,
        bootstrap_source,
        gatekeeper_audit_path,
        gatekeeper_audit_source,
        projection_path,
        projection_source,
    ) = _resolve_bootstrap_inputs(
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        live_websocket_config_path=live_websocket_config_path,
        startup_live_config=startup_live_config,
    )
    return _write_execution_runtime_bootstrap_summary(
        service_dir=service_dir,
        bootstrap_enabled=bootstrap_enabled,
        bootstrap_source=bootstrap_source,
        live_config=startup_live_config,
        execution_runtime_projection_path=projection_path,
        execution_runtime_projection_source=projection_source,
        gatekeeper_audit_path=gatekeeper_audit_path,
        gatekeeper_audit_source=gatekeeper_audit_source,
    )


def _resolve_telegram_alerter(
    *,
    telegram_alert_config_path: Path | None,
    telegram_alert_key_path: Path | None,
    live_websocket_config_path: Path | None,
    startup_live_config: ShadowLiveWebSocketConfig | None,
    telegram_post_func: TelegramPostFunc | None,
) -> tuple[Path | None, str, Path | None, str, TelegramAlerter | None]:
    resolved_config_path, resolved_config_source = _resolve_telegram_alert_config_path(
        explicit_path=telegram_alert_config_path,
        live_websocket_config_path=live_websocket_config_path,
        live_config=startup_live_config,
    )
    resolved_key_path, resolved_key_source = _resolve_telegram_alert_key_path(
        explicit_path=telegram_alert_key_path,
        live_websocket_config_path=live_websocket_config_path,
        live_config=startup_live_config,
    )
    if resolved_config_path is None:
        return None, "not_configured", None, "not_configured", None
    telegram_alerter = TelegramAlerter(
        load_telegram_alerter_config_from_file(
            resolved_config_path,
            key_path=resolved_key_path,
        ),
        post_func=telegram_post_func,
    )
    return (
        resolved_config_path,
        resolved_config_source,
        resolved_key_path,
        resolved_key_source,
        telegram_alerter,
    )


def _build_runtime_context_path_payload(
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
    dashboard_command_queue_root: Path | None,
) -> dict[str, object]:
    """Shape path-oriented keyword arguments for runtime context creation."""
    return {
        "service_dir": service_dir,
        "resolved_orchestrator_output_dir": resolved_orchestrator_output_dir,
        "resolved_shadow_output_dir": resolved_shadow_output_dir,
        "resolved_live_captures_root": resolved_live_captures_root,
        "resolved_auto_snapshots_root": resolved_auto_snapshots_root,
        "resolved_auto_exports_root": resolved_auto_exports_root,
        "exports_root": exports_root,
        "raw_inputs_root": raw_inputs_root,
        "websocket_streams_root": websocket_streams_root,
        "live_websocket_config_path": live_websocket_config_path,
        "execution_time_sync_offsets_path": execution_time_sync_offsets_path,
        "execution_runtime_projection_path": execution_runtime_projection_path,
        "regime_lite_assessment_path": regime_lite_assessment_path,
        "regime_lite_safing_recommendation_path": regime_lite_safing_recommendation_path,
        "info_stress_assessment_path": info_stress_assessment_path,
        "dashboard_command_queue_root": dashboard_command_queue_root,
    }


def _build_runtime_context_monitoring_payload(
    *,
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
) -> dict[str, object]:
    """Shape monitoring keyword arguments for runtime context creation."""
    return {
        "resolved_telegram_alert_config_path": resolved_telegram_alert_config_path,
        "resolved_telegram_alert_config_source": resolved_telegram_alert_config_source,
        "resolved_telegram_alert_key_path": resolved_telegram_alert_key_path,
        "resolved_telegram_alert_key_source": resolved_telegram_alert_key_source,
        "bootstrap_summary": bootstrap_summary,
        "bootstrap_summary_path": bootstrap_summary_path,
        "telegram_alerter": telegram_alerter,
        "node_exporter_textfile_dir": node_exporter_textfile_dir,
        "scrape_host": scrape_host,
        "vps_id": vps_id,
        "node_exporter_port": node_exporter_port,
        "node_exporter_scheme": node_exporter_scheme,
        "node_exporter_metrics_path": node_exporter_metrics_path,
        "prometheus_job_name": prometheus_job_name,
        "launcher_loader": _load_daily_orchestrator_module,
    }


def _build_shadow_vps_service_payloads(
    *, service_dir: Path, resolved_orchestrator_output_dir: Path,
    resolved_shadow_output_dir: Path, resolved_live_captures_root: Path,
    resolved_auto_snapshots_root: Path, resolved_auto_exports_root: Path,
    exports_root: Path | None, raw_inputs_root: Path | None,
    websocket_streams_root: Path | None, live_websocket_config_path: Path | None,
    execution_time_sync_offsets_path: Path | None, execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None, regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None, dashboard_command_queue_root: Path | None,
    resolved_telegram_alert_config_path: Path | None,
    resolved_telegram_alert_config_source: str, resolved_telegram_alert_key_path: Path | None,
    resolved_telegram_alert_key_source: str, bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary,
    bootstrap_summary_path: Path | None, telegram_alerter: TelegramAlerter | None,
    node_exporter_textfile_dir: Path | None, scrape_host: str, vps_id: str,
    node_exporter_port: int, node_exporter_scheme: str,
    node_exporter_metrics_path: str, prometheus_job_name: str,
) -> tuple[dict[str, object], dict[str, object]]:
    path_payload = _build_runtime_context_path_payload(
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
        dashboard_command_queue_root=dashboard_command_queue_root,
    )
    monitoring_payload = _build_runtime_context_monitoring_payload(
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
    return path_payload, monitoring_payload


def _build_shadow_vps_service_runtime_context(
    *, service_dir: Path, orchestrator_output_dir: Path | None, shadow_output_dir: Path | None,
    exports_root: Path | None, raw_inputs_root: Path | None, websocket_streams_root: Path | None,
    live_websocket_config_path: Path | None, live_captures_root: Path | None, auto_snapshots_root: Path | None,
    auto_exports_root: Path | None, execution_time_sync_offsets_path: Path | None,
    execution_runtime_bootstrap_enabled: bool, execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None, regime_lite_assessment_path: Path | None,
    regime_lite_safing_recommendation_path: Path | None, info_stress_assessment_path: Path | None,
    dashboard_command_queue_root: Path | None,
    telegram_alert_config_path: Path | None, telegram_alert_key_path: Path | None, telegram_post_func: TelegramPostFunc | None,
    node_exporter_textfile_dir: Path | None, scrape_host: str, vps_id: str, node_exporter_port: int,
    node_exporter_scheme: str, node_exporter_metrics_path: str, prometheus_job_name: str,
) -> ShadowVpsServiceRuntimeContext:
    inputs = _resolve_shadow_vps_runtime_context_inputs(
        service_dir=service_dir, orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir, live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root, auto_exports_root=auto_exports_root,
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        live_websocket_config_path=live_websocket_config_path,
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        telegram_post_func=telegram_post_func,
    )
    path_payload, monitoring_payload = _build_shadow_vps_service_payloads(
        service_dir=service_dir, resolved_orchestrator_output_dir=inputs.resolved_orchestrator_output_dir,
        resolved_shadow_output_dir=inputs.resolved_shadow_output_dir,
        resolved_live_captures_root=inputs.resolved_live_captures_root,
        resolved_auto_snapshots_root=inputs.resolved_auto_snapshots_root,
        resolved_auto_exports_root=inputs.resolved_auto_exports_root,
        exports_root=exports_root, raw_inputs_root=raw_inputs_root,
        websocket_streams_root=websocket_streams_root, live_websocket_config_path=live_websocket_config_path,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        dashboard_command_queue_root=dashboard_command_queue_root,
        resolved_telegram_alert_config_path=inputs.resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source=inputs.resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path=inputs.resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source=inputs.resolved_telegram_alert_key_source,
        bootstrap_summary=inputs.bootstrap_summary, bootstrap_summary_path=inputs.bootstrap_summary_path,
        telegram_alerter=inputs.telegram_alerter, node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host, vps_id=vps_id, node_exporter_port=node_exporter_port,
        node_exporter_scheme=node_exporter_scheme, node_exporter_metrics_path=node_exporter_metrics_path,
        prometheus_job_name=prometheus_job_name,
    )
    return _create_shadow_vps_service_runtime_context(
        **path_payload,
        **monitoring_payload,
    )


def _resolve_shadow_vps_runtime_context_inputs(
    *, service_dir: Path, orchestrator_output_dir: Path | None, shadow_output_dir: Path | None,
    live_captures_root: Path | None, auto_snapshots_root: Path | None, auto_exports_root: Path | None,
    execution_runtime_bootstrap_enabled: bool, execution_runtime_gatekeeper_audit_path: Path | None,
    execution_runtime_projection_path: Path | None, live_websocket_config_path: Path | None,
    telegram_alert_config_path: Path | None, telegram_alert_key_path: Path | None,
    telegram_post_func: TelegramPostFunc | None,
) -> _ShadowVpsRuntimeContextInputs:
    (
        resolved_orchestrator_output_dir,
        resolved_shadow_output_dir,
        resolved_live_captures_root,
        resolved_auto_snapshots_root,
        resolved_auto_exports_root,
    ) = _resolve_runtime_dir_bundle(
        service_dir=service_dir,
        orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir,
        live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root,
        auto_exports_root=auto_exports_root,
    )
    startup_live_config = _resolve_startup_live_config(live_websocket_config_path)
    (
        resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source,
        telegram_alerter,
    ) = _resolve_telegram_alerter(
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        live_websocket_config_path=live_websocket_config_path,
        startup_live_config=startup_live_config,
        telegram_post_func=telegram_post_func,
    )
    bootstrap_summary, bootstrap_summary_path = _resolve_bootstrap_summary(
        service_dir=service_dir,
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        live_websocket_config_path=live_websocket_config_path,
        startup_live_config=startup_live_config,
    )
    return _ShadowVpsRuntimeContextInputs(
        resolved_orchestrator_output_dir=resolved_orchestrator_output_dir,
        resolved_shadow_output_dir=resolved_shadow_output_dir,
        resolved_live_captures_root=resolved_live_captures_root,
        resolved_auto_snapshots_root=resolved_auto_snapshots_root,
        resolved_auto_exports_root=resolved_auto_exports_root,
        resolved_telegram_alert_config_path=resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source=resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path=resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source=resolved_telegram_alert_key_source,
        telegram_alerter=telegram_alerter,
        bootstrap_summary=bootstrap_summary,
        bootstrap_summary_path=bootstrap_summary_path,
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
    state.last_execution_runtime_bootstrap_remote_state_snapshot_captured = (
        context.bootstrap_summary.remote_state_snapshot_captured
    )
    state.last_execution_runtime_bootstrap_remote_open_order_count = (
        context.bootstrap_summary.remote_open_order_count
    )
    state.last_execution_runtime_bootstrap_remote_position_asset_count = (
        context.bootstrap_summary.remote_position_asset_count
    )
    state.last_execution_runtime_bootstrap_remote_open_orders_present = (
        context.bootstrap_summary.remote_open_orders_present
    )
    state.last_execution_runtime_bootstrap_remote_positions_present = (
        context.bootstrap_summary.remote_positions_present
    )
    context.store.persist()


def _emit_shadow_vps_startup_events(context: ShadowVpsServiceRuntimeContext) -> None:
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="service_started",
            message=(
                "Shadow VPS service resumed"
                if context.store.state.resumed
                else "Shadow VPS service started."
            ),
        ),
    )
    if context.bootstrap_summary.status == "not_configured":
        return
    if context.bootstrap_summary.status == "ready":
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="execution_runtime_bootstrap_ready",
                message="Bounded execution runtime bootstrap succeeded.",
            ),
        )
    else:
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


def _emit_shadow_vps_recovery_event(context: ShadowVpsServiceRuntimeContext) -> None:
    status = context.store.state.last_vps_recovery_status
    if status == "not_configured":
        return
    event_type = {
        "eligible_to_trade": "vps_recovery_eligible_to_trade",
        "review_only": "vps_recovery_review_only",
        "blocked": "vps_recovery_blocked",
    }.get(status, "vps_recovery_review_only")
    message = (
        f"Shadow VPS recovery status={status}; "
        f"warmup={context.store.state.last_vps_warmup_final_state}."
    )
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type=event_type,
            message=message,
        ),
    )


def _initialize_shadow_vps_service_runtime(
    *, service_dir: Path, orchestrator_output_dir: Path | None, shadow_output_dir: Path | None,
    exports_root: Path | None, raw_inputs_root: Path | None, websocket_streams_root: Path | None,
    live_websocket_config_path: Path | None, live_captures_root: Path | None,
    auto_snapshots_root: Path | None, auto_exports_root: Path | None,
    execution_time_sync_offsets_path: Path | None, execution_runtime_bootstrap_enabled: bool,
    execution_runtime_gatekeeper_audit_path: Path | None, execution_runtime_projection_path: Path | None,
    regime_lite_assessment_path: Path | None, regime_lite_safing_recommendation_path: Path | None,
    info_stress_assessment_path: Path | None, telegram_alert_config_path: Path | None,
    telegram_alert_key_path: Path | None, telegram_post_func: TelegramPostFunc | None,
    dashboard_command_queue_root: Path | None,
    node_exporter_textfile_dir: Path | None, scrape_host: str, vps_id: str,
    node_exporter_port: int, node_exporter_scheme: str,
    node_exporter_metrics_path: str, prometheus_job_name: str,
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
        dashboard_command_queue_root=dashboard_command_queue_root,
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
    _refresh_shadow_vps_recovery_artifacts(context)
    _emit_shadow_vps_startup_events(context)
    _emit_shadow_vps_recovery_event(context)
    _write_service_monitoring(context)
    return context
