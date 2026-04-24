from __future__ import annotations

from pathlib import Path
import shutil

from monitoring.local_grafana_dashboard import (
    build_local_shadow_vps_grafana_dashboard,
    build_local_shadow_vps_grafana_dashboard_summary,
    extract_prometheus_metric_names,
)


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-grafana-dashboard-summary", label)


def test_extract_prometheus_metric_names_preserves_unique_metric_order() -> None:
    prom_text = """# comment
metric_a{label="x"} 1
metric_b 2
metric_a{label="y"} 3
"""

    assert extract_prometheus_metric_names(prom_text) == ("metric_a", "metric_b")


def _dashboard_titles_and_exprs() -> tuple[
    dict[str, object],
    set[str],
    dict[str, object],
    list[str],
]:
    payload = build_local_shadow_vps_grafana_dashboard()
    panels = payload["dashboard"]["panels"]
    titles = {panel["title"] for panel in panels}
    guide_panel = next(
        panel
        for panel in panels
        if panel["title"] == "Metric Guide and Status Semantics"
    )
    all_exprs = [
        target["expr"]
        for panel in panels
        for target in panel.get("targets", [])
        if "expr" in target
    ]
    return payload, titles, guide_panel, all_exprs


def test_build_local_shadow_vps_grafana_dashboard_contains_expected_panels() -> None:
    payload, titles, guide_panel, _ = _dashboard_titles_and_exprs()

    assert payload["overwrite"] is True
    assert "Loop and Outcome Counters" in titles
    assert "Process Metrics" in titles
    assert "Execution Telemetry Ready" in titles
    assert "Execution Telemetry Labels" in titles
    assert "Execution Projection Ready" in titles
    assert "Execution Projection Consumer Counts" in titles
    assert "Execution Projection Labels" in titles
    assert "Execution Projection Bridge Loaded" in titles
    assert "Execution Projection Model Loads" in titles
    assert "Execution Projection Bridge Labels" in titles
    assert "Recovery Eligible to Trade" in titles
    assert "Warmup Eligible to Trade" in titles
    assert "Bootstrap Remote State" in titles
    assert "Dashboard Control Suspensions" in titles
    assert "Dashboard Control Labels" in titles
    assert "Active Artifact and Recovery Labels" in titles
    assert "Governed Operator Queue Bridge" in titles
    assert "Regime Lite Entries Blocked" in titles
    assert "Regime Lite Exit-All Recommended" in titles
    assert "Regime Lite Labels" in titles
    assert "Telegram Alerts" in titles
    assert "Telegram Alert Labels" in titles
    assert "Instant Metric Snapshot" in titles
    assert "Metric Guide and Status Semantics" in titles
    assert guide_panel["type"] == "text"
    assert guide_panel["options"]["mode"] == "markdown"
    assert (
        "v53_shadow_vps_service_promotion_gate_passed"
        in guide_panel["options"]["content"]
    )
    assert (
        "v53_shadow_vps_execution_runtime_projection_bridge_loaded"
        in guide_panel["options"]["content"]
    )
    assert "v53_shadow_vps_recovery_status" in guide_panel["options"]["content"]
    assert (
        "v53_shadow_vps_dashboard_control_halted"
        in guide_panel["options"]["content"]
    )
    assert (
        "v53_shadow_vps_active_regime_detector_artifact"
        in guide_panel["options"]["content"]
    )
    assert (
        "v53_shadow_vps_regime_lite_safing_status"
        in guide_panel["options"]["content"]
    )
    assert (
        "v53_shadow_vps_telegram_alert_delivery_status"
        in guide_panel["options"]["content"]
    )
    bridge_panel = next(
        panel
        for panel in payload["dashboard"]["panels"]
        if panel["title"] == "Governed Operator Queue Bridge"
    )
    assert bridge_panel["type"] == "text"
    assert bridge_panel["options"]["mode"] == "markdown"
    assert "run_dashboard_governed_command.py" in bridge_panel["options"]["content"]
    assert "--command-kind set_halted" in bridge_panel["options"]["content"]
    assert "--command-kind rollback_to_light" in bridge_panel["options"]["content"]
    assert (
        "request_export_regime_detector_shadow_audit_bundle"
        in bridge_panel["options"]["content"]
    )


def test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries() -> None:
    _, _, _, all_exprs = _dashboard_titles_and_exprs()

    assert any("v53_shadow_vps_service_failure_count" in expr for expr in all_exprs)
    assert any("v53_shadow_vps_process_cpu_pct" in expr for expr in all_exprs)
    assert any("v53_shadow_vps_disk_free_gb" in expr for expr in all_exprs)
    assert any(
        "v53_shadow_vps_execution_telemetry_ready" in expr for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_ready" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_ready_consumer_count" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_partial_consumer_count" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_blocked_consumer_count" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_bridge_loaded" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_rate_limit_model_loaded" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_spread_guard_model_loaded" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_projection_slippage_model_loaded" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_recovery_eligible_to_trade" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_warmup_eligible_to_trade" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_bootstrap_remote_state_snapshot_captured"
        in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_bootstrap_remote_open_order_count"
        in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_execution_runtime_bootstrap_remote_position_asset_count"
        in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_dashboard_control_halted" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_dashboard_control_suspended_pair_count" in expr
        for expr in all_exprs
    )
    assert any(
        "active_regime_detector_artifact" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_regime_lite_entries_blocked" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_regime_lite_should_exit_all" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_regime_lite_safing_status" in expr
        for expr in all_exprs
    )
    assert any(
        "v53_shadow_vps_telegram_alert_delivery_status" in expr
        for expr in all_exprs
    )


def test_build_local_shadow_vps_grafana_dashboard_summary_reads_observed_metrics() -> None:
    scratch = _scratch_dir("summary")
    try:
        prom_path = scratch / "shadow_vps_service_observability.prom"
        prom_path.write_text(
            "v53_shadow_vps_service_status{status=\"healthy\"} 1\n"
            "v53_shadow_vps_process_cpu_pct 0\n",
            encoding="utf-8",
        )
        output_path = scratch / "dashboard.json"

        summary = build_local_shadow_vps_grafana_dashboard_summary(
            source_prom_path=prom_path,
            output_path=output_path,
        )

        assert summary.panel_count == 30
        assert summary.observed_metric_count == 2
        assert "v53_shadow_vps_service_status" in summary.observed_metrics
        assert summary.output_path.endswith("dashboard.json")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
