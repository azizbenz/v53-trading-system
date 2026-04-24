"""Shared Shadow VPS service state/event contracts."""

from __future__ import annotations

from datetime import date
import time
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .dashboard_command_contracts import (
    BinanceCredentialInventoryEntry,
    BinanceCredentialValidationStatus,
    DashboardArtifactTransferManifest,
)
from .domain_types import DeploymentState, ProfileId

class ShadowVpsServiceStatus(StrEnum):
    """Runtime status for the autonomous VPS Shadow service."""

    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"


class ShadowVpsServiceState(BaseModel):
    """Persisted state for the autonomous VPS Shadow service."""

    service_status: ShadowVpsServiceStatus = ShadowVpsServiceStatus.IDLE
    started_at: float | None = None
    last_heartbeat_at: float | None = None
    loop_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    idle_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    resumed: bool = False
    last_selected_session_date: str = ""
    last_completed_session_date: str = ""
    last_raw_input_dir_ref: str = ""
    last_websocket_input_dir_ref: str = ""
    last_live_capture_dir_ref: str = ""
    last_live_capture_snapshot_batch_ref: str = ""
    last_live_capture_summary_ref: str = ""
    last_live_capture_time_sync_offsets_ref: str = ""
    last_live_user_data_summary_ref: str = ""
    last_auto_snapshot_dir_ref: str = ""
    last_auto_export_dir_ref: str = ""
    last_export_dir_ref: str = ""
    last_local_replay_evidence_ref: str = ""
    last_shadow_runtime_evidence_ref: str = ""
    last_runtime_evidence_bundle_ref: str = ""
    last_execution_telemetry_ref: str = ""
    last_execution_telemetry_status: str = "not_configured"
    last_telegram_alert_delivery_status: str = "not_configured"
    last_telegram_alert_delivery_event_type: str = ""
    last_telegram_alert_delivery_error: str = ""
    last_telegram_alert_config_ref: str = ""
    last_telegram_alert_config_source: str = ""
    last_telegram_alert_key_ref: str = ""
    last_telegram_alert_key_source: str = ""
    last_execution_runtime_bootstrap_ref: str = ""
    last_execution_runtime_bootstrap_status: str = "not_configured"
    last_execution_runtime_bootstrap_source: str = ""
    last_execution_runtime_gatekeeper_audit_ref: str = ""
    last_execution_runtime_gatekeeper_audit_source: str = ""
    last_execution_runtime_bootstrap_remote_state_snapshot_captured: bool = False
    last_execution_runtime_bootstrap_remote_open_order_count: int = Field(
        default=0,
        ge=0,
    )
    last_execution_runtime_bootstrap_remote_position_asset_count: int = Field(
        default=0,
        ge=0,
    )
    last_execution_runtime_bootstrap_remote_open_orders_present: bool = False
    last_execution_runtime_bootstrap_remote_positions_present: bool = False
    last_execution_runtime_projection_ref: str = ""
    last_execution_runtime_projection_source: str = ""
    last_vps_recovery_readiness_report_ref: str = ""
    last_vps_recovery_status: str = "not_configured"
    last_vps_recovery_eligible_to_trade: bool = False
    last_vps_warmup_summary_ref: str = ""
    last_vps_warmup_final_state: str = "not_configured"
    last_vps_warmup_eligible_to_trade: bool = False
    last_live_complete_summary_ref: str = ""
    last_live_complete_status: str = "not_configured"
    last_live_complete_verdict: str = "not_configured"
    last_live_complete_run_state: str = "not_configured"
    last_live_complete_blocking_reason_count: int = Field(default=0, ge=0)
    last_live_complete_operator_report_ref: str = ""
    last_live_complete_operator_report_status: str = "not_available"
    last_live_complete_operator_report_recommendation: str = ""
    active_ml_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_shadow_audit_bundle_ref: str = ""
    binance_credential_inventory: tuple[BinanceCredentialInventoryEntry, ...] = ()
    active_binance_credential_profile_id: str = ""
    active_binance_credential_environment: str = ""
    binance_credential_validation_status: str = (
        BinanceCredentialValidationStatus.UNKNOWN.value
    )
    binance_credential_last_auth_check_ms: int = Field(default=0, ge=0)
    binance_credential_last_failure_reason_codes: tuple[str, ...] = ()
    dashboard_control_halted: bool = False
    dashboard_control_target_profile: str = ""
    dashboard_control_target_deployment_state: str = ""
    dashboard_control_suspended_pairs: tuple[str, ...] = ()
    dashboard_control_suspended_engines: tuple[str, ...] = ()
    dashboard_control_last_request_id: str = ""
    dashboard_control_last_command_kind: str = ""
    dashboard_control_last_operator_reason: str = ""
    dashboard_control_last_result_status: str = ""
    dashboard_control_last_command_timestamp_ms: int = Field(default=0, ge=0)
    last_regime_lite_assessment_ref: str = ""
    last_regime_lite_assessment_source: str = ""
    last_regime_lite_safing_recommendation_ref: str = ""
    last_regime_lite_safing_recommendation_source: str = ""
    last_info_stress_assessment_ref: str = ""
    last_info_stress_assessment_source: str = ""
    last_shadow_report_ref: str = ""
    last_shadow_session_summary_ref: str = ""
    last_shadow_session_registry_ref: str = ""
    last_orchestrator_state_ref: str = ""
    last_campaign_summary_ref: str = ""
    last_error: str = ""

    @model_validator(mode="after")
    def validate_dashboard_control_state(self) -> "ShadowVpsServiceState":
        if len(set(self.dashboard_control_suspended_pairs)) != len(
            self.dashboard_control_suspended_pairs
        ):
            raise ValueError("dashboard_control_suspended_pairs must be unique")
        if len(set(self.dashboard_control_suspended_engines)) != len(
            self.dashboard_control_suspended_engines
        ):
            raise ValueError("dashboard_control_suspended_engines must be unique")
        if self.dashboard_control_target_profile:
            ProfileId(self.dashboard_control_target_profile)
        if self.dashboard_control_target_deployment_state:
            DeploymentState(self.dashboard_control_target_deployment_state)
        profile_ids = tuple(
            item.profile.profile_id for item in self.binance_credential_inventory
        )
        if len(set(profile_ids)) != len(profile_ids):
            raise ValueError("binance_credential_inventory profile_id values must be unique")
        if self.active_binance_credential_profile_id:
            if self.active_binance_credential_profile_id not in set(profile_ids):
                raise ValueError(
                    "active_binance_credential_profile_id must exist in inventory"
                )
        if len(set(self.binance_credential_last_failure_reason_codes)) != len(
            self.binance_credential_last_failure_reason_codes
        ):
            raise ValueError(
                "binance_credential_last_failure_reason_codes must be unique"
            )
        BinanceCredentialValidationStatus(self.binance_credential_validation_status)
        return self


