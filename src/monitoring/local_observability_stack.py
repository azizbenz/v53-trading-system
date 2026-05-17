"""One-shot local launcher for the Shadow VPS Prometheus/Grafana observability stack."""

from __future__ import annotations

import os
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from pydantic import BaseModel, Field
import yaml

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from monitoring.local_grafana_api import bootstrap_local_grafana, import_dashboard_payload
from monitoring.local_grafana_dashboard import (
    build_local_shadow_vps_grafana_dashboard,
    build_local_shadow_vps_grafana_dashboard_summary,
)
from monitoring.local_lab_grafana_dashboard import build_local_lab_grafana_dashboard


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_OBSERVABILITY_OUTPUT_DIR = REPO_ROOT / ".local_observability_stack"
DEFAULT_READINESS_TIMEOUT_S = 90.0
_HTTP_READY_ATTEMPT_TIMEOUT_S = 3.0
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


def _coerce_to_executable_file(path: Path, *, executable_names: tuple[str, ...]) -> Path:
    if path.is_file():
        return path
    if path.is_dir():
        for executable_name in executable_names:
            candidate = path / executable_name
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(
            f"No executable found in directory {path} (looked for: {', '.join(executable_names)})"
        )
    raise FileNotFoundError(f"Executable path is neither file nor directory: {path}")


def _resolve_executable_path(
    *,
    explicit_path: str | Path | None,
    env_var_names: tuple[str, ...],
    executable_names: tuple[str, ...],
    candidate_paths: tuple[Path, ...],
) -> Path | None:
    if explicit_path is not None:
        resolved = _normalize_existing_path(explicit_path, label="Explicit executable")
        return _coerce_to_executable_file(resolved, executable_names=executable_names)
    for env_var_name in env_var_names:
        candidate = os.environ.get(env_var_name, "").strip()
        if candidate:
            resolved = _normalize_existing_path(candidate, label=f"Environment executable {env_var_name}")
            return _coerce_to_executable_file(resolved, executable_names=executable_names)
    for executable_name in executable_names:
        discovered = shutil.which(executable_name)
        if discovered:
            return Path(discovered).expanduser().resolve()
    for candidate_path in candidate_paths:
        if candidate_path.exists():
            return _coerce_to_executable_file(candidate_path.resolve(), executable_names=executable_names)
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
            with urlopen(
                url,
                timeout=min(
                    _HTTP_READY_ATTEMPT_TIMEOUT_S,
                    max(timeout_s, 0.1),
                ),
            ) as response:
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


