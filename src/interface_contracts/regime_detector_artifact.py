"""Typed artifact contract for VPS-shadow RegimeDetectorML."""

from __future__ import annotations

import base64
import hashlib
import json
import math
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from interface_contracts.domain_types import PromotionState


class RegimeDetectorModelFamily(StrEnum):
    """Bounded model-family vocabulary for the Regime Detector artifact."""

    LIGHTGBM = "lightgbm"


class RegimeDetectorFeatureSetVersion(StrEnum):
    """Explicit feature-schema versions for governed regime-detector artifacts."""

    LOB_REGIME_FEATURE_SET_V1 = "lob_regime_feature_set.v1"
    LOB_REGIME_FEATURE_SET_V2 = "lob_regime_feature_set.v2"


class RegimeDetectorOutputSemantics(StrEnum):
    """Stable output semantics for governed runtime consumers."""

    LOB_REGIME_DETECTOR_V1 = "lob_regime_detector.v1"


class RegimeDurationBucket(StrEnum):
    """Bucketed duration output; exact minute prediction is intentionally avoided."""

    FRAGILE = "fragile"
    SHORT = "short"
    MEDIUM = "medium"
    PERSISTENT = "persistent"


class RegimeDetectorWindow(BaseModel):
    """Train/validation window carried by the Regime Detector artifact."""

    start_at: datetime
    end_at: datetime

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_window(self) -> "RegimeDetectorWindow":
        if self.end_at < self.start_at:
            raise ValueError("RegimeDetectorWindow end_at must be >= start_at")
        return self


