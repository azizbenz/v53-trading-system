"""Typed contracts for shared dynamic-threshold calibration artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field, model_validator


class CalibrationSignatureMode(StrEnum):
    """Bounded signature modes accepted by the shared calibration loader."""

    HUMAN_ATTESTATION = "human_attestation"


class CalibrationManualSignature(BaseModel, frozen=True):
    """Human attestation metadata for a calibration artifact."""

    mode: CalibrationSignatureMode = CalibrationSignatureMode.HUMAN_ATTESTATION
    signed_by: str = Field(..., min_length=1)
    signed_at: datetime
    payload_hash_sha256: str = Field(default="", pattern=r"^[0-9a-f]{64}$|^$")
    note: str = ""


class CalibrationThresholdEntry(BaseModel, frozen=True):
    """Single calibrated threshold resolved by threshold_id."""

    threshold_id: str = Field(..., min_length=1)
    value: bool | int | float | str
    description: str = ""
    source_module: str = ""
    calibration_artifact: str = ""
    notes: str = ""


class CalibrationArtifact(BaseModel, frozen=True):
    """Signed calibration artifact carrying one or more threshold values."""

    schema_version: str = Field(default="calibration.v1", min_length=1)
    artifact_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    produced_by: str = Field(..., min_length=1)
    generated_at: datetime
    thresholds: tuple[CalibrationThresholdEntry, ...]
    signature: CalibrationManualSignature

    @model_validator(mode="after")
    def validate_thresholds(self) -> "CalibrationArtifact":
        if not self.thresholds:
            raise ValueError("CalibrationArtifact thresholds must not be empty")
        threshold_ids = tuple(entry.threshold_id for entry in self.thresholds)
        if len(threshold_ids) != len(set(threshold_ids)):
            raise ValueError("CalibrationArtifact threshold_ids must be unique")
        expected_hash = self.payload_hash_sha256()
        provided_hash = self.signature.payload_hash_sha256
        if provided_hash and provided_hash != expected_hash:
            raise ValueError("CalibrationArtifact signature payload_hash_sha256 mismatch")
        return self

    def canonical_payload(self) -> dict[str, object]:
        """Return the canonical unsigned payload used for hash attestation."""

        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "produced_by": self.produced_by,
            "generated_at": self.generated_at.isoformat(),
            "thresholds": [
                {
                    "threshold_id": entry.threshold_id,
                    "value": entry.value,
                    "description": entry.description,
                    "source_module": entry.source_module,
                    "calibration_artifact": entry.calibration_artifact,
                    "notes": entry.notes,
                }
                for entry in self.thresholds
            ],
        }

    def payload_hash_sha256(self) -> str:
        """Return the SHA-256 of the canonical unsigned payload."""

        payload = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class CalibrationArtifactCollection(BaseModel, frozen=True):
    """Deterministic merged view of one or more signed calibration artifacts."""

    artifacts: tuple[CalibrationArtifact, ...]

    @model_validator(mode="after")
    def validate_unique_thresholds(self) -> "CalibrationArtifactCollection":
        seen: set[str] = set()
        duplicates: set[str] = set()
        for artifact in self.artifacts:
            for entry in artifact.thresholds:
                if entry.threshold_id in seen:
                    duplicates.add(entry.threshold_id)
                seen.add(entry.threshold_id)
        if duplicates:
            duplicate_ids = ", ".join(sorted(duplicates))
            raise ValueError(
                f"CalibrationArtifactCollection duplicate threshold_ids: {duplicate_ids}"
            )
        return self

    @property
    def threshold_entries(self) -> tuple[CalibrationThresholdEntry, ...]:
        return tuple(entry for artifact in self.artifacts for entry in artifact.thresholds)
