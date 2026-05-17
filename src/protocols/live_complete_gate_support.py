"""Support helpers for the Build-17 Complete control gate."""

from __future__ import annotations

from interface_contracts import VpsWarmupState

from .contracts_complete import (
    LiveCompleteDecision,
    LiveCompleteExecutionEnvelope,
    LiveCompleteGateGroupSummary,
    LiveCompleteInput,
    LiveCompleteAllowedAction,
    LiveCompleteForbiddenAction,
)
from .enums import LiveCompleteRunState, LiveCompleteVerdict, LiveLightRunState, LiveLightVerdict

_REQUIRED_ALLOWED_ACTIONS = frozenset(
    {
        LiveCompleteAllowedAction.SET_HALTED,
        LiveCompleteAllowedAction.ROLLBACK_TO_LIGHT,
        LiveCompleteAllowedAction.SUSPEND_PAIR,
        LiveCompleteAllowedAction.REQUEST_PAIR_RESUME,
        LiveCompleteAllowedAction.SUSPEND_ENGINE,
        LiveCompleteAllowedAction.REQUEST_ENGINE_RESUME,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_ML_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_CLEAR_SHADOW_ML_CHALLENGER_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_CLEAR_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
        LiveCompleteAllowedAction.REQUEST_EXPORT_SHADOW_ML_ARTIFACT_COMPARISON_EVIDENCE,
        LiveCompleteAllowedAction.REQUEST_EXPORT_SHADOW_REGIME_DETECTOR_ARTIFACT_COMPARISON_EVIDENCE,
        LiveCompleteAllowedAction.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE,
        LiveCompleteAllowedAction.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
        LiveCompleteAllowedAction.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
        LiveCompleteAllowedAction.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        LiveCompleteAllowedAction.REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY,
        LiveCompleteAllowedAction.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
        LiveCompleteAllowedAction.VIEW_COMPLETE_GATES,
    }
)
_REQUIRED_FORBIDDEN_ACTIONS = frozenset(
    {
        LiveCompleteForbiddenAction.MODIFY_RISK_CAPS,
        LiveCompleteForbiddenAction.INJECT_UNVERSIONED_CONFIG,
        LiveCompleteForbiddenAction.BYPASS_HARD_BLOCKER,
    }
)


def governance_reasons(
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


def command_plane_reasons(
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


def artifact_state_reasons(
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
    blocked = tuple(
        "Build-17 Complete requires active governed artifacts to carry artifact_hash"
        for manifest in manifests
        if not manifest.artifact_hash
    )
    review = tuple(
        "Build-17 Complete active artifact is missing lineage_version"
        for manifest in manifests
        if not manifest.lineage_version
    )
    return blocked, review


def recovery_warmup_reasons(
    live_complete_input: LiveCompleteInput,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if live_complete_input.recovery_readiness_report is None:
        return ("Build-17 Complete requires a VPS recovery readiness report",), ()
    if live_complete_input.warmup_run_summary is None:
        return ("Build-17 Complete requires a VPS warmup run summary",), ()
    blocked = list(live_complete_input.recovery_readiness_report.blocking_reasons)
    review: list[str] = []
    if live_complete_input.warmup_run_summary.final_state == VpsWarmupState.BLOCKED:
        blocked.append("Build-17 Complete refuses while VPS warmup is blocked")
    elif (
        live_complete_input.warmup_run_summary.final_state
        == VpsWarmupState.WARMUP_SHADOW_ONLY
    ):
        review.append("Build-17 Complete stays review_only while VPS remains warmup_shadow_only")
    return tuple(dict.fromkeys(blocked)), tuple(dict.fromkeys(review))


def operator_surface_reasons(
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
            "Build-17 Complete missing required allowed_actions: "
            f"{', '.join(action.value for action in missing_allowed)}"
        )
    missing_forbidden = sorted(_REQUIRED_FORBIDDEN_ACTIONS - forbidden)
    if missing_forbidden:
        blocked.append(
            "Build-17 Complete missing required forbidden_actions: "
            f"{', '.join(action.value for action in missing_forbidden)}"
        )
    review = () if live_complete_input.complete_gates else (
        "Build-17 Complete has no explicit gate evidence attached",
    )
    return tuple(blocked), review


def build_gate_group(
    gate_id: str,
    *,
    blocked: tuple[str, ...],
    review: tuple[str, ...],
) -> LiveCompleteGateGroupSummary:
    if blocked:
        return LiveCompleteGateGroupSummary(
            gate_id=gate_id,
            status="blocked",
            reasons=blocked,
        )
    if review:
        return LiveCompleteGateGroupSummary(
            gate_id=gate_id,
            status="review_only",
            reasons=review,
        )
    return LiveCompleteGateGroupSummary(gate_id=gate_id, status="passed")


def build_decision(
    *,
    governance_blocked: tuple[str, ...],
    governance_review: tuple[str, ...],
    command_blocked: tuple[str, ...],
    command_review: tuple[str, ...],
    artifact_blocked: tuple[str, ...],
    artifact_review: tuple[str, ...],
    recovery_blocked: tuple[str, ...],
    recovery_review: tuple[str, ...],
    operator_blocked: tuple[str, ...],
    operator_review: tuple[str, ...],
) -> tuple[LiveCompleteDecision, LiveCompleteRunState]:
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
        return (
            LiveCompleteDecision(
                allowed_complete_supervision=False,
                verdict=LiveCompleteVerdict.BLOCKED,
                review_state="needs_revision",
                blocking_reasons=tuple(dict.fromkeys(hard_blocking_reasons + review_reasons)),
                manual_review_required=True,
            ),
            LiveCompleteRunState.BLOCKED,
        )
    if review_reasons:
        return (
            LiveCompleteDecision(
                allowed_complete_supervision=False,
                verdict=LiveCompleteVerdict.REVIEW_ONLY,
                review_state="pending",
                blocking_reasons=tuple(dict.fromkeys(review_reasons)),
                manual_review_required=True,
            ),
            LiveCompleteRunState.PREPARED,
        )
    return (
        LiveCompleteDecision(
            allowed_complete_supervision=True,
            verdict=LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION,
            review_state="approved",
            blocking_reasons=(),
            manual_review_required=False,
        ),
        LiveCompleteRunState.READY_FOR_COMPLETE_SUPERVISION,
    )


def build_execution_envelope(
    live_complete_input: LiveCompleteInput,
) -> LiveCompleteExecutionEnvelope:
    return LiveCompleteExecutionEnvelope(
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
        shadow_ml_challenger_artifact_hash=""
        if live_complete_input.shadow_ml_challenger_artifact is None
        else live_complete_input.shadow_ml_challenger_artifact.artifact_hash,
        shadow_regime_detector_challenger_artifact_hash=""
        if live_complete_input.shadow_regime_detector_challenger_artifact is None
        else live_complete_input.shadow_regime_detector_challenger_artifact.artifact_hash,
        recovery_state="cold_start"
        if live_complete_input.warmup_run_summary is None
        else live_complete_input.warmup_run_summary.final_state.value,
        halt_guard_required=True,
        autonomous_execution_enabled=False,
    )


__all__ = [
    "artifact_state_reasons",
    "build_decision",
    "build_execution_envelope",
    "build_gate_group",
    "command_plane_reasons",
    "governance_reasons",
    "operator_surface_reasons",
    "recovery_warmup_reasons",
]
