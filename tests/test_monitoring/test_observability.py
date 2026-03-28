"""Tests for the grouped Build-10 observability export."""

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
    Build9XProjection,
    LiveLightProjection,
    MicroLiveProjection,
    ReplayImportProjection,
    ShadowProjection,
    build_observability_export,
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)


def _payload(
    *,
    build9x_projection: Build9XProjection | None = None,
    shadow_projection: ShadowProjection | None = None,
    micro_live_projection: MicroLiveProjection | None = None,
    live_light_projection: LiveLightProjection | None = None,
    replay_projection: ReplayImportProjection | None = None,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
):
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
    snapshot = collect_monitoring_snapshot(
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
    return build_technical_dashboard_payload(
        snapshot,
        active_modules=active_modules,
        active_engines=active_engines,
        build9x_projection=build9x_projection,
        shadow_projection=shadow_projection,
        micro_live_projection=micro_live_projection,
        live_light_projection=live_light_projection,
        replay_projection=replay_projection,
    )


def test_monitoring_exports_observability_symbols():
    assert {
        "MetricSample",
        "ObservabilityExport",
        "build_observability_export",
    }.issubset(set(monitoring.__all__))


def test_observability_export_contains_grouped_metrics():
    payload = _payload()
    export = build_observability_export(payload)
    names = {sample.name for sample in export.samples}

    assert "v53_system_headline_status" in names
    assert "v53_meta_dtr_coverage_ratio" in names
    assert "v53_shadow_run_state" in names
    assert "v53_micro_live_run_state" in names
    assert "v53_live_light_run_state" in names
    assert "v53_alert_active_count" in names
    assert export.correlation_id == "corr-obs"
    assert 'profile="light"' in export.text_payload
    assert 'runtime_mode="shadow"' in export.text_payload


def test_observability_export_tracks_modules_engines_and_governed_flags():
    payload = _payload(
        active_modules=("monitoring", "ui", "meta_learning"),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=Build9XProjection(
            status="warning",
            diagnostics_count=4,
            diagnostics_summary="Governed review bundle available",
            open_hypotheses=2,
            total_hypotheses=3,
            near_miss_count=1,
            replay_candidate_count=1,
            memory_record_count=2,
            latest_memory_summary="Most recent governed memory stored",
            review_export_ready=True,
            review_export_ref="exports/review.md",
        ),
        shadow_projection=ShadowProjection(
            status="warning",
            run_state="completed",
            verdict="needs_review",
            truth_set_ref="shadow_truth:t1",
            validation_set_ref="shadow_validation:v1",
            divergent_comparison_count=2,
            blocking_comparison_count=0,
            total_comparison_count=7,
            build9x_diagnostics_count=4,
            open_hypotheses=2,
            replay_candidate_count=1,
            review_export_ready=False,
            import_artifact_id="artifact-1",
            import_lineage_version="a.v2.1",
            blocking_reasons=("review export missing",),
            manual_review_required=True,
        ),
        micro_live_projection=MicroLiveProjection(
            status="warning",
            run_state="prepared",
            verdict="dry_run_only",
            shadow_run_id="shadow-run-1",
            shadow_verdict="needs_review",
            allowed_to_probe=False,
            requested_total_notional_usdt=20.0,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            order_probe_limit=2,
            planned_pairs=("BTCUSDT",),
            planned_engines=("engine_a",),
            import_artifact_id="artifact-1",
            import_lineage_version="a.v2.1",
            observability_ready=True,
            halt_ready=True,
            onboarding_ready=True,
            blocking_reasons=("Build-11 Shadow verdict must be accepted before Micro-live can probe capital",),
        ),
        live_light_projection=LiveLightProjection(
            status="warning",
            run_state="prepared",
            verdict="dry_run_only",
            micro_live_run_id="micro-run-1",
            micro_live_verdict="dry_run_only",
            allowed_to_execute_small=False,
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=3,
            planned_pairs=("BTCUSDT",),
            planned_engines=("engine_a",),
            import_artifact_id="artifact-1",
            import_lineage_version="a.v2.1",
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=False,
            exchange_ready=True,
            blocking_reasons=("broker readiness must be confirmed before Live-Light execution",),
        ),
        replay_projection=ReplayImportProjection(
            status="warning",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v2.1",
            lifecycle_state="exported",
            validation_status="needs_revision",
            review_state="needs_revision",
            rejection_reasons=("lineage mismatch",),
        ),
    )
    export = build_observability_export(payload)

    module_samples = [sample for sample in export.samples if sample.name == "v53_system_module_active"]
    engine_samples = [sample for sample in export.samples if sample.name == "v53_system_engine_stale"]
    assert {sample.labels["module"] for sample in module_samples} == {"monitoring", "ui", "meta_learning"}
    assert {sample.labels["engine"] for sample in engine_samples} == {"engine_a", "engine_b"}
    stale_b = next(sample for sample in engine_samples if sample.labels["engine"] == "engine_b")
    assert stale_b.value == 1.0
    assert any(sample.name == "v53_build9x_recent_diagnostics" and sample.value == 4.0 for sample in export.samples)
    assert any(sample.name == "v53_shadow_divergent_comparison_count" and sample.value == 2.0 for sample in export.samples)
    assert any(sample.name == "v53_micro_live_allowed_to_probe" and sample.value == 0.0 for sample in export.samples)
    assert any(sample.name == "v53_micro_live_blocking_reason_count" and sample.value == 1.0 for sample in export.samples)
    assert any(sample.name == "v53_live_light_allowed_to_execute_small" and sample.value == 0.0 for sample in export.samples)
    assert any(sample.name == "v53_live_light_blocking_reason_count" and sample.value == 1.0 for sample in export.samples)
    assert any(sample.name == "v53_live_light_broker_ready" and sample.value == 0.0 for sample in export.samples)
    assert any(sample.name == "v53_replay_validation_accepted" and sample.value == 0.0 for sample in export.samples)


def test_observability_export_marks_import_as_not_started_when_absent():
    export = build_observability_export(_payload())

    started = next(sample for sample in export.samples if sample.name == "v53_replay_validation_started")
    accepted = next(sample for sample in export.samples if sample.name == "v53_replay_validation_accepted")
    assert started.value == 0.0
    assert accepted.value == 0.0


def test_observability_export_handles_empty_module_and_engine_lists():
    export = build_observability_export(_payload())

    assert all(sample.name != "v53_system_module_active" for sample in export.samples)
    assert all(sample.name != "v53_system_engine_stale" for sample in export.samples)
    assert export.text_payload.startswith("# V5.3 technical observability export")


def test_observability_export_preserves_correlation_id_in_all_samples():
    export = build_observability_export(
        _payload(
            active_modules=("monitoring",),
            active_engines=("engine_a",),
        )
    )

    assert all(sample.labels.get("correlation_id") == "corr-obs" for sample in export.samples)
