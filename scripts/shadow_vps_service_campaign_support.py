#!/usr/bin/env python3
"""Campaign summary helpers for the Shadow VPS service."""

from __future__ import annotations

from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from interface_contracts.shadow_vps_service_contracts import ShadowVpsServiceState
from protocols import ShadowVpsCampaignSummary, ShadowVpsRuntimeEvidenceBundle


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
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)
    return summary_path
