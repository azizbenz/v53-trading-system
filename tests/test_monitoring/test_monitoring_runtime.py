"""Tests for the Build-10 runtime orchestration path."""

from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import SterilizationClass, SterilizationResult
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification, EdgeStatus
from monitoring import (
    MonitoringRuntime,
    MonitoringRuntimeConfig,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_pair_metrics,
    collect_portfolio_metrics,
)


def _scratch_dir(name: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "monitoring_runtime_tests" / name


def _meta_metrics():
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-runtime-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1000.0,
            ),
            build_dtr(
                dtr_id="dtr-runtime-2",
                pair="ETHUSDT",
                engine_id="engine_b",
                decision_state=DecisionState.REJECTED_RANKING,
                timestamp=1001.0,
            ),
        ),
        total_opportunities=3,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.1,
            ),
            SterilizationResult(
                pair="ETHUSDT",
                engine_id="engine_b",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.5,
                phantom_risk_score=0.8,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_b",
                sterilization_rate=0.5,
                total_trades=2,
                sterilized_count=1,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=12,
                mean_realized_cost=0.0015,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0005,
                profitable_rate=0.4,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.002,
                standard_error=0.0003,
                sample_size=24,
                sharpe_per_trade=0.3,
                mean_cost_p90=0.001,
                ce_observed=0.0005,
                cluster_utilization=0.2,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0004,
                sample_size=24,
                sharpe_per_trade=-0.1,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.4,
            ),
        )
    )
    return collect_meta_metrics(
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
        future_learning_diagnostics=2,
        future_learning_hypotheses=1,
    )


def test_monitoring_runtime_chains_build10_path_end_to_end():
    runtime = MonitoringRuntime()

    result = runtime.evaluate(
        correlation_id="corr-runtime",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.3,
            capital_deployed_usdt=1200.0,
            ce_net=0.0012,
        ),
        infra=collect_infra_metrics(
            queue_backlog=40,
            backlog_high_water_mark=600,
            total_enqueued=100,
            total_dropped=12,
            recovery_retry_count=4,
            kill_switch_active=True,
            kill_switch_timestamp_ms=1_700_000_000_123,
            persisted_metric_names=("backlog_high_water_mark", "drop_rate_pct", "kill_switch_active"),
        ),
        meta=_meta_metrics(),
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=12.0,
                expected_cost_bps=4.0,
                ce_expected=0.0007,
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=4.0,
                expected_cost_bps=3.0,
                ce_expected=0.0002,
                stale=True,
            ),
        ),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=9000,
                backlog_depth=40,
            ),
        ),
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
    )

    alert_ids = {alert.alert_id for alert in result.snapshot.alerts}
    assert f"{result.snapshot.correlation_id}:kill_switch_active" in alert_ids
    assert f"{result.snapshot.correlation_id}:drop_rate_high" in alert_ids
    assert f"{result.snapshot.correlation_id}:snapshot_trompeur" in alert_ids
    assert f"{result.snapshot.correlation_id}:observability_gap" in alert_ids

    alerts_section = next(
        section for section in result.technical_view.sections if section.title == "Alerts"
    )
    assert any(card.key == "infra_guardrails" for card in alerts_section.cards)
    assert any(card.key == "observability_surface" for card in alerts_section.cards)
    assert any(card.key == "operator_events" for card in alerts_section.cards)
    assert any(card.key == "operator_notifications" for card in alerts_section.cards)
    assert result.health_payload.kill_switch_active is True
    assert result.health_payload.deployment_state.value == "halted"
    assert result.health_payload.last_transition_summary == "kill_switch_active -> halted"
    assert result.health_payload.shadow_status == "healthy"
    assert result.health_payload.micro_live_status == "planned"
    assert result.health_payload.live_light_status == "planned"
    assert result.health_payload.operator_runtime.event_count == 1
    assert result.health_payload.operator_runtime.latest_event_message == "screen opened: overview"
    assert result.health_payload.operator_runtime.pending_notification_count == 2
    assert result.technical_payload.alerts.backlog_high_water_mark == 600
    assert result.technical_payload.alerts.drop_rate_pct == 12.0
    assert result.technical_payload.alerts.operator_runtime.pending_notification_count == 2
    assert any(
        sample.name == "v53_alert_metric_persistence"
        and sample.labels.get("persistence") == "volatile"
        for sample in result.observability_export.samples
    )
    assert any(
        sample.name == "v53_alert_operator_pending_notification_count"
        and sample.value == 2.0
        for sample in result.observability_export.samples
    )
    assert any(
        sample.name == "v53_alert_operator_recent_event"
        and sample.labels.get("event_type") == "screen_opened"
        for sample in result.observability_export.samples
    )
    light_titles = {section.title for section in result.light_view.sections}
    assert {"Pairs", "Engines", "Risk", "Execution", "Data & Infra", "Alerts & Events"}.issubset(light_titles)
    assert result.light_view.pending_notifications
    assert result.light_view.pending_notifications[0].alert_id == "corr-runtime:loss"
    assert len(result.light_view.pending_notifications) == 2
    assert result.light_view.event_log[0].message == "screen opened: overview"
    light_profile = next(section for section in result.light_view.sections if section.title == "Profile & State")
    assert any(card.key == "deployment_state" and card.value == "halted" for card in light_profile.cards)
    assert any(card.key == "last_transition" and card.value == "kill_switch_active -> halted" for card in light_profile.cards)
    light_alerts = next(section for section in result.light_view.sections if section.title == "Alerts & Events")
    assert any(card.key == "operator_events" and card.detail == "screen opened: overview" for card in light_alerts.cards)
    assert any(card.key == "critical_notifications" and card.value == "pending=2 / ack=0" for card in light_alerts.cards)


