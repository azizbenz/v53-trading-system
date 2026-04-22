"""Build-13 governed live supervision helpers for the technical interface."""

from __future__ import annotations

from monitoring import LiveLightGateGroupProjection, LiveLightProjection
from protocols.contracts import LiveLightRunSummary
from protocols.enums import LiveLightRunState, LiveLightVerdict
from ui.contracts import DashboardCard, DashboardSection


def _status_from_summary(summary: LiveLightRunSummary) -> str:
    if summary.decision.verdict == LiveLightVerdict.BLOCKED:
        return "critical"
    if summary.decision.verdict == LiveLightVerdict.DRY_RUN_ONLY:
        return "warning"
    if summary.run_state == LiveLightRunState.PREPARED:
        return "info"
    return "healthy"


def _operator_safing_value(summary: LiveLightRunSummary) -> str:
    request = summary.operator_safing_request
    if request is None:
        return "none"
    if request.target_runtime_mode is None:
        return request.action.value
    return f"{request.action.value} -> {request.target_runtime_mode.value}"


def _operator_safing_status(summary: LiveLightRunSummary) -> str:
    request = summary.operator_safing_request
    if request is None:
        return "info"
    if request.action.value == "set_halted":
        return "critical"
    return "warning"


def _gate_group_value(
    gate_groups: tuple[LiveLightGateGroupProjection, ...],
) -> str:
    blocked = sum(1 for group in gate_groups if group.status == "blocked")
    review_only = sum(1 for group in gate_groups if group.status == "review_only")
    passed = sum(1 for group in gate_groups if group.status == "passed")
    return f"blocked={blocked} / review={review_only} / passed={passed}"


def _gate_group_detail(
    gate_groups: tuple[LiveLightGateGroupProjection, ...],
) -> str:
    if not gate_groups:
        return "No gate group projection"
    return ", ".join(
        f"{group.gate_id}={group.status}:{len(group.reasons)}"
        for group in gate_groups
    )


def _gate_group_status(
    gate_groups: tuple[LiveLightGateGroupProjection, ...],
) -> str:
    if any(group.status == "blocked" for group in gate_groups):
        return "critical"
    if any(group.status == "review_only" for group in gate_groups):
        return "warning"
    if gate_groups:
        return "healthy"
    return "info"


def build_live_light_projection(summary: LiveLightRunSummary) -> LiveLightProjection:
    """Project a governed Build-13 summary into the normalized supervision surface."""

    return LiveLightProjection(
        status=_status_from_summary(summary),
        run_state=summary.run_state.value,
        verdict=summary.decision.verdict.value,
        micro_live_run_id=summary.micro_live_run_id,
        micro_live_verdict=summary.micro_live_verdict.value,
        allowed_to_execute_small=summary.decision.allowed_to_execute_small,
        requested_total_notional_usdt=summary.execution_intent.requested_total_notional_usdt,
        approved_total_notional_usdt=summary.decision.approved_total_notional_usdt,
        approved_pair_notional_usdt=summary.decision.approved_pair_notional_usdt,
        execution_order_limit=summary.execution_intent.execution_order_limit,
        planned_pairs=summary.execution_intent.planned_pairs,
        planned_engines=summary.execution_intent.planned_engines,
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
        execution_ready=summary.execution_ready,
        broker_ready=summary.broker_ready,
        exchange_ready=summary.exchange_ready,
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
        build14_influence_mode=summary.build14_influence_mode,
        build14_action=summary.build14_action,
        build14_severity=summary.build14_severity,
        build14_summary=summary.build14_summary,
        build14_reason_codes=summary.build14_reason_codes,
        build14_confidence_penalty_weight=summary.build14_confidence_penalty_weight,
        build14_recommended_budget_factor=summary.build14_recommended_budget_factor,
        gate_groups=tuple(
            LiveLightGateGroupProjection(
                gate_id=group.gate_id,
                status=group.status,
                reasons=group.reasons,
            )
            for group in summary.gate_groups
        ),
    )


