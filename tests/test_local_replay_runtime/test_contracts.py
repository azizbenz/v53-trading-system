"""Tests for the governed LOCAL_REPLAY MVP scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import local_replay_runtime
from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import (
    ArtifactManifest,
    LocalReplayOrchestrator,
    LocalReplayRequest,
    ReplayArtifactKind,
    ReplayBundle,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
    ReplayLifecycleState,
    SHARED_CORE_ID,
)


def test_local_replay_runtime_exports_expected_symbols():
    assert {
        "ArtifactManifest",
        "ReplayDatasetRef",
        "ReplayClockRef",
        "LocalReplayRequest",
        "ReplayBundle",
        "ReplayExecutionPlan",
        "LocalReplayOrchestrator",
        "ReplayArtifactKind",
    }.issubset(set(local_replay_runtime.__all__))


def test_artifact_manifest_accepts_unified_v53_shape():
    manifest = ArtifactManifest(
        artifact_id="artifact-1",
        correlation_id="corr-1",
        source_profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v1",
        lineage_version="a.v1.1",
    )

    assert manifest.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert manifest.shared_core_id == SHARED_CORE_ID


def test_artifact_manifest_rejects_backtest_profile():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2",
            correlation_id="corr-2",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
            backtest_profile="paper_only",
        )


def test_artifact_manifest_rejects_non_local_replay_runtime():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2b",
            correlation_id="corr-2b",
            source_profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
        )


def test_artifact_manifest_rejects_shared_core_drift():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2c",
            correlation_id="corr-2c",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
            shared_core_id="forked_core",
        )


def test_artifact_manifest_rejects_inconsistent_lineage_and_ref_pairs():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2e",
            correlation_id="corr-2e",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="b.v2.1",
        )

    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2f",
            correlation_id="corr-2f",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
            dataset_ref="dataset-1",
        )


def test_artifact_manifest_rejects_duplicate_governed_refs():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2g",
            correlation_id="corr-2g",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
            dataset_ref="dataset-1",
            clock_ref="clock-1",
            diagnostic_ids=("diag-1", "diag-1"),
        )


def test_artifact_manifest_rejects_implicit_promotion_request():
    with pytest.raises(ValidationError):
        ArtifactManifest(
            artifact_id="artifact-2d",
            correlation_id="corr-2d",
            source_profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            strategy_version="a.v1",
            lineage_version="a.v1.1",
            implicit_promotion_requested=True,
        )


def test_local_replay_request_rejects_non_local_replay_mode():
    with pytest.raises(ValidationError):
        LocalReplayRequest(
            correlation_id="corr-3",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            strategy_classification=StrategyClassification.B_VARIANT,
            lineage_version="b.v2",
            replay_reason="Validate a guarded replay candidate",
        )


def test_local_replay_request_rejects_profile_fork():
    with pytest.raises(ValidationError):
        LocalReplayRequest(
            correlation_id="corr-4",
            profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.B_VARIANT,
            lineage_version="b.v2",
            replay_reason="Validate a guarded replay candidate",
            creates_profile_fork=True,
        )


def test_local_replay_request_rejects_live_mutation():
    with pytest.raises(ValidationError):
        LocalReplayRequest(
            correlation_id="corr-5",
            profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.B_VARIANT,
            lineage_version="b.v2",
            replay_reason="Validate a guarded replay candidate",
            live_mutation_requested=True,
        )


def test_replay_bundle_wraps_manifest_without_mutating_policy():
    manifest = ArtifactManifest(
        artifact_id="artifact-3",
        correlation_id="corr-3",
        source_profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.BUILD14_ENABLER,
        strategy_version="build14.v0",
        lineage_version="build14.v0.1",
    )
    bundle = ReplayBundle(
        manifest=manifest,
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
        lifecycle_state=ReplayLifecycleState.VALIDATED,
        payload_refs=("reports/review.md",),
    )

    assert bundle.manifest.artifact_id == "artifact-3"
    assert bundle.lifecycle_state == ReplayLifecycleState.VALIDATED


def test_replay_bundle_defaults_to_draft_state():
    manifest = ArtifactManifest(
        artifact_id="artifact-4",
        correlation_id="corr-4",
        source_profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.A_VARIANT,
        strategy_version="a.v2",
        lineage_version="a.v2.1",
    )
    bundle = ReplayBundle(
        manifest=manifest,
        artifact_kind=ReplayArtifactKind.REVIEW_PACKET,
    )

    assert bundle.lifecycle_state == ReplayLifecycleState.DRAFT


def test_replay_clock_ref_rejects_inverted_ranges():
    with pytest.raises(ValidationError):
        ReplayClockRef(
            clock_id="clock-1",
            start_timestamp_ms=2_000,
            end_timestamp_ms=1_000,
        )


def test_local_replay_orchestrator_prepares_validated_bundle_when_refs_are_complete():
    request = LocalReplayRequest(
        correlation_id="corr-plan",
        profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v2.1",
        replay_reason="Validate governed candidate",
    )
    dataset_ref = ReplayDatasetRef(dataset_id="dataset-1", pair_scope=("BTCUSDT",), record_count=100)
    clock_ref = ReplayClockRef(
        clock_id="clock-1",
        start_timestamp_ms=1_000,
        end_timestamp_ms=2_000,
        tick_count=50,
    )

    plan = LocalReplayOrchestrator.prepare_bundle(
        request,
        artifact_id="artifact-plan",
        strategy_version="a.v2",
        payload_refs=("exports/review.md", "exports/bundle.json"),
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        diagnostic_ids=("diag-1",),
        candidate_ids=("cand-1",),
        review_export_ref="exports/review.md",
    )

    assert isinstance(plan, ReplayExecutionPlan)
    assert plan.validation_ready is True
    assert plan.bundle.lifecycle_state == ReplayLifecycleState.VALIDATED
    assert plan.bundle.manifest.dataset_ref == "dataset-1"
    assert plan.bundle.manifest.review_export_ref == "exports/review.md"


def test_local_replay_orchestrator_keeps_partial_plan_non_ready_without_executing_replay():
    request = LocalReplayRequest(
        correlation_id="corr-plan-partial",
        profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.B_VARIANT,
        lineage_version="b.v1.2",
        replay_reason="Prepare governed bundle",
    )

    plan = LocalReplayOrchestrator.prepare_bundle(
        request,
        artifact_id="artifact-partial",
        strategy_version="b.v1",
    )

    assert plan.validation_ready is False
    assert plan.bundle.lifecycle_state == ReplayLifecycleState.DRAFT
    assert set(plan.validation_notes) == {
        "dataset ref is required before validation",
        "clock ref is required before validation",
        "payload refs are required before validation",
        "review export ref is required for review packets",
    }
