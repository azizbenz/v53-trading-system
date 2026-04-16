"""Typed monitoring projection for the real Shadow VPS service loop."""

from __future__ import annotations

from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
)
from monitoring.contracts import (
    DiskUsageSample,
    ObservabilityExport,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.shadow_vps_service_monitoring_observability_support import (
    build_shadow_vps_service_observability_export_support,
)
from monitoring.shadow_vps_service_monitoring_payload_support import (
    build_shadow_vps_service_monitoring_payload_support,
)


def build_shadow_vps_service_monitoring_payload(
    *,
    timestamp_ms: int,
    state: ShadowVpsServiceState,
    process: ProcessMetricsSample,
    disk: DiskUsageSample,
    campaign_summary: ShadowVpsCampaignSummary | None = None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None = None,
    state_path: str = "",
    events_path: str = "",
    recent_events_summary_ref: str = "",
    node_exporter_textfile_ref: str = "",
    scrape_manifest_ref: str = "",
    prometheus_file_sd_ref: str = "",
) -> ShadowVpsServiceMonitoringPayload:
    """Project durable service state into a future-dashboard payload."""

    return build_shadow_vps_service_monitoring_payload_support(
        timestamp_ms=timestamp_ms,
        state=state,
        process=process,
        disk=disk,
        campaign_summary=campaign_summary,
        runtime_evidence_bundle=runtime_evidence_bundle,
        state_path=state_path,
        events_path=events_path,
        recent_events_summary_ref=recent_events_summary_ref,
        node_exporter_textfile_ref=node_exporter_textfile_ref,
        scrape_manifest_ref=scrape_manifest_ref,
        prometheus_file_sd_ref=prometheus_file_sd_ref,
    )


def build_shadow_vps_service_observability_export(
    payload: ShadowVpsServiceMonitoringPayload,
) -> ObservabilityExport:
    """Emit a compact Prometheus-style export for the real Shadow VPS service."""

    return build_shadow_vps_service_observability_export_support(payload)


__all__ = [
    "build_shadow_vps_service_monitoring_payload",
    "build_shadow_vps_service_observability_export",
]
