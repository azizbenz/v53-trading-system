"""Typed monitoring projection for the real Shadow VPS service loop."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
)
from monitoring.contracts import (
    DiskUsageSample,
    MetricSample,
    ObservabilityExport,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)


def _sample(
    name: str,
    *,
    kind: str,
    value: float,
    labels: dict[str, str],
    unit: str = "",
) -> MetricSample:
    return MetricSample(name=name, kind=kind, value=value, labels=labels, unit=unit)


def _projection_status_from_state(state: ShadowVpsServiceState) -> str:
    if state.service_status.value == "degraded":
        return "critical"
    if state.last_error:
        return "warning"
    if state.service_status.value in {"idle", "stopped"}:
        return "info"
    return "healthy"


def build_shadow_vps_service_monitoring_payload(
    *,
    timestamp_ms: int,
    state: ShadowVpsServiceState,
    process: ProcessMetricsSample,
    disk: DiskUsageSample,
    campaign_summary: ShadowVpsCampaignSummary | None = None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None = None,
    state_path: str = "",
    events_path: str = "",
    recent_events_summary_ref: str = "",
    node_exporter_textfile_ref: str = "",
    scrape_manifest_ref: str = "",
    prometheus_file_sd_ref: str = "",
) -> ShadowVpsServiceMonitoringPayload:
    """Project durable service state into a future-dashboard payload."""

    heartbeat_age_ms = 0
    if state.last_heartbeat_at is not None:
        heartbeat_age_ms = max(
            0,
            int(timestamp_ms - int(state.last_heartbeat_at * 1000.0)),
        )

    acquisition_mode = (
        campaign_summary.acquisition_mode
        if campaign_summary is not None and campaign_summary.acquisition_mode
        else runtime_evidence_bundle.acquisition_mode
        if runtime_evidence_bundle is not None
        else "unknown"
    )
    runtime_data_source = (
        campaign_summary.runtime_data_source
        if campaign_summary is not None and campaign_summary.runtime_data_source
        else runtime_evidence_bundle.runtime_data_source
        if runtime_evidence_bundle is not None
        else "unknown"
    )
    accepted = (
        campaign_summary.accepted
        if campaign_summary is not None
        else runtime_evidence_bundle.accepted
        if runtime_evidence_bundle is not None
        else False
    )
    consecutive_days = (
        campaign_summary.consecutive_days
        if campaign_summary is not None
        else runtime_evidence_bundle.consecutive_days
        if runtime_evidence_bundle is not None
        else 0
    )
    remaining_days = (
        campaign_summary.remaining_days
        if campaign_summary is not None
        else runtime_evidence_bundle.remaining_days
        if runtime_evidence_bundle is not None
        else 0
    )
    promotion_gate_passed = (
        campaign_summary.promotion_gate_passed
        if campaign_summary is not None
        else bool(accepted and remaining_days == 0)
    )
    live_capture_emitted_message_count = (
        campaign_summary.live_capture_emitted_message_count
        if campaign_summary is not None
        else runtime_evidence_bundle.live_capture_emitted_message_count
        if runtime_evidence_bundle is not None
        else 0
    )
    live_capture_accepted_message_count = (
        campaign_summary.live_capture_accepted_message_count
        if campaign_summary is not None
        else runtime_evidence_bundle.live_capture_accepted_message_count
        if runtime_evidence_bundle is not None
        else 0
    )
    live_capture_rejected_message_count = (
        campaign_summary.live_capture_rejected_message_count
        if campaign_summary is not None
        else runtime_evidence_bundle.live_capture_rejected_message_count
        if runtime_evidence_bundle is not None
        else 0
    )
    live_user_data_authenticated = (
        campaign_summary.live_user_data_authenticated
        if campaign_summary is not None
        else runtime_evidence_bundle.live_user_data_authenticated
        if runtime_evidence_bundle is not None
        else False
    )
    live_user_data_event_count = (
        campaign_summary.live_user_data_event_count
        if campaign_summary is not None
        else runtime_evidence_bundle.live_user_data_event_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_telemetry_status = (
        campaign_summary.execution_telemetry_status
        if campaign_summary is not None
        and campaign_summary.execution_telemetry_status
        and campaign_summary.execution_telemetry_status != "not_configured"
        else state.last_execution_telemetry_status or "not_configured"
    )
    telegram_alert_delivery_status = (
        campaign_summary.telegram_alert_delivery_status
        if campaign_summary is not None
        and campaign_summary.telegram_alert_delivery_status
        and campaign_summary.telegram_alert_delivery_status != "not_configured"
        else state.last_telegram_alert_delivery_status or "not_configured"
    )
    telegram_alert_delivery_event_type = (
        campaign_summary.telegram_alert_delivery_event_type
        if campaign_summary is not None
        and campaign_summary.telegram_alert_delivery_event_type
        else state.last_telegram_alert_delivery_event_type
    )
    telegram_alert_delivery_error = (
        campaign_summary.telegram_alert_delivery_error
        if campaign_summary is not None
        and campaign_summary.telegram_alert_delivery_error
        else state.last_telegram_alert_delivery_error
    )
    telegram_alert_config_ref = (
        campaign_summary.telegram_alert_config_ref
        if campaign_summary is not None and campaign_summary.telegram_alert_config_ref
        else runtime_evidence_bundle.telegram_alert_config_ref
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.telegram_alert_config_ref
        else state.last_telegram_alert_config_ref
    )
    telegram_alert_config_source = (
        campaign_summary.telegram_alert_config_source
        if campaign_summary is not None and campaign_summary.telegram_alert_config_source
        else runtime_evidence_bundle.telegram_alert_config_source
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.telegram_alert_config_source
        else state.last_telegram_alert_config_source or "not_configured"
    )
    telegram_alert_key_ref = (
        campaign_summary.telegram_alert_key_ref
        if campaign_summary is not None and campaign_summary.telegram_alert_key_ref
        else runtime_evidence_bundle.telegram_alert_key_ref
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.telegram_alert_key_ref
        else state.last_telegram_alert_key_ref
    )
    telegram_alert_key_source = (
        campaign_summary.telegram_alert_key_source
        if campaign_summary is not None and campaign_summary.telegram_alert_key_source
        else runtime_evidence_bundle.telegram_alert_key_source
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.telegram_alert_key_source
        else state.last_telegram_alert_key_source or "not_configured"
    )
    execution_runtime_bootstrap_ref = (
        campaign_summary.execution_runtime_bootstrap_ref
        if campaign_summary is not None and campaign_summary.execution_runtime_bootstrap_ref
        else runtime_evidence_bundle.execution_runtime_bootstrap_ref
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.execution_runtime_bootstrap_ref
        else state.last_execution_runtime_bootstrap_ref
    )
    execution_runtime_bootstrap_status = (
        campaign_summary.execution_runtime_bootstrap_status
        if campaign_summary is not None
        and campaign_summary.execution_runtime_bootstrap_status
        and campaign_summary.execution_runtime_bootstrap_status != "not_configured"
        else runtime_evidence_bundle.execution_runtime_bootstrap_status
        if runtime_evidence_bundle is not None
        and runtime_evidence_bundle.execution_runtime_bootstrap_status
        and runtime_evidence_bundle.execution_runtime_bootstrap_status != "not_configured"
        else state.last_execution_runtime_bootstrap_status or "not_configured"
    )
    execution_runtime_bootstrap_source = (
        campaign_summary.execution_runtime_bootstrap_source
        if campaign_summary is not None and campaign_summary.execution_runtime_bootstrap_source
        else runtime_evidence_bundle.execution_runtime_bootstrap_source
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.execution_runtime_bootstrap_source
        else state.last_execution_runtime_bootstrap_source or "not_configured"
    )
    execution_runtime_gatekeeper_audit_ref = (
        campaign_summary.execution_runtime_gatekeeper_audit_ref
        if campaign_summary is not None and campaign_summary.execution_runtime_gatekeeper_audit_ref
        else runtime_evidence_bundle.execution_runtime_gatekeeper_audit_ref
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.execution_runtime_gatekeeper_audit_ref
        else state.last_execution_runtime_gatekeeper_audit_ref
    )
    execution_runtime_gatekeeper_audit_source = (
        campaign_summary.execution_runtime_gatekeeper_audit_source
        if campaign_summary is not None and campaign_summary.execution_runtime_gatekeeper_audit_source
        else runtime_evidence_bundle.execution_runtime_gatekeeper_audit_source
        if runtime_evidence_bundle is not None and runtime_evidence_bundle.execution_runtime_gatekeeper_audit_source
        else state.last_execution_runtime_gatekeeper_audit_source or "not_configured"
    )
    execution_runtime_bootstrap_user_data_stream_enabled = (
        campaign_summary.execution_runtime_bootstrap_user_data_stream_enabled
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_bootstrap_user_data_stream_enabled
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_bootstrap_reconciliation_boot_executed = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_executed
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_executed
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_bootstrap_reconciliation_boot_trading_blocked = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_bootstrap_reconciliation_boot_detail = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_detail
        if campaign_summary is not None
        and campaign_summary.execution_runtime_bootstrap_reconciliation_boot_detail
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_detail
        if runtime_evidence_bundle is not None
        else ""
    )
    execution_runtime_bootstrap_reconciliation_boot_recovery_action = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_recovery_action
        if campaign_summary is not None
        and campaign_summary.execution_runtime_bootstrap_reconciliation_boot_recovery_action
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_recovery_action
        if runtime_evidence_bundle is not None
        else ""
    )
    execution_runtime_bootstrap_reconciliation_boot_divergence_count = (
        campaign_summary.execution_runtime_bootstrap_reconciliation_boot_divergence_count
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_divergence_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_runtime_projection_status = (
        campaign_summary.execution_runtime_projection_status
        if campaign_summary is not None
        and campaign_summary.execution_runtime_projection_status
        else runtime_evidence_bundle.execution_runtime_projection_status
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    execution_runtime_projection_source = (
        campaign_summary.execution_runtime_projection_source
        if campaign_summary is not None
        and campaign_summary.execution_runtime_projection_source
        else runtime_evidence_bundle.execution_runtime_projection_source
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_assessment_source = (
        campaign_summary.regime_lite_assessment_source
        if campaign_summary is not None
        and campaign_summary.regime_lite_assessment_source
        else runtime_evidence_bundle.regime_lite_assessment_source
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_safing_recommendation_source = (
        campaign_summary.regime_lite_safing_recommendation_source
        if campaign_summary is not None
        and campaign_summary.regime_lite_safing_recommendation_source
        else runtime_evidence_bundle.regime_lite_safing_recommendation_source
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    info_stress_assessment_source = (
        campaign_summary.info_stress_assessment_source
        if campaign_summary is not None
        and campaign_summary.info_stress_assessment_source
        else runtime_evidence_bundle.info_stress_assessment_source
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    execution_runtime_projection_ready = (
        campaign_summary.execution_runtime_projection_ready
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_ready
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_projection_consumer_count = (
        campaign_summary.execution_runtime_projection_consumer_count
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_consumer_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_runtime_projection_ready_consumer_count = (
        campaign_summary.execution_runtime_projection_ready_consumer_count
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_ready_consumer_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_runtime_projection_partial_consumer_count = (
        campaign_summary.execution_runtime_projection_partial_consumer_count
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_partial_consumer_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_runtime_projection_blocked_consumer_count = (
        campaign_summary.execution_runtime_projection_blocked_consumer_count
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_blocked_consumer_count
        if runtime_evidence_bundle is not None
        else 0
    )
    execution_runtime_projection_bridge_status = (
        campaign_summary.execution_runtime_projection_bridge_status
        if campaign_summary is not None
        and campaign_summary.execution_runtime_projection_bridge_status
        else runtime_evidence_bundle.execution_runtime_projection_bridge_status
        if runtime_evidence_bundle is not None
        else "planned"
    )
    execution_runtime_projection_bridge_loaded = (
        campaign_summary.execution_runtime_projection_bridge_loaded
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_bridge_loaded
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_projection_rate_limit_model_loaded = (
        campaign_summary.execution_runtime_projection_rate_limit_model_loaded
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_rate_limit_model_loaded
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_projection_spread_guard_model_loaded = (
        campaign_summary.execution_runtime_projection_spread_guard_model_loaded
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_spread_guard_model_loaded
        if runtime_evidence_bundle is not None
        else False
    )
    execution_runtime_projection_slippage_model_loaded = (
        campaign_summary.execution_runtime_projection_slippage_model_loaded
        if campaign_summary is not None
        else runtime_evidence_bundle.execution_runtime_projection_slippage_model_loaded
        if runtime_evidence_bundle is not None
        else False
    )
    regime_lite_governance_status = (
        campaign_summary.regime_lite_governance_status
        if campaign_summary is not None
        and campaign_summary.regime_lite_governance_status
        else runtime_evidence_bundle.regime_lite_governance_status
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_state = (
        campaign_summary.regime_lite_state
        if campaign_summary is not None and campaign_summary.regime_lite_state
        else runtime_evidence_bundle.regime_lite_state
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_candidate_state = (
        campaign_summary.regime_lite_candidate_state
        if campaign_summary is not None
        and campaign_summary.regime_lite_candidate_state
        else runtime_evidence_bundle.regime_lite_candidate_state
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_entries_blocked = (
        campaign_summary.regime_lite_entries_blocked
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_entries_blocked
        if runtime_evidence_bundle is not None
        else False
    )
    regime_lite_sudden_event = (
        campaign_summary.regime_lite_sudden_event
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_sudden_event
        if runtime_evidence_bundle is not None
        else False
    )
    regime_lite_safing_severity = (
        campaign_summary.regime_lite_safing_severity
        if campaign_summary is not None
        and campaign_summary.regime_lite_safing_severity
        else runtime_evidence_bundle.regime_lite_safing_severity
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    regime_lite_safing_should_block_new_entries = (
        campaign_summary.regime_lite_safing_should_block_new_entries
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_should_block_new_entries
        if runtime_evidence_bundle is not None
        else False
    )
    regime_lite_safing_should_exit_all = (
        campaign_summary.regime_lite_safing_should_exit_all
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_should_exit_all
        if runtime_evidence_bundle is not None
        else False
    )
    regime_lite_safing_recommended_operator_action = (
        campaign_summary.regime_lite_safing_recommended_operator_action
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_recommended_operator_action
        if runtime_evidence_bundle is not None
        else ""
    )
    regime_lite_safing_operator_safing_request_action = (
        campaign_summary.regime_lite_safing_operator_safing_request_action
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_operator_safing_request_action
        if runtime_evidence_bundle is not None
        else ""
    )
    regime_lite_safing_operator_safing_request_source_runtime_mode = (
        campaign_summary.regime_lite_safing_operator_safing_request_source_runtime_mode
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_operator_safing_request_source_runtime_mode
        if runtime_evidence_bundle is not None
        else ""
    )
    regime_lite_safing_reason_codes = (
        campaign_summary.regime_lite_safing_reason_codes
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_reason_codes
        if runtime_evidence_bundle is not None
        else ()
    )
    regime_lite_safing_detail = (
        campaign_summary.regime_lite_safing_detail
        if campaign_summary is not None
        else runtime_evidence_bundle.regime_lite_safing_detail
        if runtime_evidence_bundle is not None
        else ""
    )
    info_stress_governance_status = (
        campaign_summary.info_stress_governance_status
        if campaign_summary is not None
        and campaign_summary.info_stress_governance_status
        else runtime_evidence_bundle.info_stress_governance_status
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    info_stress_level = (
        campaign_summary.info_stress_level
        if campaign_summary is not None
        and campaign_summary.info_stress_level
        else runtime_evidence_bundle.info_stress_level
        if runtime_evidence_bundle is not None
        else "not_configured"
    )
    info_stress_alert_count = (
        campaign_summary.info_stress_alert_count
        if campaign_summary is not None
        else runtime_evidence_bundle.info_stress_alert_count
        if runtime_evidence_bundle is not None
        else 0
    )
    info_stress_entries_blocked = (
        campaign_summary.info_stress_entries_blocked
        if campaign_summary is not None
        else runtime_evidence_bundle.info_stress_entries_blocked
        if runtime_evidence_bundle is not None
        else False
    )
    info_stress_entries_blocked_until_ts = (
        campaign_summary.info_stress_entries_blocked_until_ts
        if campaign_summary is not None
        else runtime_evidence_bundle.info_stress_entries_blocked_until_ts
        if runtime_evidence_bundle is not None
        else 0
    )
    info_stress_reason_codes = (
        campaign_summary.info_stress_reason_codes
        if campaign_summary is not None
        else runtime_evidence_bundle.info_stress_reason_codes
        if runtime_evidence_bundle is not None
        else ()
    )
    info_stress_detail = (
        campaign_summary.info_stress_detail
        if campaign_summary is not None
        else runtime_evidence_bundle.info_stress_detail
        if runtime_evidence_bundle is not None
        else ""
    )

    detail = (
        f"status={state.service_status.value} / "
        f"loops={state.loop_count} / "
        f"source={runtime_data_source} / "
        f"exec_telemetry={execution_telemetry_status} / "
        f"telegram={telegram_alert_delivery_status}"
        f"@{telegram_alert_delivery_event_type or 'none'}"
        f"@{telegram_alert_config_source} / "
        f"exec_bootstrap={execution_runtime_bootstrap_status}"
        f"@{execution_runtime_bootstrap_source}"
        f"@{execution_runtime_gatekeeper_audit_source}"
        f"/div={execution_runtime_bootstrap_reconciliation_boot_divergence_count} / "
        f"exec_projection={execution_runtime_projection_status}@{execution_runtime_projection_source} / "
        f"regime_lite={regime_lite_safing_severity}@{regime_lite_state}"
        f"@{regime_lite_assessment_source}/{regime_lite_safing_recommendation_source} / "
        f"info_stress={info_stress_governance_status}@{info_stress_level}"
        f"@{info_stress_assessment_source} / "
        f"exec_bridge={execution_runtime_projection_bridge_status} / "
        f"cpu={process.cpu_pct:.1f}% / ram={process.ram_pct:.1f}% / "
        f"disk_used={disk.used_pct:.1f}%"
    )

    return ShadowVpsServiceMonitoringPayload(
        timestamp_ms=timestamp_ms,
        correlation_id="shadow-vps-service",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status=_projection_status_from_state(state),
        detail=detail,
        service_status=state.service_status.value,
        heartbeat_age_ms=heartbeat_age_ms,
        loop_count=state.loop_count,
        success_count=state.success_count,
        idle_count=state.idle_count,
        failure_count=state.failure_count,
        resumed=state.resumed,
        acquisition_mode=acquisition_mode,
        runtime_data_source=runtime_data_source,
        accepted=accepted,
        consecutive_days=consecutive_days,
        remaining_days=remaining_days,
        promotion_gate_passed=promotion_gate_passed,
        live_capture_emitted_message_count=live_capture_emitted_message_count,
        live_capture_accepted_message_count=live_capture_accepted_message_count,
        live_capture_rejected_message_count=live_capture_rejected_message_count,
        live_user_data_authenticated=live_user_data_authenticated,
        live_user_data_event_count=live_user_data_event_count,
        last_selected_session_date=state.last_selected_session_date,
        last_completed_session_date=state.last_completed_session_date,
        last_error=state.last_error,
        state_path=state_path,
        events_path=events_path,
        campaign_summary_ref=state.last_campaign_summary_ref,
        runtime_evidence_bundle_ref=state.last_runtime_evidence_bundle_ref,
        execution_telemetry_ref=state.last_execution_telemetry_ref,
        execution_telemetry_status=execution_telemetry_status,
        telegram_alert_delivery_status=telegram_alert_delivery_status,
        telegram_alert_delivery_event_type=telegram_alert_delivery_event_type,
        telegram_alert_delivery_error=telegram_alert_delivery_error,
        telegram_alert_config_ref=telegram_alert_config_ref,
        telegram_alert_config_source=telegram_alert_config_source,
        telegram_alert_key_ref=telegram_alert_key_ref,
        telegram_alert_key_source=telegram_alert_key_source,
        execution_runtime_bootstrap_ref=execution_runtime_bootstrap_ref,
        execution_runtime_bootstrap_status=execution_runtime_bootstrap_status,
        execution_runtime_bootstrap_source=execution_runtime_bootstrap_source,
        execution_runtime_gatekeeper_audit_ref=execution_runtime_gatekeeper_audit_ref,
        execution_runtime_gatekeeper_audit_source=(
            execution_runtime_gatekeeper_audit_source
        ),
        execution_runtime_bootstrap_user_data_stream_enabled=(
            execution_runtime_bootstrap_user_data_stream_enabled
        ),
        execution_runtime_bootstrap_reconciliation_boot_executed=(
            execution_runtime_bootstrap_reconciliation_boot_executed
        ),
        execution_runtime_bootstrap_reconciliation_boot_trading_blocked=(
            execution_runtime_bootstrap_reconciliation_boot_trading_blocked
        ),
        execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped=(
            execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
        ),
        execution_runtime_bootstrap_reconciliation_boot_detail=(
            execution_runtime_bootstrap_reconciliation_boot_detail
        ),
        execution_runtime_bootstrap_reconciliation_boot_recovery_action=(
            execution_runtime_bootstrap_reconciliation_boot_recovery_action
        ),
        execution_runtime_bootstrap_reconciliation_boot_divergence_count=(
            execution_runtime_bootstrap_reconciliation_boot_divergence_count
        ),
        execution_runtime_projection_ref=state.last_execution_runtime_projection_ref,
        execution_runtime_projection_source=(
            state.last_execution_runtime_projection_source or "not_configured"
        ),
        regime_lite_assessment_ref=state.last_regime_lite_assessment_ref,
        regime_lite_assessment_source=(
            state.last_regime_lite_assessment_source or regime_lite_assessment_source
        ),
        regime_lite_safing_recommendation_ref=(
            state.last_regime_lite_safing_recommendation_ref
        ),
        regime_lite_safing_recommendation_source=(
            state.last_regime_lite_safing_recommendation_source
            or regime_lite_safing_recommendation_source
        ),
        info_stress_assessment_ref=state.last_info_stress_assessment_ref,
        info_stress_assessment_source=(
            state.last_info_stress_assessment_source or info_stress_assessment_source
        ),
        execution_runtime_projection_status=execution_runtime_projection_status,
        execution_runtime_projection_ready=execution_runtime_projection_ready,
        execution_runtime_projection_consumer_count=(
            execution_runtime_projection_consumer_count
        ),
        execution_runtime_projection_ready_consumer_count=(
            execution_runtime_projection_ready_consumer_count
        ),
        execution_runtime_projection_partial_consumer_count=(
            execution_runtime_projection_partial_consumer_count
        ),
        execution_runtime_projection_blocked_consumer_count=(
            execution_runtime_projection_blocked_consumer_count
        ),
        execution_runtime_projection_bridge_status=(
            execution_runtime_projection_bridge_status
        ),
        execution_runtime_projection_bridge_loaded=(
            execution_runtime_projection_bridge_loaded
        ),
        execution_runtime_projection_rate_limit_model_loaded=(
            execution_runtime_projection_rate_limit_model_loaded
        ),
        execution_runtime_projection_spread_guard_model_loaded=(
            execution_runtime_projection_spread_guard_model_loaded
        ),
        execution_runtime_projection_slippage_model_loaded=(
            execution_runtime_projection_slippage_model_loaded
        ),
        regime_lite_governance_status=regime_lite_governance_status,
        regime_lite_state=regime_lite_state,
        regime_lite_candidate_state=regime_lite_candidate_state,
        regime_lite_entries_blocked=regime_lite_entries_blocked,
        regime_lite_sudden_event=regime_lite_sudden_event,
        regime_lite_safing_severity=regime_lite_safing_severity,
        regime_lite_safing_should_block_new_entries=(
            regime_lite_safing_should_block_new_entries
        ),
        regime_lite_safing_should_exit_all=regime_lite_safing_should_exit_all,
        regime_lite_safing_recommended_operator_action=(
            regime_lite_safing_recommended_operator_action
        ),
        regime_lite_safing_operator_safing_request_action=(
            regime_lite_safing_operator_safing_request_action
        ),
        regime_lite_safing_operator_safing_request_source_runtime_mode=(
            regime_lite_safing_operator_safing_request_source_runtime_mode
        ),
        regime_lite_safing_reason_codes=regime_lite_safing_reason_codes,
        regime_lite_safing_detail=regime_lite_safing_detail,
        info_stress_governance_status=info_stress_governance_status,
        info_stress_level=info_stress_level,
        info_stress_alert_count=info_stress_alert_count,
        info_stress_entries_blocked=info_stress_entries_blocked,
        info_stress_entries_blocked_until_ts=info_stress_entries_blocked_until_ts,
        info_stress_reason_codes=info_stress_reason_codes,
        info_stress_detail=info_stress_detail,
        export_dir_ref=state.last_export_dir_ref,
        recent_events_summary_ref=recent_events_summary_ref,
        node_exporter_textfile_ref=node_exporter_textfile_ref,
        scrape_manifest_ref=scrape_manifest_ref,
        prometheus_file_sd_ref=prometheus_file_sd_ref,
        process=process,
        disk=disk,
    )


def build_shadow_vps_service_observability_export(
    payload: ShadowVpsServiceMonitoringPayload,
) -> ObservabilityExport:
    """Emit a compact Prometheus-style export for the real Shadow VPS service."""

    base_labels = {
        "correlation_id": payload.correlation_id,
        "profile": payload.profile.value,
        "runtime_mode": payload.runtime_mode.value,
    }
    samples = (
        _sample(
            "v53_shadow_vps_service_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "status": payload.service_status,
                "acquisition_mode": payload.acquisition_mode,
                "runtime_data_source": payload.runtime_data_source,
            },
        ),
        _sample(
            "v53_shadow_vps_service_heartbeat_age_ms",
            kind="gauge",
            value=float(payload.heartbeat_age_ms),
            unit="ms",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_loop_count",
            kind="counter",
            value=float(payload.loop_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_success_count",
            kind="counter",
            value=float(payload.success_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_idle_count",
            kind="counter",
            value=float(payload.idle_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_failure_count",
            kind="counter",
            value=float(payload.failure_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_promotion_gate_passed",
            kind="state",
            value=1.0 if payload.promotion_gate_passed else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_live_capture_accepted_message_count",
            kind="gauge",
            value=float(payload.live_capture_accepted_message_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_live_user_data_authenticated",
            kind="state",
            value=1.0 if payload.live_user_data_authenticated else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_telemetry_ready",
            kind="state",
            value=1.0 if payload.execution_telemetry_status == "written" else 0.0,
            labels={
                **base_labels,
                "telemetry_status": payload.execution_telemetry_status,
                "acquisition_mode": payload.acquisition_mode,
            },
        ),
        _sample(
            "v53_shadow_vps_telegram_alert_delivery_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "delivery_status": payload.telegram_alert_delivery_status,
                "alert_event_type": (
                    payload.telegram_alert_delivery_event_type or "none"
                ),
                "config_source": payload.telegram_alert_config_source,
                "error_present": (
                    "true" if bool(payload.telegram_alert_delivery_error) else "false"
                ),
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_status",
            kind="state",
            value=1.0 if payload.execution_runtime_bootstrap_status == "ready" else 0.0,
            labels={
                **base_labels,
                "bootstrap_status": payload.execution_runtime_bootstrap_status,
                "bootstrap_source": payload.execution_runtime_bootstrap_source,
                "gatekeeper_audit_source": payload.execution_runtime_gatekeeper_audit_source,
                "user_data_stream_enabled": (
                    "true"
                    if payload.execution_runtime_bootstrap_user_data_stream_enabled
                    else "false"
                ),
                "reconciliation_executed": (
                    "true"
                    if payload.execution_runtime_bootstrap_reconciliation_boot_executed
                    else "false"
                ),
                "trading_blocked": (
                    "true"
                    if payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
                    else "false"
                ),
                "circuit_breaker_tripped": (
                    "true"
                    if payload.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
                    else "false"
                ),
                "recovery_action": (
                    payload.execution_runtime_bootstrap_reconciliation_boot_recovery_action
                    or "none"
                ),
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_divergence_count",
            kind="gauge",
            value=float(
                payload.execution_runtime_bootstrap_reconciliation_boot_divergence_count
            ),
            unit="count",
            labels={
                **base_labels,
                "bootstrap_status": payload.execution_runtime_bootstrap_status,
                "bootstrap_source": payload.execution_runtime_bootstrap_source,
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_trading_blocked",
            kind="state",
            value=1.0
            if payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
            else 0.0,
            labels={
                **base_labels,
                "bootstrap_status": payload.execution_runtime_bootstrap_status,
                "bootstrap_source": payload.execution_runtime_bootstrap_source,
                "gatekeeper_audit_source": payload.execution_runtime_gatekeeper_audit_source,
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_ready",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_ready else 0.0,
            labels={
                **base_labels,
                "projection_status": payload.execution_runtime_projection_status,
                "projection_source": payload.execution_runtime_projection_source,
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_bridge_loaded",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_bridge_loaded else 0.0,
            labels={
                **base_labels,
                "bridge_status": payload.execution_runtime_projection_bridge_status,
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_ready_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_ready_consumer_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_rate_limit_model_loaded",
            kind="state",
            value=1.0
            if payload.execution_runtime_projection_rate_limit_model_loaded
            else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_spread_guard_model_loaded",
            kind="state",
            value=1.0
            if payload.execution_runtime_projection_spread_guard_model_loaded
            else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_slippage_model_loaded",
            kind="state",
            value=1.0
            if payload.execution_runtime_projection_slippage_model_loaded
            else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_partial_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_partial_consumer_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_blocked_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_blocked_consumer_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_regime_lite_safing_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "governance_status": payload.regime_lite_governance_status,
                "severity": payload.regime_lite_safing_severity,
                "state": payload.regime_lite_state,
                "candidate_state": payload.regime_lite_candidate_state,
                "assessment_source": payload.regime_lite_assessment_source,
                "safing_source": payload.regime_lite_safing_recommendation_source,
                "recommended_action": (
                    payload.regime_lite_safing_recommended_operator_action or "none"
                ),
            },
        ),
        _sample(
            "v53_shadow_vps_regime_lite_entries_blocked",
            kind="state",
            value=1.0 if payload.regime_lite_entries_blocked else 0.0,
            labels={
                **base_labels,
                "governance_status": payload.regime_lite_governance_status,
                "severity": payload.regime_lite_safing_severity,
                "assessment_source": payload.regime_lite_assessment_source,
                "safing_source": payload.regime_lite_safing_recommendation_source,
            },
        ),
        _sample(
            "v53_shadow_vps_regime_lite_should_exit_all",
            kind="state",
            value=1.0 if payload.regime_lite_safing_should_exit_all else 0.0,
            labels={
                **base_labels,
                "governance_status": payload.regime_lite_governance_status,
                "severity": payload.regime_lite_safing_severity,
                "assessment_source": payload.regime_lite_assessment_source,
                "safing_source": payload.regime_lite_safing_recommendation_source,
            },
        ),
        _sample(
            "v53_shadow_vps_info_stress_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "governance_status": payload.info_stress_governance_status,
                "level": payload.info_stress_level,
                "assessment_source": payload.info_stress_assessment_source,
            },
        ),
        _sample(
            "v53_shadow_vps_info_stress_alert_count",
            kind="gauge",
            value=float(payload.info_stress_alert_count),
            unit="count",
            labels={
                **base_labels,
                "governance_status": payload.info_stress_governance_status,
                "level": payload.info_stress_level,
            },
        ),
        _sample(
            "v53_shadow_vps_info_stress_entries_blocked",
            kind="state",
            value=1.0 if payload.info_stress_entries_blocked else 0.0,
            labels={
                **base_labels,
                "governance_status": payload.info_stress_governance_status,
                "level": payload.info_stress_level,
                "assessment_source": payload.info_stress_assessment_source,
            },
        ),
        _sample(
            "v53_shadow_vps_process_cpu_pct",
            kind="gauge",
            value=payload.process.cpu_pct,
            unit="pct",
            labels={**base_labels, "pid": str(payload.process.pid), "mode": payload.process.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_process_ram_pct",
            kind="gauge",
            value=payload.process.ram_pct,
            unit="pct",
            labels={**base_labels, "pid": str(payload.process.pid), "mode": payload.process.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_process_rss_mb",
            kind="gauge",
            value=payload.process.rss_mb,
            unit="mb",
            labels={**base_labels, "pid": str(payload.process.pid), "mode": payload.process.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_process_thread_count",
            kind="gauge",
            value=float(payload.process.thread_count),
            unit="count",
            labels={**base_labels, "pid": str(payload.process.pid), "mode": payload.process.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_disk_used_pct",
            kind="gauge",
            value=payload.disk.used_pct,
            unit="pct",
            labels={**base_labels, "path": payload.disk.path, "mode": payload.disk.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_disk_free_gb",
            kind="gauge",
            value=payload.disk.free_gb,
            unit="gb",
            labels={**base_labels, "path": payload.disk.path, "mode": payload.disk.sampling_mode},
        ),
        _sample(
            "v53_shadow_vps_service_last_error_present",
            kind="state",
            value=1.0 if payload.last_error else 0.0,
            labels=base_labels,
        ),
    )
    lines = ["# V5.3 Shadow VPS service observability export"]
    for sample in samples:
        label_text = ""
        if sample.labels:
            joined = ",".join(f'{key}="{value}"' for key, value in sorted(sample.labels.items()))
            label_text = f"{{{joined}}}"
        lines.append(f"{sample.name}{label_text} {sample.value}")

    return ObservabilityExport(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        samples=samples,
        text_payload="\n".join(lines),
    )


__all__ = [
    "build_shadow_vps_service_monitoring_payload",
    "build_shadow_vps_service_observability_export",
]
