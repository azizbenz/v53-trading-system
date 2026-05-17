from __future__ import annotations

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DeploymentState,
    ReviewState,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from monitoring import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)
from protocols import (
    LiveCompleteDecision,
    LiveCompleteExecutionEnvelope,
    LiveCompleteGateGroupSummary,
    LiveCompleteRunState,
    LiveCompleteRunSummary,
    LiveCompleteVerdict,
    LiveLightVerdict,
    build_live_complete_dashboard_section,
    build_live_complete_projection,
)


def _artifact(kind: DashboardArtifactKind, hash_seed: str) -> DashboardArtifactTransferManifest:
    return DashboardArtifactTransferManifest(
        artifact_hash=hash_seed * 64,
        artifact_kind=kind,
        artifact_id=f"{kind.value}-1",
        lineage_version="a.v1.0.r1",
        source_ref=f"exports/{kind.value}.json",
    )


def _recovery_report() -> VpsRecoveryReadinessReport:
    return VpsRecoveryReadinessReport(
        report_id="recovery-1",
        runtime_mode=RuntimeMode.LIVE,
        deployment_state=DeploymentState.LIVE_COMPLETE,
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=VpsRecoveryCheckStatus.PASSED,
            ),
        ),
        eligible_to_trade=True,
    )


def _queue_snapshot() -> DashboardCommandQueueSnapshot:
    return DashboardCommandQueueSnapshot(
        queue_dir_ref="build/queue",
        request_dir_ref="build/queue/requests",
        ack_dir_ref="build/queue/acks",
        result_dir_ref="build/queue/results",
        queue_status=DashboardCommandQueueStatus.HEALTHY,
        pending_request_count=1,
        accepted_ack_count=1,
        completed_result_count=1,
        writable=True,
        drainable=True,
        healthy=True,
    )


def _artifact_surfaces() -> tuple[
    tuple[ArtifactRuntimeVisibilityProjection, ...],
    tuple[ArtifactThresholdConsumerProjection, ...],
    tuple[ArtifactComparisonProjection, ...],
    ArtifactVerdictBundleProjection,
]:
    return (
        (
            ArtifactRuntimeVisibilityProjection(
                slot="active",
                artifact_kind="ml_model_artifact",
                artifact_id="ml-model-artifact-1",
                artifact_hash="a" * 64,
                lineage_version="a.v1.0.r1",
                feature_hash="f" * 64,
                calibration_version="calib.v1",
                review_state="approved",
                validation_status="accepted",
                pair_universe_count=2,
                feature_count=8,
                forecast_target_class="net_return",
                forecast_horizon_class="intraday",
                bet_structure="single_decision",
                top_feature_names_ref="exports/ml_features.json",
            ),
            ArtifactRuntimeVisibilityProjection(
                slot="shadow_challenger",
                artifact_kind="ml_model_artifact",
                artifact_id="ml-model-artifact-2",
                artifact_hash="c" * 64,
                lineage_version="a.v1.0.r2",
                review_state="pending",
                validation_status="accepted",
                shadow_only=True,
                influence_detail="shadow_only / non_influential",
                summary_ref="exports/ml_challenger_summary.json",
            ),
        ),
        (
            ArtifactThresholdConsumerProjection(
                threshold_id="THR-X03",
                threshold_family="execution_runtime",
                consumer_id="rate_limiter",
                consumer_interface="quota_ratio_ceiling",
                method="quota_ratio_ceiling_v1",
                unit="quota_ratio",
                current_value=0.8,
                threshold_review_status="ready",
                threshold_fit_ready=True,
                source_ref="exports/local_lab_execution_runtime_projection.json",
            ),
        ),
        (
            ArtifactComparisonProjection(
                champion_artifact_id="ml-model-artifact-1",
                challenger_artifact_id="ml-model-artifact-2",
                event_count=7,
                expected_gain_delta_mean=0.00021,
                expected_ce_delta_mean=0.00018,
                halal_eligible_event_count=5,
                halal_excluded_event_count=2,
                sharia_policy_version="sharia_policy_v1",
                comparison_status="shadow_ready",
            ),
        ),
        ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=1,
            ready_family_count=1,
            ml_comparison_status="shadow_ready",
            evidence_ref="exports/shadow_verdict_bundle.json",
        ),
    )


