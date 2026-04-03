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
    Build14ReaderProjection,
    Build14Projection,
    Build9XProjection,
    LiveLightProjection,
    MicroLiveProjection,
    OperatorRuntimeEvent,
    OperatorRuntimeProjection,
    ReplayImportProjection,
    ShadowProjection,
    build_health_dashboard_payload,
    build_monitoring_alerts,
    build_technical_dashboard_payload,
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
        "Build9XProjection",
        "Build14ReaderProjection",
        "Build14Projection",
        "ShadowProjection",
        "LiveLightProjection",
        "ReplayImportProjection",
        "TechnicalDashboardPayload",
        "build_technical_dashboard_payload",
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
    assert set(payload.active_alert_ids) == {alert.alert_id for alert in alerts}
    assert payload.alert_history
    assert {entry.alert_id for entry in payload.alert_history} == {alert.alert_id for alert in alerts}
    assert payload.pairs[0].pair == "BTCUSDT"
    assert payload.engines[0].engine_id == "engine_a"
    assert payload.reconnect_count == 2
    assert payload.dtr_loss_count == 1
    assert payload.cpu_pct == 35.0
    assert payload.future_learning_diagnostics == 2
    assert payload.future_learning_hypotheses == 1
    assert payload.cra_alert_count == 1
    assert payload.deployment_state.value == "shadow"
    assert payload.last_transition_summary == "entered shadow"
    assert payload.shadow_status == "healthy"
    assert payload.micro_live_status == "planned"
    assert payload.live_light_status == "planned"
    assert payload.pnl_net_usdt == 0.0


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
    assert payload.deployment_state.value == "shadow"
    assert payload.last_transition_summary == "entered shadow"


def test_health_and_technical_payloads_project_operator_runtime_state():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-operator-projection",
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
    operator_runtime = OperatorRuntimeProjection(
        event_count=3,
        latest_event_type="critical_alert_acknowledged",
        latest_event_message="critical alert acknowledged",
        recent_event_log=(
            OperatorRuntimeEvent(
                timestamp_ms=1_700_000_123_450,
                correlation_id="corr-operator-projection",
                event_type="operator_action_requested",
                action="set_halted",
                target="",
                accepted=False,
                message="operator action requested: set_halted",
            ),
            OperatorRuntimeEvent(
                timestamp_ms=1_700_000_123_456,
                correlation_id="corr-operator-projection",
                event_type="operator_action_rejected",
                action="modify_risk_caps",
                target="risk",
                accepted=False,
                message="operator action rejected: modify_risk_caps",
                rejection_reason="risk cap changes are forbidden in the locked Light UI",
            ),
        ),
        rejection_event_count=1,
        latest_rejection_reason="risk cap changes are forbidden in the locked Light UI",
        pending_notification_count=1,
        pending_notification_alert_ids=("corr-operator-projection:loss",),
        acknowledged_notification_count=2,
        latest_acknowledged_alert_id="corr-operator-projection:latency",
        latest_safing_action="downgrade_to_shadow",
        latest_safing_source_runtime_mode="micro_live",
        latest_safing_target_runtime_mode="shadow",
        latest_safing_reason="manual requalification requested",
    )

    health_payload = build_health_dashboard_payload(snapshot, operator_runtime=operator_runtime)
    technical_payload = build_technical_dashboard_payload(snapshot, operator_runtime=operator_runtime)

    assert health_payload.operator_runtime.event_count == 3
    assert health_payload.operator_runtime.rejection_event_count == 1
    assert health_payload.operator_runtime.latest_rejection_reason == (
        "risk cap changes are forbidden in the locked Light UI"
    )
    assert health_payload.operator_runtime.pending_notification_count == 1
    assert health_payload.last_transition_summary == "critical alert acknowledged"
    assert technical_payload.alerts.operator_runtime.latest_event_message == "critical alert acknowledged"
    assert technical_payload.alerts.operator_runtime.recent_event_log[-1].event_type == "operator_action_rejected"
    assert technical_payload.alerts.operator_runtime.latest_acknowledged_alert_id == (
        "corr-operator-projection:latency"
    )
    assert technical_payload.micro_live.operator_safing_action == "downgrade_to_shadow"
    assert technical_payload.micro_live.operator_safing_reason == "manual requalification requested"


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


