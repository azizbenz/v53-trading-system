"""Projection layer for the locked Build-10 Light UI."""

from __future__ import annotations

from monitoring import HealthDashboardPayload
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView


def build_light_dashboard_view(payload: HealthDashboardPayload) -> LightDashboardView:
    """Render the stable backend payload into a locked UI view model."""

    sections = (
        DashboardSection(
            title="Health",
            cards=(
                DashboardCard(
                    key="headline_status",
                    label="Headline",
                    value=payload.headline_status,
                    status=payload.headline_status,
                    detail=f"{payload.active_alert_count} active alert(s)",
                ),
                DashboardCard(
                    key="stale_pairs",
                    label="Stale Pairs",
                    value=str(payload.stale_pair_count),
                    status="warning" if payload.stale_pair_count else "healthy",
                    detail=f"Queue backlog {payload.queue_backlog}",
                ),
            ),
        ),
        DashboardSection(
            title="Portfolio",
            cards=(
                DashboardCard(
                    key="capital_deployed",
                    label="Capital Deployed",
                    value=f"{payload.capital_deployed_usdt:.2f}",
                    status="info",
                    detail=f"Gross {payload.gross_capacity_used_pct:.1f}% / Loss {payload.loss_capacity_used_pct:.1f}%",
                ),
                DashboardCard(
                    key="ce_net",
                    label="CE Net",
                    value=f"{payload.ce_net:.6f}",
                    status="healthy" if payload.ce_net >= 0 else "warning",
                ),
            ),
        ),
        DashboardSection(
            title="Meta",
            cards=(
                DashboardCard(
                    key="dtr_coverage",
                    label="DTR Coverage",
                    value=f"{payload.dtr_coverage:.2%}",
                    status="healthy" if payload.dtr_coverage >= 0.8 else "warning",
                ),
                DashboardCard(
                    key="cra_sterilization",
                    label="CRA Sterilization",
                    value=f"{payload.cra_sterilization_rate:.2%}",
                    status="warning" if payload.cra_sterilization_rate >= 0.2 else "healthy",
                ),
                DashboardCard(
                    key="edge_status",
                    label="Edge Status",
                    value=f"C{payload.edge_credible_count}/D{payload.edge_degraded_count}/S{payload.edge_surveillance_count}",
                    status="warning" if payload.edge_degraded_count > 0 else "healthy",
                    detail=f"Break-even drift scopes: {len(payload.break_even_drift_scopes)}",
                ),
            ),
        ),
        DashboardSection(
            title="Future Learning",
            cards=(
                DashboardCard(
                    key="future_learning_diagnostics",
                    label="Diagnostics",
                    value=str(payload.future_learning_diagnostics),
                    status="planned",
                    detail="Reserved for Build-9X governed outputs",
                ),
                DashboardCard(
                    key="future_learning_hypotheses",
                    label="Hypotheses",
                    value=str(payload.future_learning_hypotheses),
                    status="planned",
                    detail="Reserved for LOCAL_REPLAY candidate review",
                ),
            ),
        ),
    )

    return LightDashboardView(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        sections=sections,
        future_panels=("build9x_diagnostics", "strategy_onboarding", "artifact_import"),
    )


__all__ = [
    "build_light_dashboard_view",
]
