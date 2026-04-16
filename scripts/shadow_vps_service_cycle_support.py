#!/usr/bin/env python3
"""Cycle selection helpers for the Shadow VPS service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from protocols import (
    ShadowDailyOrchestrator,
    ShadowDailyPlanSlot,
    ShadowLiveWebSocketCaptureResult,
    ShadowLiveWebSocketConfig,
    ShadowVpsServiceEvent,
    ShadowVpsServiceStatus,
    ShadowVpsRawInputSlot,
    ShadowVpsWebsocketInputSlot,
)
from shadow_vps_service_models import (
    ShadowVpsCycleSelection,
    ShadowVpsServiceRuntimeContext,
)


SelectNextRawSlot = Callable[
    [Path | None, ShadowDailyOrchestrator], ShadowVpsRawInputSlot | None
]
SelectNextWebsocketSlot = Callable[
    [Path | None, ShadowDailyOrchestrator], ShadowVpsWebsocketInputSlot | None
]
ReadLiveWebsocketConfig = Callable[[Path], ShadowLiveWebSocketConfig]
ResolveProjectionPath = Callable[..., tuple[Path | None, str]]
ResolveAssessmentPath = Callable[..., tuple[Path | None, str]]
EnsureAutoExportRaw = Callable[..., Path]
EnsureAutoExportWebsocket = Callable[..., tuple[Path | None, Path]]
EnsureAutoExportLive = Callable[..., tuple[Path | None, Path]]
PinSessionDate = Callable[[Path, str], None]
AppendServiceEvent = Callable[..., None]
WriteServiceMonitoring = Callable[[ShadowVpsServiceRuntimeContext], None]
ReadLiveCaptureResult = Callable[[Path | None], ShadowLiveWebSocketCaptureResult | None]


@dataclass(frozen=True)
class _ShadowVpsResolvedCycleInputs:
    raw_slot: ShadowVpsRawInputSlot | None
    websocket_slot: ShadowVpsWebsocketInputSlot | None
    live_config: ShadowLiveWebSocketConfig | None
    projection_path: Path | None
    projection_source: str
    regime_assessment_path: Path | None
    regime_assessment_source: str
    regime_safing_path: Path | None
    regime_safing_source: str
    info_stress_path: Path | None
    info_stress_source: str


@dataclass(frozen=True)
class _ShadowVpsResolvedGovernancePaths:
    projection_path: Path | None
    projection_source: str
    regime_assessment_path: Path | None
    regime_assessment_source: str
    regime_safing_path: Path | None
    regime_safing_source: str
    info_stress_path: Path | None
    info_stress_source: str


@dataclass(frozen=True)
class _ShadowVpsPreparedSelection:
    next_slot: ShadowDailyPlanSlot | None
    live_capture_dir: Path | None
    auto_snapshot_dir: Path | None
    auto_export_dir: Path | None


def _resolve_shadow_vps_governance_paths(
    context: ShadowVpsServiceRuntimeContext,
    live_config: ShadowLiveWebSocketConfig | None,
    *,
    resolve_execution_runtime_projection_path: ResolveProjectionPath,
    resolve_regime_lite_assessment_path: ResolveAssessmentPath,
    resolve_regime_lite_safing_recommendation_path: ResolveAssessmentPath,
    resolve_info_stress_assessment_path: ResolveAssessmentPath,
) -> _ShadowVpsResolvedGovernancePaths:
    projection_path, projection_source = resolve_execution_runtime_projection_path(
        explicit_path=context.execution_runtime_projection_path,
        live_websocket_config_path=context.live_websocket_config_path,
        live_config=live_config,
    )
    regime_assessment_path, regime_assessment_source = (
        resolve_regime_lite_assessment_path(
            explicit_path=context.regime_lite_assessment_path,
            live_websocket_config_path=context.live_websocket_config_path,
            live_config=live_config,
        )
    )
    regime_safing_path, regime_safing_source = (
        resolve_regime_lite_safing_recommendation_path(
            explicit_path=context.regime_lite_safing_recommendation_path,
            live_websocket_config_path=context.live_websocket_config_path,
            live_config=live_config,
        )
    )
    info_stress_path, info_stress_source = resolve_info_stress_assessment_path(
        explicit_path=context.info_stress_assessment_path,
        live_websocket_config_path=context.live_websocket_config_path,
        live_config=live_config,
    )
    return _ShadowVpsResolvedGovernancePaths(
        projection_path=projection_path,
        projection_source=projection_source,
        regime_assessment_path=regime_assessment_path,
        regime_assessment_source=regime_assessment_source,
        regime_safing_path=regime_safing_path,
        regime_safing_source=regime_safing_source,
        info_stress_path=info_stress_path,
        info_stress_source=info_stress_source,
    )


def _resolve_shadow_vps_cycle_inputs(
    context: ShadowVpsServiceRuntimeContext,
    daily_orchestrator: ShadowDailyOrchestrator,
    *,
    select_next_raw_input_slot: SelectNextRawSlot,
    select_next_websocket_input_slot: SelectNextWebsocketSlot,
    read_live_websocket_config: ReadLiveWebsocketConfig,
    resolve_execution_runtime_projection_path: ResolveProjectionPath,
    resolve_regime_lite_assessment_path: ResolveAssessmentPath,
    resolve_regime_lite_safing_recommendation_path: ResolveAssessmentPath,
    resolve_info_stress_assessment_path: ResolveAssessmentPath,
) -> _ShadowVpsResolvedCycleInputs:
    raw_slot = (
        select_next_raw_input_slot(context.raw_inputs_root, daily_orchestrator)
        if context.raw_inputs_root is not None
        else None
    )
    websocket_slot = (
        select_next_websocket_input_slot(context.websocket_streams_root, daily_orchestrator)
        if context.websocket_streams_root is not None
        else None
    )
    live_config = (
        read_live_websocket_config(context.live_websocket_config_path)
        if context.live_websocket_config_path is not None
        else None
    )
    governance_paths = _resolve_shadow_vps_governance_paths(
        context,
        live_config,
        resolve_execution_runtime_projection_path=resolve_execution_runtime_projection_path,
        resolve_regime_lite_assessment_path=resolve_regime_lite_assessment_path,
        resolve_regime_lite_safing_recommendation_path=resolve_regime_lite_safing_recommendation_path,
        resolve_info_stress_assessment_path=resolve_info_stress_assessment_path,
    )
    return _ShadowVpsResolvedCycleInputs(
        raw_slot=raw_slot,
        websocket_slot=websocket_slot,
        live_config=live_config,
        projection_path=governance_paths.projection_path,
        projection_source=governance_paths.projection_source,
        regime_assessment_path=governance_paths.regime_assessment_path,
        regime_assessment_source=governance_paths.regime_assessment_source,
        regime_safing_path=governance_paths.regime_safing_path,
        regime_safing_source=governance_paths.regime_safing_source,
        info_stress_path=governance_paths.info_stress_path,
        info_stress_source=governance_paths.info_stress_source,
    )


def _prepare_shadow_vps_auto_export_selection(
    context: ShadowVpsServiceRuntimeContext,
    daily_orchestrator: ShadowDailyOrchestrator,
    completed_session_dates: set[str],
    resolved_inputs: _ShadowVpsResolvedCycleInputs,
    *,
    ensure_auto_export_from_raw_slot: EnsureAutoExportRaw,
    ensure_auto_export_from_websocket_slot: EnsureAutoExportWebsocket,
    ensure_auto_export_from_live_websocket: EnsureAutoExportLive,
    pin_auto_export_session_date: PinSessionDate,
) -> _ShadowVpsPreparedSelection:
    auto_export_dir: Path | None = None
    auto_snapshot_dir: Path | None = None
    live_capture_dir: Path | None = None
    if resolved_inputs.raw_slot is not None:
        auto_export_dir = ensure_auto_export_from_raw_slot(
            resolved_inputs.raw_slot,
            auto_exports_root=context.resolved_auto_exports_root,
        )
        pin_auto_export_session_date(auto_export_dir, resolved_inputs.raw_slot.session_date)
        next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
        return _ShadowVpsPreparedSelection(next_slot, None, None, auto_export_dir)
    if resolved_inputs.websocket_slot is not None:
        auto_snapshot_dir, auto_export_dir = ensure_auto_export_from_websocket_slot(
            resolved_inputs.websocket_slot,
            auto_snapshots_root=context.resolved_auto_snapshots_root,
            auto_exports_root=context.resolved_auto_exports_root,
        )
        pin_auto_export_session_date(
            auto_export_dir,
            resolved_inputs.websocket_slot.session_date,
        )
        next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
        return _ShadowVpsPreparedSelection(
            next_slot,
            None,
            auto_snapshot_dir,
            auto_export_dir,
        )
    return _prepare_shadow_vps_live_or_demo_selection(
        context,
        daily_orchestrator,
        completed_session_dates,
        resolved_inputs,
        ensure_auto_export_from_live_websocket=ensure_auto_export_from_live_websocket,
        pin_auto_export_session_date=pin_auto_export_session_date,
    )


def _prepare_shadow_vps_live_or_demo_selection(
    context: ShadowVpsServiceRuntimeContext,
    daily_orchestrator: ShadowDailyOrchestrator,
    completed_session_dates: set[str],
    resolved_inputs: _ShadowVpsResolvedCycleInputs,
    *,
    ensure_auto_export_from_live_websocket: EnsureAutoExportLive,
    pin_auto_export_session_date: PinSessionDate,
) -> _ShadowVpsPreparedSelection:
    live_session_date = (
        resolved_inputs.live_config.session_date_override or date.today().isoformat()
        if resolved_inputs.live_config is not None
        else ""
    )
    if resolved_inputs.live_config is None:
        next_slot = (
            daily_orchestrator.select_next_slot(context.exports_root)
            if context.exports_root is not None
            else daily_orchestrator.next_demo_slot()
        )
        return _ShadowVpsPreparedSelection(next_slot, None, None, None)
    if live_session_date in completed_session_dates:
        return _ShadowVpsPreparedSelection(None, None, None, None)
    live_capture_dir, auto_export_dir = ensure_auto_export_from_live_websocket(
        resolved_inputs.live_config,
        live_captures_root=context.resolved_live_captures_root,
        auto_exports_root=context.resolved_auto_exports_root,
    )
    pin_auto_export_session_date(auto_export_dir, live_session_date)
    next_slot = daily_orchestrator.select_next_slot(context.resolved_auto_exports_root)
    return _ShadowVpsPreparedSelection(next_slot, live_capture_dir, None, auto_export_dir)


def _resolve_shadow_vps_cycle_selection(
    context: ShadowVpsServiceRuntimeContext,
    *,
    select_next_raw_input_slot: SelectNextRawSlot,
    select_next_websocket_input_slot: SelectNextWebsocketSlot,
    read_live_websocket_config: ReadLiveWebsocketConfig,
    resolve_execution_runtime_projection_path: ResolveProjectionPath,
    resolve_regime_lite_assessment_path: ResolveAssessmentPath,
    resolve_regime_lite_safing_recommendation_path: ResolveAssessmentPath,
    resolve_info_stress_assessment_path: ResolveAssessmentPath,
    ensure_auto_export_from_raw_slot: EnsureAutoExportRaw,
    ensure_auto_export_from_websocket_slot: EnsureAutoExportWebsocket,
    ensure_auto_export_from_live_websocket: EnsureAutoExportLive,
    pin_auto_export_session_date: PinSessionDate,
) -> ShadowVpsCycleSelection:
    daily_orchestrator = ShadowDailyOrchestrator(context.resolved_orchestrator_output_dir)
    completed_session_dates = set(daily_orchestrator.completed_session_dates())
    resolved_inputs = _resolve_shadow_vps_cycle_inputs(
        context,
        daily_orchestrator,
        select_next_raw_input_slot=select_next_raw_input_slot,
        select_next_websocket_input_slot=select_next_websocket_input_slot,
        read_live_websocket_config=read_live_websocket_config,
        resolve_execution_runtime_projection_path=resolve_execution_runtime_projection_path,
        resolve_regime_lite_assessment_path=resolve_regime_lite_assessment_path,
        resolve_regime_lite_safing_recommendation_path=resolve_regime_lite_safing_recommendation_path,
        resolve_info_stress_assessment_path=resolve_info_stress_assessment_path,
    )
    prepared_selection = _prepare_shadow_vps_auto_export_selection(
        context,
        daily_orchestrator,
        completed_session_dates,
        resolved_inputs,
        ensure_auto_export_from_raw_slot=ensure_auto_export_from_raw_slot,
        ensure_auto_export_from_websocket_slot=ensure_auto_export_from_websocket_slot,
        ensure_auto_export_from_live_websocket=ensure_auto_export_from_live_websocket,
        pin_auto_export_session_date=pin_auto_export_session_date,
    )
    return ShadowVpsCycleSelection(
        raw_slot=resolved_inputs.raw_slot,
        websocket_slot=resolved_inputs.websocket_slot,
        next_slot=prepared_selection.next_slot,
        live_capture_dir=prepared_selection.live_capture_dir,
        auto_snapshot_dir=prepared_selection.auto_snapshot_dir,
        auto_export_dir=prepared_selection.auto_export_dir,
        resolved_execution_runtime_projection_path=resolved_inputs.projection_path,
        resolved_execution_runtime_projection_source=resolved_inputs.projection_source,
        resolved_regime_lite_assessment_path=resolved_inputs.regime_assessment_path,
        resolved_regime_lite_assessment_source=resolved_inputs.regime_assessment_source,
        resolved_regime_lite_safing_recommendation_path=resolved_inputs.regime_safing_path,
        resolved_regime_lite_safing_recommendation_source=resolved_inputs.regime_safing_source,
        resolved_info_stress_assessment_path=resolved_inputs.info_stress_path,
        resolved_info_stress_assessment_source=resolved_inputs.info_stress_source,
        live_capture_result=None,
    )


def _record_shadow_vps_idle_cycle(
    context: ShadowVpsServiceRuntimeContext,
    *,
    append_service_event: AppendServiceEvent,
    write_service_monitoring: WriteServiceMonitoring,
) -> None:
    state = context.store.state
    state.idle_count += 1
    state.service_status = ShadowVpsServiceStatus.IDLE
    context.store.persist()
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="idle_no_pending_export",
            message="No pending governed Shadow export directory was found.",
        ),
    )
    write_service_monitoring(context)


def _apply_selected_cycle_state(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> None:
    state = context.store.state
    state.last_selected_session_date = selection.next_slot.session_date
    state.last_raw_input_dir_ref = (
        selection.raw_slot.raw_input_dir_ref if selection.raw_slot is not None else ""
    )
    state.last_websocket_input_dir_ref = (
        selection.websocket_slot.websocket_input_dir_ref
        if selection.websocket_slot is not None
        else ""
    )
    state.last_live_capture_dir_ref = (
        live_capture_result.live_capture_dir_ref if live_capture_result is not None else ""
    )
    state.last_live_capture_snapshot_batch_ref = (
        live_capture_result.snapshot_batch_path_ref
        if live_capture_result is not None
        else ""
    )
    state.last_live_capture_summary_ref = (
        live_capture_result.summary_path_ref if live_capture_result is not None else ""
    )
    state.last_live_capture_time_sync_offsets_ref = (
        live_capture_result.time_sync_offsets_path_ref
        if live_capture_result is not None
        else ""
    )
    state.last_live_user_data_summary_ref = (
        live_capture_result.user_data_summary_path_ref
        if live_capture_result is not None
        else ""
    )
    state.last_auto_snapshot_dir_ref = (
        str(selection.auto_snapshot_dir.resolve())
        if selection.auto_snapshot_dir is not None
        else ""
    )
    state.last_auto_export_dir_ref = (
        str(selection.auto_export_dir.resolve())
        if selection.auto_export_dir is not None
        else ""
    )
    context.store.persist()


def _emit_selected_cycle_events(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    append_service_event: AppendServiceEvent,
) -> None:
    if selection.raw_slot is not None and selection.auto_export_dir is not None:
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from raw VPS input.",
                session_date=selection.raw_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )
    if selection.websocket_slot is not None and selection.auto_snapshot_dir is not None:
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_snapshot_completed",
                message="Historical snapshot batch was auto-generated from injected websocket stream.",
                session_date=selection.websocket_slot.session_date,
                export_dir_ref=str(selection.auto_snapshot_dir.resolve()),
            ),
        )
    if selection.websocket_slot is not None and selection.auto_export_dir is not None:
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from injected websocket stream.",
                session_date=selection.websocket_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )
    if selection.live_capture_dir is not None:
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=_build_live_capture_completed_event(selection, live_capture_result),
        )
    if selection.live_capture_dir is not None and selection.auto_export_dir is not None:
        append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="auto_export_completed",
                message="Governed local replay export was auto-generated from native live_websocket capture.",
                session_date=selection.next_slot.session_date,
                export_dir_ref=str(selection.auto_export_dir.resolve()),
            ),
        )


def _build_live_capture_completed_event(
    selection: ShadowVpsCycleSelection,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> ShadowVpsServiceEvent:
    return ShadowVpsServiceEvent(
        event_type="live_capture_completed",
        message="Native live_websocket capture completed.",
        session_date=selection.next_slot.session_date,
        export_dir_ref=str(selection.live_capture_dir.resolve()),
        live_capture_summary_ref=(
            live_capture_result.summary_path_ref if live_capture_result is not None else ""
        ),
        emitted_message_count=(
            live_capture_result.emitted_message_count if live_capture_result is not None else None
        ),
        accepted_message_count=(
            live_capture_result.accepted_message_count if live_capture_result is not None else None
        ),
        ignored_message_count=(
            live_capture_result.ignored_message_count if live_capture_result is not None else None
        ),
        rejected_message_count=(
            live_capture_result.rejected_message_count if live_capture_result is not None else None
        ),
        pair_scope=live_capture_result.pair_scope if live_capture_result is not None else (),
        event_types=live_capture_result.event_types if live_capture_result is not None else (),
    )


def _set_last_run_ref_and_source(
    last_run: dict[str, object],
    *,
    ref_key: str,
    source_key: str,
    path: Path | None,
    source: str,
) -> None:
    last_run[ref_key] = str(path.resolve()) if path is not None else ""
    last_run[source_key] = source if path is not None else "not_configured"


def _set_last_run_selection_metadata(
    last_run: dict[str, object],
    selection: ShadowVpsCycleSelection,
) -> None:
    last_run["execution_runtime_projection_source"] = (
        selection.resolved_execution_runtime_projection_source
        if selection.resolved_execution_runtime_projection_path is not None
        else "not_configured"
    )
    _set_last_run_ref_and_source(
        last_run,
        ref_key="regime_lite_assessment_ref",
        source_key="regime_lite_assessment_source",
        path=selection.resolved_regime_lite_assessment_path,
        source=selection.resolved_regime_lite_assessment_source,
    )
    _set_last_run_ref_and_source(
        last_run,
        ref_key="regime_lite_safing_recommendation_ref",
        source_key="regime_lite_safing_recommendation_source",
        path=selection.resolved_regime_lite_safing_recommendation_path,
        source=selection.resolved_regime_lite_safing_recommendation_source,
    )
    _set_last_run_ref_and_source(
        last_run,
        ref_key="info_stress_assessment_ref",
        source_key="info_stress_assessment_source",
        path=selection.resolved_info_stress_assessment_path,
        source=selection.resolved_info_stress_assessment_source,
    )


def _set_last_run_telegram_metadata(
    last_run: dict[str, object],
    context: ShadowVpsServiceRuntimeContext,
) -> None:
    _set_last_run_ref_and_source(
        last_run,
        ref_key="telegram_alert_config_ref",
        source_key="telegram_alert_config_source",
        path=context.resolved_telegram_alert_config_path,
        source=context.resolved_telegram_alert_config_source,
    )
    _set_last_run_ref_and_source(
        last_run,
        ref_key="telegram_alert_key_ref",
        source_key="telegram_alert_key_source",
        path=context.resolved_telegram_alert_key_path,
        source=context.resolved_telegram_alert_key_source,
    )


def _set_last_run_bootstrap_metadata(
    last_run: dict[str, object],
    context: ShadowVpsServiceRuntimeContext,
) -> None:
    bootstrap_summary = context.bootstrap_summary
    last_run["execution_runtime_bootstrap_ref"] = (
        str(context.bootstrap_summary_path.resolve())
        if context.bootstrap_summary_path is not None
        else ""
    )
    last_run["execution_runtime_bootstrap_status"] = bootstrap_summary.status
    last_run["execution_runtime_bootstrap_source"] = (
        bootstrap_summary.source
        if bootstrap_summary.status != "not_configured"
        else "not_configured"
    )
    last_run["execution_runtime_gatekeeper_audit_ref"] = (
        bootstrap_summary.gatekeeper_audit_ref
    )
    last_run["execution_runtime_gatekeeper_audit_source"] = (
        bootstrap_summary.gatekeeper_audit_source
        if bootstrap_summary.gatekeeper_audit_ref
        else "not_configured"
    )
    last_run["execution_runtime_bootstrap_user_data_stream_enabled"] = bool(
        bootstrap_summary.user_data_stream_enabled
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_executed"] = bool(
        bootstrap_summary.reconciliation_boot_executed
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_trading_blocked"] = bool(
        bootstrap_summary.reconciliation_boot_trading_blocked
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped"] = bool(
        bootstrap_summary.reconciliation_boot_circuit_breaker_tripped
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_detail"] = (
        bootstrap_summary.reconciliation_boot_detail
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_recovery_action"] = (
        bootstrap_summary.reconciliation_boot_recovery_action
    )
    last_run["execution_runtime_bootstrap_reconciliation_boot_divergence_count"] = int(
        bootstrap_summary.reconciliation_boot_divergence_count
    )


def _prepare_shadow_vps_selected_cycle(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    *,
    read_live_capture_result: ReadLiveCaptureResult,
    append_service_event: AppendServiceEvent,
) -> ShadowLiveWebSocketCaptureResult | None:
    if selection.next_slot is None:
        raise ValueError("selected cycle requires a governed slot")
    live_capture_result = read_live_capture_result(selection.live_capture_dir)
    _apply_selected_cycle_state(context, selection, live_capture_result)
    _emit_selected_cycle_events(
        context,
        selection,
        live_capture_result,
        append_service_event,
    )
    return live_capture_result


def _augment_last_run_with_operated_metadata(
    *,
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
    last_run: dict[str, object],
) -> None:
    _set_last_run_selection_metadata(last_run, selection)
    _set_last_run_telegram_metadata(last_run, context)
    _set_last_run_bootstrap_metadata(last_run, context)
