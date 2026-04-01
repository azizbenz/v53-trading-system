"""Governed LOCAL_REPLAY bundle preparation helpers."""

from __future__ import annotations

from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.contracts import (
    LocalReplayRequest,
    LocalReplayRuntimeEvidence,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
    ReplayBundle,
)
from local_replay_runtime.enums import ReplayArtifactKind, ReplayLifecycleState


class LocalReplayOrchestrator:
    """Prepare governed LOCAL_REPLAY bundles without executing replay logic."""

    @staticmethod
    def build_runtime_evidence(
        execution_plan: ReplayExecutionPlan,
    ) -> LocalReplayRuntimeEvidence:
        """Project typed replay-usefulness evidence from a prepared execution plan."""

        manifest = execution_plan.bundle.manifest
        payload_refs = set(execution_plan.bundle.payload_refs)
        feature_bridge_ready = bool(manifest.feature_bridge_ref) and (
            manifest.feature_bridge_ref in payload_refs
        )
        parity_diagnostics_ready = bool(manifest.parity_diagnostics_ref) and (
            manifest.parity_diagnostics_ref in payload_refs
        )
        replay_metrics_ready = bool(manifest.replay_metrics_ref) and (
            manifest.replay_metrics_ref in payload_refs
        )
        replay_dtr_ready = bool(manifest.replay_dtr_ref) and (
            manifest.replay_dtr_ref in payload_refs
        )
        data_source = (
            "recorded_replay"
            if execution_plan.dataset_ref is not None and execution_plan.clock_ref is not None
            else "unknown"
        )
        replay_useful_ready = (
            execution_plan.validation_ready
            and feature_bridge_ready
            and parity_diagnostics_ready
            and replay_metrics_ready
            and replay_dtr_ready
        )
        return LocalReplayRuntimeEvidence(
            artifact_id=manifest.artifact_id,
            lineage_version=manifest.lineage_version,
            data_source=data_source,
            feature_bridge_ready=feature_bridge_ready,
            parity_diagnostics_ready=parity_diagnostics_ready,
            replay_metrics_ready=replay_metrics_ready,
            replay_dtr_ready=replay_dtr_ready,
            replay_useful_ready=replay_useful_ready,
            evidence_summary=(
                f"source={data_source} / "
                f"feature_bridge={'yes' if feature_bridge_ready else 'no'} / "
                f"parity={'yes' if parity_diagnostics_ready else 'no'} / "
                f"metrics={'yes' if replay_metrics_ready else 'no'} / "
                f"replay_dtr={'yes' if replay_dtr_ready else 'no'}"
            ),
        )

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
        feature_bridge_ref: str = "",
        parity_diagnostics_ref: str = "",
        replay_metrics_ref: str = "",
        replay_dtr_ref: str = "",
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
        if not feature_bridge_ref:
            validation_notes.append("feature bridge ref is required before validation")
        if not parity_diagnostics_ref:
            validation_notes.append("parity diagnostics ref is required before validation")
        if not replay_metrics_ref:
            validation_notes.append("replay metrics ref is required before validation")
        if not replay_dtr_ref:
            validation_notes.append("replay dtr ref is required before validation")

        manifest = ArtifactManifest(
            artifact_id=artifact_id,
            correlation_id=request.correlation_id,
            source_profile=request.profile,
            strategy_classification=request.strategy_classification,
            strategy_version=strategy_version,
            lineage_version=request.lineage_version,
            dataset_ref=dataset_ref.dataset_id if dataset_ref else "",
            clock_ref=clock_ref.clock_id if clock_ref else "",
            feature_bridge_ref=feature_bridge_ref,
            parity_diagnostics_ref=parity_diagnostics_ref,
            replay_metrics_ref=replay_metrics_ref,
            replay_dtr_ref=replay_dtr_ref,
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
