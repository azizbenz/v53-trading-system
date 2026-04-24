from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
from types import ModuleType

import pytest

from monitoring.local_observability_stack import LocalObservabilityStackSummary


def _load_launcher_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_observability_stack.py"
    module_name = "test_run_local_observability_stack"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-observability-stack-launcher", label)


def test_local_observability_stack_launcher_delegates_to_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 13\n", encoding="utf-8")
        output_dir = scratch / "output"
        captured_args: dict[str, object] = {}

        def _fake_launch_local_observability_stack(**kwargs: object) -> LocalObservabilityStackSummary:
            captured_args.update(kwargs)
            return LocalObservabilityStackSummary(
                output_dir=str(output_dir),
                prom_text_path=str(prom_path),
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

        monkeypatch.setattr(
            launcher,
            "launch_local_observability_stack",
            _fake_launch_local_observability_stack,
        )

        exit_code = launcher.main(
            [
                "--prom-text-path",
                str(prom_path),
                "--output-dir",
                str(output_dir),
                "--grafana-password",
                "admin",
            ]
        )

        assert exit_code == 0
        assert captured_args["prom_text_path"] == prom_path
        assert captured_args["output_dir"] == output_dir
        assert captured_args["grafana_password"] == "admin"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
