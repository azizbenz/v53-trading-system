#!/usr/bin/env python3
"""Run the autonomous long-running VPS Shadow service."""

from __future__ import annotations

from collections.abc import Callable
import logging
import os
import signal
import sys
import time
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
for candidate in (SCRIPT_ROOT, SRC_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import shadow_vps_service_input_support as _shadow_vps_service_input_support  # noqa: E402
import shadow_vps_service_io_support as _shadow_vps_service_io_support  # noqa: E402
from interface_contracts import DashboardGovernedCommandKind  # noqa: E402
from interface_contracts.shadow_vps_service_contracts import (  # noqa: E402
    ShadowVpsServiceState,
)
from protocols import (  # noqa: E402
    DashboardGovernedCommandExecutionContext,
    ShadowVpsServiceStatus,
    ShadowVpsServiceEvent,
    build_binance_execution_runtime_bootstrap_bundle,
    capture_live_websocket_snapshot_batch,
    process_dashboard_command_queue_once,
)
from shadow_vps_service_campaign_support import (  # noqa: E402
    _write_campaign_summary,
)
from shadow_vps_service_cli_support import (  # noqa: E402
    _build_argument_parser,
    _build_service_output_lines,
    _configure_stdio,
    _emit_output_lines,
    _validate_input_root_selection,
)
from shadow_vps_service_cycle_support import (  # noqa: E402
    _augment_last_run_with_operated_metadata,
    _prepare_shadow_vps_selected_cycle,
    _record_shadow_vps_idle_cycle,
    _resolve_shadow_vps_cycle_selection,
)
from shadow_vps_service_governance_snapshot_support import (  # noqa: E402
    _refresh_shadow_vps_governance_snapshots,
)
from shadow_vps_service_complete_support import (  # noqa: E402
    ShadowVpsBuild17Refresh,
    refresh_shadow_vps_build17_supervision,
)
from shadow_vps_service_event_support import (  # noqa: E402
    _append_service_event,
)
from shadow_vps_service_execution_support import (  # noqa: E402
    _apply_last_run_to_shadow_vps_state,
    _complete_shadow_vps_successful_cycle,
    _persist_shadow_artifact_comparison_evidence,
    _record_shadow_vps_failed_cycle,
    _run_shadow_vps_daily_orchestrator,
    _write_shadow_vps_cycle_execution_telemetry,
)
from shadow_vps_service_input_support import (  # noqa: E402
    _ensure_auto_export_from_live_websocket,
    _ensure_auto_export_from_raw_slot,
    _ensure_auto_export_from_websocket_slot,
    _select_next_raw_input_slot,
    _select_next_websocket_input_slot,
)
from shadow_vps_service_io_support import (  # noqa: E402
    _pin_auto_export_session_date,
    _read_live_websocket_config,
    _resolve_execution_runtime_projection_path,
    _resolve_info_stress_assessment_path,
    _resolve_regime_lite_assessment_path,
    _resolve_regime_lite_safing_recommendation_path,
)
from shadow_vps_service_loader_support import (  # noqa: E402
    _read_last_run,
    _read_live_capture_result,
)
from shadow_vps_service_models import (  # noqa: E402
    ShadowVpsCycleSelection,
    ShadowVpsServiceRuntimeContext,
)
from shadow_vps_service_monitoring_support import (  # noqa: E402
    _read_runtime_evidence_bundle,
    _write_service_monitoring,
)
from shadow_vps_service_projection_support import (  # noqa: E402
    _last_run_str,
    _write_runtime_evidence_bundle,
)
from shadow_vps_service_recovery_support import (  # noqa: E402
    _refresh_shadow_vps_recovery_artifacts,
)
from shadow_vps_service_runtime_support import (  # noqa: E402
    _emit_service_output,
    _finalize_shadow_vps_service_runtime,
    _run_shadow_vps_service_main_loop,
)
from shadow_vps_service_startup_support import (  # noqa: E402
    TelegramPostFunc,
    _initialize_shadow_vps_service_runtime,
)
from shadow_vps_service_telemetry_support import (  # noqa: E402
    _write_execution_telemetry_artifacts,
)


class _ShadowVpsSignalController:
    def __init__(self) -> None:
        self._stop_requested = False
        self._signal_name = ""

    def request_stop(self, signal_name: str) -> None:
        normalized_name = signal_name.strip() or "UNKNOWN"
        if not self._stop_requested:
            self._signal_name = normalized_name
        self._stop_requested = True

    def stop_requested(self) -> bool:
        return self._stop_requested

    def stop_reason(self) -> str:
        if self._signal_name:
            return f"signal {self._signal_name}"
        return "external stop requested"


def _install_shadow_vps_signal_handlers(
    controller: _ShadowVpsSignalController,
) -> Callable[[], None]:
    registered_handlers: list[tuple[signal.Signals, object]] = []

    def _handle_stop_signal(stop_signal: signal.Signals, _frame: object) -> None:
        controller.request_stop(getattr(stop_signal, "name", str(stop_signal)))

    for signal_name in ("SIGINT", "SIGTERM"):
        stop_signal = getattr(signal, signal_name, None)
        if stop_signal is None:
            continue
        try:
            previous_handler = signal.getsignal(stop_signal)
            signal.signal(stop_signal, _handle_stop_signal)
        except (OSError, RuntimeError, ValueError):
            continue
        registered_handlers.append((stop_signal, previous_handler))

    def _restore_signal_handlers() -> None:
        for stop_signal, previous_handler in reversed(registered_handlers):
            try:
                signal.signal(stop_signal, previous_handler)
            except (OSError, RuntimeError, ValueError):
                continue

    return _restore_signal_handlers


_COCKPIT_LOGGER = logging.getLogger("v53.cockpit.kill_channel")


def _write_pid_file_if_configured(pid_file: Path | None) -> bool:
    """Atomically write the current PID. Returns True iff the file was written.

    Used by the cockpit kill switch (Phase 3): the cockpit reads this file to
    know which process to ``SIGTERM``.  Atomic write protects against partial
    files if the service crashes mid-write.
    """
    if pid_file is None:
        return False
    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = pid_file.with_suffix(pid_file.suffix + ".tmp")
        tmp.write_text(str(os.getpid()), encoding="utf-8")
        os.replace(tmp, pid_file)
    except OSError as exc:
        _COCKPIT_LOGGER.warning("cannot write PID file %s: %s", pid_file, exc)
        return False
    _COCKPIT_LOGGER.info("PID file written: %s (pid=%d)", pid_file, os.getpid())
    return True


def _clear_pid_file(pid_file: Path) -> None:
    try:
        pid_file.unlink(missing_ok=True)
    except OSError as exc:
        _COCKPIT_LOGGER.warning("cannot clear PID file %s: %s", pid_file, exc)


def _build_should_stop_callable(
    *,
    signal_controller: _ShadowVpsSignalController,
    halt_flag_file: Path | None,
) -> Callable[[], bool]:
    """Compose the main-loop ``should_stop`` callback.

    The base check is the signal_controller (SIGINT/SIGTERM). When a
    ``halt_flag_file`` is configured, the callback also watches the filesystem
    for a flag dropped by the cockpit ``POST /kill`` endpoint. Detecting the
    flag triggers an orderly stop and removes the flag (one-shot semantics).

    This dual channel makes the kill switch work on Windows (no SIGTERM) and
    survives stale PID files (the cockpit can drop the flag even if the PID
    tracker is out of sync).
    """
    def _should_stop() -> bool:
        if halt_flag_file is not None:
            try:
                exists = halt_flag_file.is_file()
            except OSError:
                exists = False
            if exists:
                _COCKPIT_LOGGER.info(
                    "cockpit.halt_flag_observed file=%s", halt_flag_file
                )
                signal_controller.request_stop("HALT_FLAG_OBSERVED")
                try:
                    halt_flag_file.unlink(missing_ok=True)
                except OSError as exc:
                    _COCKPIT_LOGGER.warning(
                        "cannot clear halt flag %s: %s", halt_flag_file, exc
                    )
        return signal_controller.stop_requested()

    return _should_stop


def _sync_shadow_vps_service_protocol_dependencies() -> None:
    # Keep support modules wired to the launcher module surface so tests can
    # monkeypatch the launcher without bypassing the canonical helpers.
    _shadow_vps_service_input_support.capture_live_websocket_snapshot_batch = (
        capture_live_websocket_snapshot_batch
    )
    _shadow_vps_service_io_support.build_binance_execution_runtime_bootstrap_bundle = (
        build_binance_execution_runtime_bootstrap_bundle
    )


def _refresh_shadow_vps_cycle_state(context: ShadowVpsServiceRuntimeContext) -> None:
    state = context.store.state
    state.loop_count += 1
    state.last_heartbeat_at = time.time()
    state.service_status = ShadowVpsServiceStatus.RUNNING
    context.store.persist()
    _write_service_monitoring(context)


def _dashboard_control_gate_result(
    context: ShadowVpsServiceRuntimeContext,
) -> str | None:
    state = context.store.state
    if not state.dashboard_control_halted:
        return None
    state.idle_count += 1
    state.service_status = ShadowVpsServiceStatus.DEGRADED
    context.store.persist()
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="dashboard_control_halted_active",
            message=(
                "Governed dashboard control halt is active; Shadow VPS cycle skipped."
            ),
            reason_codes=("shadow.dashboard_control.halted_active",),
        ),
    )
    _write_service_monitoring(context)
    return "sleep"


