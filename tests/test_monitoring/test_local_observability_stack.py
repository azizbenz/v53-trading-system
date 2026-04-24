from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from monitoring.local_grafana_api import LocalGrafanaBootstrapSummary
import monitoring.local_observability_stack as stack


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-observability-stack", label)


class _FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_build_local_bridge_prometheus_config_text_targets_bridge() -> None:
    config_text = stack.build_local_bridge_prometheus_config_text(
        metrics_target="127.0.0.1:19100",
        scrape_interval="5s",
        evaluation_interval="5s",
    )

    assert "v53_shadow_vps_bridge" in config_text
    assert "127.0.0.1:19100" in config_text
    assert "shadow_vps_metrics_bridge" in config_text


def test_launch_local_observability_stack_starts_missing_services_and_writes_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("start_all")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 7\n", encoding="utf-8")
        output_dir = scratch / "output"
        started_commands: list[tuple[tuple[str, ...], Path | None, Path]] = []
        waited_urls: list[str] = []

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            started_commands.append((command, cwd, log_path))
            return _FakeProcess(100 + len(started_commands))

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            waited_urls.append(url)

        def _fake_bootstrap(**kwargs: object) -> LocalGrafanaBootstrapSummary:
            return LocalGrafanaBootstrapSummary(
                grafana_url=str(kwargs["grafana_url"]),
                datasource_name="Prometheus",
                datasource_uid="prometheus",
                dashboard_uid="v53-shadow-vps-local",
                dashboard_title="V5.3 Shadow VPS - Local Dev Observability",
                datasource_status_code=200,
                dashboard_status_code=200,
                output_path=str(kwargs["output_path"]),
            )

        def _fake_port_is_listening(host: str, port: int) -> bool:
            return False

        def _fake_resolve_executable_path(
            *,
            explicit_path: str | Path | None,
            env_var_names: tuple[str, ...],
            executable_names: tuple[str, ...],
            candidate_paths: tuple[Path, ...],
        ) -> Path | None:
            if "prometheus.exe" in executable_names:
                return scratch / "bin" / "prometheus.exe"
            return scratch / "bin" / "grafana-server.exe"

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)

        summary = stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert summary.bridge_status == "started"
        assert summary.prometheus_status == "started"
        assert summary.grafana_status == "started"
        assert summary.bridge_pid == 101
        assert summary.prometheus_pid == 102
        assert summary.grafana_pid == 103
        assert len(started_commands) == 3
        assert waited_urls == [
            "http://127.0.0.1:19100/-/ready",
            "http://127.0.0.1:9090/-/ready",
            "http://127.0.0.1:3000/api/health",
        ]
        assert (output_dir / "v53_shadow_vps_local_grafana.dashboard.json").exists()
        assert (output_dir / "v53_shadow_vps_local_grafana.summary.json").exists()
        assert (output_dir / "local_grafana_bootstrap.summary.json").exists()
        assert (output_dir / "local_observability_stack.summary.json").exists()
        assert (output_dir / "grafana_data").is_dir()
        assert (output_dir / "grafana_logs").is_dir()
        assert (output_dir / "grafana_plugins").is_dir()
        assert "127.0.0.1:19100" in (
            output_dir / "prometheus.bridge.generated.yml"
        ).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_local_observability_stack_reuses_running_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("reuse_running")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 11\n", encoding="utf-8")
        output_dir = scratch / "output"
        waited_urls: list[str] = []

        def _unexpected_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            raise AssertionError(f"Unexpected process start: {command}")

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            waited_urls.append(url)

        def _fake_bootstrap(**kwargs: object) -> LocalGrafanaBootstrapSummary:
            return LocalGrafanaBootstrapSummary(
                grafana_url=str(kwargs["grafana_url"]),
                datasource_name="Prometheus",
                datasource_uid="prometheus",
                dashboard_uid="v53-shadow-vps-local",
                dashboard_title="V5.3 Shadow VPS - Local Dev Observability",
                datasource_status_code=200,
                dashboard_status_code=200,
                output_path=str(kwargs["output_path"]),
            )

        def _fake_port_is_listening(host: str, port: int) -> bool:
            return (host, port) in {
                ("127.0.0.1", 19100),
                ("127.0.0.1", 9090),
                ("127.0.0.1", 3000),
            }

        monkeypatch.setattr(stack, "_start_detached_process", _unexpected_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)

        summary = stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert summary.bridge_status == "already_listening"
        assert summary.prometheus_status == "already_listening"
        assert summary.grafana_status == "already_listening"
        assert summary.bridge_pid is None
        assert summary.prometheus_pid is None
        assert summary.grafana_pid is None
        assert waited_urls == [
            "http://127.0.0.1:19100/-/ready",
            "http://127.0.0.1:9090/-/ready",
            "http://127.0.0.1:3000/api/health",
        ]
        summary_payload = json.loads(
            (output_dir / "local_observability_stack.summary.json").read_text(
                encoding="utf-8"
            )
        )
        assert summary_payload["grafana_status"] == "already_listening"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
