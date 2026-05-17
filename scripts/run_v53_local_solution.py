#!/usr/bin/env python3
"""Launch the local V5.3 Shadow solution and observability stack in one command."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

_logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts.atomic_io import atomic_write_json  # noqa: E402
from monitoring.local_observability_stack import (  # noqa: E402
    DEFAULT_READINESS_TIMEOUT_S,
    LocalObservabilityStackSummary,
    launch_local_observability_stack,
)


class V53LocalSolutionLaunchSummary(BaseModel, frozen=True):
    """Typed summary for the one-click local V5.3 launcher."""

    output_dir: str = Field(..., min_length=1)
    api_env_file: str = ""
    credentials_mode: str = Field(..., min_length=1)
    campaign_root: str = Field(..., min_length=1)
    shadow_live_websocket_config: str = Field(..., min_length=1)
    shadow_service_dir: str = Field(..., min_length=1)
    dashboard_command_queue_root: str = Field(..., min_length=1)
    shadow_observability_prom_path: str = Field(..., min_length=1)
    shadow_observability_export_path: str = Field(..., min_length=1)
    shadow_service_log_path: str = ""
    shadow_service_pid: int = Field(default=0, ge=0)
    shadow_service_launched: bool
    shadow_user_data_stream_enabled: bool
    observability_output_dir: str = Field(..., min_length=1)
    observability_summary_path: str = Field(..., min_length=1)
    prometheus_url: str = Field(..., min_length=1)
    grafana_url: str = Field(..., min_length=1)
    cockpit_url: str = Field(..., min_length=1)
    cockpit_log_path: str = Field(..., min_length=1)
    cockpit_pid: int = Field(default=0, ge=0)
    cockpit_started: bool = False
    grafana_opened: bool = False
    cockpit_opened: bool = False


class CockpitLaunchSummary(BaseModel, frozen=True):
    """Typed startup summary for the local cockpit server."""

    cockpit_url: str = Field(..., min_length=1)
    cockpit_log_path: str = Field(..., min_length=1)
    cockpit_pid: int = Field(default=0, ge=0)


class ShadowServiceLaunchSummary(BaseModel, frozen=True):
    """Typed startup summary for the detached Shadow VPS service."""

    shadow_service_log_path: str = ""
    shadow_service_pid: int = Field(default=0, ge=0)


def _strip_optional_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"API env file not found: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = _strip_optional_quotes(raw_value)
    return values


def _install_binance_env(env: dict[str, str], *, api_key: str, api_secret: str) -> None:
    env["BINANCE_API_KEY"] = api_key
    env["BINANCE_API_SECRET"] = api_secret
    env["V53_BINANCE_API_KEY"] = api_key
    env["V53_BINANCE_SECRET_KEY"] = api_secret


def _resolve_binance_credentials(env: dict[str, str]) -> tuple[str, str] | None:
    api_key = env.get("BINANCE_API_KEY", "").strip()
    api_secret = env.get("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        return None
    return api_key, api_secret


def _default_powershell_executable() -> str:
    for candidate in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return "powershell"


def _parse_last_json_payload(stdout: str) -> dict[str, object]:
    text = stdout.strip()
    if not text:
        raise ValueError("Shadow campaign launcher returned no JSON summary.")
    candidate_starts = [index for index, char in enumerate(text) if char == "{"]
    for start_index in reversed(candidate_starts):
        try:
            payload = json.loads(text[start_index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("Unable to parse Shadow campaign JSON summary from launcher stdout.")


def _run_shadow_campaign(
    *,
    repo_root: Path,
    powershell_executable: str,
    campaign_root: Path | None,
    enable_time_sync_probe: bool,
    enable_execution_runtime_bootstrap: bool,
    public_only: bool,
    stop_on_error: bool,
    skip_service_launch: bool = False,
    env: dict[str, str],
) -> dict[str, object]:
    command = [
        powershell_executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "Start-BinanceShadowLiveCampaign.ps1"),
    ]
    if campaign_root is not None:
        command.extend(["-CampaignRoot", str(campaign_root)])
    if public_only:
        command.append("-PublicOnly")
    if enable_time_sync_probe:
        command.append("-EnableTimeSyncProbe")
    if enable_execution_runtime_bootstrap:
        command.append("-EnableExecutionRuntimeBootstrap")
    if stop_on_error:
        command.append("-StopOnError")
    if skip_service_launch:
        command.append("-SkipServiceLaunch")

    completed = subprocess.run(
        command,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit_code={completed.returncode}"
        raise RuntimeError(f"Shadow campaign launcher failed: {detail}")

    return _parse_last_json_payload(completed.stdout)


def _resolve_shadow_prom_path(shadow_summary: dict[str, object]) -> Path:
    prom_path_value = str(shadow_summary.get("observability_prom", "")).strip()
    if prom_path_value:
        prom_path = Path(prom_path_value).expanduser().resolve()
        if prom_path.is_file():
            return prom_path

    service_dir_value = str(shadow_summary.get("service_dir", "")).strip()
    if not service_dir_value:
        raise FileNotFoundError("Shadow summary did not provide a valid service_dir.")

    fallback_path = Path(service_dir_value).expanduser().resolve() / "shadow_vps_service_observability.prom"
    if fallback_path.is_file():
        return fallback_path
    raise FileNotFoundError(f"Shadow observability `.prom` payload not found: {fallback_path}")


def _maybe_open_browser(*, url: str, no_open_browser: bool) -> bool:
    if no_open_browser:
        return False
    return bool(webbrowser.open(url))


def _resolve_dashboard_command_queue_root(shadow_summary: dict[str, object]) -> Path:
    queue_root_value = str(shadow_summary.get("dashboard_command_queue_root", "")).strip()
    if queue_root_value:
        return Path(queue_root_value).expanduser().resolve()
    service_dir_value = str(shadow_summary.get("service_dir", "")).strip()
    if not service_dir_value:
        raise FileNotFoundError("Shadow summary did not provide a valid service_dir.")
    return (Path(service_dir_value).expanduser().resolve() / "dashboard_command_queue")


def _resolve_shadow_service_pid_file(shadow_summary: dict[str, object]) -> Path:
    pid_file_value = str(shadow_summary.get("service_pid_file", "")).strip()
    if pid_file_value:
        return Path(pid_file_value).expanduser().resolve()
    service_dir_value = str(shadow_summary.get("service_dir", "")).strip()
    if not service_dir_value:
        raise FileNotFoundError("Shadow summary did not provide a valid service_dir.")
    return (Path(service_dir_value).expanduser().resolve() / "shadow_vps_service.pid")


def _build_shadow_service_command(
    *,
    repo_root: Path,
    python_executable: str,
    campaign_root: Path,
    service_dir: Path,
    live_websocket_config: Path,
    dashboard_command_queue_root: Path,
    pid_file: Path,
    enable_execution_runtime_bootstrap: bool,
    stop_on_error: bool,
) -> list[str]:
    command = [
        python_executable,
        str(repo_root / "scripts" / "run_shadow_vps_service.py"),
        "--service-dir",
        str(service_dir),
        "--orchestrator-output-dir",
        str(campaign_root / "orchestrator"),
        "--shadow-output-dir",
        str(campaign_root / "shadow_session"),
        "--live-websocket-config",
        str(live_websocket_config),
        "--live-captures-root",
        str(campaign_root / "live_captures"),
        "--auto-exports-root",
        str(campaign_root / "auto_exports"),
        "--dashboard-command-queue-root",
        str(dashboard_command_queue_root),
        "--pid-file",
        str(pid_file),
        "--poll-interval-s",
        "5.0",
    ]
    if enable_execution_runtime_bootstrap:
        command.append("--execution-runtime-bootstrap-enabled")
    if stop_on_error:
        command.append("--stop-on-error")
    return command


def _build_cockpit_command(
    *,
    repo_root: Path,
    python_executable: str,
    host: str,
    port: int,
    service_dir: Path,
    auto_exports_root: Path,
    live_websocket_config: Path,
    build_root: Path,
    dashboard_command_queue_root: Path,
    observability_output_dir: Path,
    backtest_jobs_root: Path,
    artifact_ingress_root: Path,
    grafana_url: str,
    prometheus_url: str,
) -> list[str]:
    return [
        python_executable,
        str(repo_root / "scripts" / "run_cockpit.py"),
        "--host",
        host,
        "--port",
        str(port),
        "--service-dir",
        str(service_dir),
        "--auto-exports-root",
        str(auto_exports_root),
        "--live-websocket-config",
        str(live_websocket_config),
        "--build-root",
        str(build_root),
        "--dashboard-command-queue-root",
        str(dashboard_command_queue_root),
        "--observability-output-dir",
        str(observability_output_dir),
        "--backtest-jobs-root",
        str(backtest_jobs_root),
        "--artifact-ingress-root",
        str(artifact_ingress_root),
        "--grafana-url",
        grafana_url,
        "--prometheus-url",
        prometheus_url,
    ]


def _wait_for_cockpit_ready(*, url: str, timeout_s: float, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Cockpit server exited before readiness check completed: exit_code={process.returncode}"
            )
        try:
            with urlopen(f"{url.rstrip('/')}/healthz", timeout=1.0) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.25)
    raise TimeoutError(f"Cockpit server did not become ready within {timeout_s:.1f}s: {url}")


def _wait_for_shadow_service_ready(
    *,
    service_dir: Path,
    pid_file: Path,
    prom_path: Path,
    timeout_s: float,
    process: subprocess.Popen[str],
) -> None:
    deadline = time.time() + timeout_s
    monitoring_payload_path = service_dir / "shadow_vps_service_monitoring_backend_payload.json"
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "Shadow service exited before readiness check completed: "
                f"exit_code={process.returncode}"
            )
        if pid_file.is_file() and prom_path.is_file() and monitoring_payload_path.is_file():
            return
        time.sleep(0.25)
    raise TimeoutError(
        "Shadow service did not become ready within "
        f"{timeout_s:.1f}s: {service_dir}"
    )


def _launch_shadow_service(
    *,
    repo_root: Path,
    python_executable: str,
    output_dir: Path,
    campaign_root: Path,
    service_dir: Path,
    live_websocket_config: Path,
    dashboard_command_queue_root: Path,
    pid_file: Path,
    prom_path: Path,
    enable_execution_runtime_bootstrap: bool,
    stop_on_error: bool,
    readiness_timeout_s: float,
    env: dict[str, str],
) -> ShadowServiceLaunchSummary:
    service_log_path = service_dir / "shadow_vps_service.launch.log"
    service_log_path.parent.mkdir(parents=True, exist_ok=True)
    command = _build_shadow_service_command(
        repo_root=repo_root,
        python_executable=python_executable,
        campaign_root=campaign_root,
        service_dir=service_dir,
        live_websocket_config=live_websocket_config,
        dashboard_command_queue_root=dashboard_command_queue_root,
        pid_file=pid_file,
        enable_execution_runtime_bootstrap=enable_execution_runtime_bootstrap,
        stop_on_error=stop_on_error,
    )
    log_handle = service_log_path.open("a", encoding="utf-8")
    try:
        popen_kwargs: dict[str, object] = {
            "cwd": str(repo_root),
            "env": env,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **popen_kwargs)
    finally:
        log_handle.close()
    _wait_for_shadow_service_ready(
        service_dir=service_dir,
        pid_file=pid_file,
        prom_path=prom_path,
        timeout_s=readiness_timeout_s,
        process=process,
    )
    return ShadowServiceLaunchSummary(
        shadow_service_log_path=str(service_log_path.resolve()),
        shadow_service_pid=0 if process.pid is None else int(process.pid),
    )


def _launch_cockpit(
    *,
    repo_root: Path,
    python_executable: str,
    output_dir: Path,
    service_dir: Path,
    campaign_root: Path,
    live_websocket_config: Path,
    observability_output_dir: Path,
    dashboard_command_queue_root: Path,
    grafana_url: str,
    prometheus_url: str,
    host: str,
    port: int,
    readiness_timeout_s: float,
    env: dict[str, str],
) -> CockpitLaunchSummary:
    cockpit_root = output_dir / "cockpit"
    cockpit_root.mkdir(parents=True, exist_ok=True)
    backtest_jobs_root = repo_root / "build" / "cockpit" / "backtest_jobs"
    artifact_ingress_root = repo_root / "build" / "cockpit" / "artifact_ingress"
    for directory in (
        dashboard_command_queue_root,
        backtest_jobs_root,
        artifact_ingress_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    cockpit_log_path = cockpit_root / "cockpit.log"
    command = _build_cockpit_command(
        repo_root=repo_root,
        python_executable=python_executable,
        host=host,
        port=port,
        service_dir=service_dir,
        auto_exports_root=campaign_root / "auto_exports",
        live_websocket_config=live_websocket_config,
        build_root=repo_root / "build",
        dashboard_command_queue_root=dashboard_command_queue_root,
        observability_output_dir=observability_output_dir,
        backtest_jobs_root=backtest_jobs_root,
        artifact_ingress_root=artifact_ingress_root,
        grafana_url=grafana_url,
        prometheus_url=prometheus_url,
    )
    log_handle = cockpit_log_path.open("a", encoding="utf-8")
    try:
        popen_kwargs: dict[str, object] = {
            "cwd": str(repo_root),
            "env": env,
            "stdin": subprocess.DEVNULL,
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **popen_kwargs)
    finally:
        log_handle.close()
    cockpit_url = f"http://{host}:{port}"
    _wait_for_cockpit_ready(
        url=cockpit_url,
        timeout_s=readiness_timeout_s,
        process=process,
    )
    return CockpitLaunchSummary(
        cockpit_url=cockpit_url,
        cockpit_log_path=str(cockpit_log_path.resolve()),
        cockpit_pid=0 if process.pid is None else int(process.pid),
    )


def run_v53_local_solution(
    *,
    api_env_file: Path,
    output_dir: Path,
    campaign_root: Path | None,
    public_only: bool,
    enable_time_sync_probe: bool,
    enable_execution_runtime_bootstrap: bool = True,
    stop_on_error: bool,
    skip_service_launch: bool = False,
    grafana_password: str,
    grafana_user: str,
    grafana_url: str,
    prometheus_url: str,
    bridge_host: str,
    bridge_port: int,
    prometheus_exe: Path | None,
    grafana_server_exe: Path | None,
    grafana_home: Path | None,
    scrape_interval: str,
    evaluation_interval: str,
    readiness_timeout_s: float,
    no_open_browser: bool,
    cockpit_host: str = "127.0.0.1",
    cockpit_port: int = 8080,
    powershell_executable: str | None = None,
) -> V53LocalSolutionLaunchSummary:
    resolved_output_dir = output_dir.expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    resolved_api_env_file = api_env_file.expanduser().resolve()

    env = os.environ.copy()
    credentials_mode = "public_only"
    if resolved_api_env_file.is_file():
        file_values = _load_env_file(resolved_api_env_file)
        env.update(file_values)

    credentials = _resolve_binance_credentials(env)
    if credentials is not None:
        api_key, api_secret = credentials
        _install_binance_env(env, api_key=api_key, api_secret=api_secret)
        credentials_mode = "authenticated"
    elif not public_only:
        _logger.warning(
            "Binance credentials not found in %s — running in public-only mode. "
            "Set BINANCE_API_KEY and BINANCE_API_SECRET for authenticated mode.",
            resolved_api_env_file,
        )
        public_only = True

    launch_shadow_service_detached = not skip_service_launch
    shadow_summary = _run_shadow_campaign(
        repo_root=REPO_ROOT,
        powershell_executable=powershell_executable or _default_powershell_executable(),
        campaign_root=None if campaign_root is None else campaign_root.expanduser().resolve(),
        enable_time_sync_probe=enable_time_sync_probe,
        enable_execution_runtime_bootstrap=enable_execution_runtime_bootstrap,
        public_only=public_only,
        stop_on_error=stop_on_error,
        skip_service_launch=launch_shadow_service_detached or skip_service_launch,
        env=env,
    )
    resolved_campaign_root = Path(str(shadow_summary["campaign_root"])).resolve()
    resolved_service_dir = Path(str(shadow_summary["service_dir"])).resolve()
    resolved_live_websocket_config = Path(str(shadow_summary["live_websocket_config"])).resolve()
    dashboard_command_queue_root = _resolve_dashboard_command_queue_root(shadow_summary)
    service_pid_file = _resolve_shadow_service_pid_file(shadow_summary)
    prom_text_path = resolved_service_dir / "shadow_vps_service_observability.prom"
    shadow_service_summary = ShadowServiceLaunchSummary(
        shadow_service_log_path="",
        shadow_service_pid=0,
    )
    if launch_shadow_service_detached:
        shadow_service_summary = _launch_shadow_service(
            repo_root=REPO_ROOT,
            python_executable=sys.executable,
            output_dir=resolved_output_dir,
            campaign_root=resolved_campaign_root,
            service_dir=resolved_service_dir,
            live_websocket_config=resolved_live_websocket_config,
            dashboard_command_queue_root=dashboard_command_queue_root,
            pid_file=service_pid_file,
            prom_path=prom_text_path,
            enable_execution_runtime_bootstrap=enable_execution_runtime_bootstrap,
            stop_on_error=stop_on_error,
            readiness_timeout_s=readiness_timeout_s,
            env=env,
        )
    else:
        prom_text_path = _resolve_shadow_prom_path(shadow_summary)
    observability_output_dir = resolved_output_dir / "local_observability_stack"
    observability_summary = launch_local_observability_stack(
        prom_text_path=prom_text_path,
        output_dir=observability_output_dir,
        grafana_url=grafana_url,
        grafana_user=grafana_user,
        grafana_password=grafana_password,
        prometheus_url=prometheus_url,
        bridge_host=bridge_host,
        bridge_port=bridge_port,
        prometheus_exe=prometheus_exe,
        grafana_server_exe=grafana_server_exe,
        grafana_home=grafana_home,
        scrape_interval=scrape_interval,
        evaluation_interval=evaluation_interval,
        readiness_timeout_s=readiness_timeout_s,
    )
    cockpit_summary = _launch_cockpit(
        repo_root=REPO_ROOT,
        python_executable=sys.executable,
        output_dir=resolved_output_dir,
        service_dir=resolved_service_dir,
        campaign_root=resolved_campaign_root,
        live_websocket_config=resolved_live_websocket_config,
        observability_output_dir=observability_output_dir,
        dashboard_command_queue_root=dashboard_command_queue_root,
        grafana_url=observability_summary.grafana_url,
        prometheus_url=observability_summary.prometheus_url,
        host=cockpit_host,
        port=cockpit_port,
        readiness_timeout_s=readiness_timeout_s,
        env=env,
    )
    cockpit_opened = _maybe_open_browser(
        url=cockpit_summary.cockpit_url,
        no_open_browser=no_open_browser,
    )

    summary = V53LocalSolutionLaunchSummary(
        output_dir=str(resolved_output_dir),
        api_env_file=str(resolved_api_env_file),
        credentials_mode=credentials_mode,
        campaign_root=str(resolved_campaign_root),
        shadow_live_websocket_config=str(resolved_live_websocket_config),
        shadow_service_dir=str(resolved_service_dir),
        dashboard_command_queue_root=str(dashboard_command_queue_root),
        shadow_observability_prom_path=str(prom_text_path),
        shadow_observability_export_path=str(
            Path(str(shadow_summary["observability_export"])).resolve()
        ),
        shadow_service_log_path=shadow_service_summary.shadow_service_log_path,
        shadow_service_pid=shadow_service_summary.shadow_service_pid,
        shadow_service_launched=launch_shadow_service_detached or bool(
            shadow_summary.get("service_launched", False)
        ),
        shadow_user_data_stream_enabled=bool(
            shadow_summary.get("user_data_stream_enabled", False)
        ),
        observability_output_dir=observability_summary.output_dir,
        observability_summary_path=str(
            Path(observability_summary.output_dir) / "local_observability_stack.summary.json"
        ),
        prometheus_url=observability_summary.prometheus_url,
        grafana_url=observability_summary.grafana_url,
        cockpit_url=cockpit_summary.cockpit_url,
        cockpit_log_path=cockpit_summary.cockpit_log_path,
        cockpit_pid=cockpit_summary.cockpit_pid,
        cockpit_started=True,
        grafana_opened=False,
        cockpit_opened=cockpit_opened,
    )
    atomic_write_json(
        resolved_output_dir / "launch.summary.json",
        summary.model_dump(mode="json"),
        indent=2,
    )
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local V5.3 Shadow solution and local Grafana observability stack in one command."
        ),
    )
    parser.add_argument(
        "--api-env-file",
        type=Path,
        default=REPO_ROOT / ".env",
        help="Local non-tracked file containing BINANCE_API_KEY and BINANCE_API_SECRET.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "build" / "run_v53_local_solution",
        help="Directory where the unified launcher summary will be written.",
    )
    parser.add_argument(
        "--campaign-root",
        type=Path,
        default=None,
        help="Optional explicit Shadow campaign root; defaults to the governed build11 campaign root.",
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="Allow the launcher to run without authenticated Binance user-data credentials.",
    )
    parser.add_argument(
        "--enable-time-sync-probe",
        action="store_true",
        help="Enable the bounded Binance time-sync probe during the Shadow launch.",
    )
    parser.add_argument(
        "--enable-execution-runtime-bootstrap",
        action="store_true",
        dest="enable_execution_runtime_bootstrap",
        help="Enable the bounded execution runtime bootstrap seam at Shadow startup.",
    )
    parser.add_argument(
        "--disable-execution-runtime-bootstrap",
        action="store_false",
        dest="enable_execution_runtime_bootstrap",
        help="Disable the bounded execution runtime bootstrap seam at Shadow startup.",
    )
    parser.set_defaults(enable_execution_runtime_bootstrap=True)
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Forward stop-on-error to the Shadow campaign launcher.",
    )
    parser.add_argument(
        "--skip-service-launch",
        action="store_true",
        help=(
            "Skip the Shadow service run and go straight to Grafana/Prometheus setup. "
            "Useful when the service is already running in a separate terminal."
        ),
    )
    parser.add_argument(
        "--grafana-url",
        default="http://127.0.0.1:3000",
        help="Grafana URL used by the local observability stack.",
    )
    parser.add_argument(
        "--grafana-user",
        default="admin",
        help="Grafana username.",
    )
    parser.add_argument(
        "--grafana-password",
        default="admin",
        help="Grafana password used for bootstrap.",
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://127.0.0.1:9090",
        help="Prometheus URL used by the local observability stack.",
    )
    parser.add_argument(
        "--bridge-host",
        default="127.0.0.1",
        help="Host bound by the local metrics bridge.",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=19100,
        help="Port bound by the local metrics bridge.",
    )
    parser.add_argument(
        "--prometheus-exe",
        type=Path,
        default=None,
        help="Optional explicit Prometheus executable path.",
    )
    parser.add_argument(
        "--grafana-server-exe",
        type=Path,
        default=None,
        help="Optional explicit Grafana server executable path.",
    )
    parser.add_argument(
        "--grafana-home",
        type=Path,
        default=None,
        help="Optional explicit Grafana home directory.",
    )
    parser.add_argument(
        "--scrape-interval",
        default="5s",
        help="Prometheus scrape interval for the generated bridge config.",
    )
    parser.add_argument(
        "--evaluation-interval",
        default="5s",
        help="Prometheus evaluation interval for the generated bridge config.",
    )
    parser.add_argument(
        "--readiness-timeout-s",
        type=float,
        default=DEFAULT_READINESS_TIMEOUT_S,
        help="Timeout applied while waiting for Shadow observability and Grafana stack readiness.",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="Do not open the cockpit URL automatically after launch.",
    )
    parser.add_argument(
        "--cockpit-host",
        default="127.0.0.1",
        help="Host bound by the cockpit server started by the one-click launcher.",
    )
    parser.add_argument(
        "--cockpit-port",
        type=int,
        default=8080,
        help="Port bound by the cockpit server started by the one-click launcher.",
    )
    return parser


def _emit_summary(summary: V53LocalSolutionLaunchSummary) -> None:
    summary_path = Path(summary.output_dir) / "launch.summary.json"
    sys.stdout.write(f"Unified launcher summary JSON: {summary_path}\n")
    if summary.api_env_file:
        sys.stdout.write(f"Binance API file: {summary.api_env_file}\n")
    sys.stdout.write(f"Shadow campaign root: {summary.campaign_root}\n")
    sys.stdout.write(f"Cockpit URL: {summary.cockpit_url}\n")
    sys.stdout.write(f"Grafana URL: {summary.grafana_url}\n")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_v53_local_solution(
            api_env_file=args.api_env_file,
            output_dir=args.output_dir,
            campaign_root=args.campaign_root,
            public_only=args.public_only,
            enable_time_sync_probe=args.enable_time_sync_probe,
            enable_execution_runtime_bootstrap=args.enable_execution_runtime_bootstrap,
            stop_on_error=args.stop_on_error,
            skip_service_launch=args.skip_service_launch,
            grafana_password=args.grafana_password,
            grafana_user=args.grafana_user,
            grafana_url=args.grafana_url,
            prometheus_url=args.prometheus_url,
            bridge_host=args.bridge_host,
            bridge_port=args.bridge_port,
            prometheus_exe=args.prometheus_exe,
            grafana_server_exe=args.grafana_server_exe,
            grafana_home=args.grafana_home,
            scrape_interval=args.scrape_interval,
            evaluation_interval=args.evaluation_interval,
            readiness_timeout_s=args.readiness_timeout_s,
            no_open_browser=args.no_open_browser,
            cockpit_host=args.cockpit_host,
            cockpit_port=args.cockpit_port,
        )
    except (
        FileNotFoundError,
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
    ) as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")
    _emit_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
