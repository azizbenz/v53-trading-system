"""Typed Local-IA-Lab label and dataset contracts for RegimeDetectorML."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .regime_detector_artifact import RegimeDetectorFeatureSetVersion, RegimeDurationBucket


REGIME_DETECTOR_LABEL_POLICY = "lob_future_regime_state.v1"
DEFAULT_REGIME_DETECTOR_WINDOW_SECONDS = 5.0
MAX_REGIME_DETECTOR_WINDOW_SECONDS = 30.0
DEFAULT_REGIME_DETECTOR_FUTURE_STEPS = 4
DEFAULT_REGIME_DETECTOR_TOP_N = 5
MAX_REGIME_DETECTOR_TOP_N = 10


class RegimeToxicityBucket(StrEnum):
    """Bucketed future microstructure toxicity used by RegimeDetector labels."""

    NOMINAL = "nominal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class RegimeDetectorLabelConfig(BaseModel):
    """Deterministic label-generation knobs for Local-Lab regime datasets."""

    current_window_seconds: float = Field(
        default=DEFAULT_REGIME_DETECTOR_WINDOW_SECONDS,
        gt=0.0,
        le=MAX_REGIME_DETECTOR_WINDOW_SECONDS,
    )
    future_window_seconds: float = Field(
        default=DEFAULT_REGIME_DETECTOR_WINDOW_SECONDS,
        gt=0.0,
        le=MAX_REGIME_DETECTOR_WINDOW_SECONDS,
    )
    max_future_steps: int = Field(default=DEFAULT_REGIME_DETECTOR_FUTURE_STEPS, ge=1, le=4)
    top_n_levels: int = Field(default=DEFAULT_REGIME_DETECTOR_TOP_N, ge=1, le=MAX_REGIME_DETECTOR_TOP_N)
    touch_eps_bps: float = Field(default=2.0, gt=0.0, le=25.0)
    toxicity_elevated_floor: float = Field(default=0.35, ge=0.0, le=1.0)
    toxicity_critical_floor: float = Field(default=0.65, ge=0.0, le=1.0)
    liquidity_elevated_floor: float = Field(default=0.25, ge=0.0, le=1.0)
    liquidity_critical_floor: float = Field(default=0.50, ge=0.0, le=1.0)
    spoof_elevated_floor: float = Field(default=0.45, ge=0.0, le=1.0)
    spoof_critical_floor: float = Field(default=0.70, ge=0.0, le=1.0)
    imbalance_flip_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    microprice_flip_threshold_bps: float = Field(default=0.50, ge=0.0, le=25.0)
    toxicity_delta_threshold: float = Field(default=0.25, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_threshold_ordering(self) -> "RegimeDetectorLabelConfig":
        if self.toxicity_critical_floor <= self.toxicity_elevated_floor:
            raise ValueError("toxicity_critical_floor must be > toxicity_elevated_floor")
        if self.liquidity_critical_floor <= self.liquidity_elevated_floor:
            raise ValueError("liquidity_critical_floor must be > liquidity_elevated_floor")
        if self.spoof_critical_floor <= self.spoof_elevated_floor:
            raise ValueError("spoof_critical_floor must be > spoof_elevated_floor")
        return self

    def canonical_payload(self) -> dict[str, float | int]:
        """Return the canonical payload used to hash label-generation settings."""

        return {
            "current_window_seconds": self.current_window_seconds,
            "future_window_seconds": self.future_window_seconds,
            "max_future_steps": self.max_future_steps,
            "top_n_levels": self.top_n_levels,
            "touch_eps_bps": self.touch_eps_bps,
            "toxicity_elevated_floor": self.toxicity_elevated_floor,
            "toxicity_critical_floor": self.toxicity_critical_floor,
            "liquidity_elevated_floor": self.liquidity_elevated_floor,
            "liquidity_critical_floor": self.liquidity_critical_floor,
            "spoof_elevated_floor": self.spoof_elevated_floor,
            "spoof_critical_floor": self.spoof_critical_floor,
            "imbalance_flip_threshold": self.imbalance_flip_threshold,
            "microprice_flip_threshold_bps": self.microprice_flip_threshold_bps,
            "toxicity_delta_threshold": self.toxicity_delta_threshold,
        }

    def config_hash(self) -> str:
        payload = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(payload).hexdigest()


class RegimeDetectorDatasetSample(BaseModel):
    """One Local-Lab regime-training sample built from raw historical LOB events."""

    pair: str = Field(..., min_length=1)
    anchor_timestamp_ns: int = Field(..., ge=1)
    feature_values: dict[str, float]
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    label_policy: str = Field(default=REGIME_DETECTOR_LABEL_POLICY, min_length=1)
    transition_next_window: int = Field(..., ge=0, le=1)
    duration_bucket: RegimeDurationBucket
    toxicity_bucket: RegimeToxicityBucket
    future_steps_observed: int = Field(..., ge=1)
    input_data_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    feature_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    label_config_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    reason_codes: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("feature_values")
    @classmethod
    def _validate_feature_values(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("RegimeDetectorDatasetSample feature_values must not be empty")
        normalized: dict[str, float] = {}
        for key, item in value.items():
            if not key.strip():
                raise ValueError("RegimeDetectorDatasetSample feature names must not be blank")
            if not math.isfinite(item):
                raise ValueError("RegimeDetectorDatasetSample feature values must be finite")
            normalized[key] = float(item)
        return normalized

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.feature_values))


class RegimeDetectorTrainingDataset(BaseModel):
    """Dataset-level audit wrapper for Local-Lab regime-training samples."""

    dataset_id: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    label_policy: str = Field(default=REGIME_DETECTOR_LABEL_POLICY, min_length=1)
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    label_config_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    samples: tuple[RegimeDetectorDatasetSample, ...] = Field(..., min_length=1)
    pair_scope: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_feature_schema(self) -> "RegimeDetectorTrainingDataset":
        expected = self.feature_names or self.samples[0].feature_names
        for sample in self.samples:
            if sample.feature_names != expected:
                raise ValueError("RegimeDetectorTrainingDataset feature schema must stay stable")
            if sample.feature_set_version != self.feature_set_version:
                raise ValueError(
                    "RegimeDetectorTrainingDataset feature_set_version must stay stable"
                )
            if sample.label_config_hash != self.label_config_hash:
                raise ValueError("RegimeDetectorTrainingDataset label_config_hash drift detected")
        return self


__all__ = [
    "REGIME_DETECTOR_LABEL_POLICY",
    "DEFAULT_REGIME_DETECTOR_WINDOW_SECONDS",
    "MAX_REGIME_DETECTOR_WINDOW_SECONDS",
    "DEFAULT_REGIME_DETECTOR_FUTURE_STEPS",
    "DEFAULT_REGIME_DETECTOR_TOP_N",
    "MAX_REGIME_DETECTOR_TOP_N",
    "RegimeDetectorFeatureSetVersion",
    "RegimeToxicityBucket",
    "RegimeDetectorLabelConfig",
    "RegimeDetectorDatasetSample",
    "RegimeDetectorTrainingDataset",
]