def build_live_light_dashboard_section(summary: LiveLightRunSummary) -> DashboardSection:
    """Project a minimal Build-13 run summary into dashboard cards."""

    projection = build_live_light_projection(summary)
    blocking_detail = (
        ", ".join(projection.blocking_reasons)
        if projection.blocking_reasons
        else "No blocking reason"
    )
    return DashboardSection(
        title="Build-13 Live",
        cards=(
            DashboardCard(
                key="live_light_run_state",
                label="Run State",
                value=projection.run_state,
                status=projection.status,
                detail=f"micro_live_run={projection.micro_live_run_id}",
            ),
            DashboardCard(
                key="live_light_verdict",
                label="Execution Verdict",
                value=projection.verdict,
                status=projection.status,
                detail=f"micro_live_verdict={projection.micro_live_verdict}",
            ),
            DashboardCard(
                key="live_light_budget",
                label="Budget",
                value=(
                    f"approved={projection.approved_total_notional_usdt:.2f} / "
                    f"pair={projection.approved_pair_notional_usdt:.2f}"
                ),
                status=projection.status,
                detail=(
                    f"requested={projection.requested_total_notional_usdt:.2f} / "
                    f"build14={projection.build14_action}@{projection.build14_recommended_budget_factor:.2f}"
                ),
            ),
            DashboardCard(
                key="live_light_surface",
                label="Execution Surface",
                value=(
                    f"pairs={len(projection.planned_pairs)} / "
                    f"engines={len(projection.planned_engines)} / "
                    f"orders={projection.execution_order_limit}"
                ),
                status=(
                    "info"
                    if projection.planned_pairs or projection.planned_engines
                    else projection.status
                ),
                detail=", ".join(projection.planned_pairs) or "No execution surface planned",
            ),
            DashboardCard(
                key="live_light_readiness",
                label="Readiness",
                value=(
                    f"obs={'ready' if projection.observability_ready else 'missing'} / "
                    f"halt={'ready' if projection.halt_ready else 'missing'} / "
                    f"exec={'ready' if projection.execution_ready else 'missing'} / "
                    f"broker={'ready' if projection.broker_ready else 'missing'} / "
                    f"exchange={'ready' if projection.exchange_ready else 'missing'}"
                ),
                status=(
                    "healthy"
                    if projection.observability_ready
                    and projection.halt_ready
                    and projection.execution_ready
                    and projection.broker_ready
                    and projection.exchange_ready
                    else "critical"
                ),
                detail=(
                    f"{projection.build14_summary or projection.import_lineage_version} / "
                    f"exec_proj={projection.execution_runtime_projection_status} / "
                    f"ready={projection.execution_runtime_projection_ready_consumer_count} / "
                    f"partial={projection.execution_runtime_projection_partial_consumer_count} / "
                    f"blocked={projection.execution_runtime_projection_blocked_consumer_count}"
                ),
            ),
            DashboardCard(
                key="live_light_gate_groups",
                label="Gate Groups",
                value=_gate_group_value(projection.gate_groups),
                status=_gate_group_status(projection.gate_groups),
                detail=_gate_group_detail(projection.gate_groups),
            ),
            DashboardCard(
                key="live_light_safing_request",
                label="Safing Request",
                value=_operator_safing_value(summary),
                status=_operator_safing_status(summary),
                detail=(
                    projection.operator_safing_reason
                    or "No manual safing request projected"
                ),
            ),
            DashboardCard(
                key="live_light_blocking_reasons",
                label="Blocking Reasons",
                value=str(len(projection.blocking_reasons)),
                status="critical" if projection.blocking_reasons else "healthy",
                detail=blocking_detail,
            ),
        ),
    )


__all__ = [
    "build_live_projection",
    "build_live_dashboard_section",
    "build_live_light_projection",
    "build_live_light_dashboard_section",
]


build_live_projection = build_live_light_projection
build_live_dashboard_section = build_live_light_dashboard_section
