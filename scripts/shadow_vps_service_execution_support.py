#!/usr/bin/env python3
"""Execution cycle helpers for the Shadow VPS service."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from protocols import ShadowVpsServiceEvent, ShadowVpsServiceStatus
from shadow_vps_service_artifact_support import (
    _persist_shadow_artifact_comparison_evidence,
)
from shadow_vps_service_models import (
    ShadowVpsCycleSelection,
    ShadowVpsServiceRuntimeContext,
)

WriteRuntimeEvidenceBundle = Callable[..., Path]
ReadRuntimeEvidenceBundle = Callable[[str], object | None]
WriteCampaignSummary = Callable[..., Path]
WriteServiceMonitoring = Callable[[ShadowVpsServiceRuntimeContext], None]
AppendServiceEvent = Callable[..., None]
ReadLastRun = Callable[[Path], dict]
RunDailyOrchestrator = Callable[..., int]
WriteExecutionTelemetry = Callable[..., tuple[str, Path | None]]
LastRunStr = Callable[[dict, str, str | None], str]


def _run_shadow_vps_daily_orchestrator(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    *,
    run_daily_orchestrator: RunDailyOrchestrator,
    read_last_run: ReadLastRun,
    augment_last_run_with_operated_metadata: Callable[..., None],
) -> dict:
    if selection.next_slot is None:
        raise ValueError("selected cycle requires a governed slot")
    exit_code = run_daily_orchestrator(
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
    last_run = read_last_run(context.resolved_orchestrator_output_dir)
    augment_last_run_with_operated_metadata(
        context=context,
        selection=selection,
        last_run=last_run,
    )
    return last_run


def _apply_last_run_to_shadow_vps_state(
    context: ShadowVpsServiceRuntimeContext,
    last_run: dict,
    runtime_evidence_bundle_path: Path,
    *,
    last_run_str: Callable[[dict, str, str], str],
) -> None:
    state = context.store.state
    state.last_export_dir_ref = last_run_str(last_run, "export_dir_ref", "")
    state.last_local_replay_evidence_ref = last_run_str(
        last_run, "local_replay_evidence_ref", ""
    )
    state.last_shadow_runtime_evidence_ref = last_run_str(
        last_run, "shadow_runtime_evidence_ref", ""
    )
    state.last_runtime_evidence_bundle_ref = str(runtime_evidence_bundle_path.resolve())
    state.last_execution_runtime_projection_ref = last_run_str(
        last_run, "execution_runtime_projection_ref", ""
    )
    state.last_execution_runtime_projection_source = last_run_str(
        last_run, "execution_runtime_projection_source", "not_configured"
    )
    state.last_regime_lite_assessment_ref = last_run_str(
        last_run, "regime_lite_assessment_ref", ""
    )
    state.last_regime_lite_assessment_source = last_run_str(
        last_run, "regime_lite_assessment_source", "not_configured"
    )
    state.last_regime_lite_safing_recommendation_ref = last_run_str(
        last_run, "regime_lite_safing_recommendation_ref", ""
    )
    state.last_regime_lite_safing_recommendation_source = last_run_str(
        last_run,
        "regime_lite_safing_recommendation_source",
        "not_configured",
    )
    state.last_info_stress_assessment_ref = last_run_str(
        last_run, "info_stress_assessment_ref", ""
    )
    state.last_info_stress_assessment_source = last_run_str(
        last_run, "info_stress_assessment_source", "not_configured"
    )
    state.last_telegram_alert_config_ref = last_run_str(
        last_run, "telegram_alert_config_ref", ""
    )
    state.last_telegram_alert_config_source = last_run_str(
        last_run, "telegram_alert_config_source", "not_configured"
    )
    state.last_telegram_alert_key_ref = last_run_str(
        last_run, "telegram_alert_key_ref", ""
    )
    state.last_telegram_alert_key_source = last_run_str(
        last_run, "telegram_alert_key_source", "not_configured"
    )
    state.last_execution_runtime_bootstrap_ref = last_run_str(
        last_run, "execution_runtime_bootstrap_ref", ""
    )
    state.last_execution_runtime_bootstrap_status = last_run_str(
        last_run, "execution_runtime_bootstrap_status", "not_configured"
    )
    state.last_execution_runtime_bootstrap_source = last_run_str(
        last_run, "execution_runtime_bootstrap_source", "not_configured"
    )
    state.last_execution_runtime_gatekeeper_audit_ref = last_run_str(
        last_run, "execution_runtime_gatekeeper_audit_ref", ""
    )
    state.last_execution_runtime_gatekeeper_audit_source = last_run_str(
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
    live_capture_result: object | None,
    *,
    write_execution_telemetry_artifacts: Callable[..., tuple[Path, Path]],
) -> tuple[str, Path | None]:
    if str(last_run.get("export_dir_ref", "")).strip():
        try:
            _, artifact_path = write_execution_telemetry_artifacts(
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
    live_capture_result: object | None,
    execution_telemetry_status: str,
    execution_telemetry_artifact_path: Path | None,
    *,
    read_runtime_evidence_bundle: ReadRuntimeEvidenceBundle,
    write_campaign_summary: WriteCampaignSummary,
    write_service_monitoring: WriteServiceMonitoring,
    append_service_event: AppendServiceEvent,
    last_run_str: Callable[[dict, str, str], str],
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
    bundle = read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
    campaign_summary_path = write_campaign_summary(
        service_dir=context.service_dir,
        state=state,
        bundle=bundle,
    )
    state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
    context.store.persist()
    write_service_monitoring(context)
    append_service_event(
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
        append_service_event(
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
        append_service_event(
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
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="shadow_day_completed",
            message="Governed Shadow day completed.",
            session_date=last_run["session_date"],
            export_dir_ref=last_run_str(last_run, "export_dir_ref", ""),
            accepted=bool(last_run["accepted"]),
            consecutive_days=int(last_run["consecutive_days"]),
            remaining_days=int(last_run["remaining_days"]),
        ),
    )


def _record_shadow_vps_failed_cycle(
    context: ShadowVpsServiceRuntimeContext,
    exc: Exception,
    *,
    write_service_monitoring: WriteServiceMonitoring,
    append_service_event: AppendServiceEvent,
) -> None:
    state = context.store.state
    state.failure_count += 1
    state.service_status = ShadowVpsServiceStatus.DEGRADED
    state.last_error = str(exc)
    context.store.persist()
    write_service_monitoring(context)
    append_service_event(
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
