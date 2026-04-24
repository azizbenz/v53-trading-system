from __future__ import annotations

from monitoring.contracts import (
    DiskUsageSample,
    ObservabilityExport,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.shadow_vps_service_monitoring import (
    build_shadow_vps_service_monitoring_payload,
    build_shadow_vps_service_observability_export,
)
from interface_contracts import (
    BinanceCredentialValidationStatus,
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    DashboardSecretEnvironment,
    DashboardSecretKind,
    DashboardSecretTransferManifest,
    binance_credential_entry_from_manifest,
)
from protocols.shadow_vps_service import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
    ShadowVpsServiceStatus,
)


def _build_rich_monitoring_state() -> ShadowVpsServiceState:
    return ShadowVpsServiceState(
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
        last_runtime_evidence_bundle_ref=(
            "E:/shadow/runtime_evidence/2026-04-09.shadow_vps_runtime_evidence.json"
        ),
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
        last_execution_runtime_bootstrap_remote_state_snapshot_captured=True,
        last_execution_runtime_bootstrap_remote_open_order_count=1,
        last_execution_runtime_bootstrap_remote_position_asset_count=1,
        last_execution_runtime_bootstrap_remote_open_orders_present=True,
        last_execution_runtime_bootstrap_remote_positions_present=True,
        last_vps_recovery_readiness_report_ref="E:/shadow/vps_recovery_readiness.report.json",
        last_vps_recovery_status="blocked",
        last_vps_recovery_eligible_to_trade=False,
        last_vps_warmup_summary_ref="E:/shadow/vps_warmup_run.summary.json",
        last_vps_warmup_final_state="blocked",
        last_vps_warmup_eligible_to_trade=False,
        last_live_complete_summary_ref="E:/shadow/live_complete_run.summary.json",
        last_live_complete_status="blocked",
        last_live_complete_verdict="blocked",
        last_live_complete_run_state="blocked",
        last_live_complete_blocking_reason_count=3,
        last_live_complete_operator_report_ref="E:/shadow/live_complete_operator_audit_report.json",
        last_live_complete_operator_report_status="blocked",
        last_live_complete_operator_report_recommendation="investigate_live_complete_blockers",
        active_ml_artifact=DashboardArtifactTransferManifest(
            artifact_hash="a" * 64,
            artifact_kind=DashboardArtifactKind.ML_MODEL_ARTIFACT,
            artifact_id="ml-active",
            source_ref="E:/shadow/active_ml_artifact.json",
        ),
        active_regime_detector_artifact=DashboardArtifactTransferManifest(
            artifact_hash="b" * 64,
            artifact_kind=DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
            artifact_id="regime-active",
            source_ref="E:/shadow/active_regime_detector_artifact.json",
        ),
        active_regime_detector_shadow_audit_bundle_ref=(
            "E:/shadow/regime_detector_shadow_audit_bundle.json"
        ),
        binance_credential_inventory=(
            binance_credential_entry_from_manifest(
                DashboardSecretTransferManifest(
                    secret_hash="c" * 64,
                    secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
                    profile_id="binance-live-001",
                    environment=DashboardSecretEnvironment.LIVE,
                    sealed_ref="secrets/binance-live-001.sealed.json",
                    review_state="approved",
                    validation_status="validated",
                ),
                active=True,
                validation_status=BinanceCredentialValidationStatus.VALIDATED,
            ),
        ),
        active_binance_credential_profile_id="binance-live-001",
        active_binance_credential_environment="live",
        binance_credential_validation_status="validated",
        binance_credential_last_auth_check_ms=1_800_000_000_000,
        dashboard_control_halted=True,
        dashboard_control_target_profile="light",
        dashboard_control_target_deployment_state="rollback",
        dashboard_control_suspended_pairs=("BTCUSDT",),
        dashboard_control_suspended_engines=("engine_c",),
        dashboard_control_last_request_id="req-queue-1",
        dashboard_control_last_command_kind="set_halted",
        dashboard_control_last_result_status="completed",
        last_execution_runtime_projection_ref="E:/shadow/local_lab_execution_runtime_projection.json",
        last_execution_runtime_projection_source="cli",
        last_regime_lite_assessment_ref="E:/shadow/regime_lite_assessment.json",
        last_regime_lite_assessment_source="live_websocket_config",
        last_regime_lite_safing_recommendation_ref=(
            "E:/shadow/regime_lite_safing_recommendation.json"
        ),
        last_regime_lite_safing_recommendation_source="cli",
        last_info_stress_assessment_ref="E:/shadow/info_stress_assessment.json",
        last_info_stress_assessment_source="cli",
        last_export_dir_ref="E:/shadow/exports/2026-04-09",
    )


