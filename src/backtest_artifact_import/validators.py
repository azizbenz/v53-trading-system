"""Guards for controlled artifact import."""

from __future__ import annotations

from backtest_artifact_import.contracts import ArtifactImportDecision, ArtifactImportRequest
from interface_contracts import PromotionState, ReviewState, RuntimeMode
from local_replay_runtime.artifact_manifest import ArtifactManifest


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


__all__ = [
    "validate_artifact_manifest",
    "validate_import_request",
]