class ShadowVpsRuntimeEvidenceBundle(BaseModel, frozen=True):
    """Durable proof chain emitted by the autonomous VPS Shadow service."""

    session_date: str = Field(..., min_length=10)
    acquisition_mode: str = Field(..., min_length=1)
    raw_input_dir_ref: str = ""
    websocket_input_dir_ref: str = ""
    live_capture_dir_ref: str = ""
    live_capture_snapshot_batch_ref: str = ""
    live_capture_summary_ref: str = ""
    live_capture_emitted_message_count: int = Field(default=0, ge=0)
    live_capture_accepted_message_count: int = Field(default=0, ge=0)
    live_capture_ignored_message_count: int = Field(default=0, ge=0)
    live_capture_rejected_message_count: int = Field(default=0, ge=0)
    live_capture_pair_scope: tuple[str, ...] = ()
    live_capture_event_types: tuple[str, ...] = ()
    live_capture_time_sync_offsets_ref: str = ""
    live_capture_time_sync_sample_count: int = Field(default=0, ge=0)
    live_capture_time_sync_probe_error: str = ""
    live_user_data_summary_ref: str = ""
    live_user_data_events_ref: str = ""
    live_user_data_authenticated: bool = False
    live_user_data_subscription_id: int | None = Field(default=None, ge=0)
    live_user_data_event_count: int = Field(default=0, ge=0)
    live_user_data_event_types: tuple[str, ...] = ()
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
    regime_lite_state_changed: bool = False
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
    auto_snapshot_dir_ref: str = ""
    auto_export_dir_ref: str = ""
    export_dir_ref: str = ""
    local_replay_evidence_ref: str = ""
    shadow_runtime_evidence_ref: str = ""
    shadow_summary_ref: str = ""
    shadow_report_ref: str = ""
    shadow_session_summary_ref: str = ""
    shadow_session_registry_ref: str = ""
    orchestrator_state_ref: str = ""
    runtime_data_source: str = "unknown"
    runtime_evidence_summary: str = "No real runtime evidence recorded"
    accepted: bool = False
    consecutive_days: int = Field(default=0, ge=0)
    remaining_days: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_session_date(self) -> "ShadowVpsRuntimeEvidenceBundle":
        date.fromisoformat(self.session_date)
        return self


