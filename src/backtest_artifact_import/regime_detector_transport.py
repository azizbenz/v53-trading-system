"""Governed supplementary transport helpers for RegimeDetectorML artifacts."""

from __future__ import annotations

from datetime import date
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
    RegimeDetectorArtifact,
    RegimeDetectorArtifactSummary,
)
from interface_contracts.atomic_io import atomic_write_bytes, atomic_write_json
from local_replay_runtime import ReplayExecutionPlan


class RegimeDetectorTransportPackage(BaseModel, frozen=True):
    """Packaged regime-detector artifact refs attached to a governed payload bundle."""

    transport_artifact_ref: str = Field(..., min_length=1)
    summary_ref: str = Field(..., min_length=1)
    summary: RegimeDetectorArtifactSummary


def load_regime_detector_artifact(source_artifact_ref: str) -> RegimeDetectorArtifact:
    """Load and validate a governed RegimeDetector artifact JSON payload."""

    path = Path(source_artifact_ref).resolve()
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Regime detector artifact unreadable: {path}") from exc
    try:
        return RegimeDetectorArtifact.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"Regime detector artifact invalid: {path}") from exc


def build_regime_detector_artifact_summary(
    source_artifact_ref: str,
    *,
    transport_artifact_ref: str | None = None,
) -> RegimeDetectorArtifactSummary:
    """Build a typed sidecar summary from a governed RegimeDetector artifact."""

    artifact = load_regime_detector_artifact(source_artifact_ref)
    resolved_source = str(Path(source_artifact_ref).resolve())
    resolved_transport = resolved_source if transport_artifact_ref is None else str(
        Path(transport_artifact_ref).resolve()
    )
    return RegimeDetectorArtifactSummary(
        artifact_hash=artifact.artifact_hash,
        schema_version=artifact.schema_version,
        model_family=artifact.model_family.value,
        feature_set_version=artifact.feature_set_version,
        output_semantics=artifact.output_semantics.value,
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


def package_regime_detector_artifact_for_transport(
    export_dir: Path,
    *,
    source_artifact_ref: str,
    artifact_filename: str = "regime_detector_artifact.json",
    summary_filename: str = "regime_detector_artifact.summary.json",
) -> RegimeDetectorTransportPackage:
    """Package a governed RegimeDetector artifact into an export dir."""

    resolved_export_dir = export_dir.resolve()
    resolved_export_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(source_artifact_ref).resolve()
    artifact = load_regime_detector_artifact(str(source_path))
    transport_artifact_path = (resolved_export_dir / artifact_filename).resolve()
    summary_path = (resolved_export_dir / summary_filename).resolve()

    atomic_write_bytes(transport_artifact_path, source_path.read_bytes())
    summary = build_regime_detector_artifact_summary(
        str(source_path),
        transport_artifact_ref=str(transport_artifact_path),
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)

    reloaded_transport_artifact = load_regime_detector_artifact(str(transport_artifact_path))
    if reloaded_transport_artifact.artifact_hash != artifact.artifact_hash:
        raise ValueError("packaged RegimeDetector artifact hash drifted during transport packaging")

    return RegimeDetectorTransportPackage(
        transport_artifact_ref=str(transport_artifact_path),
        summary_ref=str(summary_path),
        summary=summary,
    )


def attach_regime_detector_transport_refs(
    payload_bundle: ArtifactPayloadRefBundle,
    *,
    transport_package: RegimeDetectorTransportPackage,
) -> ArtifactPayloadRefBundle:
    """Attach packaged RegimeDetector supplementary refs to the canonical payload bundle."""

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


def build_upload_request_from_replay_plan_with_regime_detector_artifact(
    replay_plan: ReplayExecutionPlan,
    *,
    payload_bundle: ArtifactPayloadRefBundle,
    bundle: ArtifactExportBundle,
    signature_envelope: ArtifactSignatureEnvelope,
    uploaded_by: str,
    upload_context: ArtifactUploadContext,
    governance_reference_date: date,
    transport_package: RegimeDetectorTransportPackage,
) -> ArtifactUploadRequest:
    """Reuse the governed upload request path while carrying RegimeDetector refs."""

    enriched_payload_bundle = attach_regime_detector_transport_refs(
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
    "RegimeDetectorTransportPackage",
    "load_regime_detector_artifact",
    "build_regime_detector_artifact_summary",
    "package_regime_detector_artifact_for_transport",
    "attach_regime_detector_transport_refs",
    "build_upload_request_from_replay_plan_with_regime_detector_artifact",
]
