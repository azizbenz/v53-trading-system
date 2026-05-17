"""Artifact-only VPS Shadow runtime for RegimeDetectorML."""

from __future__ import annotations

import base64
import importlib
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from complete_enablers.regime_detector_runtime_loader import (
    RegimeDetectorArtifactLoadStatus,
    load_regime_detector_runtime_artifact,
)
from complete_enablers.supplementary_refs_governance import (
    validate_regime_detector_supplementary_refs,
)
from data_backbone.microstructure import LobRegimeFeatureSnapshot
from interface_contracts import RegimeDetectorArtifact, RegimeDurationBucket

RUNTIME_REGIME_OUTPUTS = (
    "regime_transition_risk",
    "regime_stability_score",
    "market_toxicity_score",
    "expected_duration_bucket",
)
DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN = (
    "direction_up_300s_fee_safe",
    "buy_probability",
    "sell_probability",
    "market_will_go_up",
    "side",
    "long",
    "short",
    "target_return",
    "future_return",
    "label",
    "direct_trade_decision",
)
RUNTIME_REGIME_OUTPUT_MODE = "NON_DIRECTIONAL_ONLY"


class RegimeDetectorSignalStatus(StrEnum):
    """Runtime signal state; V1 is observational and shadow-only."""

    ACTIVE = "active"
    NEUTRAL = "neutral"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALID_ARTIFACT = "invalid_artifact"
    PAIR_NOT_SUPPORTED = "pair_not_supported"
    FEATURE_SCHEMA_MISMATCH = "feature_schema_mismatch"


class RegimeDetectorSignal(BaseModel, frozen=True):
    """Shadow-only regime context emitted by the VPS RegimeDetector runtime."""

    status: RegimeDetectorSignalStatus
    pair: str = Field(..., min_length=1)
    computed_at_ns: int = Field(..., ge=1)
    artifact_hash: str | None = None
    feature_hash: str | None = None
    regime_transition_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    regime_stability_score: float = Field(default=1.0, ge=0.0, le=1.0)
    market_toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_duration_bucket: RegimeDurationBucket = RegimeDurationBucket.PERSISTENT
    reason_codes: tuple[str, ...] = ()

    @property
    def shadow_only(self) -> bool:
        return True


def _load_lightgbm_module() -> Any:  # noqa: Any
    try:
        return importlib.import_module("lightgbm")
    except ImportError:
        return None


def _decode_model_string(artifact: RegimeDetectorArtifact) -> str | None:
    if artifact.model_bytes_b64 is None:
        return None
    return base64.b64decode(artifact.model_bytes_b64.encode("ascii")).decode("utf-8")


def _clip(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _feature_vector(
    features: LobRegimeFeatureSnapshot,
    artifact: RegimeDetectorArtifact,
) -> list[float]:
    feature_map = features.as_feature_map_for_version(artifact.feature_set_version)
    try:
        return [float(feature_map[name]) for name in artifact.feature_names]
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"missing feature {missing}") from exc


def _duration_from_score(score: float) -> RegimeDurationBucket:
    normalized = _clip(score)
    if normalized < 0.25:
        return RegimeDurationBucket.FRAGILE
    if normalized < 0.50:
        return RegimeDurationBucket.SHORT
    if normalized < 0.75:
        return RegimeDurationBucket.MEDIUM
    return RegimeDurationBucket.PERSISTENT


def _duration_from_index(index: float) -> RegimeDurationBucket:
    buckets = (
        RegimeDurationBucket.FRAGILE,
        RegimeDurationBucket.SHORT,
        RegimeDurationBucket.MEDIUM,
        RegimeDurationBucket.PERSISTENT,
    )
    resolved = int(round(index))
    return buckets[min(max(resolved, 0), len(buckets) - 1)]


def _normalize_prediction(raw_prediction: object) -> tuple[float, float, float, RegimeDurationBucket]:
    if isinstance(raw_prediction, dict):
        transition = _clip(float(raw_prediction.get("regime_transition_risk", 0.0)))
        stability = _clip(float(raw_prediction.get("regime_stability_score", 1.0 - transition)))
        toxicity = _clip(float(raw_prediction.get("market_toxicity_score", transition)))
        bucket_raw = raw_prediction.get("expected_duration_bucket", RegimeDurationBucket.PERSISTENT.value)
        bucket = RegimeDurationBucket(str(bucket_raw))
        return transition, stability, toxicity, bucket

    if isinstance(raw_prediction, (list, tuple)):
        values = [float(item) for item in raw_prediction]
    else:
        values = [float(raw_prediction)]

    transition = _clip(values[0])
    stability = _clip(values[1]) if len(values) > 1 else _clip(1.0 - transition)
    toxicity = _clip(values[2]) if len(values) > 2 else transition
    if len(values) > 3:
        duration_value = values[3]
        bucket = (
            _duration_from_index(duration_value)
            if duration_value > 1.0
            else _duration_from_score(duration_value)
        )
    else:
        bucket = _duration_from_score(stability)
    return transition, stability, toxicity, bucket


