"""Technical Build-10 supervision view over the locked backend surface."""

from __future__ import annotations

from meta_learning import (
    BreakdownReport,
    ImprovementCandidate,
    LearningHypothesis,
    LearningMemoryRecord,
    LearningReviewExport,
)
from monitoring import MonitoringSnapshot, build_health_dashboard_payload, build_monitoring_alerts
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView


def _headline_status(snapshot: MonitoringSnapshot) -> tuple[MonitoringSnapshot, str]:
    resolved_alerts = snapshot.alerts or build_monitoring_alerts(snapshot)
    resolved_snapshot = snapshot if snapshot.alerts else snapshot.model_copy(update={"alerts": resolved_alerts})
    payload = build_health_dashboard_payload(resolved_snapshot)
    return resolved_snapshot, payload.headline_status


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


def _engine_status(snapshot: MonitoringSnapshot, active_engines: tuple[str, ...]) -> tuple[str, str, str]:
    if not active_engines:
        return "0", "planned", "No active engines declared"

    stale = tuple(engine.engine_id for engine in snapshot.engines if engine.stale)
    detail = f"Active: {_join(active_engines, empty='none')}"
    if stale:
        detail = f"{detail} / stale: {_join(stale, empty='none')}"
        return str(len(active_engines)), "warning", detail
    return str(len(active_engines)), "healthy", detail


def _build9x_status(
    *,
    active_modules: tuple[str, ...],
    diagnostics_count: int,
    open_hypotheses: int,
    candidate_count: int,
) -> str:
    if "meta_learning" not in active_modules:
        return "planned"
    if candidate_count > 0 or open_hypotheses > 0:
        return "warning"
    if diagnostics_count > 0:
        return "healthy"
    return "info"


def _replay_status(
    *,
    active_modules: tuple[str, ...],
    replay_bundle: object | None,
    import_decision: object | None,
) -> str:
    if "local_replay_runtime" not in active_modules and "backtest_artifact_import" not in active_modules:
        return "planned"
    if import_decision is not None and not getattr(import_decision, "accepted", False):
        return "warning"
    if replay_bundle is None:
        return "info"
    lifecycle_state = getattr(getattr(replay_bundle, "lifecycle_state", None), "value", None)
    if lifecycle_state in {"exported", "imported"}:
        return "healthy"
    if lifecycle_state == "validated":
        return "info"
    return "planned"


