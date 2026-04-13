from __future__ import annotations

from monitoring.contracts import DiskUsageSample, ProcessMetricsSample
from monitoring.shadow_vps_service_monitoring import (
    build_shadow_vps_service_monitoring_payload,
    build_shadow_vps_service_observability_export,
)
from protocols.shadow_vps_service import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
    ShadowVpsServiceStatus,
)


def test_shadow_vps_service_monitoring_payload_projects_state_and_process_metrics():
    state = ShadowVpsServiceState(
        service_status=ShadowVpsServiceStatus.RUNNING,
        last_heartbeat_at=1_800_000_000.0,
        loop_count=4,
        success_count=3,
        idle_count=1,
        failure_count=0,
        resumed=True,
        last_selected_session_date="2026-04-10",
        last_completed_session_date="2026-04-09",
        last_campaign_summary_ref="E:/shadow/shadow_vps_service.campaign_summary.json",
        last_runtime_evidence_bundle_ref="E:/shadow/runtime_evidence/2026-04-09.shadow_vps_runtime_evidence.json",
        last_execution_telemetry_ref="E:/shadow/shadow_vps_service_execution_telemetry.json",
        last_execution_telemetry_status="written",
        last_telegram_alert_delivery_status="sent",
        last_telegram_alert_delivery_event_type="shadow_day_completed",
        last_telegram_alert_delivery_error="",
        last_telegram_alert_config_ref="E:/shadow/telegram_alert_config.json",
        last_telegram_alert_config_source="live_websocket_config",
        last_telegram_alert_key_ref="E:/shadow/telegram_alert.key",
        last_telegram_alert_key_source="cli",
        last_execution_runtime_bootstrap_ref="E:/shadow/execution_runtime_bootstrap.summary.json",
        last_execution_runtime_bootstrap_status="ready",
        last_execution_runtime_bootstrap_source="live_websocket_config",
        last_execution_runtime_gatekeeper_audit_ref="E:/shadow/artifacts/gatekeeper/audit.jsonl",
        last_execution_runtime_gatekeeper_audit_source="cli",
        last_execution_runtime_projection_ref="E:/shadow/local_lab_execution_runtime_projection.json",
        last_execution_runtime_projection_source="cli",
        last_regime_lite_assessment_ref="E:/shadow/regime_lite_assessment.json",
        last_regime_lite_assessment_source="live_websocket_config",
        last_regime_lite_safing_recommendation_ref="E:/shadow/regime_lite_safing_recommendation.json",
        last_regime_lite_safing_recommendation_source="cli",
        last_info_stress_assessment_ref="E:/shadow/info_stress_assessment.json",
        last_info_stress_assessment_source="cli",
        last_export_dir_ref="E:/shadow/exports/2026-04-09",
    )
    campaign_summary = ShadowVpsCampaignSummary(
        service_status=ShadowVpsServiceStatus.RUNNING,
        loop_count=4,
        success_count=3,
        idle_count=1,
        failure_count=0,
        resumed=True,
        last_selected_session_date="2026-04-10",
        last_completed_session_date="2026-04-09",
        acquisition_mode="dated_export",
        accepted=False,
        consecutive_days=3,
        remaining_days=27,
        promotion_gate_passed=False,
        runtime_data_source="recorded_replay",
        runtime_evidence_summary="shadow runtime evidence ok",
        telegram_alert_delivery_status="sent",
        telegram_alert_delivery_event_type="shadow_day_completed",
        telegram_alert_delivery_error="",
        telegram_alert_config_ref="E:/shadow/telegram_alert_config.json",
        telegram_alert_config_source="live_websocket_config",
        telegram_alert_key_ref="E:/shadow/telegram_alert.key",
        telegram_alert_key_source="cli",
        execution_runtime_bootstrap_ref="E:/shadow/execution_runtime_bootstrap.summary.json",
        execution_runtime_bootstrap_status="ready",
        execution_runtime_bootstrap_source="live_websocket_config",
        execution_runtime_gatekeeper_audit_ref="E:/shadow/artifacts/gatekeeper/audit.jsonl",
        execution_runtime_gatekeeper_audit_source="cli",
        execution_runtime_bootstrap_user_data_stream_enabled=False,
        execution_runtime_bootstrap_reconciliation_boot_executed=True,
        execution_runtime_bootstrap_reconciliation_boot_trading_blocked=False,
        execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped=False,
        execution_runtime_bootstrap_reconciliation_boot_detail="boot reconciliation aligned local and remote state",
        execution_runtime_bootstrap_reconciliation_boot_recovery_action="none",
        execution_runtime_bootstrap_reconciliation_boot_divergence_count=0,
        execution_runtime_projection_ref="E:/shadow/local_lab_execution_runtime_projection.json",
        execution_runtime_projection_source="cli",
        regime_lite_assessment_ref="E:/shadow/regime_lite_assessment.json",
        regime_lite_assessment_source="live_websocket_config",
        regime_lite_safing_recommendation_ref="E:/shadow/regime_lite_safing_recommendation.json",
        regime_lite_safing_recommendation_source="cli",
        info_stress_assessment_ref="E:/shadow/info_stress_assessment.json",
        info_stress_assessment_source="cli",
        execution_runtime_projection_status="ready",
        execution_runtime_projection_ready=True,
        execution_runtime_projection_consumer_count=3,
        execution_runtime_projection_ready_consumer_count=3,
        execution_runtime_projection_partial_consumer_count=0,
        execution_runtime_projection_blocked_consumer_count=0,
        execution_runtime_projection_bridge_status="healthy",
        execution_runtime_projection_bridge_loaded=True,
        execution_runtime_projection_rate_limit_model_loaded=True,
        execution_runtime_projection_spread_guard_model_loaded=True,
        execution_runtime_projection_slippage_model_loaded=True,
        regime_lite_governance_status="ready",
        regime_lite_state="extreme",
        regime_lite_candidate_state="extreme",
        regime_lite_entries_blocked=True,
        regime_lite_sudden_event=True,
        regime_lite_safing_severity="halt_recommended",
        regime_lite_safing_should_block_new_entries=True,
        regime_lite_safing_should_exit_all=True,
        regime_lite_safing_recommended_operator_action="set_halted",
        regime_lite_safing_operator_safing_request_action="set_halted",
        regime_lite_safing_operator_safing_request_source_runtime_mode="shadow",
        regime_lite_safing_reason_codes=("RISK_REGIME_EXTREME",),
        regime_lite_safing_detail="EXTREME regime_lite state recommends HALT_RECOMMENDED",
        info_stress_governance_status="assessment_only",
        info_stress_level="extreme",
        info_stress_alert_count=3,
        info_stress_entries_blocked=True,
        info_stress_entries_blocked_until_ts=1_700_086_400,
        info_stress_reason_codes=("INFO_STRESS_SPREAD_EXPLOSION",),
        info_stress_detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
    )
    runtime_bundle = ShadowVpsRuntimeEvidenceBundle(
        session_date="2026-04-09",
        acquisition_mode="dated_export",
        runtime_data_source="recorded_replay",
        runtime_evidence_summary="shadow runtime evidence ok",
        telegram_alert_config_ref="E:/shadow/telegram_alert_config.json",
        telegram_alert_config_source="live_websocket_config",
        telegram_alert_key_ref="E:/shadow/telegram_alert.key",
        telegram_alert_key_source="cli",
        execution_runtime_bootstrap_ref="E:/shadow/execution_runtime_bootstrap.summary.json",
        execution_runtime_bootstrap_status="ready",
        execution_runtime_bootstrap_source="live_websocket_config",
        execution_runtime_gatekeeper_audit_ref="E:/shadow/artifacts/gatekeeper/audit.jsonl",
        execution_runtime_gatekeeper_audit_source="cli",
        execution_runtime_bootstrap_user_data_stream_enabled=False,
        execution_runtime_bootstrap_reconciliation_boot_executed=True,
        execution_runtime_bootstrap_reconciliation_boot_trading_blocked=False,
        execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped=False,
        execution_runtime_bootstrap_reconciliation_boot_detail="boot reconciliation aligned local and remote state",
        execution_runtime_bootstrap_reconciliation_boot_recovery_action="none",
        execution_runtime_bootstrap_reconciliation_boot_divergence_count=0,
        accepted=False,
        consecutive_days=3,
        remaining_days=27,
        execution_runtime_projection_ref="E:/shadow/local_lab_execution_runtime_projection.json",
        execution_runtime_projection_source="cli",
        regime_lite_assessment_ref="E:/shadow/regime_lite_assessment.json",
        regime_lite_assessment_source="live_websocket_config",
        regime_lite_safing_recommendation_ref="E:/shadow/regime_lite_safing_recommendation.json",
        regime_lite_safing_recommendation_source="cli",
        info_stress_assessment_ref="E:/shadow/info_stress_assessment.json",
        info_stress_assessment_source="cli",
        execution_runtime_projection_status="ready",
        execution_runtime_projection_ready=True,
        execution_runtime_projection_consumer_count=3,
        execution_runtime_projection_ready_consumer_count=3,
        execution_runtime_projection_partial_consumer_count=0,
        execution_runtime_projection_blocked_consumer_count=0,
        execution_runtime_projection_bridge_status="healthy",
        execution_runtime_projection_bridge_loaded=True,
        execution_runtime_projection_rate_limit_model_loaded=True,
        execution_runtime_projection_spread_guard_model_loaded=True,
        execution_runtime_projection_slippage_model_loaded=True,
        regime_lite_governance_status="ready",
        regime_lite_state="extreme",
        regime_lite_candidate_state="extreme",
        regime_lite_entries_blocked=True,
        regime_lite_sudden_event=True,
        regime_lite_safing_severity="halt_recommended",
        regime_lite_safing_should_block_new_entries=True,
        regime_lite_safing_should_exit_all=True,
        regime_lite_safing_recommended_operator_action="set_halted",
        regime_lite_safing_operator_safing_request_action="set_halted",
        regime_lite_safing_operator_safing_request_source_runtime_mode="shadow",
        regime_lite_safing_reason_codes=("RISK_REGIME_EXTREME",),
        regime_lite_safing_detail="EXTREME regime_lite state recommends HALT_RECOMMENDED",
        info_stress_governance_status="assessment_only",
        info_stress_level="extreme",
        info_stress_alert_count=3,
        info_stress_entries_blocked=True,
        info_stress_entries_blocked_until_ts=1_700_086_400,
        info_stress_reason_codes=("INFO_STRESS_SPREAD_EXPLOSION",),
        info_stress_detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
    )
    process = ProcessMetricsSample(
        pid=4321,
        cpu_pct=6.5,
        ram_pct=12.5,
        rss_mb=256.0,
        thread_count=11,
        sampling_mode="test_mode",
    )

    payload = build_shadow_vps_service_monitoring_payload(
        timestamp_ms=1_800_000_002_500,
        state=state,
        process=process,
        disk=DiskUsageSample(
            path="E:/shadow",
            total_gb=100.0,
            free_gb=40.0,
            used_pct=60.0,
            sampling_mode="test_mode",
        ),
        campaign_summary=campaign_summary,
        runtime_evidence_bundle=runtime_bundle,
        state_path="E:/shadow/shadow_vps_service.state.json",
        events_path="E:/shadow/shadow_vps_service.events.jsonl",
        recent_events_summary_ref="E:/shadow/shadow_vps_service_recent_events.json",
        node_exporter_textfile_ref="E:/node-textfile/v53_shadow_vps_service.prom",
    )

    assert payload.status == "healthy"
    assert payload.service_status == "running"
    assert payload.heartbeat_age_ms == 2_500
    assert payload.acquisition_mode == "dated_export"
    assert payload.runtime_data_source == "recorded_replay"
    assert payload.process.pid == 4321
    assert payload.process.thread_count == 11
    assert payload.disk.used_pct == 60.0
    assert payload.state_path.endswith("shadow_vps_service.state.json")
    assert payload.events_path.endswith("shadow_vps_service.events.jsonl")
    assert payload.recent_events_summary_ref.endswith(
        "shadow_vps_service_recent_events.json"
    )
    assert payload.execution_telemetry_ref.endswith(
        "shadow_vps_service_execution_telemetry.json"
    )
    assert payload.execution_telemetry_status == "written"
    assert payload.telegram_alert_delivery_status == "sent"
    assert payload.telegram_alert_delivery_event_type == "shadow_day_completed"
    assert payload.telegram_alert_delivery_error == ""
    assert payload.telegram_alert_config_ref.endswith("telegram_alert_config.json")
    assert payload.telegram_alert_config_source == "live_websocket_config"
    assert payload.telegram_alert_key_ref.endswith("telegram_alert.key")
    assert payload.telegram_alert_key_source == "cli"
    assert payload.execution_runtime_bootstrap_ref.endswith(
        "execution_runtime_bootstrap.summary.json"
    )
    assert payload.execution_runtime_bootstrap_status == "ready"
    assert payload.execution_runtime_bootstrap_source == "live_websocket_config"
    assert payload.execution_runtime_gatekeeper_audit_ref.endswith("audit.jsonl")
    assert payload.execution_runtime_gatekeeper_audit_source == "cli"
    assert payload.execution_runtime_bootstrap_reconciliation_boot_executed is True
    assert payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked is False
    assert (
        payload.execution_runtime_bootstrap_reconciliation_boot_divergence_count == 0
    )
    assert payload.execution_runtime_projection_ref.endswith(
        "local_lab_execution_runtime_projection.json"
    )
    assert payload.execution_runtime_projection_source == "cli"
    assert payload.regime_lite_assessment_ref.endswith("regime_lite_assessment.json")
    assert payload.regime_lite_assessment_source == "live_websocket_config"
    assert payload.regime_lite_safing_recommendation_ref.endswith(
        "regime_lite_safing_recommendation.json"
    )
    assert payload.regime_lite_safing_recommendation_source == "cli"
    assert payload.info_stress_assessment_ref.endswith("info_stress_assessment.json")
    assert payload.info_stress_assessment_source == "cli"
    assert payload.execution_runtime_projection_status == "ready"
    assert payload.execution_runtime_projection_ready is True
    assert payload.execution_runtime_projection_ready_consumer_count == 3
    assert payload.execution_runtime_projection_bridge_status == "healthy"
    assert payload.execution_runtime_projection_bridge_loaded is True
    assert payload.execution_runtime_projection_rate_limit_model_loaded is True
    assert payload.execution_runtime_projection_spread_guard_model_loaded is True
    assert payload.execution_runtime_projection_slippage_model_loaded is True
    assert payload.regime_lite_governance_status == "ready"
    assert payload.regime_lite_state == "extreme"
    assert payload.regime_lite_safing_severity == "halt_recommended"
    assert payload.regime_lite_safing_should_block_new_entries is True
    assert payload.regime_lite_safing_should_exit_all is True
    assert payload.regime_lite_safing_recommended_operator_action == "set_halted"
    assert payload.info_stress_governance_status == "assessment_only"
    assert payload.info_stress_level == "extreme"
    assert payload.info_stress_alert_count == 3
    assert payload.info_stress_entries_blocked is True
    assert payload.node_exporter_textfile_ref.endswith(
        "v53_shadow_vps_service.prom"
    )
    assert (
        "regime_lite=halt_recommended@extreme@live_websocket_config/cli"
        in payload.detail
    )
    assert "info_stress=assessment_only@extreme@cli" in payload.detail
    assert "telegram=sent@shadow_day_completed@live_websocket_config" in payload.detail
    assert "exec_bootstrap=ready@live_websocket_config@cli/div=0" in payload.detail