def _replace_url_host_port(url: str, *, host: str, port: int) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    netloc = f"{host}:{port}"
    return urlunparse(
        (scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def _find_next_free_port(host: str, *, start_port: int, max_attempts: int = 25) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No free local port found for managed Grafana starting at {host}:{start_port}"
    )


def _managed_grafana_runtime_dirs(
    output_dir: Path,
    *,
    port: int,
) -> tuple[Path, Path, Path]:
    if port == 3000:
        suffix = ""
    else:
        suffix = f"_{port}"
    return (
        output_dir / f"grafana_data{suffix}",
        output_dir / f"grafana_logs{suffix}",
        output_dir / f"grafana_plugins{suffix}",
    )


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
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
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


def _reset_managed_grafana_state(grafana_data_dir: Path) -> None:
    """Reset the service-owned Grafana state before starting a managed instance.

    The local one-click stack owns the selected ``grafana_data`` directory. Resetting this
    state keeps the default bootstrap credentials deterministic across reruns.
    """
    if grafana_data_dir.exists():
        shutil.rmtree(grafana_data_dir)


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
    (
        grafana_data_dir,
        grafana_logs_dir,
        grafana_plugins_dir,
    ) = _managed_grafana_runtime_dirs(output_dir, port=port)
    _reset_managed_grafana_state(grafana_data_dir.resolve())
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


def _import_lab_dashboard(
    *,
    grafana_url: str,
    grafana_user: str,
    grafana_password: str,
) -> tuple[int, str]:
    lab_payload = build_local_lab_grafana_dashboard()
    return import_dashboard_payload(
        grafana_url=grafana_url,
        username=grafana_user,
        password=grafana_password,
        dashboard_payload=lab_payload,
    )


def _write_bootstrap_summary(
    *,
    grafana_url: str,
    grafana_user: str,
    grafana_password: str,
    dashboard_json_path: Path,
    prometheus_url: str,
    bootstrap_summary_path: Path,
) -> None:
    shadow_summary = bootstrap_local_grafana(
        grafana_url=grafana_url,
        username=grafana_user,
        password=grafana_password,
        dashboard_payload_path=dashboard_json_path,
        datasource_name="Prometheus",
        datasource_uid="prometheus",
        prometheus_url=prometheus_url,
        output_path=bootstrap_summary_path,
    )
    lab_status_code, lab_uid = _import_lab_dashboard(
        grafana_url=grafana_url,
        grafana_user=grafana_user,
        grafana_password=grafana_password,
    )
    atomic_write_json(
        bootstrap_summary_path,
        {
            "shadow_vps": shadow_summary.model_dump(mode="json"),
            "lab": {
                "dashboard_status_code": lab_status_code,
                "dashboard_uid": lab_uid,
            },
            "build17": {
                "dashboard_status_code": shadow_summary.dashboard_status_code,
                "dashboard_uid": shadow_summary.dashboard_uid,
                "embedded_in_shadow": True,
            },
        },
        indent=2,
    )


def _raise_actionable_grafana_bootstrap_error(
    *,
    exc: HTTPError,
    grafana_url: str,
    grafana_user: str,
    grafana_status: str,
) -> None:
    if exc.code != 401:
        raise exc
    if grafana_status == "already_listening":
        raise RuntimeError(
            "Grafana bootstrap unauthorized on "
            f"{grafana_url}. A Grafana instance is already listening and rejected "
            f"the supplied credentials for user {grafana_user!r}. "
            "Pass the correct --grafana-user/--grafana-password, or stop the "
            "existing Grafana instance before rerunning the one-click launcher."
        ) from exc
    raise RuntimeError(
        "Grafana bootstrap unauthorized on "
        f"{grafana_url} even after starting the managed local instance. "
        "Rerun with explicit --grafana-user/--grafana-password or remove the "
        "managed local observability state under build/run_v53_local_solution/"
        "local_observability_stack if it was customized outside the launcher."
    ) from exc


def _retry_managed_grafana_on_fallback_port(
    *,
    output_dir: Path,
    grafana_url: str,
    grafana_server_exe: str | Path | None,
    grafana_home: str | Path | None,
    readiness_timeout_s: float,
) -> tuple[str, str, int | None, Path | None]:
    host, port = _parsed_host_port(
        grafana_url,
        default_host="127.0.0.1",
        default_port=3000,
    )
    fallback_port = _find_next_free_port(host, start_port=port + 1)
    fallback_url = _replace_url_host_port(
        grafana_url,
        host=host,
        port=fallback_port,
    )
    grafana_status, grafana_pid, resolved_grafana_server_exe = _ensure_grafana(
        output_dir=output_dir,
        grafana_url=fallback_url,
        grafana_server_exe=grafana_server_exe,
        grafana_home=grafana_home,
        readiness_timeout_s=readiness_timeout_s,
    )
    return fallback_url, grafana_status, grafana_pid, resolved_grafana_server_exe


def _try_wait_for_http_ready(url: str, *, timeout_s: float) -> bool:
    try:
        _wait_for_http_ready(url, timeout_s=timeout_s)
    except (TimeoutError, HTTPError, URLError, OSError):
        return False
    return True


def _find_reusable_grafana_url(
    *,
    output_dir: Path,
    grafana_url: str,
    scan_ports: bool = False,
) -> str | None:
    host, port = _parsed_host_port(
        grafana_url,
        default_host="127.0.0.1",
        default_port=3000,
    )
    candidates: list[str] = []
    summary_path = output_dir / "local_observability_stack.summary.json"
    if summary_path.is_file():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        summary_url = str(payload.get("grafana_url", "")).strip()
        if summary_url:
            candidates.append(summary_url)
    if scan_ports:
        for candidate_port in range(port, port + 12):
            candidates.append(
                _replace_url_host_port(
                    grafana_url,
                    host=host,
                    port=candidate_port,
                )
            )
    seen: set[str] = set()
    for candidate_url in candidates:
        if not candidate_url or candidate_url in seen:
            continue
        seen.add(candidate_url)
        ready_url = f"{candidate_url.rstrip('/')}/api/health"
        if _try_wait_for_http_ready(ready_url, timeout_s=0.75):
            return candidate_url
    return None


def _ensure_grafana_with_fallback(
    *,
    output_dir: Path,
    grafana_url: str,
    grafana_server_exe: str | Path | None,
    grafana_home: str | Path | None,
    readiness_timeout_s: float,
) -> tuple[str, str, int | None, Path | None]:
    reusable_url = _find_reusable_grafana_url(
        output_dir=output_dir,
        grafana_url=grafana_url,
        scan_ports=False,
    )
    if reusable_url is not None:
        return reusable_url, "already_listening", None, None
    try:
        grafana_status, grafana_pid, resolved_grafana_server_exe = _ensure_grafana(
            output_dir=output_dir,
            grafana_url=grafana_url,
            grafana_server_exe=grafana_server_exe,
            grafana_home=grafana_home,
            readiness_timeout_s=readiness_timeout_s,
        )
        return grafana_url, grafana_status, grafana_pid, resolved_grafana_server_exe
    except TimeoutError as exc:
        try:
            return _retry_managed_grafana_on_fallback_port(
                output_dir=output_dir,
                grafana_url=grafana_url,
                grafana_server_exe=grafana_server_exe,
                grafana_home=grafana_home,
                readiness_timeout_s=readiness_timeout_s,
            )
        except TimeoutError as retry_exc:
            reusable_url = _find_reusable_grafana_url(
                output_dir=output_dir,
                grafana_url=grafana_url,
                scan_ports=True,
            )
            if reusable_url is not None:
                return reusable_url, "already_listening", None, None
            raise RuntimeError(
                "Grafana startup timed out on "
                f"{grafana_url} and the managed fallback port also failed to become healthy."
            ) from retry_exc
        except Exception as retry_exc:
            reusable_url = _find_reusable_grafana_url(
                output_dir=output_dir,
                grafana_url=grafana_url,
                scan_ports=True,
            )
            if reusable_url is not None:
                return reusable_url, "already_listening", None, None
            raise RuntimeError(
                "Grafana startup timed out on "
                f"{grafana_url} and fallback startup also failed."
            ) from retry_exc


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
    readiness_timeout_s: float = DEFAULT_READINESS_TIMEOUT_S,
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
        effective_grafana_url,
        grafana_status,
        grafana_pid,
        resolved_grafana_server_exe,
    ) = _ensure_grafana_with_fallback(
        output_dir=resolved_output_dir,
        grafana_url=grafana_url,
        grafana_server_exe=grafana_server_exe,
        grafana_home=grafana_home,
        readiness_timeout_s=readiness_timeout_s,
    )
    try:
        _write_bootstrap_summary(
            grafana_url=effective_grafana_url,
            grafana_user=grafana_user,
            grafana_password=grafana_password,
            dashboard_json_path=dashboard_json_path,
            prometheus_url=prometheus_url,
            bootstrap_summary_path=bootstrap_summary_path,
        )
    except HTTPError as exc:
        if exc.code == 401 and grafana_status == "already_listening":
            (
                effective_grafana_url,
                grafana_status,
                grafana_pid,
                resolved_grafana_server_exe,
            ) = _retry_managed_grafana_on_fallback_port(
                output_dir=resolved_output_dir,
                grafana_url=grafana_url,
                grafana_server_exe=grafana_server_exe,
                grafana_home=grafana_home,
                readiness_timeout_s=readiness_timeout_s,
            )
            try:
                _write_bootstrap_summary(
                    grafana_url=effective_grafana_url,
                    grafana_user=grafana_user,
                    grafana_password=grafana_password,
                    dashboard_json_path=dashboard_json_path,
                    prometheus_url=prometheus_url,
                    bootstrap_summary_path=bootstrap_summary_path,
                )
            except HTTPError as retry_exc:
                _raise_actionable_grafana_bootstrap_error(
                    exc=retry_exc,
                    grafana_url=effective_grafana_url,
                    grafana_user=grafana_user,
                    grafana_status=grafana_status,
                )
        else:
            _raise_actionable_grafana_bootstrap_error(
                exc=exc,
                grafana_url=effective_grafana_url,
                grafana_user=grafana_user,
                grafana_status=grafana_status,
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
        grafana_url=effective_grafana_url,
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
    "DEFAULT_READINESS_TIMEOUT_S",
    "LocalObservabilityStackSummary",
    "build_local_bridge_prometheus_config_text",
    "launch_local_observability_stack",
]
