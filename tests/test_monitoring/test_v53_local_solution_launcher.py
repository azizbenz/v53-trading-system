from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType

import pytest

from monitoring.local_observability_stack import LocalObservabilityStackSummary


def _load_launcher_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_v53_local_solution.py"
    module_name = "test_run_v53_local_solution_launcher"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-v53-local-solution-launcher", label)


def _observability_summary(output_dir: Path) -> LocalObservabilityStackSummary:
    return LocalObservabilityStackSummary(
        output_dir=str(output_dir),
        prom_text_path=str(output_dir / "shadow_vps_service_observability.prom"),
        dashboard_json_path=str(output_dir / "v53_shadow_vps_local_grafana.dashboard.json"),
        dashboard_summary_path=str(output_dir / "v53_shadow_vps_local_grafana.summary.json"),
        bootstrap_summary_path=str(output_dir / "local_grafana_bootstrap.summary.json"),
        prometheus_config_path=str(output_dir / "prometheus.bridge.generated.yml"),
        bridge_url="http://127.0.0.1:19100/metrics",
        prometheus_url="http://127.0.0.1:9090",
        grafana_url="http://127.0.0.1:3000",
        bridge_status="started",
        prometheus_status="started",
        grafana_status="started",
        bridge_pid=101,
        prometheus_pid=102,
        grafana_pid=103,
        grafana_server_exe="C:/Grafana/grafana-server.exe",
        prometheus_exe="C:/Prometheus/prometheus.exe",
        bridge_log_path=str(output_dir / "bridge.log"),
        prometheus_log_path=str(output_dir / "prometheus.log"),
        grafana_log_path=str(output_dir / "grafana.log"),
    )


