"""Build-17 Complete control gate and typed supervision builder."""

from __future__ import annotations

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DeploymentState,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
    VpsWarmupState,
)

from .contracts import LiveLightRunSummary
from .contracts_complete import (
    LiveCompleteDecision,
    LiveCompleteExecutionEnvelope,
    LiveCompleteGateGroupSummary,
    LiveCompleteInput,
    LiveCompleteRunSummary,
    build_live_complete_input_defaults,
)
from .enums import LiveCompleteRunState, LiveCompleteVerdict, LiveLightRunState, LiveLightVerdict


_REQUIRED_ALLOWED_ACTIONS = frozenset(
    {
        "set_halted",
        "rollback_to_light",
        "suspend_pair",
        "request_pair_resume",
        "suspend_engine",
        "request_engine_resume",
        "request_upload_ml_artifact",
        "request_upload_regime_detector_artifact",
        "request_export_active_ml_artifact",
        "request_export_active_regime_detector_artifact",
        "request_export_regime_detector_shadow_audit_bundle",
        "view_complete_gates",
    }
)
_REQUIRED_FORBIDDEN_ACTIONS = frozenset(
    {"modify_risk_caps", "inject_unversioned_config", "bypass_hard_blocker"}
)


def build_live_complete_input_from_live_light(
    live_light_summary: LiveLightRunSummary,
    *,
    complete_gates: tuple[str, ...] = (),
    selected_pairs: tuple[str, ...] = (),
    available_pairs: tuple[str, ...] = (),
    allowed_actions: tuple[str, ...] = (),
    forbidden_actions: tuple[str, ...] = (),
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None,
    active_ml_artifact: DashboardArtifactTransferManifest | None = None,
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None,
    recovery_readiness_report: VpsRecoveryReadinessReport | None = None,
    warmup_run_summary: VpsWarmupRunSummary | None = None,
) -> LiveCompleteInput:
    """Build a governed Build-17 input from Build-13 Live-Light outputs."""

    return LiveCompleteInput(
        **build_live_complete_input_defaults(live_light_summary),
        deployment_state=DeploymentState.LIVE_COMPLETE,
        complete_gates=complete_gates,
        selected_pairs=selected_pairs,
        available_pairs=available_pairs,
        allowed_actions=allowed_actions,
        forbidden_actions=forbidden_actions,
        command_queue_snapshot=command_queue_snapshot,
        active_ml_artifact=active_ml_artifact,
        active_regime_detector_artifact=active_regime_detector_artifact,
        recovery_readiness_report=recovery_readiness_report,
        warmup_run_summary=warmup_run_summary,
    )


def _governance_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    blocked: list[str] = []
    review: list[str] = []
    if live_complete_input.live_light_run_state != LiveLightRunState.READY_TO_EXECUTE_SMALL:
        blocked.append("Build-17 Complete requires Build-13 Live-Light to be ready_to_execute_small")
    if live_complete_input.live_light_verdict == LiveLightVerdict.BLOCKED:
        blocked.append("Build-17 Complete cannot open while Build-13 Live-Light is blocked")
    if live_complete_input.live_light_verdict == LiveLightVerdict.DRY_RUN_ONLY:
        review.append("Build-17 Complete remains review_only while Build-13 stays dry_run_only")
    return tuple(blocked), tuple(review)


def _command_plane_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if live_complete_input.command_queue_snapshot is None:
        return ("Build-17 Complete requires a typed dashboard command queue snapshot",), ()
    blocked: list[str] = []
    review: list[str] = []
    if not live_complete_input.command_queue_snapshot.writable:
        blocked.append("Build-17 Complete requires a writable dashboard command queue")
    if not live_complete_input.command_queue_snapshot.drainable:
        blocked.append("Build-17 Complete requires a drainable dashboard command queue")
    if live_complete_input.command_queue_snapshot.ambiguous_pending_count:
        blocked.append("Build-17 Complete refuses ambiguous pending dashboard commands")
    if live_complete_input.command_queue_snapshot.failed_result_count:
        review.append("dashboard command queue contains failed results that require review")
    if live_complete_input.command_queue_snapshot.rejected_ack_count:
        review.append("dashboard command queue contains rejected acknowledgements")
    return tuple(blocked), tuple(review)


