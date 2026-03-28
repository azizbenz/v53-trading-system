"""Governed LOCAL_REPLAY bundle preparation helpers."""

from __future__ import annotations

from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.contracts import (
    LocalReplayRequest,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
    ReplayBundle,
)
from local_replay_runtime.enums import ReplayArtifactKind, ReplayLifecycleState


class LocalReplayOrchestrator:
    """Prepare governed LOCAL_REPLAY bundles without executing replay logic."""

    @staticmethod
    def prepare_bundle(
        request: LocalReplayRequest,
        *,
        artifact_id: str,
        strategy_version: str,
        artifact_kind: ReplayArtifactKind = ReplayArtifactKind.REVIEW_PACKET,
        payload_refs: tuple[str, ...] = (),
        dataset_ref: ReplayDatasetRef | None = None,
        clock_ref: ReplayClockRef | None = None,
        diagnostic_ids: tuple[str, ...] = (),
        candidate_ids: tuple[str, ...] = (),
        review_export_ref: str = "",
        notes: str = "",
    ) -> ReplayExecutionPlan:
        validation_notes: list[str] = []
        if dataset_ref is None:
            validation_notes.append("dataset ref is required before validation")
        if clock_ref is None:
            validation_notes.append("clock ref is required before validation")
        if not payload_refs:
            validation_notes.append("payload refs are required before validation")
        if artifact_kind == ReplayArtifactKind.REVIEW_PACKET and not review_export_ref:
            validation_notes.append("review export ref is required for review packets")

        manifest = ArtifactManifest(
            artifact_id=artifact_id,
            correlation_id=request.correlation_id,
            source_profile=request.profile,
            strategy_classification=request.strategy_classification,
            strategy_version=strategy_version,
            lineage_version=request.lineage_version,
            dataset_ref=dataset_ref.dataset_id if dataset_ref else "",
            clock_ref=clock_ref.clock_id if clock_ref else "",
            diagnostic_ids=diagnostic_ids,
            candidate_ids=candidate_ids,
            review_export_ref=review_export_ref,
        )
        bundle = ReplayBundle(
            manifest=manifest,
            artifact_kind=artifact_kind,
            lifecycle_state=(
                ReplayLifecycleState.VALIDATED
                if not validation_notes
                else ReplayLifecycleState.DRAFT
            ),
            payload_refs=payload_refs,
            notes=notes,
        )

        return ReplayExecutionPlan(
            request=request,
            bundle=bundle,
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
            validation_ready=not validation_notes,
            validation_notes=tuple(validation_notes),
        )


__all__ = [
    "LocalReplayOrchestrator",
]