def _build_rich_monitoring_campaign_summary() -> ShadowVpsCampaignSummary:
    return ShadowVpsCampaignSummary(
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
        execution_runtime_bootstrap_reconciliation_boot_detail=(
            "boot reconciliation aligned local and remote state"
        ),
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


def _build_rich_monitoring_runtime_bundle() -> ShadowVpsRuntimeEvidenceBundle:
    return ShadowVpsRuntimeEvidenceBundle(
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
        execution_runtime_bootstrap_reconciliation_boot_detail=(
            "boot reconciliation aligned local and remote state"
        ),
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


def _build_rich_monitoring_process() -> ProcessMetricsSample:
    return ProcessMetricsSample(
        pid=4321,
        cpu_pct=6.5,
        ram_pct=12.5,
        rss_mb=256.0,
        thread_count=11,
        sampling_mode="test_mode",
    )


def _build_rich_monitoring_payload() -> ShadowVpsServiceMonitoringPayload:
    return build_shadow_vps_service_monitoring_payload(
        timestamp_ms=1_800_000_002_500,
        state=_build_rich_monitoring_state(),
        process=_build_rich_monitoring_process(),
        disk=DiskUsageSample(
            path="E:/shadow",
            total_gb=100.0,
            free_gb=40.0,
            used_pct=60.0,
            sampling_mode="test_mode",
        ),
        campaign_summary=_build_rich_monitoring_campaign_summary(),
        runtime_evidence_bundle=_build_rich_monitoring_runtime_bundle(),
        state_path="E:/shadow/shadow_vps_service.state.json",
        events_path="E:/shadow/shadow_vps_service.events.jsonl",
        recent_events_summary_ref="E:/shadow/shadow_vps_service_recent_events.json",
        latest_event_type="recovery_gate_blocked",
        latest_error="network timeout",
        parse_error_count=2,
        node_exporter_textfile_ref="E:/node-textfile/v53_shadow_vps_service.prom",
    )


def _assert_projected_payload_fields(
    payload: ShadowVpsServiceMonitoringPayload,
) -> None:
    assert payload.status == "critical"
    assert payload.service_status == "running"
    assert payload.heartbeat_age_ms == 2_500
    assert payload.acquisition_mode == "dated_export"
    assert payload.runtime_data_source == "recorded_replay"
    assert payload.process.pid == 4321
    assert payload.process.thread_count == 11
    assert payload.disk.used_pct == 60.0
    assert payload.state_path.endswith("shadow_vps_service.state.json")
    assert payload.events_path.endswith("shadow_vps_service.events.jsonl")
    assert payload.recent_events_summary_ref.endswith("shadow_vps_service_recent_events.json")
    assert payload.execution_telemetry_ref.endswith("shadow_vps_service_execution_telemetry.json")
    assert payload.execution_telemetry_status == "written"
    assert payload.telegram_alert_delivery_status == "sent"
    assert payload.telegram_alert_delivery_event_type == "shadow_day_completed"
    assert payload.telegram_alert_delivery_error == ""
    assert payload.telegram_alert_config_ref.endswith("telegram_alert_config.json")
    assert payload.telegram_alert_config_source == "live_websocket_config"
    assert payload.telegram_alert_key_ref.endswith("telegram_alert.key")
    assert payload.telegram_alert_key_source == "cli"
    assert payload.execution_runtime_bootstrap_ref.endswith("execution_runtime_bootstrap.summary.json")
    assert payload.execution_runtime_bootstrap_status == "ready"
    assert payload.execution_runtime_bootstrap_source == "live_websocket_config"
    assert payload.execution_runtime_gatekeeper_audit_ref.endswith("audit.jsonl")
    assert payload.execution_runtime_gatekeeper_audit_source == "cli"
    assert payload.execution_runtime_bootstrap_reconciliation_boot_executed is True
    assert payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked is False
    assert payload.execution_runtime_bootstrap_remote_state_snapshot_captured is True
    assert payload.execution_runtime_bootstrap_remote_open_order_count == 1
    assert payload.execution_runtime_bootstrap_remote_position_asset_count == 1
    assert payload.vps_recovery_status == "blocked"
    assert payload.vps_warmup_final_state == "blocked"
    assert payload.last_live_complete_status == "blocked"
    assert payload.last_live_complete_verdict == "blocked"
    assert payload.last_live_complete_run_state == "blocked"
    assert payload.last_live_complete_operator_report_status == "blocked"
    assert payload.latest_event_type == "recovery_gate_blocked"
    assert payload.latest_error == "network timeout"
    assert payload.parse_error_count == 2
    assert payload.active_ml_artifact_hash == "a" * 64
    assert payload.active_ml_artifact_id == "ml-active"
    assert payload.active_regime_detector_artifact_hash == "b" * 64
    assert payload.active_regime_detector_artifact_id == "regime-active"
    assert payload.binance_credential_inventory_count == 1
    assert payload.active_binance_credential_profile_id == "binance-live-001"
    assert payload.active_binance_credential_environment == "live"
    assert payload.binance_credential_validation_status == "validated"
    assert payload.dashboard_control_halted is True
    assert payload.dashboard_control_target_profile == "light"
    assert payload.dashboard_control_target_deployment_state == "rollback"
    assert payload.dashboard_control_suspended_pair_count == 1
    assert payload.dashboard_control_suspended_engine_count == 1
    assert payload.dashboard_control_suspended_pairs == ("BTCUSDT",)
    assert payload.dashboard_control_suspended_engines == ("engine_c",)
    assert payload.dashboard_control_last_request_id == "req-queue-1"
    assert payload.dashboard_control_last_command_kind == "set_halted"
    assert payload.dashboard_control_last_result_status == "completed"
    assert payload.execution_runtime_bootstrap_reconciliation_boot_divergence_count == 0


def _assert_projected_payload_detail(
    payload: ShadowVpsServiceMonitoringPayload,
) -> None:
    assert payload.execution_runtime_projection_ref.endswith("local_lab_execution_runtime_projection.json")
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
    assert payload.node_exporter_textfile_ref.endswith("v53_shadow_vps_service.prom")
    assert (
        payload.active_regime_detector_shadow_audit_bundle_ref.endswith(
            "regime_detector_shadow_audit_bundle.json"
        )
    )
    assert "regime_lite=halt_recommended@extreme@live_websocket_config/cli" in payload.detail
    assert "info_stress=assessment_only@extreme@cli" in payload.detail
    assert "telegram=sent@shadow_day_completed@live_websocket_config" in payload.detail
    assert "exec_bootstrap=ready@live_websocket_config@cli/div=0" in payload.detail
    assert "remote_orders=1/remote_positions=1" in payload.detail
    assert "recovery=blocked/warmup=blocked" in payload.detail
    assert "dashboard_halted=True/target=light:rollback/pair_susp=1/engine_susp=1" in payload.detail
    assert "live_complete=blocked@blocked@blocked/report=blocked" in payload.detail
    assert "log=recovery_gate_blocked/log_errs=2/latest_error=network timeout" in payload.detail
    assert "artifacts=ml:aaaaaaaaaaaa/regime:bbbbbbbbbbbb" in payload.detail
    assert "binance_profile=binance-live-001@live@validated" in payload.detail


def _build_observability_payload() -> ShadowVpsServiceMonitoringPayload:
    return build_shadow_vps_service_monitoring_payload(
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


def _assert_observability_export(export: ObservabilityExport) -> None:
    assert export.correlation_id == "shadow-vps-service"
    assert export.text_payload.startswith("# V5.3 Shadow VPS service observability export")
    sample_names = {sample.name for sample in export.samples}
    assert "v53_shadow_vps_service_status" in sample_names
    assert "v53_shadow_vps_dashboard_control_halted" in sample_names
    assert "v53_shadow_vps_dashboard_control_suspended_pair_count" in sample_names
    assert "v53_shadow_vps_dashboard_control_suspended_engine_count" in sample_names
    assert "v53_shadow_vps_recovery_status" in sample_names
    assert "v53_shadow_vps_recovery_eligible_to_trade" in sample_names
    assert "v53_shadow_vps_warmup_state" in sample_names
    assert "v53_shadow_vps_warmup_eligible_to_trade" in sample_names
    assert "v53_shadow_vps_live_complete_summary" in sample_names
    assert "v53_shadow_vps_live_complete_blocking_reason_count" in sample_names
    assert "v53_shadow_vps_live_complete_operator_report" in sample_names
    assert "v53_shadow_vps_recent_log_summary" in sample_names
    assert "v53_shadow_vps_recent_log_parse_error_count" in sample_names
    assert "v53_shadow_vps_active_ml_artifact" in sample_names
    assert "v53_shadow_vps_active_regime_detector_artifact" in sample_names
    assert "v53_shadow_vps_active_regime_detector_shadow_audit_bundle_present" in sample_names
    assert "v53_shadow_vps_active_binance_credential_profile" in sample_names
    assert "v53_shadow_vps_binance_credential_inventory_count" in sample_names
    assert "v53_shadow_vps_process_cpu_pct" in sample_names
    assert "v53_shadow_vps_process_rss_mb" in sample_names
    assert "v53_shadow_vps_disk_used_pct" in sample_names
    assert "v53_shadow_vps_execution_telemetry_ready" in sample_names
    assert "v53_shadow_vps_telegram_alert_delivery_status" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_status" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_divergence_count" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_trading_blocked" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_remote_state_snapshot_captured" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_remote_open_order_count" in sample_names
    assert "v53_shadow_vps_execution_runtime_bootstrap_remote_position_asset_count" in sample_names
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
    recovery_status_sample = next(
        sample for sample in export.samples if sample.name == "v53_shadow_vps_recovery_status"
    )
    assert recovery_status_sample.labels["recovery_status"] == "not_configured"
    assert recovery_status_sample.labels["eligible_to_trade"] == "false"
    warmup_status_sample = next(
        sample for sample in export.samples if sample.name == "v53_shadow_vps_warmup_state"
    )
    assert warmup_status_sample.labels["warmup_final_state"] == "not_configured"
    live_complete_sample = next(
        sample for sample in export.samples if sample.name == "v53_shadow_vps_live_complete_summary"
    )
    assert live_complete_sample.labels["status"] == "not_configured"
    operator_report_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_live_complete_operator_report"
    )
    assert operator_report_sample.labels["status"] == "not_available"
    active_ml_sample = next(
        sample for sample in export.samples if sample.name == "v53_shadow_vps_active_ml_artifact"
    )
    assert active_ml_sample.labels["artifact_hash"] == "none"
    active_regime_sample = next(
        sample
        for sample in export.samples
        if sample.name == "v53_shadow_vps_active_regime_detector_artifact"
    )
    assert active_regime_sample.labels["artifact_id"] == "none"


def test_shadow_vps_service_monitoring_payload_projects_state_and_process_metrics() -> None:
    payload = _build_rich_monitoring_payload()
    _assert_projected_payload_fields(payload)
    _assert_projected_payload_detail(payload)


def test_shadow_vps_service_observability_export_emits_process_and_service_metrics() -> None:
    export = build_shadow_vps_service_observability_export(_build_observability_payload())
    _assert_observability_export(export)
