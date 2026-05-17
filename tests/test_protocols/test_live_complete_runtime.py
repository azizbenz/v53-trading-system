from __future__ import annotations

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DeploymentState,
    PromotionState,
    ReviewState,
    RuntimeMode,
    VpsRecoveryCheck,
    VpsRecoveryCheckStatus,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)
from protocols import (
    LiveCompleteAllowedAction,
    LiveCompleteForbiddenAction,
    LiveCompleteRunState,
    LiveCompleteVerdict,
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightRunState,
    LiveLightRunSummary,
    MicroLiveVerdict,
    build_live_complete_input_from_live_light,
    run_live_complete_gate,
)


def _live_light_summary(*, verdict: LiveLightDecision | None = None) -> LiveLightRunSummary:
    resolved_decision = verdict or LiveLightDecision(
        allowed_to_execute_small=True,
        verdict="allowed_to_execute_small",
        normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
        review_state=ReviewState.PENDING,
        approved_total_notional_usdt=80.0,
        approved_pair_notional_usdt=40.0,
        blocking_reasons=(),
        manual_review_required=False,
    )
    return LiveLightRunSummary(
        run_id="live-light-run-1",
        correlation_id="corr-live-complete",
        run_state=LiveLightRunState.READY_TO_EXECUTE_SMALL,
        micro_live_run_id="micro-run-1",
        shadow_run_id="shadow-run-1",
        micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
        decision=resolved_decision,
        execution_intent=LiveLightExecutionIntent(
            intent_id="intent-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            planned_engines=("engine_a", "engine_b"),
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=80.0,
            approved_pair_notional_usdt=40.0,
            execution_order_limit=3,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_ready=True,
    )


def _queue_snapshot(*, status: DashboardCommandQueueStatus) -> DashboardCommandQueueSnapshot:
    return DashboardCommandQueueSnapshot(
        queue_dir_ref="build/queue",
        request_dir_ref="build/queue/requests",
        ack_dir_ref="build/queue/acks",
        result_dir_ref="build/queue/results",
        queue_status=status,
        pending_request_count=0,
        accepted_ack_count=1,
        completed_result_count=1,
        writable=status != DashboardCommandQueueStatus.BLOCKED,
        drainable=status != DashboardCommandQueueStatus.BLOCKED,
        healthy=status == DashboardCommandQueueStatus.HEALTHY,
        blocking_reasons=()
        if status != DashboardCommandQueueStatus.BLOCKED
        else ("dashboard.command.queue.not_writable",),
    )


def _artifact(kind: DashboardArtifactKind, hash_seed: str) -> DashboardArtifactTransferManifest:
    return DashboardArtifactTransferManifest(
        artifact_hash=hash_seed * 64,
        artifact_kind=kind,
        artifact_id=f"{kind.value}-1",
        feature_set_version="lob_regime_feature_set.v2",
        feature_profile="extended_v2",
        lineage_version="a.v1.0.r1",
        source_ref=f"exports/{kind.value}.json",
    )


def _allowed_actions() -> tuple[str, ...]:
    return (
        "set_halted",
        "rollback_to_light",
        "suspend_pair",
        "request_pair_resume",
        "suspend_engine",
        "request_engine_resume",
        "request_upload_ml_artifact",
        "request_upload_regime_detector_artifact",
        "request_upload_shadow_ml_challenger_artifact",
        "request_upload_shadow_regime_detector_challenger_artifact",
        "request_clear_shadow_ml_challenger_artifact",
        "request_clear_shadow_regime_detector_challenger_artifact",
        "request_export_active_ml_artifact",
        "request_export_active_regime_detector_artifact",
        "request_export_shadow_ml_artifact_comparison_evidence",
        "request_export_shadow_regime_detector_artifact_comparison_evidence",
        "request_export_regime_detector_shadow_audit_bundle",
        "request_upload_binance_credentials_bundle",
        "request_activate_binance_credentials_profile",
        "request_export_binance_credential_inventory",
        "request_deactivate_binance_credentials_profile",
        "view_complete_gates",
    )


def _recovery_report(*, eligible: bool) -> VpsRecoveryReadinessReport:
    check_status = VpsRecoveryCheckStatus.PASSED if eligible else VpsRecoveryCheckStatus.BLOCKED
    return VpsRecoveryReadinessReport(
        report_id="recovery-1",
        runtime_mode=RuntimeMode.LIVE,
        deployment_state=DeploymentState.LIVE_COMPLETE,
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=check_status,
                reasons=() if eligible else ("artifact registry blocked",),
            ),
        ),
        eligible_to_trade=eligible,
        blocking_reasons=() if eligible else ("artifact registry blocked",),
    )


def _warmup(*, report: VpsRecoveryReadinessReport, final_state: VpsWarmupState) -> VpsWarmupRunSummary:
    return VpsWarmupRunSummary(
        run_id="warmup-1",
        runtime_mode=RuntimeMode.LIVE,
        final_state=final_state,
        phase_sequence=(VpsWarmupState.COLD_START, final_state),
        report=report,
        eligible_to_trade=final_state == VpsWarmupState.ELIGIBLE_TO_TRADE,
        blocking_reasons=report.blocking_reasons,
    )


