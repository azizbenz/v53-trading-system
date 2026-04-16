"""Rendering helpers for shadow day counter report artifacts."""

from __future__ import annotations

import time
from typing import Callable

from protocols.contracts import (
    ShadowBuild14Contribution,
    ShadowBuild14ReaderContribution,
    ShadowEngineReport,
    ShadowReportArtifact,
    ShadowReportSection,
)
from protocols.shadow_day_counter_models import ShadowCounterState, ShadowDayRecord

FloatMetricMap = dict[str, float | None]

_REQUIRED_ENGINE_IDS = ("engine_a", "engine_b", "engine_c", "engine_d")
_REQUIRED_BUILD14_IDS = (
    "build14_microstructure",
    "build14_regime",
    "build14_covariance",
    "build14_risk_contribution",
    "build14_edge_diversity",
)
_OPTIONAL_BUILD14_READER_IDS = (
    "market_toxicity_snapshot",
    "execution_fragility_score",
    "lob_deep_filter_vwa",
    "order_book_imbalance",
    "false_breakout_model",
    "hurst_regime_classifier",
    "competition_monitor",
)
_REQUIRED_BOOLEAN_FLAGS = (
    "dtr_complete",
    "decisions_reproducible",
    "infra_stable",
    "costs_plausible",
    "break_even_visible",
    "critical_alerts_visible",
    "operator_actions_logged",
    "ui_locked",
    "go_no_go_rendered",
)


def build_report_sections(
    *,
    global_metrics: FloatMetricMap,
    infra_metrics: FloatMetricMap,
    decision_metrics: FloatMetricMap,
    portfolio_metrics: FloatMetricMap,
    dominant_cluster: str,
    critical_alerts_visible: bool,
    operator_actions_logged: bool,
    ui_locked: bool,
    go_no_go_report_ready: bool,
    data_infra_report_ready: bool,
    decisions_dtr_report_ready: bool,
    costs_break_even_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    inter_engine_comparison: tuple[ShadowEngineReport, ...],
    build14_contribution: tuple[ShadowBuild14Contribution, ...],
    build14_reader_contribution: tuple[ShadowBuild14ReaderContribution, ...],
    pnl_shadow: float | None,
) -> tuple[ShadowReportSection, ...]:
    return (
        ShadowReportSection(
            section_id="data_infra_report",
            title="rapport stabilite data / infra",
            ready=data_infra_report_ready,
            summary=(
                f"stale={global_metrics['stale_rate'] if global_metrics['stale_rate'] is not None else 'n/a'} / "
                f"pair_health={global_metrics['pair_health_ratio'] if global_metrics['pair_health_ratio'] is not None else 'n/a'} / "
                f"dtr_loss={infra_metrics['dtr_loss_rate'] if infra_metrics['dtr_loss_rate'] is not None else 'n/a'} / "
                f"log_loss={infra_metrics['log_loss_rate'] if infra_metrics['log_loss_rate'] is not None else 'n/a'}"
            ),
        ),
        ShadowReportSection(
            section_id="decisions_dtr_report",
            title="rapport decisions & dtr",
            ready=decisions_dtr_report_ready,
            summary=(
                f"dtr={global_metrics['dtr_coverage'] if global_metrics['dtr_coverage'] is not None else 'n/a'} / "
                f"hard_block={decision_metrics['hard_block_rate'] if decision_metrics['hard_block_rate'] is not None else 'n/a'} / "
                f"phantom={decision_metrics['phantom_trade_count'] if decision_metrics['phantom_trade_count'] is not None else 'n/a'}"
            ),
        ),
        ShadowReportSection(
            section_id="costs_break_even_report",
            title="rapport couts & break-even",
            ready=costs_break_even_report_ready,
            summary=(
                f"cost_bps={global_metrics['estimated_cost_bps'] if global_metrics['estimated_cost_bps'] is not None else 'n/a'} / "
                f"edge={global_metrics['edge_net'] if global_metrics['edge_net'] is not None else 'n/a'} / "
                f"economic_pass={global_metrics['economic_pass_rate'] if global_metrics['economic_pass_rate'] is not None else 'n/a'}"
            ),
        ),
        ShadowReportSection(
            section_id="engine_comparison_report",
            title="rapport A vs B vs C vs D",
            ready=inter_engine_comparison_ready and build14_contribution_ready,
            summary=(
                f"engines={len(inter_engine_comparison)}/{len(_REQUIRED_ENGINE_IDS)} / "
                f"build14={len(build14_contribution)}/{len(_REQUIRED_BUILD14_IDS)} / "
                f"readers={len(build14_reader_contribution)}/{len(_OPTIONAL_BUILD14_READER_IDS)}"
            ),
        ),
        ShadowReportSection(
            section_id="portfolio_report",
            title="rapport portefeuille shadow",
            ready=(
                global_metrics["ce_net"] is not None
                and pnl_shadow is not None
                and all(value is not None for value in portfolio_metrics.values())
                and bool(dominant_cluster)
            ),
            summary=(
                f"ce={global_metrics['ce_net'] if global_metrics['ce_net'] is not None else 'n/a'} / "
                f"pnl={pnl_shadow if pnl_shadow is not None else 'n/a'} / "
                f"beta={portfolio_metrics['beta_btc_shadow'] if portfolio_metrics['beta_btc_shadow'] is not None else 'n/a'} / "
                f"cluster={dominant_cluster or 'n/a'}"
            ),
        ),
        ShadowReportSection(
            section_id="ui_alerting_report",
            title="rapport ui / alerting",
            ready=critical_alerts_visible and operator_actions_logged and ui_locked,
            summary=(
                f"critical_alerts={'yes' if critical_alerts_visible else 'no'} / "
                f"operator_log={'yes' if operator_actions_logged else 'no'} / "
                f"ui_locked={'yes' if ui_locked else 'no'}"
            ),
        ),
        ShadowReportSection(
            section_id="go_no_go_report",
            title="verdict go / no-go micro-live",
            ready=go_no_go_report_ready,
            summary="go/no-go rendered" if go_no_go_report_ready else "go/no-go missing",
        ),
    )


