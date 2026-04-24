from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandRequest,
    DeploymentState,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from protocols import initialize_dashboard_command_queue, write_dashboard_command_request


def _load_service_module() -> ModuleType:
    from tests.test_protocols.test_shadow_vps_service_launcher import _load_service_module as load

    return load()


def _scratch_dir(label: str) -> Path:
    from tests.test_protocols.test_shadow_vps_service_launcher import _scratch_dir as scratch

    return scratch(label)


def _write_daily_export(export_dir: Path, session_date: str, run_suffix: str) -> None:
    from tests.test_protocols.test_shadow_vps_service_launcher import _write_daily_export as write

    write(export_dir, session_date, run_suffix)


def _write_live_websocket_config(config_path: Path, session_date: str) -> None:
    from tests.test_protocols.test_shadow_vps_service_launcher import _write_live_websocket_config as write

    write(config_path, session_date)


def _write_validated_binance_credential_state(service_dir: Path) -> None:
    from tests.test_protocols.test_shadow_vps_service_launcher import (
        _write_validated_binance_credential_state as write,
    )

    write(service_dir)


def _read_events(service_dir: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (service_dir / "shadow_vps_service.events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]


def test_shadow_vps_service_blocks_live_cycle_when_recovery_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("recovery_gate_blocked")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        _write_live_websocket_config(live_config_path, "2026-04-02")
        _write_validated_binance_credential_state(service_dir)

        def _unexpected_orchestrator(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("orchestrator should be skipped while recovery is blocked")

        monkeypatch.setattr(
            service,
            "_run_shadow_vps_daily_orchestrator",
            _unexpected_orchestrator,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        events = _read_events(service_dir)

        assert exit_code == 0
        assert state["service_status"] == "degraded"
        assert state["idle_count"] == 1
        assert state["success_count"] == 0
        assert state["last_live_complete_summary_ref"].endswith("live_complete_run.summary.json")
        assert state["last_live_complete_operator_report_ref"].endswith(
            "live_complete_operator_audit_report.json"
        )
        assert monitoring_payload["last_live_complete_status"] == "blocked"
        assert monitoring_payload["last_live_complete_operator_report_status"] == "blocked"
        assert any(event["event_type"] == "recovery_gate_blocked" for event in events)
        assert not any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_skips_live_cycle_during_warmup_shadow_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("warmup_shadow_only_gate")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_config_path = output_dir / "live_websocket_config.json"
        _write_live_websocket_config(live_config_path, "2026-04-02")
        _write_validated_binance_credential_state(service_dir)

        def _forced_warmup_shadow_only(
            context: object,
            live_capture_result: object | None = None,
        ) -> None:
            _ = live_capture_result
            recovery = VpsRecoveryReadinessReport(
                report_id="recovery-shadow-only",
                runtime_mode=RuntimeMode.SHADOW,
                deployment_state=DeploymentState.SHADOW,
                checks=(
                    VpsRecoveryCheck(
                        check_id="market_data_capture",
                        status=VpsRecoveryCheckStatus.PASSED,
                    ),
                ),
                eligible_to_trade=False,
            )
            warmup = VpsWarmupRunSummary(
                run_id="warmup-shadow-only",
                runtime_mode=RuntimeMode.SHADOW,
                final_state=VpsWarmupState.WARMUP_SHADOW_ONLY,
                phase_sequence=(
                    VpsWarmupState.COLD_START,
                    VpsWarmupState.WARMUP_SHADOW_ONLY,
                ),
                report=recovery,
                eligible_to_trade=False,
            )
            recovery_path = context.service_dir / "vps_recovery_readiness.report.json"
            warmup_path = context.service_dir / "vps_warmup_run.summary.json"
            recovery_path.write_text(recovery.model_dump_json(indent=2), encoding="utf-8")
            warmup_path.write_text(warmup.model_dump_json(indent=2), encoding="utf-8")
            context.store.update_state(
                last_vps_recovery_readiness_report_ref=str(recovery_path.resolve()),
                last_vps_recovery_status="review_only",
                last_vps_recovery_eligible_to_trade=False,
                last_vps_warmup_summary_ref=str(warmup_path.resolve()),
                last_vps_warmup_final_state=VpsWarmupState.WARMUP_SHADOW_ONLY.value,
                last_vps_warmup_eligible_to_trade=False,
            )

        def _unexpected_orchestrator(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("orchestrator should be skipped during warmup_shadow_only")

        monkeypatch.setattr(
            service,
            "_refresh_shadow_vps_recovery_artifacts",
            _forced_warmup_shadow_only,
        )
        monkeypatch.setattr(
            service,
            "_run_shadow_vps_daily_orchestrator",
            _unexpected_orchestrator,
        )

        exit_code = service.run_shadow_vps_service(
            service_dir,
            orchestrator_output_dir=orchestrator_dir,
            shadow_output_dir=shadow_output_dir,
            live_websocket_config_path=live_config_path,
            max_cycles=1,
            poll_interval_s=0.0,
        )

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        events = _read_events(service_dir)

        assert exit_code == 0
        assert state["idle_count"] == 1
        assert state["last_vps_warmup_final_state"] == "warmup_shadow_only"
        assert any(event["event_type"] == "warmup_review_only" for event in events)
        assert not any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_persists_build17_surface_when_dashboard_controls_mutate_runtime() -> None:
    service = _load_service_module()
    output_dir = _scratch_dir("dashboard_control_build17_surface")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        command_queue_root = output_dir / "dashboard_command_queue"
        export_day = exports_root / "2026-04-02"
        export_day.mkdir(parents=True, exist_ok=False)
        _write_daily_export(export_day, "2026-04-02", "dashboard-controls")
        initialize_dashboard_command_queue(command_queue_root)
        requests = (
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_000,
                correlation_id="corr-rollback",
                request_id="req-rollback",
                command_kind=DashboardGovernedCommandKind.ROLLBACK_TO_LIGHT,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="rollback to light from grafana",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_001,
                correlation_id="corr-suspend-pair",
                request_id="req-suspend-pair",
                command_kind=DashboardGovernedCommandKind.SUSPEND_PAIR,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="suspend pair from grafana",
                target_pair="BTCUSDT",
            ),
            DashboardGovernedCommandRequest(
                timestamp_ms=1_700_000_000_002,
                correlation_id="corr-suspend-engine",
                request_id="req-suspend-engine",
                command_kind=DashboardGovernedCommandKind.SUSPEND_ENGINE,
                source_runtime_mode=RuntimeMode.LOCAL_REPLAY,
                target_runtime_mode=RuntimeMode.LIVE,
                operator_reason="suspend engine from grafana",
                target_engine="engine_c",
            ),
        )
        for request in requests:
            write_dashboard_command_request(command_queue_root, request)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--dashboard-command-queue-root",
                str(command_queue_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(encoding="utf-8")
        )
        monitoring_payload = json.loads(
            (
                service_dir / "shadow_vps_service_monitoring_backend_payload.json"
            ).read_text(encoding="utf-8")
        )
        live_complete_summary = json.loads(
            (service_dir / "live_complete_run.summary.json").read_text(encoding="utf-8")
        )
        operator_report = json.loads(
            (service_dir / "live_complete_operator_audit_report.json").read_text(
                encoding="utf-8"
            )
        )
        events = _read_events(service_dir)

        assert exit_code == 0
        assert state["dashboard_control_target_profile"] == "light"
        assert state["dashboard_control_target_deployment_state"] == "rollback"
        assert state["dashboard_control_suspended_pairs"] == ["BTCUSDT"]
        assert state["dashboard_control_suspended_engines"] == ["engine_c"]
        assert state["last_live_complete_summary_ref"].endswith("live_complete_run.summary.json")
        assert state["last_live_complete_operator_report_ref"].endswith(
            "live_complete_operator_audit_report.json"
        )
        assert live_complete_summary["decision"]["verdict"] == "blocked"
        assert operator_report["status"] == "blocked"
        assert monitoring_payload["last_live_complete_status"] == "blocked"
        assert monitoring_payload["last_live_complete_operator_report_status"] == "blocked"
        assert any(event["event_type"] == "rollback_active" for event in events)
        assert any(event["event_type"] == "suspended_pair_active" for event in events)
        assert any(event["event_type"] == "suspended_engine_active" for event in events)
        assert any(event["event_type"] == "operator_report_written" for event in events)
        assert not any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
