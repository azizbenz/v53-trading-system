"""Support helpers for Shadow VPS service monitoring payload construction."""

from __future__ import annotations

from typing import TypeVar

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
)
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.shadow_vps_service_monitoring_payload_field_support import (
    resolve_bootstrap_fields,
    resolve_projection_fields,
)


T = TypeVar("T")


def _prefer_value(primary: T | None, secondary: T | None, default: T) -> T:
    if primary is not None:
        return primary
    if secondary is not None:
        return secondary
    return default


def _prefer_text(
    primary: str | None,
    secondary: str | None,
    default: str,
    *,
    disallowed: tuple[str, ...] = (),
) -> str:
    for value in (primary, secondary):
        if value and value not in disallowed:
            return value
    return default


def _prefer_optional_text(primary: str | None, secondary: str | None) -> str:
    for value in (primary, secondary):
        if value:
            return value
    return ""


def _projection_status_from_state(state: ShadowVpsServiceState) -> str:
    if state.dashboard_control_halted:
        return "critical"
    if state.dashboard_control_target_deployment_state == "rollback":
        return "warning"
    if state.service_status.value == "degraded":
        return "critical"
    if state.last_error:
        return "warning"
    if state.service_status.value in {"idle", "stopped"}:
        return "info"
    return "healthy"


def _resolve_campaign_runtime_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    accepted = _prefer_value(
        campaign_summary.accepted if campaign_summary is not None else None,
        runtime_evidence_bundle.accepted if runtime_evidence_bundle is not None else None,
        False,
    )
    remaining_days = _prefer_value(
        campaign_summary.remaining_days if campaign_summary is not None else None,
        runtime_evidence_bundle.remaining_days if runtime_evidence_bundle is not None else None,
        0,
    )
    return {
        "acquisition_mode": _prefer_text(
            campaign_summary.acquisition_mode if campaign_summary is not None else None,
            runtime_evidence_bundle.acquisition_mode if runtime_evidence_bundle is not None else None,
            "unknown",
        ),
        "runtime_data_source": _prefer_text(
            campaign_summary.runtime_data_source if campaign_summary is not None else None,
            runtime_evidence_bundle.runtime_data_source if runtime_evidence_bundle is not None else None,
            "unknown",
        ),
        "accepted": accepted,
        "consecutive_days": _prefer_value(
            campaign_summary.consecutive_days if campaign_summary is not None else None,
            runtime_evidence_bundle.consecutive_days if runtime_evidence_bundle is not None else None,
            0,
        ),
        "remaining_days": remaining_days,
        "promotion_gate_passed": (
            campaign_summary.promotion_gate_passed
            if campaign_summary is not None
            else bool(accepted and remaining_days == 0)
        ),
        "live_capture_emitted_message_count": _prefer_value(
            campaign_summary.live_capture_emitted_message_count if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.live_capture_emitted_message_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "live_capture_accepted_message_count": _prefer_value(
            campaign_summary.live_capture_accepted_message_count if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.live_capture_accepted_message_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "live_capture_rejected_message_count": _prefer_value(
            campaign_summary.live_capture_rejected_message_count if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.live_capture_rejected_message_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "live_user_data_authenticated": _prefer_value(
            campaign_summary.live_user_data_authenticated if campaign_summary is not None else None,
            runtime_evidence_bundle.live_user_data_authenticated if runtime_evidence_bundle is not None else None,
            False,
        ),
        "live_user_data_event_count": _prefer_value(
            campaign_summary.live_user_data_event_count if campaign_summary is not None else None,
            runtime_evidence_bundle.live_user_data_event_count if runtime_evidence_bundle is not None else None,
            0,
        ),
    }


def _resolve_telemetry_and_telegram_fields(
    state: ShadowVpsServiceState,
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_telemetry_status": _prefer_text(
            campaign_summary.execution_telemetry_status if campaign_summary is not None else None,
            state.last_execution_telemetry_status,
            "not_configured",
            disallowed=("not_configured",),
        ),
        "telegram_alert_delivery_status": _prefer_text(
            campaign_summary.telegram_alert_delivery_status if campaign_summary is not None else None,
            state.last_telegram_alert_delivery_status,
            "not_configured",
            disallowed=("not_configured",),
        ),
        "telegram_alert_delivery_event_type": _prefer_optional_text(
            (
                campaign_summary.telegram_alert_delivery_event_type
                if campaign_summary is not None
                else None
            ),
            state.last_telegram_alert_delivery_event_type,
        ),
        "telegram_alert_delivery_error": _prefer_optional_text(
            campaign_summary.telegram_alert_delivery_error if campaign_summary is not None else None,
            state.last_telegram_alert_delivery_error,
        ),
        "telegram_alert_config_ref": _prefer_optional_text(
            campaign_summary.telegram_alert_config_ref if campaign_summary is not None else None,
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.telegram_alert_config_ref
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_telegram_alert_config_ref,
            ),
        ),
        "telegram_alert_config_source": _prefer_text(
            campaign_summary.telegram_alert_config_source if campaign_summary is not None else None,
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.telegram_alert_config_source
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_telegram_alert_config_source,
            ),
            "not_configured",
        ),
        "telegram_alert_key_ref": _prefer_optional_text(
            campaign_summary.telegram_alert_key_ref if campaign_summary is not None else None,
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.telegram_alert_key_ref
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_telegram_alert_key_ref,
            ),
        ),
        "telegram_alert_key_source": _prefer_text(
            campaign_summary.telegram_alert_key_source if campaign_summary is not None else None,
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.telegram_alert_key_source
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_telegram_alert_key_source,
            ),
            "not_configured",
        ),
    }


