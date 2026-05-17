#!/usr/bin/env python3
"""Runtime loop helpers for the Shadow VPS service."""

from __future__ import annotations

import time
from typing import Callable

from protocols import ShadowVpsServiceEvent, ShadowVpsServiceStatus
from shadow_vps_service_resource_hygiene_support import (
    ShadowVpsServiceResourceHygieneController,
)
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext

ReadRuntimeEvidenceBundle = Callable[[str], object | None]
WriteCampaignSummary = Callable[..., object]
WriteServiceMonitoring = Callable[[ShadowVpsServiceRuntimeContext], None]
AppendServiceEvent = Callable[..., None]
RunServiceCycle = Callable[..., str]
EmitOutputLines = Callable[..., None]
BuildServiceOutputLines = Callable[..., tuple[str, ...]]
ShouldStop = Callable[[], bool]
ResolveStopReason = Callable[[], str]


def _finalize_shadow_vps_service_runtime(
    context: ShadowVpsServiceRuntimeContext,
    *,
    read_runtime_evidence_bundle: ReadRuntimeEvidenceBundle,
    write_campaign_summary: WriteCampaignSummary,
    write_service_monitoring: WriteServiceMonitoring,
    append_service_event: AppendServiceEvent,
) -> None:
    state = context.store.state
    if state.service_status != ShadowVpsServiceStatus.DEGRADED:
        state.service_status = ShadowVpsServiceStatus.STOPPED
    state.last_heartbeat_at = time.time()
    final_bundle = read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
    if state.last_runtime_evidence_bundle_ref:
        campaign_summary_path = write_campaign_summary(
            service_dir=context.service_dir,
            state=state,
            bundle=final_bundle,
        )
        state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
    context.store.persist()
    write_service_monitoring(context)
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="service_stopped",
            message="Shadow VPS service stopped.",
            session_date=state.last_completed_session_date,
        ),
    )
    if state.last_runtime_evidence_bundle_ref:
        final_bundle = read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
        campaign_summary_path = write_campaign_summary(
            service_dir=context.service_dir,
            state=state,
            bundle=final_bundle,
        )
        state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
        context.store.persist()
    write_service_monitoring(context)


def _record_shadow_vps_stop_request(
    context: ShadowVpsServiceRuntimeContext,
    *,
    reason: str,
    append_service_event: AppendServiceEvent,
    write_service_monitoring: WriteServiceMonitoring,
) -> None:
    state = context.store.state
    state.last_heartbeat_at = time.time()
    context.store.persist()
    write_service_monitoring(context)
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="service_stop_requested",
            message=f"Shadow VPS service stop requested: {reason}.",
            session_date=state.last_completed_session_date,
        ),
    )


def _run_shadow_vps_service_main_loop(
    context: ShadowVpsServiceRuntimeContext,
    *,
    poll_interval_s: float,
    max_cycles: int | None,
    continue_on_error: bool,
    run_shadow_vps_service_cycle: RunServiceCycle,
    should_stop: ShouldStop | None = None,
    resolve_stop_reason: ResolveStopReason | None = None,
    write_service_monitoring: WriteServiceMonitoring | None = None,
    append_service_event: AppendServiceEvent | None = None,
) -> None:
    cycle_index = 0
    stop_request_recorded = False
    resource_hygiene = ShadowVpsServiceResourceHygieneController()

    def _should_stop_now() -> bool:
        return should_stop is not None and should_stop()

    def _record_stop_request_if_needed() -> bool:
        nonlocal stop_request_recorded
        if not _should_stop_now():
            return False
        if (
            not stop_request_recorded
            and append_service_event is not None
            and write_service_monitoring is not None
        ):
            stop_reason = (
                resolve_stop_reason().strip()
                if resolve_stop_reason is not None
                else ""
            )
            _record_shadow_vps_stop_request(
                context,
                reason=stop_reason or "external stop requested",
                append_service_event=append_service_event,
                write_service_monitoring=write_service_monitoring,
            )
            stop_request_recorded = True
        return True

    while max_cycles is None or cycle_index < max_cycles:
        if _record_stop_request_if_needed():
            break
        cycle_index += 1
        action = run_shadow_vps_service_cycle(
            context,
            continue_on_error=continue_on_error,
        )
        if append_service_event is not None:
            resource_hygiene.run_due(
                context,
                append_service_event=append_service_event,
            )
        if action == "break":
            break
        if _record_stop_request_if_needed():
            break
        if action == "sleep" and (max_cycles is None or cycle_index < max_cycles):
            if _record_stop_request_if_needed():
                break
            time.sleep(max(0.0, poll_interval_s))


def _emit_service_output(
    context: ShadowVpsServiceRuntimeContext,
    *,
    emit_output_lines: EmitOutputLines,
    build_service_output_lines: BuildServiceOutputLines,
) -> None:
    emit_output_lines(
        build_service_output_lines(
            store=context.store,
            service_dir=context.service_dir,
            resolved_orchestrator_output_dir=context.resolved_orchestrator_output_dir,
            resolved_shadow_output_dir=context.resolved_shadow_output_dir,
            scrape_host=context.monitoring.scrape_host,
            node_exporter_textfile_dir=context.monitoring.node_exporter_textfile_dir,
        )
    )
