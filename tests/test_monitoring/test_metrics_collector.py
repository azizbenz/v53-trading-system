"""Tests for metrics_collector functions and snapshot construction."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from monitoring import (
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from monitoring.contracts import EngineMetrics, InfraMetrics, PairMetrics, PortfolioMetrics

from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.sterilization_classifier import SterilizationClass, SterilizationResult
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification, EdgeStatus


class TestPortfolioMetrics:
    def test_valid_portfolio_metrics(self):
        m = collect_portfolio_metrics(
            allocated_opportunities=3, gross_capacity_used_pct=50.0,
            loss_capacity_used_pct=10.0, beta_utilization=0.5,
            capital_deployed_usdt=2000.0, ce_net=0.002,
        )
        assert isinstance(m, PortfolioMetrics)
        assert m.allocated_opportunities == 3
        assert m.ce_net == 0.002

    def test_zero_values_accepted(self):
        m = collect_portfolio_metrics(
            allocated_opportunities=0, gross_capacity_used_pct=0.0,
            loss_capacity_used_pct=0.0, beta_utilization=0.0,
            capital_deployed_usdt=0.0, ce_net=0.0,
        )
        assert m.allocated_opportunities == 0

    def test_negative_opportunities_rejected(self):
        with pytest.raises(ValidationError):
            collect_portfolio_metrics(
                allocated_opportunities=-1, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0,
            )

    def test_capacity_over_100_rejected(self):
        with pytest.raises(ValidationError):
            collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=101.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0,
            )


class TestEngineMetrics:
    def test_valid_engine_metrics(self):
        m = collect_engine_metrics(
            engine_id="engine_a", emitted_signals=5,
            net_edge_bps=12.0, expected_cost_bps=3.0, ce_expected=0.001,
        )
        assert isinstance(m, EngineMetrics)
        assert m.stale is False

    def test_stale_engine(self):
        m = collect_engine_metrics(
            engine_id="engine_b", emitted_signals=0,
            net_edge_bps=0.0, expected_cost_bps=0.0, ce_expected=0.0, stale=True,
        )
        assert m.stale is True

    def test_empty_engine_id_rejected(self):
        with pytest.raises(ValidationError):
            collect_engine_metrics(
                engine_id="", emitted_signals=0,
                net_edge_bps=0.0, expected_cost_bps=0.0, ce_expected=0.0,
            )


class TestPairMetrics:
    def test_valid_pair_metrics(self):
        m = collect_pair_metrics(pair="BTCUSDT", health=PairHealthLevel.HEALTHY, freshness_ms=1000)
        assert isinstance(m, PairMetrics)
        assert m.is_active is True

    def test_inactive_pair(self):
        m = collect_pair_metrics(
            pair="BTCUSDT", health=PairHealthLevel.SUSPENDED,
            freshness_ms=15000, is_active=False,
        )
        assert m.is_active is False


class TestInfraMetrics:
    def test_defaults(self):
        m = collect_infra_metrics()
        assert isinstance(m, InfraMetrics)
        assert m.queue_backlog == 0
        assert m.stale_pairs == ()

    def test_full_infra(self):
        m = collect_infra_metrics(
            queue_backlog=500, reconnect_count=3,
            stale_pairs=("BTCUSDT", "ETHUSDT"),
            dtr_loss_count=2, log_loss_count=1,
            cpu_pct=80.0, ram_pct=60.0,
        )
        assert m.queue_backlog == 500
        assert len(m.stale_pairs) == 2


class TestSnapshotConstruction:
    def _meta(self):
        dtr_summary = build_dtr_summary(
            (build_dtr(dtr_id="d1", pair="BTCUSDT", engine_id="engine_a",
                       decision_state=DecisionState.SELECTED, timestamp=1000.0),),
            total_opportunities=1,
        )
        cra_report = build_cra_report(
            (SterilizationResult(pair="BTCUSDT", engine_id="engine_a",
                                 classification=SterilizationClass.HEALTHY,
                                 multiplier=1.0, phantom_risk_score=0.05),), alerts=())
        be_report = build_break_even_report(
            (BreakEvenView(scope="engine_a", sample_size=20, mean_realized_cost=0.001,
                           mean_expected_cost=0.001, mean_cost_drift=0.0, profitable_rate=0.6),))
        edge_report = build_edge_report(
            (EdgeClassification(scope="engine_a", status=EdgeStatus.CREDIBLE,
                                mean_net_return=0.003, standard_error=0.0003,
                                sample_size=30, sharpe_per_trade=0.5,
                                mean_cost_p90=0.001, ce_observed=0.0005,
                                cluster_utilization=0.15),))
        return collect_meta_metrics(dtr_summary, cra_report, be_report, edge_report)

    def test_backlog_warning_threshold_50(self):
        s = collect_monitoring_snapshot(
            correlation_id="c1", profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW, timestamp_ms=1_700_000_000_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0),
            infra=collect_infra_metrics(queue_backlog=51),
            meta=self._meta(),
        )
        assert s.backlog_warning is True

    def test_no_backlog_warning_at_50(self):
        s = collect_monitoring_snapshot(
            correlation_id="c1", profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW, timestamp_ms=1_700_000_000_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0),
            infra=collect_infra_metrics(queue_backlog=50),
            meta=self._meta(),
        )
        assert s.backlog_warning is False

    def test_stale_warning_from_pair_health(self):
        s = collect_monitoring_snapshot(
            correlation_id="c1", profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW, timestamp_ms=1_700_000_000_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0),
            infra=collect_infra_metrics(),
            meta=self._meta(),
            pairs=(collect_pair_metrics(pair="BTCUSDT", health=PairHealthLevel.OFFLINE, freshness_ms=20000),),
        )
        assert s.stale_warning is True

    def test_loss_warning_from_dtr(self):
        s = collect_monitoring_snapshot(
            correlation_id="c1", profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW, timestamp_ms=1_700_000_000_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0),
            infra=collect_infra_metrics(dtr_loss_count=1),
            meta=self._meta(),
        )
        assert s.loss_warning is True

    def test_snapshot_computed_properties(self):
        from interface_contracts import AlertCategory, AlertRecord, AlertSeverity
        s = collect_monitoring_snapshot(
            correlation_id="c1", profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW, timestamp_ms=1_700_000_000_000,
            portfolio=collect_portfolio_metrics(
                allocated_opportunities=0, gross_capacity_used_pct=0.0,
                loss_capacity_used_pct=0.0, beta_utilization=0.0,
                capital_deployed_usdt=0.0, ce_net=0.0),
            infra=collect_infra_metrics(stale_pairs=("BTCUSDT", "ETHUSDT")),
            meta=self._meta(),
        )
        assert s.stale_pair_count == 2
        assert s.active_alert_count == 0