class ShadowVpsCampaignSummary(BaseModel, frozen=True):
    """Current cumulative Build-11 VPS campaign status for operator review."""

    service_status: ShadowVpsServiceStatus
    loop_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    idle_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    resumed: bool = False
    last_selected_session_date: str = ""
    last_completed_session_date: str = ""
    acquisition_mode: str = ""
    accepted: bool = False
    consecutive_days: int = Field(default=0, ge=0)
    remaining_days: int = Field(default=0, ge=0)
    promotion_gate_passed: bool = False
    runtime_data_source: str = "unknown"
    runtime_evidence_summary: str = "No real runtime evidence recorded"
    live_capture_summary_ref: str = ""
    live_capture_emitted_message_count: int = Field(default=0, ge=0)
    live_capture_accepted_message_count: int = Field(default=0, ge=0)
    live_capture_ignored_message_count: int = Field(default=0, ge=0)
    live_capture_rejected_message_count: int = Field(default=0, ge=0)
    live_capture_pair_scope: tuple[str, ...] = ()
    live_capture_event_types: tuple[str, ...] = ()
    live_capture_time_sync_offsets_ref: str = ""
    live_capture_time_sync_sample_count: int = Field(default=0, ge=0)
    live_capture_time_sync_probe_error: str = ""
    live_user_data_summary_ref: str = ""
    live_user_data_authenticated: bool = False
    live_user_data_subscription_id: int | None = Field(default=None, ge=0)
    live_user_data_event_count: int = Field(default=0, ge=0)
    live_user_data_event_types: tuple[str, ...] = ()
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
    regime_lite_state_changed: bool = False
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
    runtime_evidence_bundle_ref: str = ""
    shadow_report_ref: str = ""
    shadow_session_summary_ref: str = ""
    shadow_session_registry_ref: str = ""
    orchestrator_state_ref: str = ""


class ShadowVpsServiceEvent(BaseModel, frozen=True):
    """Single structured event emitted by the autonomous VPS Shadow service."""

    event_type: str = Field(..., min_length=1)
    timestamp: float = Field(default_factory=time.time)
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
    reason_codes: tuple[str, ...] = ()
    error: str = ""


class ShadowVpsExecutionRuntimeBootstrapSummary(BaseModel, frozen=True):
    """Bounded service-owned summary of the explicit execution bootstrap seam."""

    status: str = "not_configured"
    source: str = "not_configured"
    execution_runtime_projection_ref: str = ""
    execution_runtime_projection_source: str = "not_configured"
    gatekeeper_audit_ref: str = ""
    gatekeeper_audit_source: str = "not_configured"
    user_data_stream_enabled: bool = False
    reconciliation_boot_executed: bool = False
    reconciliation_boot_trading_blocked: bool = False
    reconciliation_boot_circuit_breaker_tripped: bool = False
    reconciliation_boot_detail: str = ""
    reconciliation_boot_recovery_action: str = ""
    reconciliation_boot_divergence_count: int = Field(default=0, ge=0)
    remote_state_snapshot_captured: bool = False
    remote_open_order_count: int = Field(default=0, ge=0)
    remote_position_asset_count: int = Field(default=0, ge=0)
    remote_open_orders_present: bool = False
    remote_positions_present: bool = False
    error: str = ""


__all__ = [
    "ShadowVpsServiceStatus",
    "ShadowVpsServiceState",
    "ShadowVpsRuntimeEvidenceBundle",
    "ShadowVpsCampaignSummary",
    "ShadowVpsServiceEvent",
    "ShadowVpsExecutionRuntimeBootstrapSummary",
]
