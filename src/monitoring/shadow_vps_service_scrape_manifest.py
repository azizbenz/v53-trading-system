"""Typed scrape handoff artifacts for local Prometheus over Shadow VPS observability."""

from __future__ import annotations

from monitoring.contracts import (
    PrometheusFileSdEntry,
    ShadowVpsServiceMonitoringPayload,
    ShadowVpsServiceScrapeManifest,
)


def build_shadow_vps_service_scrape_manifest(
    payload: ShadowVpsServiceMonitoringPayload,
    *,
    scrape_host: str,
    vps_id: str,
    node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http",
    node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps",
    monitoring_backend_payload_ref: str = "",
    observability_export_ref: str = "",
    labels: dict[str, str] | None = None,
) -> ShadowVpsServiceScrapeManifest:
    """Build a stable local-PC scrape handoff for one VPS service instance."""

    target = f"{scrape_host}:{node_exporter_port}"
    resolved_labels = {
        "job": prometheus_job_name,
        "vps_id": vps_id,
        "runtime_mode": payload.runtime_mode.value,
        "service_status": payload.service_status,
    }
    if labels:
        resolved_labels.update(labels)
    node_exporter_textfile_ready = bool(payload.node_exporter_textfile_ref)
    status = payload.status if node_exporter_textfile_ready else "warning"
    detail = (
        f"target={target} / path={node_exporter_metrics_path} / "
        f"textfile_ready={node_exporter_textfile_ready}"
    )
    return ShadowVpsServiceScrapeManifest(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        status=status,
        detail=detail,
        service_status=payload.service_status,
        vps_id=vps_id,
        scrape_host=scrape_host,
        node_exporter_scheme=node_exporter_scheme,
        node_exporter_port=node_exporter_port,
        node_exporter_metrics_path=node_exporter_metrics_path,
        node_exporter_target=target,
        prometheus_job_name=prometheus_job_name,
        file_sd_entry_count=1,
        node_exporter_textfile_ready=node_exporter_textfile_ready,
        monitoring_backend_payload_ref=monitoring_backend_payload_ref,
        observability_export_ref=observability_export_ref,
        recent_events_summary_ref=payload.recent_events_summary_ref,
        node_exporter_textfile_ref=payload.node_exporter_textfile_ref,
        labels=resolved_labels,
    )


def build_shadow_vps_service_prometheus_file_sd(
    manifest: ShadowVpsServiceScrapeManifest,
) -> tuple[PrometheusFileSdEntry, ...]:
    """Project the scrape manifest into Prometheus file_sd entries."""

    return (
        PrometheusFileSdEntry(
            targets=(manifest.node_exporter_target,),
            labels=manifest.labels,
        ),
    )


__all__ = [
    "build_shadow_vps_service_prometheus_file_sd",
    "build_shadow_vps_service_scrape_manifest",
]
