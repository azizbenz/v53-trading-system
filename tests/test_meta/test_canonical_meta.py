"""Canonical facade tests for Build-9 meta."""

from __future__ import annotations

import meta
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_minimal.break_even_dashboard.break_even_reporter import (
    build_break_even_report as impl_build_break_even_report,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.cra_reporter import build_cra_report as impl_build_cra_report
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.dtr_core.dtr_reporter import build_dtr_summary as impl_build_dtr_summary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import (
    build_edge_report as impl_build_edge_report,
)
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)


def test_meta_facade_exports_expected_symbols():
    assert meta.__all__ == [
        "break_even_dashboard",
        "cra_monitor",
        "dtr_core",
        "edge_tracker_prudent_minimal",
        "build_break_even_report",
        "build_cra_report",
        "build_dtr_summary",
        "build_edge_report",
    ]


def test_meta_facade_reexports_impl_builders():
    assert build_dtr_summary is impl_build_dtr_summary
    assert build_cra_report is impl_build_cra_report
    assert build_break_even_report is impl_build_break_even_report
    assert build_edge_report is impl_build_edge_report


def test_meta_facade_builders_run_minimally():
    dtr_records = (
        build_dtr(
            dtr_id="dtr_001",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            timestamp=1000.0,
        ),
        build_dtr(
            dtr_id="dtr_002",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            timestamp=1001.0,
        ),
    )
    dtr_summary = build_dtr_summary(dtr_records, total_opportunities=2)
    assert dtr_summary.total_records == 2
    assert dtr_summary.dtr_coverage == 1.0

    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.0,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_a",
                sterilization_rate=0.0,
                total_trades=1,
                sterilized_count=0,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="smoke_only",
            ),
        ),
    )
    assert cra_report.total_trades == 1
    assert len(cra_report.alerts) == 1

    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_a",
                sample_size=1,
                mean_realized_cost=0.0013,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0003,
                profitable_rate=1.0,
            ),
        )
    )
    assert len(break_even_report.views) == 1
    assert break_even_report.has_cost_drift_alert is True

    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.002,
                standard_error=0.0005,
                sample_size=20,
                sharpe_per_trade=0.25,
                mean_cost_p90=0.001,
                ce_observed=0.0005,
                cluster_utilization=0.2,
            ),
        )
    )
    assert edge_report.total_scopes == 1
    assert edge_report.credible_count == 1