def _process_dashboard_command_queue(
    context: ShadowVpsServiceRuntimeContext,
) -> None:
    if context.dashboard_command_queue_root is None:
        return
    previous_state = context.store.state.model_copy(deep=True)
    process_dashboard_command_queue_once(
        context.dashboard_command_queue_root,
        context=DashboardGovernedCommandExecutionContext(
            allowed_commands=frozenset(DashboardGovernedCommandKind),
            shadow_vps_service_state_dir=context.service_dir,
        ),
    )
    context.store.reload()
    _append_dashboard_control_change_events(context, previous_state=previous_state)
    _write_service_monitoring(context)


def _append_dashboard_control_change_events(
    context: ShadowVpsServiceRuntimeContext,
    *,
    previous_state: ShadowVpsServiceState,
) -> None:
    state = context.store.state
    if (
        (
            previous_state.dashboard_control_target_profile,
            previous_state.dashboard_control_target_deployment_state,
        )
        != (
            state.dashboard_control_target_profile,
            state.dashboard_control_target_deployment_state,
        )
        and (
            state.dashboard_control_target_profile == "light"
            or state.dashboard_control_target_deployment_state == "rollback"
        )
    ):
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="rollback_active",
                message="Governed rollback_to_light is active on the Shadow control surface.",
                reason_codes=("shadow.dashboard_control.rollback_active",),
            ),
        )
    if (
        previous_state.dashboard_control_suspended_pairs
        != state.dashboard_control_suspended_pairs
        and state.dashboard_control_suspended_pairs
    ):
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="suspended_pair_active",
                message=(
                    "Governed suspended pair surface refreshed: "
                    f"{', '.join(state.dashboard_control_suspended_pairs)}."
                ),
                reason_codes=("shadow.dashboard_control.suspended_pairs_active",),
            ),
        )
    if (
        previous_state.dashboard_control_suspended_engines
        != state.dashboard_control_suspended_engines
        and state.dashboard_control_suspended_engines
    ):
        _append_service_event(
            store=context.store,
            telegram_alerter=context.telegram_alerter,
            event=ShadowVpsServiceEvent(
                event_type="suspended_engine_active",
                message=(
                    "Governed suspended engine surface refreshed: "
                    f"{', '.join(state.dashboard_control_suspended_engines)}."
                ),
                reason_codes=("shadow.dashboard_control.suspended_engines_active",),
            ),
        )