def build_missing_sections(
    *,
    state: ShadowCounterState,
    global_metrics: FloatMetricMap,
    portfolio_metrics: FloatMetricMap,
    infra_metrics: FloatMetricMap,
    decision_metrics: FloatMetricMap,
    dominant_cluster: str,
    successful_records: list[ShadowDayRecord],
    metric_flag: Callable[[list[ShadowDayRecord], str], bool],
    dtr_complete: bool,
    decisions_reproducible: bool,
    infra_stable: bool,
    costs_plausible: bool,
    data_infra_report_ready: bool,
    decisions_dtr_report_ready: bool,
    costs_break_even_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    portfolio_report_ready: bool,
    ui_alerting_report_ready: bool,
    go_no_go_report_ready: bool,
) -> list[str]:
    missing_sections: list[str] = []
    if not state.is_complete:
        missing_sections.append("30_day_counter")
    if not dtr_complete:
        missing_sections.append("dtr_complete")
    if not decisions_reproducible:
        missing_sections.append("decisions_reproducible")
    if not infra_stable:
        missing_sections.append("infra_stable")
    if not costs_plausible:
        missing_sections.append("costs_plausible")
    for metric_name, value in global_metrics.items():
        if value is None:
            missing_sections.append(metric_name)
    for metric_name, value in portfolio_metrics.items():
        if value is None:
            missing_sections.append(metric_name)
    for metric_name, value in infra_metrics.items():
        if value is None:
            missing_sections.append(metric_name)
    for metric_name, value in decision_metrics.items():
        if value is None:
            missing_sections.append(metric_name)
    if not dominant_cluster:
        missing_sections.append("dominant_cluster")
    for metric_name in _REQUIRED_BOOLEAN_FLAGS:
        if not metric_flag(successful_records, metric_name):
            missing_sections.append(metric_name)
    if not data_infra_report_ready:
        missing_sections.append("data_infra_report")
    if not decisions_dtr_report_ready:
        missing_sections.append("decisions_dtr_report")
    if not costs_break_even_report_ready:
        missing_sections.append("costs_break_even_report")
    if not inter_engine_comparison_ready:
        missing_sections.append("inter_engine_comparison")
    if not build14_contribution_ready:
        missing_sections.append("build14_contribution")
    if not portfolio_report_ready:
        missing_sections.append("portfolio_report")
    if not ui_alerting_report_ready:
        missing_sections.append("ui_alerting_report")
    if not go_no_go_report_ready:
        missing_sections.append("go_no_go_report")
    return missing_sections