def _artifact_state_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    manifests = tuple(
        manifest
        for manifest in (
            live_complete_input.active_ml_artifact,
            live_complete_input.active_regime_detector_artifact,
        )
        if manifest is not None
    )
    if not manifests:
        return (), ("Build-17 Complete has no active governed artifact state attached",)
    blocked = [
        "Build-17 Complete requires active governed artifacts to carry artifact_hash"
        for manifest in manifests
        if not manifest.artifact_hash
    ]
    review = [
        "Build-17 Complete active artifact is missing lineage_version"
        for manifest in manifests
        if not manifest.lineage_version
    ]
    return tuple(blocked), tuple(review)


def _recovery_warmup_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if live_complete_input.recovery_readiness_report is None:
        return ("Build-17 Complete requires a VPS recovery readiness report",), ()
    if live_complete_input.warmup_run_summary is None:
        return ("Build-17 Complete requires a VPS warmup run summary",), ()
    blocked: list[str] = list(live_complete_input.recovery_readiness_report.blocking_reasons)
    review: list[str] = []
    if live_complete_input.warmup_run_summary.final_state == VpsWarmupState.BLOCKED:
        blocked.append("Build-17 Complete refuses while VPS warmup is blocked")
    elif live_complete_input.warmup_run_summary.final_state == VpsWarmupState.WARMUP_SHADOW_ONLY:
        review.append("Build-17 Complete stays review_only while VPS remains warmup_shadow_only")
    return tuple(dict.fromkeys(blocked)), tuple(dict.fromkeys(review))


def _operator_surface_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    allowed = set(live_complete_input.allowed_actions)
    forbidden = set(live_complete_input.forbidden_actions)
    blocked: list[str] = []
    if not live_complete_input.halt_ready:
        blocked.append("Build-17 Complete requires halt_ready=True")
    missing_allowed = sorted(_REQUIRED_ALLOWED_ACTIONS - allowed)
    if missing_allowed:
        blocked.append(
            f"Build-17 Complete missing required allowed_actions: {', '.join(missing_allowed)}"
        )
    missing_forbidden = sorted(_REQUIRED_FORBIDDEN_ACTIONS - forbidden)
    if missing_forbidden:
        blocked.append(
            f"Build-17 Complete missing required forbidden_actions: {', '.join(missing_forbidden)}"
        )
    review = () if live_complete_input.complete_gates else (
        "Build-17 Complete has no explicit gate evidence attached",
    )
    return tuple(blocked), review


def _build_gate_group(
    gate_id: str,
    *,
    blocked: tuple[str, ...],
    review: tuple[str, ...],
) -> LiveCompleteGateGroupSummary:
    if blocked:
        return LiveCompleteGateGroupSummary(
            gate_id=gate_id, status="blocked", reasons=blocked
        )
    if review:
        return LiveCompleteGateGroupSummary(
            gate_id=gate_id, status="review_only", reasons=review
        )
    return LiveCompleteGateGroupSummary(gate_id=gate_id, status="passed")


