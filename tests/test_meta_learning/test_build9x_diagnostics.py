"""Diagnostics and classification tests for the real Build-9X layer."""

from __future__ import annotations

from interface_contracts import EngineId, ProfileId, RuntimeMode, StrategyClassification
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_learning import (
    TradeLearningInput,
    analyze_near_misses,
    build_post_trade_diagnostics,
    classify_mistakes,
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


def _trade_input() -> TradeLearningInput:
    return TradeLearningInput(
        correlation_id="corr-9x",
        dtr_ids=("dtr-1", "dtr-2"),
        pair="BTCUSDT",
        engine_id=EngineId.B,
        profile=ProfileId.LIGHT,
        source_runtime_mode=RuntimeMode.SHADOW,
        strategy_classification=StrategyClassification.B_VARIANT,
        source_version="5.3.0-build10",
    )


def _reports():
    records = (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            raw_score=0.92,
            final_score=0.82,
            timestamp=1000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.SELECTED,
            raw_score=0.70,
            final_score=0.68,
            timestamp=1001.0,
        ),
    )
    dtr_summary = build_dtr_summary(records, total_opportunities=4)
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_b",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.40,
                phantom_risk_score=0.80,
                reason="spread_drift",
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_b",
                sterilization_rate=1.0,
                total_trades=1,
                sterilized_count=1,
                alert_level=CRAAlertLevel.CRITICAL,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=10,
                mean_realized_cost=0.0016,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0006,
                profitable_rate=0.4,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0005,
                sample_size=12,
                sharpe_per_trade=-0.15,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.50,
            ),
        )
    )
    return records, dtr_summary, cra_report, break_even_report, edge_report


def test_post_trade_diagnostics_detect_build9_issues():
    _, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    diagnostics = build_post_trade_diagnostics(
        _trade_input(),
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
    )

    categories = {diagnostic.category for diagnostic in diagnostics}
    assert {"trace_coverage", "sterilization", "cost_drift", "edge_degraded"} <= categories


def test_near_miss_analyzer_flags_high_score_blocked_records():
    records, *_ = _reports()
    near_misses = analyze_near_misses("corr-9x", records)

    assert len(near_misses) == 1
    assert near_misses[0].category == "near_miss"
    assert "BTCUSDT" in near_misses[0].summary


def test_mistake_classifier_deduplicates_classes():
    records, dtr_summary, cra_report, break_even_report, edge_report = _reports()
    diagnostics = build_post_trade_diagnostics(
        _trade_input(),
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
    ) + analyze_near_misses("corr-9x", records)

    mistake_classes = classify_mistakes(diagnostics)

    assert "economic_sterilization" in mistake_classes
    assert "near_miss" in mistake_classes
    assert len(mistake_classes) == len(set(mistake_classes))
