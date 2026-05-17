"""Tests for bounded challenger verdict monitoring and observability."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertSeverity, ProfileId, RuntimeMode
from meta import (
    build_break_even_report,
    build_cra_report,
    build_dtr_summary,
    build_edge_report,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from monitoring import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactVerdictBundleProjection,
    MonitoringRuntime,
    build_observability_export,
    build_technical_dashboard_payload,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_portfolio_metrics,
)
from monitoring.challenger_evidence_alerts import build_shadow_challenger_alerts


def _snapshot(correlation_id: str) -> object:
    return collect_monitoring_snapshot(
        correlation_id=correlation_id,
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=250.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(
            queue_backlog=0,
            persisted_metric_names=(
                "backlog_high_water_mark",
                "drop_rate_pct",
                "stale_spike_count",
                "recovery_retry_count",
                "kill_switch_active",
            ),
        ),
        meta=_meta_metrics(),
    )


def _meta_metrics():
    return collect_meta_metrics(
        build_dtr_summary(
            (
                build_dtr(
                    dtr_id="shadow-challenger-dtr",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.SELECTED,
                    timestamp=1_000.0,
                ),
            ),
            total_opportunities=1,
        ),
        build_cra_report(()),
        build_break_even_report(()),
        build_edge_report(()),
    )


def _challenger_visibility() -> ArtifactRuntimeVisibilityProjection:
    return ArtifactRuntimeVisibilityProjection(
        slot="shadow_challenger",
        artifact_kind="ml_model_artifact",
        artifact_id="ml-shadow-1",
        shadow_only=True,
        influence_detail="shadow_only / non_influential",
    )


def _ready_comparison() -> ArtifactComparisonProjection:
    return ArtifactComparisonProjection(
        champion_artifact_id="ml-1",
        challenger_artifact_id="ml-shadow-1",
        event_count=5,
        comparison_status="shadow_ready",
    )


def test_technical_dashboard_payload_derives_missing_challenger_evidence_warning() -> None:
    payload = build_technical_dashboard_payload(
        _snapshot("corr-shadow-challenger-missing"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert "shadow_challenger:shadow_challenger_evidence_missing" in payload.alerts.alert_ids
    assert payload.alerts.active_alert_count == 1


def test_technical_dashboard_payload_derives_stale_challenger_evidence_warning() -> None:
    payload = build_technical_dashboard_payload(
        _snapshot("corr-shadow-challenger-stale"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-24",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=1,
            ready_family_count=1,
            ml_comparison_status="shadow_ready",
            evidence_ref="exports/shadow_verdict_bundle.json",
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert "shadow_challenger:shadow_challenger_evidence_stale" in payload.alerts.alert_ids
    assert payload.alerts.active_alert_count == 1


def test_shadow_challenger_alerts_mark_invalid_evidence_critical() -> None:
    alerts = build_shadow_challenger_alerts(
        _snapshot("corr-shadow-challenger-invalid"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            overall_verdict="invalid_evidence",
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert len(alerts) == 1
    assert alerts[0].alert_id == "shadow_challenger:shadow_challenger_invalid_evidence"
    assert alerts[0].severity == AlertSeverity.CRITICAL
    assert alerts[0].category == AlertCategory.INFRA


def test_shadow_challenger_alerts_mark_sharia_scope_blocked_warning() -> None:
    alerts = build_shadow_challenger_alerts(
        _snapshot("corr-shadow-challenger-halal"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="sharia_scope_blocked",
            configured_family_count=1,
            sharia_blocked_family_count=1,
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert len(alerts) == 1
    assert alerts[0].alert_id == "shadow_challenger:shadow_challenger_sharia_scope_blocked"
    assert alerts[0].severity == AlertSeverity.WARNING
    assert alerts[0].category == AlertCategory.RISK


def test_shadow_challenger_alerts_do_not_open_runtime_inputs_missing_alert() -> None:
    alerts = build_shadow_challenger_alerts(
        _snapshot("corr-shadow-challenger-runtime-inputs"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="shadow_runtime_inputs_missing",
            configured_family_count=1,
            runtime_inputs_missing_family_count=1,
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert alerts == ()


def test_monitoring_runtime_tracks_shadow_challenger_alert_resolution() -> None:
    runtime = MonitoringRuntime()

    opened = runtime.evaluate(
        correlation_id="corr-shadow-challenger-open",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=250.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(queue_backlog=0),
        meta=_meta_metrics(),
        artifact_runtime_visibility=(_challenger_visibility(),),
        shadow_last_completed_session_date="2026-04-25",
    )
    resolved = runtime.evaluate(
        correlation_id="corr-shadow-challenger-resolved",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_500,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=1,
            gross_capacity_used_pct=10.0,
            loss_capacity_used_pct=2.0,
            beta_utilization=0.1,
            capital_deployed_usdt=250.0,
            ce_net=0.001,
        ),
        infra=collect_infra_metrics(queue_backlog=0),
        meta=_meta_metrics(),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_comparisons=(_ready_comparison(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=1,
            ready_family_count=1,
            ml_comparison_status="shadow_ready",
            evidence_ref="exports/shadow_verdict_bundle.json",
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    assert any(
        entry.alert_id == "shadow_challenger:shadow_challenger_evidence_missing"
        and entry.status == "open"
        for entry in opened.health_payload.alert_history
    )
    assert any(
        entry.alert_id == "shadow_challenger:shadow_challenger_evidence_missing"
        and entry.status == "resolved"
        for entry in resolved.health_payload.alert_history
    )


def test_observability_export_contains_shadow_challenger_verdict_metrics() -> None:
    payload = build_technical_dashboard_payload(
        _snapshot("corr-shadow-challenger-observability"),
        artifact_runtime_visibility=(_challenger_visibility(),),
        artifact_comparisons=(_ready_comparison(),),
        artifact_verdict_bundle=ArtifactVerdictBundleProjection(
            session_date="2026-04-25",
            overall_verdict="shadow_validated",
            operator_recommendation="review_for_micro_live_candidate",
            configured_family_count=2,
            ready_family_count=1,
            ml_comparison_status="shadow_ready",
            regime_detector_comparison_status="shadow_runtime_inputs_missing",
            evidence_ref="exports/shadow_verdict_bundle.json",
        ),
        shadow_last_completed_session_date="2026-04-25",
    )

    export = build_observability_export(payload)
    names = {sample.name for sample in export.samples}

    assert "v53_shadow_challenger_verdict" in names
    assert "v53_shadow_challenger_family_status" in names
    assert "v53_shadow_challenger_evidence_missing" in names
    assert "v53_shadow_challenger_evidence_stale" in names
    assert any(
        sample.name == "v53_shadow_challenger_verdict"
        and sample.labels.get("overall_verdict") == "shadow_validated"
        and sample.labels.get("operator_recommendation")
        == "review_for_micro_live_candidate"
        for sample in export.samples
    )
    assert any(
        sample.name == "v53_shadow_challenger_family_status"
        and sample.labels.get("family") == "ml"
        and sample.labels.get("status") == "shadow_ready"
        for sample in export.samples
    )
    assert any(
        sample.name == "v53_shadow_challenger_evidence_missing"
        and sample.value == 0.0
        for sample in export.samples
    )
    assert any(
        sample.name == "v53_shadow_challenger_evidence_stale"
        and sample.value == 0.0
        for sample in export.samples
    )
