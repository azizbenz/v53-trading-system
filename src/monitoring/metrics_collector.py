"""Metrics aggregation for the real Build-10 monitoring backend."""

from __future__ import annotations

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from meta_minimal.break_even_dashboard.break_even_reporter import BreakEvenReport
from meta_minimal.cra_monitor.cra_reporter import CRAReport
from meta_minimal.dtr_core.dtr_reporter import DTRSummary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport
from monitoring.contracts import (
    EngineMetrics,
    InfraMetrics,
    MetaMetrics,
    MonitoringSnapshot,
    PairMetrics,
    PortfolioMetrics,
)


def collect_portfolio_metrics(
    *,
    allocated_opportunities: int,
    gross_capacity_used_pct: float,
    loss_capacity_used_pct: float,
    beta_utilization: float,
    capital_deployed_usdt: float,
    ce_net: float,
) -> PortfolioMetrics:
    """Collect portfolio-facing metrics without recalculating source logic."""

    return PortfolioMetrics(
        allocated_opportunities=allocated_opportunities,
        gross_capacity_used_pct=gross_capacity_used_pct,
        loss_capacity_used_pct=loss_capacity_used_pct,
        beta_utilization=beta_utilization,
        capital_deployed_usdt=capital_deployed_usdt,
        ce_net=ce_net,
    )


def collect_engine_metrics(
    *,
    engine_id: str,
    emitted_signals: int,
    net_edge_bps: float,
    expected_cost_bps: float,
    ce_expected: float,
    stale: bool = False,
) -> EngineMetrics:
    """Collect per-engine projections for the dashboard."""

    return EngineMetrics(
        engine_id=engine_id,
        emitted_signals=emitted_signals,
        net_edge_bps=net_edge_bps,
        expected_cost_bps=expected_cost_bps,
        ce_expected=ce_expected,
        stale=stale,
    )


def collect_pair_metrics(
    *,
    pair: str,
    health: PairHealthLevel,
    freshness_ms: int,
    backlog_depth: int = 0,
    is_active: bool = True,
) -> PairMetrics:
    """Collect pair-level health metrics."""

    return PairMetrics(
        pair=pair,
        health=health,
        freshness_ms=freshness_ms,
        backlog_depth=backlog_depth,
        is_active=is_active,
    )


def collect_infra_metrics(
    *,
    queue_backlog: int = 0,
    reconnect_count: int = 0,
    stale_pairs: tuple[str, ...] = (),
    dtr_loss_count: int = 0,
    log_loss_count: int = 0,
    cpu_pct: float = 0.0,
    ram_pct: float = 0.0,
) -> InfraMetrics:
    """Collect infra metrics used by the alert manager."""

    return InfraMetrics(
        queue_backlog=queue_backlog,
        reconnect_count=reconnect_count,
        stale_pairs=stale_pairs,
        dtr_loss_count=dtr_loss_count,
        log_loss_count=log_loss_count,
        cpu_pct=cpu_pct,
        ram_pct=ram_pct,
    )


def collect_meta_metrics(
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
    *,
    future_learning_diagnostics: int = 0,
    future_learning_hypotheses: int = 0,
) -> MetaMetrics:
    """Project Build-9 outputs into the Build-10 monitoring surface."""

    return MetaMetrics(
        dtr_coverage=dtr_summary.dtr_coverage,
        cra_sterilization_rate=cra_report.sterilization_rate,
        cra_alert_count=len(cra_report.alerts),
        break_even_drift_alert=break_even_report.has_cost_drift_alert,
        break_even_drift_scopes=break_even_report.cost_drift_alert_scopes,
        edge_credible_count=edge_report.credible_count,
        edge_degraded_count=edge_report.degraded_count,
        edge_surveillance_count=edge_report.surveillance_count,
        future_learning_diagnostics=future_learning_diagnostics,
        future_learning_hypotheses=future_learning_hypotheses,
    )


def collect_monitoring_snapshot(
    *,
    correlation_id: str,
    profile: ProfileId,
    runtime_mode: RuntimeMode,
    timestamp_ms: int,
    portfolio: PortfolioMetrics,
    infra: InfraMetrics,
    meta: MetaMetrics,
    engines: tuple[EngineMetrics, ...] = (),
    pairs: tuple[PairMetrics, ...] = (),
) -> MonitoringSnapshot:
    """Build a coherent snapshot for alerting and dashboard projection."""

    stale_from_pairs = any(
        pair.health in {PairHealthLevel.STALE, PairHealthLevel.OFFLINE, PairHealthLevel.SUSPENDED}
        for pair in pairs
    )

    return MonitoringSnapshot(
        timestamp_ms=timestamp_ms,
        correlation_id=correlation_id,
        profile=profile,
        runtime_mode=runtime_mode,
        portfolio=portfolio,
        infra=infra,
        meta=meta,
        engines=engines,
        pairs=pairs,
        backlog_warning=infra.queue_backlog > 50,
        stale_warning=stale_from_pairs or len(infra.stale_pairs) > 0,
        loss_warning=infra.dtr_loss_count > 0 or infra.log_loss_count > 0,
    )


__all__ = [
    "collect_portfolio_metrics",
    "collect_engine_metrics",
    "collect_pair_metrics",
    "collect_infra_metrics",
    "collect_meta_metrics",
    "collect_monitoring_snapshot",
]
