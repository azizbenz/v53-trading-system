"""Tests for the normalized Build-10 technical supervision view."""

from __future__ import annotations

from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
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
    Build9XProjection,
    ReplayImportProjection,
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
)
from ui import build_technical_dashboard_view


def _snapshot(**overrides):
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-1",
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
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.002,
                standard_error=0.0003,
                sample_size=20,
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
                sample_size=20,
                sharpe_per_trade=-0.1,
                mean_cost_p90=0.002,
                ce_observed=0.0,
                cluster_utilization=0.4,
            ),
        )
    )
    defaults = dict(
        correlation_id="corr-tech",
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
        infra=collect_infra_metrics(queue_backlog=75, stale_pairs=("BTCUSDT",)),
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
            collect_pair_metrics(
                pair="BTCUSDT",
                health=PairHealthLevel.STALE,
                freshness_ms=9000,
                backlog_depth=75,
            ),
        ),
    )
    defaults.update(overrides)
    return collect_monitoring_snapshot(**defaults)


def _build9x_projection() -> Build9XProjection:
    return Build9XProjection(
        status="warning",
        diagnostics_count=2,
        diagnostics_summary="Two governed issues detected",
        open_hypotheses=1,
        total_hypotheses=1,
        near_miss_count=1,
        replay_candidate_count=1,
        memory_record_count=1,
        latest_memory_summary="Stored governed review state",
        review_export_ready=True,
        review_export_ref="exports/review.md",
    )


def _accepted_replay_projection() -> ReplayImportProjection:
    return ReplayImportProjection(
        status="healthy",
        artifact_id="artifact-1",
        artifact_kind="review_packet",
        lineage_version="a.v2.1",
        lifecycle_state="exported",
        validation_status="accepted",
        review_state="pending",
        rejection_reasons=(),
    )


def test_technical_dashboard_view_exposes_system_meta_build9x_and_replay_sections():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=(
            "interface_contracts",
            "manifest_registry",
            "meta",
            "meta_learning",
            "local_replay_runtime",
            "backtest_artifact_import",
            "monitoring",
            "ui",
        ),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=_build9x_projection(),
        replay_projection=_accepted_replay_projection(),
    )

    view = build_technical_dashboard_view(payload)

    titles = {section.title for section in view.sections}
    assert titles == {
        "System",
        "Portfolio",
        "Build-9 Meta",
        "Build-9X",
        "Replay & Import",
        "Alerts",
    }
    system = next(section for section in view.sections if section.title == "System")
    assert any(card.key == "governed_extensions" and "9X=warning" in card.value for card in system.cards)
    build9x = next(section for section in view.sections if section.title == "Build-9X")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "2"
    assert next(card for card in build9x.cards if card.key == "hypotheses_open").value == "1"
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    assert next(card for card in replay.cards if card.key == "artifact_manifest").value == "artifact-1"
    assert next(card for card in replay.cards if card.key == "validation_status").value == "accepted"


def test_technical_dashboard_view_handles_empty_governed_state_cleanly():
    payload = build_technical_dashboard_payload(
        _snapshot(infra=collect_infra_metrics()),
        active_modules=("interface_contracts", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    build9x = next(section for section in view.sections if section.title == "Build-9X")
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "0"
    assert next(card for card in build9x.cards if card.key == "memory_review").status == "planned"
    assert next(card for card in replay.cards if card.key == "artifact_manifest").value == "none"
    assert next(card for card in replay.cards if card.key == "validation_status").value == "not_run"


def test_technical_dashboard_view_projects_alerts_and_engine_staleness_without_prefilled_alerts():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("interface_contracts", "meta_learning", "local_replay_runtime", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    alerts = next(section for section in view.sections if section.title == "Alerts")
    engines = next(card for card in system.cards if card.key == "engines_ab")
    active_alerts = next(card for card in alerts.cards if card.key == "active_alerts")

    assert engines.status == "warning"
    assert "stale: engine_b" in engines.detail
    assert int(active_alerts.value) >= 3
    assert active_alerts.status in {"warning", "critical"}


def test_technical_dashboard_view_surfaces_rejected_import_and_future_panels():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("meta_learning", "local_replay_runtime", "backtest_artifact_import", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=_build9x_projection(),
        replay_projection=ReplayImportProjection(
            status="warning",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v2.1",
            lifecycle_state="exported",
            validation_status="needs_revision",
            review_state="needs_revision",
            rejection_reasons=("import target must start at SHADOW",),
        ),
    )

    view = build_technical_dashboard_view(payload)
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    validation = next(card for card in replay.cards if card.key == "validation_status")
    reasons = next(card for card in replay.cards if card.key == "validation_reasons")
    assert validation.status == "warning"
    assert validation.value == "needs_revision"
    assert reasons.detail == "import target must start at SHADOW"
    assert set(view.future_panels) == {
        "technical_supervision",
        "build9x_diagnostics",
        "artifact_import",
        "observability_export",
    }


def test_technical_dashboard_view_marks_missing_modules_and_engines_as_planned():
    payload = build_technical_dashboard_payload(_snapshot(infra=collect_infra_metrics()))
    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    modules = next(card for card in system.cards if card.key == "active_modules")
    engines = next(card for card in system.cards if card.key == "engines_ab")

    assert modules.status == "planned"
    assert modules.detail == "No active modules declared"
    assert engines.status == "planned"
    assert engines.detail == "No active engines declared"
