"""Build-17 Complete control gate and typed supervision builder."""

from __future__ import annotations

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DeploymentState,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)
from monitoring.contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)

from .contracts import LiveLightRunSummary
from .contracts_complete import (
    LiveCompleteAllowedAction,
    LiveCompleteForbiddenAction,
    LiveCompleteInput,
    LiveCompleteRunSummary,
    build_live_complete_input_defaults,
)
from .live_complete_gate_support import (
    artifact_state_reasons,
    build_decision,
    build_execution_envelope,
    build_gate_group,
    command_plane_reasons,
    governance_reasons,
    operator_surface_reasons,
    recovery_warmup_reasons,
)


def build_live_complete_input_from_live_light(
    live_light_summary: LiveLightRunSummary,
    *,
    complete_gates: tuple[str, ...] = (),
    selected_pairs: tuple[str, ...] = (),
    available_pairs: tuple[str, ...] = (),
    allowed_actions: tuple[LiveCompleteAllowedAction, ...] = (),
    forbidden_actions: tuple[LiveCompleteForbiddenAction, ...] = (),
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None,
    active_ml_artifact: DashboardArtifactTransferManifest | None = None,
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None = (
        None
    ),
    recovery_readiness_report: VpsRecoveryReadinessReport | None = None,
    warmup_run_summary: VpsWarmupRunSummary | None = None,
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = (),
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...] = (),
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = (),
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None,
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
        shadow_ml_challenger_artifact=shadow_ml_challenger_artifact,
        shadow_regime_detector_challenger_artifact=shadow_regime_detector_challenger_artifact,
        recovery_readiness_report=recovery_readiness_report,
        warmup_run_summary=warmup_run_summary,
        artifact_runtime_visibility=artifact_runtime_visibility,
        artifact_threshold_consumers=artifact_threshold_consumers,
        artifact_comparisons=artifact_comparisons,
        artifact_verdict_bundle=artifact_verdict_bundle,
    )


def run_live_complete_gate(
    live_complete_input: LiveCompleteInput,
    *,
    run_id: str | None = None,
) -> LiveCompleteRunSummary:
    """Run the Build-17 Complete control gate without opening autonomous live execution."""

    governance_blocked, governance_review = governance_reasons(live_complete_input)
    command_blocked, command_review = command_plane_reasons(live_complete_input)
    artifact_blocked, artifact_review = artifact_state_reasons(live_complete_input)
    recovery_blocked, recovery_review = recovery_warmup_reasons(live_complete_input)
    operator_blocked, operator_review = operator_surface_reasons(live_complete_input)
    gate_groups = (
        build_gate_group(
            "governed_live_complete",
            blocked=governance_blocked,
            review=governance_review,
        ),
        build_gate_group("command_plane", blocked=command_blocked, review=command_review),
        build_gate_group("artifact_state", blocked=artifact_blocked, review=artifact_review),
        build_gate_group(
            "recovery_warmup",
            blocked=recovery_blocked,
            review=recovery_review,
        ),
        build_gate_group(
            "operator_surface",
            blocked=operator_blocked,
            review=operator_review,
        ),
    )
    decision, run_state = build_decision(
        governance_blocked=governance_blocked,
        governance_review=governance_review,
        command_blocked=command_blocked,
        command_review=command_review,
        artifact_blocked=artifact_blocked,
        artifact_review=artifact_review,
        recovery_blocked=recovery_blocked,
        recovery_review=recovery_review,
        operator_blocked=operator_blocked,
        operator_review=operator_review,
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
        execution_envelope=build_execution_envelope(live_complete_input),
        import_artifact_id=live_complete_input.import_artifact_id,
        import_lineage_version=live_complete_input.import_lineage_version,
        command_queue_snapshot=live_complete_input.command_queue_snapshot,
        active_ml_artifact=live_complete_input.active_ml_artifact,
        active_regime_detector_artifact=live_complete_input.active_regime_detector_artifact,
        shadow_ml_challenger_artifact=live_complete_input.shadow_ml_challenger_artifact,
        shadow_regime_detector_challenger_artifact=(
            live_complete_input.shadow_regime_detector_challenger_artifact
        ),
        recovery_readiness_report=live_complete_input.recovery_readiness_report,
        warmup_run_summary=live_complete_input.warmup_run_summary,
        artifact_runtime_visibility=live_complete_input.artifact_runtime_visibility,
        artifact_threshold_consumers=live_complete_input.artifact_threshold_consumers,
        artifact_comparisons=live_complete_input.artifact_comparisons,
        artifact_verdict_bundle=live_complete_input.artifact_verdict_bundle,
        gate_groups=gate_groups,
    )


__all__ = [
    "build_live_complete_input_from_live_light",
    "run_live_complete_gate",
]
