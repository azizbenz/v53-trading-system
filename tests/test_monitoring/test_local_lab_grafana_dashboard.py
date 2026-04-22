from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from monitoring.local_lab_grafana_dashboard import (
    build_local_lab_grafana_dashboard,
    build_local_lab_grafana_dashboard_summary,
)


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-lab-grafana-dashboard-unit", label)


def test_build_local_lab_grafana_dashboard_contains_expected_queries():
    payload = build_local_lab_grafana_dashboard()
    panels = payload["dashboard"]["panels"]
    titles = {panel["title"] for panel in panels}
    guide_panel = next(panel for panel in panels if panel["title"] == "Metric Guide and Threshold Semantics")

    assert payload["overwrite"] is True
    assert "Core Gate Readiness" in titles
    assert "Calibration Methods" in titles
    assert "Replay Workflow" in titles
    assert "Metric Guide and Threshold Semantics" in titles
    all_exprs = [
        target["expr"]
        for panel in panels
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    assert any("v53_local_lab_artifact_proof_ready" in expr for expr in all_exprs)
    assert any("v53_local_lab_execution_ready_threshold_count" in expr for expr in all_exprs)
    assert any("v53_local_lab_replay_dispatch_ready_count" in expr for expr in all_exprs)
    assert guide_panel["type"] == "text"
    assert guide_panel["options"]["mode"] == "markdown"
    assert "v53_live_light_gate_group_status" in guide_panel["options"]["content"]
    assert "v53_build14_recommended_budget_factor" in guide_panel["options"]["content"]


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

        assert summary.panel_count == 17
        assert summary.observed_metric_count == 2
        assert "v53_local_lab_monitoring_status" in summary.observed_metrics
        assert summary.source_kind == "observability_export_json"
        assert summary.output_path.endswith("dashboard.json")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
