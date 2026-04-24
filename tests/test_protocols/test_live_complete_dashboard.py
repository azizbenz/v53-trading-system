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


def _summary() -> LiveCompleteRunSummary:
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
        eligible_to_trade=True,
    )
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
        active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
        active_regime_detector_artifact=_artifact(
            DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            "b",
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
    )


def test_build_live_complete_projection_returns_normalized_surface() -> None:
    projection = build_live_complete_projection(_summary())

    assert projection.status == "healthy"
    assert projection.run_state == "ready_for_complete_supervision"
    assert projection.command_queue_status == "healthy"
    assert projection.command_queue_pending_request_count == 1
    assert projection.warmup_final_state == "eligible_to_trade"
    assert projection.active_regime_detector_artifact_hash == "b" * 64
    assert len(projection.gate_groups) == 5


def test_build_live_complete_dashboard_section_renders_control_cards() -> None:
    section = build_live_complete_dashboard_section(_summary())

    assert section.title == "Build-17 Live Complete"
    keys = {card.key for card in section.cards}
    assert keys == {
        "live_complete_run_state",
        "live_complete_command_queue",
        "live_complete_active_artifacts",
        "live_complete_warmup",
        "live_complete_blocking_reasons",
    }
    queue_card = next(card for card in section.cards if card.key == "live_complete_command_queue")
    warmup_card = next(card for card in section.cards if card.key == "live_complete_warmup")
    assert queue_card.value == "status=healthy / pending=1"
    assert warmup_card.status == "healthy"