def _predict_regime_signal(
    artifact: RegimeDetectorArtifact,
    features: LobRegimeFeatureSnapshot,
) -> tuple[float, float, float, RegimeDurationBucket]:
    lightgbm = _load_lightgbm_module()
    if lightgbm is None:
        raise ValueError("lightgbm_unavailable")
    model_string = _decode_model_string(artifact)
    if model_string is None and artifact.model_path_ref is None:
        raise ValueError("model_payload_missing")
    booster_kwargs: dict[str, Any] = {}
    if model_string is not None:
        booster_kwargs["model_str"] = model_string
    elif artifact.model_path_ref is not None:
        booster_kwargs["model_file"] = artifact.model_path_ref
    booster = lightgbm.Booster(**booster_kwargs)
    prediction = booster.predict([_feature_vector(features, artifact)])[0]
    return _normalize_prediction(prediction)


def _neutral_signal(
    *,
    status: RegimeDetectorSignalStatus,
    features: LobRegimeFeatureSnapshot,
    artifact: RegimeDetectorArtifact | None = None,
    reason_codes: tuple[str, ...],
) -> RegimeDetectorSignal:
    return RegimeDetectorSignal(
        status=status,
        pair=features.pair,
        computed_at_ns=features.computed_at_ns,
        artifact_hash=None if artifact is None else artifact.artifact_hash,
        feature_hash=None if artifact is None else artifact.feature_hash,
        reason_codes=reason_codes,
    )


class RegimeDetectorRuntime:
    """VPS runtime inference for RegimeDetectorML; no training and no live influence."""

    def evaluate(
        self,
        *,
        features: LobRegimeFeatureSnapshot,
        artifact: RegimeDetectorArtifact | None,
    ) -> RegimeDetectorSignal:
        if features.data_status != "ready" or features.insufficient_data:
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.INSUFFICIENT_DATA,
                features=features,
                artifact=artifact,
                reason_codes=features.reason_codes or ("REGIME_DETECTOR_FEATURES_INSUFFICIENT",),
            )
        if artifact is None:
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.NEUTRAL,
                features=features,
                reason_codes=("REGIME_DETECTOR_ARTIFACT_MISSING",),
            )
        if features.pair not in artifact.pair_universe:
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.PAIR_NOT_SUPPORTED,
                features=features,
                artifact=artifact,
                reason_codes=("REGIME_DETECTOR_PAIR_NOT_SUPPORTED",),
            )
        try:
            transition, stability, toxicity, bucket = _predict_regime_signal(artifact, features)
        except ValueError as exc:
            if str(exc).startswith("missing feature") or "unsupported lob regime feature_set_version" in str(exc):
                return _neutral_signal(
                    status=RegimeDetectorSignalStatus.FEATURE_SCHEMA_MISMATCH,
                    features=features,
                    artifact=artifact,
                    reason_codes=("REGIME_DETECTOR_FEATURE_SCHEMA_MISMATCH",),
                )
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.INVALID_ARTIFACT,
                features=features,
                artifact=artifact,
                reason_codes=(f"REGIME_DETECTOR_INVALID_ARTIFACT:{type(exc).__name__}",),
            )
        except Exception as exc:
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.INVALID_ARTIFACT,
                features=features,
                artifact=artifact,
                reason_codes=(f"REGIME_DETECTOR_INVALID_ARTIFACT:{type(exc).__name__}",),
            )

        return RegimeDetectorSignal(
            status=RegimeDetectorSignalStatus.ACTIVE,
            pair=features.pair,
            computed_at_ns=features.computed_at_ns,
            artifact_hash=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            regime_transition_risk=transition,
            regime_stability_score=stability,
            market_toxicity_score=toxicity,
            expected_duration_bucket=bucket,
            reason_codes=("REGIME_DETECTOR_SHADOW_SIGNAL_ACTIVE",),
        )

    def evaluate_from_supplementary_refs(
        self,
        *,
        features: LobRegimeFeatureSnapshot,
        supplementary_refs: tuple[str, ...],
    ) -> RegimeDetectorSignal:
        governance = validate_regime_detector_supplementary_refs(supplementary_refs)
        if governance.rejected:
            return _neutral_signal(
                status=RegimeDetectorSignalStatus.INVALID_ARTIFACT,
                features=features,
                reason_codes=governance.reason_codes,
            )
        selection = load_regime_detector_runtime_artifact(governance.accepted_refs)
        if selection.status == RegimeDetectorArtifactLoadStatus.LOADED and selection.artifact is not None:
            return self.evaluate(features=features, artifact=selection.artifact)
        artifact = selection.artifact
        status = (
            RegimeDetectorSignalStatus.NEUTRAL
            if selection.status
            in (
                RegimeDetectorArtifactLoadStatus.MISSING_SUPPLEMENTARY_REFS,
                RegimeDetectorArtifactLoadStatus.SUMMARY_NOT_FOUND,
            )
            else RegimeDetectorSignalStatus.INVALID_ARTIFACT
        )
        return _neutral_signal(
            status=status,
            features=features,
            artifact=artifact,
            reason_codes=selection.reasons,
        )


__all__ = [
    "DIRECTIONAL_RUNTIME_KEYS_FORBIDDEN",
    "RegimeDetectorSignalStatus",
    "RegimeDetectorSignal",
    "RegimeDetectorRuntime",
    "RUNTIME_REGIME_OUTPUT_MODE",
    "RUNTIME_REGIME_OUTPUTS",
]
