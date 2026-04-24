"""Artifact-only runtime loader for governed ML supplementary refs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import MlModelArtifact, MlModelSourceArtifactSummary

_SUMMARY_FILENAME = "ml_model_artifact.summary.json"


class MlRuntimeArtifactLoadStatus(StrEnum):
    """Fail-closed runtime load statuses for transported ML artifacts."""

    MISSING_SUPPLEMENTARY_REFS = "missing_supplementary_refs"
    SUMMARY_NOT_FOUND = "summary_not_found"
    SUMMARY_INVALID = "summary_invalid"
    TRANSPORT_ARTIFACT_NOT_DECLARED = "transport_artifact_not_declared"
    TRANSPORT_ARTIFACT_UNREADABLE = "transport_artifact_unreadable"
    TRANSPORT_ARTIFACT_INVALID = "transport_artifact_invalid"
    HASH_MISMATCH = "hash_mismatch"
    STALE = "stale"
    LOADED = "loaded"


class MlRuntimeArtifactSelection(BaseModel, frozen=True):
    """Typed result of selecting and validating a runtime ML artifact."""

    status: MlRuntimeArtifactLoadStatus
    artifact: MlModelArtifact | None = None
    summary: MlModelSourceArtifactSummary | None = None
    summary_ref: str | None = None
    transport_artifact_ref: str | None = None
    reasons: tuple[str, ...] = Field(default_factory=tuple)

    @property
    def artifact_ready(self) -> bool:
        return self.status == MlRuntimeArtifactLoadStatus.LOADED and self.artifact is not None


def _normalize_as_of(as_of: datetime | None) -> datetime:
    if as_of is None:
        return datetime.now(tz=UTC)
    return as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=UTC)


def _read_summary(summary_ref: str) -> MlModelSourceArtifactSummary:
    try:
        payload = Path(summary_ref).resolve().read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"summary_unreadable:{summary_ref}") from exc
    try:
        return MlModelSourceArtifactSummary.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"summary_invalid:{summary_ref}") from exc


def _read_artifact(artifact_ref: str) -> MlModelArtifact:
    try:
        payload = Path(artifact_ref).resolve().read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"artifact_unreadable:{artifact_ref}") from exc
    try:
        return MlModelArtifact.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"artifact_invalid:{artifact_ref}") from exc


def _find_summary_ref(supplementary_refs: tuple[str, ...]) -> str | None:
    for ref in supplementary_refs:
        if Path(ref).name == _SUMMARY_FILENAME:
            return ref
    return None


def load_ml_runtime_artifact(
    supplementary_refs: tuple[str, ...],
    *,
    as_of: datetime | None = None,
) -> MlRuntimeArtifactSelection:
    """Load a governed runtime ML artifact from supplementary refs only."""

    if not supplementary_refs:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.MISSING_SUPPLEMENTARY_REFS,
            reasons=("ML_RUNTIME_ARTIFACT_MISSING_SUPPLEMENTARY_REFS",),
        )

    summary_ref = _find_summary_ref(supplementary_refs)
    if summary_ref is None:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.SUMMARY_NOT_FOUND,
            reasons=("ML_RUNTIME_ARTIFACT_SUMMARY_NOT_FOUND",),
        )

    try:
        summary = _read_summary(summary_ref)
    except ValueError:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.SUMMARY_INVALID,
            summary_ref=summary_ref,
            reasons=("ML_RUNTIME_ARTIFACT_SUMMARY_INVALID",),
        )

    transport_artifact_ref = summary.transport_artifact_ref
    if transport_artifact_ref not in supplementary_refs:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.TRANSPORT_ARTIFACT_NOT_DECLARED,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("ML_RUNTIME_ARTIFACT_TRANSPORT_NOT_DECLARED",),
        )

    try:
        artifact = _read_artifact(transport_artifact_ref)
    except OSError:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.TRANSPORT_ARTIFACT_UNREADABLE,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("ML_RUNTIME_ARTIFACT_UNREADABLE",),
        )
    except ValueError:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.TRANSPORT_ARTIFACT_INVALID,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("ML_RUNTIME_ARTIFACT_INVALID",),
        )

    if artifact.artifact_hash != summary.artifact_hash:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.HASH_MISMATCH,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("ML_RUNTIME_ARTIFACT_HASH_MISMATCH",),
        )

    if artifact.stale_after is not None and _normalize_as_of(as_of) > artifact.stale_after:
        return MlRuntimeArtifactSelection(
            status=MlRuntimeArtifactLoadStatus.STALE,
            artifact=artifact,
            summary=summary,
            summary_ref=summary_ref,
            transport_artifact_ref=transport_artifact_ref,
            reasons=("ML_RUNTIME_ARTIFACT_STALE",),
        )

    return MlRuntimeArtifactSelection(
        status=MlRuntimeArtifactLoadStatus.LOADED,
        artifact=artifact,
        summary=summary,
        summary_ref=summary_ref,
        transport_artifact_ref=transport_artifact_ref,
        reasons=("ML_RUNTIME_ARTIFACT_LOADED",),
    )


__all__ = [
    "MlRuntimeArtifactLoadStatus",
    "MlRuntimeArtifactSelection",
    "load_ml_runtime_artifact",
]
