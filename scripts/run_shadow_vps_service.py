#!/usr/bin/env python3
"""Run the autonomous long-running VPS Shadow service."""

from __future__ import annotations

from collections.abc import Callable
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
from protocols import (  # noqa: E402
    ShadowVpsServiceStatus,
    build_binance_execution_runtime_bootstrap_bundle,
    capture_live_websocket_snapshot_batch,
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
from shadow_vps_service_event_support import (  # noqa: E402
    _append_service_event,
)
from shadow_vps_service_execution_support import (  # noqa: E402
    _apply_last_run_to_shadow_vps_state,
    _complete_shadow_vps_successful_cycle,
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


def _run_shadow_vps_service_cycle(
    context: ShadowVpsServiceRuntimeContext,
    *,
    continue_on_error: bool,
) -> str:
    _refresh_shadow_vps_cycle_state(context)
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
    telegram_alert_config_path: Path | None = None, telegram_alert_key_path: Path | None = None,
    telegram_post_func: TelegramPostFunc | None = None, node_exporter_textfile_dir: Path | None = None,
    scrape_host: str = "", vps_id: str = "", node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http", node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps", poll_interval_s: float = 5.0,
    max_cycles: int | None = None, continue_on_error: bool = True,
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
        telegram_alert_config_path=telegram_alert_config_path,
        telegram_alert_key_path=telegram_alert_key_path,
        telegram_post_func=telegram_post_func,
        node_exporter_textfile_dir=node_exporter_textfile_dir, scrape_host=scrape_host, vps_id=vps_id,
        node_exporter_port=node_exporter_port, node_exporter_scheme=node_exporter_scheme,
        node_exporter_metrics_path=node_exporter_metrics_path, prometheus_job_name=prometheus_job_name,
    )
    signal_controller = _ShadowVpsSignalController()
    restore_signal_handlers = _install_shadow_vps_signal_handlers(signal_controller)
    try:
        _run_shadow_vps_service_main_loop(
            context,
            poll_interval_s=poll_interval_s,
            max_cycles=max_cycles,
            continue_on_error=continue_on_error,
            run_shadow_vps_service_cycle=_run_shadow_vps_service_cycle,
            should_stop=signal_controller.stop_requested,
            resolve_stop_reason=signal_controller.stop_reason,
            write_service_monitoring=_write_service_monitoring,
            append_service_event=_append_service_event,
        )
    finally:
        restore_signal_handlers()
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
