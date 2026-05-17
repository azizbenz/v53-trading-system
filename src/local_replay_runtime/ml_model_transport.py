"""Shared LOCAL_REPLAY packaging helpers for governed ML model artifacts."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    MlModelArtifact,
    MlModelSourceArtifactSummary,
    MlSupplementaryRefsSourceSummary,
)
from interface_contracts.atomic_io import atomic_write_bytes, atomic_write_json
from local_replay_runtime.ml_governance_sidecars import discover_ml_governance_sidecar_refs


class MlModelTransportPackage(BaseModel, frozen=True):
    """Packaged ML artifact refs materialized for Local->VPS transport."""

    transport_artifact_ref: str = Field(..., min_length=1)
    summary_ref: str = Field(..., min_length=1)
    source_summary_ref: str = Field(..., min_length=1)
    supplementary_refs: tuple[str, ...] = ()
    summary: MlModelSourceArtifactSummary
    source_summary: MlSupplementaryRefsSourceSummary


def load_ml_model_artifact(source_artifact_ref: str) -> MlModelArtifact:
    """Load and validate a governed ML artifact from its serialized JSON payload."""

    path = Path(source_artifact_ref).resolve()
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"ML model artifact unreadable: {path}") from exc
    try:
        return MlModelArtifact.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"ML model artifact invalid: {path}") from exc


def build_ml_model_source_artifact_summary(
    source_artifact_ref: str,
    *,
    transport_artifact_ref: str | None = None,
) -> MlModelSourceArtifactSummary:
    """Build a typed sidecar summary from a governed ML artifact."""

    artifact = load_ml_model_artifact(source_artifact_ref)
    resolved_source = str(Path(source_artifact_ref).resolve())
    resolved_transport = resolved_source if transport_artifact_ref is None else str(
        Path(transport_artifact_ref).resolve()
    )
    return MlModelSourceArtifactSummary(
        artifact_hash=artifact.artifact_hash,
        schema_version=artifact.schema_version,
        model_family=artifact.model_family.value,
        calibration_version=artifact.calibration_version,
        feature_hash=artifact.feature_hash,
        dataset_hash=artifact.dataset_hash,
        promotion_state=artifact.promotion_state,
        pair_universe=artifact.pair_universe,
        train_window_start_at=artifact.train_window.start_at.isoformat(),
        train_window_end_at=artifact.train_window.end_at.isoformat(),
        validation_window_start_at=artifact.validation_window.start_at.isoformat(),
        validation_window_end_at=artifact.validation_window.end_at.isoformat(),
        source_artifact_ref=resolved_source,
        transport_artifact_ref=resolved_transport,
    )


def build_ml_supplementary_refs_source_summary(
    *,
    artifact: MlModelArtifact,
    transport_artifact_ref: str,
    summary_ref: str,
    supplementary_refs_count: int = 3,
    source_component: str = "LOCAL_REPLAY_ML_MODEL_TRANSPORT",
    source_stage: str = "LOCAL_REPLAY",
    source_ttl: timedelta = timedelta(days=1),
    generated_at: datetime | None = None,
) -> MlSupplementaryRefsSourceSummary:
    """Build the governed source-summary sidecar for runtime supplementary refs."""

    created_at = generated_at or datetime.now(tz=UTC)
    return MlSupplementaryRefsSourceSummary.create(
        artifact_id=f"ml-supplementary-refs-source:{artifact.artifact_hash[:12]}",
        target_artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        dataset_hash=artifact.dataset_hash,
        transport_artifact_ref=str(Path(transport_artifact_ref).resolve()),
        summary_ref=str(Path(summary_ref).resolve()),
        supplementary_refs_count=supplementary_refs_count,
        source_component=source_component,
        source_stage=source_stage,
        source_status="SUPPLEMENTARY_REFS_SOURCE_GOVERNED",
        non_empty_refs_status="NON_EMPTY_SUPPLEMENTARY_REFS_PROVEN",
        generated_at=created_at,
        source_stale_after=created_at + source_ttl,
        method_version_hash="ml_model_transport.source_summary.v1",
    )


def package_ml_model_artifact_for_transport(
    export_dir: Path,
    *,
    source_artifact_ref: str,
    artifact_filename: str = "ml_model_artifact.json",
    summary_filename: str = "ml_model_artifact.summary.json",
    source_summary_filename: str = "ml_supplementary_refs_source_summary.json",
) -> MlModelTransportPackage:
    """Package a governed ML artifact into an export dir for Local->VPS transport."""

    resolved_export_dir = export_dir.resolve()
    resolved_export_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(source_artifact_ref).resolve()
    artifact = load_ml_model_artifact(str(source_path))
    transport_artifact_path = (resolved_export_dir / artifact_filename).resolve()
    summary_path = (resolved_export_dir / summary_filename).resolve()
    source_summary_path = (resolved_export_dir / source_summary_filename).resolve()
    governance_sidecar_refs: list[str] = []

    atomic_write_bytes(transport_artifact_path, source_path.read_bytes())
    for sidecar_ref in discover_ml_governance_sidecar_refs(source_path):
        source_sidecar_path = Path(sidecar_ref).resolve()
        transport_sidecar_path = (resolved_export_dir / source_sidecar_path.name).resolve()
        shutil.copyfile(source_sidecar_path, transport_sidecar_path)
        governance_sidecar_refs.append(str(transport_sidecar_path))
    summary = build_ml_model_source_artifact_summary(
        str(source_path),
        transport_artifact_ref=str(transport_artifact_path),
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)
    supplementary_refs = tuple(
        dict.fromkeys(
            (
                str(transport_artifact_path),
                str(summary_path),
                str(source_summary_path),
                *governance_sidecar_refs,
            )
        )
    )
    source_summary = build_ml_supplementary_refs_source_summary(
        artifact=artifact,
        transport_artifact_ref=str(transport_artifact_path),
        summary_ref=str(summary_path),
        supplementary_refs_count=len(supplementary_refs),
    )
    atomic_write_json(source_summary_path, source_summary.model_dump(mode="json"), indent=2)

    reloaded_transport_artifact = load_ml_model_artifact(str(transport_artifact_path))
    if reloaded_transport_artifact.artifact_hash != artifact.artifact_hash:
        raise ValueError("packaged ML model artifact hash drifted during transport packaging")

    return MlModelTransportPackage(
        transport_artifact_ref=str(transport_artifact_path),
        summary_ref=str(summary_path),
        source_summary_ref=str(source_summary_path),
        supplementary_refs=supplementary_refs,
        summary=summary,
        source_summary=source_summary,
    )


__all__ = [
    "MlModelTransportPackage",
    "load_ml_model_artifact",
    "build_ml_model_source_artifact_summary",
    "build_ml_supplementary_refs_source_summary",
    "package_ml_model_artifact_for_transport",
]
