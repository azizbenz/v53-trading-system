"""Monitoring-side ingestion helpers for Local IA Lab backend payloads."""

from __future__ import annotations

from monitoring.contracts import (
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
    ObservabilityExport,
)


def build_local_lab_monitoring_ingestion_summary(
    *,
    backend_payload: LocalLabMonitoringBackendPayload,
    observability_export: ObservabilityExport,
    backend_payload_ref: str = "",
    observability_export_ref: str = "",
) -> LocalLabMonitoringIngestionSummary:
    """Summarize whether a Local IA Lab monitoring bundle is coherent for backend ingestion."""

    if observability_export.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring ingestion requires matching correlation_id between backend payload and observability export"
        )
    if observability_export.profile != backend_payload.profile:
        raise ValueError(
            "Local IA Lab monitoring ingestion requires matching profile between backend payload and observability export"
        )
    if observability_export.runtime_mode != backend_payload.runtime_mode:
        raise ValueError(
            "Local IA Lab monitoring ingestion requires matching runtime_mode between backend payload and observability export"
        )
    if observability_export.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring ingestion requires matching timestamp_ms between backend payload and observability export"
        )

    text_payload = observability_export.text_payload.strip()
    sample_count = len(observability_export.samples)
    text_payload_present = bool(text_payload)
    text_payload_line_count = len(text_payload.splitlines()) if text_payload else 0
    ingestion_ready = sample_count > 0 and text_payload_present
    ingestion_detail = (
        "Local IA Lab monitoring bundle is ready for backend ingestion."
        if ingestion_ready
        else "Local IA Lab monitoring bundle is incomplete for backend ingestion."
    )

    return LocalLabMonitoringIngestionSummary(
        timestamp_ms=backend_payload.timestamp_ms,
        correlation_id=backend_payload.correlation_id,
        profile=backend_payload.profile,
        runtime_mode=backend_payload.runtime_mode,
        projection_status=backend_payload.status,
        selected_pair=backend_payload.selected_pair,
        selected_engine_id=backend_payload.selected_engine_id,
        release_status=backend_payload.release_status,
        bridge_status=backend_payload.bridge_status,
        promotion_readiness_status=backend_payload.promotion_readiness_status,
        release_ready_for_shadow=backend_payload.release_ready_for_shadow,
        ready_for_shadow_import_dry_run=backend_payload.ready_for_shadow_import_dry_run,
        sample_count=sample_count,
        text_payload_present=text_payload_present,
        text_payload_line_count=text_payload_line_count,
        scope_count=backend_payload.scope_count,
        release_scope_ready_count=backend_payload.release_scope_ready_count,
        release_scope_blocked_count=backend_payload.release_scope_blocked_count,
        blocking_reason_count=backend_payload.blocking_reason_count,
        release_gate_reason_count=backend_payload.release_gate_reason_count,
        ingestion_ready=ingestion_ready,
        ingestion_detail=ingestion_detail,
        observability_export_ref=observability_export_ref,
        backend_payload_ref=backend_payload_ref,
    )


__all__ = ["build_local_lab_monitoring_ingestion_summary"]
