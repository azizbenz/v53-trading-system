"""Observability and VPS monitoring contracts for the real Build-10 backend."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import ProfileId, RuntimeMode, TimestampedModel

from .contracts_core import MetricKind, ProjectionStatus, ShadowVpsLogScanMode


class MetricSample(BaseModel, frozen=True):
    """Single structured metric emitted by the minimal observability layer."""

    name: str = Field(..., min_length=1)
    kind: MetricKind
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    unit: str = ""


class ObservabilityExport(TimestampedModel):
    """Structured and text-exportable monitoring snapshot."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    samples: tuple[MetricSample, ...] = ()
    text_payload: str = Field(..., min_length=1)


class ProcessMetricsSample(BaseModel, frozen=True):
    """Bounded real process metrics sampled from the running VPS service."""

    pid: int = Field(..., ge=1)
    cpu_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    rss_mb: float = Field(default=0.0, ge=0.0)
    thread_count: int = Field(default=0, ge=0)
    sampling_mode: str = Field(..., min_length=1)


class DiskUsageSample(BaseModel, frozen=True):
    """Bounded disk usage snapshot for the runtime service directory/volume."""

    path: str = Field(..., min_length=1)
    total_gb: float = Field(default=0.0, ge=0.0)
    free_gb: float = Field(default=0.0, ge=0.0)
    used_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    sampling_mode: str = Field(..., min_length=1)


class ShadowVpsServiceMonitoringPayload(TimestampedModel):
    """Typed future-dashboard payload emitted by the real VPS Shadow service."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    status: ProjectionStatus
    detail: str = Field(..., min_length=1)
    service_status: str = Field(..., min_length=1)
    heartbeat_age_ms: int = Field(default=0, ge=0)
    loop_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    idle_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    resumed: bool = False
    acquisition_mode: str = Field(default="unknown", min_length=1)
    runtime_data_source: str = Field(default="unknown", min_length=1)
    accepted: bool = False
    consecutive_days: int = Field(default=0, ge=0)
    remaining_days: int = Field(default=0, ge=0)
    promotion_gate_passed: bool = False
    live_capture_emitted_message_count: int = Field(default=0, ge=0)
    live_capture_accepted_message_count: int = Field(default=0, ge=0)
    live_capture_rejected_message_count: int = Field(default=0, ge=0)
    live_user_data_authenticated: bool = False
    live_user_data_event_count: int = Field(default=0, ge=0)
    last_selected_session_date: str = ""
    last_completed_session_date: str = ""
    last_error: str = ""
    state_path: str = ""
    events_path: str = ""
    campaign_summary_ref: str = ""
    runtime_evidence_bundle_ref: str = ""
    execution_telemetry_ref: str = ""
    execution_telemetry_status: str = "not_configured"
    telegram_alert_delivery_status: str = "not_configured"
    telegram_alert_delivery_event_type: str = ""
    telegram_alert_delivery_error: str = ""
    telegram_alert_config_ref: str = ""
    telegram_alert_config_source: str = "not_configured"
    telegram_alert_key_ref: str = ""
    telegram_alert_key_source: str = "not_configured"
    execution_runtime_bootstrap_ref: str = ""
    execution_runtime_bootstrap_status: str = "not_configured"
    execution_runtime_bootstrap_source: str = "not_configured"
    execution_runtime_gatekeeper_audit_ref: str = ""
    execution_runtime_gatekeeper_audit_source: str = "not_configured"
    execution_runtime_bootstrap_user_data_stream_enabled: bool = False
    execution_runtime_bootstrap_reconciliation_boot_executed: bool = False
    execution_runtime_bootstrap_reconciliation_boot_trading_blocked: bool = False
    execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped: bool = False
    execution_runtime_bootstrap_reconciliation_boot_detail: str = ""
    execution_runtime_bootstrap_reconciliation_boot_recovery_action: str = ""
    execution_runtime_bootstrap_reconciliation_boot_divergence_count: int = Field(
        default=0,
        ge=0,
    )
    execution_runtime_bootstrap_remote_state_snapshot_captured: bool = False
    execution_runtime_bootstrap_remote_open_order_count: int = Field(default=0, ge=0)
    execution_runtime_bootstrap_remote_position_asset_count: int = Field(default=0, ge=0)
    execution_runtime_bootstrap_remote_open_orders_present: bool = False
    execution_runtime_bootstrap_remote_positions_present: bool = False
    vps_recovery_readiness_report_ref: str = ""
    vps_recovery_status: str = "not_configured"
    vps_recovery_eligible_to_trade: bool = False
    vps_warmup_summary_ref: str = ""
    vps_warmup_final_state: str = "not_configured"
    vps_warmup_eligible_to_trade: bool = False
    active_ml_artifact_hash: str = ""
    active_ml_artifact_id: str = ""
    active_regime_detector_artifact_hash: str = ""
    active_regime_detector_artifact_id: str = ""
    active_regime_detector_shadow_audit_bundle_ref: str = ""
    dashboard_control_halted: bool = False
    dashboard_control_target_profile: str = ""
    dashboard_control_target_deployment_state: str = ""
    dashboard_control_suspended_pair_count: int = Field(default=0, ge=0)
    dashboard_control_suspended_engine_count: int = Field(default=0, ge=0)
    dashboard_control_suspended_pairs: tuple[str, ...] = ()
    dashboard_control_suspended_engines: tuple[str, ...] = ()
    dashboard_control_last_request_id: str = ""
    dashboard_control_last_command_kind: str = ""
    dashboard_control_last_result_status: str = ""
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_source: str = "not_configured"
    regime_lite_assessment_ref: str = ""
    regime_lite_assessment_source: str = "not_configured"
    regime_lite_safing_recommendation_ref: str = ""
    regime_lite_safing_recommendation_source: str = "not_configured"
    info_stress_assessment_ref: str = ""
    info_stress_assessment_source: str = "not_configured"
    execution_runtime_projection_status: str = "not_configured"
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_bridge_status: str = "planned"
    execution_runtime_projection_bridge_loaded: bool = False
    execution_runtime_projection_rate_limit_model_loaded: bool = False
    execution_runtime_projection_spread_guard_model_loaded: bool = False
    execution_runtime_projection_slippage_model_loaded: bool = False
    regime_lite_governance_status: str = "not_configured"
    regime_lite_state: str = "not_configured"
    regime_lite_candidate_state: str = "not_configured"
    regime_lite_entries_blocked: bool = False
    regime_lite_sudden_event: bool = False
    regime_lite_safing_severity: str = "not_configured"
    regime_lite_safing_should_block_new_entries: bool = False
    regime_lite_safing_should_exit_all: bool = False
    regime_lite_safing_recommended_operator_action: str = ""
    regime_lite_safing_operator_safing_request_action: str = ""
    regime_lite_safing_operator_safing_request_source_runtime_mode: str = ""
    regime_lite_safing_reason_codes: tuple[str, ...] = ()
    regime_lite_safing_detail: str = ""
    info_stress_governance_status: str = "not_configured"
    info_stress_level: str = "not_configured"
    info_stress_alert_count: int = Field(default=0, ge=0)
    info_stress_entries_blocked: bool = False
    info_stress_entries_blocked_until_ts: int = Field(default=0, ge=0)
    info_stress_reason_codes: tuple[str, ...] = ()
    info_stress_detail: str = ""
    export_dir_ref: str = ""
    recent_events_summary_ref: str = ""
    node_exporter_textfile_ref: str = ""
    scrape_manifest_ref: str = ""
    prometheus_file_sd_ref: str = ""
    process: ProcessMetricsSample
    disk: DiskUsageSample


class PrometheusFileSdEntry(BaseModel, frozen=True):
    """Single Prometheus file_sd target entry."""

    targets: tuple[str, ...] = Field(..., min_length=1)
    labels: dict[str, str] = Field(default_factory=dict)


class ShadowVpsServiceScrapeManifest(TimestampedModel):
    """Typed local-PC scrape handoff for one Shadow VPS service instance."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    status: ProjectionStatus
    detail: str = Field(..., min_length=1)
    service_status: str = Field(..., min_length=1)
    vps_id: str = Field(..., min_length=1)
    scrape_host: str = Field(..., min_length=1)
    node_exporter_scheme: str = Field(default="http", min_length=1)
    node_exporter_port: int = Field(default=9100, ge=1, le=65535)
    node_exporter_metrics_path: str = Field(default="/metrics", min_length=1)
    node_exporter_target: str = Field(..., min_length=1)
    prometheus_job_name: str = Field(..., min_length=1)
    file_sd_entry_count: int = Field(default=0, ge=0)
    node_exporter_textfile_ready: bool = False
    monitoring_backend_payload_ref: str = ""
    observability_export_ref: str = ""
    recent_events_summary_ref: str = ""
    node_exporter_textfile_ref: str = ""
    labels: dict[str, str] = Field(default_factory=dict)


