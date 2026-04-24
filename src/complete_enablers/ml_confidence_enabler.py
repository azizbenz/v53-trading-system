"""Bounded runtime-facing ML confidence enabler for additive score modulation."""

from __future__ import annotations

import base64
import importlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from complete_enablers.ml_fusion import MlFusionResult, apply_ml_score_fusion
from complete_enablers.ml_runtime_artifact_loader import (
    MlRuntimeArtifactLoadStatus,
    load_ml_runtime_artifact,
)
from interface_contracts import MlModelArtifact, Side


class MlDirection(StrEnum):
    """Research/debug-only ML direction hint."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class MlArtifactStatus(StrEnum):
    """Operational status of the bounded ML artifact at scoring time."""

    ACTIVE = "active"
    MISSING = "missing"
    STALE = "stale"
    INVALID = "invalid"


class MlConfidenceSignal(BaseModel, frozen=True):
    """Bounded ML confidence signal used for additive score fusion only."""

    ml_confidence: float = Field(..., ge=0.0, le=1.0)
    ml_direction: MlDirection = MlDirection.FLAT
    artifact_status: MlArtifactStatus
    artifact_id: str | None = None
    reason_codes: tuple[str, ...] = ()


class MlScoreApplication(BaseModel, frozen=True):
    """Final additive ML score application result."""

    engine_side: Side
    signal: MlConfidenceSignal
    fusion: MlFusionResult

    @property
    def fused_score(self) -> float:
        return self.fusion.fused_score


def _load_lightgbm_module() -> Any:  # noqa: Any
    try:
        return importlib.import_module("lightgbm")
    except ImportError:
        return None


def _decode_model_string(artifact: MlModelArtifact) -> str | None:
    if artifact.model_bytes_b64 is None:
        return None
    return base64.b64decode(artifact.model_bytes_b64.encode("ascii")).decode("utf-8")


def _normalize_side(engine_side: Side | str) -> Side:
    return engine_side if isinstance(engine_side, Side) else Side(engine_side)


def _is_stale(artifact: MlModelArtifact, as_of: datetime | None) -> bool:
    if artifact.stale_after is None:
        return False
    comparison_time = as_of or datetime.now(tz=UTC)
    if comparison_time.tzinfo is None:
        comparison_time = comparison_time.replace(tzinfo=UTC)
    return comparison_time > artifact.stale_after


def _feature_vector(feature_values: dict[str, float], artifact: MlModelArtifact) -> list[float]:
    try:
        return [float(feature_values[name]) for name in artifact.feature_names]
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise ValueError(f"missing feature {missing}") from exc


def _predict_probability(artifact: MlModelArtifact, feature_values: dict[str, float]) -> float:
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
    probability = float(booster.predict([_feature_vector(feature_values, artifact)])[0])
    if probability >= 0.55:
        return min(1.0, max(0.0, probability))
    return min(1.0, max(0.0, probability))


def _direction_from_confidence(ml_confidence: float) -> MlDirection:
    if ml_confidence > 0.55:
        return MlDirection.LONG
    if ml_confidence < 0.45:
        return MlDirection.SHORT
    return MlDirection.FLAT


class MlConfidenceEnabler:
    """Bounded ML confidence layer that never overrides engine side."""

    def __init__(self, *, default_alpha: float = 0.2) -> None:
        self._default_alpha = default_alpha

    def score_candidate(
        self,
        *,
        feature_values: dict[str, float],
        artifact: MlModelArtifact | None,
        as_of: datetime | None = None,
    ) -> MlConfidenceSignal:
        """Score a candidate with the governed ML artifact or fail open to neutral."""

        if artifact is None:
            return MlConfidenceSignal(
                ml_confidence=0.5,
                ml_direction=MlDirection.FLAT,
                artifact_status=MlArtifactStatus.MISSING,
                reason_codes=("ML_ARTIFACT_MISSING",),
            )
        if _is_stale(artifact, as_of):
            return MlConfidenceSignal(
                ml_confidence=0.5,
                ml_direction=MlDirection.FLAT,
                artifact_status=MlArtifactStatus.STALE,
                artifact_id=artifact.artifact_hash,
                reason_codes=("ML_ARTIFACT_STALE",),
            )
        try:
            probability = _predict_probability(artifact, feature_values)
        except Exception as exc:
            return MlConfidenceSignal(
                ml_confidence=0.5,
                ml_direction=MlDirection.FLAT,
                artifact_status=MlArtifactStatus.INVALID,
                artifact_id=artifact.artifact_hash,
                reason_codes=(f"ML_ARTIFACT_INVALID:{type(exc).__name__}",),
            )
        clipped_probability = min(1.0, max(0.0, probability))
        return MlConfidenceSignal(
            ml_confidence=clipped_probability,
            ml_direction=_direction_from_confidence(clipped_probability),
            artifact_status=MlArtifactStatus.ACTIVE,
            artifact_id=artifact.artifact_hash,
            reason_codes=("ML_ARTIFACT_ACTIVE",),
        )

    def score_candidate_from_supplementary_refs(
        self,
        *,
        feature_values: dict[str, float],
        supplementary_refs: tuple[str, ...],
        as_of: datetime | None = None,
    ) -> MlConfidenceSignal:
        """Load a transported ML artifact from supplementary refs or degrade to neutral."""

        selection = load_ml_runtime_artifact(
            supplementary_refs,
            as_of=as_of,
        )
        if selection.status == MlRuntimeArtifactLoadStatus.LOADED and selection.artifact is not None:
            return self.score_candidate(
                feature_values=feature_values,
                artifact=selection.artifact,
                as_of=as_of,
            )
        if selection.status == MlRuntimeArtifactLoadStatus.STALE:
            artifact_id = None
            if selection.artifact is not None:
                artifact_id = selection.artifact.artifact_hash
            elif selection.summary is not None:
                artifact_id = selection.summary.artifact_hash
            return MlConfidenceSignal(
                ml_confidence=0.5,
                ml_direction=MlDirection.FLAT,
                artifact_status=MlArtifactStatus.STALE,
                artifact_id=artifact_id,
                reason_codes=selection.reasons,
            )

        artifact_status = (
            MlArtifactStatus.MISSING
            if selection.status
            in (
                MlRuntimeArtifactLoadStatus.MISSING_SUPPLEMENTARY_REFS,
                MlRuntimeArtifactLoadStatus.SUMMARY_NOT_FOUND,
                MlRuntimeArtifactLoadStatus.TRANSPORT_ARTIFACT_NOT_DECLARED,
            )
            else MlArtifactStatus.INVALID
        )
        artifact_id = None if selection.summary is None else selection.summary.artifact_hash
        return MlConfidenceSignal(
            ml_confidence=0.5,
            ml_direction=MlDirection.FLAT,
            artifact_status=artifact_status,
            artifact_id=artifact_id,
            reason_codes=selection.reasons,
        )

    def apply_to_engine_score(
        self,
        *,
        base_score: float,
        engine_side: Side | str,
        artifact: MlModelArtifact | None = None,
        feature_values: dict[str, float] | None = None,
        ml_confidence: float | None = None,
        alpha: float | None = None,
        as_of: datetime | None = None,
    ) -> MlScoreApplication:
        """Apply bounded ML fusion without mutating the canonical engine side."""

        if ml_confidence is None:
            signal = self.score_candidate(
                feature_values={} if feature_values is None else feature_values,
                artifact=artifact,
                as_of=as_of,
            )
        else:
            clipped_confidence = min(1.0, max(0.0, float(ml_confidence)))
            signal = MlConfidenceSignal(
                ml_confidence=clipped_confidence,
                ml_direction=_direction_from_confidence(clipped_confidence),
                artifact_status=MlArtifactStatus.ACTIVE if artifact is not None else MlArtifactStatus.MISSING,
                artifact_id=None if artifact is None else artifact.artifact_hash,
                reason_codes=(
                    ("ML_CONFIDENCE_PROVIDED",)
                    if artifact is not None
                    else ("ML_CONFIDENCE_PROVIDED_WITHOUT_ARTIFACT",)
                ),
            )
        fusion = apply_ml_score_fusion(
            base_score=base_score,
            ml_confidence=signal.ml_confidence,
            alpha=self._default_alpha if alpha is None else alpha,
            artifact_ready=signal.artifact_status == MlArtifactStatus.ACTIVE,
        )
        return MlScoreApplication(
            engine_side=_normalize_side(engine_side),
            signal=signal,
            fusion=fusion,
        )


__all__ = [
    "MlDirection",
    "MlArtifactStatus",
    "MlConfidenceSignal",
    "MlScoreApplication",
    "MlConfidenceEnabler",
]