def test_build_live_complete_input_from_live_light_maps_governed_surfaces() -> None:
    recovery = _recovery_report(eligible=True)
    warmup = _warmup(report=recovery, final_state=VpsWarmupState.ELIGIBLE_TO_TRADE)
    complete_input = build_live_complete_input_from_live_light(
        _live_light_summary(),
        complete_gates=("gate.shadow_to_live_complete",),
        selected_pairs=("BTCUSDT",),
        available_pairs=("BTCUSDT", "ETHUSDT"),
        allowed_actions=_allowed_actions(),
        forbidden_actions=("modify_risk_caps", "inject_unversioned_config", "bypass_hard_blocker"),
        command_queue_snapshot=_queue_snapshot(status=DashboardCommandQueueStatus.HEALTHY),
        active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
        active_regime_detector_artifact=_artifact(DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT, "b"),
        recovery_readiness_report=recovery,
        warmup_run_summary=warmup,
    )

    assert complete_input.runtime_mode == RuntimeMode.LIVE
    assert complete_input.deployment_state == DeploymentState.LIVE_COMPLETE
    assert complete_input.command_queue_snapshot is not None
    assert complete_input.active_ml_artifact is not None
    assert complete_input.warmup_run_summary is not None
    assert complete_input.allowed_actions[0] == LiveCompleteAllowedAction.SET_HALTED
    assert (
        complete_input.forbidden_actions[0]
        == LiveCompleteForbiddenAction.MODIFY_RISK_CAPS
    )


def test_run_live_complete_gate_allows_supervision_when_all_surfaces_are_ready() -> None:
    recovery = _recovery_report(eligible=True)
    summary = run_live_complete_gate(
        build_live_complete_input_from_live_light(
            _live_light_summary(),
            complete_gates=("gate.shadow_to_live_complete",),
            selected_pairs=("BTCUSDT",),
            available_pairs=("BTCUSDT", "ETHUSDT"),
            allowed_actions=_allowed_actions(),
            forbidden_actions=("modify_risk_caps", "inject_unversioned_config", "bypass_hard_blocker"),
            command_queue_snapshot=_queue_snapshot(status=DashboardCommandQueueStatus.HEALTHY),
            active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
            active_regime_detector_artifact=_artifact(DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT, "b"),
            recovery_readiness_report=recovery,
            warmup_run_summary=_warmup(
                report=recovery,
                final_state=VpsWarmupState.ELIGIBLE_TO_TRADE,
            ),
        )
    )

    assert summary.run_state == LiveCompleteRunState.READY_FOR_COMPLETE_SUPERVISION
    assert summary.decision.verdict == LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION
    assert summary.execution_envelope.autonomous_execution_enabled is False


def test_run_live_complete_gate_stays_review_only_during_warmup_shadow_only() -> None:
    recovery = VpsRecoveryReadinessReport(
        report_id="recovery-shadow-only",
        runtime_mode=RuntimeMode.LIVE,
        deployment_state=DeploymentState.LIVE_COMPLETE,
        checks=(
            VpsRecoveryCheck(
                check_id="artifact_registry",
                status=VpsRecoveryCheckStatus.PASSED,
            ),
        ),
        eligible_to_trade=False,
    )
    summary = run_live_complete_gate(
        build_live_complete_input_from_live_light(
            _live_light_summary(),
            complete_gates=("gate.shadow_to_live_complete",),
            selected_pairs=("BTCUSDT",),
            available_pairs=("BTCUSDT", "ETHUSDT"),
            allowed_actions=_allowed_actions(),
            forbidden_actions=("modify_risk_caps", "inject_unversioned_config", "bypass_hard_blocker"),
            command_queue_snapshot=_queue_snapshot(status=DashboardCommandQueueStatus.HEALTHY),
            active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
            active_regime_detector_artifact=_artifact(DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT, "b"),
            recovery_readiness_report=recovery,
            warmup_run_summary=_warmup(
                report=recovery,
                final_state=VpsWarmupState.WARMUP_SHADOW_ONLY,
            ),
        )
    )

    assert summary.run_state == LiveCompleteRunState.PREPARED
    assert summary.decision.verdict == LiveCompleteVerdict.REVIEW_ONLY
    assert "warmup_shadow_only" in summary.execution_envelope.recovery_state


def test_run_live_complete_gate_blocks_on_unhealthy_queue() -> None:
    recovery = _recovery_report(eligible=True)
    summary = run_live_complete_gate(
        build_live_complete_input_from_live_light(
            _live_light_summary(),
            complete_gates=("gate.shadow_to_live_complete",),
            selected_pairs=("BTCUSDT",),
            available_pairs=("BTCUSDT", "ETHUSDT"),
            allowed_actions=_allowed_actions(),
            forbidden_actions=("modify_risk_caps", "inject_unversioned_config", "bypass_hard_blocker"),
            command_queue_snapshot=_queue_snapshot(status=DashboardCommandQueueStatus.BLOCKED),
            active_ml_artifact=_artifact(DashboardArtifactKind.ML_MODEL_ARTIFACT, "a"),
            active_regime_detector_artifact=_artifact(DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT, "b"),
            recovery_readiness_report=recovery,
            warmup_run_summary=_warmup(
                report=recovery,
                final_state=VpsWarmupState.ELIGIBLE_TO_TRADE,
            ),
        )
    )

    assert summary.run_state == LiveCompleteRunState.BLOCKED
    assert summary.decision.verdict == LiveCompleteVerdict.BLOCKED
    assert any("dashboard command queue" in reason for reason in summary.decision.blocking_reasons)
