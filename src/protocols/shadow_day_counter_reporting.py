"""Reporting helpers for shadow day counter artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import time

from protocols.contracts import (
    ShadowBuild14Contribution,
    ShadowBuild14ReaderContribution,
    ShadowEngineReport,
)
from protocols.shadow_day_counter_models import ShadowCounterState, ShadowDayRecord
from protocols.shadow_day_counter_report_rendering import (
    build_missing_sections,
    build_report_sections,
    build_shadow_report_artifact,
)

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
_REQUIRED_GLOBAL_METRICS = (
    "dtr_coverage",
    "ce_net",
    "estimated_cost_bps",
    "edge_net",
    "drawdown_pct",
    "stale_rate",
    "economic_pass_rate",
    "pair_health_ratio",
    "backlog_avg",
)
_REQUIRED_PORTFOLIO_METRICS = (
    "capital_simulated_usdt",
    "gross_exposure_shadow_pct",
    "loss_budget_shadow_pct",
    "capital_free_usdt",
    "beta_btc_shadow",
)
_REQUIRED_INFRA_METRICS = (
    "dtr_loss_rate",
    "log_loss_rate",
    "event_latency_ms",
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


FloatMetricMap = dict[str, float | None]


@dataclass(frozen=True)
class _ShadowReportComputation:
    global_metrics: FloatMetricMap
    portfolio_metrics: FloatMetricMap
    infra_metrics: FloatMetricMap
    decision_metrics: FloatMetricMap
    dominant_cluster: str
    pnl_shadow: float | None
    dtr_complete: bool
    decisions_reproducible: bool
    infra_stable: bool
    costs_plausible: bool
    break_even_visible: bool
    critical_alerts_visible: bool
    operator_actions_logged: bool
    ui_locked: bool
    go_no_go_rendered: bool
    inter_engine_comparison: tuple[ShadowEngineReport, ...]
    build14_contribution: tuple[ShadowBuild14Contribution, ...]
    build14_reader_contribution: tuple[ShadowBuild14ReaderContribution, ...]
    inter_engine_comparison_ready: bool
    build14_contribution_ready: bool
    data_infra_report_ready: bool
    decisions_dtr_report_ready: bool
    costs_break_even_report_ready: bool
    portfolio_report_ready: bool
    ui_alerting_report_ready: bool
    go_no_go_report_ready: bool
    missing_sections: list[str]
    rendered_sections: tuple[object, ...]


def _successful_daily_records(state: ShadowCounterState) -> list[ShadowDayRecord]:
    return [record for record in state.daily_records if record.passed_all_gates]


def _metric_values(records: list[ShadowDayRecord], metric_name: str) -> list[float]:
    values: list[float] = []
    for record in records:
        raw_value = record.metrics_summary.get(metric_name)
        if isinstance(raw_value, (int, float)):
            values.append(float(raw_value))
    return values


def _metric_average(records: list[ShadowDayRecord], metric_name: str) -> float | None:
    values = _metric_values(records, metric_name)
    if not values:
        return None
    return round(sum(values) / len(values), 8)


def _metric_flag(records: list[ShadowDayRecord], metric_name: str) -> bool:
    values = _metric_values(records, metric_name)
    return bool(values) and all(value >= 0.5 for value in values)


def _metric_sum(records: list[ShadowDayRecord], metric_name: str) -> float | None:
    values = _metric_values(records, metric_name)
    if not values:
        return None
    return round(sum(values), 8)


def _metric_latest(records: list[ShadowDayRecord], metric_name: str) -> float | None:
    for record in reversed(records):
        raw_value = record.metrics_summary.get(metric_name)
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
    return None


def _text_metric_latest(records: list[ShadowDayRecord], metric_name: str) -> str:
    for record in reversed(records):
        raw_value = record.metrics_summary.get(metric_name)
        if isinstance(raw_value, str) and raw_value.strip():
            return raw_value.strip()
    return ""


def _build_engine_report(
    records: list[ShadowDayRecord],
    engine_id: str,
) -> ShadowEngineReport | None:
    gross_frequency = _metric_average(records, f"{engine_id}.gross_frequency")
    useful_frequency = _metric_average(records, f"{engine_id}.useful_frequency")
    estimated_cost_bps = _metric_average(records, f"{engine_id}.estimated_cost_bps")
    edge_net = _metric_average(records, f"{engine_id}.edge_net")
    economic_pass_rate = _metric_average(records, f"{engine_id}.economic_pass_rate")
    conflict_rate = _metric_average(records, f"{engine_id}.conflict_rate")
    marginal_edge = _metric_average(records, f"{engine_id}.marginal_edge")
    observations = len(_metric_values(records, f"{engine_id}.gross_frequency"))
    if (
        gross_frequency is None
        or useful_frequency is None
        or estimated_cost_bps is None
        or edge_net is None
        or economic_pass_rate is None
        or conflict_rate is None
        or observations == 0
    ):
        return None
    return ShadowEngineReport(
        engine_id=engine_id,
        gross_frequency=gross_frequency,
        useful_frequency=useful_frequency,
        estimated_cost_bps=estimated_cost_bps,
        edge_net=edge_net,
        economic_pass_rate=economic_pass_rate,
        conflict_rate=conflict_rate,
        marginal_edge=marginal_edge or 0.0,
        observations=observations,
    )


def _build_build14_contribution(
    records: list[ShadowDayRecord],
    component_id: str,
) -> ShadowBuild14Contribution | None:
    contribution_score = _metric_average(records, f"{component_id}.contribution_score")
    interaction_score = _metric_average(records, f"{component_id}.interaction_score")
    observations = len(_metric_values(records, f"{component_id}.contribution_score"))
    if contribution_score is None or observations == 0:
        return None
    return ShadowBuild14Contribution(
        component_id=component_id,
        contribution_score=contribution_score,
        interaction_score=interaction_score or 0.0,
        observations=observations,
    )


def _build_build14_reader_contribution(
    records: list[ShadowDayRecord],
    reader_name: str,
) -> ShadowBuild14ReaderContribution | None:
    metric_prefix = f"build14_reader.{reader_name}"
    average_observed_value = _metric_average(records, f"{metric_prefix}.observed_value")
    average_severity_score = _metric_average(records, f"{metric_prefix}.severity_score")
    latest_status = _text_metric_latest(records, f"{metric_prefix}.status")
    signal_family = _text_metric_latest(records, f"{metric_prefix}.signal_family")
    latest_detail = _text_metric_latest(records, f"{metric_prefix}.detail")
    structured_log_key = _text_metric_latest(records, f"{metric_prefix}.structured_log_key")
    observations = len(_metric_values(records, f"{metric_prefix}.observed_value"))
    if (
        average_observed_value is None
        or average_severity_score is None
        or not latest_status
        or not signal_family
        or observations == 0
    ):
        return None
    return ShadowBuild14ReaderContribution(
        reader_name=reader_name,
        signal_family=signal_family,
        average_observed_value=average_observed_value,
        average_severity_score=average_severity_score,
        latest_status=latest_status,
        latest_detail=latest_detail,
        structured_log_key=structured_log_key,
        observations=observations,
    )


def _collect_metric_maps(
    successful_records: list[ShadowDayRecord],
) -> tuple[FloatMetricMap, FloatMetricMap, FloatMetricMap, FloatMetricMap, str, float | None]:
    global_metrics = {
        metric_name: _metric_average(successful_records, metric_name)
        for metric_name in _REQUIRED_GLOBAL_METRICS
    }
    portfolio_metrics = {
        metric_name: _metric_latest(successful_records, metric_name)
        for metric_name in _REQUIRED_PORTFOLIO_METRICS
    }
    infra_metrics = {
        metric_name: _metric_average(successful_records, metric_name)
        for metric_name in _REQUIRED_INFRA_METRICS
    }
    decision_metrics = {
        "hard_block_rate": _metric_average(successful_records, "hard_block_rate"),
        "phantom_trade_count": _metric_sum(successful_records, "phantom_trade_count"),
    }
    dominant_cluster = _text_metric_latest(successful_records, "dominant_cluster")
    pnl_shadow = _metric_sum(successful_records, "pnl_shadow")
    return (
        global_metrics,
        portfolio_metrics,
        infra_metrics,
        decision_metrics,
        dominant_cluster,
        pnl_shadow,
    )


def _collect_status_flags(
    successful_records: list[ShadowDayRecord],
) -> tuple[bool, bool, bool, bool, bool, bool, bool, bool, bool]:
    dtr_complete = _metric_flag(successful_records, "dtr_complete")
    decisions_reproducible = _metric_flag(successful_records, "decisions_reproducible")
    infra_stable = _metric_flag(successful_records, "infra_stable")
    costs_plausible = _metric_flag(successful_records, "costs_plausible")
    break_even_visible = _metric_flag(successful_records, "break_even_visible")
    critical_alerts_visible = _metric_flag(successful_records, "critical_alerts_visible")
    operator_actions_logged = _metric_flag(successful_records, "operator_actions_logged")
    ui_locked = _metric_flag(successful_records, "ui_locked")
    go_no_go_rendered = _metric_flag(successful_records, "go_no_go_rendered")
    return (
        dtr_complete,
        decisions_reproducible,
        infra_stable,
        costs_plausible,
        break_even_visible,
        critical_alerts_visible,
        operator_actions_logged,
        ui_locked,
        go_no_go_rendered,
    )


def _collect_component_reports(
    successful_records: list[ShadowDayRecord],
) -> tuple[
    tuple[ShadowEngineReport, ...],
    tuple[ShadowBuild14Contribution, ...],
    tuple[ShadowBuild14ReaderContribution, ...],
]:
    inter_engine_comparison = tuple(
        report
        for engine_id in _REQUIRED_ENGINE_IDS
        if (report := _build_engine_report(successful_records, engine_id)) is not None
    )
    build14_contribution = tuple(
        contribution
        for component_id in _REQUIRED_BUILD14_IDS
        if (
            contribution := _build_build14_contribution(
                successful_records,
                component_id,
            )
        )
        is not None
    )
    build14_reader_contribution = tuple(
        contribution
        for reader_name in _OPTIONAL_BUILD14_READER_IDS
        if (
            contribution := _build_build14_reader_contribution(
                successful_records,
                reader_name,
            )
        )
        is not None
    )
    return (
        inter_engine_comparison,
        build14_contribution,
        build14_reader_contribution,
    )


def _evaluate_report_readiness(
    *,
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
    go_no_go_rendered: bool,
    inter_engine_comparison: tuple[ShadowEngineReport, ...],
    build14_contribution: tuple[ShadowBuild14Contribution, ...],
) -> tuple[bool, bool, bool, bool, bool, bool, bool, bool]:
    inter_engine_comparison_ready = len(inter_engine_comparison) == len(_REQUIRED_ENGINE_IDS)
    build14_contribution_ready = len(build14_contribution) == len(_REQUIRED_BUILD14_IDS)
    data_infra_report_ready = (
        infra_stable
        and all(value is not None for value in infra_metrics.values())
        and global_metrics["stale_rate"] is not None
        and global_metrics["pair_health_ratio"] is not None
        and global_metrics["backlog_avg"] is not None
    )
    decisions_dtr_report_ready = (
        dtr_complete
        and decisions_reproducible
        and global_metrics["dtr_coverage"] is not None
        and decision_metrics["hard_block_rate"] is not None
        and decision_metrics["phantom_trade_count"] is not None
    )
    costs_break_even_report_ready = (
        costs_plausible
        and break_even_visible
        and global_metrics["estimated_cost_bps"] is not None
        and global_metrics["edge_net"] is not None
        and global_metrics["economic_pass_rate"] is not None
    )
    portfolio_report_ready = (
        global_metrics["ce_net"] is not None
        and pnl_shadow is not None
        and all(value is not None for value in portfolio_metrics.values())
        and bool(dominant_cluster)
    )
    ui_alerting_report_ready = (
        critical_alerts_visible and operator_actions_logged and ui_locked
    )
    go_no_go_report_ready = go_no_go_rendered
    return (
        inter_engine_comparison_ready,
        build14_contribution_ready,
        data_infra_report_ready,
        decisions_dtr_report_ready,
        costs_break_even_report_ready,
        portfolio_report_ready,
        ui_alerting_report_ready,
        go_no_go_report_ready,
    )


def _build_render_state(
    *,
    state: ShadowCounterState,
    successful_records: list[ShadowDayRecord],
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
) -> tuple[list[str], tuple[object, ...]]:
    missing_sections = build_missing_sections(
        state=state,
        global_metrics=global_metrics,
        portfolio_metrics=portfolio_metrics,
        infra_metrics=infra_metrics,
        decision_metrics=decision_metrics,
        dominant_cluster=dominant_cluster,
        successful_records=successful_records,
        metric_flag=_metric_flag,
        dtr_complete=dtr_complete,
        decisions_reproducible=decisions_reproducible,
        infra_stable=infra_stable,
        costs_plausible=costs_plausible,
        data_infra_report_ready=data_infra_report_ready,
        decisions_dtr_report_ready=decisions_dtr_report_ready,
        costs_break_even_report_ready=costs_break_even_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        portfolio_report_ready=portfolio_report_ready,
        ui_alerting_report_ready=ui_alerting_report_ready,
        go_no_go_report_ready=go_no_go_report_ready,
    )
    rendered_sections = build_report_sections(
        global_metrics=global_metrics,
        infra_metrics=infra_metrics,
        decision_metrics=decision_metrics,
        portfolio_metrics=portfolio_metrics,
        dominant_cluster=dominant_cluster,
        critical_alerts_visible=critical_alerts_visible,
        operator_actions_logged=operator_actions_logged,
        ui_locked=ui_locked,
        go_no_go_report_ready=go_no_go_report_ready,
        data_infra_report_ready=data_infra_report_ready,
        decisions_dtr_report_ready=decisions_dtr_report_ready,
        costs_break_even_report_ready=costs_break_even_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=build14_contribution,
        build14_reader_contribution=build14_reader_contribution,
        pnl_shadow=pnl_shadow,
    )
    return missing_sections, rendered_sections


def _compute_shadow_report(state: ShadowCounterState) -> _ShadowReportComputation:
    successful_records = _successful_daily_records(state)
    (
        global_metrics,
        portfolio_metrics,
        infra_metrics,
        decision_metrics,
        dominant_cluster,
        pnl_shadow,
    ) = _collect_metric_maps(successful_records)
    (
        dtr_complete,
        decisions_reproducible,
        infra_stable,
        costs_plausible,
        break_even_visible,
        critical_alerts_visible,
        operator_actions_logged,
        ui_locked,
        go_no_go_rendered,
    ) = _collect_status_flags(successful_records)
    (
        inter_engine_comparison,
        build14_contribution,
        build14_reader_contribution,
    ) = _collect_component_reports(successful_records)
    (
        inter_engine_comparison_ready,
        build14_contribution_ready,
        data_infra_report_ready,
        decisions_dtr_report_ready,
        costs_break_even_report_ready,
        portfolio_report_ready,
        ui_alerting_report_ready,
        go_no_go_report_ready,
    ) = _evaluate_report_readiness(
        global_metrics=global_metrics,
        portfolio_metrics=portfolio_metrics,
        infra_metrics=infra_metrics,
        decision_metrics=decision_metrics,
        dominant_cluster=dominant_cluster,
        pnl_shadow=pnl_shadow,
        dtr_complete=dtr_complete,
        decisions_reproducible=decisions_reproducible,
        infra_stable=infra_stable,
        costs_plausible=costs_plausible,
        break_even_visible=break_even_visible,
        critical_alerts_visible=critical_alerts_visible,
        operator_actions_logged=operator_actions_logged,
        ui_locked=ui_locked,
        go_no_go_rendered=go_no_go_rendered,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=build14_contribution,
    )
    missing_sections, rendered_sections = _build_render_state(
        state=state,
        successful_records=successful_records,
        global_metrics=global_metrics,
        portfolio_metrics=portfolio_metrics,
        infra_metrics=infra_metrics,
        decision_metrics=decision_metrics,
        dominant_cluster=dominant_cluster,
        pnl_shadow=pnl_shadow,
        dtr_complete=dtr_complete,
        decisions_reproducible=decisions_reproducible,
        infra_stable=infra_stable,
        costs_plausible=costs_plausible,
        critical_alerts_visible=critical_alerts_visible,
        operator_actions_logged=operator_actions_logged,
        ui_locked=ui_locked,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        data_infra_report_ready=data_infra_report_ready,
        decisions_dtr_report_ready=decisions_dtr_report_ready,
        costs_break_even_report_ready=costs_break_even_report_ready,
        portfolio_report_ready=portfolio_report_ready,
        ui_alerting_report_ready=ui_alerting_report_ready,
        go_no_go_report_ready=go_no_go_report_ready,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=build14_contribution,
        build14_reader_contribution=build14_reader_contribution,
    )
    return _ShadowReportComputation(
        global_metrics=global_metrics,
        portfolio_metrics=portfolio_metrics,
        infra_metrics=infra_metrics,
        decision_metrics=decision_metrics,
        dominant_cluster=dominant_cluster,
        pnl_shadow=pnl_shadow,
        dtr_complete=dtr_complete,
        decisions_reproducible=decisions_reproducible,
        infra_stable=infra_stable,
        costs_plausible=costs_plausible,
        break_even_visible=break_even_visible,
        critical_alerts_visible=critical_alerts_visible,
        operator_actions_logged=operator_actions_logged,
        ui_locked=ui_locked,
        go_no_go_rendered=go_no_go_rendered,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=build14_contribution,
        build14_reader_contribution=build14_reader_contribution,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        data_infra_report_ready=data_infra_report_ready,
        decisions_dtr_report_ready=decisions_dtr_report_ready,
        costs_break_even_report_ready=costs_break_even_report_ready,
        portfolio_report_ready=portfolio_report_ready,
        ui_alerting_report_ready=ui_alerting_report_ready,
        go_no_go_report_ready=go_no_go_report_ready,
        missing_sections=missing_sections,
        rendered_sections=rendered_sections,
    )


def generate_shadow_report(state: ShadowCounterState) -> dict[str, object]:
    """Generate the governed shadow promotion report."""

    computed = _compute_shadow_report(state)
    report = build_shadow_report_artifact(
        state=state,
        global_metrics=computed.global_metrics,
        portfolio_metrics=computed.portfolio_metrics,
        infra_metrics=computed.infra_metrics,
        decision_metrics=computed.decision_metrics,
        dominant_cluster=computed.dominant_cluster,
        pnl_shadow=computed.pnl_shadow,
        dtr_complete=computed.dtr_complete,
        decisions_reproducible=computed.decisions_reproducible,
        infra_stable=computed.infra_stable,
        costs_plausible=computed.costs_plausible,
        break_even_visible=computed.break_even_visible,
        critical_alerts_visible=computed.critical_alerts_visible,
        operator_actions_logged=computed.operator_actions_logged,
        ui_locked=computed.ui_locked,
        inter_engine_comparison_ready=computed.inter_engine_comparison_ready,
        build14_contribution_ready=computed.build14_contribution_ready,
        data_infra_report_ready=computed.data_infra_report_ready,
        decisions_dtr_report_ready=computed.decisions_dtr_report_ready,
        costs_break_even_report_ready=computed.costs_break_even_report_ready,
        portfolio_report_ready=computed.portfolio_report_ready,
        ui_alerting_report_ready=computed.ui_alerting_report_ready,
        go_no_go_report_ready=computed.go_no_go_report_ready,
        inter_engine_comparison=computed.inter_engine_comparison,
        build14_contribution=computed.build14_contribution,
        build14_reader_contribution=computed.build14_reader_contribution,
        missing_sections=computed.missing_sections,
        rendered_sections=computed.rendered_sections,
    )
    return report.model_dump(mode="json")


__all__ = ["generate_shadow_report"]
