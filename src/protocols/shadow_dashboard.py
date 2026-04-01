"""Build-11 Shadow supervision helpers for the technical interface."""

from __future__ import annotations

from monitoring import ShadowProjection
from protocols.contracts import ShadowRunSummary
from protocols.enums import ShadowRunState, ShadowVerdict
from ui.contracts import DashboardCard, DashboardSection


def _status_from_summary(summary: ShadowRunSummary) -> str:
    if summary.decision.verdict in {ShadowVerdict.BLOCKED, ShadowVerdict.REJECTED}:
        return "critical"
    if summary.decision.verdict == ShadowVerdict.NEEDS_REVIEW:
        return "warning"
    if summary.run_state == ShadowRunState.PREPARED:
        return "info"
    return "healthy"


def build_shadow_projection(summary: ShadowRunSummary) -> ShadowProjection:
    """Project a governed Build-11 summary into the normalized supervision surface."""

    return ShadowProjection(
        status=_status_from_summary(summary),
        run_state=summary.run_state.value,
        verdict=summary.decision.verdict.value,
        truth_set_ref=summary.truth_set_ref,
        validation_set_ref=summary.validation_set_ref,
        divergent_comparison_count=summary.divergent_comparison_count,
        blocking_comparison_count=summary.blocking_comparison_count,
        total_comparison_count=len(summary.comparisons),
        build9x_diagnostics_count=summary.build9x_diagnostics_count,
        open_hypotheses=summary.open_hypotheses,
        replay_candidate_count=summary.replay_candidate_count,
        review_export_ready=summary.review_export_ready,
        import_artifact_id=summary.import_artifact_id or "none",
        import_lineage_version=summary.import_lineage_version or "n/a",
        blocking_reasons=summary.decision.blocking_reasons,
        manual_review_required=summary.decision.manual_review_required,
        shadow_days_completed=summary.shadow_days_completed,
        shadow_required_days=summary.shadow_required_days,
        shadow_report_ready=summary.shadow_report_ready,
        active_engine_count=len(summary.active_engines),
        build14_enabler_count=summary.build14_component_count,
        shadow_validated_component_count=summary.shadow_validated_component_count,
        dormant_component_count=summary.dormant_component_count,
    )


def build_shadow_dashboard_section(summary: ShadowRunSummary) -> DashboardSection:
    """Project a minimal Build-11 run summary into dashboard cards."""

    projection = build_shadow_projection(summary)
    blocking_detail = (
        ", ".join(projection.blocking_reasons)
        if projection.blocking_reasons
        else "No blocking reason"
    )
    comparison_detail = (
        f"blocking={projection.blocking_comparison_count}, "
        f"divergent={projection.divergent_comparison_count}, "
        f"total={projection.total_comparison_count}"
    )
    return DashboardSection(
        title="Build-11 Shadow",
        cards=(
            DashboardCard(
                key="shadow_run_state",
                label="Run State",
                value=projection.run_state,
                status=projection.status,
                detail=f"run_id={summary.run_id}",
            ),
            DashboardCard(
                key="shadow_verdict",
                label="Gating Verdict",
                value=projection.verdict,
                status=projection.status,
                detail=(
                    f"promotion={summary.decision.normalized_promotion_state.value} / "
                    f"review={summary.decision.review_state.value}"
                ),
            ),
            DashboardCard(
                key="shadow_day_counter",
                label="Shadow 30-Day Gate",
                value=(
                    f"{projection.shadow_days_completed}/"
                    f"{projection.shadow_required_days}"
                ),
                status=(
                    "healthy"
                    if projection.shadow_days_completed >= projection.shadow_required_days
                    and projection.shadow_report_ready
                    else "critical"
                ),
                detail=(
                    "shadow report ready"
                    if projection.shadow_report_ready
                    else "shadow report incomplete"
                ),
            ),
            DashboardCard(
                key="shadow_divergences",
                label="Divergences",
                value=comparison_detail,
                status=(
                    "critical"
                    if projection.blocking_comparison_count > 0
                    else "warning"
                    if projection.divergent_comparison_count > 0
                    else projection.status
                ),
            ),
            DashboardCard(
                key="shadow_candidate_state",
                label="Candidate State",
                value=(
                    f"diagnostics={projection.build9x_diagnostics_count} / "
                    f"hypotheses={projection.open_hypotheses} / "
                    f"replay={projection.replay_candidate_count}"
                ),
                status="warning" if projection.manual_review_required else "info",
                detail=(
                    "review export ready"
                    if projection.review_export_ready
                    else "review export missing"
                ),
            ),
            DashboardCard(
                key="shadow_import_lineage",
                label="Import Lineage",
                value=projection.import_lineage_version,
                status="healthy" if projection.import_lineage_version != "n/a" else "critical",
                detail=projection.import_artifact_id or "No import artifact id",
            ),
            DashboardCard(
                key="shadow_component_verdicts",
                label="Component Verdicts",
                value=(
                    f"validated={projection.shadow_validated_component_count} / "
                    f"dormant={projection.dormant_component_count}"
                ),
                status=(
                    "healthy"
                    if projection.build14_enabler_count >= 5
                    and projection.active_engine_count >= 4
                    else "critical"
                ),
                detail=(
                    f"engines={projection.active_engine_count} / "
                    f"build14={projection.build14_enabler_count}"
                ),
            ),
            DashboardCard(
                key="shadow_blocking_reasons",
                label="Blocking Reasons",
                value=str(len(projection.blocking_reasons)),
                status="critical" if projection.blocking_reasons else "healthy",
                detail=blocking_detail,
            ),
        ),
    )


__all__ = [
    "build_shadow_projection",
    "build_shadow_dashboard_section",
]
