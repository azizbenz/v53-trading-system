from __future__ import annotations

import base64
from datetime import datetime, timezone

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DeploymentState,
    MlModelArtifact,
    RegimeDetectorFeatureSetVersion,
    ReviewState,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from local_replay_runtime import (
    LiveCompleteOperatorAuditReport,
    LocalLabMlArtifactTrainingReport,
    LocalLabMlFinalAuditReport,
    LocalLabRegimeDetectorFinalAuditReport,
    LocalLabRegimeDetectorProfileComparisonReport,
    build_live_complete_operator_audit_report,
    write_live_complete_operator_audit_report,
)
from tests.support_paths import make_repo_scratch_dir
from protocols import (
    LiveCompleteDecision,
    LiveCompleteExecutionEnvelope,
    LiveCompleteRunState,
    LiveCompleteRunSummary,
    LiveCompleteVerdict,
    LiveLightVerdict,
)


def _live_complete_summary(*, final_state: VpsWarmupState) -> LiveCompleteRunSummary:
    recovery = VpsRecoveryReadinessReport(
        report_id="recovery-1",
        runtime_mode=RuntimeMode.LIVE,
        deployment_state=DeploymentState.LIVE_COMPLETE,
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=VpsRecoveryCheckStatus.PASSED,
            ),
        ),
        eligible_to_trade=final_state == VpsWarmupState.ELIGIBLE_TO_TRADE,
    )
    return LiveCompleteRunSummary(
        run_id="live-complete-run-1",
        correlation_id="corr-operator-audit",
        run_state=LiveCompleteRunState.READY_FOR_COMPLETE_SUPERVISION,
        deployment_state=DeploymentState.LIVE_COMPLETE,
        live_light_run_id="live-light-run-1",
        micro_live_run_id="micro-run-1",
        shadow_run_id="shadow-run-1",
        live_light_verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
        decision=LiveCompleteDecision(
            allowed_complete_supervision=True,
            verdict=LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION,
            review_state=ReviewState.APPROVED,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_envelope=LiveCompleteExecutionEnvelope(
            envelope_id="complete-envelope-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            deployment_state=DeploymentState.LIVE_COMPLETE,
            selected_pairs=("BTCUSDT",),
            allowed_actions=("set_halted", "request_export_active_ml_artifact"),
            forbidden_actions=("bypass_hard_blocker",),
            command_queue_enabled=True,
            active_ml_artifact_hash="a" * 64,
            active_regime_detector_artifact_hash="b" * 64,
            recovery_state=final_state.value,
            autonomous_execution_enabled=False,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        command_queue_snapshot=DashboardCommandQueueSnapshot(
            queue_dir_ref="build/queue",
            request_dir_ref="build/queue/requests",
            ack_dir_ref="build/queue/acks",
            result_dir_ref="build/queue/results",
            queue_status=DashboardCommandQueueStatus.HEALTHY,
            pending_request_count=0,
            accepted_ack_count=1,
            completed_result_count=1,
            writable=True,
            drainable=True,
            healthy=True,
        ),
        active_ml_artifact=DashboardArtifactTransferManifest(
            artifact_hash="a" * 64,
            artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
            artifact_id="ml-1",
            source_ref="exports/ml.json",
        ),
        active_regime_detector_artifact=DashboardArtifactTransferManifest(
            artifact_hash="b" * 64,
            artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            artifact_id="regime-1",
            feature_profile="extended_v2",
            source_ref="exports/regime.json",
        ),
        recovery_readiness_report=recovery,
        warmup_run_summary=VpsWarmupRunSummary(
            run_id="warmup-1",
            runtime_mode=RuntimeMode.LIVE,
            final_state=final_state,
            phase_sequence=(VpsWarmupState.COLD_START, final_state),
            report=recovery,
            eligible_to_trade=final_state == VpsWarmupState.ELIGIBLE_TO_TRADE,
        ),
    )


def _regime_report(*, status: str, audit_ready: bool) -> LocalLabRegimeDetectorFinalAuditReport:
    comparison = LocalLabRegimeDetectorProfileComparisonReport(
        correlation_id="corr-operator-audit",
        status="ready",
        comparison_ready=True,
        calibration_version="lob-regime.v2",
        training_seed=17,
        dataset_id="dataset-1",
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        pair_scope=("BTCUSDT",),
        compared_profile_count=3,
        ready_profile_count=3,
        winner_profile="extended_v2",
        recommended_default_profile="extended_v2",
        recommendation="keep_extended_v2_default",
    )
    return LocalLabRegimeDetectorFinalAuditReport(
        correlation_id="corr-operator-audit",
        status=status,
        audit_ready=audit_ready,
        comparison_ready=True,
        shadow_audit_present=True,
        calibration_version="lob-regime.v2",
        training_seed=17,
        dataset_id="dataset-1",
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        pair_scope=("BTCUSDT",),
        winner_profile="extended_v2",
        recommended_default_profile="extended_v2",
        uploaded_profile="extended_v2",
        uploaded_artifact_hash="b" * 64,
        uploaded_profile_rank=1,
        uploaded_profile_matches_lab_default=True,
        final_recommendation="uploaded_profile_matches_lab_recommendation",
        comparison_report=comparison,
    )


def _ml_artifact(seed: str) -> MlModelArtifact:
    return MlModelArtifact.create(
        feature_names=("spread_bps", "depth_imbalance"),
        feature_hash=seed * 64,
        pair_universe=("BTCUSDT",),
        train_window={
            "start_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "end_at": datetime(2026, 1, 31, tzinfo=timezone.utc),
        },
        validation_window={
            "start_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
            "end_at": datetime(2026, 2, 28, tzinfo=timezone.utc),
        },
        oos_sharpe=1.1,
        backtest_sharpe=1.4,
        shadow_diff_pct=1.0,
        training_seed=17,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        calibration_version="ml.v1",
        dataset_hash="d" * 64,
        model_bytes_b64=base64.b64encode(b"ml-model").decode("ascii"),
    )


def _training_report() -> LocalLabMlArtifactTrainingReport:
    artifact = _ml_artifact("a")
    return LocalLabMlArtifactTrainingReport(
        correlation_id="corr-operator-audit",
        export_dir="build/ml",
        status="ready",
        ready=True,
        replay_sample_count=16,
        training_row_count=16,
        recognized_feature_key_count=2,
        pair_scope=("BTCUSDT",),
        engine_scope=("engine_a",),
        artifact=artifact,
        artifact_hash=artifact.artifact_hash,
        oos_sharpe=artifact.oos_sharpe,
        backtest_sharpe=artifact.backtest_sharpe,
    )


def _ml_report(*, status: str, audit_ready: bool) -> LocalLabMlFinalAuditReport:
    training_report = _training_report()
    return LocalLabMlFinalAuditReport(
        correlation_id="corr-operator-audit",
        status=status,
        audit_ready=audit_ready,
        uploaded_artifact_present=True,
        recommended_artifact_hash=training_report.artifact_hash or "",
        uploaded_artifact_hash=training_report.artifact_hash or "",
        uploaded_artifact_id="ml-1",
        uploaded_lineage_version="a.v1.0.r1",
        uploaded_feature_set_version="ml_feature_set.v1",
        feature_set_compatible=True,
        artifact_matches_lab_recommendation=audit_ready,
        final_recommendation=(
            "uploaded_ml_artifact_matches_lab_recommendation"
            if audit_ready
            else "uploaded_ml_artifact_differs_from_lab_recommendation"
        ),
        training_report=training_report,
    )


def test_live_complete_operator_audit_report_requires_regime_report_for_full_readiness() -> None:
    report = build_live_complete_operator_audit_report(
        live_complete_summary=_live_complete_summary(
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE
        ),
    )

    assert isinstance(report, LiveCompleteOperatorAuditReport)
    assert report.status == "partial"
    assert report.operator_ready is False
    assert report.final_recommendation == "collect_ml_final_audit_report"


def test_live_complete_operator_audit_report_is_ready_when_all_surfaces_are_ready() -> None:
    report = build_live_complete_operator_audit_report(
        live_complete_summary=_live_complete_summary(
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE
        ),
        ml_final_audit_report=_ml_report(status="ready", audit_ready=True),
        regime_detector_final_audit_report=_regime_report(status="ready", audit_ready=True),
    )

    assert report.status == "ready"
    assert report.operator_ready is True
    assert report.final_recommendation == "operator_surface_ready_for_complete_supervision"


def test_live_complete_operator_audit_report_stays_partial_until_warmup_is_complete() -> None:
    report = build_live_complete_operator_audit_report(
        live_complete_summary=_live_complete_summary(
            final_state=VpsWarmupState.WARMUP_SHADOW_ONLY
        ),
        ml_final_audit_report=_ml_report(status="ready", audit_ready=True),
        regime_detector_final_audit_report=_regime_report(status="ready", audit_ready=True),
    )

    assert report.status == "partial"
    assert report.operator_ready is False
    assert report.final_recommendation == "complete_warmup_before_trading"


def test_live_complete_operator_audit_report_can_be_persisted() -> None:
    report = build_live_complete_operator_audit_report(
        live_complete_summary=_live_complete_summary(
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE
        ),
        ml_final_audit_report=_ml_report(status="ready", audit_ready=True),
        regime_detector_final_audit_report=_regime_report(status="ready", audit_ready=True),
    )
    scratch_dir = make_repo_scratch_dir("live_complete_operator_audit", "persist")
    path = write_live_complete_operator_audit_report(
        report,
        scratch_dir / "live_complete_operator_audit_report.json",
    )

    assert path.exists()
    assert '"status": "ready"' in path.read_text(encoding="utf-8")


def test_live_complete_operator_audit_report_downgrades_when_ml_audit_is_not_ready() -> None:
    report = build_live_complete_operator_audit_report(
        live_complete_summary=_live_complete_summary(
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE
        ),
        ml_final_audit_report=_ml_report(status="partial", audit_ready=False),
        regime_detector_final_audit_report=_regime_report(status="ready", audit_ready=True),
    )

    assert report.status == "partial"
    assert report.operator_ready is False
    assert report.ml_audit_present is True
    assert report.ml_audit_status == "partial"
    assert report.final_recommendation == "uploaded_ml_artifact_differs_from_lab_recommendation"
