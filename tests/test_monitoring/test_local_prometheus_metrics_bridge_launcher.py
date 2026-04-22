from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
import time
from uuid import uuid4
from urllib.request import urlopen


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_prometheus_metrics_bridge.py"
    module_name = "test_run_local_prometheus_metrics_bridge"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-prometheus-metrics-bridge", label)


def test_local_prometheus_metrics_bridge_launcher_writes_summary_and_serves_metrics():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text("bridge_metric 7\n", encoding="utf-8")
        output_dir = scratch / "output"
        result_holder: list[int] = []

        thread = Thread(
            target=lambda: result_holder.append(
                launcher.main(
                    [
                        "--prom-text-path",
                        str(prom_path),
                        "--listen-host",
                        "127.0.0.1",
                        "--listen-port",
                        "0",
                        "--output-dir",
                        str(output_dir),
                        "--max-requests",
                        "1",
                    ]
                )
            ),
            daemon=True,
        )
        thread.start()

        summary_path = output_dir / "local_prometheus_metrics_bridge.summary.json"
        deadline = time.time() + 5
        while time.time() < deadline and not summary_path.exists():
            time.sleep(0.05)

        assert summary_path.exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        port = summary["listen_port"]

        metrics_text = urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5).read().decode("utf-8")
        thread.join(timeout=5)

        assert "bridge_metric 7" in metrics_text
        assert result_holder == [0]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_metrics_bridge_launcher_serves_observability_export():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("observability")
    try:
        export_path = scratch / "local_lab_observability_export.json"
        export_path.write_text(
            '{"text_payload": "bridge_metric_from_export 11\\n"}',
            encoding="utf-8",
        )
        output_dir = scratch / "output"
        result_holder: list[int] = []

        thread = Thread(
            target=lambda: result_holder.append(
                launcher.main(
                    [
                        "--observability-export-path",
                        str(export_path),
                        "--listen-host",
                        "127.0.0.1",
                        "--listen-port",
                        "0",
                        "--output-dir",
                        str(output_dir),
                        "--max-requests",
                        "1",
                    ]
                )
            ),
            daemon=True,
        )
        thread.start()

        summary_path = output_dir / "local_prometheus_metrics_bridge.summary.json"
        deadline = time.time() + 5
        while time.time() < deadline and not summary_path.exists():
            time.sleep(0.05)

        assert summary_path.exists()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        port = summary["listen_port"]

        metrics_text = urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5).read().decode("utf-8")
        thread.join(timeout=5)

        assert summary["source_kind"] == "observability_export_json"
        assert "bridge_metric_from_export 11" in metrics_text
        assert result_holder == [0]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