def _summary() -> LiveCompleteRunSummary:
    visibility, threshold_consumers, comparisons, verdict_bundle = _artifact_surfaces()
    recovery = _recovery_report()
    return LiveCompleteRunSummary(
        run_id="live-complete-run-1",
        correlation_id="corr-live-complete",
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
            selected_pairs=("BTCUSDT", "ETHUSDT"),
            allowed_actions=("set_halted", "request_export_active_ml_artifact"),
            forbidden_actions=("bypass_hard_blocker",),
            command_queue_enabled=True,
            active_ml_artifact_hash="a" * 64,
            active_regime_detector_artifact_hash="b" * 64,
            recovery_state="eligible_to_trade",
            autonomous_execution_enabled=False,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        command_queue_snapshot=_queue_snapshot(),
        active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
        active_regime_detector_artifact=_artifact(
            DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            "b",
        ),
        shadow_ml_challenger_artifact=_artifact(
            DashboardArtifactKind.ML_MODEL_ARTIFACT,
            "c",
        ),
        shadow_regime_detector_challenger_artifact=_artifact(
            DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            "d",
        ),
        recovery_readiness_report=recovery,
        warmup_run_summary=VpsWarmupRunSummary(
            run_id="warmup-1",
            runtime_mode=RuntimeMode.LIVE,
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE,
            phase_sequence=(VpsWarmupState.COLD_START, VpsWarmupState.ELIGIBLE_TO_TRADE),
            report=recovery,
            eligible_to_trade=True,
        ),
        gate_groups=(
            LiveCompleteGateGroupSummary(gate_id="governed_live_complete", status="passed"),
            LiveCompleteGateGroupSummary(gate_id="command_plane", status="passed"),
            LiveCompleteGateGroupSummary(gate_id="artifact_state", status="passed"),
            LiveCompleteGateGroupSummary(gate_id="recovery_warmup", status="passed"),
            LiveCompleteGateGroupSummary(gate_id="operator_surface", status="passed"),
        ),
        artifact_runtime_visibility=visibility,
        artifact_threshold_consumers=threshold_consumers,
        artifact_comparisons=comparisons,
        artifact_verdict_bundle=verdict_bundle,
    )


def test_build_live_complete_projection_returns_normalized_surface() -> None:
    projection = build_live_complete_projection(_summary())

    assert projection.status == "healthy"
    assert projection.run_state == "ready_for_complete_supervision"
    assert projection.command_queue_status == "healthy"
    assert projection.command_queue_pending_request_count == 1
    assert projection.warmup_final_state == "eligible_to_trade"
    assert projection.active_regime_detector_artifact_hash == "b" * 64
    assert projection.shadow_ml_challenger_artifact_hash == ""
    assert len(projection.artifact_runtime_visibility) == 2
    assert projection.artifact_threshold_consumers[0].threshold_id == "THR-X03"
    assert projection.artifact_comparisons[0].comparison_status == "shadow_ready"
    assert projection.artifact_comparisons[0].expected_gain_delta_mean == 0.00021
    assert projection.artifact_comparisons[0].halal_eligible_event_count == 5
    assert projection.artifact_verdict_bundle is not None
    assert projection.artifact_verdict_bundle.overall_verdict == "shadow_validated"
    assert len(projection.gate_groups) == 5


def test_build_live_complete_dashboard_section_renders_control_cards() -> None:
    section = build_live_complete_dashboard_section(_summary())

    assert section.title == "Build-17 Live Complete"
    keys = {card.key for card in section.cards}
    assert keys == {
        "live_complete_run_state",
        "live_complete_command_queue",
        "live_complete_active_artifacts",
        "live_complete_shadow_challengers",
        "live_complete_threshold_consumers",
        "live_complete_shadow_verdict_bundle",
        "live_complete_warmup",
        "live_complete_blocking_reasons",
    }
    queue_card = next(card for card in section.cards if card.key == "live_complete_command_queue")
    warmup_card = next(card for card in section.cards if card.key == "live_complete_warmup")
    challenger_card = next(
        card for card in section.cards if card.key == "live_complete_shadow_challengers"
    )
    verdict_card = next(
        card for card in section.cards if card.key == "live_complete_shadow_verdict_bundle"
    )
    assert queue_card.value == "status=healthy / pending=1"
    assert warmup_card.status == "healthy"
    assert "compare=1" in challenger_card.detail
    assert "statuses=shadow_ready" in challenger_card.detail
    assert verdict_card.value == "shadow_validated / review_for_micro_live_candidate"
    assert "configured=1 / ready=1" in verdict_card.detail
