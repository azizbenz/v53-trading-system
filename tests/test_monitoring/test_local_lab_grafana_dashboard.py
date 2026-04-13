from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from monitoring.local_lab_grafana_dashboard import (
    build_local_lab_grafana_dashboard,
    build_local_lab_grafana_dashboard_summary,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "pytest-local-lab-grafana-dashboard-unit"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_build_local_lab_grafana_dashboard_contains_expected_queries():
    payload = build_local_lab_grafana_dashboard()
    panels = payload["dashboard"]["panels"]
    titles = {panel["title"] for panel in panels}

    assert payload["overwrite"] is True
    assert "Core Gate Readiness" in titles
    assert "Calibration Methods" in titles
    assert "Replay Workflow" in titles
    all_exprs = [
        target["expr"]
        for panel in panels
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    assert any("v53_local_lab_artifact_proof_ready" in expr for expr in all_exprs)
    assert any("v53_local_lab_execution_ready_threshold_count" in expr for expr in all_exprs)
    assert any("v53_local_lab_replay_dispatch_ready_count" in expr for expr in all_exprs)


def test_build_local_lab_grafana_dashboard_summary_reads_observability_export_text_payload():
    scratch = _scratch_dir("summary")
    try:
        export_path = scratch / "local_lab_observability_export.json"
        export_path.write_text(
            (
                '{"text_payload": '
                '"v53_local_lab_monitoring_status{status=\\"warning\\"} 2\\n'
                'v53_local_lab_artifact_proof_ready 1\\n"}'
            ),
            encoding="utf-8",
        )
        output_path = scratch / "dashboard.json"

        summary = build_local_lab_grafana_dashboard_summary(
            observability_export_path=export_path,
            output_path=output_path,
        )

        assert summary.panel_count == 16
        assert summary.observed_metric_count == 2
        assert "v53_local_lab_monitoring_status" in summary.observed_metrics
        assert summary.source_kind == "observability_export_json"
        assert summary.output_path.endswith("dashboard.json")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
