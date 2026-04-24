#!/usr/bin/env python3
"""Projection helpers for the Shadow VPS service."""

from __future__ import annotations

import json
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    ShadowLiveWebSocketCaptureResult,
    ShadowVpsRawInputSlot,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsWebsocketInputSlot,
)


def _read_optional_json(path_ref: str) -> dict:
    if not path_ref:
        return {}
    try:
        return json.loads(Path(path_ref).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


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
    atomic_write_json(bundle_path, bundle.model_dump(mode="json"), indent=2)
    return bundle_path
