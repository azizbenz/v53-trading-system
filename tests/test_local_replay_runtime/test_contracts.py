"""Tests for the governed LOCAL_REPLAY MVP scaffold."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

import local_replay_runtime
from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import (
    ArtifactManifest,
    LocalReplayOrchestrator,
    LocalReplayEvidenceRecorder,
    LocalReplayEvidenceRecorderConfig,
    LocalReplayRequest,
    ReplayRunManifest,
    ReplayArtifactKind,
    ReplayBundle,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
    ReplayLifecycleState,
    LocalReplayRuntimeEvidence,
    SHARED_CORE_ID,
)


def _scratch_dir(name: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "local_replay_runtime_tests" / name


def test_local_replay_runtime_exports_expected_symbols():
    assert {
        "ArtifactManifest",
        "ReplayDatasetRef",
        "ReplayClockRef",
        "LocalReplayRequest",
        "ReplayBundle",
        "ReplayExecutionPlan",
        "LocalReplayRuntimeEvidence",
        "LocalReplayOrchestrator",
        "ReplayRunManifest",
        "ReplayArtifactKind",
        "HistoricalReplayOpportunity",
        "HistoricalReplayDataset",
        "load_historical_replay_dataset",
        "build_feature_bridge_payload",
        "ReplayRouteHint",
        "HistoricalMarketEventEnvelope",
        "HistoricalSnapshotBatch",
        "load_historical_snapshot_batch",
        "ReplayEventRouterConfig",
        "route_snapshot_batch_to_dataset",
        "ReplayInputKind",
        "ReplayDetailLevel",
        "ReplaySessionConfig",
        "build_replay_session_config",
        "ReplaySessionLifecycle",
        "ReplaySessionState",
        "ReplaySessionStoreConfig",
        "ReplaySessionStateStore",
        "PerformanceModeGuardReport",
        "build_performance_mode_guard_report",
        "RunConsistencyGuardReport",
        "compare_replay_runs",
        "ReplayClockTick",
        "HistoricalReplayClock",
        "build_replay_clock",
        "ShadowExecutionSimulatorConfig",
        "simulate_shadow_compatible_dtrs",
        "build_parity_diagnostics_payload",
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


def test_replay_run_manifest_accepts_canonical_local_replay_shape():
    manifest = ReplayRunManifest(
        run_id="run-1",
        strategy_id="strategy-a",
        strategy_version="a.v1",
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v1.r1",
        profile_scope=ProfileId.LIGHT,
        engine_scope=("engine_a", "engine_b"),
        tested_pairs=("BTCUSDT", "ETHUSDT"),
        dataset_manifest_id="dataset-1",
        timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="feature.v1",
        formula_set_version="formula.v1",
        scoring_version="score.v1",
        regime_version="regime.v1",
        risk_policy_version="risk.v1",
        cost_model_version="cost.v1",
        performance_mode="shadow_fidelity_mode",
        artifact_schema_version="artifact.v1",
        artifact_hash="hash-1",
        clock_id="clock-1",
        start_timestamp_ms=1_700,
        end_timestamp_ms=2_000,
        tick_count=12,
        record_count=42,
    )

    assert manifest.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert manifest.record_count == 42


def test_replay_run_manifest_rejects_non_local_runtime_and_duplicate_scope():
    with pytest.raises(ValidationError):
        ReplayRunManifest(
            run_id="run-2",
            strategy_id="strategy-a",
            strategy_version="a.v1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v1.r1",
            profile_scope=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-1",
            timeframe_scope="2026-03-01/2026-03-31",
            feature_set_version="feature.v1",
            formula_set_version="formula.v1",
            scoring_version="score.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_schema_version="artifact.v1",
            artifact_hash="hash-1",
            clock_id="clock-1",
            start_timestamp_ms=1_700,
            end_timestamp_ms=2_000,
        )

    with pytest.raises(ValidationError):
        ReplayRunManifest(
            run_id="run-3",
            strategy_id="strategy-a",
            strategy_version="a.v1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v1.r1",
            profile_scope=ProfileId.LIGHT,
            engine_scope=("engine_a", "engine_a"),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-1",
            timeframe_scope="2026-03-01/2026-03-31",
            feature_set_version="feature.v1",
            formula_set_version="formula.v1",
            scoring_version="score.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="research_fast_mode",
            artifact_schema_version="artifact.v1",
            artifact_hash="hash-1",
            clock_id="clock-1",
            start_timestamp_ms=2_000,
            end_timestamp_ms=1_700,
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
        payload_refs=(
            "exports/review.md",
            "exports/feature_bridge.json",
            "exports/parity.json",
            "exports/replay_metrics.json",
            "exports/replay_dtr.json",
        ),
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        diagnostic_ids=("diag-1",),
        candidate_ids=("cand-1",),
        review_export_ref="exports/review.md",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
    )

    assert isinstance(plan, ReplayExecutionPlan)
    assert plan.validation_ready is True
    assert plan.bundle.lifecycle_state == ReplayLifecycleState.VALIDATED
    assert plan.bundle.manifest.dataset_ref == "dataset-1"
    assert plan.bundle.manifest.review_export_ref == "exports/review.md"
    assert plan.bundle.manifest.feature_bridge_ref == "exports/feature_bridge.json"
    assert plan.bundle.manifest.parity_diagnostics_ref == "exports/parity.json"

    evidence = LocalReplayOrchestrator.build_runtime_evidence(plan)
    assert isinstance(evidence, LocalReplayRuntimeEvidence)
    assert evidence.data_source == "recorded_replay"
    assert evidence.feature_bridge_ready is True
    assert evidence.parity_diagnostics_ready is True
    assert evidence.replay_metrics_ready is True
    assert evidence.replay_dtr_ready is True
    assert evidence.replay_useful_ready is True


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
        "feature bridge ref is required before validation",
        "parity diagnostics ref is required before validation",
        "replay metrics ref is required before validation",
        "replay dtr ref is required before validation",
    }

    evidence = LocalReplayOrchestrator.build_runtime_evidence(plan)
    assert evidence.data_source == "unknown"
    assert evidence.replay_useful_ready is False


def test_local_replay_evidence_recorder_materializes_useful_replay_evidence():
    request = LocalReplayRequest(
        correlation_id="corr-runtime-recorder",
        profile=ProfileId.LIGHT,
        strategy_classification=StrategyClassification.A_VARIANT,
        lineage_version="a.v4.1",
        replay_reason="Replay runtime recorder coverage",
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
        artifact_id="artifact-runtime",
        strategy_version="a.v4",
        payload_refs=(
            "exports/review.md",
            "exports/feature_bridge.json",
            "exports/parity.json",
            "exports/replay_metrics.json",
            "exports/replay_dtr.json",
        ),
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        review_export_ref="exports/review.md",
        feature_bridge_ref="exports/feature_bridge.json",
        parity_diagnostics_ref="exports/parity.json",
        replay_metrics_ref="exports/replay_metrics.json",
        replay_dtr_ref="exports/replay_dtr.json",
    )
    recorder = LocalReplayEvidenceRecorder()

    recorder.load_execution_plan(plan)
    recorder.mark_payload_generated("exports/feature_bridge.json")
    recorder.mark_payload_generated("exports/parity.json")
    recorder.mark_payload_generated("exports/replay_metrics.json")
    partial = recorder.build_evidence()
    recorder.mark_payload_generated("exports/replay_dtr.json")
    full = recorder.build_evidence()

    assert partial.replay_useful_ready is False
    assert full.replay_useful_ready is True
    assert full.data_source == "recorded_replay"


def test_local_replay_evidence_recorder_persists_state_across_restart():
    state_dir = _scratch_dir("evidence")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        request = LocalReplayRequest(
            correlation_id="corr-runtime-recorder-persist",
            profile=ProfileId.LIGHT,
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v5.1",
            replay_reason="Replay runtime recorder persistence",
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
            artifact_id="artifact-runtime-persist",
            strategy_version="a.v5",
            payload_refs=(
                "exports/review.md",
                "exports/feature_bridge.json",
                "exports/parity.json",
                "exports/replay_metrics.json",
                "exports/replay_dtr.json",
            ),
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
            review_export_ref="exports/review.md",
            feature_bridge_ref="exports/feature_bridge.json",
            parity_diagnostics_ref="exports/parity.json",
            replay_metrics_ref="exports/replay_metrics.json",
            replay_dtr_ref="exports/replay_dtr.json",
        )
        config = LocalReplayEvidenceRecorderConfig(state_dir=state_dir, persist_state=True)
        recorder = LocalReplayEvidenceRecorder(config=config)
        recorder.load_execution_plan(plan)
        recorder.mark_payloads_generated(
            (
                "exports/feature_bridge.json",
                "exports/parity.json",
                "exports/replay_metrics.json",
                "exports/replay_dtr.json",
            )
        )

        reloaded = LocalReplayEvidenceRecorder(config=config)
        evidence = reloaded.build_evidence()

        assert evidence.replay_useful_ready is True
        assert evidence.artifact_id == "artifact-runtime-persist"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
