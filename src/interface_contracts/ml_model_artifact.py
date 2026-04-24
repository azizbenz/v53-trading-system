"""Typed contract for Local-Lab-trained ML model artifacts."""

from __future__ import annotations

import base64
import hashlib
import json
import math
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from interface_contracts.domain_types import PromotionState


class MlModelFamily(StrEnum):
    """Bounded family vocabulary for governed ML artifacts."""

    LIGHTGBM = "lightgbm"


class MlModelWindow(BaseModel, frozen=True):
    """Bounded train/validation window carried by the ML artifact."""

    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "MlModelWindow":
        if self.end_at < self.start_at:
            raise ValueError("MlModelWindow end_at must be >= start_at")
        return self


class MlModelDriftBaseline(BaseModel, frozen=True):
    """Optional Local-Lab baseline used by downstream drift monitoring."""

    forecast_mean: float | None = None
    win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    ce_mean: float | None = None
    feature_ks_reference_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    sample_count: int = Field(default=0, ge=0)

    @field_validator("forecast_mean", "ce_mean")
    @classmethod
    def _validate_finite_metrics(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("MlModelDriftBaseline metrics must be finite")
        return value


class MlModelArtifact(BaseModel, frozen=True):
    """Signed-by-hash LightGBM artifact consumed by bounded runtime enablers."""

    schema_version: str = Field(default="ml_model_artifact.v1", min_length=1)
    model_family: MlModelFamily = MlModelFamily.LIGHTGBM
    feature_names: tuple[str, ...]
    feature_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    pair_universe: tuple[str, ...]
    train_window: MlModelWindow
    validation_window: MlModelWindow
    oos_sharpe: float
    backtest_sharpe: float
    ks_test_features_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    training_seed: int
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    calibration_version: str = Field(..., min_length=1)
    dataset_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    model_bytes_b64: str | None = None
    model_path_ref: str | None = None
    shap_summary_ref: str | None = None
    training_metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)
    drift_baseline: MlModelDriftBaseline | None = None
    stale_after: datetime | None = None

    @field_validator("feature_names", "pair_universe")
    @classmethod
    def _validate_non_empty_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        if not normalized:
            raise ValueError("MlModelArtifact tuple fields must not be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("MlModelArtifact tuple fields must be unique")
        return normalized

    @field_validator("oos_sharpe", "backtest_sharpe", "shadow_diff_pct")
    @classmethod
    def _validate_finite_metrics(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("MlModelArtifact metrics must be finite")
        return value

    @field_validator("model_bytes_b64")
    @classmethod
    def _validate_model_bytes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        base64.b64decode(value.encode("ascii"), validate=True)
        return value

    @model_validator(mode="after")
    def validate_payload(self) -> "MlModelArtifact":
        if self.model_bytes_b64 is None and self.model_path_ref is None:
            raise ValueError("MlModelArtifact requires model_bytes_b64 or model_path_ref")
        if self.stale_after is not None and self.stale_after < self.created_at:
            raise ValueError("MlModelArtifact stale_after must be >= created_at")
        if self.artifact_hash != self.artifact_hash_sha256():
            raise ValueError("MlModelArtifact artifact_hash mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:  # noqa: Any
        """Return the canonical payload used to compute artifact_hash."""

        return {
            "schema_version": self.schema_version,
            "model_family": self.model_family.value,
            "feature_names": list(self.feature_names),
            "feature_hash": self.feature_hash,
            "pair_universe": list(self.pair_universe),
            "train_window": self.train_window.model_dump(mode="json"),
            "validation_window": self.validation_window.model_dump(mode="json"),
            "oos_sharpe": self.oos_sharpe,
            "backtest_sharpe": self.backtest_sharpe,
            "ks_test_features_pvalue": self.ks_test_features_pvalue,
            "shadow_diff_pct": self.shadow_diff_pct,
            "promotion_state": self.promotion_state.value,
            "training_seed": self.training_seed,
            "created_at": self.created_at.isoformat(),
            "calibration_version": self.calibration_version,
            "dataset_hash": self.dataset_hash,
            "model_bytes_b64": self.model_bytes_b64,
            "model_path_ref": self.model_path_ref,
            "shap_summary_ref": self.shap_summary_ref,
            "training_metrics": self.training_metrics,
            "drift_baseline": (
                None if self.drift_baseline is None else self.drift_baseline.model_dump(mode="json")
            ),
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
    def create(cls, **payload: Any) -> "MlModelArtifact":  # noqa: Any
        """Build a validated artifact with a computed artifact_hash."""

        canonical_payload = dict(payload)
        if "model_family" in canonical_payload and isinstance(canonical_payload["model_family"], str):
            canonical_payload["model_family"] = MlModelFamily(canonical_payload["model_family"])
        if "promotion_state" in canonical_payload and isinstance(canonical_payload["promotion_state"], str):
            canonical_payload["promotion_state"] = PromotionState(canonical_payload["promotion_state"])
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
        if "drift_baseline" in canonical_payload and isinstance(canonical_payload["drift_baseline"], dict):
            canonical_payload["drift_baseline"] = MlModelDriftBaseline.model_validate(
                canonical_payload["drift_baseline"]
            )
        canonical_payload["artifact_hash"] = "0" * 64
        provisional = cls.model_construct(**canonical_payload)
        canonical_payload["artifact_hash"] = provisional.artifact_hash_sha256()
        return cls.model_validate(canonical_payload)


__all__ = [
    "MlModelFamily",
    "MlModelWindow",
    "MlModelDriftBaseline",
    "MlModelArtifact",
]