def run_live_complete_gate(
    live_complete_input: LiveCompleteInput,
    *,
    run_id: str | None = None,
) -> LiveCompleteRunSummary:
    """Run the Build-17 Complete control gate without opening autonomous live execution."""

    governance_blocked, governance_review = _governance_reasons(live_complete_input)
    command_blocked, command_review = _command_plane_reasons(live_complete_input)
    artifact_blocked, artifact_review = _artifact_state_reasons(live_complete_input)
    recovery_blocked, recovery_review = _recovery_warmup_reasons(live_complete_input)
    operator_blocked, operator_review = _operator_surface_reasons(live_complete_input)
    gate_groups = (
        _build_gate_group(
            "governed_live_complete",
            blocked=governance_blocked,
            review=governance_review,
        ),
        _build_gate_group("command_plane", blocked=command_blocked, review=command_review),
        _build_gate_group("artifact_state", blocked=artifact_blocked, review=artifact_review),
        _build_gate_group(
            "recovery_warmup",
            blocked=recovery_blocked,
            review=recovery_review,
        ),
        _build_gate_group(
            "operator_surface",
            blocked=operator_blocked,
            review=operator_review,
        ),
    )
    hard_blocking_reasons = (
        governance_blocked
        + command_blocked
        + artifact_blocked
        + recovery_blocked
        + operator_blocked
    )
    review_reasons = (
        governance_review
        + command_review
        + artifact_review
        + recovery_review
        + operator_review
    )
    if hard_blocking_reasons:
        decision = LiveCompleteDecision(
            allowed_complete_supervision=False,
            verdict=LiveCompleteVerdict.BLOCKED,
            review_state="needs_revision",
            blocking_reasons=tuple(dict.fromkeys(hard_blocking_reasons + review_reasons)),
            manual_review_required=True,
        )
        run_state = LiveCompleteRunState.BLOCKED
    elif review_reasons:
        decision = LiveCompleteDecision(
            allowed_complete_supervision=False,
            verdict=LiveCompleteVerdict.REVIEW_ONLY,
            review_state="pending",
            blocking_reasons=tuple(dict.fromkeys(review_reasons)),
            manual_review_required=True,
        )
        run_state = LiveCompleteRunState.PREPARED
    else:
        decision = LiveCompleteDecision(
            allowed_complete_supervision=True,
            verdict=LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION,
            review_state="approved",
            blocking_reasons=(),
            manual_review_required=False,
        )
        run_state = LiveCompleteRunState.READY_FOR_COMPLETE_SUPERVISION
    execution_envelope = LiveCompleteExecutionEnvelope(
        envelope_id=f"{live_complete_input.correlation_id}.complete_envelope",
        import_artifact_id=live_complete_input.import_artifact_id,
        import_lineage_version=live_complete_input.import_lineage_version,
        deployment_state=live_complete_input.deployment_state,
        selected_pairs=live_complete_input.selected_pairs,
        allowed_actions=live_complete_input.allowed_actions,
        forbidden_actions=live_complete_input.forbidden_actions,
        command_queue_enabled=live_complete_input.command_queue_snapshot is not None,
        active_ml_artifact_hash=""
        if live_complete_input.active_ml_artifact is None
        else live_complete_input.active_ml_artifact.artifact_hash,
        active_regime_detector_artifact_hash=""
        if live_complete_input.active_regime_detector_artifact is None
        else live_complete_input.active_regime_detector_artifact.artifact_hash,
        recovery_state="cold_start"
        if live_complete_input.warmup_run_summary is None
        else live_complete_input.warmup_run_summary.final_state.value,
        halt_guard_required=True,
        autonomous_execution_enabled=False,
    )
    return LiveCompleteRunSummary(
        run_id=run_id or f"{live_complete_input.correlation_id}.live_complete",
        correlation_id=live_complete_input.correlation_id,
        run_state=run_state,
        deployment_state=live_complete_input.deployment_state,
        live_light_run_id=live_complete_input.live_light_run_id,
        micro_live_run_id=live_complete_input.micro_live_run_id,
        shadow_run_id=live_complete_input.shadow_run_id,
        live_light_verdict=live_complete_input.live_light_verdict,
        decision=decision,
        execution_envelope=execution_envelope,
        import_artifact_id=live_complete_input.import_artifact_id,
        import_lineage_version=live_complete_input.import_lineage_version,
        command_queue_snapshot=live_complete_input.command_queue_snapshot,
        active_ml_artifact=live_complete_input.active_ml_artifact,
        active_regime_detector_artifact=live_complete_input.active_regime_detector_artifact,
        recovery_readiness_report=live_complete_input.recovery_readiness_report,
        warmup_run_summary=live_complete_input.warmup_run_summary,
        gate_groups=gate_groups,
    )


__all__ = [
    "build_live_complete_input_from_live_light",
    "run_live_complete_gate",
]
