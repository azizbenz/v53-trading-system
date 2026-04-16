"""Support helpers for Build-10 structured observability export."""

from __future__ import annotations

from monitoring.contracts import MetricSample, ObservabilityExport, TechnicalDashboardPayload


def _sample(
    name: str,
    *,
    kind: str,
    value: float,
    unit: str = "",
    labels: dict[str, str] | None = None,
) -> MetricSample:
    return MetricSample(name=name, kind=kind, value=value, unit=unit, labels=labels or {})


def _labels(payload: TechnicalDashboardPayload) -> dict[str, str]:
    return {
        "correlation_id": payload.correlation_id,
        "profile": payload.profile.value,
        "runtime_mode": payload.runtime_mode.value,
    }


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    joined = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    return f"{{{joined}}}"


def _runtime_hook_bridge_samples(payload: TechnicalDashboardPayload) -> tuple[MetricSample, ...]:
    base_labels = _labels(payload)
    samples: list[MetricSample] = []
    for bridge in payload.runtime_hook_bridges:
        hook_labels = {
            **base_labels,
            "hook_id": bridge.hook_id.value,
            "status": bridge.status,
            "selection_status": bridge.selection_status,
            "failure_mode": bridge.failure_mode or "none",
            "error_stage": bridge.error_stage or "none",
        }
        samples.extend(
            (
                _sample("v53_runtime_hook_bridge_status", kind="state", value=1.0, labels=hook_labels),
                _sample("v53_runtime_hook_bridge_configured", kind="state", value=1.0 if bridge.configured else 0.0, labels={**base_labels, "hook_id": bridge.hook_id.value}),
                _sample("v53_runtime_hook_bridge_binding_present", kind="state", value=1.0 if bridge.binding_present else 0.0, labels={**base_labels, "hook_id": bridge.hook_id.value}),
                _sample("v53_runtime_hook_bridge_loaded", kind="state", value=1.0 if bridge.loaded else 0.0, labels={**base_labels, "hook_id": bridge.hook_id.value}),
                _sample("v53_runtime_hook_bridge_artifact_count", kind="gauge", value=float(bridge.artifact_count), unit="count", labels={**base_labels, "hook_id": bridge.hook_id.value}),
            )
        )
    return tuple(samples)