def _skip_shadow_vps_cycle(
    context: ShadowVpsServiceRuntimeContext,
    *,
    event_type: str,
    message: str,
    reason_codes: tuple[str, ...],
) -> str:
    state = context.store.state
    state.idle_count += 1
    state.service_status = ShadowVpsServiceStatus.DEGRADED
    context.store.persist()
    _append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type=event_type,
            message=message,
            reason_codes=reason_codes,
        ),
    )
    _write_service_monitoring(context)
    return "sleep"


def _recovery_gate_enabled(context: ShadowVpsServiceRuntimeContext) -> bool:
    return (
        bool(context.store.state.active_binance_credential_profile_id)
        or bool(context.store.state.last_live_capture_dir_ref)
    )


def _governed_runtime_gate_result(
    context: ShadowVpsServiceRuntimeContext,
    *,
    supervision: ShadowVpsBuild17Refresh,
) -> str | None:
    state = context.store.state
    dashboard_result = _dashboard_control_gate_result(context)
    if dashboard_result is not None:
        return dashboard_result
    if (
        (
            _recovery_gate_enabled(context)
            and (
                state.last_vps_recovery_status == "blocked"
                or state.last_vps_warmup_final_state == "blocked"
            )
        )
        or "shadow.dashboard_control.all_pairs_suspended"
        in supervision.control_surface.reason_codes
        or "shadow.dashboard_control.all_engines_suspended"
        in supervision.control_surface.reason_codes
    ):
        reason_codes = list(supervision.control_surface.reason_codes)
        if state.last_vps_recovery_status == "blocked":
            reason_codes.append("shadow.recovery.blocked")
        if state.last_vps_warmup_final_state == "blocked":
            reason_codes.append("shadow.warmup.blocked")
        return _skip_shadow_vps_cycle(
            context,
            event_type="recovery_gate_blocked",
            message=(
                "Governed Shadow VPS cycle skipped because recovery, warm-up, "
                "or the controlled execution surface remains blocked."
            ),
            reason_codes=tuple(dict.fromkeys(reason_codes)),
        )
    if supervision.control_surface.rollback_active:
        return _skip_shadow_vps_cycle(
            context,
            event_type="rollback_active",
            message="Governed rollback_to_light remains active; Shadow VPS cycle skipped.",
            reason_codes=supervision.control_surface.reason_codes,
        )
    if (
        _recovery_gate_enabled(context)
        and state.last_vps_warmup_final_state == "warmup_shadow_only"
    ):
        return _skip_shadow_vps_cycle(
            context,
            event_type="warmup_review_only",
            message="Governed warmup_shadow_only remains active; Shadow VPS cycle skipped.",
            reason_codes=("shadow.warmup.shadow_only",),
        )
    return None