class ShadowVpsServiceLogEventProjection(BaseModel, frozen=True):
    """Normalized structured Shadow VPS service event for bounded retrieval."""

    event_type: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    message: str = Field(..., min_length=1)
    session_date: str = ""
    export_dir_ref: str = ""
    accepted: bool | None = None
    consecutive_days: int | None = Field(default=None, ge=0)
    remaining_days: int | None = Field(default=None, ge=0)
    live_capture_summary_ref: str = ""
    emitted_message_count: int | None = Field(default=None, ge=0)
    accepted_message_count: int | None = Field(default=None, ge=0)
    ignored_message_count: int | None = Field(default=None, ge=0)
    rejected_message_count: int | None = Field(default=None, ge=0)
    pair_scope: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    error: str = ""


class ShadowVpsServiceLogQuery(BaseModel, frozen=True):
    """Bounded filter set used to inspect durable Shadow VPS service events."""

    max_events: int = Field(default=50, ge=1, le=500)
    event_types: tuple[str, ...] = ()
    session_date: str = ""
    contains_text: str = ""
    error_only: bool = False
    since_timestamp_ms: int | None = Field(default=None, ge=0)
    newest_first: bool = True


class ShadowVpsServiceLogQueryResult(TimestampedModel):
    """Typed bounded result returned by Shadow VPS service event retrieval."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    status: ProjectionStatus
    detail: str = Field(..., min_length=1)
    scan_mode: ShadowVpsLogScanMode
    scan_complete: bool = True
    events_path: str = Field(..., min_length=1)
    query: ShadowVpsServiceLogQuery
    scanned_line_count: int = Field(default=0, ge=0)
    parsed_event_count: int = Field(default=0, ge=0)
    parse_error_count: int = Field(default=0, ge=0)
    matched_event_count: int = Field(default=0, ge=0)
    returned_event_count: int = Field(default=0, ge=0)
    truncated: bool = False
    latest_event_type: str = ""
    latest_session_date: str = ""
    latest_error: str = ""
    events: tuple[ShadowVpsServiceLogEventProjection, ...] = ()


__all__ = [
    "DiskUsageSample",
    "MetricSample",
    "ObservabilityExport",
    "ProcessMetricsSample",
    "PrometheusFileSdEntry",
    "ShadowVpsServiceLogEventProjection",
    "ShadowVpsServiceLogQuery",
    "ShadowVpsServiceLogQueryResult",
    "ShadowVpsServiceMonitoringPayload",
    "ShadowVpsServiceScrapeManifest",
]
