"""Typed dashboard-to-VPS governed command contracts for Build-17 control."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
import re

from pydantic import BaseModel, Field, model_validator

from .domain_types import RuntimeMode, TimestampedModel


class DashboardArtifactKind(StrEnum):
    """Artifact families handled by the governed dashboard command plane."""

    ML_MODEL_ARTIFACT = "ml_model_artifact"
    REGIME_DETECTOR_ARTIFACT = "regime_detector_artifact"
    REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE = "regime_detector_shadow_audit_bundle"
    GENERIC_EXPORT_BUNDLE = "generic_export_bundle"


class DashboardSecretKind(StrEnum):
    """Secret bundle families handled by the governed command plane."""

    BINANCE_SPOT_CREDENTIALS = "binance_spot_credentials"


class DashboardSecretEnvironment(StrEnum):
    """Venue credential environment carried without secret material."""

    TESTNET = "testnet"
    LIVE = "live"


class BinanceCredentialValidationStatus(StrEnum):
    """Non-sensitive credential validation status vocabulary."""

    UNKNOWN = "unknown"
    PENDING = "pending"
    VALIDATED = "validated"
    FAILED = "failed"
    STALE = "stale"
    DEACTIVATED = "deactivated"


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
    REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE = (
        "request_upload_binance_credentials_bundle"
    )
    REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE = (
        "request_activate_binance_credentials_profile"
    )
    REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY = (
        "request_export_binance_credential_inventory"
    )
    REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE = (
        "request_deactivate_binance_credentials_profile"
    )


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
_SECRET_UPLOAD_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
    }
)
_SECRET_PROFILE_COMMANDS = frozenset(
    {
        DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        DashboardGovernedCommandKind.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
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
        DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
        DashboardGovernedCommandKind.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        DashboardGovernedCommandKind.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
    }
)

_SECRET_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PLAINTEXT_SECRET_SUFFIXES = (".env", ".yaml", ".yml")


def validate_dashboard_secret_reference(*, secret_hash: str, sealed_ref: str) -> None:
    """Validate the governed secret hash and sealed bundle reference format."""

    if not _SECRET_HASH_RE.fullmatch(secret_hash):
        raise ValueError(
            "Dashboard secret_hash must be a lowercase 64-character sha256 hex digest"
        )
    if not sealed_ref or sealed_ref.strip() != sealed_ref:
        raise ValueError("Dashboard sealed_ref must not be empty or padded")
    if any(char.isspace() for char in sealed_ref):
        raise ValueError("Dashboard sealed_ref must not contain whitespace")
    lowered = sealed_ref.lower()
    if lowered.endswith(_FORBIDDEN_PLAINTEXT_SECRET_SUFFIXES):
        raise ValueError("Dashboard sealed_ref must not reference plaintext secret files")
    if lowered.startswith("sealed://"):
        tail = sealed_ref[len("sealed://") :]
        if not tail:
            raise ValueError("Dashboard sealed_ref sealed:// URI must not be empty")
        parts = tail.split("/")
        if any(not part or part in {".", ".."} for part in parts):
            raise ValueError(
                "Dashboard sealed_ref sealed:// URI must not contain empty or traversal segments"
            )
        return
    if "\\" in sealed_ref or ":" in sealed_ref or sealed_ref.startswith("/"):
        raise ValueError("Dashboard sealed_ref must be a relative sealed bundle path")
    candidate = PurePosixPath(sealed_ref)
    if candidate.suffixes[-2:] != [".sealed", ".json"]:
        raise ValueError("Dashboard sealed_ref must reference a .sealed.json bundle")
    if any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError(
            "Dashboard sealed_ref must not contain empty or traversal path segments"
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


class DashboardSecretTransferManifest(BaseModel, frozen=True):
    """Metadata-only descriptor for a sealed credential bundle.

    The dashboard queue never carries API keys or decrypted credential payloads.
    It only carries hashes, profile ids, lineage, and a sealed bundle reference.
    """

    secret_hash: str = Field(..., min_length=1)
    secret_kind: DashboardSecretKind
    profile_id: str = Field(..., min_length=1)
    venue: str = Field(default="binance_spot", min_length=1)
    environment: DashboardSecretEnvironment
    sealed_ref: str = Field(..., min_length=1)
    sealed_schema_version: str = Field(
        default="binance_credentials_bundle.v1",
        min_length=1,
    )
    backend: str = ""
    lineage_version: str = ""
    review_state: str = ""
    validation_status: str = ""
    source_ref: str = ""
    payload_refs: tuple[str, ...] = ()
    created_at_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_secret_manifest(self) -> "DashboardSecretTransferManifest":
        if len(set(self.payload_refs)) != len(self.payload_refs):
            raise ValueError("DashboardSecretTransferManifest payload_refs must be unique")
        validate_dashboard_secret_reference(
            secret_hash=self.secret_hash,
            sealed_ref=self.sealed_ref,
        )
        return self


class BinanceCredentialProfileRef(BaseModel, frozen=True):
    """Metadata-only reference to a governed Binance credential profile."""

    profile_id: str = Field(..., min_length=1)
    venue: str = Field(default="binance_spot", min_length=1)
    environment: DashboardSecretEnvironment
    secret_kind: DashboardSecretKind = DashboardSecretKind.BINANCE_SPOT_CREDENTIALS
    secret_hash: str = Field(..., min_length=1)
    sealed_ref: str = Field(..., min_length=1)
    backend: str = ""

    @model_validator(mode="after")
    def validate_reference(self) -> "BinanceCredentialProfileRef":
        validate_dashboard_secret_reference(
            secret_hash=self.secret_hash,
            sealed_ref=self.sealed_ref,
        )
        return self


class BinanceCredentialInventoryEntry(BaseModel, frozen=True):
    """Safe inventory row for one sealed Binance credential profile."""

    profile: BinanceCredentialProfileRef
    active: bool = False
    review_state: str = ""
    validation_status: BinanceCredentialValidationStatus = (
        BinanceCredentialValidationStatus.UNKNOWN
    )
    last_auth_check_ms: int = Field(default=0, ge=0)
    last_failure_reason_codes: tuple[str, ...] = ()
    source_ref: str = ""
    lineage_version: str = ""
    created_at_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_reason_codes(self) -> "BinanceCredentialInventoryEntry":
        if len(set(self.last_failure_reason_codes)) != len(
            self.last_failure_reason_codes
        ):
            raise ValueError(
                "BinanceCredentialInventoryEntry reason codes must be unique"
            )
        return self


class BinanceCredentialInventorySnapshot(BaseModel, frozen=True):
    """Metadata-only export surface for Binance credential inventory."""

    active_profile_id: str = ""
    entries: tuple[BinanceCredentialInventoryEntry, ...] = ()
    exported_at_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_inventory(self) -> "BinanceCredentialInventorySnapshot":
        profile_ids = tuple(entry.profile.profile_id for entry in self.entries)
        if len(set(profile_ids)) != len(profile_ids):
            raise ValueError("Binance credential inventory profile ids must be unique")
        active_count = sum(1 for entry in self.entries if entry.active)
        if active_count > 1:
            raise ValueError("Only one Binance credential inventory entry may be active")
        if self.active_profile_id and self.active_profile_id not in set(profile_ids):
            raise ValueError("active_profile_id must exist in Binance credential inventory")
        return self


def binance_credential_entry_from_manifest(
    manifest: DashboardSecretTransferManifest,
    *,
    active: bool = False,
    validation_status: BinanceCredentialValidationStatus = (
        BinanceCredentialValidationStatus.PENDING
    ),
) -> BinanceCredentialInventoryEntry:
    """Convert a sealed credential manifest into safe inventory metadata."""

    return BinanceCredentialInventoryEntry(
        profile=BinanceCredentialProfileRef(
            profile_id=manifest.profile_id,
            venue=manifest.venue,
            environment=manifest.environment,
            secret_kind=manifest.secret_kind,
            secret_hash=manifest.secret_hash,
            sealed_ref=manifest.sealed_ref,
            backend=manifest.backend,
        ),
        active=active,
        review_state=manifest.review_state,
        validation_status=validation_status,
        source_ref=manifest.source_ref,
        lineage_version=manifest.lineage_version,
        created_at_ms=manifest.created_at_ms,
    )


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
    target_secret_profile: str = ""
    artifact_manifest: DashboardArtifactTransferManifest | None = None
    secret_manifest: DashboardSecretTransferManifest | None = None
    command_version: str = Field(default="dashboard_governed_command.v1", min_length=1)

    @property
    def idempotency_key(self) -> str:
        if self.artifact_manifest is not None:
            payload_hash = self.artifact_manifest.artifact_hash
        elif self.secret_manifest is not None:
            payload_hash = self.secret_manifest.secret_hash
        elif self.target_secret_profile:
            payload_hash = self.target_secret_profile
        else:
            payload_hash = "no_artifact"
        return f"{self.request_id}:{payload_hash}:{self.command_kind.value}"

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
        if self.command_kind in _SECRET_UPLOAD_COMMANDS and self.secret_manifest is None:
            raise ValueError(
                f"{self.command_kind.value} requires a secret_manifest"
            )
        if self.command_kind not in _SECRET_UPLOAD_COMMANDS and self.secret_manifest is not None:
            raise ValueError(
                f"{self.command_kind.value} must not declare a secret_manifest"
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
        if (
            self.command_kind
            == DashboardGovernedCommandKind.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE
        ):
            if self.secret_manifest is None:
                raise ValueError(
                    "request_upload_binance_credentials_bundle requires secret_manifest"
                )
            if (
                self.secret_manifest.secret_kind
                != DashboardSecretKind.BINANCE_SPOT_CREDENTIALS
            ):
                raise ValueError(
                    "request_upload_binance_credentials_bundle requires secret_kind=binance_spot_credentials"
                )
            if (
                self.target_secret_profile
                and self.target_secret_profile != self.secret_manifest.profile_id
            ):
                raise ValueError(
                    "target_secret_profile must match secret_manifest.profile_id"
                )
        if self.command_kind in _SECRET_PROFILE_COMMANDS and not self.target_secret_profile:
            raise ValueError(f"{self.command_kind.value} requires target_secret_profile")
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
    secret_manifest: DashboardSecretTransferManifest | None = None
    credential_inventory: BinanceCredentialInventorySnapshot | None = None
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
    "DashboardSecretKind",
    "DashboardSecretEnvironment",
    "BinanceCredentialValidationStatus",
    "DashboardGovernedCommandKind",
    "DashboardGovernedCommandStatus",
    "DashboardCommandQueueStatus",
    "validate_dashboard_secret_reference",
    "DashboardArtifactTransferManifest",
    "DashboardSecretTransferManifest",
    "BinanceCredentialProfileRef",
    "BinanceCredentialInventoryEntry",
    "BinanceCredentialInventorySnapshot",
    "binance_credential_entry_from_manifest",
    "DashboardGovernedCommandRequest",
    "DashboardGovernedCommandAck",
    "DashboardGovernedCommandResult",
    "DashboardCommandQueueSnapshot",
]
