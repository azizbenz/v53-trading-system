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
    Build14ReaderProjection,
    Build14Projection,
    Build9XProjection,
    LiveLightProjection,
    MicroLiveProjection,
    OperatorRuntimeProjection,
    ReplayImportProjection,
    ShadowProjection,
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
        learning_queue_depth=1200,
        learning_queue_oldest_age_ms=350,
        learning_worker_cpu_pct=8.5,
        learning_worker_rss_mb=180.0,
        learning_write_latency_ms=12.0,
        learning_export_failures_total=0,
        learning_log_loss_total=0,
        learning_unprocessed_items_count=0,
        learning_backlog_state="alert",
        learning_capture_mode="full_capture",
        learning_observability_reduced=False,
        learning_backpressure_active=False,
        review_blocked_due_to_incomplete_data=False,
        promotion_blocked_due_to_incomplete_data=False,
        learning_capacity_summary="queue=1200 / backlog=alert / mode=full_capture",
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
        "Pairs",
        "Engines",
        "Risk",
        "Execution",
        "Data & Infra",
        "Build-9 Meta",
        "Build-9X",
        "Build-11 Shadow",
        "Build-12 Micro-live",
        "Build-13 Live-Light",
        "Build-14 Enablers",
        "Operator Controls",
        "Replay & Import",
        "Alerts",
    }
    system = next(section for section in view.sections if section.title == "System")
    assert any(card.key == "governed_extensions" and "9X=warning" in card.value for card in system.cards)
    assert any(card.key == "governed_extensions" and "micro=planned" in card.value for card in system.cards)
    assert any(card.key == "governed_extensions" and "live=planned" in card.value for card in system.cards)
    assert any(card.key == "governed_extensions" and "b14=planned" in card.value for card in system.cards)
    build9x = next(section for section in view.sections if section.title == "Build-9X")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "2"
    assert next(card for card in build9x.cards if card.key == "hypotheses_open").value == "1"
    assert next(card for card in build9x.cards if card.key == "capacity_backpressure").detail == (
        "backlog=alert / oldest=350ms / unprocessed=0"
    )
    assert next(card for card in build9x.cards if card.key == "worker_budget").value == "cpu=8.5% / rss=180.0MB"
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")
    live = next(section for section in view.sections if section.title == "Build-13 Live-Light")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")
    pairs = next(section for section in view.sections if section.title == "Pairs")
    engines = next(section for section in view.sections if section.title == "Engines")
    risk = next(section for section in view.sections if section.title == "Risk")
    execution = next(section for section in view.sections if section.title == "Execution")
    infra = next(section for section in view.sections if section.title == "Data & Infra")
    assert next(card for card in shadow.cards if card.key == "shadow_run_state").value == "not_run"
    assert next(card for card in micro.cards if card.key == "micro_live_run_state").value == "not_run"
    assert next(card for card in live.cards if card.key == "live_light_run_state").value == "not_run"
    assert next(card for card in build14.cards if card.key == "build14_mode").value == "read_only / observe"
    assert next(card for card in build14.cards if card.key == "build14_readers").value.startswith("count=0 /")
    assert next(card for card in pairs.cards if card.key == "pair_btcusdt").value == "stale / fresh=9000ms"
    assert next(card for card in engines.cards if card.key == "engine_engine_a").value == "signals=2 / edge=12.0"
    assert next(card for card in risk.cards if card.key == "risk_exposure").value == "gross=35.0% / loss=8.0%"
    assert next(card for card in execution.cards if card.key == "execution_fills").value == "partial=0 / latency_p95=0ms"
    assert next(card for card in infra.cards if card.key == "infra_queue").value == "backlog=75 / hwm=75 / drop=0.0%"
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
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")
    live = next(section for section in view.sections if section.title == "Build-13 Live-Light")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")
    replay = next(section for section in view.sections if section.title == "Replay & Import")
    assert next(card for card in build9x.cards if card.key == "diagnostics_recent").value == "0"
    assert next(card for card in build9x.cards if card.key == "memory_review").status == "planned"
    assert next(card for card in build9x.cards if card.key == "capacity_backpressure").status == "planned"
    assert next(card for card in build9x.cards if card.key == "worker_budget").status == "planned"
    assert next(card for card in shadow.cards if card.key == "shadow_run_state").status == "planned"
    assert next(card for card in micro.cards if card.key == "micro_live_run_state").status == "planned"
    assert next(card for card in live.cards if card.key == "live_light_run_state").status == "planned"
    assert next(card for card in build14.cards if card.key == "build14_mode").status == "planned"
    assert next(card for card in replay.cards if card.key == "artifact_manifest").value == "none"
    assert next(card for card in replay.cards if card.key == "validation_status").value == "not_run"