def _resolve_shadow_vps_cycle_selection_inputs(
    context: ShadowVpsServiceRuntimeContext,
) -> ShadowVpsCycleSelection:
    return _resolve_shadow_vps_cycle_selection(
        context,
        select_next_raw_input_slot=_select_next_raw_input_slot,
        select_next_websocket_input_slot=_select_next_websocket_input_slot,
        read_live_websocket_config=_read_live_websocket_config,
        resolve_execution_runtime_projection_path=_resolve_execution_runtime_projection_path,
        resolve_regime_lite_assessment_path=_resolve_regime_lite_assessment_path,
        resolve_regime_lite_safing_recommendation_path=_resolve_regime_lite_safing_recommendation_path,
        resolve_info_stress_assessment_path=_resolve_info_stress_assessment_path,
        ensure_auto_export_from_raw_slot=_ensure_auto_export_from_raw_slot,
        ensure_auto_export_from_websocket_slot=_ensure_auto_export_from_websocket_slot,
        ensure_auto_export_from_live_websocket=_ensure_auto_export_from_live_websocket,
        pin_auto_export_session_date=_pin_auto_export_session_date,
    )


def _run_shadow_vps_orchestrator_cycle(
    context: ShadowVpsServiceRuntimeContext,
    selection: ShadowVpsCycleSelection,
) -> None:
    """Run the governed Shadow orchestration and apply successful outputs."""
    live_capture_result = _prepare_shadow_vps_selected_cycle(
        context,
        selection,
        read_live_capture_result=_read_live_capture_result,
        append_service_event=_append_service_event,
    )
    last_run = _run_shadow_vps_daily_orchestrator(
        context,
        selection,
        run_daily_orchestrator=context.launcher.orchestrate_one_shadow_day,
        read_last_run=_read_last_run,
        augment_last_run_with_operated_metadata=_augment_last_run_with_operated_metadata,
    )
    runtime_evidence_bundle_path = _write_runtime_evidence_bundle(
        service_dir=context.service_dir,
        session_date=last_run["session_date"],
        raw_slot=selection.raw_slot,
        websocket_slot=selection.websocket_slot,
        live_capture_result=live_capture_result,
        auto_snapshot_dir=selection.auto_snapshot_dir,
        auto_export_dir=selection.auto_export_dir,
        last_run=last_run,
    )
    _apply_last_run_to_shadow_vps_state(
        context,
        last_run,
        runtime_evidence_bundle_path,
        last_run_str=_last_run_str,
    )
    _persist_shadow_artifact_comparison_evidence(
        context,
        last_run,
    )
    _refresh_shadow_vps_governance_snapshots(context)
    _refresh_shadow_vps_recovery_artifacts(
        context,
        live_capture_result=live_capture_result,
    )
    execution_telemetry_status, execution_telemetry_artifact_path = (
        _write_shadow_vps_cycle_execution_telemetry(
            context,
            selection,
            last_run,
            live_capture_result,
            write_execution_telemetry_artifacts=_write_execution_telemetry_artifacts,
        )
    )
    _complete_shadow_vps_successful_cycle(
        context,
        selection,
        last_run,
        live_capture_result,
        execution_telemetry_status,
        execution_telemetry_artifact_path,
        read_runtime_evidence_bundle=_read_runtime_evidence_bundle,
        write_campaign_summary=_write_campaign_summary,
        write_service_monitoring=_write_service_monitoring,
        append_service_event=_append_service_event,
        last_run_str=_last_run_str,
    )
    refresh_shadow_vps_build17_supervision(
        context,
        append_service_event=_append_service_event,
    )
    _write_service_monitoring(context)