def test_health_payload_accepts_rollout_status_overrides_for_light_surface():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-rollout-health",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.MICRO_LIVE,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=500.0,
            ce_net=0.0010,
            pnl_net_usdt=42.0,
        ),
        infra=collect_infra_metrics(),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_health_dashboard_payload(
        snapshot,
        shadow_status="healthy",
        micro_live_status="warning",
        live_light_status="planned",
    )

    assert payload.deployment_state.value == "degraded"
    assert payload.last_transition_summary == "micro_live -> degraded"
    assert payload.pnl_net_usdt == 42.0


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


def test_technical_dashboard_payload_normalizes_system_meta_and_governed_extensions():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-tech-payload",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=30.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.3,
            capital_deployed_usdt=900.0,
            ce_net=0.0011,
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
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("meta", "meta_learning", "local_replay_runtime", "backtest_artifact_import", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build9x_projection=Build9XProjection(
            status="warning",
            diagnostics_count=2,
            diagnostics_summary="Two governed issues detected",
            open_hypotheses=1,
            total_hypotheses=2,
            near_miss_count=1,
            replay_candidate_count=1,
            memory_record_count=1,
            latest_memory_summary="Stored governed review state",
            review_export_ready=True,
            review_export_ref="exports/review.md",
        ),
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

    assert payload.system.headline_status == "critical"
    assert payload.system.stale_engines == ("engine_b",)
    assert payload.system.build9x_status == "warning"
    assert payload.system.shadow_status == "planned"
    assert payload.system.micro_live_status == "planned"
    assert payload.system.live_light_status == "planned"
    assert payload.system.build14_status == "planned"
    assert payload.system.replay_import_status == "warning"
    assert payload.build9_meta.break_even_state == "drift_alert"
    assert payload.build9x.review_export_ready is True
    assert payload.shadow.run_state == "not_run"
    assert payload.replay_import.rejection_reasons == ("import target must start at SHADOW",)
    assert payload.alerts.active_alert_count >= 4


def test_technical_dashboard_payload_defaults_governed_sections_without_raw_protocol_objects():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-tech-defaults",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
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

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "meta_learning", "local_replay_runtime"),
        active_engines=("engine_a", "engine_b"),
    )

    assert payload.build9x.status == "info"
    assert payload.build9x.diagnostics_count == 0
    assert payload.shadow.status == "planned"
    assert payload.shadow.verdict == "not_run"
    assert payload.micro_live.status == "planned"
    assert payload.micro_live.verdict == "not_run"
    assert payload.live_light.status == "planned"
    assert payload.live_light.verdict == "not_run"
    assert payload.build14.status == "planned"
    assert payload.build14.hard_state == "coded"
    assert payload.build14.live_promotion_eligible is False
    assert payload.build14.influence_mode == "read_only"
    assert payload.replay_import.status == "info"
    assert payload.replay_import.validation_status == "not_run"
    assert payload.alerts.backlog_stale_status == "healthy"


def test_technical_dashboard_payload_defaults_build14_to_shadow_enabled_when_module_active():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-build14-default-active",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
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

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "complete_enablers"),
        active_engines=("engine_a", "engine_b"),
    )

    assert payload.system.build14_status == "info"
    assert payload.build14.hard_state == "shadow_enabled"
    assert payload.build14.influence_mode == "shadow_enabled"
    assert payload.build14.action == "shadow_apply"
    assert payload.build14.candidate_effect == "shadow_enabled"
    assert payload.build14.reader_projections == ()


def test_technical_dashboard_payload_accepts_shadow_projection_summary():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-shadow-projection",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=18.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.15,
            capital_deployed_usdt=700.0,
            ce_net=0.0009,
        ),
        infra=collect_infra_metrics(queue_backlog=20),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
        shadow_projection=ShadowProjection(
            status="warning",
            run_state="completed",
            verdict="needs_review",
            truth_set_ref="shadow_truth:t1",
            validation_set_ref="shadow_validation:v1",
            divergent_comparison_count=2,
            blocking_comparison_count=0,
            total_comparison_count=7,
            build9x_diagnostics_count=2,
            open_hypotheses=1,
            replay_candidate_count=1,
            review_export_ready=False,
            import_artifact_id="artifact-shadow-1",
            import_lineage_version="a.v1.0.r1",
            blocking_reasons=("review export missing",),
            manual_review_required=True,
        ),
    )

    assert payload.system.shadow_status == "warning"
    assert payload.shadow.run_state == "completed"
    assert payload.shadow.validation_set_ref == "shadow_validation:v1"
    assert payload.shadow.blocking_reasons == ("review export missing",)


