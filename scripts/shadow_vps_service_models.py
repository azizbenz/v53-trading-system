#!/usr/bin/env python3
"""Models for the Shadow VPS service launcher."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsExecutionRuntimeBootstrapSummary,
    ShadowVpsServiceState,
)
from monitoring import ProcessMetricsSampler
from protocols import (
    ShadowDailyPlanSlot,
    ShadowLiveWebSocketCaptureResult,
    ShadowVpsRawInputSlot,
    ShadowVpsServiceStore,
    ShadowVpsWebsocketInputSlot,
)
from alerting import TelegramAlerter


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
    dashboard_command_queue_root: Path | None
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
    live_capture_result: ShadowLiveWebSocketCaptureResult | None
