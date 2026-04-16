#!/usr/bin/env python3
"""Monitoring helpers for the Shadow VPS service."""

from __future__ import annotations

import time
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from monitoring import (
    ProcessMetricsSampler,
    build_shadow_vps_service_monitoring_payload,
    build_shadow_vps_service_observability_export,
    build_shadow_vps_service_prometheus_file_sd,
    build_shadow_vps_service_recent_events_summary,
    build_shadow_vps_service_scrape_manifest,
    sample_disk_usage,
    write_node_exporter_textfile_payload,
    write_observability_text_payload,
)
from protocols import ShadowVpsCampaignSummary, ShadowVpsRuntimeEvidenceBundle, ShadowVpsServiceStore


def _read_runtime_evidence_bundle(
    bundle_path_ref: str,
) -> ShadowVpsRuntimeEvidenceBundle | None:
    if not bundle_path_ref:
        return None
    bundle_path = Path(bundle_path_ref)
    if not bundle_path.is_file():
        return None
    try:
        return ShadowVpsRuntimeEvidenceBundle.model_validate_json(
            bundle_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        return None


def _read_campaign_summary(
    summary_path_ref: str,
) -> ShadowVpsCampaignSummary | None:
    if not summary_path_ref:
        return None
    summary_path = Path(summary_path_ref)
    if not summary_path.is_file():
        return None
    try:
        return ShadowVpsCampaignSummary.model_validate_json(
            summary_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        return None


def _resolve_monitoring_artifact_paths(
    *,
    service_dir: Path,
    node_exporter_textfile_dir: Path | None,
    scrape_host: str,
) -> tuple[Path, Path | None, Path | None, Path | None]:
    recent_events_summary_path = service_dir / "shadow_vps_service_recent_events.json"
    node_exporter_textfile_path = (
        node_exporter_textfile_dir / "v53_shadow_vps_service.prom"
        if node_exporter_textfile_dir is not None
        else None
    )
    scrape_manifest_path = (
        service_dir / "shadow_vps_service_scrape_manifest.json"
        if scrape_host
        else None
    )
    prometheus_file_sd_path = (
        service_dir / "shadow_vps_service_prometheus_file_sd.json"
        if scrape_host
        else None
    )
    return (
        recent_events_summary_path,
        node_exporter_textfile_path,
        scrape_manifest_path,
        prometheus_file_sd_path,
    )


def _write_monitoring_artifacts(
    *,
    service_dir: Path,
    store: ShadowVpsServiceStore,
    sampler: ProcessMetricsSampler,
    node_exporter_textfile_dir: Path | None = None,
    scrape_host: str = "",
    vps_id: str = "",
    node_exporter_port: int = 9100,
    node_exporter_scheme: str = "http",
    node_exporter_metrics_path: str = "/metrics",
    prometheus_job_name: str = "v53_shadow_vps",
) -> tuple[Path, Path, Path, Path, Path | None, Path | None, Path | None]:
    state = store.state
    timestamp_ms = int(time.time() * 1000.0)
    (
        recent_events_summary_path,
        node_exporter_textfile_path,
        scrape_manifest_path,
        prometheus_file_sd_path,
    ) = _resolve_monitoring_artifact_paths(
        service_dir=service_dir,
        node_exporter_textfile_dir=node_exporter_textfile_dir,
        scrape_host=scrape_host,
    )
    payload = build_shadow_vps_service_monitoring_payload(
        timestamp_ms=timestamp_ms,
        state=state,
        process=sampler.sample(),
        disk=sample_disk_usage(service_dir),
        campaign_summary=_read_campaign_summary(state.last_campaign_summary_ref),
        runtime_evidence_bundle=_read_runtime_evidence_bundle(
            state.last_runtime_evidence_bundle_ref
        ),
        state_path=str(store.state_path.resolve()),
        events_path=str(store.events_path.resolve()),
        recent_events_summary_ref=str(recent_events_summary_path.resolve()),
        node_exporter_textfile_ref=(
            str(node_exporter_textfile_path.resolve())
            if node_exporter_textfile_path is not None
            else ""
        ),
        scrape_manifest_ref=(
            str(scrape_manifest_path.resolve()) if scrape_manifest_path is not None else ""
        ),
        prometheus_file_sd_ref=(
            str(prometheus_file_sd_path.resolve()) if prometheus_file_sd_path is not None else ""
        ),
    )
    backend_payload_path = service_dir / "shadow_vps_service_monitoring_backend_payload.json"
    observability_export_path = (
        service_dir / "shadow_vps_service_observability_export.json"
    )
    observability_text_path = service_dir / "shadow_vps_service_observability.prom"
    atomic_write_json(
        backend_payload_path,
        payload.model_dump(mode="json"),
    )
    observability_export = build_shadow_vps_service_observability_export(payload)
    atomic_write_json(
        observability_export_path,
        observability_export.model_dump(mode="json"),
    )
    write_observability_text_payload(
        observability_export,
        observability_text_path,
    )
    if node_exporter_textfile_dir is not None:
        write_node_exporter_textfile_payload(
            observability_export,
            node_exporter_textfile_dir,
            filename="v53_shadow_vps_service.prom",
        )
    atomic_write_json(
        recent_events_summary_path,
        build_shadow_vps_service_recent_events_summary(
            store.events_path,
            max_events=20,
            timestamp_ms=timestamp_ms,
        ).model_dump(mode="json"),
    )
    if scrape_manifest_path is not None and prometheus_file_sd_path is not None:
        scrape_manifest = build_shadow_vps_service_scrape_manifest(
            payload,
            scrape_host=scrape_host,
            vps_id=vps_id or scrape_host,
            node_exporter_port=node_exporter_port,
            node_exporter_scheme=node_exporter_scheme,
            node_exporter_metrics_path=node_exporter_metrics_path,
            prometheus_job_name=prometheus_job_name,
            monitoring_backend_payload_ref=str(backend_payload_path.resolve()),
            observability_export_ref=str(observability_export_path.resolve()),
        )
        atomic_write_json(
            scrape_manifest_path,
            scrape_manifest.model_dump(mode="json"),
        )
        atomic_write_json(
            prometheus_file_sd_path,
            [
                entry.model_dump(mode="json")
                for entry in build_shadow_vps_service_prometheus_file_sd(scrape_manifest)
            ],
        )
    return (
        backend_payload_path,
        observability_export_path,
        observability_text_path,
        recent_events_summary_path,
        node_exporter_textfile_path.resolve()
        if node_exporter_textfile_path is not None
        else None,
        scrape_manifest_path.resolve() if scrape_manifest_path is not None else None,
        prometheus_file_sd_path.resolve()
        if prometheus_file_sd_path is not None
        else None,
    )


def _write_service_monitoring(context: "ShadowVpsServiceRuntimeContext") -> None:
    _write_monitoring_artifacts(
        service_dir=context.service_dir,
        store=context.store,
        sampler=context.process_metrics_sampler,
        node_exporter_textfile_dir=context.monitoring.node_exporter_textfile_dir,
        scrape_host=context.monitoring.scrape_host,
        vps_id=context.monitoring.vps_id,
        node_exporter_port=context.monitoring.node_exporter_port,
        node_exporter_scheme=context.monitoring.node_exporter_scheme,
        node_exporter_metrics_path=context.monitoring.node_exporter_metrics_path,
        prometheus_job_name=context.monitoring.prometheus_job_name,
    )
