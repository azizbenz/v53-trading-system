#!/usr/bin/env python3
"""Runtime loop helpers for the Shadow VPS service."""

from __future__ import annotations

import time
from typing import Callable

from protocols import ShadowVpsServiceEvent, ShadowVpsServiceStatus
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext

ReadRuntimeEvidenceBundle = Callable[[str], object | None]
WriteCampaignSummary = Callable[..., object]
WriteServiceMonitoring = Callable[[ShadowVpsServiceRuntimeContext], None]
AppendServiceEvent = Callable[..., None]
RunServiceCycle = Callable[..., str]
EmitOutputLines = Callable[..., None]
BuildServiceOutputLines = Callable[..., tuple[str, ...]]


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


def _run_shadow_vps_service_main_loop(
    context: ShadowVpsServiceRuntimeContext,
    *,
    poll_interval_s: float,
    max_cycles: int | None,
    continue_on_error: bool,
    run_shadow_vps_service_cycle: RunServiceCycle,
) -> None:
    cycle_index = 0
    while max_cycles is None or cycle_index < max_cycles:
        cycle_index += 1
        action = run_shadow_vps_service_cycle(
            context,
            continue_on_error=continue_on_error,
        )
        if action == "break":
            break
        if action == "sleep" and (max_cycles is None or cycle_index < max_cycles):
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
