"""Tests for alert_manager edge cases and coverage."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity, PairHealthLevel, ProfileId, RuntimeMode
from monitoring import (
    AlertLifecycleTracker,
    build_monitoring_alerts,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from monitoring.contracts import MonitoringSnapshot

from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import SterilizationClass, SterilizationResult
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification, EdgeStatus


def _clean_meta():
    dtr_summary = build_dtr_summary(
        (build_dtr(dtr_id="d1", pair="BTCUSDT", engine_id="engine_a",
                   decision_state=DecisionState.SELECTED, timestamp=1000.0),),
        total_opportunities=1,
    )
    cra_report = build_cra_report(
        (SterilizationResult(pair="BTCUSDT", engine_id="engine_a",
                             classification=SterilizationClass.HEALTHY,
                             multiplier=1.0, phantom_risk_score=0.05),),
        alerts=(),
    )
    be_report = build_break_even_report(
        (BreakEvenView(scope="engine_a", sample_size=20, mean_realized_cost=0.001,
                       mean_expected_cost=0.001, mean_cost_drift=0.0, profitable_rate=0.6),)
    )
    edge_report = build_edge_report(
        (EdgeClassification(scope="engine_a", status=EdgeStatus.CREDIBLE,
                            mean_net_return=0.003, standard_error=0.0003,
                            sample_size=30, sharpe_per_trade=0.5,
                            mean_cost_p90=0.001, ce_observed=0.0005,
                            cluster_utilization=0.15),)
    )
    return collect_meta_metrics(dtr_summary, cra_report, be_report, edge_report)


def _snapshot(**overrides):
    defaults = dict(
        correlation_id="corr-test",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1, gross_capacity_used_pct=20.0,
            loss_capacity_used_pct=5.0, beta_utilization=0.3,
            capital_deployed_usdt=500.0, ce_net=0.001,
        ),
        infra=collect_infra_metrics(),
        meta=_clean_meta(),
        engines=(),
        pairs=(),
    )
    defaults.update(overrides)
    return collect_monitoring_snapshot(**defaults)


class TestAlertManagerNoAlerts:
    def test_healthy_snapshot_produces_no_alerts(self):
        snapshot = _snapshot()
        alerts = build_monitoring_alerts(snapshot)
        assert alerts == ()

    def test_healthy_status_flags_all_false(self):
        snapshot = _snapshot()
        assert snapshot.stale_warning is False
        assert snapshot.backlog_warning is False
        assert snapshot.loss_warning is False


class TestAlertManagerStale:
    def test_stale_pair_triggers_stale_alert(self):
        snapshot = _snapshot(
            infra=collect_infra_metrics(stale_pairs=("BTCUSDT",)),
        )
        alerts = build_monitoring_alerts(snapshot)
        stale_alerts = [a for a in alerts if a.category == AlertCategory.DATA]
        assert len(stale_alerts) == 1
        assert stale_alerts[0].severity == AlertSeverity.WARNING
        assert "stale" in stale_alerts[0].message.lower()

    def test_stale_from_pair_health(self):
        snapshot = _snapshot(
            pairs=(collect_pair_metrics(pair="BTCUSDT", health=PairHealthLevel.STALE, freshness_ms=9000),),
        )
        assert snapshot.stale_warning is True

    def test_multiple_stale_pairs_count_in_message(self):
        snapshot = _snapshot(
            infra=collect_infra_metrics(stale_pairs=("BTCUSDT", "ETHUSDT", "BNBUSDT")),
        )
        alerts = build_monitoring_alerts(snapshot)
        stale_alerts = [a for a in alerts if a.category == AlertCategory.DATA]
        assert "3" in stale_alerts[0].message


class TestAlertManagerBacklog:
    def test_moderate_backlog_triggers_warning(self):
        snapshot = _snapshot(infra=collect_infra_metrics(queue_backlog=60))
        alerts = build_monitoring_alerts(snapshot)
        backlog_alerts = [a for a in alerts if a.category == AlertCategory.INFRA and "backlog" in a.alert_id]
        assert len(backlog_alerts) == 1
        assert backlog_alerts[0].severity == AlertSeverity.WARNING

    def test_high_backlog_triggers_critical(self):
        snapshot = _snapshot(infra=collect_infra_metrics(queue_backlog=150))
        alerts = build_monitoring_alerts(snapshot)
        backlog_alerts = [a for a in alerts if "backlog" in a.alert_id]
        assert len(backlog_alerts) == 1
        assert backlog_alerts[0].severity == AlertSeverity.CRITICAL

    def test_low_backlog_no_alert(self):
        snapshot = _snapshot(infra=collect_infra_metrics(queue_backlog=10))
        assert snapshot.backlog_warning is False


class TestAlertManagerLoss:
    def test_dtr_loss_triggers_critical(self):
        snapshot = _snapshot(infra=collect_infra_metrics(dtr_loss_count=3))
        alerts = build_monitoring_alerts(snapshot)
        loss_alerts = [a for a in alerts if "loss" in a.alert_id]
        assert len(loss_alerts) == 1
        assert loss_alerts[0].severity == AlertSeverity.CRITICAL
        assert "dtr=3" in loss_alerts[0].message

    def test_log_loss_triggers_critical(self):
        snapshot = _snapshot(infra=collect_infra_metrics(log_loss_count=5))
        alerts = build_monitoring_alerts(snapshot)
        loss_alerts = [a for a in alerts if "loss" in a.alert_id]
        assert len(loss_alerts) == 1
        assert "log=5" in loss_alerts[0].message

    def test_combined_loss_single_alert(self):
        snapshot = _snapshot(infra=collect_infra_metrics(dtr_loss_count=1, log_loss_count=2))
        alerts = build_monitoring_alerts(snapshot)
        loss_alerts = [a for a in alerts if "loss" in a.alert_id]
        assert len(loss_alerts) == 1


class TestAlertManagerRiskAndMetaCoverage:
    def test_capacity_thresholds_produce_near_full_alerts(self):
        snapshot = _snapshot(
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=82.0,
                loss_capacity_used_pct=84.0,
                beta_utilization=0.3,
                capital_deployed_usdt=500.0,
                ce_net=0.001,
            ),
        )
        alerts = build_monitoring_alerts(snapshot)
        alert_ids = {alert.alert_id.split(":")[-1] for alert in alerts}

        assert "gross_cap_near_full" in alert_ids
        assert "loss_budget_near_full" in alert_ids

    def test_capacity_thresholds_produce_full_alerts(self):
        snapshot = _snapshot(
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=100.0,
                loss_capacity_used_pct=100.0,
                beta_utilization=0.3,
                capital_deployed_usdt=500.0,
                ce_net=0.001,
            ),
        )
        alerts = build_monitoring_alerts(snapshot)
        full_alerts = {alert.alert_id.split(":")[-1]: alert for alert in alerts}

        assert full_alerts["gross_cap_full"].severity == AlertSeverity.CRITICAL
        assert full_alerts["loss_budget_full"].severity == AlertSeverity.CRITICAL

    def test_beta_cluster_and_sterilization_alerts_are_actionable(self):
        snapshot = _snapshot(
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=1,
                gross_capacity_used_pct=30.0,
                loss_capacity_used_pct=10.0,
                beta_utilization=1.15,
                capital_deployed_usdt=500.0,
                ce_net=0.001,
                dominant_cluster="trend",
                breaches=("cluster_limit", "beta_limit"),
            ),
            meta=collect_meta_metrics(
                build_dtr_summary(
                    (build_dtr(
                        dtr_id="d1", pair="BTCUSDT", engine_id="engine_a",
                        decision_state=DecisionState.SELECTED, timestamp=1000.0),),
                    total_opportunities=1,
                ),
                build_cra_report(
                    (SterilizationResult(
                        pair="BTCUSDT", engine_id="engine_a",
                        classification=SterilizationClass.PHANTOM_PROBABLE,
                        multiplier=0.5, phantom_risk_score=0.8),),
                    alerts=(
                        CRAAlert(
                            scope="engine_a",
                            sterilization_rate=0.5,
                            total_trades=2,
                            sterilized_count=1,
                            alert_level=CRAAlertLevel.WARNING,
                            dominant_cause="spread_drift",
                        ),
                    ),
                ),
                build_break_even_report(
                    (BreakEvenView(
                        scope="engine_a", sample_size=20, mean_realized_cost=0.001,
                        mean_expected_cost=0.001, mean_cost_drift=0.0, profitable_rate=0.6),)
                ),
                build_edge_report(
                    (EdgeClassification(
                        scope="engine_a", status=EdgeStatus.CREDIBLE,
                        mean_net_return=0.003, standard_error=0.0003,
                        sample_size=30, sharpe_per_trade=0.5,
                        mean_cost_p90=0.001, ce_observed=0.0005,
                        cluster_utilization=0.15),)
                ),
            ),
        )
        alerts = build_monitoring_alerts(snapshot)
        alert_ids = {alert.alert_id.split(":")[-1] for alert in alerts}

        assert "beta_btc_breach" in alert_ids
        assert "cluster_breach" in alert_ids
        assert "sterilization_spike" in alert_ids


class TestAlertManagerEdgeDegradation:
    def test_edge_degraded_produces_alert(self):
        meta = collect_meta_metrics(
            build_dtr_summary(
                (build_dtr(dtr_id="d1", pair="BTCUSDT", engine_id="engine_a",
                           decision_state=DecisionState.SELECTED, timestamp=1000.0),),
                total_opportunities=1),
            build_cra_report(
                (SterilizationResult(pair="BTCUSDT", engine_id="engine_a",
                                     classification=SterilizationClass.HEALTHY,
                                     multiplier=1.0, phantom_risk_score=0.05),), alerts=()),
            build_break_even_report(
                (BreakEvenView(scope="engine_a", sample_size=20, mean_realized_cost=0.001,
                               mean_expected_cost=0.001, mean_cost_drift=0.0, profitable_rate=0.6),)),
            build_edge_report(
                (EdgeClassification(scope="engine_a", status=EdgeStatus.DEGRADED,
                                    mean_net_return=-0.001, standard_error=0.0005,
                                    sample_size=15, sharpe_per_trade=-0.1,
                                    mean_cost_p90=0.002, ce_observed=0.0,
                                    cluster_utilization=0.4),)),
        )
        snapshot = _snapshot(meta=meta)
        alerts = build_monitoring_alerts(snapshot)
        edge_alerts = [a for a in alerts if "edge" in a.alert_id]
        assert len(edge_alerts) == 1
        assert edge_alerts[0].severity == AlertSeverity.WARNING


class TestAlertManagerCombined:
    def test_all_conditions_produce_all_alerts(self):
        meta = collect_meta_metrics(
            build_dtr_summary(
                (build_dtr(dtr_id="d1", pair="BTCUSDT", engine_id="engine_a",
                           decision_state=DecisionState.SELECTED, timestamp=1000.0),),
                total_opportunities=1),
            build_cra_report(
                (SterilizationResult(pair="BTCUSDT", engine_id="engine_a",
                                     classification=SterilizationClass.HEALTHY,
                                     multiplier=1.0, phantom_risk_score=0.05),), alerts=()),
            build_break_even_report(
                (BreakEvenView(scope="engine_b", sample_size=10, mean_realized_cost=0.002,
                               mean_expected_cost=0.001, mean_cost_drift=0.001, profitable_rate=0.3),)),
            build_edge_report(
                (EdgeClassification(scope="engine_a", status=EdgeStatus.DEGRADED,
                                    mean_net_return=-0.001, standard_error=0.0005,
                                    sample_size=15, sharpe_per_trade=-0.1,
                                    mean_cost_p90=0.002, ce_observed=0.0,
                                    cluster_utilization=0.4),)),
        )
        snapshot = _snapshot(
            infra=collect_infra_metrics(
                stale_pairs=("BTCUSDT",), queue_backlog=200,
                dtr_loss_count=1, log_loss_count=1,
            ),
            meta=meta,
        )
        alerts = build_monitoring_alerts(snapshot)
        alert_ids = {a.alert_id.split(":")[-1] for a in alerts}
        assert {
            "stale",
            "backlog",
            "loss",
            "cost_drift",
            "edge_degraded",
            "observability_gap",
        } == alert_ids

    def test_alert_ids_contain_correlation_id(self):
        snapshot = _snapshot(
            infra=collect_infra_metrics(stale_pairs=("BTCUSDT",)),
        )
        alerts = build_monitoring_alerts(snapshot)
        assert all("corr-test" in a.alert_id for a in alerts)


class TestAlertLifecycleTracker:
    def test_tracker_marks_alert_resolved_when_missing_from_next_snapshot(self):
        tracker = AlertLifecycleTracker()
        open_history = tracker.update(
            (
                AlertRecord(
                    timestamp_ms=1_700_000_000_000,
                    alert_id="corr-open:backlog",
                    severity=AlertSeverity.WARNING,
                    category=AlertCategory.INFRA,
                    message="Queue backlog elevated at 80",
                    module="monitoring",
                ),
            ),
            timestamp_ms=1_700_000_000_000,
        )

        resolved_history = tracker.update((), timestamp_ms=1_700_000_000_500)

        assert open_history[0].status == "open"
        assert open_history[0].alert_id == "corr-open:backlog"
        assert resolved_history[0].status == "resolved"
        assert resolved_history[0].resolved_ms == 1_700_000_000_500
