"""Governed supplementary transport helpers for bounded ML model artifacts."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from pydantic import BaseModel, Field

from backtest_artifact_import.contracts import (
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    ArtifactUploadRequest,
)
from backtest_artifact_import.export_dir_bridge import build_upload_request_from_replay_plan
from interface_contracts import (
    ArtifactExportBundle,
    ArtifactSignatureEnvelope,
    MlModelArtifact,
    MlModelSourceArtifactSummary,
)
from interface_contracts.atomic_io import atomic_write_bytes, atomic_write_json
from local_replay_runtime import ReplayExecutionPlan

class MlModelTransportPackage(BaseModel, frozen=True):
    """Packaged ML artifact refs attached to the governed payload bundle."""

    transport_artifact_ref: str = Field(..., min_length=1)
    summary_ref: str = Field(..., min_length=1)
    summary: MlModelSourceArtifactSummary


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


def package_ml_model_artifact_for_transport(
    export_dir: Path,
    *,
    source_artifact_ref: str,
    artifact_filename: str = "ml_model_artifact.json",
    summary_filename: str = "ml_model_artifact.summary.json",
) -> MlModelTransportPackage:
    """Package a governed ML artifact into an export dir for Local->VPS transport."""

    resolved_export_dir = export_dir.resolve()
    resolved_export_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(source_artifact_ref).resolve()
    artifact = load_ml_model_artifact(str(source_path))
    transport_artifact_path = (resolved_export_dir / artifact_filename).resolve()
    summary_path = (resolved_export_dir / summary_filename).resolve()

    atomic_write_bytes(transport_artifact_path, source_path.read_bytes())
    summary = build_ml_model_source_artifact_summary(
        str(source_path),
        transport_artifact_ref=str(transport_artifact_path),
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    reloaded_transport_artifact = load_ml_model_artifact(str(transport_artifact_path))
    if reloaded_transport_artifact.artifact_hash != artifact.artifact_hash:
        raise ValueError("packaged ML model artifact hash drifted during transport packaging")

    return MlModelTransportPackage(
        transport_artifact_ref=str(transport_artifact_path),
        summary_ref=str(summary_path),
        summary=summary,
    )


def attach_ml_model_transport_refs(
    payload_bundle: ArtifactPayloadRefBundle,
    *,
    transport_package: MlModelTransportPackage,
) -> ArtifactPayloadRefBundle:
    """Attach packaged ML supplementary refs to the canonical payload bundle."""

    supplementary_refs = tuple(
        dict.fromkeys(
            (
                *payload_bundle.supplementary_refs,
                transport_package.transport_artifact_ref,
                transport_package.summary_ref,
            )
        )
    )
    return ArtifactPayloadRefBundle(
        review_export_ref=payload_bundle.review_export_ref,
        feature_bridge_ref=payload_bundle.feature_bridge_ref,
        parity_diagnostics_ref=payload_bundle.parity_diagnostics_ref,
        replay_metrics_ref=payload_bundle.replay_metrics_ref,
        replay_dtr_ref=payload_bundle.replay_dtr_ref,
        supplementary_refs=supplementary_refs,
    )


def build_upload_request_from_replay_plan_with_ml_model_artifact(
    replay_plan: ReplayExecutionPlan,
    *,
    payload_bundle: ArtifactPayloadRefBundle,
    bundle: ArtifactExportBundle,
    signature_envelope: ArtifactSignatureEnvelope,
    uploaded_by: str,
    upload_context: ArtifactUploadContext,
    governance_reference_date: date,
    transport_package: MlModelTransportPackage,
) -> ArtifactUploadRequest:
    """Reuse the governed upload request path while carrying ML supplementary refs."""

    enriched_payload_bundle = attach_ml_model_transport_refs(
        payload_bundle,
        transport_package=transport_package,
    )
    return build_upload_request_from_replay_plan(
        replay_plan,
        payload_bundle=enriched_payload_bundle,
        bundle=bundle,
        signature_envelope=signature_envelope,
        uploaded_by=uploaded_by,
        upload_context=upload_context,
        governance_reference_date=governance_reference_date,
    )


__all__ = [
    "MlModelSourceArtifactSummary",
    "MlModelTransportPackage",
    "load_ml_model_artifact",
    "build_ml_model_source_artifact_summary",
    "package_ml_model_artifact_for_transport",
    "attach_ml_model_transport_refs",
    "build_upload_request_from_replay_plan_with_ml_model_artifact",
]