def _resolve_regime_lite_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "regime_lite_governance_status": _prefer_text(
            campaign_summary.regime_lite_governance_status if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_governance_status if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "regime_lite_state": _prefer_text(
            campaign_summary.regime_lite_state if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_state if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "regime_lite_candidate_state": _prefer_text(
            campaign_summary.regime_lite_candidate_state if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_candidate_state if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "regime_lite_entries_blocked": _prefer_value(
            campaign_summary.regime_lite_entries_blocked if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_entries_blocked if runtime_evidence_bundle is not None else None,
            False,
        ),
        "regime_lite_sudden_event": _prefer_value(
            campaign_summary.regime_lite_sudden_event if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_sudden_event if runtime_evidence_bundle is not None else None,
            False,
        ),
        "regime_lite_safing_severity": _prefer_text(
            campaign_summary.regime_lite_safing_severity if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_safing_severity if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "regime_lite_safing_should_block_new_entries": _prefer_value(
            (
                campaign_summary.regime_lite_safing_should_block_new_entries
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.regime_lite_safing_should_block_new_entries
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "regime_lite_safing_should_exit_all": _prefer_value(
            campaign_summary.regime_lite_safing_should_exit_all if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_safing_should_exit_all if runtime_evidence_bundle is not None else None,
            False,
        ),
        "regime_lite_safing_recommended_operator_action": _prefer_value(
            (
                campaign_summary.regime_lite_safing_recommended_operator_action
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.regime_lite_safing_recommended_operator_action
                if runtime_evidence_bundle is not None
                else None
            ),
            "",
        ),
        "regime_lite_safing_operator_safing_request_action": _prefer_value(
            (
                campaign_summary.regime_lite_safing_operator_safing_request_action
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.regime_lite_safing_operator_safing_request_action
                if runtime_evidence_bundle is not None
                else None
            ),
            "",
        ),
        "regime_lite_safing_operator_safing_request_source_runtime_mode": _prefer_value(
            (
                campaign_summary.regime_lite_safing_operator_safing_request_source_runtime_mode
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.regime_lite_safing_operator_safing_request_source_runtime_mode
                if runtime_evidence_bundle is not None
                else None
            ),
            "",
        ),
        "regime_lite_safing_reason_codes": _prefer_value(
            campaign_summary.regime_lite_safing_reason_codes if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_safing_reason_codes if runtime_evidence_bundle is not None else None,
            (),
        ),
        "regime_lite_safing_detail": _prefer_value(
            campaign_summary.regime_lite_safing_detail if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_safing_detail if runtime_evidence_bundle is not None else None,
            "",
        ),
    }


def _resolve_info_stress_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "info_stress_governance_status": _prefer_text(
            campaign_summary.info_stress_governance_status if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_governance_status if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "info_stress_level": _prefer_text(
            campaign_summary.info_stress_level if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_level if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "info_stress_alert_count": _prefer_value(
            campaign_summary.info_stress_alert_count if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_alert_count if runtime_evidence_bundle is not None else None,
            0,
        ),
        "info_stress_entries_blocked": _prefer_value(
            campaign_summary.info_stress_entries_blocked if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_entries_blocked if runtime_evidence_bundle is not None else None,
            False,
        ),
        "info_stress_entries_blocked_until_ts": _prefer_value(
            campaign_summary.info_stress_entries_blocked_until_ts if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.info_stress_entries_blocked_until_ts
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "info_stress_reason_codes": _prefer_value(
            campaign_summary.info_stress_reason_codes if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_reason_codes if runtime_evidence_bundle is not None else None,
            (),
        ),
        "info_stress_detail": _prefer_value(
            campaign_summary.info_stress_detail if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_detail if runtime_evidence_bundle is not None else None,
            "",
        ),
    }


def _build_detail(
    state: ShadowVpsServiceState,
    process: ProcessMetricsSample,
    disk: DiskUsageSample,
    resolved_fields: dict[str, object],
) -> str:
    return (
        f"status={state.service_status.value} / "
        f"loops={state.loop_count} / "
        f"source={resolved_fields['runtime_data_source']} / "
        f"exec_telemetry={resolved_fields['execution_telemetry_status']} / "
        f"telegram={resolved_fields['telegram_alert_delivery_status']}"
        f"@{resolved_fields['telegram_alert_delivery_event_type'] or 'none'}"
        f"@{resolved_fields['telegram_alert_config_source']} / "
        f"exec_bootstrap={resolved_fields['execution_runtime_bootstrap_status']}"
        f"@{resolved_fields['execution_runtime_bootstrap_source']}"
        f"@{resolved_fields['execution_runtime_gatekeeper_audit_source']}"
        f"/div={resolved_fields['execution_runtime_bootstrap_reconciliation_boot_divergence_count']}"
        f"/remote_orders={resolved_fields['execution_runtime_bootstrap_remote_open_order_count']}"
        f"/remote_positions={resolved_fields['execution_runtime_bootstrap_remote_position_asset_count']} / "
        f"recovery={resolved_fields['vps_recovery_status']}"
        f"/warmup={resolved_fields['vps_warmup_final_state']} / "
        f"dashboard_halted={resolved_fields['dashboard_control_halted']}"
        f"/target={resolved_fields['dashboard_control_target_profile'] or 'none'}"
        f":{resolved_fields['dashboard_control_target_deployment_state'] or 'none'}"
        f"/pair_susp={resolved_fields['dashboard_control_suspended_pair_count']}"
        f"/engine_susp={resolved_fields['dashboard_control_suspended_engine_count']} / "
        f"artifacts=ml:{resolved_fields['active_ml_artifact_hash'][:12] or 'none'}"
        f"/regime:{resolved_fields['active_regime_detector_artifact_hash'][:12] or 'none'} / "
        f"exec_projection={resolved_fields['execution_runtime_projection_status']}"
        f"@{resolved_fields['execution_runtime_projection_source_detail']} / "
        f"regime_lite={resolved_fields['regime_lite_safing_severity']}"
        f"@{resolved_fields['regime_lite_state']}"
        f"@{resolved_fields['regime_lite_assessment_source']}"
        f"/{resolved_fields['regime_lite_safing_recommendation_source']} / "
        f"info_stress={resolved_fields['info_stress_governance_status']}"
        f"@{resolved_fields['info_stress_level']}"
        f"@{resolved_fields['info_stress_assessment_source']} / "
        f"exec_bridge={resolved_fields['execution_runtime_projection_bridge_status']} / "
        f"cpu={process.cpu_pct:.1f}% / ram={process.ram_pct:.1f}% / "
        f"disk_used={disk.used_pct:.1f}%"
    )


def build_shadow_vps_service_monitoring_payload_support(
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
    """Build the typed payload projected from service state and campaign evidence."""

    heartbeat_age_ms = 0
    if state.last_heartbeat_at is not None:
        heartbeat_age_ms = max(0, int(timestamp_ms - int(state.last_heartbeat_at * 1000.0)))

    resolved_fields: dict[str, object] = {}
    resolved_fields.update(_resolve_campaign_runtime_fields(campaign_summary, runtime_evidence_bundle))
    resolved_fields.update(
        _resolve_telemetry_and_telegram_fields(state, campaign_summary, runtime_evidence_bundle)
    )
    resolved_fields.update(resolve_bootstrap_fields(state, campaign_summary, runtime_evidence_bundle))
    resolved_fields.update(resolve_projection_fields(campaign_summary, runtime_evidence_bundle))
    resolved_fields.update(_resolve_regime_lite_fields(campaign_summary, runtime_evidence_bundle))
    resolved_fields.update(_resolve_info_stress_fields(campaign_summary, runtime_evidence_bundle))

    detail = _build_detail(state, process, disk, resolved_fields)
    resolved_fields.pop("execution_runtime_projection_source_detail", None)

    payload_fields: dict[str, object] = {
        "timestamp_ms": timestamp_ms,
        "correlation_id": "shadow-vps-service",
        "profile": ProfileId.COMPLETE,
        "runtime_mode": RuntimeMode.SHADOW,
        "status": _projection_status_from_state(state),
        "detail": detail,
        "service_status": state.service_status.value,
        "heartbeat_age_ms": heartbeat_age_ms,
        "loop_count": state.loop_count,
        "success_count": state.success_count,
        "idle_count": state.idle_count,
        "failure_count": state.failure_count,
        "resumed": state.resumed,
        "last_selected_session_date": state.last_selected_session_date,
        "last_completed_session_date": state.last_completed_session_date,
        "last_error": state.last_error,
        "state_path": state_path,
        "events_path": events_path,
        "campaign_summary_ref": state.last_campaign_summary_ref,
        "runtime_evidence_bundle_ref": state.last_runtime_evidence_bundle_ref,
        "execution_telemetry_ref": state.last_execution_telemetry_ref,
        "execution_runtime_projection_ref": state.last_execution_runtime_projection_ref,
        "execution_runtime_projection_source": (
            state.last_execution_runtime_projection_source or "not_configured"
        ),
        "regime_lite_assessment_ref": state.last_regime_lite_assessment_ref,
        "regime_lite_assessment_source": (
            state.last_regime_lite_assessment_source
            or resolved_fields["regime_lite_assessment_source"]
        ),
        "regime_lite_safing_recommendation_ref": state.last_regime_lite_safing_recommendation_ref,
        "regime_lite_safing_recommendation_source": (
            state.last_regime_lite_safing_recommendation_source
            or resolved_fields["regime_lite_safing_recommendation_source"]
        ),
        "info_stress_assessment_ref": state.last_info_stress_assessment_ref,
        "info_stress_assessment_source": (
            state.last_info_stress_assessment_source
            or resolved_fields["info_stress_assessment_source"]
        ),
        "export_dir_ref": state.last_export_dir_ref,
        "recent_events_summary_ref": recent_events_summary_ref,
        "node_exporter_textfile_ref": node_exporter_textfile_ref,
        "scrape_manifest_ref": scrape_manifest_ref,
        "prometheus_file_sd_ref": prometheus_file_sd_ref,
        "process": process,
        "disk": disk,
    }
    payload_fields.update(resolved_fields)
    return ShadowVpsServiceMonitoringPayload(**payload_fields)