def build_shadow_report_artifact(
    *,
    state: ShadowCounterState,
    global_metrics: FloatMetricMap,
    portfolio_metrics: FloatMetricMap,
    infra_metrics: FloatMetricMap,
    decision_metrics: FloatMetricMap,
    dominant_cluster: str,
    pnl_shadow: float | None,
    dtr_complete: bool,
    decisions_reproducible: bool,
    infra_stable: bool,
    costs_plausible: bool,
    break_even_visible: bool,
    critical_alerts_visible: bool,
    operator_actions_logged: bool,
    ui_locked: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    data_infra_report_ready: bool,
    decisions_dtr_report_ready: bool,
    costs_break_even_report_ready: bool,
    portfolio_report_ready: bool,
    ui_alerting_report_ready: bool,
    go_no_go_report_ready: bool,
    inter_engine_comparison: tuple[ShadowEngineReport, ...],
    build14_contribution: tuple[ShadowBuild14Contribution, ...],
    build14_reader_contribution: tuple[ShadowBuild14ReaderContribution, ...],
    missing_sections: list[str],
    rendered_sections: tuple[ShadowReportSection, ...],
) -> ShadowReportArtifact:
    return ShadowReportArtifact(
        report_id=f"shadow_report:{state.profile.value}:{state.consecutive_days}",
        profile=state.profile.value,
        report_generated_at=time.time(),
        consecutive_days=state.consecutive_days,
        required_days=state.required_days,
        remaining_days=state.remaining_days,
        is_complete=state.is_complete,
        started_at=state.started_at,
        last_shadow_timestamp=state.last_shadow_timestamp,
        total_resets=state.resets,
        daily_records_count=len(state.daily_records),
        dtr_coverage=global_metrics["dtr_coverage"],
        dtr_complete=dtr_complete,
        ce_net=global_metrics["ce_net"],
        estimated_cost_bps=global_metrics["estimated_cost_bps"],
        edge_net=global_metrics["edge_net"],
        drawdown_pct=global_metrics["drawdown_pct"],
        stale_rate=global_metrics["stale_rate"],
        economic_pass_rate=global_metrics["economic_pass_rate"],
        pair_health_ratio=global_metrics["pair_health_ratio"],
        backlog_avg=global_metrics["backlog_avg"],
        capital_simulated_usdt=portfolio_metrics["capital_simulated_usdt"],
        gross_exposure_shadow_pct=portfolio_metrics["gross_exposure_shadow_pct"],
        loss_budget_shadow_pct=portfolio_metrics["loss_budget_shadow_pct"],
        capital_free_usdt=portfolio_metrics["capital_free_usdt"],
        beta_btc_shadow=portfolio_metrics["beta_btc_shadow"],
        dominant_cluster=dominant_cluster,
        pnl_shadow=pnl_shadow,
        dtr_loss_rate=infra_metrics["dtr_loss_rate"],
        log_loss_rate=infra_metrics["log_loss_rate"],
        event_latency_ms=infra_metrics["event_latency_ms"],
        hard_block_rate=decision_metrics["hard_block_rate"],
        phantom_trade_count=(
            int(decision_metrics["phantom_trade_count"])
            if decision_metrics["phantom_trade_count"] is not None
            else None
        ),
        decisions_reproducible=decisions_reproducible,
        infra_stable=infra_stable,
        costs_plausible=costs_plausible,
        break_even_visible=break_even_visible,
        critical_alerts_visible=critical_alerts_visible,
        operator_actions_logged=operator_actions_logged,
        ui_locked=ui_locked,
        shadow_report_ready=not missing_sections,
        data_infra_report_ready=data_infra_report_ready,
        decisions_dtr_report_ready=decisions_dtr_report_ready,
        costs_break_even_report_ready=costs_break_even_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        portfolio_report_ready=portfolio_report_ready,
        ui_alerting_report_ready=ui_alerting_report_ready,
        go_no_go_report_ready=go_no_go_report_ready,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=build14_contribution,
        build14_reader_contribution=build14_reader_contribution,
        rendered_sections=rendered_sections,
        missing_sections=tuple(missing_sections),
    )


__all__ = [
    "build_missing_sections",
    "build_report_sections",
    "build_shadow_report_artifact",
]
