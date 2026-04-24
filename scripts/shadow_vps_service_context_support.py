#!/usr/bin/env python3
"""Runtime context helpers for the Shadow VPS service."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Callable

from alerting import TelegramAlerter
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsExecutionRuntimeBootstrapSummary,
)
from monitoring import ProcessMetricsSampler
from protocols import ShadowVpsServiceStore
from shadow_vps_service_models import (
    ShadowVpsServiceMonitoringConfig,
    ShadowVpsServiceRuntimeContext,
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
    dashboard_command_queue_root: Path | None,
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
    launcher_loader: Callable[[], ModuleType],
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
        dashboard_command_queue_root=dashboard_command_queue_root,
        resolved_telegram_alert_config_path=resolved_telegram_alert_config_path,
        resolved_telegram_alert_config_source=resolved_telegram_alert_config_source,
        resolved_telegram_alert_key_path=resolved_telegram_alert_key_path,
        resolved_telegram_alert_key_source=resolved_telegram_alert_key_source,
        bootstrap_summary=bootstrap_summary,
        bootstrap_summary_path=bootstrap_summary_path,
        store=ShadowVpsServiceStore(service_dir),
        process_metrics_sampler=ProcessMetricsSampler(),
        telegram_alerter=telegram_alerter,
        launcher=launcher_loader(),
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
