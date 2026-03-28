"""Guards for controlled artifact import."""

from __future__ import annotations

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactImportSummary,
)
from interface_contracts import PromotionState, ReviewState, RuntimeMode
from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.enums import ReplayArtifactKind


def validate_artifact_manifest(manifest: ArtifactManifest) -> None:
    """Rely on ArtifactManifest model validation for canonical guards."""
    ArtifactManifest.model_validate(manifest.model_dump())


def validate_import_request(request: ArtifactImportRequest) -> ArtifactImportDecision:
    """Validate import request without bypassing promotion gates."""
    validate_artifact_manifest(request.manifest)

    reasons: list[str] = []

    if request.target_runtime_mode != RuntimeMode.SHADOW:
        reasons.append("import target must start at SHADOW")

    if request.requested_promotion_state in {
        PromotionState.MICRO_LIVE_CANDIDATE,
        PromotionState.LIVE_CANDIDATE,
    }:
        reasons.append("implicit promotion beyond SHADOW is forbidden")

    if request.manifest.exported_from != "local":
        reasons.append("unsupported artifact origin")

    if len(set(request.payload_refs)) != len(request.payload_refs):
        reasons.append("payload refs must be unique")

    if not request.payload_refs:
        reasons.append("payload refs are required for governed import")

    if request.artifact_kind == ReplayArtifactKind.REVIEW_PACKET:
        if not request.manifest.review_export_ref:
            reasons.append("review packets require a review export ref")
        elif request.manifest.review_export_ref not in request.payload_refs:
            reasons.append("review export ref must be included in payload refs")

    if not request.manifest.dataset_ref or not request.manifest.clock_ref:
        reasons.append("dataset and clock refs are required for governed import")

    accepted = len(reasons) == 0
    normalized_state = (
        PromotionState.SHADOW_CANDIDATE if accepted else PromotionState.REPLAY_ONLY
    )
    review_state = ReviewState.PENDING if accepted else ReviewState.NEEDS_REVISION

    return ArtifactImportDecision(
        accepted=accepted,
        normalized_promotion_state=normalized_state,
        review_state=review_state,
        reasons=tuple(reasons),
    )


def summarize_import_request(
    request: ArtifactImportRequest,
    decision: ArtifactImportDecision,
) -> ArtifactImportSummary:
    """Build a stable summary for monitoring and UI projections."""

    return ArtifactImportSummary(
        artifact_id=request.manifest.artifact_id,
        correlation_id=request.manifest.correlation_id,
        artifact_kind=request.artifact_kind,
        strategy_classification=request.manifest.strategy_classification,
        lineage_version=request.manifest.lineage_version,
        exported_from=request.manifest.exported_from,
        dataset_ref=request.manifest.dataset_ref,
        clock_ref=request.manifest.clock_ref,
        review_export_ref=request.manifest.review_export_ref,
        payload_ref_count=len(request.payload_refs),
        accepted=decision.accepted,
        validation_status="accepted" if decision.accepted else "needs_revision",
        normalized_promotion_state=decision.normalized_promotion_state,
        review_state=decision.review_state,
        rejection_reasons=decision.reasons,
    )


__all__ = [
    "validate_artifact_manifest",
    "validate_import_request",
    "summarize_import_request",
]
