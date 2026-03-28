"""Build-13 Live-Light supervision helpers for the technical interface."""

from __future__ import annotations

from monitoring import LiveLightProjection
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
        observability_ready=summary.observability_ready,
        halt_ready=summary.halt_ready,
        execution_ready=summary.execution_ready,
        broker_ready=summary.broker_ready,
        exchange_ready=summary.exchange_ready,
        blocking_reasons=summary.decision.blocking_reasons,
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
        title="Build-13 Live-Light",
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
                detail=f"requested={projection.requested_total_notional_usdt:.2f}",
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
                detail=projection.import_lineage_version,
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
    "build_live_light_projection",
    "build_live_light_dashboard_section",
]
