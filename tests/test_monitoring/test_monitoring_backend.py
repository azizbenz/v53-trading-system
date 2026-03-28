"""Tests for the real Build-10 monitoring backend."""

from __future__ import annotations

import monitoring
import pytest
from pydantic import ValidationError

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity, PairHealthLevel, ProfileId, RuntimeMode
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)
from monitoring import (
    build_health_dashboard_payload,
    build_monitoring_alerts,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)


def _sample_build9_reports():
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1000.0,
            ),
            build_dtr(
                dtr_id="dtr-2",
                pair="ETHUSDT",
                engine_id="engine_b",
                decision_state=DecisionState.HARD_BLOCKED,
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
                multiplier=0.4,
                phantom_risk_score=0.8,
                reason="spread_drift",
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
                sample_size=10,
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
                standard_error=0.0004,
                sample_size=20,
                sharpe_per_trade=0.30,
                mean_cost_p90=0.001,
                ce_observed=0.0004,
                cluster_utilization=0.20,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0005,
                sample_size=20,
                sharpe_per_trade=-0.10,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.45,
            ),
        )
    )
    return dtr_summary, cra_report, break_even_report, edge_report


def test_monitoring_exports_expected_symbols():
    assert {
        "MonitoringSnapshot",
        "collect_monitoring_snapshot",
        "build_monitoring_alerts",
        "build_health_dashboard_payload",
    }.issubset(set(monitoring.__all__))


def test_collect_meta_metrics_projects_real_build9_outputs():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()

    meta_metrics = collect_meta_metrics(
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
        future_learning_diagnostics=2,
        future_learning_hypotheses=1,
    )

    assert meta_metrics.dtr_coverage == dtr_summary.dtr_coverage
    assert meta_metrics.cra_alert_count == 1
    assert meta_metrics.break_even_drift_alert is True
    assert meta_metrics.edge_degraded_count == 1
    assert meta_metrics.future_learning_hypotheses == 1


def test_monitoring_alerts_and_dashboard_payload_are_actionable():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-build10",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=40.0,
            loss_capacity_used_pct=10.0,
            beta_utilization=0.4,
            capital_deployed_usdt=1500.0,
            ce_net=0.0015,
        ),
        infra=collect_infra_metrics(
            queue_backlog=120,
            reconnect_count=2,
            stale_pairs=("BTCUSDT",),
            dtr_loss_count=1,
            log_loss_count=0,
            cpu_pct=35.0,
            ram_pct=42.0,
        ),
        meta=collect_meta_metrics(
            dtr_summary,
            cra_report,
            break_even_report,
            edge_report,
            future_learning_diagnostics=2,
            future_learning_hypotheses=1,
        ),
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=1,
                net_edge_bps=12.0,
                expected_cost_bps=5.0,
                ce_expected=0.0005,
            ),
        ),
        pairs=(
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=9_000,
                backlog_depth=120,
            ),
        ),
    )

    alerts = build_monitoring_alerts(snapshot)
    payload = build_health_dashboard_payload(snapshot.model_copy(update={"alerts": alerts}))

    assert len(alerts) >= 4
    assert payload.headline_status == "critical"
    assert payload.active_alert_count == len(alerts)
    assert payload.future_learning_diagnostics == 2
    assert payload.future_learning_hypotheses == 1


def test_health_dashboard_payload_preserves_identifiers_and_modes():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-preserved",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_123_456,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=500.0,
            ce_net=0.0010,
        ),
        infra=collect_infra_metrics(),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_health_dashboard_payload(snapshot)

    assert payload.correlation_id == "corr-preserved"
    assert payload.timestamp_ms == 1_700_000_123_456
    assert payload.profile == ProfileId.LIGHT
    assert payload.runtime_mode == RuntimeMode.SHADOW


def test_critical_alert_overrides_warning_only_flags():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-critical",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=15.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.2,
            capital_deployed_usdt=700.0,
            ce_net=0.0008,
        ),
        infra=collect_infra_metrics(queue_backlog=60),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )
    critical_alert = AlertRecord(
        alert_id="corr-critical:manual_critical",
        category=AlertCategory.INFRA,
        severity=AlertSeverity.CRITICAL,
        message="manual critical escalation",
        timestamp_ms=snapshot.timestamp_ms,
    )
    payload = build_health_dashboard_payload(
        snapshot.model_copy(
            update={
                "alerts": (critical_alert,),
                "loss_warning": False,
                "backlog_warning": False,
                "stale_warning": False,
            }
        )
    )

    assert payload.headline_status == "critical"


def test_warning_payload_without_critical_loss_stays_warning():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-warning",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=15.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.2,
            capital_deployed_usdt=700.0,
            ce_net=0.0008,
        ),
        infra=collect_infra_metrics(),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_health_dashboard_payload(
        snapshot.model_copy(update={"alerts": (), "loss_warning": False})
    )

    assert payload.headline_status == "warning"


def test_invalid_headline_status_rejected_by_contract():
    with pytest.raises(ValidationError):
        monitoring.HealthDashboardPayload(
            timestamp_ms=1_700_000_000_000,
            correlation_id="corr-invalid",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            headline_status="degraded",
            active_alert_count=0,
            stale_pair_count=0,
            queue_backlog=0,
            capital_deployed_usdt=0.0,
            gross_capacity_used_pct=0.0,
            loss_capacity_used_pct=0.0,
            ce_net=0.0,
            dtr_coverage=1.0,
            cra_sterilization_rate=0.0,
            break_even_drift_scopes=(),
            edge_credible_count=0,
            edge_degraded_count=0,
            edge_surveillance_count=0,
            future_learning_diagnostics=0,
            future_learning_hypotheses=0,
        )