class RegimeDetectorArtifact(BaseModel):
    """Hash-validated LightGBM artifact for VPS shadow-only regime inference."""

    schema_version: str = Field(default="regime_detector_artifact.v1", min_length=1)
    model_family: RegimeDetectorModelFamily = RegimeDetectorModelFamily.LIGHTGBM
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    feature_names: tuple[str, ...]
    feature_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    pair_universe: tuple[str, ...]
    train_window: RegimeDetectorWindow
    validation_window: RegimeDetectorWindow
    output_semantics: RegimeDetectorOutputSemantics = (
        RegimeDetectorOutputSemantics.LOB_REGIME_DETECTOR_V1
    )
    regime_labels: tuple[str, ...]
    duration_bucket_scheme: tuple[RegimeDurationBucket, ...] = (
        RegimeDurationBucket.FRAGILE,
        RegimeDurationBucket.SHORT,
        RegimeDurationBucket.MEDIUM,
        RegimeDurationBucket.PERSISTENT,
    )
    oos_metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    shadow_metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    training_seed: int
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    calibration_version: str = Field(..., min_length=1)
    dataset_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    model_bytes_b64: str | None = None
    model_path_ref: str | None = None
    stale_after: datetime | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("feature_names", "pair_universe", "regime_labels")
    @classmethod
    def _validate_non_empty_unique_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if not normalized:
            raise ValueError("RegimeDetectorArtifact tuple fields must not be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("RegimeDetectorArtifact tuple fields must be unique")
        return normalized

    @field_validator("oos_metrics", "shadow_metrics")
    @classmethod
    def _validate_metric_payload(
        cls,
        value: dict[str, float | int | str | bool],
    ) -> dict[str, float | int | str | bool]:
        for key, item in value.items():
            if not key.strip():
                raise ValueError("RegimeDetectorArtifact metric names must not be blank")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("RegimeDetectorArtifact metrics must be finite")
        return dict(value)

    @field_validator("model_bytes_b64")
    @classmethod
    def _validate_model_bytes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        base64.b64decode(value.encode("ascii"), validate=True)
        return value

    @model_validator(mode="after")
    def validate_payload(self) -> "RegimeDetectorArtifact":
        if self.model_bytes_b64 is None and self.model_path_ref is None:
            raise ValueError("RegimeDetectorArtifact requires model_bytes_b64 or model_path_ref")
        if self.stale_after is not None and self.stale_after < self.created_at:
            raise ValueError("RegimeDetectorArtifact stale_after must be >= created_at")
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("RegimeDetectorArtifact artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:  # noqa: Any
        """Return the canonical payload used to compute artifact_hash."""

        return {
            "schema_version": self.schema_version,
            "model_family": self.model_family.value,
            "feature_set_version": self.feature_set_version.value,
            "feature_names": list(self.feature_names),
            "feature_hash": self.feature_hash,
            "pair_universe": list(self.pair_universe),
            "train_window": self.train_window.model_dump(mode="json"),
            "validation_window": self.validation_window.model_dump(mode="json"),
            "output_semantics": self.output_semantics.value,
            "regime_labels": list(self.regime_labels),
            "duration_bucket_scheme": [bucket.value for bucket in self.duration_bucket_scheme],
            "oos_metrics": self.oos_metrics,
            "shadow_metrics": self.shadow_metrics,
            "promotion_state": self.promotion_state.value,
            "training_seed": self.training_seed,
            "created_at": self.created_at.isoformat(),
            "calibration_version": self.calibration_version,
            "dataset_hash": self.dataset_hash,
            "model_bytes_b64": self.model_bytes_b64,
            "model_path_ref": self.model_path_ref,
            "stale_after": None if self.stale_after is None else self.stale_after.isoformat(),
        }

    def artifact_hash_sha256(self) -> str:
        """Return the canonical SHA-256 of the artifact payload."""

        payload = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def create(cls, **payload: Any) -> "RegimeDetectorArtifact":  # noqa: Any
        """Build a validated artifact with a computed artifact_hash."""

        canonical_payload = dict(payload)
        if "model_family" in canonical_payload and isinstance(canonical_payload["model_family"], str):
            canonical_payload["model_family"] = RegimeDetectorModelFamily(
                canonical_payload["model_family"]
            )
        if "feature_set_version" in canonical_payload and isinstance(
            canonical_payload["feature_set_version"],
            str,
        ):
            canonical_payload["feature_set_version"] = RegimeDetectorFeatureSetVersion(
                canonical_payload["feature_set_version"]
            )
        if "output_semantics" in canonical_payload and isinstance(
            canonical_payload["output_semantics"],
            str,
        ):
            canonical_payload["output_semantics"] = RegimeDetectorOutputSemantics(
                canonical_payload["output_semantics"]
            )
        if "promotion_state" in canonical_payload and isinstance(
            canonical_payload["promotion_state"],
            str,
        ):
            canonical_payload["promotion_state"] = PromotionState(
                canonical_payload["promotion_state"]
            )
        for window_key in ("train_window", "validation_window"):
            if window_key in canonical_payload and isinstance(canonical_payload[window_key], dict):
                canonical_payload[window_key] = RegimeDetectorWindow.model_validate(
                    canonical_payload[window_key]
                )
        if "duration_bucket_scheme" in canonical_payload:
            canonical_payload["duration_bucket_scheme"] = tuple(
                item if isinstance(item, RegimeDurationBucket) else RegimeDurationBucket(item)
                for item in canonical_payload["duration_bucket_scheme"]
            )
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


class RegimeDetectorArtifactSummary(BaseModel):
    """Stable sidecar summary for transported Regime Detector artifacts."""

    artifact_hash: str = Field(..., min_length=64, max_length=64)
    schema_version: str = Field(..., min_length=1)
    model_family: str = Field(..., min_length=1)
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    output_semantics: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    dataset_hash: str = Field(..., min_length=64, max_length=64)
    promotion_state: PromotionState
    pair_universe: tuple[str, ...]
    train_window_start_at: str = Field(..., min_length=1)
    train_window_end_at: str = Field(..., min_length=1)
    validation_window_start_at: str = Field(..., min_length=1)
    validation_window_end_at: str = Field(..., min_length=1)
    source_artifact_ref: str = Field(..., min_length=1)
    transport_artifact_ref: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")


__all__ = [
    "RegimeDetectorModelFamily",
    "RegimeDetectorFeatureSetVersion",
    "RegimeDetectorOutputSemantics",
    "RegimeDurationBucket",
    "RegimeDetectorWindow",
    "RegimeDetectorArtifact",
    "RegimeDetectorArtifactSummary",
]
