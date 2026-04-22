from __future__ import annotations

from monitoring.dashboard_metric_guides import (
    render_local_lab_metric_guide_markdown,
    render_shadow_vps_metric_guide_markdown,
)


def test_render_local_lab_metric_guide_uses_canonical_terms() -> None:
    markdown = render_local_lab_metric_guide_markdown()

    assert "## Metric guide" in markdown
    assert "v53_live_light_gate_group_status" in markdown
    assert "v53_build14_recommended_budget_factor" in markdown
    assert "Prometheus remains the compact machine-readable surface." in markdown
    assert "Grafana is the explanation surface." in markdown


def test_render_shadow_vps_metric_guide_uses_canonical_terms() -> None:
    markdown = render_shadow_vps_metric_guide_markdown()

    assert "## Metric guide" in markdown
    assert "v53_shadow_vps_service_promotion_gate_passed" in markdown
    assert "v53_shadow_vps_execution_runtime_projection_bridge_loaded" in markdown
    assert "v53_shadow_vps_regime_lite_safing_status" in markdown
    assert "Read labels and paired counters together" in markdown
