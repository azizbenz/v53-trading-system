"""Build-12 Micro-live supervision helpers for the technical interface."""

from __future__ import annotations

from monitoring import MicroLiveProjection
from protocols.contracts import MicroLiveRunSummary
from protocols.enums import MicroLiveRunState, MicroLiveVerdict
from ui.contracts import DashboardCard, DashboardSection


def _status_from_summary(summary: MicroLiveRunSummary) -> str:
    if summary.decision.verdict == MicroLiveVerdict.BLOCKED:
        return "critical"
    if summary.decision.verdict == MicroLiveVerdict.DRY_RUN_ONLY:
        return "warning"
    if summary.run_state == MicroLiveRunState.PREPARED:
        return "info"
    return "healthy"


def _operator_safing_value(summary: MicroLiveRunSummary) -> str:
    request = summary.operator_safing_request
    if request is None:
        return "none"
    if request.target_runtime_mode is None:
        return request.action.value
    return f"{request.action.value} -> {request.target_runtime_mode.value}"


def _operator_safing_status(summary: MicroLiveRunSummary) -> str:
    request = summary.operator_safing_request
    if request is None:
        return "info"
    if request.action.value == "set_halted":
        return "critical"
    return "warning"


def build_micro_live_projection(summary: MicroLiveRunSummary) -> MicroLiveProjection:
    """Project a governed Build-12 summary into the normalized supervision surface."""

    return MicroLiveProjection(
        status=_status_from_summary(summary),
        run_state=summary.run_state.value,
        verdict=summary.decision.verdict.value,
        shadow_run_id=summary.shadow_run_id,
        shadow_verdict=summary.shadow_verdict.value,
        allowed_to_probe=summary.decision.allowed_to_probe,
        requested_total_notional_usdt=summary.execution_plan.requested_total_notional_usdt,
        approved_total_notional_usdt=summary.decision.approved_total_notional_usdt,
        approved_pair_notional_usdt=summary.decision.approved_pair_notional_usdt,
        order_probe_limit=summary.execution_plan.order_probe_limit,
        planned_pairs=summary.execution_plan.planned_pairs,
        planned_engines=summary.execution_plan.planned_engines,
        import_artifact_id=summary.import_artifact_id,
        import_lineage_version=summary.import_lineage_version,
        execution_runtime_projection_ref=summary.execution_runtime_projection_ref,
        execution_runtime_projection_status=summary.execution_runtime_projection_status,
        execution_runtime_projection_ready=summary.execution_runtime_projection_ready,
        execution_runtime_projection_consumer_count=(
            summary.execution_runtime_projection_consumer_count
        ),
        execution_runtime_projection_ready_consumer_count=(
            summary.execution_runtime_projection_ready_consumer_count
        ),
        execution_runtime_projection_partial_consumer_count=(
            summary.execution_runtime_projection_partial_consumer_count
        ),
        execution_runtime_projection_blocked_consumer_count=(
            summary.execution_runtime_projection_blocked_consumer_count
        ),
        observability_ready=summary.observability_ready,
        halt_ready=summary.halt_ready,
        onboarding_ready=summary.onboarding_ready,
        operator_safing_action=(
            summary.operator_safing_request.action.value
            if summary.operator_safing_request is not None
            else ""
        ),
        operator_safing_target_runtime_mode=(
            summary.operator_safing_request.target_runtime_mode.value
            if summary.operator_safing_request is not None
            and summary.operator_safing_request.target_runtime_mode is not None
            else ""
        ),
        operator_safing_reason=(
            summary.operator_safing_request.reason
            if summary.operator_safing_request is not None
            else ""
        ),
        blocking_reasons=summary.decision.blocking_reasons,
    )


def build_micro_live_dashboard_section(summary: MicroLiveRunSummary) -> DashboardSection:
    """Project a minimal Build-12 run summary into dashboard cards."""

    projection = build_micro_live_projection(summary)
    blocking_detail = (
        ", ".join(projection.blocking_reasons)
        if projection.blocking_reasons
        else "No blocking reason"
    )
    return DashboardSection(
        title="Build-12 Micro-live",
        cards=(
            DashboardCard(
                key="micro_live_run_state",
                label="Run State",
                value=projection.run_state,
                status=projection.status,
                detail=f"shadow_run={projection.shadow_run_id}",
            ),
            DashboardCard(
                key="micro_live_verdict",
                label="Probe Verdict",
                value=projection.verdict,
                status=projection.status,
                detail=f"shadow_verdict={projection.shadow_verdict}",
            ),
            DashboardCard(
                key="micro_live_budget",
                label="Budget",
                value=(
                    f"approved={projection.approved_total_notional_usdt:.2f} / "
                    f"pair={projection.approved_pair_notional_usdt:.2f}"
                ),
                status=projection.status,
                detail=f"requested={projection.requested_total_notional_usdt:.2f}",
            ),
            DashboardCard(
                key="micro_live_surface",
                label="Probe Surface",
                value=(
                    f"pairs={len(projection.planned_pairs)} / "
                    f"engines={len(projection.planned_engines)} / "
                    f"orders={projection.order_probe_limit}"
                ),
                status="info" if projection.planned_pairs or projection.planned_engines else projection.status,
                detail=", ".join(projection.planned_pairs) or "No probe surface planned",
            ),
            DashboardCard(
                key="micro_live_guardrails",
                label="Guardrails",
                value=(
                    f"obs={'ready' if projection.observability_ready else 'missing'} / "
                    f"halt={'ready' if projection.halt_ready else 'missing'} / "
                    f"onboarding={'ready' if projection.onboarding_ready else 'missing'}"
                ),
                status=(
                    "healthy"
                    if projection.observability_ready and projection.halt_ready and projection.onboarding_ready
                    else "critical"
                ),
                detail=(
                    f"{projection.import_lineage_version} / "
                    f"exec_proj={projection.execution_runtime_projection_status} / "
                    f"ready={projection.execution_runtime_projection_ready_consumer_count} / "
                    f"partial={projection.execution_runtime_projection_partial_consumer_count} / "
                    f"blocked={projection.execution_runtime_projection_blocked_consumer_count}"
                ),
            ),
            DashboardCard(
                key="micro_live_safing_request",
                label="Safing Request",
                value=_operator_safing_value(summary),
                status=_operator_safing_status(summary),
                detail=(
                    projection.operator_safing_reason
                    or "No manual safing request projected"
                ),
            ),
            DashboardCard(
                key="micro_live_blocking_reasons",
                label="Blocking Reasons",
                value=str(len(projection.blocking_reasons)),
                status="critical" if projection.blocking_reasons else "healthy",
                detail=blocking_detail,
            ),
        ),
    )


__all__ = [
    "build_micro_live_projection",
    "build_micro_live_dashboard_section",
]
