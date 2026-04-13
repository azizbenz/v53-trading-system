"""Manifest over Local IA Lab monitoring sidecars."""

from __future__ import annotations

from pydantic import BaseModel, Field

from monitoring.contracts import (
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
    ObservabilityExport,
)


class LocalLabMonitoringBundleManifest(BaseModel, frozen=True):
    """Stable manifest for future Local IA Lab monitoring ingestion."""

    timestamp_ms: int = Field(..., ge=0)
    correlation_id: str = Field(..., min_length=1)
    profile: str = Field(..., min_length=1)
    runtime_mode: str = Field(..., min_length=1)
    backend_payload_path: str = Field(..., min_length=1)
    observability_export_path: str = Field(..., min_length=1)
    ingestion_summary_path: str = Field(..., min_length=1)
    replay_workflow_manifest_path: str = ""
    backend_status: str = Field(..., min_length=1)
    ingestion_ready: bool = False
    observability_sample_count: int = Field(default=0, ge=0)
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    execution_review_status: str = Field(default="not_evaluated", min_length=1)
    execution_review_ready: bool = False
    execution_ready_threshold_count: int = Field(default=0, ge=0)
    execution_partial_threshold_count: int = Field(default=0, ge=0)
    execution_blocked_threshold_count: int = Field(default=0, ge=0)
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_family_count: int = Field(default=0, ge=0)
    replay_workflow_manifest_status: str = Field(default="not_provided", min_length=1)


def build_local_lab_monitoring_bundle_manifest(
    *,
    backend_payload: LocalLabMonitoringBackendPayload,
    backend_payload_path: str,
    observability_export: ObservabilityExport,
    observability_export_path: str,
    ingestion_summary: LocalLabMonitoringIngestionSummary,
    ingestion_summary_path: str,
    replay_workflow_manifest_path: str = "",
    replay_workflow_manifest_status: str = "not_provided",
) -> LocalLabMonitoringBundleManifest:
    """Build a stable manifest over Local IA Lab monitoring sidecars."""

    if observability_export.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching correlation_id between backend payload and observability export"
        )
    if ingestion_summary.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching correlation_id between backend payload and ingestion summary"
        )
    if observability_export.profile.value != backend_payload.profile.value:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching profile between backend payload and observability export"
        )
    if ingestion_summary.profile.value != backend_payload.profile.value:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching profile between backend payload and ingestion summary"
        )
    if observability_export.runtime_mode.value != backend_payload.runtime_mode.value:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching runtime_mode between backend payload and observability export"
        )
    if ingestion_summary.runtime_mode.value != backend_payload.runtime_mode.value:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching runtime_mode between backend payload and ingestion summary"
        )
    if observability_export.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching timestamp_ms between backend payload and observability export"
        )
    if ingestion_summary.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring bundle manifest requires matching timestamp_ms between backend payload and ingestion summary"
        )

    return LocalLabMonitoringBundleManifest(
        timestamp_ms=backend_payload.timestamp_ms,
        correlation_id=backend_payload.correlation_id,
        profile=backend_payload.profile.value,
        runtime_mode=backend_payload.runtime_mode.value,
        backend_payload_path=backend_payload_path,
        observability_export_path=observability_export_path,
        ingestion_summary_path=ingestion_summary_path,
        replay_workflow_manifest_path=replay_workflow_manifest_path,
        backend_status=backend_payload.status,
        ingestion_ready=ingestion_summary.ingestion_ready,
        observability_sample_count=len(observability_export.samples),
        calibration_methods_review_status=backend_payload.calibration_methods_review_status,
        calibration_methods_review_ready=backend_payload.calibration_methods_review_ready,
        calibration_methods_dsr_pass=backend_payload.calibration_methods_dsr_pass,
        calibration_methods_walk_forward_plan_ready=(
            backend_payload.calibration_methods_walk_forward_plan_ready
        ),
        execution_review_status=backend_payload.execution_review_status,
        execution_review_ready=backend_payload.execution_review_ready,
        execution_ready_threshold_count=backend_payload.execution_ready_threshold_count,
        execution_partial_threshold_count=backend_payload.execution_partial_threshold_count,
        execution_blocked_threshold_count=backend_payload.execution_blocked_threshold_count,
        multiple_testing_review_status=backend_payload.multiple_testing_review_status,
        multiple_testing_review_ready=backend_payload.multiple_testing_review_ready,
        multiple_testing_correction_required=backend_payload.multiple_testing_correction_required,
        multiple_testing_family_count=backend_payload.multiple_testing_family_count,
        replay_workflow_manifest_status=replay_workflow_manifest_status,
    )


__all__ = [
    "LocalLabMonitoringBundleManifest",
    "build_local_lab_monitoring_bundle_manifest",
]
