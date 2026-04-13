"""Build a detailed local Grafana dashboard over the current V5.3 Shadow VPS metrics."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field


METRIC_NAME_PATTERN = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)")


class LocalGrafanaDashboardSummary(BaseModel, frozen=True):
    """Typed summary for one generated local Grafana dashboard bundle."""

    title: str = Field(..., min_length=1)
    uid: str = Field(..., min_length=1)
    datasource_uid: str = Field(..., min_length=1)
    datasource_name: str = Field(..., min_length=1)
    panel_count: int = Field(default=0, ge=0)
    output_path: str = Field(..., min_length=1)
    observed_metric_count: int = Field(default=0, ge=0)
    observed_metrics: tuple[str, ...] = ()
    source_prom_path: str = Field(..., min_length=1)


def extract_prometheus_metric_names(prom_text: str) -> tuple[str, ...]:
    """Extract unique metric names from a Prometheus text payload."""

    names: list[str] = []
    seen: set[str] = set()
    for raw_line in prom_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = METRIC_NAME_PATTERN.match(line)
        if match is None:
            continue
        metric_name = match.group(1)
        if metric_name in seen:
            continue
        seen.add(metric_name)
        names.append(metric_name)
    return tuple(names)


def _stat_panel(
    *,
    panel_id: int,
    title: str,
    expr: str,
    x: int,
    y: int,
    w: int = 6,
    h: int = 4,
    unit: str = "none",
    color_mode: str = "background",
) -> dict[str, Any]:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [
            {
                "expr": expr,
                "legendFormat": title,
                "refId": "A",
            }
        ],
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
) -> dict[str, Any]:
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
    h: int = 7,
) -> dict[str, Any]:
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [
            {
                "expr": expr,
                "refId": "A",
                "format": "table",
                "instant": True,
            }
        ],
        "options": {
            "showHeader": True,
            "sortBy": [{"displayName": "Value", "desc": True}],
        },
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def build_local_shadow_vps_grafana_dashboard(
    *,
    datasource_uid: str = "prometheus",
    datasource_name: str = "Prometheus",
    title: str = "V5.3 Shadow VPS - Local Dev Observability",
    uid: str = "v53-shadow-vps-local",
) -> dict[str, Any]:
    """Build a detailed Grafana dashboard over the current Shadow VPS metrics."""

    job_filter = 'job=~"$job"'
    instance_filter = 'instance=~"$instance"'

    panels: list[dict[str, Any]] = [
        _stat_panel(
            panel_id=1,
            title="Service Status Series",
            expr=f"max by (status) (v53_shadow_vps_service_status{{{job_filter},{instance_filter}}})",
            x=0,
            y=0,
        ),
        _stat_panel(
            panel_id=2,
            title="Heartbeat Age",
            expr=f"max(v53_shadow_vps_service_heartbeat_age_ms{{{job_filter},{instance_filter}}})",
            x=6,
            y=0,
            unit="ms",
        ),
        _stat_panel(
            panel_id=3,
            title="Promotion Gate Passed",
            expr=f"max(v53_shadow_vps_service_promotion_gate_passed{{{job_filter},{instance_filter}}})",
            x=12,
            y=0,
        ),
        _stat_panel(
            panel_id=4,
            title="Last Error Present",
            expr=f"max(v53_shadow_vps_service_last_error_present{{{job_filter},{instance_filter}}})",
            x=18,
            y=0,
        ),
        _timeseries_panel(
            panel_id=5,
            title="Loop and Outcome Counters",
            exprs=[
                (f"v53_shadow_vps_service_loop_count{{{job_filter},{instance_filter}}}", "loop_count"),
                (f"v53_shadow_vps_service_success_count{{{job_filter},{instance_filter}}}", "success_count"),
                (f"v53_shadow_vps_service_idle_count{{{job_filter},{instance_filter}}}", "idle_count"),
                (f"v53_shadow_vps_service_failure_count{{{job_filter},{instance_filter}}}", "failure_count"),
            ],
            x=0,
            y=4,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=6,
            title="Live Capture and User-Data Signals",
            exprs=[
                (
                    f"v53_shadow_vps_service_live_capture_accepted_message_count{{{job_filter},{instance_filter}}}",
                    "live_capture_accepted",
                ),
                (
                    f"v53_shadow_vps_service_live_user_data_authenticated{{{job_filter},{instance_filter}}}",
                    "user_data_authenticated",
                ),
            ],
            x=12,
            y=4,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=7,
            title="Process Metrics",
            exprs=[
                (f"v53_shadow_vps_process_cpu_pct{{{job_filter},{instance_filter}}}", "cpu_pct"),
                (f"v53_shadow_vps_process_ram_pct{{{job_filter},{instance_filter}}}", "ram_pct"),
                (f"v53_shadow_vps_process_rss_mb{{{job_filter},{instance_filter}}}", "rss_mb"),
                (f"v53_shadow_vps_process_thread_count{{{job_filter},{instance_filter}}}", "thread_count"),
            ],
            x=0,
            y=12,
            w=12,
            h=8,
        ),
        _timeseries_panel(
            panel_id=8,
            title="Disk Metrics",
            exprs=[
                (f"v53_shadow_vps_disk_used_pct{{{job_filter},{instance_filter}}}", "disk_used_pct"),
                (f"v53_shadow_vps_disk_free_gb{{{job_filter},{instance_filter}}}", "disk_free_gb"),
            ],
            x=12,
            y=12,
            w=12,
            h=8,
        ),
        _stat_panel(
            panel_id=9,
            title="Execution Telemetry Ready",
            expr=(
                f"max(v53_shadow_vps_execution_telemetry_ready"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=0,
            y=20,
        ),
        _table_panel(
            panel_id=10,
            title="Execution Telemetry Labels",
            expr=(
                f"v53_shadow_vps_execution_telemetry_ready"
                f"{{{job_filter},{instance_filter}}}"
            ),
            x=6,
            y=20,
            w=18,
            h=8,
        ),
        _stat_panel(
            panel_id=11,
            title="Execution Projection Ready",
            expr=(
                f"max(v53_shadow_vps_execution_runtime_projection_ready"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=0,
            y=28,
        ),
        _timeseries_panel(
            panel_id=12,
            title="Execution Projection Consumer Counts",
            exprs=[
                (
                    f"v53_shadow_vps_execution_runtime_projection_ready_consumer_count"
                    f"{{{job_filter},{instance_filter}}}",
                    "ready_consumers",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_projection_partial_consumer_count"
                    f"{{{job_filter},{instance_filter}}}",
                    "partial_consumers",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_projection_blocked_consumer_count"
                    f"{{{job_filter},{instance_filter}}}",
                    "blocked_consumers",
                ),
            ],
            x=6,
            y=28,
            w=18,
            h=8,
            unit="short",
        ),
        _table_panel(
            panel_id=13,
            title="Execution Projection Labels",
            expr=(
                f"v53_shadow_vps_execution_runtime_projection_ready"
                f"{{{job_filter},{instance_filter}}}"
            ),
            x=0,
            y=36,
            w=12,
            h=8,
        ),
        _stat_panel(
            panel_id=14,
            title="Execution Projection Bridge Loaded",
            expr=(
                f"max(v53_shadow_vps_execution_runtime_projection_bridge_loaded"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=12,
            y=36,
        ),
        _timeseries_panel(
            panel_id=15,
            title="Execution Projection Model Loads",
            exprs=[
                (
                    f"v53_shadow_vps_execution_runtime_projection_rate_limit_model_loaded"
                    f"{{{job_filter},{instance_filter}}}",
                    "rate_limit_model",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_projection_spread_guard_model_loaded"
                    f"{{{job_filter},{instance_filter}}}",
                    "spread_guard_model",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_projection_slippage_model_loaded"
                    f"{{{job_filter},{instance_filter}}}",
                    "slippage_model",
                ),
            ],
            x=0,
            y=44,
            w=24,
            h=8,
            unit="short",
        ),
        _table_panel(
            panel_id=16,
            title="Execution Projection Bridge Labels",
            expr=(
                f"v53_shadow_vps_execution_runtime_projection_bridge_loaded"
                f"{{{job_filter},{instance_filter}}}"
            ),
            x=0,
            y=52,
            w=24,
            h=8,
        ),
        _table_panel(
            panel_id=17,
            title="Instant Metric Snapshot",
            expr=f"{{__name__=~\"v53_shadow_vps_.*\",{job_filter},{instance_filter}}}",
            x=0,
            y=60,
            w=24,
            h=8,
        ),
        _stat_panel(
            panel_id=18,
            title="Regime Lite Entries Blocked",
            expr=(
                f"max(v53_shadow_vps_regime_lite_entries_blocked"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=0,
            y=68,
        ),
        _stat_panel(
            panel_id=19,
            title="Regime Lite Exit-All Recommended",
            expr=(
                f"max(v53_shadow_vps_regime_lite_should_exit_all"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=6,
            y=68,
        ),
        _table_panel(
            panel_id=20,
            title="Regime Lite Labels",
            expr=(
                f"v53_shadow_vps_regime_lite_safing_status"
                f"{{{job_filter},{instance_filter}}}"
            ),
            x=12,
            y=68,
            w=12,
            h=8,
        ),
        _stat_panel(
            panel_id=21,
            title="Telegram Alerts",
            expr=(
                f"max(v53_shadow_vps_telegram_alert_delivery_status"
                f"{{{job_filter},{instance_filter}}})"
            ),
            x=0,
            y=76,
        ),
        _table_panel(
            panel_id=22,
            title="Telegram Alert Labels",
            expr=(
                f"v53_shadow_vps_telegram_alert_delivery_status"
                f"{{{job_filter},{instance_filter}}}"
            ),
            x=6,
            y=76,
            w=18,
            h=8,
        ),
    ]

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
        "tags": ["v53", "shadow", "vps", "local-dev", "prometheus"],
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
                        "query": "label_values(v53_shadow_vps_service_status, job)",
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
                        "query": "label_values(v53_shadow_vps_service_status{job=~\"$job\"}, instance)",
                        "refId": "PromInstanceVar",
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

    return {
        "dashboard": dashboard,
        "overwrite": True,
    }


def build_local_shadow_vps_grafana_dashboard_summary(
    *,
    source_prom_path: str | Path,
    output_path: str | Path,
    datasource_uid: str = "prometheus",
    datasource_name: str = "Prometheus",
    title: str = "V5.3 Shadow VPS - Local Dev Observability",
    uid: str = "v53-shadow-vps-local",
) -> LocalGrafanaDashboardSummary:
    """Project dashboard generation metadata into a typed summary."""

    resolved_source = Path(source_prom_path).expanduser().resolve()
    observed_metrics: tuple[str, ...] = ()
    if resolved_source.exists():
        observed_metrics = extract_prometheus_metric_names(
            resolved_source.read_text(encoding="utf-8")
        )
    payload = build_local_shadow_vps_grafana_dashboard(
        datasource_uid=datasource_uid,
        datasource_name=datasource_name,
        title=title,
        uid=uid,
    )
    panel_count = len(payload["dashboard"]["panels"])
    return LocalGrafanaDashboardSummary(
        title=title,
        uid=uid,
        datasource_uid=datasource_uid,
        datasource_name=datasource_name,
        panel_count=panel_count,
        output_path=str(Path(output_path).expanduser().resolve()),
        observed_metric_count=len(observed_metrics),
        observed_metrics=observed_metrics,
        source_prom_path=str(resolved_source),
    )


__all__ = [
    "LocalGrafanaDashboardSummary",
    "build_local_shadow_vps_grafana_dashboard",
    "build_local_shadow_vps_grafana_dashboard_summary",
    "extract_prometheus_metric_names",
]
