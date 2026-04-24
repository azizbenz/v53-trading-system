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


def test_build_complete_dashboard_sections_render_control_plane_cards() -> None:
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
    supplement = CompleteDashboardSupplement(
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
        recovery_readiness_report=recovery,
        warmup_run_summary=VpsWarmupRunSummary(
            run_id="warmup-1",
            final_state=VpsWarmupState.ELIGIBLE_TO_TRADE,
            phase_sequence=(VpsWarmupState.COLD_START, VpsWarmupState.ELIGIBLE_TO_TRADE),
            report=recovery,
            eligible_to_trade=True,
        ),
        operator_report_status="ready",
        operator_report_ref="build/live_complete_operator_audit_report.json",
    )

    sections = build_complete_dashboard_sections(_payload(), supplement)
    control_plane = next(
        section for section in sections if section.title == "Build-17 Control Plane"
    )

    keys = {card.key for card in control_plane.cards}
    assert keys == {
        "complete_control_queue",
        "complete_control_artifacts",
        "complete_control_recovery",
        "complete_control_warmup",
        "complete_control_operator_report",
    }
    queue_card = next(card for card in control_plane.cards if card.key == "complete_control_queue")
    operator_card = next(
        card for card in control_plane.cards if card.key == "complete_control_operator_report"
    )
    assert queue_card.value == "healthy / pending=1"
    assert operator_card.detail == "build/live_complete_operator_audit_report.json"