def test_technical_dashboard_view_projects_shadow_enabled_build14_when_module_active():
    payload = build_technical_dashboard_payload(
        _snapshot(infra=collect_infra_metrics()),
        active_modules=("monitoring", "ui", "complete_enablers"),
        active_engines=("engine_a", "engine_b"),
    )

    view = build_technical_dashboard_view(payload)
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")

    assert next(card for card in build14.cards if card.key == "build14_mode").value == (
        "shadow_enabled / shadow_apply"
    )
    assert next(card for card in build14.cards if card.key == "build14_candidate_effect").value == (
        "shadow_enabled"
    )
    assert next(card for card in build14.cards if card.key == "build14_guardrails").value == (
        "shadow_enabled"
    )


def test_technical_dashboard_view_projects_alerts_and_engine_staleness_without_prefilled_alerts():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("interface_contracts", "meta_learning", "local_replay_runtime", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        operator_runtime=OperatorRuntimeProjection(
            event_count=2,
            latest_event_type="screen_opened",
            latest_event_message="screen opened: overview",
            pending_notification_count=1,
            pending_notification_alert_ids=("corr-tech:loss",),
            acknowledged_notification_count=0,
        ),
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
    assert any(card.key == "operator_events" and card.value == "2" for card in alerts.cards)
    assert any(card.key == "operator_notifications" and card.value == "pending=1 / ack=0" for card in alerts.cards)


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
        "shadow_supervision",
        "micro_live_supervision",
        "live_light_supervision",
        "build14_supervision",
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


def test_technical_dashboard_view_projects_shadow_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
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
            blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
            manual_review_required=True,
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    shadow = next(section for section in view.sections if section.title == "Build-11 Shadow")

    governed = next(card for card in system.cards if card.key == "governed_extensions")
    assert "shadow=warning" in governed.value
    assert next(card for card in shadow.cards if card.key == "shadow_verdict").value == "needs_review"
    assert next(card for card in shadow.cards if card.key == "shadow_divergences").status == "warning"
    assert next(card for card in shadow.cards if card.key == "shadow_blocking_reasons").detail == (
        "Build-9X review export must be ready before accepting Shadow"
    )


def test_technical_dashboard_view_projects_micro_live_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(),
        active_modules=("protocols", "monitoring", "ui"),
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
            operator_safing_action="downgrade_to_shadow",
            operator_safing_target_runtime_mode="shadow",
            operator_safing_reason="manual requalification requested",
            blocking_reasons=(),
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    micro = next(section for section in view.sections if section.title == "Build-12 Micro-live")

    governed = next(card for card in system.cards if card.key == "governed_extensions")
    assert "micro=healthy" in governed.value
    assert next(card for card in micro.cards if card.key == "micro_live_verdict").value == "allowed_to_probe"
    assert next(card for card in micro.cards if card.key == "micro_live_guardrails").status == "healthy"
    assert next(card for card in micro.cards if card.key == "micro_live_safing_request").value == (
        "downgrade_to_shadow -> shadow"
    )
    assert next(card for card in micro.cards if card.key == "micro_live_safing_request").detail == (
        "manual requalification requested"
    )


def test_technical_dashboard_view_projects_live_light_summary_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE),
        active_modules=("protocols", "monitoring", "ui"),
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
            operator_safing_action="downgrade_to_micro_live",
            operator_safing_target_runtime_mode="micro_live",
            operator_safing_reason="execution drift requires step-down",
            blocking_reasons=(),
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    live = next(section for section in view.sections if section.title == "Build-13 Live-Light")

    governed = next(card for card in system.cards if card.key == "governed_extensions")
    assert "live=healthy" in governed.value
    assert next(card for card in live.cards if card.key == "live_light_verdict").value == "allowed_to_execute_small"
    assert next(card for card in live.cards if card.key == "live_light_readiness").status == "healthy"
    assert next(card for card in live.cards if card.key == "live_light_safing_request").value == (
        "downgrade_to_micro_live -> micro_live"
    )
    assert next(card for card in live.cards if card.key == "live_light_safing_request").detail == (
        "execution drift requires step-down"
    )