def _run_shadow_vps_service_cycle(
    context: ShadowVpsServiceRuntimeContext,
    *,
    continue_on_error: bool,
) -> str:
    _refresh_shadow_vps_cycle_state(context)
    _process_dashboard_command_queue(context)
    _refresh_shadow_vps_recovery_artifacts(context)
    _refresh_shadow_vps_governance_snapshots(context)
    supervision = refresh_shadow_vps_build17_supervision(
        context,
        append_service_event=_append_service_event,
    )
    _write_service_monitoring(context)
    governed_gate_result = _governed_runtime_gate_result(
        context,
        supervision=supervision,
    )
    if governed_gate_result is not None:
        return governed_gate_result
    try:
        selection = _resolve_shadow_vps_cycle_selection_inputs(context)
        if selection.next_slot is None:
            _record_shadow_vps_idle_cycle(
                context,
                append_service_event=_append_service_event,
                write_service_monitoring=_write_service_monitoring,
            )
            return "sleep"
        _run_shadow_vps_orchestrator_cycle(context, selection)
        return "next"
    except Exception as exc:
        _record_shadow_vps_failed_cycle(
            context,
            exc,
            write_service_monitoring=_write_service_monitoring,
            append_service_event=_append_service_event,
        )
        return "sleep" if continue_on_error else "break"


