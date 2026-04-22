"""Build a detailed local Grafana dashboard over the current V5.3 Local IA Lab metrics."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from monitoring.dashboard_metric_guides import render_local_lab_metric_guide_markdown
from monitoring.grafana_types import GrafanaPayload
from monitoring.local_grafana_dashboard import extract_prometheus_metric_names
from monitoring.local_prometheus_metrics_bridge import load_local_prometheus_text_payload


class LocalLabGrafanaDashboardSummary(BaseModel, frozen=True):
    """Typed summary for one generated Local IA Lab Grafana dashboard bundle."""

    title: str = Field(..., min_length=1)
    uid: str = Field(..., min_length=1)
    datasource_uid: str = Field(..., min_length=1)
    datasource_name: str = Field(..., min_length=1)
    panel_count: int = Field(default=0, ge=0)
    output_path: str = Field(..., min_length=1)
    observed_metric_count: int = Field(default=0, ge=0)
    observed_metrics: tuple[str, ...] = ()
    source_path: str = Field(..., min_length=1)
    source_kind: str = Field(..., min_length=1)


def _stat_panel(
    *,
    panel_id: int,
    title: str,
    expr: str,
    x: int,
    y: int,
    w: int = 4,
    h: int = 4,
    unit: str = "none",
    color_mode: str = "background",
) -> GrafanaPayload:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"expr": expr, "legendFormat": title, "refId": "A"}],
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "orientation": "auto",
            "colorMode": color_mode,
            "graphMode": "none",
            "justifyMode": "auto",
            "textMode": "auto",
        },
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "orange", "value": 1},
                    ],
                },
            },
            "overrides": [],
        },
    }


def _timeseries_panel(
    *,
    panel_id: int,
    title: str,
    exprs: list[tuple[str, str]],
    x: int,
    y: int,
    w: int = 12,
    h: int = 8,
    unit: str = "none",
) -> GrafanaPayload:
    targets = [
        {
            "expr": expr,
            "legendFormat": legend,
            "refId": chr(ord("A") + index),
        }
        for index, (expr, legend) in enumerate(exprs)
    ]
    return {
        "id": panel_id,
        "type": "timeseries",
        "title": title,
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 10,
                    "showPoints": "never",
                    "spanNulls": True,
                },
            },
            "overrides": [],
        },
        "options": {
            "legend": {"displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def _table_panel(
    *,
    panel_id: int,
    title: str,
    expr: str,
    x: int,
    y: int,
    w: int = 24,
    h: int = 8,
) -> GrafanaPayload:
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [{"expr": expr, "refId": "A", "format": "table", "instant": True}],
        "options": {
            "showHeader": True,
            "sortBy": [{"displayName": "Value", "desc": True}],
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _text_panel(
    *,
    panel_id: int,
    title: str,
    markdown: str,
    x: int,
    y: int,
    w: int = 24,
    h: int = 10,
) -> GrafanaPayload:
    return {
        "id": panel_id,
        "type": "text",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {
            "mode": "markdown",
            "content": markdown,
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def _build_local_lab_overview_panels(*, base_filter: str) -> list[GrafanaPayload]:
    return [
        _stat_panel(
            panel_id=1,
            title="Monitoring Status Series",
            expr=f"max by (status) (v53_local_lab_monitoring_status{{{base_filter}}})",
            x=0,
            y=0,
        ),
        _stat_panel(
            panel_id=2,
            title="Review Ready",
            expr=f"max(v53_local_lab_review_ready{{{base_filter}}})",
            x=4,
            y=0,
        ),
        _stat_panel(
            panel_id=3,
            title="Artifact Proof Ready",
            expr=f"max(v53_local_lab_artifact_proof_ready{{{base_filter}}})",
            x=8,
            y=0,
        ),
        _stat_panel(
            panel_id=4,
            title="Release Ready for Shadow",
            expr=f"max(v53_local_lab_release_ready_for_shadow{{{base_filter}}})",
            x=12,
            y=0,
        ),
        _stat_panel(
            panel_id=5,
            title="Dry-Run Ready for Shadow",
            expr=f"max(v53_local_lab_dry_run_ready_for_shadow{{{base_filter}}})",
            x=16,
            y=0,
        ),
        _stat_panel(
            panel_id=6,
            title="Blocking Reason Count",
            expr=f"max(v53_local_lab_blocking_reason_count{{{base_filter}}})",
            x=20,
            y=0,
            unit="short",
        ),
    ]


def _build_local_lab_readiness_panels(*, base_filter: str) -> list[GrafanaPayload]:
    return [
        _timeseries_panel(
            panel_id=7,
            title="Core Gate Readiness",
            exprs=[
                (f"v53_local_lab_review_ready{{{base_filter}}}", "review_ready"),
                (
                    f"v53_local_lab_trade_loss_attribution_ready{{{base_filter}}}",
                    "trade_loss_attribution_ready",
                ),
                (f"v53_local_lab_walk_forward_ready{{{base_filter}}}", "walk_forward_ready"),
                (
                    f"v53_local_lab_artifact_ablation_ready{{{base_filter}}}",
                    "artifact_ablation_ready",
                ),
                (
                    f"v53_local_lab_artifact_proof_ready{{{base_filter}}}",
                    "artifact_proof_ready",
                ),
                (
                    f"v53_local_lab_edge_calibration_ready{{{base_filter}}}",
                    "edge_calibration_ready",
                ),
            ],
            x=0,
            y=4,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=8,
            title="Promotion and Reason Counts",
            exprs=[
                (
                    f"v53_local_lab_release_ready_for_shadow{{{base_filter}}}",
                    "release_ready_for_shadow",
                ),
                (
                    f"v53_local_lab_dry_run_ready_for_shadow{{{base_filter}}}",
                    "dry_run_ready_for_shadow",
                ),
                (
                    f"v53_local_lab_blocking_reason_count{{{base_filter}}}",
                    "blocking_reason_count",
                ),
                (
                    f"v53_local_lab_release_gate_reason_count{{{base_filter}}}",
                    "release_gate_reason_count",
                ),
            ],
            x=12,
            y=4,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=9,
            title="Scope and Release Counts",
            exprs=[
                (f"v53_local_lab_scope_count{{{base_filter}}}", "scope_count"),
                (f"v53_local_lab_scope_ready_count{{{base_filter}}}", "scope_ready_count"),
                (f"v53_local_lab_scope_blocked_count{{{base_filter}}}", "scope_blocked_count"),
                (
                    f"v53_local_lab_release_scope_ready_count{{{base_filter}}}",
                    "release_scope_ready_count",
                ),
                (
                    f"v53_local_lab_release_scope_blocked_count{{{base_filter}}}",
                    "release_scope_blocked_count",
                ),
            ],
            x=0,
            y=12,
            w=12,
            h=8,
        ),
    ]


def _build_local_lab_calibration_panels(*, base_filter: str) -> list[GrafanaPayload]:
    return [
        _timeseries_panel(
            panel_id=10,
            title="Calibration Methods",
            exprs=[
                (
                    f"v53_local_lab_calibration_methods_review_ready{{{base_filter}}}",
                    "calibration_methods_review_ready",
                ),
                (
                    f"v53_local_lab_calibration_methods_dsr_pass{{{base_filter}}}",
                    "calibration_methods_dsr_pass",
                ),
                (
                    f"v53_local_lab_calibration_methods_walkforward_plan_ready{{{base_filter}}}",
                    "calibration_methods_walkforward_plan_ready",
                ),
                (
                    f"v53_local_lab_calibration_methods_stationarity_pass{{{base_filter}}}",
                    "calibration_methods_stationarity_pass",
                ),
            ],
            x=12,
            y=12,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=11,
            title="Execution Threshold Review",
            exprs=[
                (
                    f"v53_local_lab_execution_review_ready{{{base_filter}}}",
                    "execution_review_ready",
                ),
                (
                    f"v53_local_lab_execution_ready_threshold_count{{{base_filter}}}",
                    "execution_ready_threshold_count",
                ),
                (
                    f"v53_local_lab_execution_partial_threshold_count{{{base_filter}}}",
                    "execution_partial_threshold_count",
                ),
                (
                    f"v53_local_lab_execution_blocked_threshold_count{{{base_filter}}}",
                    "execution_blocked_threshold_count",
                ),
            ],
            x=0,
            y=20,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=12,
            title="Multiple Testing and Normalized Calibration",
            exprs=[
                (
                    f"v53_local_lab_multiple_testing_review_ready{{{base_filter}}}",
                    "multiple_testing_review_ready",
                ),
                (
                    f"v53_local_lab_multiple_testing_correction_required{{{base_filter}}}",
                    "multiple_testing_correction_required",
                ),
                (
                    f"v53_local_lab_multiple_testing_family_count{{{base_filter}}}",
                    "multiple_testing_family_count",
                ),
                (
                    f"v53_local_lab_calibration_normalized_report_ready{{{base_filter}}}",
                    "calibration_normalized_report_ready",
                ),
                (
                    f"v53_local_lab_calibration_normalized_threshold_count{{{base_filter}}}",
                    "calibration_normalized_threshold_count",
                ),
            ],
            x=12,
            y=20,
            w=12,
            h=8,
        ),
    ]


def _build_local_lab_tail_panels(*, base_filter: str) -> list[GrafanaPayload]:
    return [
        _timeseries_panel(
            panel_id=13,
            title="Tail Risk Review",
            exprs=[
                (
                    f"v53_local_lab_tail_risk_review_ready{{{base_filter}}}",
                    "tail_risk_review_ready",
                ),
                (
                    f"v53_local_lab_tail_risk_ready_breaker_count{{{base_filter}}}",
                    "tail_risk_ready_breaker_count",
                ),
                (
                    f"v53_local_lab_tail_risk_partial_breaker_count{{{base_filter}}}",
                    "tail_risk_partial_breaker_count",
                ),
                (
                    f"v53_local_lab_tail_risk_blocked_breaker_count{{{base_filter}}}",
                    "tail_risk_blocked_breaker_count",
                ),
            ],
            x=0,
            y=28,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=14,
            title="Research and Loss Surrogate",
            exprs=[
                (
                    f"v53_local_lab_loss_surrogate_ready{{{base_filter}}}",
                    "loss_surrogate_ready",
                ),
                (
                    f"v53_local_lab_loss_surrogate_scope_count{{{base_filter}}}",
                    "loss_surrogate_scope_count",
                ),
                (
                    f"v53_local_lab_loss_surrogate_top_probability{{{base_filter}}}",
                    "loss_surrogate_top_probability",
                ),
                (
                    f"v53_local_lab_research_priority_scope_count{{{base_filter}}}",
                    "research_priority_scope_count",
                ),
                (
                    f"v53_local_lab_research_priority_top_score{{{base_filter}}}",
                    "research_priority_top_score",
                ),
            ],
            x=12,
            y=28,
            w=12,
            h=8,
            unit="percentunit",
        ),
        _timeseries_panel(
            panel_id=15,
            title="Replay Workflow",
            exprs=[
                (
                    f"v53_local_lab_replay_candidate_count{{{base_filter}}}",
                    "replay_candidate_count",
                ),
                (
                    f"v53_local_lab_replay_candidate_ready_count{{{base_filter}}}",
                    "replay_candidate_ready_count",
                ),
                (
                    f"v53_local_lab_replay_ticket_count{{{base_filter}}}",
                    "replay_ticket_count",
                ),
                (
                    f"v53_local_lab_replay_ticket_ready_count{{{base_filter}}}",
                    "replay_ticket_ready_count",
                ),
                (
                    f"v53_local_lab_replay_dispatch_ready_count{{{base_filter}}}",
                    "replay_dispatch_ready_count",
                ),
                (
                    f"v53_local_lab_replay_dispatch_blocked_count{{{base_filter}}}",
                    "replay_dispatch_blocked_count",
                ),
            ],
            x=0,
            y=36,
            w=24,
            h=8,
        ),
        _table_panel(
            panel_id=16,
            title="Instant Local IA Lab Metric Snapshot",
            expr=f'{{__name__=~"v53_local_lab_.*",{base_filter}}}',
            x=0,
            y=44,
            w=24,
            h=8,
        ),
        _text_panel(
            panel_id=17,
            title="Metric Guide and Threshold Semantics",
            markdown=render_local_lab_metric_guide_markdown(),
            x=0,
            y=52,
            w=24,
            h=10,
        ),
    ]


def build_local_lab_grafana_dashboard(
    *,
    datasource_uid: str = "prometheus",
    datasource_name: str = "Prometheus",
    title: str = "V5.3 Local IA Lab - Local Dev Observability",
    uid: str = "v53-local-lab",
) -> GrafanaPayload:
    """Build a detailed Grafana dashboard over the current Local IA Lab metrics."""

    base_filter = 'job=~"$job",instance=~"$instance",correlation_id=~"$correlation_id"'
    panels = (
        _build_local_lab_overview_panels(base_filter=base_filter)
        + _build_local_lab_readiness_panels(base_filter=base_filter)
        + _build_local_lab_calibration_panels(base_filter=base_filter)
        + _build_local_lab_tail_panels(base_filter=base_filter)
    )

    dashboard = {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": panels,
        "refresh": "15s",
        "schemaVersion": 39,
        "style": "dark",
        "tags": ["v53", "local-lab", "observability", "prometheus", "local-dev"],
        "templating": {
            "list": [
                {
                    "name": "DS_PROMETHEUS",
                    "label": "Datasource",
                    "type": "datasource",
                    "query": "prometheus",
                    "current": {
                        "selected": True,
                        "text": datasource_name,
                        "value": datasource_uid,
                    },
                },
                {
                    "name": "job",
                    "label": "Job",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
                    "query": {
                        "query": "label_values(v53_local_lab_monitoring_status, job)",
                        "refId": "PromJobVar",
                    },
                    "includeAll": True,
                    "multi": False,
                    "current": {"selected": True, "text": "All", "value": "$__all"},
                },
                {
                    "name": "instance",
                    "label": "Instance",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
                    "query": {
                        "query": "label_values(v53_local_lab_monitoring_status{job=~\"$job\"}, instance)",
                        "refId": "PromInstanceVar",
                    },
                    "includeAll": True,
                    "multi": False,
                    "current": {"selected": True, "text": "All", "value": "$__all"},
                },
                {
                    "name": "correlation_id",
                    "label": "Correlation",
                    "type": "query",
                    "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
                    "query": {
                        "query": (
                            "label_values("
                            "v53_local_lab_monitoring_status{job=~\"$job\",instance=~\"$instance\"}, "
                            "correlation_id)"
                        ),
                        "refId": "PromCorrelationVar",
                    },
                    "includeAll": True,
                    "multi": False,
                    "current": {"selected": True, "text": "All", "value": "$__all"},
                },
            ]
        },
        "time": {"from": "now-15m", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "",
    }
    return {"dashboard": dashboard, "overwrite": True}


def build_local_lab_grafana_dashboard_summary(
    *,
    output_path: str | Path,
    prom_text_path: str | Path | None = None,
    observability_export_path: str | Path | None = None,
    datasource_uid: str = "prometheus",
    datasource_name: str = "Prometheus",
    title: str = "V5.3 Local IA Lab - Local Dev Observability",
    uid: str = "v53-local-lab",
) -> LocalLabGrafanaDashboardSummary:
    """Project Local IA Lab dashboard generation metadata into a typed summary."""

    prom_text, resolved_source, source_kind = load_local_prometheus_text_payload(
        source_prom_path=prom_text_path,
        observability_export_path=observability_export_path,
    )
    observed_metrics = extract_prometheus_metric_names(prom_text)
    payload = build_local_lab_grafana_dashboard(
        datasource_uid=datasource_uid,
        datasource_name=datasource_name,
        title=title,
        uid=uid,
    )
    return LocalLabGrafanaDashboardSummary(
        title=title,
        uid=uid,
        datasource_uid=datasource_uid,
        datasource_name=datasource_name,
        panel_count=len(payload["dashboard"]["panels"]),
        output_path=str(Path(output_path).expanduser().resolve()),
        observed_metric_count=len(observed_metrics),
        observed_metrics=observed_metrics,
        source_path=str(resolved_source),
        source_kind=source_kind,
    )


__all__ = [
    "LocalLabGrafanaDashboardSummary",
    "build_local_lab_grafana_dashboard",
    "build_local_lab_grafana_dashboard_summary",
]