def test_monitoring_runtime_tracks_session_high_water_mark_and_stale_spikes():
    runtime = MonitoringRuntime()

    first = runtime.evaluate(
        correlation_id="corr-runtime-1",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=250.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(
            queue_backlog=20,
            persisted_metric_names=("backlog_high_water_mark",),
        ),
        meta=_meta_metrics(),
    )
    second = runtime.evaluate(
        correlation_id="corr-runtime-2",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_500,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=250.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(
            queue_backlog=5,
            persisted_metric_names=("backlog_high_water_mark", "stale_spike_count"),
        ),
        meta=_meta_metrics(),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=12_000,
            ),
        ),
    )

    assert first.snapshot.infra.backlog_high_water_mark == 20
    assert first.snapshot.infra.stale_spike_count == 0
    assert second.snapshot.infra.backlog_high_water_mark == 20
    assert second.snapshot.infra.stale_spike_count == 1


def test_monitoring_runtime_tracks_alert_open_and_resolution_history():
    runtime = MonitoringRuntime()

    opened = runtime.evaluate(
        correlation_id="corr-runtime-open",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=15.0,
            loss_capacity_used_pct=3.0,
            beta_utilization=0.1,
            capital_deployed_usdt=200.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(queue_backlog=80),
        meta=_meta_metrics(),
    )
    resolved = runtime.evaluate(
        correlation_id="corr-runtime-resolved",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_500,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=15.0,
            loss_capacity_used_pct=3.0,
            beta_utilization=0.1,
            capital_deployed_usdt=200.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(queue_backlog=0),
        meta=_meta_metrics(),
    )

    assert any(entry.alert_id.endswith(":backlog") and entry.status == "open" for entry in opened.health_payload.alert_history)
    assert any(
        entry.alert_id.endswith(":backlog")
        and entry.status == "resolved"
        and entry.resolved_ms == 1_700_000_000_500
        for entry in resolved.health_payload.alert_history
    )


def test_monitoring_runtime_persists_guardrail_state_across_restart():
    state_dir = _scratch_dir("persist")
    config = MonitoringRuntimeConfig(
        state_dir=state_dir,
        persist_runtime_state=True,
    )
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        first_runtime = MonitoringRuntime(config=config)
        first = first_runtime.evaluate(
            correlation_id="corr-runtime-persist-1",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            timestamp_ms=1_700_000_001_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=10.0,
                loss_capacity_used_pct=2.0,
                beta_utilization=0.1,
                capital_deployed_usdt=250.0,
                ce_net=0.001,
            ),
            infra=collect_infra_metrics(queue_backlog=90),
            meta=_meta_metrics(),
        )
        restarted_runtime = MonitoringRuntime(config=config)
        second = restarted_runtime.evaluate(
            correlation_id="corr-runtime-persist-2",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            timestamp_ms=1_700_000_001_500,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=10.0,
                loss_capacity_used_pct=2.0,
                beta_utilization=0.1,
                capital_deployed_usdt=250.0,
                ce_net=0.001,
            ),
            infra=collect_infra_metrics(queue_backlog=5),
            meta=_meta_metrics(),
        )

        assert first.state_path.endswith("monitoring_runtime_state.json")
        assert second.snapshot.infra.backlog_high_water_mark == 90
        assert any(
            entry.alert_id.endswith(":backlog")
            and entry.status == "resolved"
            and entry.resolved_ms == 1_700_000_001_500
            for entry in second.health_payload.alert_history
        )
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