def _build_system_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_system_headline_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.headline_status}),
        _sample("v53_system_active_alert_count", kind="gauge", value=float(payload.alerts.active_alert_count), unit="count", labels=base_labels),
        _sample("v53_system_active_module_count", kind="gauge", value=float(len(payload.system.active_modules)), unit="count", labels=base_labels),
        _sample("v53_system_active_engine_count", kind="gauge", value=float(len(payload.system.active_engines)), unit="count", labels=base_labels),
        _sample("v53_system_build9x_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.build9x_status}),
        _sample("v53_system_shadow_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.shadow_status}),
        _sample("v53_system_micro_live_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.micro_live_status}),
        _sample("v53_system_live_light_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.live_light_status}),
        _sample("v53_system_build14_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.build14_status}),
        _sample("v53_system_replay_status", kind="state", value=1.0, labels={**base_labels, "status": payload.system.replay_import_status}),
    )


def _build_portfolio_and_meta_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_portfolio_capital_deployed_usdt", kind="gauge", value=payload.portfolio.capital_deployed_usdt, unit="usdt", labels=base_labels),
        _sample("v53_portfolio_ce_net", kind="gauge", value=payload.portfolio.ce_net, unit="ratio", labels=base_labels),
        _sample("v53_portfolio_pnl_net_usdt", kind="gauge", value=payload.portfolio.pnl_net_usdt, unit="usdt", labels=base_labels),
        _sample("v53_risk_beta_utilization", kind="gauge", value=payload.portfolio.beta_utilization, unit="ratio", labels=base_labels),
        _sample("v53_risk_breach_count", kind="gauge", value=float(len(payload.portfolio.breaches)), unit="count", labels=base_labels),
        _sample("v53_meta_dtr_coverage_ratio", kind="gauge", value=payload.build9_meta.dtr_coverage, unit="ratio", labels=base_labels),
        _sample("v53_meta_cra_sterilization_ratio", kind="gauge", value=payload.build9_meta.cra_sterilization_rate, unit="ratio", labels=base_labels),
        _sample("v53_meta_cra_alert_count", kind="gauge", value=float(payload.build9_meta.cra_alert_count), unit="count", labels=base_labels),
        _sample("v53_meta_break_even_drift_scope_count", kind="gauge", value=float(len(payload.build9_meta.break_even_drift_scopes)), unit="count", labels=base_labels),
        _sample("v53_meta_edge_credible_count", kind="gauge", value=float(payload.build9_meta.edge_credible_count), unit="count", labels=base_labels),
        _sample("v53_meta_edge_degraded_count", kind="gauge", value=float(payload.build9_meta.edge_degraded_count), unit="count", labels=base_labels),
        _sample("v53_meta_edge_surveillance_count", kind="gauge", value=float(payload.build9_meta.edge_surveillance_count), unit="count", labels=base_labels),
    )


def _build_build9x_and_shadow_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_build9x_status", kind="state", value=1.0, labels={**base_labels, "status": payload.build9x.status}),
        _sample("v53_build9x_recent_diagnostics", kind="gauge", value=float(payload.build9x.diagnostics_count), unit="count", labels=base_labels),
        _sample("v53_build9x_open_hypotheses", kind="gauge", value=float(payload.build9x.open_hypotheses), unit="count", labels=base_labels),
        _sample("v53_build9x_total_hypotheses", kind="gauge", value=float(payload.build9x.total_hypotheses), unit="count", labels=base_labels),
        _sample("v53_build9x_near_miss_count", kind="gauge", value=float(payload.build9x.near_miss_count), unit="count", labels=base_labels),
        _sample("v53_build9x_replay_candidate_count", kind="gauge", value=float(payload.build9x.replay_candidate_count), unit="count", labels=base_labels),
        _sample("v53_build9x_memory_record_count", kind="gauge", value=float(payload.build9x.memory_record_count), unit="count", labels=base_labels),
        _sample("v53_build9x_review_export_ready", kind="state", value=1.0 if payload.build9x.review_export_ready else 0.0, labels=base_labels),
        _sample("v53_build9x_learning_queue_depth", kind="gauge", value=float(payload.build9x.learning_queue_depth), unit="count", labels=base_labels),
        _sample("v53_build9x_learning_queue_oldest_age_ms", kind="gauge", value=float(payload.build9x.learning_queue_oldest_age_ms), unit="ms", labels=base_labels),
        _sample("v53_build9x_learning_worker_cpu_pct", kind="gauge", value=payload.build9x.learning_worker_cpu_pct, unit="pct", labels=base_labels),
        _sample("v53_build9x_learning_worker_rss_mb", kind="gauge", value=payload.build9x.learning_worker_rss_mb, unit="mb", labels=base_labels),
        _sample("v53_build9x_learning_write_latency_ms", kind="gauge", value=payload.build9x.learning_write_latency_ms, unit="ms", labels=base_labels),
        _sample("v53_build9x_learning_export_failures_total", kind="counter", value=float(payload.build9x.learning_export_failures_total), unit="count", labels=base_labels),
        _sample("v53_build9x_learning_log_loss_total", kind="counter", value=float(payload.build9x.learning_log_loss_total), unit="count", labels=base_labels),
        _sample("v53_build9x_learning_unprocessed_items_count", kind="gauge", value=float(payload.build9x.learning_unprocessed_items_count), unit="count", labels=base_labels),
        _sample("v53_build9x_learning_backlog_state", kind="state", value=1.0, labels={**base_labels, "state": payload.build9x.learning_backlog_state}),
        _sample("v53_build9x_learning_capture_mode", kind="state", value=1.0, labels={**base_labels, "mode": payload.build9x.learning_capture_mode}),
        _sample("v53_build9x_learning_backpressure_active", kind="state", value=1.0 if payload.build9x.learning_backpressure_active else 0.0, labels=base_labels),
        _sample("v53_build9x_learning_observability_reduced", kind="state", value=1.0 if payload.build9x.learning_observability_reduced else 0.0, labels=base_labels),
        _sample("v53_build9x_review_blocked_due_to_incomplete_data", kind="state", value=1.0 if payload.build9x.review_blocked_due_to_incomplete_data else 0.0, labels=base_labels),
        _sample("v53_build9x_promotion_blocked_due_to_incomplete_data", kind="state", value=1.0 if payload.build9x.promotion_blocked_due_to_incomplete_data else 0.0, labels=base_labels),
        _sample("v53_shadow_run_state", kind="state", value=1.0, labels={**base_labels, "state": payload.shadow.run_state}),
        _sample("v53_shadow_verdict", kind="state", value=1.0, labels={**base_labels, "verdict": payload.shadow.verdict}),
        _sample("v53_shadow_divergent_comparison_count", kind="gauge", value=float(payload.shadow.divergent_comparison_count), unit="count", labels=base_labels),
        _sample("v53_shadow_blocking_comparison_count", kind="gauge", value=float(payload.shadow.blocking_comparison_count), unit="count", labels=base_labels),
        _sample("v53_shadow_blocking_reason_count", kind="gauge", value=float(len(payload.shadow.blocking_reasons)), unit="count", labels=base_labels),
        _sample("v53_shadow_regime_lite_safing_status", kind="state", value=1.0, labels={**base_labels, "status": payload.shadow.regime_lite_safing.status, "severity": payload.shadow.regime_lite_safing.severity, "recommended_action": payload.shadow.regime_lite_safing.recommended_operator_action or "none", "request_action": payload.shadow.regime_lite_safing.operator_safing_request_action or "none"}),
        _sample("v53_shadow_manual_review_required", kind="state", value=1.0 if payload.shadow.manual_review_required else 0.0, labels=base_labels),
        _sample("v53_shadow_review_export_ready", kind="state", value=1.0 if payload.shadow.review_export_ready else 0.0, labels=base_labels),
    )


def _build_rollout_and_bridge_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_micro_live_run_state", kind="state", value=1.0, labels={**base_labels, "state": payload.micro_live.run_state}),
        _sample("v53_micro_live_verdict", kind="state", value=1.0, labels={**base_labels, "verdict": payload.micro_live.verdict}),
        _sample("v53_micro_live_allowed_to_probe", kind="state", value=1.0 if payload.micro_live.allowed_to_probe else 0.0, labels=base_labels),
        _sample("v53_micro_live_planned_pair_count", kind="gauge", value=float(len(payload.micro_live.planned_pairs)), unit="count", labels=base_labels),
        _sample("v53_micro_live_planned_engine_count", kind="gauge", value=float(len(payload.micro_live.planned_engines)), unit="count", labels=base_labels),
        _sample("v53_micro_live_approved_total_notional_usdt", kind="gauge", value=payload.micro_live.approved_total_notional_usdt, unit="usdt", labels=base_labels),
        _sample("v53_micro_live_blocking_reason_count", kind="gauge", value=float(len(payload.micro_live.blocking_reasons)), unit="count", labels=base_labels),
        _sample("v53_micro_live_observability_ready", kind="state", value=1.0 if payload.micro_live.observability_ready else 0.0, labels=base_labels),
        _sample("v53_micro_live_halt_ready", kind="state", value=1.0 if payload.micro_live.halt_ready else 0.0, labels=base_labels),
        _sample("v53_micro_live_onboarding_ready", kind="state", value=1.0 if payload.micro_live.onboarding_ready else 0.0, labels=base_labels),
        _sample("v53_live_light_run_state", kind="state", value=1.0, labels={**base_labels, "state": payload.live_light.run_state}),
        _sample("v53_live_light_verdict", kind="state", value=1.0, labels={**base_labels, "verdict": payload.live_light.verdict}),
        _sample("v53_live_light_allowed_to_execute_small", kind="state", value=1.0 if payload.live_light.allowed_to_execute_small else 0.0, labels=base_labels),
        _sample("v53_live_light_planned_pair_count", kind="gauge", value=float(len(payload.live_light.planned_pairs)), unit="count", labels=base_labels),
        _sample("v53_live_light_planned_engine_count", kind="gauge", value=float(len(payload.live_light.planned_engines)), unit="count", labels=base_labels),
        _sample("v53_live_light_approved_total_notional_usdt", kind="gauge", value=payload.live_light.approved_total_notional_usdt, unit="usdt", labels=base_labels),
        _sample("v53_live_light_blocking_reason_count", kind="gauge", value=float(len(payload.live_light.blocking_reasons)), unit="count", labels=base_labels),
        _sample("v53_live_light_observability_ready", kind="state", value=1.0 if payload.live_light.observability_ready else 0.0, labels=base_labels),
        _sample("v53_live_light_halt_ready", kind="state", value=1.0 if payload.live_light.halt_ready else 0.0, labels=base_labels),
        _sample("v53_live_light_execution_ready", kind="state", value=1.0 if payload.live_light.execution_ready else 0.0, labels=base_labels),
        _sample("v53_live_light_broker_ready", kind="state", value=1.0 if payload.live_light.broker_ready else 0.0, labels=base_labels),
        _sample("v53_live_light_exchange_ready", kind="state", value=1.0 if payload.live_light.exchange_ready else 0.0, labels=base_labels),
        _sample("v53_execution_no_trade_bridge_status", kind="state", value=1.0, labels={**base_labels, "status": payload.execution_no_trade_bridge.status, "selection_status": payload.execution_no_trade_bridge.selection_status, "failure_mode": payload.execution_no_trade_bridge.failure_mode or "none", "error_stage": payload.execution_no_trade_bridge.error_stage or "none"}),
        _sample("v53_execution_no_trade_bridge_configured", kind="state", value=1.0 if payload.execution_no_trade_bridge.configured else 0.0, labels=base_labels),
        _sample("v53_execution_no_trade_bridge_binding_present", kind="state", value=1.0 if payload.execution_no_trade_bridge.binding_present else 0.0, labels=base_labels),
        _sample("v53_execution_no_trade_bridge_loaded", kind="state", value=1.0 if payload.execution_no_trade_bridge.loaded else 0.0, labels=base_labels),
        _sample("v53_execution_no_trade_bridge_artifact_count", kind="gauge", value=float(payload.execution_no_trade_bridge.artifact_count), unit="count", labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_status", kind="state", value=1.0, labels={**base_labels, "status": payload.execution_runtime_projection_bridge.status, "projection_status": payload.execution_runtime_projection_bridge.projection_status or "none"}),
        _sample("v53_execution_runtime_projection_bridge_configured", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.configured else 0.0, labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_found", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.projection_found else 0.0, labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_loaded", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.projection_loaded else 0.0, labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_ready_consumer_count", kind="gauge", value=float(payload.execution_runtime_projection_bridge.ready_consumer_count), unit="count", labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_partial_consumer_count", kind="gauge", value=float(payload.execution_runtime_projection_bridge.partial_consumer_count), unit="count", labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_blocked_consumer_count", kind="gauge", value=float(payload.execution_runtime_projection_bridge.blocked_consumer_count), unit="count", labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_rate_limit_model_loaded", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.rate_limit_model_loaded else 0.0, labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_spread_guard_model_loaded", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.spread_guard_model_loaded else 0.0, labels=base_labels),
        _sample("v53_execution_runtime_projection_bridge_slippage_model_loaded", kind="state", value=1.0 if payload.execution_runtime_projection_bridge.slippage_model_loaded else 0.0, labels=base_labels),
        *_runtime_hook_bridge_samples(payload),
    )


def _build_build14_replay_alert_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_build14_status", kind="state", value=1.0, labels={**base_labels, "status": payload.build14.status}),
        _sample("v53_build14_hard_state", kind="state", value=1.0, labels={**base_labels, "hard_state": payload.build14.hard_state}),
        _sample("v53_build14_live_promotion_eligible", kind="state", value=1.0 if payload.build14.live_promotion_eligible else 0.0, labels=base_labels),
        _sample("v53_build14_influence_mode", kind="state", value=1.0, labels={**base_labels, "mode": payload.build14.influence_mode}),
        _sample("v53_build14_action", kind="state", value=1.0, labels={**base_labels, "action": payload.build14.action}),
        _sample("v53_build14_severity", kind="state", value=1.0, labels={**base_labels, "severity": payload.build14.severity}),
        _sample("v53_build14_market_toxicity_value", kind="gauge", value=payload.build14.market_toxicity_value, unit="score", labels={**base_labels, "status": payload.build14.market_toxicity_status}),
        _sample("v53_build14_execution_fragility_value", kind="gauge", value=payload.build14.execution_fragility_value, unit="score", labels={**base_labels, "status": payload.build14.execution_fragility_status}),
        _sample("v53_build14_confidence_penalty_weight", kind="gauge", value=payload.build14.confidence_penalty_weight, unit="ratio", labels=base_labels),
        _sample("v53_build14_recommended_budget_factor", kind="gauge", value=payload.build14.recommended_budget_factor, unit="ratio", labels=base_labels),
        _sample("v53_build14_requires_manual_review", kind="state", value=1.0 if payload.build14.requires_manual_review else 0.0, labels=base_labels),
        _sample("v53_build14_reason_code_count", kind="gauge", value=float(len(payload.build14.reason_codes)), unit="count", labels=base_labels),
        _sample("v53_replay_artifact_present", kind="state", value=1.0 if payload.replay_import.artifact_id != "none" else 0.0, labels=base_labels),
        _sample("v53_replay_validation_started", kind="state", value=1.0 if payload.replay_import.validation_status != "not_run" else 0.0, labels=base_labels),
        _sample("v53_replay_validation_accepted", kind="state", value=1.0 if payload.replay_import.validation_status == "accepted" else 0.0, labels=base_labels),
        _sample("v53_replay_compatibility_status", kind="state", value=1.0, labels={**base_labels, "status": payload.replay_import.compatibility_status}),
        _sample("v53_replay_compatibility_reason_count", kind="gauge", value=float(len(payload.replay_import.compatibility_reasons)), unit="count", labels=base_labels),
        _sample("v53_replay_feature_lineage_required", kind="state", value=1.0 if payload.replay_import.feature_lineage_required else 0.0, labels=base_labels),
        _sample("v53_replay_feature_lineage_present", kind="state", value=1.0 if payload.replay_import.feature_lineage_present else 0.0, labels=base_labels),
        _sample("v53_replay_feature_lineage_status", kind="state", value=1.0, labels={**base_labels, "status": payload.replay_import.feature_lineage_status}),
        _sample("v53_replay_feature_lineage_reason_count", kind="gauge", value=float(len(payload.replay_import.feature_lineage_reasons)), unit="count", labels=base_labels),
        _sample("v53_replay_transform_whitelist_required", kind="state", value=1.0 if payload.replay_import.transform_whitelist_required else 0.0, labels=base_labels),
        _sample("v53_replay_transform_whitelist_present", kind="state", value=1.0 if payload.replay_import.transform_whitelist_present else 0.0, labels=base_labels),
        _sample("v53_replay_transform_whitelist_status", kind="state", value=1.0, labels={**base_labels, "status": payload.replay_import.transform_whitelist_status}),
        _sample("v53_replay_transform_whitelist_reason_count", kind="gauge", value=float(len(payload.replay_import.transform_whitelist_reasons)), unit="count", labels=base_labels),
        _sample("v53_replay_signature_present", kind="state", value=1.0 if payload.replay_import.signature_check_status != "not_provided" else 0.0, labels=base_labels),
        _sample("v53_replay_signature_check_status", kind="state", value=1.0, labels={**base_labels, "status": payload.replay_import.signature_check_status, "trusted_key_status": payload.replay_import.trusted_key_status or "n/a"}),
        _sample("v53_replay_signature_reason_count", kind="gauge", value=float(len(payload.replay_import.signature_check_reasons)), unit="count", labels=base_labels),
        _sample("v53_replay_conflict_resolution_mode", kind="state", value=1.0, labels={**base_labels, "resolution_mode": payload.replay_import.conflict_resolution_mode or "n/a", "hard_veto_action": payload.replay_import.conflict_hard_veto_action or "n/a"}),
        _sample("v53_replay_conflict_additive_soft_boosts_allowed", kind="state", value=1.0 if payload.replay_import.conflict_additive_soft_boosts_allowed else 0.0, labels=base_labels),
        _sample("v53_replay_conflict_additive_soft_reduces_allowed", kind="state", value=1.0 if payload.replay_import.conflict_additive_soft_reduces_allowed else 0.0, labels=base_labels),
        _sample("v53_replay_registry_atomicity_mode", kind="state", value=1.0, labels={**base_labels, "atomicity_mode": payload.replay_import.registry_atomicity_mode or "n/a", "concurrency_model": payload.replay_import.registry_concurrency_model or "n/a"}),
        _sample("v53_replay_registry_atomic_replace_required", kind="state", value=1.0 if payload.replay_import.registry_publish_requires_atomic_replace else 0.0, labels=base_labels),
        _sample("v53_replay_registry_fsync_required", kind="state", value=1.0 if payload.replay_import.registry_publish_requires_fsync else 0.0, labels=base_labels),
        _sample("v53_replay_registry_last_known_good_enabled", kind="state", value=1.0 if payload.replay_import.registry_rollback_to_last_known_good else 0.0, labels=base_labels),
        _sample("v53_replay_rejection_reason_count", kind="gauge", value=float(len(payload.replay_import.rejection_reasons)), unit="count", labels=base_labels),
        _sample("v53_alert_active_count", kind="gauge", value=float(payload.alerts.active_alert_count), unit="count", labels=base_labels),
        _sample("v53_alert_queue_backlog", kind="gauge", value=float(payload.alerts.queue_backlog), unit="count", labels=base_labels),
        _sample("v53_alert_queue_backlog_high_water_mark", kind="gauge", value=float(payload.alerts.backlog_high_water_mark), unit="count", labels=base_labels),
        _sample("v53_alert_queue_drop_rate_pct", kind="gauge", value=payload.alerts.drop_rate_pct, unit="pct", labels=base_labels),
        _sample("v53_alert_stale_pair_count", kind="gauge", value=float(payload.alerts.stale_pair_count), unit="count", labels=base_labels),
        _sample("v53_alert_stale_spike_count", kind="gauge", value=float(payload.alerts.stale_spike_count), unit="count", labels=base_labels),
        _sample("v53_alert_recovery_retry_count", kind="gauge", value=float(payload.alerts.recovery_retry_count), unit="count", labels=base_labels),
        _sample("v53_alert_dtr_loss_count", kind="gauge", value=float(payload.alerts.dtr_loss_count), unit="count", labels=base_labels),
        _sample("v53_alert_log_loss_count", kind="gauge", value=float(payload.alerts.log_loss_count), unit="count", labels=base_labels),
        _sample("v53_alert_backlog_stale_status", kind="state", value=1.0, labels={**base_labels, "status": payload.alerts.backlog_stale_status}),
        _sample("v53_alert_loss_drift_status", kind="state", value=1.0, labels={**base_labels, "status": payload.alerts.loss_drift_status}),
        _sample("v53_alert_kill_switch_active", kind="state", value=1.0 if payload.alerts.kill_switch_active else 0.0, labels=base_labels),
        _sample("v53_alert_operator_event_count", kind="gauge", value=float(payload.alerts.operator_runtime.event_count), unit="count", labels=base_labels),
        _sample("v53_alert_operator_pending_notification_count", kind="gauge", value=float(payload.alerts.operator_runtime.pending_notification_count), unit="count", labels=base_labels),
        _sample("v53_alert_operator_acknowledged_notification_count", kind="gauge", value=float(payload.alerts.operator_runtime.acknowledged_notification_count), unit="count", labels=base_labels),
        _sample("v53_alert_operator_rejection_event_count", kind="gauge", value=float(payload.alerts.operator_runtime.rejection_event_count), unit="count", labels=base_labels),
        _sample("v53_execution_expected_cost_bps", kind="gauge", value=payload.infra.expected_cost_bps, unit="bps", labels=base_labels),
        _sample("v53_execution_realized_cost_bps", kind="gauge", value=payload.infra.realized_cost_bps, unit="bps", labels=base_labels),
        _sample("v53_execution_elw_bps", kind="gauge", value=payload.infra.elw_bps, unit="bps", labels=base_labels),
        _sample("v53_execution_partial_fill_count", kind="gauge", value=float(payload.infra.partial_fill_count), unit="count", labels=base_labels),
        _sample("v53_execution_fill_latency_ms_p95", kind="gauge", value=float(payload.infra.fill_latency_ms_p95), unit="ms", labels=base_labels),
        _sample("v53_execution_reconciliation_alert_count", kind="gauge", value=float(payload.infra.reconciliation_alert_count), unit="count", labels=base_labels),
    )


def _build_dynamic_samples(payload: TechnicalDashboardPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    samples: list[MetricSample] = []
    for reader in payload.build14.reader_projections:
        samples.append(_sample("v53_build14_reader_value", kind="gauge", value=reader.observed_value, unit="score", labels={**base_labels, "reader": reader.reader_name, "family": reader.signal_family, "status": reader.status}))
        samples.append(_sample("v53_build14_reader_status", kind="state", value=1.0, labels={**base_labels, "reader": reader.reader_name, "family": reader.signal_family, "status": reader.status}))
    for metric_name in payload.alerts.persisted_metric_names:
        samples.append(_sample("v53_alert_metric_persistence", kind="state", value=1.0, labels={**base_labels, "metric": metric_name, "persistence": "persisted"}))
    for metric_name in payload.alerts.volatile_metric_names:
        samples.append(_sample("v53_alert_metric_persistence", kind="state", value=1.0, labels={**base_labels, "metric": metric_name, "persistence": "volatile"}))
    if payload.alerts.operator_runtime.latest_event_type:
        samples.append(_sample("v53_alert_operator_latest_event", kind="state", value=1.0, labels={**base_labels, "event_type": payload.alerts.operator_runtime.latest_event_type}))
    if payload.alerts.operator_runtime.latest_acknowledged_alert_id:
        samples.append(_sample("v53_alert_operator_latest_ack", kind="state", value=1.0, labels={**base_labels, "alert_id": payload.alerts.operator_runtime.latest_acknowledged_alert_id}))
    if payload.alerts.operator_runtime.latest_rejection_reason:
        samples.append(_sample("v53_alert_operator_latest_rejection", kind="state", value=1.0, labels={**base_labels, "reason": payload.alerts.operator_runtime.latest_rejection_reason}))
    for index, event in enumerate(payload.alerts.operator_runtime.recent_event_log):
        samples.append(_sample("v53_alert_operator_recent_event", kind="state", value=float(event.timestamp_ms), unit="ms", labels={**base_labels, "index": str(index), "event_type": event.event_type, "action": event.action, "accepted": "true" if event.accepted else "false", "target": event.target or "none", "message": event.message}))
        if event.rejection_reason:
            samples.append(_sample("v53_alert_operator_recent_rejection", kind="state", value=float(event.timestamp_ms), unit="ms", labels={**base_labels, "index": str(index), "action": event.action, "target": event.target or "none", "reason": event.rejection_reason}))
    for module_name in payload.system.active_modules:
        samples.append(_sample("v53_system_module_active", kind="state", value=1.0, labels={**base_labels, "module": module_name}))
    stale_engines = set(payload.system.stale_engines)
    for engine_id in payload.system.active_engines:
        samples.append(_sample("v53_system_engine_stale", kind="state", value=1.0 if engine_id in stale_engines else 0.0, labels={**base_labels, "engine": engine_id}))
    for engine in payload.engines:
        samples.append(_sample("v53_engine_useful_frequency", kind="gauge", value=engine.useful_frequency, unit="count", labels={**base_labels, "engine": engine.engine_id}))
        samples.append(_sample("v53_engine_ce_expected", kind="gauge", value=engine.ce_expected, unit="ratio", labels={**base_labels, "engine": engine.engine_id}))
        if engine.physics.physics_pressure_state:
            samples.append(_sample("v53_engine_physics_pressure_state", kind="state", value=1.0, labels={**base_labels, "engine": engine.engine_id, "state": engine.physics.physics_pressure_state}))
        if engine.physics.fragility_score is not None:
            samples.append(_sample("v53_engine_fragility_score", kind="gauge", value=engine.physics.fragility_score, unit="ratio", labels={**base_labels, "engine": engine.engine_id}))
        if engine.physics.toxicity_score is not None:
            samples.append(_sample("v53_engine_toxicity_score", kind="gauge", value=engine.physics.toxicity_score, unit="ratio", labels={**base_labels, "engine": engine.engine_id}))
        if engine.physics.execution_survivability_score is not None:
            samples.append(_sample("v53_engine_execution_survivability_score", kind="gauge", value=engine.physics.execution_survivability_score, unit="ratio", labels={**base_labels, "engine": engine.engine_id}))
        if engine.physics.micro_friction_score is not None:
            samples.append(_sample("v53_engine_micro_friction_score", kind="gauge", value=engine.physics.micro_friction_score, unit="ratio", labels={**base_labels, "engine": engine.engine_id}))
    for pair in payload.pairs:
        samples.append(_sample("v53_pair_freshness_ms", kind="gauge", value=float(pair.freshness_ms), unit="ms", labels={**base_labels, "pair": pair.pair, "health": pair.health.value}))
        samples.append(_sample("v53_pair_useful_frequency", kind="gauge", value=pair.useful_frequency, unit="count", labels={**base_labels, "pair": pair.pair}))
    return tuple(samples)


def _render_text_payload(samples: tuple[MetricSample, ...]) -> str:
    lines = ["# V5.3 technical observability export"]
    for sample in samples:
        lines.append(f"{sample.name}{_format_labels(sample.labels)} {sample.value}")
    return "\n".join(lines)


def build_observability_export_support(payload: TechnicalDashboardPayload) -> ObservabilityExport:
    """Emit a grouped, stable metrics surface from the Build-10 technical payload."""

    base_labels = _labels(payload)
    samples = (
        _build_system_samples(payload, base_labels)
        + _build_portfolio_and_meta_samples(payload, base_labels)
        + _build_build9x_and_shadow_samples(payload, base_labels)
        + _build_rollout_and_bridge_samples(payload, base_labels)
        + _build_build14_replay_alert_samples(payload, base_labels)
        + _build_dynamic_samples(payload, base_labels)
    )
    return ObservabilityExport(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        samples=samples,
        text_payload=_render_text_payload(samples),
    )
