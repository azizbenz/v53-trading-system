from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_lab_grafana_dashboard.py"
    module_name = "test_run_local_lab_grafana_dashboard"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "pytest-local-lab-grafana-dashboard"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_local_lab_grafana_dashboard_launcher_writes_dashboard_and_summary():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        export_path = scratch / "local_lab_observability_export.json"
        export_path.write_text(
            (
                '{"text_payload": '
                '"v53_local_lab_monitoring_status{status=\\"warning\\"} 2\\n'
                'v53_local_lab_replay_dispatch_ready_count 3\\n"}'
            ),
            encoding="utf-8",
        )
        output_dir = scratch / "output"

        exit_code = launcher.main(
            [
                "--observability-export-path",
                str(export_path),
                "--output-dir",
                str(output_dir),
                "--datasource-uid",
                "prometheus",
                "--datasource-name",
                "Prometheus",
            ]
        )

        assert exit_code == 0
        dashboard = json.loads(
            (output_dir / "v53_local_lab_grafana.dashboard.json").read_text(
                encoding="utf-8"
            )
        )
        summary = json.loads(
            (output_dir / "v53_local_lab_grafana.summary.json").read_text(
                encoding="utf-8"
            )
        )

        assert dashboard["dashboard"]["uid"] == "v53-local-lab"
        assert len(dashboard["dashboard"]["panels"]) == 16
        assert summary["observed_metric_count"] == 2
        assert summary["datasource_uid"] == "prometheus"
        assert summary["source_kind"] == "observability_export_json"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
