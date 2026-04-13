"""Typed Local IA Lab dry-run bridge contracts."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LocalLabSourceArtifactSummary(BaseModel, frozen=True):
    """Future-facing summary of the Local IA Lab artifact that feeds the dry-run bridge."""

    artifact_id: str = Field(..., min_length=1)
    artifact_family: str = Field(..., min_length=1)
    schema_version: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    produced_by: str = Field(..., min_length=1)
    source_artifact_path: str = Field(..., min_length=1)
    threshold_ids: tuple[str, ...] = ()
    threshold_count: int = Field(default=0, ge=0)


class LocalLabReleaseGateSummary(BaseModel, frozen=True):
    """Stable sidecar projection of the Local IA Lab packaging gate verdict."""

    correlation_id: str = Field(..., min_length=1)
    release_candidate_artifact_id: str = Field(..., min_length=1)
    release_ready_for_shadow: bool = False
    release_artifact_proof_ready: bool = False
    release_artifact_proof_validation_reasons: tuple[str, ...] = ()
    release_calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    release_calibration_methods_review_ready: bool = False
    release_calibration_methods_dsr_pass: bool | None = None
    release_calibration_methods_walk_forward_plan_ready: bool = False
    release_calibration_methods_review_ref: str | None = None
    release_recalibration_candidate_ready: bool = False
    release_recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_status: str = Field(default="not_evaluated", min_length=1)
    release_gate_reasons: tuple[str, ...] = ()


class LocalLabArtifactUploadDryRunBridge(BaseModel, frozen=True):
    """Audit-ready dry-run bridge status for future `Local IA Lab -> VPS` handoff."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    release_candidate_artifact_id: str = Field(..., min_length=1)
    source_artifact_id: str | None = None
    source_artifact_family: str | None = None
    source_artifact_schema_version: str | None = None
    source_artifact_version: str | None = None
    governed_artifact_id: str | None = None
    transport_artifact_id: str | None = None
    source_artifact_path: str = Field(..., min_length=1)
    source_artifact_summary_ref: str | None = None
    release_gate_summary_ref: str | None = None
    artifact_kind: str | None = None
    transport_artifact_kind: str | None = None
    artifact_class: str | None = None
    artifact_scope: str | None = None
    uploaded_by: str = Field(..., min_length=1)
    governance_reference_date: date | None = None
    training_end: date | None = None
    lifecycle_ttl_days: int | None = Field(default=None, ge=1)
    rule_half_life_days: int | None = Field(default=None, ge=1)
    drift_score_threshold: float | None = Field(default=None, ge=0.0)
    target_runtime_mode: str = "shadow"
    transport_payload_ref_count: int = Field(default=0, ge=0)
    transport_supplementary_refs: tuple[str, ...] = ()
    upload_request_path: str | None = None
    import_request_path: str | None = None
    import_decision_path: str | None = None
    upload_decision_path: str | None = None
    bridge_status: str = Field(..., min_length=1)
    ready_for_shadow_import_dry_run: bool = False
    release_ready_for_shadow: bool = False
    release_artifact_proof_ready: bool = False
    release_artifact_proof_validation_reasons: tuple[str, ...] = ()
    release_calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    release_calibration_methods_review_ready: bool = False
    release_calibration_methods_dsr_pass: bool | None = None
    release_calibration_methods_walk_forward_plan_ready: bool = False
    release_calibration_methods_review_ref: str | None = None
    release_recalibration_candidate_ready: bool = False
    release_recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_status: str = Field(default="not_evaluated", min_length=1)
    release_gate_reasons: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    import_decision_reasons: tuple[str, ...] = ()
    upload_decision_status: str | None = None
    semantic_status: str = Field(default="not_evaluated", min_length=1)
    semantic_reasons: tuple[str, ...] = ()


__all__ = [
    "LocalLabReleaseGateSummary",
    "LocalLabSourceArtifactSummary",
    "LocalLabArtifactUploadDryRunBridge",
]
