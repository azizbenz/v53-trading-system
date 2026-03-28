"""Tests for the minimal LOCAL_REPLAY scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import local_replay_runtime
from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import (
    ArtifactManifest,
    LocalReplayRequest,
    ReplayArtifactKind,
    ReplayBundle,
    ReplayLifecycleState,
    SHARED_CORE_ID,
)


def test_local_replay_runtime_exports_expected_symbols():
    assert {
        "ArtifactManifest",
        "LocalReplayRequest",
        "ReplayBundle",
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
