"""Governed ML transport helpers built on shared LOCAL_REPLAY packaging."""

from __future__ import annotations

from datetime import date

from backtest_artifact_import.contracts import (
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    ArtifactUploadRequest,
)
from backtest_artifact_import.export_dir_bridge import build_upload_request_from_replay_plan
from interface_contracts import (
    ArtifactExportBundle,
    ArtifactSignatureEnvelope,
    MlModelSourceArtifactSummary,
    MlSupplementaryRefsSourceSummary,
)
from local_replay_runtime.contracts import ReplayExecutionPlan
from local_replay_runtime.ml_model_transport import (
    MlModelTransportPackage,
    build_ml_model_source_artifact_summary,
    build_ml_supplementary_refs_source_summary,
    load_ml_model_artifact,
    package_ml_model_artifact_for_transport,
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
                *transport_package.supplementary_refs,
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
    "MlSupplementaryRefsSourceSummary",
    "MlModelTransportPackage",
    "load_ml_model_artifact",
    "build_ml_model_source_artifact_summary",
    "build_ml_supplementary_refs_source_summary",
    "package_ml_model_artifact_for_transport",
    "attach_ml_model_transport_refs",
    "build_upload_request_from_replay_plan_with_ml_model_artifact",
]
