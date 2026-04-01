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


_CRITICAL_INFRA_METRICS = (
    "queue_backlog",
    "backlog_high_water_mark",
    "drop_rate_pct",
    "stale_spike_count",
    "recovery_retry_count",
    "kill_switch_active",
)


def collect_portfolio_metrics(
    *,
    allocated_opportunities: int,
    gross_capacity_used_pct: float,
    loss_capacity_used_pct: float,
    beta_utilization: float,
    capital_deployed_usdt: float,
    ce_net: float,
    pnl_net_usdt: float = 0.0,
    dominant_cluster: str = "",
    breaches: tuple[str, ...] = (),
) -> PortfolioMetrics:
    """Collect portfolio-facing metrics without recalculating source logic."""

    return PortfolioMetrics(
        allocated_opportunities=allocated_opportunities,
        gross_capacity_used_pct=gross_capacity_used_pct,
        loss_capacity_used_pct=loss_capacity_used_pct,
        beta_utilization=beta_utilization,
        capital_deployed_usdt=capital_deployed_usdt,
        ce_net=ce_net,
        pnl_net_usdt=pnl_net_usdt,
        dominant_cluster=dominant_cluster,
        breaches=breaches,
    )


def collect_engine_metrics(
    *,
    engine_id: str,
    emitted_signals: int,
    net_edge_bps: float,
    expected_cost_bps: float,
    ce_expected: float,
    useful_frequency: float = 0.0,
    sharpe_per_trade: float = 0.0,
    drawdown_pct: float = 0.0,
    suspension_reason: str = "",
    stale: bool = False,
) -> EngineMetrics:
    """Collect per-engine projections for the dashboard."""

    return EngineMetrics(
        engine_id=engine_id,
        emitted_signals=emitted_signals,
        net_edge_bps=net_edge_bps,
        expected_cost_bps=expected_cost_bps,
        ce_expected=ce_expected,
        useful_frequency=useful_frequency,
        sharpe_per_trade=sharpe_per_trade,
        drawdown_pct=drawdown_pct,
        suspension_reason=suspension_reason,
        stale=stale,
    )


def collect_pair_metrics(
    *,
    pair: str,
    health: PairHealthLevel,
    freshness_ms: int,
    backlog_depth: int = 0,
    is_active: bool = True,
    average_cost_bps: float = 0.0,
    cost_p90_bps: float = 0.0,
    ce_expected: float = 0.0,
    useful_frequency: float = 0.0,
    suspension_reason: str = "",
) -> PairMetrics:
    """Collect pair-level health metrics."""

    return PairMetrics(
        pair=pair,
        health=health,
        freshness_ms=freshness_ms,
        backlog_depth=backlog_depth,
        is_active=is_active,
        average_cost_bps=average_cost_bps,
        cost_p90_bps=cost_p90_bps,
        ce_expected=ce_expected,
        useful_frequency=useful_frequency,
        suspension_reason=suspension_reason,
    )


def collect_infra_metrics(
    *,
    queue_backlog: int = 0,
    backlog_high_water_mark: int = 0,
    reconnect_count: int = 0,
    stale_pairs: tuple[str, ...] = (),
    stale_spike_count: int = 0,
    recovery_retry_count: int = 0,
    dtr_loss_count: int = 0,
    log_loss_count: int = 0,
    total_enqueued: int = 0,
    total_dropped: int = 0,
    drop_rate_pct: float | None = None,
    elw_bps: float = 0.0,
    expected_cost_bps: float = 0.0,
    realized_cost_bps: float = 0.0,
    partial_fill_count: int = 0,
    fill_latency_ms_p95: int = 0,
    reconciliation_alert_count: int = 0,
    kill_switch_active: bool = False,
    kill_switch_timestamp_ms: int | None = None,
    persisted_metric_names: tuple[str, ...] = (),
    volatile_metric_names: tuple[str, ...] = (),
    cpu_pct: float = 0.0,
    ram_pct: float = 0.0,
) -> InfraMetrics:
    """Collect infra metrics used by the alert manager."""

    resolved_backlog_high_water_mark = max(backlog_high_water_mark, queue_backlog)
    resolved_drop_rate_pct = (
        drop_rate_pct
        if drop_rate_pct is not None
        else (total_dropped / total_enqueued * 100.0 if total_enqueued > 0 else 0.0)
    )
    persisted = tuple(dict.fromkeys(persisted_metric_names))
    if volatile_metric_names:
        volatile = tuple(dict.fromkeys(volatile_metric_names))
    else:
        volatile = tuple(
            metric_name
            for metric_name in _CRITICAL_INFRA_METRICS
            if metric_name not in set(persisted)
        )

    return InfraMetrics(
        queue_backlog=queue_backlog,
        backlog_high_water_mark=resolved_backlog_high_water_mark,
        reconnect_count=reconnect_count,
        stale_pairs=stale_pairs,
        stale_spike_count=stale_spike_count,
        recovery_retry_count=recovery_retry_count,
        dtr_loss_count=dtr_loss_count,
        log_loss_count=log_loss_count,
        total_enqueued=total_enqueued,
        total_dropped=total_dropped,
        drop_rate_pct=resolved_drop_rate_pct,
        elw_bps=elw_bps,
        expected_cost_bps=expected_cost_bps,
        realized_cost_bps=realized_cost_bps,
        partial_fill_count=partial_fill_count,
        fill_latency_ms_p95=fill_latency_ms_p95,
        reconciliation_alert_count=reconciliation_alert_count,
        kill_switch_active=kill_switch_active,
        kill_switch_timestamp_ms=kill_switch_timestamp_ms,
        persisted_metric_names=persisted,
        volatile_metric_names=volatile,
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
        backlog_warning=infra.queue_backlog > 50 or infra.backlog_high_water_mark > 100,
        stale_warning=stale_from_pairs or len(infra.stale_pairs) > 0 or infra.stale_spike_count > 0,
        loss_warning=(
            infra.dtr_loss_count > 0
            or infra.log_loss_count > 0
            or infra.kill_switch_active
        ),
    )


__all__ = [
    "collect_portfolio_metrics",
    "collect_engine_metrics",
    "collect_pair_metrics",
    "collect_infra_metrics",
    "collect_meta_metrics",
    "collect_monitoring_snapshot",
]
