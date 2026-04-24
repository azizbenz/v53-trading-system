"""Typed dashboard-to-VPS governed command contracts for Build-17 control."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .domain_types import RuntimeMode, TimestampedModel


class DashboardArtifactKind(StrEnum):
    """Artifact families handled by the governed dashboard command plane."""

    ML_MODEL_ARTIFACT = "ml_model_artifact"
    REGIME_DETECTOR_ARTIFACT = "regime_detector_artifact"
    REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE = "regime_detector_shadow_audit_bundle"
    GENERIC_EXPORT_BUNDLE = "generic_export_bundle"


class DashboardGovernedCommandKind(StrEnum):
    """Minimal governed actions exposed by the Build-17 Complete surface."""

    REQUEST_UPLOAD_ML_ARTIFACT = "request_upload_ml_artifact"
    REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT = "request_upload_regime_detector_artifact"
    REQUEST_EXPORT_ACTIVE_ML_ARTIFACT = "request_export_active_ml_artifact"
    REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT = (
        "request_export_active_regime_detector_artifact"
    )
    REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE = (
        "request_export_regime_detector_shadow_audit_bundle"
    )
    SET_HALTED = "set_halted"
    ROLLBACK_TO_LIGHT = "rollback_to_light"
    SUSPEND_PAIR = "suspend_pair"
    REQUEST_PAIR_RESUME = "request_pair_resume"
    SUSPEND_ENGINE = "suspend_engine"
    REQUEST_ENGINE_RESUME = "request_engine_resume"


class DashboardGovernedCommandStatus(StrEnum):
    """Stable lifecycle vocabulary for governed dashboard queue actions."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class DashboardCommandQueueStatus(StrEnum):
    """Health summary for the watched dashboard request/response queue."""

    HEALTHY = "healthy"
    WARNING = "warning"
    BLOCKED = "blocked"


_UPLOAD_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT,
        DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
    }
)
_PAIR_TARGET_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.SUSPEND_PAIR,
        DashboardGovernedCommandKind.REQUEST_PAIR_RESUME,
    }
)
_ENGINE_TARGET_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.SUSPEND_ENGINE,
        DashboardGovernedCommandKind.REQUEST_ENGINE_RESUME,
    }
)
_REASON_REQUIRED_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.SET_HALTED,
        DashboardGovernedCommandKind.ROLLBACK_TO_LIGHT,
        DashboardGovernedCommandKind.SUSPEND_PAIR,
        DashboardGovernedCommandKind.REQUEST_PAIR_RESUME,
        DashboardGovernedCommandKind.SUSPEND_ENGINE,
        DashboardGovernedCommandKind.REQUEST_ENGINE_RESUME,
    }
)


class DashboardArtifactTransferManifest(BaseModel, frozen=True):
    """Typed artifact descriptor carried by upload/export queue messages."""

    artifact_hash: str = Field(..., min_length=1)
    artifact_kind: DashboardArtifactKind
    artifact_id: str = ""
    feature_set_version: str = ""
    feature_profile: str = ""
    lineage_version: str = ""
    review_state: str = ""
    validation_status: str = ""
    source_ref: str = ""
    payload_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_payload_refs(self) -> "DashboardArtifactTransferManifest":
        if len(set(self.payload_refs)) != len(self.payload_refs):
            raise ValueError("DashboardArtifactTransferManifest payload_refs must be unique")
        return self


