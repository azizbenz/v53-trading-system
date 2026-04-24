"""Build-17 Grafana panel helpers for the local Shadow VPS dashboard."""

from __future__ import annotations

from monitoring.grafana_operator_bridge_markdown import (
    render_shadow_vps_operator_queue_bridge_markdown,
)
from monitoring.grafana_types import GrafanaPayload


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
    h: int = 7,
) -> GrafanaPayload:
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
        "options": {"mode": "markdown", "content": markdown},
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def build_shadow_vps_recovery_and_control_panels(
    *,
    job_filter: str,
    instance_filter: str,
) -> list[GrafanaPayload]:
    return [
        _stat_panel(
            panel_id=17,
            title="Recovery Eligible to Trade",
            expr=f"max(v53_shadow_vps_recovery_eligible_to_trade{{{job_filter},{instance_filter}}})",
            x=0,
            y=60,
        ),
        _stat_panel(
            panel_id=18,
            title="Warmup Eligible to Trade",
            expr=f"max(v53_shadow_vps_warmup_eligible_to_trade{{{job_filter},{instance_filter}}})",
            x=6,
            y=60,
        ),
        _timeseries_panel(
            panel_id=19,
            title="Bootstrap Remote State",
            exprs=[
                (
                    f"v53_shadow_vps_execution_runtime_bootstrap_remote_state_snapshot_captured{{{job_filter},{instance_filter}}}",
                    "remote_snapshot_captured",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_bootstrap_remote_open_order_count{{{job_filter},{instance_filter}}}",
                    "remote_open_order_count",
                ),
                (
                    f"v53_shadow_vps_execution_runtime_bootstrap_remote_position_asset_count{{{job_filter},{instance_filter}}}",
                    "remote_position_asset_count",
                ),
            ],
            x=12,
            y=60,
            w=12,
            h=8,
            unit="short",
        ),
        _timeseries_panel(
            panel_id=20,
            title="Dashboard Control Suspensions",
            exprs=[
                (
                    f"v53_shadow_vps_dashboard_control_halted{{{job_filter},{instance_filter}}}",
                    "dashboard_halted",
                ),
                (
                    f"v53_shadow_vps_dashboard_control_suspended_pair_count{{{job_filter},{instance_filter}}}",
                    "suspended_pair_count",
                ),
                (
                    f"v53_shadow_vps_dashboard_control_suspended_engine_count{{{job_filter},{instance_filter}}}",
                    "suspended_engine_count",
                ),
            ],
            x=0,
            y=68,
            w=12,
            h=8,
            unit="short",
        ),
        _table_panel(
            panel_id=21,
            title="Dashboard Control Labels",
            expr=f"v53_shadow_vps_dashboard_control_halted{{{job_filter},{instance_filter}}}",
            x=12,
            y=68,
            w=12,
            h=8,
        ),
        _table_panel(
            panel_id=22,
            title="Active Artifact and Recovery Labels",
            expr=(
                f"{{__name__=~\"v53_shadow_vps_(recovery_status|warmup_state|active_ml_artifact|"
                f"active_regime_detector_artifact|active_regime_detector_shadow_audit_bundle_present)\",{job_filter},{instance_filter}}}"
            ),
            x=0,
            y=76,
            w=24,
            h=8,
        ),
        _text_panel(
            panel_id=23,
            title="Governed Operator Queue Bridge",
            markdown=render_shadow_vps_operator_queue_bridge_markdown(),
            x=0,
            y=84,
            w=24,
            h=10,
        ),
    ]


__all__ = ["build_shadow_vps_recovery_and_control_panels"]