def test_technical_dashboard_payload_accepts_micro_live_projection_summary():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-micro-projection",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=18.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.15,
            capital_deployed_usdt=700.0,
            ce_net=0.0009,
        ),
        infra=collect_infra_metrics(queue_backlog=20),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
        micro_live_projection=MicroLiveProjection(
            status="healthy",
            run_state="ready_to_probe",
            verdict="allowed_to_probe",
            shadow_run_id="shadow-run-1",
            shadow_verdict="accepted",
            allowed_to_probe=True,
            requested_total_notional_usdt=20.0,
            approved_total_notional_usdt=20.0,
            approved_pair_notional_usdt=10.0,
            order_probe_limit=2,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b"),
            import_artifact_id="artifact-micro-1",
            import_lineage_version="a.v1.0.r1",
            observability_ready=True,
            halt_ready=True,
            onboarding_ready=True,
            blocking_reasons=(),
        ),
    )

    assert payload.system.micro_live_status == "healthy"
    assert payload.micro_live.run_state == "ready_to_probe"
    assert payload.micro_live.allowed_to_probe is True
    assert payload.micro_live.planned_pairs == ("BTCUSDT", "ETHUSDT")


def test_technical_dashboard_payload_accepts_live_light_projection_summary():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-live-projection",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.LIVE,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=18.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.15,
            capital_deployed_usdt=700.0,
            ce_net=0.0009,
        ),
        infra=collect_infra_metrics(queue_backlog=20),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
        live_light_projection=LiveLightProjection(
            status="healthy",
            run_state="ready_to_execute_small",
            verdict="allowed_to_execute_small",
            micro_live_run_id="micro-run-1",
            micro_live_verdict="allowed_to_probe",
            allowed_to_execute_small=True,
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=80.0,
            approved_pair_notional_usdt=40.0,
            execution_order_limit=3,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b"),
            import_artifact_id="artifact-live-1",
            import_lineage_version="a.v1.0.r1",
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            blocking_reasons=(),
        ),
    )

    assert payload.system.live_light_status == "healthy"
    assert payload.live_light.run_state == "ready_to_execute_small"
    assert payload.live_light.allowed_to_execute_small is True
    assert payload.live_light.planned_pairs == ("BTCUSDT", "ETHUSDT")


def test_technical_dashboard_payload_accepts_build14_projection_summary():
    dtr_summary, cra_report, break_even_report, edge_report = _sample_build9_reports()
    snapshot = collect_monitoring_snapshot(
        correlation_id="corr-build14-projection",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.LIVE,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=18.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.15,
            capital_deployed_usdt=700.0,
            ce_net=0.0009,
        ),
        infra=collect_infra_metrics(queue_backlog=20),
        meta=collect_meta_metrics(dtr_summary, cra_report, break_even_report, edge_report),
    )

    payload = build_technical_dashboard_payload(
        snapshot,
        active_modules=("monitoring", "ui", "protocols"),
        active_engines=("engine_a", "engine_b"),
        build14_projection=Build14Projection(
            status="warning",
            hard_state="shadow_enabled",
            live_promotion_eligible=False,
            influence_mode="limited_influence",
            action="downgrade_confidence",
            severity="elevated",
            summary="Build-14 limited influence reduces live-light confidence and budget",
            market_toxicity_value=0.46,
            market_toxicity_status="elevated",
            execution_fragility_value=0.35,
            execution_fragility_status="nominal",
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
            requires_manual_review=False,
            candidate_effect="confidence_downgrade",
            reason_codes=("market_toxicity_snapshot_elevated",),
            reader_projections=(
                Build14ReaderProjection(
                    reader_name="market_toxicity_snapshot",
                    signal_family="microstructure",
                    observed_value=0.46,
                    status="elevated",
                    detail="toxicity drift detected",
                    structured_log_key="build14.market_toxicity_snapshot",
                ),
                Build14ReaderProjection(
                    reader_name="false_breakout_model",
                    signal_family="ai_edge",
                    observed_value=0.22,
                    status="nominal",
                    detail="false breakout risk remains inside tolerance",
                    structured_log_key="build14.false_breakout_model",
                ),
            ),
        ),
    )

    assert payload.system.build14_status == "warning"
    assert payload.build14.hard_state == "shadow_enabled"
    assert payload.build14.live_promotion_eligible is False
    assert payload.build14.action == "downgrade_confidence"
    assert payload.build14.recommended_budget_factor == 0.85
    assert payload.build14.reason_codes == ("market_toxicity_snapshot_elevated",)
    assert tuple(reader.reader_name for reader in payload.build14.reader_projections) == (
        "market_toxicity_snapshot",
        "false_breakout_model",
    )
