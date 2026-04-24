"""One-shot local launcher for the Shadow VPS Prometheus/Grafana observability stack."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from pydantic import BaseModel, Field
import yaml

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from monitoring.local_grafana_api import bootstrap_local_grafana
from monitoring.local_grafana_dashboard import (
    build_local_shadow_vps_grafana_dashboard,
    build_local_shadow_vps_grafana_dashboard_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR = REPO_ROOT / ".local_observability_stack"
_DEFAULT_GRAFANA_SERVER_CANDIDATES = (
    Path(r"C:\Program Files\GrafanaLabs\grafana\bin\grafana-server.exe"),
    Path(r"C:\Program Files\GrafanaLabs\grafana\bin\grafana.exe"),
)
_DEFAULT_PROMETHEUS_CANDIDATES = (
    Path(r"C:\Program Files\Prometheus\prometheus.exe"),
    Path(r"C:\prometheus\prometheus.exe"),
)


class LocalObservabilityStackSummary(BaseModel, frozen=True):
    """Typed summary for one launched local observability stack."""

    output_dir: str = Field(..., min_length=1)
    prom_text_path: str = Field(..., min_length=1)
    dashboard_json_path: str = Field(..., min_length=1)
    dashboard_summary_path: str = Field(..., min_length=1)
    bootstrap_summary_path: str = Field(..., min_length=1)
    prometheus_config_path: str = Field(..., min_length=1)
    bridge_url: str = Field(..., min_length=1)
    prometheus_url: str = Field(..., min_length=1)
    grafana_url: str = Field(..., min_length=1)
    bridge_status: str = Field(..., min_length=1)
    prometheus_status: str = Field(..., min_length=1)
    grafana_status: str = Field(..., min_length=1)
    bridge_pid: int | None = Field(default=None, ge=1)
    prometheus_pid: int | None = Field(default=None, ge=1)
    grafana_pid: int | None = Field(default=None, ge=1)
    grafana_server_exe: str = ""
    prometheus_exe: str = ""
    bridge_log_path: str = Field(..., min_length=1)
    prometheus_log_path: str = Field(..., min_length=1)
    grafana_log_path: str = Field(..., min_length=1)


def build_local_bridge_prometheus_config_text(
    *,
    metrics_target: str,
    scrape_interval: str = "5s",
    evaluation_interval: str = "5s",
) -> str:
    """Build a minimal Prometheus config scraping the local metrics bridge."""

    payload = {
        "global": {
            "scrape_interval": scrape_interval,
            "evaluation_interval": evaluation_interval,
        },
        "scrape_configs": [
            {
                "job_name": "v53_shadow_vps_bridge",
                "static_configs": [
                    {
                        "targets": [metrics_target],
                        "labels": {
                            "scope": "local_pc",
                            "component": "shadow_vps_metrics_bridge",
                        },
                    }
                ],
            }
        ],
    }
    return yaml.safe_dump(payload, sort_keys=False)


def _normalize_existing_path(path: str | Path, *, label: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return resolved


def _resolve_executable_path(
    *,
    explicit_path: str | Path | None,
    env_var_names: tuple[str, ...],
    executable_names: tuple[str, ...],
    candidate_paths: tuple[Path, ...],
) -> Path | None:
    if explicit_path is not None:
        return _normalize_existing_path(explicit_path, label="Explicit executable")
    for env_var_name in env_var_names:
        candidate = os.environ.get(env_var_name, "").strip()
        if candidate:
            return _normalize_existing_path(candidate, label=f"Environment executable {env_var_name}")
    for executable_name in executable_names:
        discovered = shutil.which(executable_name)
        if discovered:
            return Path(discovered).expanduser().resolve()
    for candidate_path in candidate_paths:
        if candidate_path.exists():
            return candidate_path.resolve()
    return None


def _infer_grafana_home(
    grafana_server_exe: Path,
    *,
    explicit_home: str | Path | None,
) -> Path:
    if explicit_home is not None:
        return _normalize_existing_path(explicit_home, label="Grafana home")
    if grafana_server_exe.parent.name.lower() == "bin":
        return grafana_server_exe.parent.parent.resolve()
    return grafana_server_exe.parent.resolve()


def _port_is_listening(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex((host, port)) == 0


def _wait_for_http_ready(url: str, *, timeout_s: float) -> None:
    deadline = time.time() + max(timeout_s, 0.1)
    last_error = ""
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.0) as response:
                if 200 <= response.getcode() < 300:
                    return
        except (HTTPError, URLError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for {url}; last_error={last_error or 'unknown'}")


def _parsed_host_port(url: str, *, default_host: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or default_host
    port = parsed.port or default_port
    return host, port


def _start_detached_process(
    command: tuple[str, ...],
    *,
    cwd: Path | None,
    log_path: Path,
) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    popen_kwargs: dict[str, object] = {
        "cwd": None if cwd is None else str(cwd),
        "stdin": subprocess.DEVNULL,
        "text": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        popen_kwargs["start_new_session"] = True
    with log_path.open("a", encoding="utf-8") as handle:
        return subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            **popen_kwargs,
        )


def _write_dashboard_bundle(
    *,
    prom_text_path: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    dashboard_json_path = output_dir / "v53_shadow_vps_local_grafana.dashboard.json"
    dashboard_summary_path = output_dir / "v53_shadow_vps_local_grafana.summary.json"
    dashboard_payload = build_local_shadow_vps_grafana_dashboard()
    dashboard_summary = build_local_shadow_vps_grafana_dashboard_summary(
        source_prom_path=prom_text_path,
        output_path=dashboard_json_path,
    )
    atomic_write_json(dashboard_json_path, dashboard_payload, indent=2)
    atomic_write_json(
        dashboard_summary_path,
        dashboard_summary.model_dump(mode="json"),
        indent=2,
    )
    return dashboard_json_path, dashboard_summary_path


def _ensure_metrics_bridge(
    *,
    prom_text_path: Path,
    output_dir: Path,
    bridge_host: str,
    bridge_port: int,
    readiness_timeout_s: float,
) -> tuple[str, int | None]:
    ready_url = f"http://{bridge_host}:{bridge_port}/-/ready"
    if _port_is_listening(bridge_host, bridge_port):
        _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
        return "already_listening", None
    process = _start_detached_process(
        (
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_local_prometheus_metrics_bridge.py"),
            "--prom-text-path",
            str(prom_text_path),
            "--listen-host",
            bridge_host,
            "--listen-port",
            str(bridge_port),
            "--output-dir",
            str(output_dir / "bridge"),
        ),
        cwd=REPO_ROOT,
        log_path=output_dir / "local_prometheus_metrics_bridge.log",
    )
    _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
    return "started", process.pid


def _ensure_prometheus(
    *,
    output_dir: Path,
    prometheus_url: str,
    prometheus_exe: str | Path | None,
    prometheus_config_path: Path,
    readiness_timeout_s: float,
) -> tuple[str, int | None, Path | None]:
    host, port = _parsed_host_port(
        prometheus_url,
        default_host="127.0.0.1",
        default_port=9090,
    )
    ready_url = f"http://{host}:{port}/-/ready"
    if _port_is_listening(host, port):
        _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
        return "already_listening", None, None
    resolved_exe = _resolve_executable_path(
        explicit_path=prometheus_exe,
        env_var_names=("V53_PROMETHEUS_EXE", "PROMETHEUS_EXE"),
        executable_names=("prometheus.exe", "prometheus"),
        candidate_paths=_DEFAULT_PROMETHEUS_CANDIDATES,
    )
    if resolved_exe is None:
        raise FileNotFoundError(
            "Prometheus executable not found. Install Prometheus or pass --prometheus-exe."
        )
    process = _start_detached_process(
        (
            str(resolved_exe),
            f"--config.file={prometheus_config_path}",
            f"--storage.tsdb.path={output_dir / 'prometheus_data'}",
            f"--web.listen-address={host}:{port}",
        ),
        cwd=resolved_exe.parent,
        log_path=output_dir / "prometheus.log",
    )
    _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
    return "started", process.pid, resolved_exe


def _ensure_grafana(
    *,
    output_dir: Path,
    grafana_url: str,
    grafana_server_exe: str | Path | None,
    grafana_home: str | Path | None,
    readiness_timeout_s: float,
) -> tuple[str, int | None, Path | None]:
    host, port = _parsed_host_port(
        grafana_url,
        default_host="127.0.0.1",
        default_port=3000,
    )
    ready_url = f"http://{host}:{port}/api/health"
    if _port_is_listening(host, port):
        _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
        return "already_listening", None, None
    resolved_exe = _resolve_executable_path(
        explicit_path=grafana_server_exe,
        env_var_names=("V53_GRAFANA_SERVER_EXE", "GRAFANA_SERVER_EXE"),
        executable_names=("grafana-server.exe", "grafana-server"),
        candidate_paths=_DEFAULT_GRAFANA_SERVER_CANDIDATES,
    )
    if resolved_exe is None:
        raise FileNotFoundError(
            "Grafana server executable not found. Install Grafana or pass --grafana-server-exe."
        )
    resolved_home = _infer_grafana_home(
        resolved_exe,
        explicit_home=grafana_home,
    )
    grafana_data_dir = output_dir / "grafana_data"
    grafana_logs_dir = output_dir / "grafana_logs"
    grafana_plugins_dir = output_dir / "grafana_plugins"
    grafana_data_dir.mkdir(parents=True, exist_ok=True)
    grafana_logs_dir.mkdir(parents=True, exist_ok=True)
    grafana_plugins_dir.mkdir(parents=True, exist_ok=True)
    process = _start_detached_process(
        (
            str(resolved_exe),
            "--homepath",
            str(resolved_home),
            f"cfg:server.http_addr={host}",
            f"cfg:server.http_port={port}",
            f"cfg:default.paths.data={grafana_data_dir}",
            f"cfg:default.paths.logs={grafana_logs_dir}",
            f"cfg:default.paths.plugins={grafana_plugins_dir}",
        ),
        cwd=resolved_home,
        log_path=output_dir / "grafana.log",
    )
    _wait_for_http_ready(ready_url, timeout_s=readiness_timeout_s)
    return "started", process.pid, resolved_exe


def _write_bootstrap_summary(
    *,
    grafana_url: str,
    grafana_user: str,
    grafana_password: str,
    dashboard_json_path: Path,
    prometheus_url: str,
    bootstrap_summary_path: Path,
) -> None:
    bootstrap_summary = bootstrap_local_grafana(
        grafana_url=grafana_url,
        username=grafana_user,
        password=grafana_password,
        dashboard_payload_path=dashboard_json_path,
        datasource_name="Prometheus",
        datasource_uid="prometheus",
        prometheus_url=prometheus_url,
        output_path=bootstrap_summary_path,
    )
    atomic_write_json(
        bootstrap_summary_path,
        bootstrap_summary.model_dump(mode="json"),
        indent=2,
    )


def launch_local_observability_stack(
    *,
    prom_text_path: str | Path,
    output_dir: str | Path = DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR,
    grafana_url: str = "http://127.0.0.1:3000",
    grafana_user: str = "admin",
    grafana_password: str = "admin",
    prometheus_url: str = "http://127.0.0.1:9090",
    bridge_host: str = "127.0.0.1",
    bridge_port: int = 19100,
    prometheus_exe: str | Path | None = None,
    grafana_server_exe: str | Path | None = None,
    grafana_home: str | Path | None = None,
    scrape_interval: str = "5s",
    evaluation_interval: str = "5s",
    readiness_timeout_s: float = 30.0,
) -> LocalObservabilityStackSummary:
    """Launch the local metrics bridge, Prometheus, Grafana, and bootstrap the dashboard."""

    resolved_prom_text_path = _normalize_existing_path(
        prom_text_path,
        label="Prometheus text payload",
    )
    resolved_output_dir = Path(output_dir).expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    dashboard_json_path, dashboard_summary_path = _write_dashboard_bundle(
        prom_text_path=resolved_prom_text_path,
        output_dir=resolved_output_dir,
    )
    bootstrap_summary_path = resolved_output_dir / "local_grafana_bootstrap.summary.json"
    prometheus_config_path = resolved_output_dir / "prometheus.bridge.generated.yml"
    bridge_log_path = resolved_output_dir / "local_prometheus_metrics_bridge.log"
    prometheus_log_path = resolved_output_dir / "prometheus.log"
    grafana_log_path = resolved_output_dir / "grafana.log"
    bridge_status, bridge_pid = _ensure_metrics_bridge(
        prom_text_path=resolved_prom_text_path,
        output_dir=resolved_output_dir,
        bridge_host=bridge_host,
        bridge_port=bridge_port,
        readiness_timeout_s=readiness_timeout_s,
    )
    atomic_write_text(
        prometheus_config_path,
        build_local_bridge_prometheus_config_text(
            metrics_target=f"{bridge_host}:{bridge_port}",
            scrape_interval=scrape_interval,
            evaluation_interval=evaluation_interval,
        ),
    )
    (
        prometheus_status,
        prometheus_pid,
        resolved_prometheus_exe,
    ) = _ensure_prometheus(
        output_dir=resolved_output_dir,
        prometheus_url=prometheus_url,
        prometheus_exe=prometheus_exe,
        prometheus_config_path=prometheus_config_path,
        readiness_timeout_s=readiness_timeout_s,
    )
    (
        grafana_status,
        grafana_pid,
        resolved_grafana_server_exe,
    ) = _ensure_grafana(
        output_dir=resolved_output_dir,
        grafana_url=grafana_url,
        grafana_server_exe=grafana_server_exe,
        grafana_home=grafana_home,
        readiness_timeout_s=readiness_timeout_s,
    )
    _write_bootstrap_summary(
        grafana_url=grafana_url,
        grafana_user=grafana_user,
        grafana_password=grafana_password,
        dashboard_json_path=dashboard_json_path,
        prometheus_url=prometheus_url,
        bootstrap_summary_path=bootstrap_summary_path,
    )

    summary = LocalObservabilityStackSummary(
        output_dir=str(resolved_output_dir),
        prom_text_path=str(resolved_prom_text_path),
        dashboard_json_path=str(dashboard_json_path),
        dashboard_summary_path=str(dashboard_summary_path),
        bootstrap_summary_path=str(bootstrap_summary_path),
        prometheus_config_path=str(prometheus_config_path),
        bridge_url=f"http://{bridge_host}:{bridge_port}/metrics",
        prometheus_url=prometheus_url,
        grafana_url=grafana_url,
        bridge_status=bridge_status,
        prometheus_status=prometheus_status,
        grafana_status=grafana_status,
        bridge_pid=bridge_pid,
        prometheus_pid=prometheus_pid,
        grafana_pid=grafana_pid,
        grafana_server_exe=(
            ""
            if resolved_grafana_server_exe is None
            else str(resolved_grafana_server_exe)
        ),
        prometheus_exe=(
            ""
            if resolved_prometheus_exe is None
            else str(resolved_prometheus_exe)
        ),
        bridge_log_path=str(bridge_log_path),
        prometheus_log_path=str(prometheus_log_path),
        grafana_log_path=str(grafana_log_path),
    )
    atomic_write_json(
        resolved_output_dir / "local_observability_stack.summary.json",
        summary.model_dump(mode="json"),
        indent=2,
    )
    return summary


__all__ = [
    "DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR",
    "LocalObservabilityStackSummary",
    "build_local_bridge_prometheus_config_text",
    "launch_local_observability_stack",
]