def build_technical_dashboard_view(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    breakdown_report: BreakdownReport | None = None,
    hypotheses: tuple[LearningHypothesis, ...] = (),
    candidates: tuple[ImprovementCandidate, ...] = (),
    memory_records: tuple[LearningMemoryRecord, ...] = (),
    review_export: LearningReviewExport | None = None,
    replay_bundle: object | None = None,
    import_decision: object | None = None,
) -> LightDashboardView:
    """Project runtime supervision into a richer Build-10 backend view."""

    resolved_snapshot, headline_status = _headline_status(snapshot)
    diagnostics_count = len(breakdown_report.diagnostics) if breakdown_report else 0
    open_hypotheses = sum(hypothesis.status.value == "open" for hypothesis in hypotheses)
    near_miss_count = len(breakdown_report.near_miss_pairs) if breakdown_report else 0
    candidate_count = len(candidates)
    build9x_status = _build9x_status(
        active_modules=active_modules,
        diagnostics_count=diagnostics_count,
        open_hypotheses=open_hypotheses,
        candidate_count=candidate_count,
    )
    replay_status = _replay_status(
        active_modules=active_modules,
        replay_bundle=replay_bundle,
        import_decision=import_decision,
    )
    engine_value, engine_status, engine_detail = _engine_status(resolved_snapshot, active_engines)
    rejection_reasons = import_decision.reasons if import_decision is not None else ()
    latest_memory_summary = memory_records[-1].summary if memory_records else "No memory records"
    replay_manifest = getattr(replay_bundle, "manifest", None)
    replay_lifecycle = getattr(getattr(replay_bundle, "lifecycle_state", None), "value", None)
    replay_kind = getattr(getattr(replay_bundle, "artifact_kind", None), "value", None)
    import_review_state = getattr(getattr(import_decision, "review_state", None), "value", None)

    sections = (
        DashboardSection(
            title="System",
            cards=(
                DashboardCard(
                    key="headline_status",
                    label="Headline",
                    value=headline_status,
                    status=headline_status,
                    detail=f"{len(resolved_snapshot.alerts)} active alert(s)",
                ),
                DashboardCard(
                    key="runtime_mode",
                    label="Runtime",
                    value=resolved_snapshot.runtime_mode.value,
                    status="info",
                    detail=f"profile={resolved_snapshot.profile.value}",
                ),
                DashboardCard(
                    key="active_modules",
                    label="Active Modules",
                    value=str(len(active_modules)),
                    status="healthy" if active_modules else "planned",
                    detail=_join(active_modules, empty="No active modules declared"),
                ),
                DashboardCard(
                    key="engines_ab",
                    label="Engines A/B",
                    value=engine_value,
                    status=engine_status,
                    detail=engine_detail,
                ),
                DashboardCard(
                    key="governed_extensions",
                    label="Governed Extensions",
                    value=f"9X={build9x_status} / replay={replay_status}",
                    status="warning" if "warning" in {build9x_status, replay_status} else "info",
                    detail="Build-9X and replay/import remain governed and non-live",
                ),
            ),
        ),
        DashboardSection(
            title="Portfolio",
            cards=(
                DashboardCard(
                    key="capital_deployed",
                    label="Capital Deployed",
                    value=f"{resolved_snapshot.portfolio.capital_deployed_usdt:.2f}",
                    status="info",
                    detail=f"opportunities={resolved_snapshot.portfolio.allocated_opportunities}",
                ),
                DashboardCard(
                    key="capacity_usage",
                    label="Capacity Usage",
                    value=(
                        f"gross={resolved_snapshot.portfolio.gross_capacity_used_pct:.1f}% / "
                        f"loss={resolved_snapshot.portfolio.loss_capacity_used_pct:.1f}%"
                    ),
                    status=(
                        "warning"
                        if resolved_snapshot.portfolio.loss_capacity_used_pct >= 25.0
                        else "healthy"
                    ),
                    detail=f"beta={resolved_snapshot.portfolio.beta_utilization:.2f}",
                ),
                DashboardCard(
                    key="ce_net",
                    label="CE Net",
                    value=f"{resolved_snapshot.portfolio.ce_net:.6f}",
                    status="healthy" if resolved_snapshot.portfolio.ce_net >= 0 else "warning",
                ),
            ),
        ),
        DashboardSection(
            title="Build-9 Meta",
            cards=(
                DashboardCard(
                    key="dtr_summary",
                    label="DTR Summary",
                    value=f"coverage={resolved_snapshot.meta.dtr_coverage:.2%}",
                    status="healthy" if resolved_snapshot.meta.dtr_coverage >= 0.8 else "warning",
                    detail=f"stale_pairs={resolved_snapshot.stale_pair_count}",
                ),
                DashboardCard(
                    key="cra_summary",
                    label="CRA Summary",
                    value=f"sterilization={resolved_snapshot.meta.cra_sterilization_rate:.2%}",
                    status="warning" if resolved_snapshot.meta.cra_sterilization_rate >= 0.2 else "healthy",
                    detail=f"alerts={resolved_snapshot.meta.cra_alert_count}",
                ),
                DashboardCard(
                    key="break_even_summary",
                    label="Break-even",
                    value=(
                        "drift_alert"
                        if resolved_snapshot.meta.break_even_drift_alert
                        else "stable"
                    ),
                    status="warning" if resolved_snapshot.meta.break_even_drift_alert else "healthy",
                    detail=_join(
                        resolved_snapshot.meta.break_even_drift_scopes,
                        empty="No drift scope",
                    ),
                ),
                DashboardCard(
                    key="edge_summary",
                    label="Edge Summary",
                    value=(
                        f"credible={resolved_snapshot.meta.edge_credible_count} / "
                        f"degraded={resolved_snapshot.meta.edge_degraded_count} / "
                        f"surveillance={resolved_snapshot.meta.edge_surveillance_count}"
                    ),
                    status="warning" if resolved_snapshot.meta.edge_degraded_count > 0 else "healthy",
                ),
            ),
        ),
        DashboardSection(
            title="Build-9X",
            cards=(
                DashboardCard(
                    key="diagnostics_recent",
                    label="Diagnostics",
                    value=str(diagnostics_count),
                    status=build9x_status,
                    detail=breakdown_report.summary if breakdown_report else "No diagnostic report",
                ),
                DashboardCard(
                    key="hypotheses_open",
                    label="Open Hypotheses",
                    value=str(open_hypotheses),
                    status="warning" if open_hypotheses > 0 else ("info" if "meta_learning" in active_modules else "planned"),
                    detail=f"total={len(hypotheses)}",
                ),
                DashboardCard(
                    key="near_miss_candidates",
                    label="Near Miss / Candidates",
                    value=f"near_miss={near_miss_count} / replay={candidate_count}",
                    status="warning" if near_miss_count > 0 or candidate_count > 0 else ("info" if "meta_learning" in active_modules else "planned"),
                ),
                DashboardCard(
                    key="memory_review",
                    label="Memory / Review",
                    value=f"records={len(memory_records)} / export={'ready' if review_export else 'none'}",
                    status="healthy" if review_export else ("info" if memory_records else "planned"),
                    detail=latest_memory_summary,
                ),
            ),
        ),
        DashboardSection(
            title="Replay & Import",
            cards=(
                DashboardCard(
                    key="artifact_manifest",
                    label="Artifact Manifest",
                    value=getattr(replay_manifest, "artifact_id", "none"),
                    status=replay_status,
                    detail=replay_kind or "No replay bundle exported",
                ),
                DashboardCard(
                    key="lineage_version",
                    label="Lineage",
                    value=getattr(replay_manifest, "lineage_version", "n/a"),
                    status="info" if replay_bundle else "planned",
                    detail=(
                        replay_lifecycle
                        if replay_bundle
                        else "Awaiting LOCAL_REPLAY artifact"
                    ),
                ),
                DashboardCard(
                    key="validation_status",
                    label="Validation",
                    value=(
                        "accepted"
                        if import_decision and getattr(import_decision, "accepted", False)
                        else "needs_revision"
                        if import_decision
                        else "not_run"
                    ),
                    status=(
                        "healthy"
                        if import_decision and getattr(import_decision, "accepted", False)
                        else "warning"
                        if import_decision
                        else "planned"
                    ),
                    detail=import_review_state or "No import review executed",
                ),
                DashboardCard(
                    key="validation_reasons",
                    label="Validation Reasons",
                    value=str(len(rejection_reasons)),
                    status="warning" if rejection_reasons else ("healthy" if import_decision else "planned"),
                    detail=_join(rejection_reasons, empty="No validation rejection"),
                ),
            ),
        ),
        DashboardSection(
            title="Alerts",
            cards=(
                DashboardCard(
                    key="active_alerts",
                    label="Active Alerts",
                    value=str(len(resolved_snapshot.alerts)),
                    status=headline_status,
                    detail=_join(tuple(alert.alert_id for alert in resolved_snapshot.alerts), empty="No active alert"),
                ),
                DashboardCard(
                    key="backlog_stale",
                    label="Backlog / Stale",
                    value=f"backlog={resolved_snapshot.infra.queue_backlog} / stale={resolved_snapshot.stale_pair_count}",
                    status="warning" if resolved_snapshot.backlog_warning or resolved_snapshot.stale_warning else "healthy",
                    detail=_join(resolved_snapshot.infra.stale_pairs, empty="No stale pair"),
                ),
                DashboardCard(
                    key="loss_drift",
                    label="Loss / Drift",
                    value=(
                        f"dtr={resolved_snapshot.infra.dtr_loss_count} / "
                        f"log={resolved_snapshot.infra.log_loss_count} / "
                        f"drift={len(resolved_snapshot.meta.break_even_drift_scopes)}"
                    ),
                    status=(
                        "critical"
                        if resolved_snapshot.loss_warning
                        else "warning"
                        if resolved_snapshot.meta.break_even_drift_alert or resolved_snapshot.meta.edge_degraded_count > 0
                        else "healthy"
                    ),
                ),
            ),
        ),
    )

    return LightDashboardView(
        timestamp_ms=resolved_snapshot.timestamp_ms,
        correlation_id=resolved_snapshot.correlation_id,
        profile=resolved_snapshot.profile,
        runtime_mode=resolved_snapshot.runtime_mode,
        sections=sections,
        future_panels=(
            "technical_supervision",
            "build9x_diagnostics",
            "artifact_import",
            "observability_export",
        ),
    )


__all__ = [
    "build_technical_dashboard_view",
]
