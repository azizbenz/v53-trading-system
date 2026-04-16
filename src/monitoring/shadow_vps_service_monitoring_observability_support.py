"""Support helpers for Shadow VPS service observability export construction."""

from __future__ import annotations

from monitoring.contracts import MetricSample, ObservabilityExport, ShadowVpsServiceMonitoringPayload


def _sample(
    name: str,
    *,
    kind: str,
    value: float,
    labels: dict[str, str],
    unit: str = "",
) -> MetricSample:
    return MetricSample(name=name, kind=kind, value=value, labels=labels, unit=unit)


def _build_base_labels(payload: ShadowVpsServiceMonitoringPayload) -> dict[str, str]:
    return {
        "correlation_id": payload.correlation_id,
        "profile": payload.profile.value,
        "runtime_mode": payload.runtime_mode.value,
    }


def _build_service_samples(
    payload: ShadowVpsServiceMonitoringPayload,
    base_labels: dict[str, str],
) -> tuple[MetricSample, ...]:
    return (
        _sample(
            "v53_shadow_vps_service_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "status": payload.service_status,
                "acquisition_mode": payload.acquisition_mode,
                "runtime_data_source": payload.runtime_data_source,
            },
        ),
        _sample(
            "v53_shadow_vps_service_heartbeat_age_ms",
            kind="gauge",
            value=float(payload.heartbeat_age_ms),
            unit="ms",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_loop_count",
            kind="counter",
            value=float(payload.loop_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_success_count",
            kind="counter",
            value=float(payload.success_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_idle_count",
            kind="counter",
            value=float(payload.idle_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_failure_count",
            kind="counter",
            value=float(payload.failure_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_promotion_gate_passed",
            kind="state",
            value=1.0 if payload.promotion_gate_passed else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_live_capture_accepted_message_count",
            kind="gauge",
            value=float(payload.live_capture_accepted_message_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_service_live_user_data_authenticated",
            kind="state",
            value=1.0 if payload.live_user_data_authenticated else 0.0,
            labels=base_labels,
        ),
    )


def _build_runtime_samples(
    payload: ShadowVpsServiceMonitoringPayload,
    base_labels: dict[str, str],
) -> tuple[MetricSample, ...]:
    return (
        _sample(
            "v53_shadow_vps_execution_telemetry_ready",
            kind="state",
            value=1.0 if payload.execution_telemetry_status == "written" else 0.0,
            labels={**base_labels, "telemetry_status": payload.execution_telemetry_status, "acquisition_mode": payload.acquisition_mode},
        ),
        _sample(
            "v53_shadow_vps_telegram_alert_delivery_status",
            kind="state",
            value=1.0,
            labels={
                **base_labels,
                "delivery_status": payload.telegram_alert_delivery_status,
                "alert_event_type": payload.telegram_alert_delivery_event_type or "none",
                "config_source": payload.telegram_alert_config_source,
                "error_present": "true" if bool(payload.telegram_alert_delivery_error) else "false",
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_status",
            kind="state",
            value=1.0 if payload.execution_runtime_bootstrap_status == "ready" else 0.0,
            labels={
                **base_labels,
                "bootstrap_status": payload.execution_runtime_bootstrap_status,
                "bootstrap_source": payload.execution_runtime_bootstrap_source,
                "gatekeeper_audit_source": payload.execution_runtime_gatekeeper_audit_source,
                "user_data_stream_enabled": "true" if payload.execution_runtime_bootstrap_user_data_stream_enabled else "false",
                "reconciliation_executed": "true" if payload.execution_runtime_bootstrap_reconciliation_boot_executed else "false",
                "trading_blocked": "true" if payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked else "false",
                "circuit_breaker_tripped": "true" if payload.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped else "false",
                "recovery_action": payload.execution_runtime_bootstrap_reconciliation_boot_recovery_action or "none",
            },
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_divergence_count",
            kind="gauge",
            value=float(payload.execution_runtime_bootstrap_reconciliation_boot_divergence_count),
            unit="count",
            labels={**base_labels, "bootstrap_status": payload.execution_runtime_bootstrap_status, "bootstrap_source": payload.execution_runtime_bootstrap_source},
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_bootstrap_trading_blocked",
            kind="state",
            value=1.0 if payload.execution_runtime_bootstrap_reconciliation_boot_trading_blocked else 0.0,
            labels={**base_labels, "bootstrap_status": payload.execution_runtime_bootstrap_status, "bootstrap_source": payload.execution_runtime_bootstrap_source, "gatekeeper_audit_source": payload.execution_runtime_gatekeeper_audit_source},
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_ready",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_ready else 0.0,
            labels={**base_labels, "projection_status": payload.execution_runtime_projection_status, "projection_source": payload.execution_runtime_projection_source},
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_bridge_loaded",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_bridge_loaded else 0.0,
            labels={**base_labels, "bridge_status": payload.execution_runtime_projection_bridge_status},
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_ready_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_ready_consumer_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_rate_limit_model_loaded",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_rate_limit_model_loaded else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_spread_guard_model_loaded",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_spread_guard_model_loaded else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_slippage_model_loaded",
            kind="state",
            value=1.0 if payload.execution_runtime_projection_slippage_model_loaded else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_partial_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_partial_consumer_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_vps_execution_runtime_projection_blocked_consumer_count",
            kind="gauge",
            value=float(payload.execution_runtime_projection_blocked_consumer_count),
            unit="count",
            labels=base_labels,
        ),
    )


def _build_governance_samples(payload: ShadowVpsServiceMonitoringPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    return (
        _sample("v53_shadow_vps_regime_lite_safing_status", kind="state", value=1.0, labels={**base_labels, "governance_status": payload.regime_lite_governance_status, "severity": payload.regime_lite_safing_severity, "state": payload.regime_lite_state, "candidate_state": payload.regime_lite_candidate_state, "assessment_source": payload.regime_lite_assessment_source, "safing_source": payload.regime_lite_safing_recommendation_source, "recommended_action": payload.regime_lite_safing_recommended_operator_action or "none"}),
        _sample("v53_shadow_vps_regime_lite_entries_blocked", kind="state", value=1.0 if payload.regime_lite_entries_blocked else 0.0, labels={**base_labels, "governance_status": payload.regime_lite_governance_status, "severity": payload.regime_lite_safing_severity, "assessment_source": payload.regime_lite_assessment_source, "safing_source": payload.regime_lite_safing_recommendation_source}),
        _sample("v53_shadow_vps_regime_lite_should_exit_all", kind="state", value=1.0 if payload.regime_lite_safing_should_exit_all else 0.0, labels={**base_labels, "governance_status": payload.regime_lite_governance_status, "severity": payload.regime_lite_safing_severity, "assessment_source": payload.regime_lite_assessment_source, "safing_source": payload.regime_lite_safing_recommendation_source}),
        _sample("v53_shadow_vps_info_stress_status", kind="state", value=1.0, labels={**base_labels, "governance_status": payload.info_stress_governance_status, "level": payload.info_stress_level, "assessment_source": payload.info_stress_assessment_source}),
        _sample("v53_shadow_vps_info_stress_alert_count", kind="gauge", value=float(payload.info_stress_alert_count), unit="count", labels={**base_labels, "governance_status": payload.info_stress_governance_status, "level": payload.info_stress_level}),
        _sample("v53_shadow_vps_info_stress_entries_blocked", kind="state", value=1.0 if payload.info_stress_entries_blocked else 0.0, labels={**base_labels, "governance_status": payload.info_stress_governance_status, "level": payload.info_stress_level, "assessment_source": payload.info_stress_assessment_source}),
    )


def _build_resource_samples(payload: ShadowVpsServiceMonitoringPayload, base_labels: dict[str, str]) -> tuple[MetricSample, ...]:
    process_labels = {**base_labels, "pid": str(payload.process.pid), "mode": payload.process.sampling_mode}
    disk_labels = {**base_labels, "path": payload.disk.path, "mode": payload.disk.sampling_mode}
    return (
        _sample("v53_shadow_vps_process_cpu_pct", kind="gauge", value=payload.process.cpu_pct, unit="pct", labels=process_labels),
        _sample("v53_shadow_vps_process_ram_pct", kind="gauge", value=payload.process.ram_pct, unit="pct", labels=process_labels),
        _sample("v53_shadow_vps_process_rss_mb", kind="gauge", value=payload.process.rss_mb, unit="mb", labels=process_labels),
        _sample("v53_shadow_vps_process_thread_count", kind="gauge", value=float(payload.process.thread_count), unit="count", labels=process_labels),
        _sample("v53_shadow_vps_disk_used_pct", kind="gauge", value=payload.disk.used_pct, unit="pct", labels=disk_labels),
        _sample("v53_shadow_vps_disk_free_gb", kind="gauge", value=payload.disk.free_gb, unit="gb", labels=disk_labels),
        _sample("v53_shadow_vps_service_last_error_present", kind="state", value=1.0 if payload.last_error else 0.0, labels=base_labels),
    )


def _render_text_payload(samples: tuple[MetricSample, ...]) -> str:
    lines = ["# V5.3 Shadow VPS service observability export"]
    for sample in samples:
        label_text = ""
        if sample.labels:
            joined = ",".join(f'{key}="{value}"' for key, value in sorted(sample.labels.items()))
            label_text = f"{{{joined}}}"
        lines.append(f"{sample.name}{label_text} {sample.value}")
    return "\n".join(lines)


def build_shadow_vps_service_observability_export_support(
    payload: ShadowVpsServiceMonitoringPayload,
) -> ObservabilityExport:
    """Emit the typed observability export for the Shadow VPS service."""

    base_labels = _build_base_labels(payload)
    samples = (
        _build_service_samples(payload, base_labels)
        + _build_runtime_samples(payload, base_labels)
        + _build_governance_samples(payload, base_labels)
        + _build_resource_samples(payload, base_labels)
    )
    return ObservabilityExport(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        samples=samples,
        text_payload=_render_text_payload(samples),
    )