class DashboardGovernedCommandRequest(TimestampedModel):
    """One typed file-queue request emitted by Local or dashboard control."""

    correlation_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    command_kind: DashboardGovernedCommandKind
    source_runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    target_runtime_mode: RuntimeMode = RuntimeMode.LIVE
    requested_by: str = Field(default="operator", min_length=1)
    operator_reason: str = ""
    target_pair: str = ""
    target_engine: str = ""
    artifact_manifest: DashboardArtifactTransferManifest | None = None
    command_version: str = Field(default="dashboard_governed_command.v1", min_length=1)

    @property
    def idempotency_key(self) -> str:
        artifact_hash = (
            self.artifact_manifest.artifact_hash
            if self.artifact_manifest is not None
            else "no_artifact"
        )
        return f"{self.request_id}:{artifact_hash}:{self.command_kind.value}"

    @model_validator(mode="after")
    def validate_request(self) -> "DashboardGovernedCommandRequest":
        if self.target_runtime_mode == RuntimeMode.LOCAL_REPLAY:
            raise ValueError(
                "DashboardGovernedCommandRequest must target a VPS-side runtime_mode"
            )
        if self.command_kind in _UPLOAD_COMMANDS and self.artifact_manifest is None:
            raise ValueError(
                f"{self.command_kind.value} requires an artifact_manifest"
            )
        if self.command_kind not in _UPLOAD_COMMANDS and self.artifact_manifest is not None:
            if self.command_kind not in {
                DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
                DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
            }:
                raise ValueError(
                    f"{self.command_kind.value} must not declare an artifact_manifest"
                )
        if self.command_kind == DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT:
            if self.artifact_manifest is None:
                raise ValueError("request_upload_ml_artifact requires artifact_manifest")
            if self.artifact_manifest.artifact_kind != DashboardArtifactKind.ML_MODEL_ARTIFACT:
                raise ValueError(
                    "request_upload_ml_artifact requires artifact_kind=ml_model_artifact"
                )
        if (
            self.command_kind
            == DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT
        ):
            if self.artifact_manifest is None:
                raise ValueError(
                    "request_upload_regime_detector_artifact requires artifact_manifest"
                )
            if (
                self.artifact_manifest.artifact_kind
                != DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT
            ):
                raise ValueError(
                    "request_upload_regime_detector_artifact requires artifact_kind=regime_detector_artifact"
                )
        if self.command_kind in _PAIR_TARGET_COMMANDS and not self.target_pair:
            raise ValueError(f"{self.command_kind.value} requires target_pair")
        if self.command_kind in _ENGINE_TARGET_COMMANDS and not self.target_engine:
            raise ValueError(f"{self.command_kind.value} requires target_engine")
        if self.command_kind in _REASON_REQUIRED_COMMANDS and not self.operator_reason.strip():
            raise ValueError(f"{self.command_kind.value} requires operator_reason")
        return self


class DashboardGovernedCommandAck(TimestampedModel, frozen=True):
    """Typed acknowledgement emitted when the VPS queue consumes one request."""

    correlation_id: str = Field(..., min_length=1)
    ack_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    command_kind: DashboardGovernedCommandKind
    status: DashboardGovernedCommandStatus
    idempotency_key: str = Field(..., min_length=1)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""

    @model_validator(mode="after")
    def validate_status(self) -> "DashboardGovernedCommandAck":
        if self.status not in {
            DashboardGovernedCommandStatus.ACCEPTED,
            DashboardGovernedCommandStatus.REJECTED,
        }:
            raise ValueError("DashboardGovernedCommandAck status must be accepted or rejected")
        return self


class DashboardGovernedCommandResult(TimestampedModel, frozen=True):
    """Typed final outcome emitted by the governed dashboard command plane."""

    correlation_id: str = Field(..., min_length=1)
    result_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    command_kind: DashboardGovernedCommandKind
    status: DashboardGovernedCommandStatus
    idempotency_key: str = Field(..., min_length=1)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    artifact_manifest: DashboardArtifactTransferManifest | None = None
    export_ref: str = ""
    failure_stage: str = ""

    @model_validator(mode="after")
    def validate_outcome(self) -> "DashboardGovernedCommandResult":
        if self.status in {
            DashboardGovernedCommandStatus.REJECTED,
            DashboardGovernedCommandStatus.FAILED,
        } and not self.reason_codes:
            raise ValueError("Rejected or failed command results must carry reason_codes")
        return self


class DashboardCommandQueueSnapshot(BaseModel, frozen=True):
    """Bounded status summary of the watched dashboard file queue."""

    queue_dir_ref: str = Field(..., min_length=1)
    request_dir_ref: str = Field(..., min_length=1)
    ack_dir_ref: str = Field(..., min_length=1)
    result_dir_ref: str = Field(..., min_length=1)
    queue_status: DashboardCommandQueueStatus = DashboardCommandQueueStatus.WARNING
    pending_request_count: int = Field(default=0, ge=0)
    accepted_ack_count: int = Field(default=0, ge=0)
    rejected_ack_count: int = Field(default=0, ge=0)
    completed_result_count: int = Field(default=0, ge=0)
    failed_result_count: int = Field(default=0, ge=0)
    ambiguous_pending_count: int = Field(default=0, ge=0)
    writable: bool = False
    drainable: bool = False
    healthy: bool = False
    last_request_id: str = ""
    last_result_status: str = ""
    last_result_ref: str = ""
    blocking_reasons: tuple[str, ...] = ()


__all__ = [
    "DashboardArtifactKind",
    "DashboardGovernedCommandKind",
    "DashboardGovernedCommandStatus",
    "DashboardCommandQueueStatus",
    "DashboardArtifactTransferManifest",
    "DashboardGovernedCommandRequest",
    "DashboardGovernedCommandAck",
    "DashboardGovernedCommandResult",
    "DashboardCommandQueueSnapshot",
]
