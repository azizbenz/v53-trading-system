"""Helpers to materialize Build-11 daily Shadow report metrics from real runtime payloads."""

from __future__ import annotations

from typing import Mapping

from interface_contracts import PairHealthLevel
from monitoring import TechnicalDashboardPayload
from protocols.contracts import ShadowRunSummary
from protocols.enums import ShadowComponentVerdict


def _average(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


_BUILD14_READER_STATUS_SCORES = {
    "nominal": 0.0,
    "elevated": 0.5,
    "critical": 1.0,
}


def build_shadow_daily_metrics_summary(
    payload: TechnicalDashboardPayload,
    shadow_summary: ShadowRunSummary,
    *,
    capital_simulated_usdt: float,
    replay_metrics_payload: Mapping[str, object] | None = None,
    hard_block_rate: float = 0.0,
    phantom_trade_count: int = 0,
    operator_actions_logged: bool | None = None,
    ui_locked: bool = True,
    go_no_go_rendered: bool = True,
) -> dict[str, float | str]:
    """Project a Build-10 technical payload + Build-11 run summary into daily report metrics.

    This bridges the operated Shadow runtime to the Build-11 day counter so daily
    reports no longer rely on handwritten metric dictionaries.
    """

    replay_metrics = replay_metrics_payload or {}
    engine_count = max(1, len(payload.engines))
    pair_count = max(1, len(payload.pairs))
    resolved_dtr_coverage = float(
        replay_metrics.get("dtr_coverage", payload.build9_meta.dtr_coverage)
    )
    replay_total_opportunities = int(replay_metrics.get("total_opportunities", 0) or 0)
    replay_total_records = int(replay_metrics.get("total_records", 0) or 0)
    replay_hard_blocked_count = int(
        replay_metrics.get("hard_blocked_count", max(int(hard_block_rate), 0)) or 0
    )
    replay_phantom_count = int(
        replay_metrics.get("phantom_count", max(phantom_trade_count, 0)) or 0
    )
    resolved_hard_block_rate = (
        replay_hard_blocked_count / replay_total_opportunities
        if replay_total_opportunities > 0
        else min(max(hard_block_rate, 0.0), 1.0)
    )
    expected_cost_bps = (
        payload.infra.expected_cost_bps
        if payload.infra.expected_cost_bps > 0.0
        else _average(tuple(engine.expected_cost_bps for engine in payload.engines))
    )
    edge_net = round(
        _average(tuple(engine.net_edge_bps for engine in payload.engines)) / 10_000.0,
        8,
    )
    drawdown_pct = round(
        max((engine.drawdown_pct for engine in payload.engines), default=0.0) / 100.0,
        8,
    )
    healthy_pairs = sum(
        1 for pair in payload.pairs if pair.health == PairHealthLevel.HEALTHY
    )
    stale_rate = round(payload.alerts.stale_pair_count / pair_count, 8)
    pair_health_ratio = round(healthy_pairs / pair_count, 8)
    economic_pass_rate = round(
        sum(
            1
            for engine in payload.engines
            if engine.net_edge_bps > engine.expected_cost_bps
        )
        / engine_count,
        8,
    )
    total_enqueued = max(payload.infra.total_enqueued, 1)
    inferred_operator_log = (
        operator_actions_logged
        if operator_actions_logged is not None
        else payload.alerts.operator_runtime.event_count > 0
    )
    capital_free_usdt = max(
        capital_simulated_usdt - payload.portfolio.capital_deployed_usdt,
        0.0,
    )
    metrics: dict[str, float | str] = {
        "dtr_coverage": resolved_dtr_coverage,
        "ce_net": payload.portfolio.ce_net,
        "estimated_cost_bps": expected_cost_bps,
        "edge_net": edge_net,
        "drawdown_pct": drawdown_pct,
        "stale_rate": stale_rate,
        "economic_pass_rate": economic_pass_rate,
        "pair_health_ratio": pair_health_ratio,
        "backlog_avg": float(payload.infra.queue_backlog),
        "capital_simulated_usdt": float(capital_simulated_usdt),
        "gross_exposure_shadow_pct": payload.portfolio.gross_capacity_used_pct,
        "loss_budget_shadow_pct": payload.portfolio.loss_capacity_used_pct,
        "capital_free_usdt": capital_free_usdt,
        "beta_btc_shadow": payload.portfolio.beta_utilization,
        "dominant_cluster": payload.portfolio.dominant_cluster or "unclustered",
        "pnl_shadow": payload.portfolio.pnl_net_usdt,
        "dtr_loss_rate": payload.infra.dtr_loss_count / total_enqueued,
        "log_loss_rate": payload.infra.log_loss_count / total_enqueued,
        "event_latency_ms": float(payload.infra.fill_latency_ms_p95),
        "hard_block_rate": resolved_hard_block_rate,
        "phantom_trade_count": float(replay_phantom_count),
        "dtr_complete": (
            1.0
            if (
                resolved_dtr_coverage >= 0.95
                and (
                    replay_total_opportunities == 0
                    or replay_total_records >= replay_total_opportunities
                )
            )
            else 0.0
        ),
        "decisions_reproducible": (
            1.0 if shadow_summary.blocking_comparison_count == 0 else 0.0
        ),
        "infra_stable": (
            1.0
            if not payload.infra.kill_switch_active
            and payload.alerts.queue_backlog <= 25
            and payload.infra.dtr_loss_count == 0
            and payload.infra.log_loss_count == 0
            else 0.0
        ),
        "costs_plausible": 1.0 if expected_cost_bps > 0.0 else 0.0,
        "break_even_visible": (
            1.0 if bool(payload.build9_meta.break_even_state.strip()) else 0.0
        ),
        "critical_alerts_visible": 1.0,
        "operator_actions_logged": 1.0 if inferred_operator_log else 0.0,
        "ui_locked": 1.0 if ui_locked else 0.0,
        "go_no_go_rendered": 1.0 if go_no_go_rendered else 0.0,
    }
    for engine in payload.engines:
        useful_frequency = (
            engine.useful_frequency
            if engine.useful_frequency > 0.0
            else float(engine.emitted_signals)
        )
        metrics[f"{engine.engine_id}.gross_frequency"] = float(engine.emitted_signals)
        metrics[f"{engine.engine_id}.useful_frequency"] = useful_frequency
        metrics[f"{engine.engine_id}.estimated_cost_bps"] = engine.expected_cost_bps
        metrics[f"{engine.engine_id}.edge_net"] = round(engine.net_edge_bps / 10_000.0, 8)
        metrics[f"{engine.engine_id}.economic_pass_rate"] = (
            1.0 if engine.net_edge_bps > engine.expected_cost_bps else 0.0
        )
        metrics[f"{engine.engine_id}.conflict_rate"] = 0.0
        metrics[f"{engine.engine_id}.marginal_edge"] = round(
            max(engine.net_edge_bps - engine.expected_cost_bps, 0.0) / 10_000.0,
            8,
        )
    for assessment in shadow_summary.component_assessments:
        if not assessment.component_id.startswith("build14_"):
            continue
        contribution_score = (
            1.0
            if assessment.verdict == ShadowComponentVerdict.SHADOW_VALIDATED
            else 0.0
        )
        metrics[f"{assessment.component_id}.contribution_score"] = contribution_score
        metrics[f"{assessment.component_id}.interaction_score"] = contribution_score
    for reader in payload.build14.reader_projections:
        metric_prefix = f"build14_reader.{reader.reader_name}"
        metrics[f"{metric_prefix}.observed_value"] = reader.observed_value
        metrics[f"{metric_prefix}.severity_score"] = _BUILD14_READER_STATUS_SCORES.get(
            reader.status, 0.0
        )
        metrics[f"{metric_prefix}.status"] = reader.status
        metrics[f"{metric_prefix}.signal_family"] = reader.signal_family
        metrics[f"{metric_prefix}.detail"] = reader.detail
        if reader.structured_log_key:
            metrics[f"{metric_prefix}.structured_log_key"] = reader.structured_log_key
    return metrics


__all__ = ["build_shadow_daily_metrics_summary"]