def test_run_v53_local_solution_loads_env_and_writes_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("authenticated")
    try:
        env_path = scratch / ".env"
        env_path.write_text(
            "BINANCE_API_KEY=demo-key\nBINANCE_API_SECRET=demo-secret\n",
            encoding="utf-8",
        )
        prom_path = scratch / "service" / "shadow_vps_service_observability.prom"
        prom_path.parent.mkdir(parents=True, exist_ok=True)
        prom_path.write_text("metric 1\n", encoding="utf-8")
        observed: dict[str, object] = {}

        def _fake_shadow_campaign(**kwargs: object) -> dict[str, object]:
            observed["shadow_kwargs"] = kwargs
            env = kwargs["env"]
            observed["shadow_env"] = {
                "BINANCE_API_KEY": env["BINANCE_API_KEY"],
                "BINANCE_API_SECRET": env["BINANCE_API_SECRET"],
                "V53_BINANCE_API_KEY": env["V53_BINANCE_API_KEY"],
                "V53_BINANCE_SECRET_KEY": env["V53_BINANCE_SECRET_KEY"],
            }
            return {
                "campaign_root": str(scratch / "campaign"),
                "live_websocket_config": str(scratch / "campaign" / "live_websocket_config.json"),
                "service_dir": str(prom_path.parent),
                "service_pid_file": str(prom_path.parent / "shadow_vps_service.pid"),
                "dashboard_command_queue_root": str(prom_path.parent / "dashboard_command_queue"),
                "observability_prom": str(prom_path),
                "observability_export": str(prom_path.parent / "shadow_vps_service_observability_export.json"),
                "service_launched": False,
                "user_data_stream_enabled": True,
            }

        def _fake_observability_stack(**kwargs: object) -> LocalObservabilityStackSummary:
            observed["observability_kwargs"] = kwargs
            output_dir = Path(kwargs["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            return _observability_summary(output_dir)

        def _fake_launch_shadow_service(**kwargs: object):
            observed["service_kwargs"] = kwargs
            prom_path.write_text("metric 1\n", encoding="utf-8")
            (prom_path.parent / "shadow_vps_service_monitoring_backend_payload.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (prom_path.parent / "shadow_vps_service.pid").write_text("12345", encoding="utf-8")
            return launcher.ShadowServiceLaunchSummary(
                shadow_service_log_path=str((prom_path.parent / "shadow_vps_service.launch.log").resolve()),
                shadow_service_pid=12345,
            )

        def _fake_launch_cockpit(**kwargs: object):
            observed["cockpit_kwargs"] = kwargs
            return launcher.CockpitLaunchSummary(
                cockpit_url="http://127.0.0.1:8080",
                cockpit_log_path=str((scratch / "output" / "cockpit" / "cockpit.log").resolve()),
                cockpit_pid=4242,
            )

        monkeypatch.setattr(launcher, "_run_shadow_campaign", _fake_shadow_campaign)
        monkeypatch.setattr(launcher, "_launch_shadow_service", _fake_launch_shadow_service)
        monkeypatch.setattr(launcher, "launch_local_observability_stack", _fake_observability_stack)
        monkeypatch.setattr(launcher, "_launch_cockpit", _fake_launch_cockpit)
        monkeypatch.setattr(launcher.webbrowser, "open", lambda url: url == "http://127.0.0.1:8080")

        summary = launcher.run_v53_local_solution(
            api_env_file=env_path,
            output_dir=scratch / "output",
            campaign_root=scratch / "campaign",
            public_only=False,
            enable_time_sync_probe=True,
            stop_on_error=True,
            grafana_password="admin",
            grafana_user="admin",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            bridge_host="127.0.0.1",
            bridge_port=19100,
            prometheus_exe=None,
            grafana_server_exe=None,
            grafana_home=None,
            scrape_interval="5s",
            evaluation_interval="5s",
            readiness_timeout_s=30.0,
            no_open_browser=False,
            powershell_executable="powershell",
        )

        assert summary.credentials_mode == "authenticated"
        assert summary.cockpit_opened is True
        assert summary.cockpit_started is True
        assert summary.cockpit_url == "http://127.0.0.1:8080"
        assert observed["shadow_env"] == {
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
            "V53_BINANCE_API_KEY": "demo-key",
            "V53_BINANCE_SECRET_KEY": "demo-secret",
        }
        assert observed["shadow_kwargs"]["public_only"] is False
        assert observed["shadow_kwargs"]["enable_time_sync_probe"] is True
        assert observed["shadow_kwargs"]["enable_execution_runtime_bootstrap"] is True
        assert observed["shadow_kwargs"]["skip_service_launch"] is True
        assert observed["service_kwargs"]["service_dir"] == prom_path.parent.resolve()
        assert observed["cockpit_kwargs"]["host"] == "127.0.0.1"
        assert observed["cockpit_kwargs"]["port"] == 8080
        assert observed["cockpit_kwargs"]["dashboard_command_queue_root"] == (
            prom_path.parent / "dashboard_command_queue"
        )
        assert summary.shadow_service_launched is True
        assert summary.shadow_service_pid == 12345
        assert Path(summary.shadow_observability_prom_path) == prom_path.resolve()
        assert Path(summary.dashboard_command_queue_root) == (
            prom_path.parent / "dashboard_command_queue"
        ).resolve()
        launch_summary_path = Path(summary.output_dir) / "launch.summary.json"
        assert launch_summary_path.exists()
        payload = json.loads(launch_summary_path.read_text(encoding="utf-8"))
        assert payload["grafana_url"] == "http://127.0.0.1:3000"
        assert payload["cockpit_url"] == "http://127.0.0.1:8080"
        assert payload["credentials_mode"] == "authenticated"
        assert Path(payload["dashboard_command_queue_root"]) == (
            prom_path.parent / "dashboard_command_queue"
        ).resolve()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_cockpit_uses_background_process_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("cockpit_isolation")
    try:
        service_dir = scratch / "service"
        service_dir.mkdir(parents=True, exist_ok=True)
        observed: dict[str, object] = {}

        class _FakePopen:
            def __init__(self, cmd, **kwargs):  # noqa: ANN001
                observed["command"] = tuple(cmd)
                observed["kwargs"] = kwargs
                self.pid = 9876
                self.returncode = None

            def poll(self):  # noqa: ANN001
                return None

        monkeypatch.setattr(launcher.subprocess, "Popen", _FakePopen)
        monkeypatch.setattr(
            launcher,
            "_wait_for_cockpit_ready",
            lambda *, url, timeout_s, process: observed.update(
                {"ready_url": url, "ready_timeout_s": timeout_s, "ready_pid": process.pid}
            ),
        )

        summary = launcher._launch_cockpit(
            repo_root=Path(launcher.REPO_ROOT),
            python_executable=sys.executable,
            output_dir=scratch / "output",
            service_dir=service_dir,
            campaign_root=scratch / "campaign",
            live_websocket_config=scratch / "campaign" / "live_websocket_config.json",
            observability_output_dir=scratch / "observability",
            dashboard_command_queue_root=scratch / "queue",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            host="127.0.0.1",
            port=8080,
            readiness_timeout_s=12.0,
            env={"PATH": "demo"},
        )

        popen_kwargs = observed["kwargs"]
        assert popen_kwargs["stdin"] is launcher.subprocess.DEVNULL
        assert popen_kwargs["stdout"] is not None
        assert popen_kwargs["stderr"] == launcher.subprocess.STDOUT
        assert popen_kwargs["text"] is True
        if launcher.os.name == "nt":
            assert popen_kwargs["creationflags"] == (
                launcher.subprocess.CREATE_NEW_PROCESS_GROUP
                | launcher.subprocess.CREATE_NO_WINDOW
            )
        else:
            assert popen_kwargs["start_new_session"] is True
        assert observed["ready_url"] == "http://127.0.0.1:8080"
        assert observed["ready_pid"] == 9876
        assert summary.cockpit_pid == 9876
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_v53_local_solution_downgrades_to_public_only_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    launcher = _load_launcher_module()
    scratch = _scratch_dir("missing_credentials")
    try:
        prom_path = scratch / "service" / "shadow_vps_service_observability.prom"
        prom_path.parent.mkdir(parents=True, exist_ok=True)
        prom_path.write_text("metric 1\n", encoding="utf-8")
        observed: dict[str, object] = {}

        for name in (
            "BINANCE_API_KEY",
            "BINANCE_API_SECRET",
            "V53_BINANCE_API_KEY",
            "V53_BINANCE_SECRET_KEY",
        ):
            monkeypatch.delenv(name, raising=False)

        def _fake_shadow_campaign(**kwargs: object) -> dict[str, object]:
            observed["shadow_kwargs"] = kwargs
            observed["public_only"] = kwargs["public_only"]
            return {
                "campaign_root": str(scratch / "campaign"),
                "live_websocket_config": str(scratch / "campaign" / "config.json"),
                "service_dir": str(prom_path.parent),
                "service_pid_file": str(prom_path.parent / "shadow_vps_service.pid"),
                "observability_prom": str(prom_path),
                "observability_export": str(prom_path.parent / "export.json"),
                "service_launched": False,
                "user_data_stream_enabled": False,
            }

        def _fake_observability_stack(**kwargs: object) -> LocalObservabilityStackSummary:
            output_dir = Path(kwargs["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            return _observability_summary(output_dir)

        def _fake_launch_shadow_service(**kwargs: object):
            observed["service_kwargs"] = kwargs
            prom_path.write_text("metric 1\n", encoding="utf-8")
            (prom_path.parent / "shadow_vps_service_monitoring_backend_payload.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (prom_path.parent / "shadow_vps_service.pid").write_text("23456", encoding="utf-8")
            return launcher.ShadowServiceLaunchSummary(
                shadow_service_log_path=str((prom_path.parent / "shadow_vps_service.launch.log").resolve()),
                shadow_service_pid=23456,
            )

        def _fake_launch_cockpit(**kwargs: object):
            return launcher.CockpitLaunchSummary(
                cockpit_url="http://127.0.0.1:8080",
                cockpit_log_path=str((scratch / "output" / "cockpit" / "cockpit.log").resolve()),
                cockpit_pid=4242,
            )

        monkeypatch.setattr(launcher, "_run_shadow_campaign", _fake_shadow_campaign)
        monkeypatch.setattr(launcher, "_launch_shadow_service", _fake_launch_shadow_service)
        monkeypatch.setattr(launcher, "launch_local_observability_stack", _fake_observability_stack)
        monkeypatch.setattr(launcher, "_launch_cockpit", _fake_launch_cockpit)
        monkeypatch.setattr(launcher.webbrowser, "open", lambda url: False)

        with caplog.at_level(logging.WARNING):
            summary = launcher.run_v53_local_solution(
                api_env_file=scratch / ".env",
                output_dir=scratch / "output",
                campaign_root=None,
                public_only=False,
                enable_time_sync_probe=False,
                stop_on_error=False,
                grafana_password="admin",
                grafana_user="admin",
                grafana_url="http://127.0.0.1:3000",
                prometheus_url="http://127.0.0.1:9090",
                bridge_host="127.0.0.1",
                bridge_port=19100,
                prometheus_exe=None,
                grafana_server_exe=None,
                grafana_home=None,
                scrape_interval="5s",
                evaluation_interval="5s",
                readiness_timeout_s=30.0,
                no_open_browser=True,
                powershell_executable="powershell",
            )

        assert summary.credentials_mode == "public_only"
        assert observed["public_only"] is True
        assert observed["shadow_kwargs"]["enable_execution_runtime_bootstrap"] is True
        assert observed["shadow_kwargs"]["skip_service_launch"] is True
        assert any("public-only mode" in record.message for record in caplog.records)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_v53_local_solution_allows_public_only_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("public_only")
    try:
        for name in (
            "BINANCE_API_KEY",
            "BINANCE_API_SECRET",
            "V53_BINANCE_API_KEY",
            "V53_BINANCE_SECRET_KEY",
        ):
            monkeypatch.delenv(name, raising=False)
        prom_path = scratch / "service" / "shadow_vps_service_observability.prom"
        prom_path.parent.mkdir(parents=True, exist_ok=True)
        prom_path.write_text("metric 2\n", encoding="utf-8")
        observed: dict[str, object] = {}

        def _fake_shadow_campaign(**kwargs: object) -> dict[str, object]:
            observed["shadow_kwargs"] = kwargs
            env = kwargs["env"]
            observed["has_binance_key"] = "BINANCE_API_KEY" in env and bool(env["BINANCE_API_KEY"])
            return {
                "campaign_root": str(scratch / "campaign"),
                "live_websocket_config": str(scratch / "campaign" / "live_websocket_config.json"),
                "service_dir": str(prom_path.parent),
                "service_pid_file": str(prom_path.parent / "shadow_vps_service.pid"),
                "observability_prom": str(prom_path),
                "observability_export": str(prom_path.parent / "shadow_vps_service_observability_export.json"),
                "service_launched": False,
                "user_data_stream_enabled": False,
            }

        def _fake_launch_shadow_service(**kwargs: object):
            observed["service_kwargs"] = kwargs
            prom_path.write_text("metric 2\n", encoding="utf-8")
            (prom_path.parent / "shadow_vps_service_monitoring_backend_payload.json").write_text(
                "{}",
                encoding="utf-8",
            )
            (prom_path.parent / "shadow_vps_service.pid").write_text("31337", encoding="utf-8")
            return launcher.ShadowServiceLaunchSummary(
                shadow_service_log_path=str((prom_path.parent / "shadow_vps_service.launch.log").resolve()),
                shadow_service_pid=31337,
            )

        def _fake_launch_cockpit(**kwargs: object):
            observed["cockpit_kwargs"] = kwargs
            return launcher.CockpitLaunchSummary(
                cockpit_url="http://127.0.0.1:8080",
                cockpit_log_path=str((scratch / "output" / "cockpit" / "cockpit.log").resolve()),
                cockpit_pid=31337,
            )

        monkeypatch.setattr(launcher, "_run_shadow_campaign", _fake_shadow_campaign)
        monkeypatch.setattr(launcher, "_launch_shadow_service", _fake_launch_shadow_service)
        monkeypatch.setattr(
            launcher,
            "launch_local_observability_stack",
            lambda **kwargs: _observability_summary(Path(kwargs["output_dir"])),
        )
        monkeypatch.setattr(launcher, "_launch_cockpit", _fake_launch_cockpit)
        monkeypatch.setattr(launcher.webbrowser, "open", lambda url: True)

        summary = launcher.run_v53_local_solution(
            api_env_file=scratch / ".env",
            output_dir=scratch / "output",
            campaign_root=None,
            public_only=True,
            enable_time_sync_probe=False,
            stop_on_error=False,
            grafana_password="admin",
            grafana_user="admin",
            grafana_url="http://127.0.0.1:3000",
            prometheus_url="http://127.0.0.1:9090",
            bridge_host="127.0.0.1",
            bridge_port=19100,
            prometheus_exe=None,
            grafana_server_exe=None,
            grafana_home=None,
            scrape_interval="5s",
            evaluation_interval="5s",
            readiness_timeout_s=30.0,
            no_open_browser=True,
            powershell_executable="powershell",
        )

        assert summary.credentials_mode == "public_only"
        assert summary.shadow_user_data_stream_enabled is False
        assert observed["shadow_kwargs"]["public_only"] is True
        assert observed["shadow_kwargs"]["enable_execution_runtime_bootstrap"] is True
        assert observed["shadow_kwargs"]["skip_service_launch"] is True
        assert observed["has_binance_key"] is False
        assert summary.cockpit_opened is False
        assert summary.cockpit_url == "http://127.0.0.1:8080"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_v53_local_solution_launcher_main_delegates_to_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("cli")
    try:
        env_path = scratch / ".env"
        env_path.write_text("BINANCE_API_KEY=cli\nBINANCE_API_SECRET=cli-secret\n", encoding="utf-8")
        captured_args: dict[str, object] = {}

        def _fake_run_v53_local_solution(**kwargs: object):
            captured_args.update(kwargs)
            output_dir = Path(kwargs["output_dir"]).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            return launcher.V53LocalSolutionLaunchSummary(
                output_dir=str(output_dir),
                api_env_file=str(Path(kwargs["api_env_file"]).resolve()),
                credentials_mode="authenticated",
                campaign_root=str((scratch / "campaign").resolve()),
                shadow_live_websocket_config=str((scratch / "campaign" / "live_websocket_config.json").resolve()),
                shadow_service_dir=str((scratch / "service").resolve()),
                dashboard_command_queue_root=str((scratch / "service" / "dashboard_command_queue").resolve()),
                shadow_observability_prom_path=str((scratch / "service" / "shadow_vps_service_observability.prom").resolve()),
                shadow_observability_export_path=str((scratch / "service" / "shadow_vps_service_observability_export.json").resolve()),
                shadow_service_log_path=str((scratch / "service" / "shadow_vps_service.launch.log").resolve()),
                shadow_service_pid=5151,
                shadow_service_launched=True,
                shadow_user_data_stream_enabled=True,
                observability_output_dir=str((output_dir / "local_observability_stack").resolve()),
                observability_summary_path=str((output_dir / "local_observability_stack.summary.json").resolve()),
                prometheus_url="http://127.0.0.1:9090",
                grafana_url="http://127.0.0.1:3000",
                cockpit_url="http://127.0.0.1:8080",
                cockpit_log_path=str((output_dir / "cockpit" / "cockpit.log").resolve()),
                cockpit_pid=5150,
                cockpit_started=True,
                grafana_opened=False,
                cockpit_opened=False,
            )

        monkeypatch.setattr(launcher, "run_v53_local_solution", _fake_run_v53_local_solution)

        exit_code = launcher.main(
            [
                "--api-env-file",
                str(env_path),
                "--output-dir",
                str(scratch / "output"),
                "--public-only",
                "--no-open-browser",
            ]
        )

        assert exit_code == 0
        assert captured_args["api_env_file"] == env_path
        assert captured_args["public_only"] is True
        assert captured_args["no_open_browser"] is True
        assert captured_args["enable_execution_runtime_bootstrap"] is True
        assert captured_args["readiness_timeout_s"] == 90.0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_v53_local_solution_launcher_main_can_disable_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("cli_disable_bootstrap")
    try:
        env_path = scratch / ".env"
        env_path.write_text("BINANCE_API_KEY=cli\nBINANCE_API_SECRET=cli-secret\n", encoding="utf-8")
        captured_args: dict[str, object] = {}

        def _fake_run_v53_local_solution(**kwargs: object):
            captured_args.update(kwargs)
            output_dir = Path(kwargs["output_dir"]).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            return launcher.V53LocalSolutionLaunchSummary(
                output_dir=str(output_dir),
                api_env_file=str(Path(kwargs["api_env_file"]).resolve()),
                credentials_mode="authenticated",
                campaign_root=str((scratch / "campaign").resolve()),
                shadow_live_websocket_config=str((scratch / "campaign" / "live_websocket_config.json").resolve()),
                shadow_service_dir=str((scratch / "service").resolve()),
                dashboard_command_queue_root=str((scratch / "service" / "dashboard_command_queue").resolve()),
                shadow_observability_prom_path=str((scratch / "service" / "shadow_vps_service_observability.prom").resolve()),
                shadow_observability_export_path=str((scratch / "service" / "shadow_vps_service_observability_export.json").resolve()),
                shadow_service_log_path=str((scratch / "service" / "shadow_vps_service.launch.log").resolve()),
                shadow_service_pid=5151,
                shadow_service_launched=True,
                shadow_user_data_stream_enabled=True,
                observability_output_dir=str((output_dir / "local_observability_stack").resolve()),
                observability_summary_path=str((output_dir / "local_observability_stack.summary.json").resolve()),
                prometheus_url="http://127.0.0.1:9090",
                grafana_url="http://127.0.0.1:3000",
                cockpit_url="http://127.0.0.1:8080",
                cockpit_log_path=str((output_dir / "cockpit" / "cockpit.log").resolve()),
                cockpit_pid=5150,
                cockpit_started=True,
                grafana_opened=False,
                cockpit_opened=False,
            )

        monkeypatch.setattr(launcher, "run_v53_local_solution", _fake_run_v53_local_solution)

        exit_code = launcher.main(
            [
                "--api-env-file",
                str(env_path),
                "--output-dir",
                str(scratch / "output"),
                "--disable-execution-runtime-bootstrap",
                "--no-open-browser",
            ]
        )

        assert exit_code == 0
        assert captured_args["enable_execution_runtime_bootstrap"] is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
