"""Tests for the minimal Build-10 observability export."""

from __future__ import annotations

import monitoring

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import SterilizationClass, SterilizationResult
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeClassification, EdgeStatus
from monitoring import (
    build_observability_export,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)


def _snapshot():
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="d1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1000.0,
            ),
        ),
        total_opportunities=2,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.5,
                phantom_risk_score=0.8,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_a",
                sterilization_rate=1.0,
                total_trades=1,
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
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.001,
                standard_error=0.0004,
                sample_size=20,
                sharpe_per_trade=-0.1,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.4,
            ),
        )
    )
    return collect_monitoring_snapshot(
        correlation_id="corr-obs",
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
        infra=collect_infra_metrics(queue_backlog=75, stale_pairs=("BTCUSDT",), dtr_loss_count=1),
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
            collect_pair_metrics(pair="BTCUSDT", health=PairHealthLevel.STALE, freshness_ms=9000),
        ),
    )


def test_monitoring_exports_observability_symbols():
    assert {
        "MetricSample",
        "ObservabilityExport",
        "build_observability_export",
    }.issubset(set(monitoring.__all__))


def test_observability_export_contains_structured_core_metrics():
    export = build_observability_export(_snapshot())
    names = {sample.name for sample in export.samples}

    assert "v53_headline_status" in names
    assert "v53_active_alert_count" in names
    assert "v53_dtr_coverage_ratio" in names
    assert export.correlation_id == "corr-obs"
    assert 'profile="light"' in export.text_payload
    assert 'runtime_mode="shadow"' in export.text_payload


def test_observability_export_tracks_modules_engines_and_governed_flags():
    export = build_observability_export(
        _snapshot(),
        active_modules=("monitoring", "ui", "meta_learning"),
        active_engines=("engine_a", "engine_b"),
        recent_diagnostics=4,
        open_hypotheses=2,
        replay_candidates=1,
        artifact_present=True,
        import_accepted=False,
    )

    module_samples = [sample for sample in export.samples if sample.name == "v53_module_active"]
    engine_samples = [sample for sample in export.samples if sample.name == "v53_engine_stale"]
    assert {sample.labels["module"] for sample in module_samples} == {"monitoring", "ui", "meta_learning"}
    assert {sample.labels["engine"] for sample in engine_samples} == {"engine_a", "engine_b"}
    stale_b = next(sample for sample in engine_samples if sample.labels["engine"] == "engine_b")
    assert stale_b.value == 1.0
    assert any(sample.name == "v53_build9x_recent_diagnostics" and sample.value == 4.0 for sample in export.samples)
    assert any(sample.name == "v53_artifact_import_accepted" and sample.value == 0.0 for sample in export.samples)


def test_observability_export_marks_import_as_not_started_when_absent():
    export = build_observability_export(_snapshot(), artifact_present=False, import_accepted=None)

    started = next(sample for sample in export.samples if sample.name == "v53_artifact_import_review_started")
    accepted = next(sample for sample in export.samples if sample.name == "v53_artifact_import_accepted")
    assert started.value == 0.0
    assert accepted.value == 0.0


def test_observability_export_handles_empty_module_and_engine_lists():
    export = build_observability_export(_snapshot())

    assert all(sample.name != "v53_module_active" for sample in export.samples)
    assert all(sample.name != "v53_engine_stale" for sample in export.samples)
    assert export.text_payload.startswith("# V5.3 monitoring export")


def test_observability_export_preserves_correlation_id_in_all_samples():
    export = build_observability_export(
        _snapshot(),
        active_modules=("monitoring",),
        active_engines=("engine_a",),
    )

    assert all(sample.labels.get("correlation_id") == "corr-obs" for sample in export.samples)
