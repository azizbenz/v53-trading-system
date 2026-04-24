"""Artifact-only runtime loader for transported RegimeDetectorML artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorArtifactSummary,
)

_SUMMARY_FILENAME = "regime_detector_artifact.summary.json"


class RegimeDetectorArtifactLoadStatus(StrEnum):
    """Fail-closed load statuses for transported RegimeDetector artifacts."""

    MISSING_SUPPLEMENTARY_REFS = "missing_supplementary_refs"
    SUMMARY_NOT_FOUND = "summary_not_found"
    SUMMARY_INVALID = "summary_invalid"
    TRANSPORT_ARTIFACT_NOT_DECLARED = "transport_artifact_not_declared"
    TRANSPORT_ARTIFACT_UNREADABLE = "transport_artifact_unreadable"
    TRANSPORT_ARTIFACT_INVALID = "transport_artifact_invalid"
    HASH_MISMATCH = "hash_mismatch"
    FEATURE_SET_VERSION_MISMATCH = "feature_set_version_mismatch"
    FEATURE_HASH_MISMATCH = "feature_hash_mismatch"
    STALE = "stale"
    SHADOW_EVIDENCE_MISSING = "shadow_evidence_missing"
    LOADED = "loaded"


class RegimeDetectorArtifactSelection(BaseModel, frozen=True):
    """Typed result of selecting and validating a runtime RegimeDetector artifact."""

    status: RegimeDetectorArtifactLoadStatus
    artifact: RegimeDetectorArtifact | None = None
    summary: RegimeDetectorArtifactSummary | None = None
    summary_ref: str | None = None
    transport_artifact_ref: str | None = None
    reasons: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def artifact_ready(self) -> bool:
        return self.status == RegimeDetectorArtifactLoadStatus.LOADED and self.artifact is not None


def _normalize_as_of(as_of: datetime | None) -> datetime:
    if as_of is None:
        return datetime.now(tz=UTC)
    return as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=UTC)


def _read_summary(summary_ref: str) -> RegimeDetectorArtifactSummary:
    try:
        payload = Path(summary_ref).resolve().read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"summary_unreadable:{summary_ref}") from exc
    try:
        return RegimeDetectorArtifactSummary.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"summary_invalid:{summary_ref}") from exc


def _read_artifact(artifact_ref: str) -> RegimeDetectorArtifact:
    try:
        payload = Path(artifact_ref).resolve().read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"artifact_unreadable:{artifact_ref}") from exc
    try:
        return RegimeDetectorArtifact.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"artifact_invalid:{artifact_ref}") from exc


def _find_summary_ref(supplementary_refs: tuple[str, ...]) -> str | None:
    for ref in supplementary_refs:
        if Path(ref).name == _SUMMARY_FILENAME:
            return ref
    return None


def load_regime_detector_runtime_artifact(
    supplementary_refs: tuple[str, ...],
    *,
    as_of: datetime | None = None,
) -> RegimeDetectorArtifactSelection:
    """Load a governed RegimeDetector artifact from supplementary refs only."""

    if not supplementary_refs:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.MISSING_SUPPLEMENTARY_REFS,
            reasons=("REGIME_DETECTOR_ARTIFACT_MISSING_SUPPLEMENTARY_REFS",),
        )

    summary_ref = _find_summary_ref(supplementary_refs)
    if summary_ref is None:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.SUMMARY_NOT_FOUND,
            reasons=("REGIME_DETECTOR_ARTIFACT_SUMMARY_NOT_FOUND",),
        )

    try:
        summary = _read_summary(summary_ref)
    except ValueError:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.SUMMARY_INVALID,
            summary_ref=summary_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_SUMMARY_INVALID",),
        )

    transport_artifact_ref = summary.transport_artifact_ref
    if transport_artifact_ref not in supplementary_refs:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.TRANSPORT_ARTIFACT_NOT_DECLARED,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_TRANSPORT_NOT_DECLARED",),
        )

    try:
        artifact = _read_artifact(transport_artifact_ref)
    except OSError:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.TRANSPORT_ARTIFACT_UNREADABLE,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_UNREADABLE",),
        )
    except ValueError:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.TRANSPORT_ARTIFACT_INVALID,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_INVALID",),
        )

    if artifact.artifact_hash != summary.artifact_hash:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.HASH_MISMATCH,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_HASH_MISMATCH",),
        )

    if artifact.feature_set_version != summary.feature_set_version:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.FEATURE_SET_VERSION_MISMATCH,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_FEATURE_SET_VERSION_MISMATCH",),
        )

    if artifact.feature_hash != summary.feature_hash:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.FEATURE_HASH_MISMATCH,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_FEATURE_HASH_MISMATCH",),
        )

    if artifact.stale_after is not None and _normalize_as_of(as_of) > artifact.stale_after:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.STALE,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_STALE",),
        )

    if artifact.promotion_state in {
        PromotionState.MICRO_LIVE_CANDIDATE,
        PromotionState.LIVE_CANDIDATE,
    } and not artifact.shadow_metrics:
        return RegimeDetectorArtifactSelection(
            status=RegimeDetectorArtifactLoadStatus.SHADOW_EVIDENCE_MISSING,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("REGIME_DETECTOR_ARTIFACT_SHADOW_EVIDENCE_MISSING",),
        )

    return RegimeDetectorArtifactSelection(
        status=RegimeDetectorArtifactLoadStatus.LOADED,
        artifact=artifact,
        summary=summary,
        summary_ref=summary_ref,
        transport_artifact_ref=transport_artifact_ref,
        reasons=("REGIME_DETECTOR_ARTIFACT_LOADED",),
    )


__all__ = [
    "RegimeDetectorArtifactLoadStatus",
    "RegimeDetectorArtifactSelection",
    "load_regime_detector_runtime_artifact",
]