def test_technical_dashboard_view_exposes_operator_controls_for_current_runtime():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE, infra=collect_infra_metrics(kill_switch_active=True)),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        operator_runtime=OperatorRuntimeProjection(
            event_count=3,
            latest_event_type="operator_action_accepted",
            latest_event_message="manual safing accepted",
            latest_safing_action="downgrade_to_micro_live",
            latest_safing_source_runtime_mode="live",
            latest_safing_target_runtime_mode="micro_live",
            latest_safing_reason="execution drift requires step-down",
            pending_notification_count=0,
            acknowledged_notification_count=1,
            latest_acknowledged_alert_id="corr-tech:loss",
        ),
    )

    view = build_technical_dashboard_view(payload)
    operator = next(section for section in view.sections if section.title == "Operator Controls")

    assert next(card for card in operator.cards if card.key == "operator_manual_scope").detail == (
        "view_critical_screens, suspend_pair, request_pair_resume, suspend_engine, "
        "set_halted, downgrade_to_micro_live, downgrade_to_shadow, view_alert_history, "
        "acknowledge_critical_alert"
    )
    assert next(card for card in operator.cards if card.key == "operator_safing_controls").detail == (
        "set_halted, downgrade_to_micro_live, downgrade_to_shadow"
    )
    assert next(card for card in operator.cards if card.key == "operator_latest_safing").value == (
        "downgrade_to_micro_live -> micro_live"
    )
    assert next(card for card in operator.cards if card.key == "operator_latest_safing").detail == (
        "execution drift requires step-down"
    )
    assert next(card for card in operator.cards if card.key == "operator_kill_path").value == "active"
    assert next(card for card in operator.cards if card.key == "operator_kill_path").status == "critical"


def test_technical_dashboard_view_projects_build14_limited_influence_when_available():
    payload = build_technical_dashboard_payload(
        _snapshot(runtime_mode=RuntimeMode.LIVE),
        active_modules=("protocols", "monitoring", "ui"),
        active_engines=("engine_a", "engine_b"),
        build14_projection=Build14Projection(
            status="warning",
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
                    reader_name="competition_monitor",
                    signal_family="risk",
                    observed_value=0.18,
                    status="nominal",
                    detail="competition remains within tolerance",
                    structured_log_key="build14.competition_monitor",
                ),
            ),
        ),
        live_light_projection=LiveLightProjection(
            status="warning",
            run_state="ready_to_execute_small",
            verdict="allowed_to_execute_small",
            micro_live_run_id="micro-run-1",
            micro_live_verdict="allowed_to_probe",
            allowed_to_execute_small=True,
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=68.0,
            approved_pair_notional_usdt=34.0,
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
            build14_influence_mode="limited_influence",
            build14_action="downgrade_confidence",
            build14_severity="elevated",
            build14_summary="Build-14 limited influence reduces live-light confidence and budget",
            build14_reason_codes=("market_toxicity_snapshot_elevated",),
            build14_confidence_penalty_weight=0.10,
            build14_recommended_budget_factor=0.85,
        ),
    )

    view = build_technical_dashboard_view(payload)
    system = next(section for section in view.sections if section.title == "System")
    live = next(section for section in view.sections if section.title == "Build-13 Live-Light")
    build14 = next(section for section in view.sections if section.title == "Build-14 Enablers")

    governed = next(card for card in system.cards if card.key == "governed_extensions")
    assert "b14=warning" in governed.value
    assert next(card for card in live.cards if card.key == "live_light_budget").detail.endswith(
        "build14=downgrade_confidence@0.85"
    )
    assert next(card for card in build14.cards if card.key == "build14_candidate_effect").value == "confidence_downgrade"
    assert next(card for card in build14.cards if card.key == "build14_guardrails").detail == "market_toxicity_snapshot_elevated"
    assert next(card for card in build14.cards if card.key == "build14_readers").value.startswith("count=2 /")
    assert next(card for card in build14.cards if card.key == "build14_reader_market_toxicity_snapshot").value == (
        "elevated (0.46)"
    )
    assert "family=microstructure" in next(
        card for card in build14.cards if card.key == "build14_reader_market_toxicity_snapshot"
    ).detail