def run_shadow_vps_service(
    service_dir: Path, *, orchestrator_output_dir: Path | None = None,
    shadow_output_dir: Path | None = None, exports_root: Path | None = None,
    raw_inputs_root: Path | None = None, websocket_streams_root: Path | None = None,
    live_websocket_config_path: Path | None = None, live_captures_root: Path | None = None,
    auto_snapshots_root: Path | None = None, auto_exports_root: Path | None = None,
    execution_time_sync_offsets_path: Path | None = None, execution_runtime_bootstrap_enabled: bool = False,
    execution_runtime_gatekeeper_audit_path: Path | None = None,
    execution_runtime_projection_path: Path | None = None, regime_lite_assessment_path: Path | None = None,
    regime_lite_safing_recommendation_path: Path | None = None, info_stress_assessment_path: Path | None = None,
    dashboard_command_queue_root: Path | None = None,
    telegram_alert_config_path: Path | None = None, telegram_alert_key_path: Path | None = None,
    telegram_post_func: TelegramPostFunc | None = None, node_exporter_textfile_dir: Path | None = None,
    scrape_host: str = "", vps_id: str = "", node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http", node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps", poll_interval_s: float = 5.0,
    max_cycles: int | None = None, continue_on_error: bool = True,
    pid_file: Path | None = None, halt_flag_file: Path | None = None,
) -> int:
    _sync_shadow_vps_service_protocol_dependencies()
    context = _initialize_shadow_vps_service_runtime(
        service_dir=service_dir, orchestrator_output_dir=orchestrator_output_dir,
        shadow_output_dir=shadow_output_dir, exports_root=exports_root,
        raw_inputs_root=raw_inputs_root, websocket_streams_root=websocket_streams_root,
        live_websocket_config_path=live_websocket_config_path, live_captures_root=live_captures_root,
        auto_snapshots_root=auto_snapshots_root, auto_exports_root=auto_exports_root,
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        execution_runtime_bootstrap_enabled=execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=execution_runtime_gatekeeper_audit_path,
        execution_runtime_projection_path=execution_runtime_projection_path,
        regime_lite_assessment_path=regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=regime_lite_safing_recommendation_path,
        info_stress_assessment_path=info_stress_assessment_path,
        dashboard_command_queue_root=dashboard_command_queue_root,
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        telegram_post_func=telegram_post_func,
        node_exporter_textfile_dir=node_exporter_textfile_dir, scrape_host=scrape_host, vps_id=vps_id,
        node_exporter_port=node_exporter_port, node_exporter_scheme=node_exporter_scheme,
        node_exporter_metrics_path=node_exporter_metrics_path, prometheus_job_name=prometheus_job_name,
    )
    signal_controller = _ShadowVpsSignalController()
    restore_signal_handlers = _install_shadow_vps_signal_handlers(signal_controller)
    pid_file_written = _write_pid_file_if_configured(pid_file)
    should_stop = _build_should_stop_callable(
        signal_controller=signal_controller,
        halt_flag_file=halt_flag_file,
    )
    try:
        refresh_shadow_vps_build17_supervision(
            context,
            append_service_event=_append_service_event,
        )
        _write_service_monitoring(context)
        _run_shadow_vps_service_main_loop(
            context,
            poll_interval_s=poll_interval_s,
            max_cycles=max_cycles,
            continue_on_error=continue_on_error,
            run_shadow_vps_service_cycle=_run_shadow_vps_service_cycle,
            should_stop=should_stop,
            resolve_stop_reason=signal_controller.stop_reason,
            write_service_monitoring=_write_service_monitoring,
            append_service_event=_append_service_event,
        )
    finally:
        restore_signal_handlers()
        if pid_file_written and pid_file is not None:
            _clear_pid_file(pid_file)
    _finalize_shadow_vps_service_runtime(
        context,
        read_runtime_evidence_bundle=_read_runtime_evidence_bundle,
        write_campaign_summary=_write_campaign_summary,
        write_service_monitoring=_write_service_monitoring,
        append_service_event=_append_service_event,
    )
    _emit_service_output(
        context,
        emit_output_lines=_emit_output_lines,
        build_service_output_lines=_build_service_output_lines,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    _validate_input_root_selection(parser, args)
    return run_shadow_vps_service(
        args.service_dir,
        orchestrator_output_dir=args.orchestrator_output_dir,
        shadow_output_dir=args.shadow_output_dir,
        exports_root=args.exports_root,
        raw_inputs_root=args.raw_inputs_root,
        websocket_streams_root=args.websocket_streams_root,
        live_websocket_config_path=args.live_websocket_config,
        live_captures_root=args.live_captures_root,
        auto_snapshots_root=args.auto_snapshots_root,
        auto_exports_root=args.auto_exports_root,
        execution_time_sync_offsets_path=args.execution_time_sync_offsets_path,
        execution_runtime_bootstrap_enabled=args.execution_runtime_bootstrap_enabled,
        execution_runtime_gatekeeper_audit_path=(
            args.execution_runtime_gatekeeper_audit_path
        ),
        execution_runtime_projection_path=args.execution_runtime_projection_path,
        regime_lite_assessment_path=args.regime_lite_assessment_path,
        regime_lite_safing_recommendation_path=(
            args.regime_lite_safing_recommendation_path
        ),
        info_stress_assessment_path=args.info_stress_assessment_path,
        dashboard_command_queue_root=args.dashboard_command_queue_root,
        telegram_alert_config_path=args.telegram_alert_config_path,
        telegram_alert_key_path=args.telegram_alert_key_path,
        node_exporter_textfile_dir=args.node_exporter_textfile_dir,
        scrape_host=args.scrape_host,
        vps_id=args.vps_id,
        node_exporter_port=args.node_exporter_port,
        node_exporter_scheme=args.node_exporter_scheme,
        node_exporter_metrics_path=args.node_exporter_metrics_path,
        prometheus_job_name=args.prometheus_job_name,
        poll_interval_s=max(0.0, args.poll_interval_s),
        max_cycles=args.max_cycles,
        continue_on_error=not args.stop_on_error,
        pid_file=args.pid_file,
        halt_flag_file=args.halt_flag_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
