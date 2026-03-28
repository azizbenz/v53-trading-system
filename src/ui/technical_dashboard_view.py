"""Technical Build-10 supervision view over the normalized backend payload."""

from __future__ import annotations

from monitoring import TechnicalDashboardPayload
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


def _engine_card(payload: TechnicalDashboardPayload) -> DashboardCard:
    if not payload.system.active_engines:
        return DashboardCard(
            key="engines_ab",
            label="Engines A/B",
            value="0",
            status="planned",
            detail="No active engines declared",
        )

    detail = f"Active: {_join(payload.system.active_engines, empty='none')}"
    if payload.system.stale_engines:
        detail = f"{detail} / stale: {_join(payload.system.stale_engines, empty='none')}"
        status = "warning"
    else:
        status = "healthy"

    return DashboardCard(
        key="engines_ab",
        label="Engines A/B",
        value=str(len(payload.system.active_engines)),
        status=status,
        detail=detail,
    )


def build_technical_dashboard_view(payload: TechnicalDashboardPayload) -> LightDashboardView:
    """Project normalized monitoring truth into the locked Build-10 UI surface."""

    sections = (
        DashboardSection(
            title="System",
            cards=(
                DashboardCard(
                    key="headline_status",
                    label="Headline",
                    value=payload.system.headline_status,
                    status=payload.system.headline_status,
                    detail=f"{payload.alerts.active_alert_count} active alert(s)",
                ),
                DashboardCard(
                    key="runtime_mode",
                    label="Runtime",
                    value=payload.runtime_mode.value,
                    status="info",
                    detail=f"profile={payload.profile.value}",
                ),
                DashboardCard(
                    key="active_modules",
                    label="Active Modules",
                    value=str(len(payload.system.active_modules)),
                    status="healthy" if payload.system.active_modules else "planned",
                    detail=_join(payload.system.active_modules, empty="No active modules declared"),
                ),
                _engine_card(payload),
                DashboardCard(
                    key="governed_extensions",
                    label="Governed Extensions",
                    value=(
                        f"9X={payload.system.build9x_status} / "
                        f"shadow={payload.system.shadow_status} / "
                        f"replay={payload.system.replay_import_status}"
                    ),
                    status=(
                        "critical"
                        if "critical" in {
                            payload.system.build9x_status,
                            payload.system.shadow_status,
                            payload.system.replay_import_status,
                        }
                        else "warning"
                        if "warning" in {
                            payload.system.build9x_status,
                            payload.system.shadow_status,
                            payload.system.replay_import_status,
                        }
                        else "info"
                    ),
                    detail=payload.system.governed_extensions_detail,
                ),
            ),
        ),
        DashboardSection(
            title="Portfolio",
            cards=(
                DashboardCard(
                    key="capital_deployed",
                    label="Capital Deployed",
                    value=f"{payload.portfolio.capital_deployed_usdt:.2f}",
                    status="info",
                    detail=f"opportunities={payload.portfolio.allocated_opportunities}",
                ),
                DashboardCard(
                    key="capacity_usage",
                    label="Capacity Usage",
                    value=(
                        f"gross={payload.portfolio.gross_capacity_used_pct:.1f}% / "
                        f"loss={payload.portfolio.loss_capacity_used_pct:.1f}%"
                    ),
                    status=(
                        "warning"
                        if payload.portfolio.loss_capacity_used_pct >= 25.0
                        else "healthy"
                    ),
                    detail=f"beta={payload.portfolio.beta_utilization:.2f}",
                ),
                DashboardCard(
                    key="ce_net",
                    label="CE Net",
                    value=f"{payload.portfolio.ce_net:.6f}",
                    status="healthy" if payload.portfolio.ce_net >= 0 else "warning",
                ),
            ),
        ),
        DashboardSection(
            title="Build-9 Meta",
            cards=(
                DashboardCard(
                    key="dtr_summary",
                    label="DTR Summary",
                    value=f"coverage={payload.build9_meta.dtr_coverage:.2%}",
                    status=payload.build9_meta.dtr_status,
                    detail=f"stale_pairs={payload.alerts.stale_pair_count}",
                ),
                DashboardCard(
                    key="cra_summary",
                    label="CRA Summary",
                    value=f"sterilization={payload.build9_meta.cra_sterilization_rate:.2%}",
                    status=payload.build9_meta.cra_status,
                    detail=f"alerts={payload.build9_meta.cra_alert_count}",
                ),
                DashboardCard(
                    key="break_even_summary",
                    label="Break-even",
                    value=payload.build9_meta.break_even_state,
                    status=payload.build9_meta.break_even_status,
                    detail=_join(
                        payload.build9_meta.break_even_drift_scopes,
                        empty="No drift scope",
                    ),
                ),
                DashboardCard(
                    key="edge_summary",
                    label="Edge Summary",
                    value=(
                        f"credible={payload.build9_meta.edge_credible_count} / "
                        f"degraded={payload.build9_meta.edge_degraded_count} / "
                        f"surveillance={payload.build9_meta.edge_surveillance_count}"
                    ),
                    status=payload.build9_meta.edge_status,
                ),
            ),
        ),
        DashboardSection(
            title="Build-9X",
            cards=(
                DashboardCard(
                    key="diagnostics_recent",
                    label="Diagnostics",
                    value=str(payload.build9x.diagnostics_count),
                    status=payload.build9x.status,
                    detail=payload.build9x.diagnostics_summary,
                ),
                DashboardCard(
                    key="hypotheses_open",
                    label="Open Hypotheses",
                    value=str(payload.build9x.open_hypotheses),
                    status=(
                        "warning"
                        if payload.build9x.open_hypotheses > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                    detail=f"total={payload.build9x.total_hypotheses}",
                ),
                DashboardCard(
                    key="near_miss_candidates",
                    label="Near Miss / Candidates",
                    value=(
                        f"near_miss={payload.build9x.near_miss_count} / "
                        f"replay={payload.build9x.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.build9x.near_miss_count > 0
                        or payload.build9x.replay_candidate_count > 0
                        else "info"
                        if payload.build9x.status != "planned"
                        else "planned"
                    ),
                ),
                DashboardCard(
                    key="memory_review",
                    label="Memory / Review",
                    value=(
                        f"records={payload.build9x.memory_record_count} / "
                        f"export={'ready' if payload.build9x.review_export_ready else 'none'}"
                    ),
                    status=(
                        "healthy"
                        if payload.build9x.review_export_ready
                        else "info"
                        if payload.build9x.memory_record_count > 0
                        else "planned"
                    ),
                    detail=payload.build9x.latest_memory_summary,
                ),
            ),
        ),
        DashboardSection(
            title="Build-11 Shadow",
            cards=(
                DashboardCard(
                    key="shadow_run_state",
                    label="Run State",
                    value=payload.shadow.run_state,
                    status=payload.shadow.status,
                    detail=(
                        f"truth={payload.shadow.truth_set_ref or 'n/a'} / "
                        f"validation={payload.shadow.validation_set_ref or 'n/a'}"
                    ),
                ),
                DashboardCard(
                    key="shadow_verdict",
                    label="Gating Verdict",
                    value=payload.shadow.verdict,
                    status=payload.shadow.status,
                    detail=(
                        "manual review required"
                        if payload.shadow.manual_review_required
                        else "manual review not required"
                    ),
                ),
                DashboardCard(
                    key="shadow_divergences",
                    label="Divergences",
                    value=(
                        f"blocking={payload.shadow.blocking_comparison_count} / "
                        f"divergent={payload.shadow.divergent_comparison_count} / "
                        f"total={payload.shadow.total_comparison_count}"
                    ),
                    status=(
                        "critical"
                        if payload.shadow.blocking_comparison_count > 0
                        else "warning"
                        if payload.shadow.divergent_comparison_count > 0
                        else payload.shadow.status
                    ),
                ),
                DashboardCard(
                    key="shadow_candidate_state",
                    label="Candidate State",
                    value=(
                        f"diagnostics={payload.shadow.build9x_diagnostics_count} / "
                        f"hypotheses={payload.shadow.open_hypotheses} / "
                        f"replay={payload.shadow.replay_candidate_count}"
                    ),
                    status=(
                        "warning"
                        if payload.shadow.manual_review_required
                        else "info"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=(
                        "review export ready"
                        if payload.shadow.review_export_ready
                        else "review export missing"
                    ),
                ),
                DashboardCard(
                    key="shadow_import_lineage",
                    label="Import Lineage",
                    value=payload.shadow.import_lineage_version,
                    status=(
                        "healthy"
                        if payload.shadow.import_lineage_version not in {"", "n/a"}
                        else "critical"
                        if payload.shadow.status != "planned"
                        else "planned"
                    ),
                    detail=payload.shadow.import_artifact_id or "No import artifact id",
                ),
                DashboardCard(
                    key="shadow_blocking_reasons",
                    label="Blocking Reasons",
                    value=str(len(payload.shadow.blocking_reasons)),
                    status=(
                        "critical"
                        if payload.shadow.blocking_reasons
                        else "healthy"
                        if payload.shadow.status == "healthy"
                        else payload.shadow.status
                    ),
                    detail=_join(payload.shadow.blocking_reasons, empty="No blocking reason"),
                ),
            ),
        ),
        DashboardSection(
            title="Replay & Import",
            cards=(
                DashboardCard(
                    key="artifact_manifest",
                    label="Artifact Manifest",
                    value=payload.replay_import.artifact_id,
                    status=payload.replay_import.status,
                    detail=payload.replay_import.artifact_kind,
                ),
                DashboardCard(
                    key="lineage_version",
                    label="Lineage",
                    value=payload.replay_import.lineage_version,
                    status="info" if payload.replay_import.artifact_id != "none" else "planned",
                    detail=payload.replay_import.lifecycle_state,
                ),
                DashboardCard(
                    key="validation_status",
                    label="Validation",
                    value=payload.replay_import.validation_status,
                    status=(
                        "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "warning"
                        if payload.replay_import.validation_status != "not_run"
                        else "planned"
                    ),
                    detail=payload.replay_import.review_state,
                ),
                DashboardCard(
                    key="validation_reasons",
                    label="Validation Reasons",
                    value=str(len(payload.replay_import.rejection_reasons)),
                    status=(
                        "warning"
                        if payload.replay_import.rejection_reasons
                        else "healthy"
                        if payload.replay_import.validation_status == "accepted"
                        else "planned"
                    ),
                    detail=_join(
                        payload.replay_import.rejection_reasons,
                        empty="No validation rejection",
                    ),
                ),
            ),
        ),
        DashboardSection(
            title="Alerts",
            cards=(
                DashboardCard(
                    key="active_alerts",
                    label="Active Alerts",
                    value=str(payload.alerts.active_alert_count),
                    status=payload.alerts.headline_status,
                    detail=_join(payload.alerts.alert_ids, empty="No active alert"),
                ),
                DashboardCard(
                    key="backlog_stale",
                    label="Backlog / Stale",
                    value=(
                        f"backlog={payload.alerts.queue_backlog} / "
                        f"stale={payload.alerts.stale_pair_count}"
                    ),
                    status=payload.alerts.backlog_stale_status,
                    detail=_join(payload.alerts.stale_pairs, empty="No stale pair"),
                ),
                DashboardCard(
                    key="loss_drift",
                    label="Loss / Drift",
                    value=(
                        f"dtr={payload.alerts.dtr_loss_count} / "
                        f"log={payload.alerts.log_loss_count} / "
                        f"drift={payload.alerts.break_even_drift_scope_count}"
                    ),
                    status=payload.alerts.loss_drift_status,
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
        future_panels=payload.future_panels,
    )


__all__ = [
    "build_technical_dashboard_view",
]