def test_shadow_vps_service_observability_export_emits_process_and_service_metrics():
    payload = build_shadow_vps_service_monitoring_payload(
        timestamp_ms=1_800_000_003_000,
        state=ShadowVpsServiceState(
            service_status=ShadowVpsServiceStatus.STOPPED,
            loop_count=2,
            success_count=2,
            idle_count=0,
            failure_count=0,
            last_heartbeat_at=1_800_000_002.0,
        ),
        process=ProcessMetricsSample(
            pid=99,
            cpu_pct=1.25,
            ram_pct=2.5,
            rss_mb=64.0,
            thread_count=4,
            sampling_mode="test_mode",
        ),
        disk=DiskUsageSample(
            path="E:/shadow",
            total_gb=100.0,
            free_gb=20.0,
            used_pct=80.0,
            sampling_mode="test_mode",
        ),
        campaign_summary=ShadowVpsCampaignSummary(
            service_status=ShadowVpsServiceStatus.STOPPED,
            loop_count=2,
            success_count=2,
            idle_count=0,
            failure_count=0,
            acquisition_mode="dated_export",
            accepted=False,
            consecutive_days=2,
            remaining_days=28,
            promotion_gate_passed=False,
            runtime_data_source="recorded_replay",
            runtime_evidence_summary="ok",
            telegram_alert_delivery_status="failed",
            telegram_alert_delivery_event_type="shadow_day_failed",
            telegram_alert_delivery_error="http_500",
            telegram_alert_config_source="cli",
            execution_runtime_bootstrap_status="ready",
            execution_runtime_bootstrap_source="live_websocket_config",
            execution_runtime_gatekeeper_audit_source="cli",
            execution_runtime_bootstrap_user_data_stream_enabled=False,
            execution_runtime_bootstrap_reconciliation_boot_executed=True,
            execution_runtime_bootstrap_reconciliation_boot_trading_blocked=False,
            execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped=False,
            execution_runtime_bootstrap_reconciliation_boot_recovery_action="none",
            execution_runtime_bootstrap_reconciliation_boot_divergence_count=0,
            execution_runtime_projection_source="cli",
            regime_lite_assessment_source="live_websocket_config",
            regime_lite_safing_recommendation_source="cli",
            info_stress_assessment_source="cli",
            execution_runtime_projection_status="ready",
            execution_runtime_projection_ready=True,
            execution_runtime_projection_consumer_count=3,
            execution_runtime_projection_ready_consumer_count=3,
            execution_runtime_projection_partial_consumer_count=0,
            execution_runtime_projection_blocked_consumer_count=0,
            execution_runtime_projection_bridge_status="healthy",
            execution_runtime_projection_bridge_loaded=True,
            execution_runtime_projection_rate_limit_model_loaded=True,
            execution_runtime_projection_spread_guard_model_loaded=True,
            execution_runtime_projection_slippage_model_loaded=True,
            regime_lite_governance_status="ready",
            regime_lite_state="extreme",
            regime_lite_candidate_state="extreme",
            regime_lite_entries_blocked=True,
            regime_lite_sudden_event=True,
            regime_lite_safing_severity="halt_recommended",
            regime_lite_safing_should_block_new_entries=True,
            regime_lite_safing_should_exit_all=True,
            regime_lite_safing_recommended_operator_action="set_halted",
            regime_lite_safing_operator_safing_request_action="set_halted",
            regime_lite_safing_operator_safing_request_source_runtime_mode="shadow",
            regime_lite_safing_reason_codes=("RISK_REGIME_EXTREME",),
            regime_lite_safing_detail="EXTREME regime_lite state recommends HALT_RECOMMENDED",
            info_stress_governance_status="assessment_only",
            info_stress_level="extreme",
            info_stress_alert_count=3,
            info_stress_entries_blocked=True,
            info_stress_entries_blocked_until_ts=1_700_086_400,
            info_stress_reason_codes=("INFO_STRESS_SPREAD_EXPLOSION",),
            info_stress_detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
        ),
    )

    export = build_shadow_vps_service_observability_export(payload)

    assert export.correlation_id == "shadow-vps-service"
    assert export.text_payload.startswith("# V5.3 Shadow VPS service observability export")
    sample_names = {sample.name for sample in export.samples}
    assert "v53_shadow_vps_service_status" in sample_names
    assert "v53_shadow_vps_process_cpu_pct" in sample_names
    assert "v53_shadow_vps_process_rss_mb" in sample_names
    assert "v53_shadow_vps_disk_used_pct" in sample_names
    assert "v53_shadow_vps_execution_telemetry_ready" in sample_names
    assert "v53_shadow_vps_telegram_alert_delivery_status" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_status" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_divergence_count" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_trading_blocked" in sample_names
    assert "v53_shadow_vps_execution_runtime_projection_ready" in sample_names
    assert "v53_shadow_vps_execution_runtime_projection_bridge_loaded" in sample_names
    assert "v53_shadow_vps_execution_runtime_projection_rate_limit_model_loaded" in sample_names
    assert "v53_shadow_vps_execution_runtime_projection_spread_guard_model_loaded" in sample_names
    assert "v53_shadow_vps_execution_runtime_projection_slippage_model_loaded" in sample_names
    assert "v53_shadow_vps_regime_lite_safing_status" in sample_names
    assert "v53_shadow_vps_regime_lite_entries_blocked" in sample_names
    assert "v53_shadow_vps_regime_lite_should_exit_all" in sample_names
    assert "v53_shadow_vps_info_stress_status" in sample_names
    assert "v53_shadow_vps_info_stress_alert_count" in sample_names
    assert "v53_shadow_vps_info_stress_entries_blocked" in sample_names
    regime_status_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_regime_lite_safing_status"
    )
    assert regime_status_sample.labels["assessment_source"] == "live_websocket_config"
    assert regime_status_sample.labels["safing_source"] == "cli"
    info_stress_status_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_info_stress_status"
    )
    assert info_stress_status_sample.labels["assessment_source"] == "cli"
    assert info_stress_status_sample.labels["level"] == "extreme"
    telegram_status_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_telegram_alert_delivery_status"
    )
    assert telegram_status_sample.labels["delivery_status"] == "failed"
    assert telegram_status_sample.labels["alert_event_type"] == "shadow_day_failed"
    assert telegram_status_sample.labels["config_source"] == "cli"
    assert telegram_status_sample.labels["error_present"] == "true"
    bootstrap_status_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_execution_runtime_bootstrap_status"
    )
    assert bootstrap_status_sample.labels["bootstrap_status"] == "ready"
    assert bootstrap_status_sample.labels["bootstrap_source"] == "live_websocket_config"
    assert bootstrap_status_sample.labels["gatekeeper_audit_source"] == "cli"
    assert bootstrap_status_sample.labels["reconciliation_executed"] == "true"
    bootstrap_divergence_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_execution_runtime_bootstrap_divergence_count"
    )
    assert bootstrap_divergence_sample.value == 0.0
