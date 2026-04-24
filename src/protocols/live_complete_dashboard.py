"""Build-17 Complete dashboard projections for governed supervision."""

from __future__ import annotations

from monitoring import LiveCompleteGateGroupProjection, LiveCompleteProjection
from protocols.contracts_complete import LiveCompleteRunSummary
from protocols.enums import LiveCompleteRunState, LiveCompleteVerdict
from ui.contracts import DashboardCard, DashboardSection


def _status_from_summary(summary: LiveCompleteRunSummary) -> str:
    if summary.decision.verdict == LiveCompleteVerdict.BLOCKED:
        return "critical"
    if summary.decision.verdict == LiveCompleteVerdict.REVIEW_ONLY:
        return "warning"
    if summary.run_state == LiveCompleteRunState.PREPARED:
        return "info"
    return "healthy"


def build_live_complete_projection(
    summary: LiveCompleteRunSummary,
) -> LiveCompleteProjection:
    """Project a Build-17 Complete summary into the normalized supervision surface."""

    return LiveCompleteProjection(
        status=_status_from_summary(summary),
        run_state=summary.run_state.value,
        verdict=summary.decision.verdict.value,
        deployment_state=summary.deployment_state.value,
        live_light_run_id=summary.live_light_run_id,
        micro_live_run_id=summary.micro_live_run_id,
        shadow_run_id=summary.shadow_run_id,
        import_artifact_id=summary.import_artifact_id,
        import_lineage_version=summary.import_lineage_version,
        selected_pairs=summary.execution_envelope.selected_pairs,
        allowed_actions=summary.execution_envelope.allowed_actions,
        forbidden_actions=summary.execution_envelope.forbidden_actions,
        active_ml_artifact_hash=summary.execution_envelope.active_ml_artifact_hash,
        active_regime_detector_artifact_hash=(
            summary.execution_envelope.active_regime_detector_artifact_hash
        ),
        command_queue_status=""
        if summary.command_queue_snapshot is None
        else summary.command_queue_snapshot.queue_status.value,
        command_queue_pending_request_count=0
        if summary.command_queue_snapshot is None
        else summary.command_queue_snapshot.pending_request_count,
        command_queue_ambiguous_pending_count=0
        if summary.command_queue_snapshot is None
        else summary.command_queue_snapshot.ambiguous_pending_count,
        recovery_state=summary.execution_envelope.recovery_state,
        recovery_eligible_to_trade=False
        if summary.recovery_readiness_report is None
        else summary.recovery_readiness_report.eligible_to_trade,
        warmup_final_state="cold_start"
        if summary.warmup_run_summary is None
        else summary.warmup_run_summary.final_state.value,
        warmup_eligible_to_trade=False
        if summary.warmup_run_summary is None
        else summary.warmup_run_summary.eligible_to_trade,
        blocking_reasons=summary.decision.blocking_reasons,
        gate_groups=tuple(
            LiveCompleteGateGroupProjection(
                gate_id=group.gate_id,
                status=group.status,
                reasons=group.reasons,
            )
            for group in summary.gate_groups
        ),
    )


def build_live_complete_dashboard_section(
    summary: LiveCompleteRunSummary,
) -> DashboardSection:
    """Project one Build-17 summary into a governed Complete dashboard section."""

    projection = build_live_complete_projection(summary)
    return DashboardSection(
        title="Build-17 Live Complete",
        cards=(
            DashboardCard(
                key="live_complete_run_state",
                label="Run State",
                value=projection.run_state,
                status=projection.status,
                detail=f"verdict={projection.verdict} / deployment={projection.deployment_state}",
            ),
            DashboardCard(
                key="live_complete_command_queue",
                label="Command Queue",
                value=(
                    f"status={projection.command_queue_status or 'not_configured'} / "
                    f"pending={projection.command_queue_pending_request_count}"
                ),
                status="warning"
                if projection.command_queue_ambiguous_pending_count
                else projection.status,
                detail=(
                    f"ambiguous={projection.command_queue_ambiguous_pending_count} / "
                    f"allowed={len(projection.allowed_actions)} / forbidden={len(projection.forbidden_actions)}"
                ),
            ),
            DashboardCard(
                key="live_complete_active_artifacts",
                label="Active Artifacts",
                value=(
                    f"ml={'set' if projection.active_ml_artifact_hash else 'none'} / "
                    f"regime={'set' if projection.active_regime_detector_artifact_hash else 'none'}"
                ),
                status="info",
                detail=f"lineage={projection.import_lineage_version}",
            ),
            DashboardCard(
                key="live_complete_warmup",
                label="Warmup / Recovery",
                value=(
                    f"recovery={projection.recovery_state} / warmup={projection.warmup_final_state}"
                ),
                status="healthy" if projection.warmup_eligible_to_trade else "warning",
                detail=f"eligible_to_trade={projection.warmup_eligible_to_trade}",
            ),
            DashboardCard(
                key="live_complete_blocking_reasons",
                label="Blocking Reasons",
                value=str(len(projection.blocking_reasons)),
                status="critical" if projection.blocking_reasons else "healthy",
                detail=", ".join(projection.blocking_reasons) or "No blocking reason",
            ),
        ),
    )


__all__ = [
    "build_live_complete_projection",
    "build_live_complete_dashboard_section",
]
