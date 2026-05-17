from __future__ import annotations

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    ProfileId,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from monitoring import (
    AlertProjection,
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
    Build9MetaProjection,
    Build9XProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from ui import CompleteDashboardSupplement, build_complete_dashboard_sections


def _payload() -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-complete-view",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LIVE,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("monitoring", "ui", "protocols"),
            active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
            live_light_status="healthy",
        ),
        portfolio=PortfolioMetrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=20.0,
            loss_capacity_used_pct=5.0,
            beta_utilization=0.2,
            capital_deployed_usdt=500.0,
            ce_net=0.001,
        ),
        build9_meta=Build9MetaProjection(
            dtr_coverage=0.9,
            dtr_status="healthy",
            cra_sterilization_rate=0.1,
            cra_alert_count=0,
            cra_status="healthy",
            break_even_state="stable",
            break_even_status="healthy",
            edge_credible_count=1,
            edge_degraded_count=0,
            edge_surveillance_count=0,
            edge_status="healthy",
        ),
        build9x=Build9XProjection(
            status="info",
            diagnostics_count=0,
            open_hypotheses=0,
            total_hypotheses=0,
            near_miss_count=0,
            replay_candidate_count=0,
            memory_record_count=0,
        ),
        replay_import=ReplayImportProjection(
            status="healthy",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v1.0.r1",
            validation_status="accepted",
            review_state="pending",
        ),
        alerts=AlertProjection(
            headline_status="healthy",
            active_alert_count=0,
            queue_backlog=0,
            stale_pair_count=0,
            backlog_stale_status="healthy",
            dtr_loss_count=0,
            log_loss_count=0,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            loss_drift_status="healthy",
        ),
    )


def _supplement() -> CompleteDashboardSupplement:
    recovery = VpsRecoveryReadinessReport(
        report_id="recovery-1",
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=VpsRecoveryCheckStatus.PASSED,
            ),
        ),
        eligible_to_trade=True,
    )
    return CompleteDashboardSupplement(
        complete_gates=("gate.shadow_to_live_complete",),
        selected_pairs=("BTCUSDT", "ETHUSDT"),
        available_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        command_queue_snapshot=DashboardCommandQueueSnapshot(
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
        shadow_ml_challenger_artifact=DashboardArtifactTransferManifest(
            artifact_hash="c" * 64,
            artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
            artifact_id="ml-shadow-1",
            source_ref="exports/ml_shadow.json",
        ),
        shadow_regime_detector_challenger_artifact=DashboardArtifactTransferManifest(
            artifact_hash="d" * 64,
            artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            artifact_id="regime-shadow-1",
            source_ref="exports/regime_shadow.json",
        ),
        artifact_runtime_visibility=(
            ArtifactRuntimeVisibilityProjection(
                slot="active",
                artifact_kind="ml_model_artifact",
                artifact_id="ml-1",
                artifact_hash="a" * 64,
                lineage_version="a.v1.0.r1",
                calibration_version="calib.v1",
                promotion_state="shadow_validated",
                review_state="approved",
                validation_status="accepted",
                pair_universe_count=3,
                feature_count=12,
                forecast_target_class="net_return",
                forecast_horizon_class="intraday",
                bet_structure="single_decision",
                feature_hash="f" * 64,
                top_feature_names_ref="exports/ml_features.json",
            ),
            ArtifactRuntimeVisibilityProjection(
                slot="shadow_challenger",
                artifact_kind="ml_model_artifact",
                artifact_id="ml-shadow-1",
                artifact_hash="c" * 64,
                lineage_version="a.v1.0.r2",
                review_state="pending",
                validation_status="accepted",
                shadow_only=True,
                influence_detail="shadow_only / non_influential",
                summary_ref="exports/ml_shadow_summary.json",
            ),
        ),
        artifact_threshold_consumers=(
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
        artifact_comparisons=(
            ArtifactComparisonProjection(
                champion_artifact_id="ml-1",
                challenger_artifact_id="ml-shadow-1",
                event_count=9,
                decision_diff_rate=0.222,
                expected_gain_delta_mean=0.00031,
                expected_cost_delta_mean=0.00008,
                expected_ce_delta_mean=0.00023,
                halal_eligible_event_count=7,
                halal_excluded_event_count=2,
                sharia_policy_version="sharia_policy_v1",
                sharia_scope_mode="pair_perimeter_with_spot_long_assumptions",
                comparison_status="shadow_ready",
                evidence_ref="exports/ml_compare.json",
            ),
        ),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=1,
            ready_family_count=1,
            ml_comparison_status="shadow_ready",
            evidence_ref="exports/shadow_verdict_bundle.json",
        ),
        recovery_readiness_report=recovery,
        warmup_run_summary=VpsWarmupRunSummary(
            run_id="warmup-1",
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE,
            phase_sequence=(VpsWarmupState.COLD_START, VpsWarmupState.ELIGIBLE_TO_TRADE),
            report=recovery,
            eligible_to_trade=True,
        ),
        active_binance_profile_id="binance-live-001",
        active_binance_environment="live",
        binance_credential_validation_status="validated",
        credential_inventory_count=1,
        operator_report_status="ready",
        operator_report_ref="build/live_complete_operator_audit_report.json",
    )


def test_build_complete_dashboard_control_plane_renders_shadow_verdict() -> None:
    sections = build_complete_dashboard_sections(_payload(), _supplement())
    control_plane = next(
        section for section in sections if section.title == "Build-17 Control Plane"
    )

    keys = {card.key for card in control_plane.cards}
    assert keys == {
        "complete_control_queue",
        "complete_control_artifacts",
        "complete_control_shadow_challengers",
        "complete_control_artifact_compare",
        "complete_control_shadow_verdict_bundle",
        "complete_control_binance_credentials",
        "complete_control_recovery",
        "complete_control_warmup",
        "complete_control_operator_report",
    }
    verdict_card = next(
        card
        for card in control_plane.cards
        if card.key == "complete_control_shadow_verdict_bundle"
    )
    assert verdict_card.value == "shadow_validated / review_for_micro_live_candidate"
    assert "ready=1 / invalid=0" in verdict_card.detail


def test_build_complete_dashboard_artifact_sections_render_compare_and_verdict() -> None:
    sections = build_complete_dashboard_sections(_payload(), _supplement())
    artifact_forecast = next(
        section for section in sections if section.title == "Forecast / Feature Visibility"
    )
    artifact_compare = next(
        section for section in sections if section.title == "Threshold Consumers & Compare"
    )
    artifact_verdict = next(
        section for section in sections if section.title == "Shadow Challenger Verdict"
    )

    assert any(card.label == "ml-1" for card in artifact_forecast.cards)
    assert any(card.key == "complete_artifact_thresholds" for card in artifact_compare.cards)
    compare_detail_card = next(
        card for card in artifact_compare.cards if card.key == "complete_artifact_compare_1"
    )
    verdict_detail_card = next(
        card for card in artifact_verdict.cards if card.key == "complete_artifact_verdict_bundle"
    )
    assert "events=9" in compare_detail_card.value
    assert "ce_delta=0.000230" in compare_detail_card.detail
    assert "gain_delta=0.000310" in compare_detail_card.detail
    assert "halal=7/2" in compare_detail_card.detail
    assert verdict_detail_card.value == "shadow_validated"
    assert "recommendation=review_for_micro_live_candidate" in verdict_detail_card.detail
