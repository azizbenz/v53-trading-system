from __future__ import annotations

import json
from pathlib import Path
import shutil
from urllib.error import HTTPError

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

        def _fake_import_dashboard(**kwargs: object) -> tuple[int, str]:
            return 200, "v53-local-lab"

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", _fake_import_dashboard)

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
        bootstrap_payload = json.loads(
            (output_dir / "local_grafana_bootstrap.summary.json").read_text(
                encoding="utf-8"
            )
        )
        assert bootstrap_payload["build17"]["dashboard_status_code"] == 200
        assert bootstrap_payload["build17"]["dashboard_uid"] == "v53-shadow-vps-local"
        assert bootstrap_payload["build17"]["embedded_in_shadow"] is True
        assert (output_dir / "grafana_data").is_dir()
        assert (output_dir / "grafana_logs").is_dir()
        assert (output_dir / "grafana_plugins").is_dir()
        assert "127.0.0.1:19100" in (
            output_dir / "prometheus.bridge.generated.yml"
        ).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_local_observability_stack_resets_managed_grafana_data_before_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("reset_managed_grafana_state")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 9\n", encoding="utf-8")
        output_dir = scratch / "output"
        stale_db = output_dir / "grafana_data" / "grafana.db"
        stale_db.parent.mkdir(parents=True, exist_ok=True)
        stale_db.write_text("stale", encoding="utf-8")
        seen_stale_db_during_start: list[bool] = []

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            if "grafana-server" in command[0]:
                seen_stale_db_during_start.append(stale_db.exists())
            return _FakeProcess(100)

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            return None

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
        monkeypatch.setattr(stack, "_find_next_free_port", lambda host, start_port: 3001)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", lambda **kwargs: (200, "v53-local-lab"))

        stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert seen_stale_db_during_start == [False]
        assert not stale_db.exists()
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

        def _fake_import_dashboard(**kwargs: object) -> tuple[int, str]:
            return 200, "v53-local-lab"

        monkeypatch.setattr(stack, "_start_detached_process", _unexpected_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", _fake_import_dashboard)

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


def test_launch_local_observability_stack_surfaces_actionable_unauthorized_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("grafana_unauthorized")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 12\n", encoding="utf-8")
        output_dir = scratch / "output"

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            return _FakeProcess(100)

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            return None

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

        def _raise_unauthorized(**kwargs: object):
            raise HTTPError(
                url="http://127.0.0.1:3000/api/datasources",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _raise_unauthorized)

        with pytest.raises(RuntimeError, match="Grafana bootstrap unauthorized"):
            stack.launch_local_observability_stack(
                prom_text_path=prom_path,
                output_dir=output_dir,
                grafana_password="admin",
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_local_observability_stack_falls_back_to_new_grafana_port_on_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("grafana_fallback_port")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 15\n", encoding="utf-8")
        output_dir = scratch / "output"
        started_commands: list[tuple[str, ...]] = []
        bootstrap_urls: list[str] = []
        stale_primary_db = output_dir / "grafana_data" / "grafana.db"
        stale_primary_db.parent.mkdir(parents=True, exist_ok=True)
        stale_primary_db.write_text("locked-elsewhere", encoding="utf-8")

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            started_commands.append(command)
            return _FakeProcess(200 + len(started_commands))

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            return None

        def _fake_port_is_listening(host: str, port: int) -> bool:
            return port in {19100, 9090, 3000}

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

        def _fake_bootstrap(**kwargs: object):
            bootstrap_urls.append(str(kwargs["grafana_url"]))
            if kwargs["grafana_url"] == "http://127.0.0.1:3000":
                raise HTTPError(
                    url="http://127.0.0.1:3000/api/datasources",
                    code=401,
                    msg="Unauthorized",
                    hdrs=None,
                    fp=None,
                )
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

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_find_next_free_port", lambda host, start_port: 3001)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", lambda **kwargs: (200, "v53-local-lab"))

        summary = stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert bootstrap_urls == [
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
        assert summary.grafana_url == "http://127.0.0.1:3001"
        assert summary.grafana_status == "started"
        assert any("cfg:server.http_port=3001" in part for cmd in started_commands for part in cmd)
        assert stale_primary_db.exists()
        assert any("grafana_data_3001" in part for cmd in started_commands for part in cmd)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_local_observability_stack_falls_back_to_new_grafana_port_on_startup_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("grafana_startup_timeout_fallback")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 16\n", encoding="utf-8")
        output_dir = scratch / "output"
        started_commands: list[tuple[str, ...]] = []
        bootstrap_urls: list[str] = []
        seen_grafana_waits: list[str] = []

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            started_commands.append(command)
            return _FakeProcess(300 + len(started_commands))

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            if "/api/health" in url:
                seen_grafana_waits.append(url)
                if url == "http://127.0.0.1:3000/api/health":
                    raise TimeoutError("startup timeout on primary grafana port")
            return None

        def _fake_port_is_listening(host: str, port: int) -> bool:
            return port in {19100, 9090}

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

        def _fake_bootstrap(**kwargs: object):
            bootstrap_urls.append(str(kwargs["grafana_url"]))
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

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_find_next_free_port", lambda host, start_port: 3001)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", lambda **kwargs: (200, "v53-local-lab"))

        summary = stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert seen_grafana_waits == [
            "http://127.0.0.1:3000/api/health",
            "http://127.0.0.1:3001/api/health",
        ]
        assert bootstrap_urls == ["http://127.0.0.1:3001"]
        assert summary.grafana_url == "http://127.0.0.1:3001"
        assert summary.grafana_status == "started"
        assert any("cfg:server.http_port=3000" in part for cmd in started_commands for part in cmd)
        assert any("cfg:server.http_port=3001" in part for cmd in started_commands for part in cmd)
        assert any("grafana_data_3001" in part for cmd in started_commands for part in cmd)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_local_observability_stack_reuses_existing_managed_grafana_from_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("grafana_reuse_existing_summary")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 17\n", encoding="utf-8")
        output_dir = scratch / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "local_observability_stack.summary.json").write_text(
            json.dumps({"grafana_url": "http://127.0.0.1:3006"}),
            encoding="utf-8",
        )
        started_commands: list[tuple[str, ...]] = []
        waited_urls: list[str] = []
        bootstrap_urls: list[str] = []

        def _fake_start(
            command: tuple[str, ...],
            *,
            cwd: Path | None,
            log_path: Path,
        ) -> _FakeProcess:
            started_commands.append(command)
            return _FakeProcess(400 + len(started_commands))

        def _fake_wait(url: str, *, timeout_s: float) -> None:
            waited_urls.append(url)
            if url == "http://127.0.0.1:3006/api/health":
                return None
            if url.endswith("/-/ready"):
                return None
            raise TimeoutError(f"unreachable {url}")

        def _fake_port_is_listening(host: str, port: int) -> bool:
            return port in {19100, 9090}

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

        def _fake_bootstrap(**kwargs: object):
            bootstrap_urls.append(str(kwargs["grafana_url"]))
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

        monkeypatch.setattr(stack, "_start_detached_process", _fake_start)
        monkeypatch.setattr(stack, "_wait_for_http_ready", _fake_wait)
        monkeypatch.setattr(stack, "_port_is_listening", _fake_port_is_listening)
        monkeypatch.setattr(stack, "_resolve_executable_path", _fake_resolve_executable_path)
        monkeypatch.setattr(stack, "bootstrap_local_grafana", _fake_bootstrap)
        monkeypatch.setattr(stack, "import_dashboard_payload", lambda **kwargs: (200, "v53-local-lab"))

        summary = stack.launch_local_observability_stack(
            prom_text_path=prom_path,
            output_dir=output_dir,
            grafana_password="admin",
        )

        assert summary.grafana_url == "http://127.0.0.1:3006"
        assert summary.grafana_status == "already_listening"
        assert bootstrap_urls == ["http://127.0.0.1:3006"]
        assert all(
            "grafana-server" not in str(part)
            for command in started_commands
            for part in command
        )
        assert "http://127.0.0.1:3006/api/health" in waited_urls
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
