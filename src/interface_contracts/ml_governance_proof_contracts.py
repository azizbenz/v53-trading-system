"""Typed proof-sidecar contracts for governed ML promotion and runtime rails."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .ml_model_artifact import MlModelWindow


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_datetime(value: object) -> object:
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


class MlAntiLeakageProofArtifact(BaseModel, frozen=True):
    """Machine-verifiable anti-leakage proof required before ML promotion."""

    schema_version: str = Field(default="ml_anti_leakage_proof_artifact.v1", min_length=1)
    artifact_id: str | None = None
    target_artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dataset_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    feature_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    label_policy: str | None = None
    train_window: MlModelWindow | None = None
    validation_window: MlModelWindow | None = None
    test_window: MlModelWindow | None = None
    purge_size: int | None = Field(default=None, ge=0)
    embargo_size: int | None = Field(default=None, ge=0)
    label_horizon: str | None = None
    max_feature_timestamp: datetime | None = None
    min_label_timestamp: datetime | None = None
    random_split_forbidden: bool = True
    feature_timestamp_alignment_status: str = "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
    no_future_data_leak_status: str = "NO_FUTURE_DATA_LEAK_NOT_PROVEN"
    reviewer_signature: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_artifact(self) -> "MlAntiLeakageProofArtifact":
        if not self.random_split_forbidden:
            raise ValueError("MlAntiLeakageProofArtifact requires random_split_forbidden=true")
        max_feature_timestamp = _normalize_datetime(self.max_feature_timestamp)
        min_label_timestamp = _normalize_datetime(self.min_label_timestamp)
        if (
            max_feature_timestamp is not None
            and min_label_timestamp is not None
            and max_feature_timestamp > min_label_timestamp
        ):
            raise ValueError(
                "MlAntiLeakageProofArtifact requires max_feature_timestamp <= min_label_timestamp"
            )
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("MlAntiLeakageProofArtifact artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "target_artifact_hash": self.target_artifact_hash,
            "dataset_hash": self.dataset_hash,
            "feature_hash": self.feature_hash,
            "label_policy": self.label_policy,
            "train_window": (
                None if self.train_window is None else self.train_window.model_dump(mode="json")
            ),
            "validation_window": (
                None
                if self.validation_window is None
                else self.validation_window.model_dump(mode="json")
            ),
            "test_window": (
                None if self.test_window is None else self.test_window.model_dump(mode="json")
            ),
            "purge_size": self.purge_size,
            "embargo_size": self.embargo_size,
            "label_horizon": self.label_horizon,
            "max_feature_timestamp": (
                None
                if self.max_feature_timestamp is None
                else _normalize_datetime(self.max_feature_timestamp).isoformat()
            ),
            "min_label_timestamp": (
                None
                if self.min_label_timestamp is None
                else _normalize_datetime(self.min_label_timestamp).isoformat()
            ),
            "random_split_forbidden": self.random_split_forbidden,
            "feature_timestamp_alignment_status": self.feature_timestamp_alignment_status,
            "no_future_data_leak_status": self.no_future_data_leak_status,
            "reviewer_signature": self.reviewer_signature,
            "method_version_hash": self.method_version_hash,
            "created_at": None if self.created_at is None else _normalize_datetime(self.created_at).isoformat(),
        }

    def artifact_hash_sha256(self) -> str:
        return _hash_payload(self.canonical_payload())

    @property
    def promotion_ready_proof(self) -> bool:
        return (
            self.target_artifact_hash is not None
            and self.dataset_hash is not None
            and self.feature_hash is not None
            and self.label_policy is not None
            and self.train_window is not None
            and self.validation_window is not None
            and self.test_window is not None
            and self.purge_size is not None
            and self.embargo_size is not None
            and self.label_horizon is not None
            and self.max_feature_timestamp is not None
            and self.min_label_timestamp is not None
            and self.random_split_forbidden
            and self.feature_timestamp_alignment_status == "FEATURE_TIMESTAMP_ALIGNED"
            and self.no_future_data_leak_status == "NO_FUTURE_DATA_LEAK_PROVEN"
        )

    @classmethod
    def create(cls, **payload: Any) -> "MlAntiLeakageProofArtifact":
        canonical_payload = dict(payload)
        if "train_window" in canonical_payload and isinstance(canonical_payload["train_window"], dict):
            canonical_payload["train_window"] = MlModelWindow.model_validate(
                canonical_payload["train_window"]
            )
        if "validation_window" in canonical_payload and isinstance(
            canonical_payload["validation_window"], dict
        ):
            canonical_payload["validation_window"] = MlModelWindow.model_validate(
                canonical_payload["validation_window"]
            )
        if "test_window" in canonical_payload and isinstance(canonical_payload["test_window"], dict):
            canonical_payload["test_window"] = MlModelWindow.model_validate(
                canonical_payload["test_window"]
            )
        for field_name in ("max_feature_timestamp", "min_label_timestamp", "created_at"):
            if field_name in canonical_payload:
                canonical_payload[field_name] = _parse_datetime(canonical_payload[field_name])
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


class MlLiveDriftSnapshot(BaseModel, frozen=True):
    """Governed ML drift snapshot required before ML promotion can advance."""

    schema_version: str = Field(default="ml_live_drift_snapshot.v1", min_length=1)
    artifact_id: str | None = None
    target_artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    feature_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    stage: str = "LIVE"
    feature_ks_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    live_diff_pct: float | None = Field(default=None, ge=0.0)
    win_rate_delta: float | None = None
    ce_delta: float | None = None
    source_status: str = "LIVE_DRIFT_SOURCE_NOT_PROVEN"
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_snapshot(self) -> "MlLiveDriftSnapshot":
        created_at = _normalize_datetime(self.created_at)
        expires_at = _normalize_datetime(self.expires_at)
        if created_at is not None and expires_at is not None and expires_at < created_at:
            raise ValueError("MlLiveDriftSnapshot expires_at must be >= created_at")
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("MlLiveDriftSnapshot artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "target_artifact_hash": self.target_artifact_hash,
            "feature_hash": self.feature_hash,
            "stage": self.stage,
            "feature_ks_pvalue": self.feature_ks_pvalue,
            "shadow_diff_pct": self.shadow_diff_pct,
            "live_diff_pct": self.live_diff_pct,
            "win_rate_delta": self.win_rate_delta,
            "ce_delta": self.ce_delta,
            "source_status": self.source_status,
            "input_data_hash": self.input_data_hash,
            "method_version_hash": self.method_version_hash,
            "created_at": None if self.created_at is None else _normalize_datetime(self.created_at).isoformat(),
            "expires_at": None if self.expires_at is None else _normalize_datetime(self.expires_at).isoformat(),
        }

    def artifact_hash_sha256(self) -> str:
        return _hash_payload(self.canonical_payload())

    def is_stale(self, *, as_of: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        comparison_time = _normalize_datetime(as_of) or datetime.now(tz=UTC)
        return comparison_time > _normalize_datetime(self.expires_at)

    @property
    def promotion_ready_snapshot(self) -> bool:
        return (
            self.target_artifact_hash is not None
            and self.feature_hash is not None
            and self.created_at is not None
            and self.expires_at is not None
            and self.source_status == "LIVE_DRIFT_SOURCE_GOVERNED"
        )

    @classmethod
    def create(cls, **payload: Any) -> "MlLiveDriftSnapshot":
        canonical_payload = dict(payload)
        for field_name in ("created_at", "expires_at"):
            if field_name in canonical_payload:
                canonical_payload[field_name] = _parse_datetime(canonical_payload[field_name])
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


class MlSupplementaryRefsSourceSummary(BaseModel, frozen=True):
    """Governed source-summary sidecar for runtime ML supplementary refs."""

    schema_version: str = Field(default="ml_supplementary_refs_source_summary.v1", min_length=1)
    artifact_id: str | None = None
    target_artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    feature_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dataset_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    transport_artifact_ref: str = Field(..., min_length=1)
    summary_ref: str = Field(..., min_length=1)
    supplementary_refs_count: int = Field(default=0, ge=0)
    source_component: str = Field(default="ML_RUNTIME_ARTIFACT_HANDOFF_NOT_PROVEN", min_length=1)
    source_stage: str = Field(default="LOCAL_REPLAY", min_length=1)
    source_status: str = "SUPPLEMENTARY_REFS_SOURCE_NOT_PROVEN"
    non_empty_refs_status: str = "SUPPLEMENTARY_REFS_NOT_PROVEN"
    generated_at: datetime
    source_stale_after: datetime
    method_version_hash: str | None = None
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_summary(self) -> "MlSupplementaryRefsSourceSummary":
        generated_at = _normalize_datetime(self.generated_at)
        source_stale_after = _normalize_datetime(self.source_stale_after)
        if source_stale_after < generated_at:
            raise ValueError(
                "MlSupplementaryRefsSourceSummary source_stale_after must be >= generated_at"
            )
        if self.supplementary_refs_count < 2:
            raise ValueError(
                "MlSupplementaryRefsSourceSummary requires supplementary_refs_count >= 2"
            )
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("MlSupplementaryRefsSourceSummary artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "target_artifact_hash": self.target_artifact_hash,
            "feature_hash": self.feature_hash,
            "dataset_hash": self.dataset_hash,
            "transport_artifact_ref": self.transport_artifact_ref,
            "summary_ref": self.summary_ref,
            "supplementary_refs_count": self.supplementary_refs_count,
            "source_component": self.source_component,
            "source_stage": self.source_stage,
            "source_status": self.source_status,
            "non_empty_refs_status": self.non_empty_refs_status,
            "generated_at": _normalize_datetime(self.generated_at).isoformat(),
            "source_stale_after": _normalize_datetime(self.source_stale_after).isoformat(),
            "method_version_hash": self.method_version_hash,
        }

    def artifact_hash_sha256(self) -> str:
        return _hash_payload(self.canonical_payload())

    def is_stale(self, *, as_of: datetime | None = None) -> bool:
        comparison_time = _normalize_datetime(as_of) or datetime.now(tz=UTC)
        return comparison_time > _normalize_datetime(self.source_stale_after)

    @property
    def runtime_active_ready(self) -> bool:
        return (
            self.target_artifact_hash is not None
            and self.feature_hash is not None
            and self.dataset_hash is not None
            and self.source_status == "SUPPLEMENTARY_REFS_SOURCE_GOVERNED"
            and self.non_empty_refs_status == "NON_EMPTY_SUPPLEMENTARY_REFS_PROVEN"
        )

    @classmethod
    def create(cls, **payload: Any) -> "MlSupplementaryRefsSourceSummary":
        canonical_payload = dict(payload)
        for field_name in ("generated_at", "source_stale_after"):
            if field_name in canonical_payload:
                canonical_payload[field_name] = _parse_datetime(canonical_payload[field_name])
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


__all__ = [
    "MlAntiLeakageProofArtifact",
    "MlLiveDriftSnapshot",
    "MlSupplementaryRefsSourceSummary",
]
