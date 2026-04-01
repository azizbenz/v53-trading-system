"""Minimal structured observability export for Build-10 supervision."""

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
    return MetricSample(
        name=name,
        kind=kind,
        value=value,
        unit=unit,
        labels=labels or {},
    )


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


def build_observability_export(payload: TechnicalDashboardPayload) -> ObservabilityExport:
    """Emit a grouped, stable metrics surface from the Build-10 technical payload."""

    base_labels = _labels(payload)
    samples: list[MetricSample] = [
        _sample(
            "v53_system_headline_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.headline_status},
        ),
        _sample(
            "v53_system_active_alert_count",
            kind="gauge",
            value=float(payload.alerts.active_alert_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_system_active_module_count",
            kind="gauge",
            value=float(len(payload.system.active_modules)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_system_active_engine_count",
            kind="gauge",
            value=float(len(payload.system.active_engines)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_system_build9x_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.build9x_status},
        ),
        _sample(
            "v53_system_shadow_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.shadow_status},
        ),
        _sample(
            "v53_system_micro_live_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.micro_live_status},
        ),
        _sample(
            "v53_system_live_light_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.live_light_status},
        ),
        _sample(
            "v53_system_build14_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.build14_status},
        ),
        _sample(
            "v53_system_replay_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.system.replay_import_status},
        ),
        _sample(
            "v53_meta_dtr_coverage_ratio",
            kind="gauge",
            value=payload.build9_meta.dtr_coverage,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_cra_sterilization_ratio",
            kind="gauge",
            value=payload.build9_meta.cra_sterilization_rate,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_cra_alert_count",
            kind="gauge",
            value=float(payload.build9_meta.cra_alert_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_break_even_drift_scope_count",
            kind="gauge",
            value=float(len(payload.build9_meta.break_even_drift_scopes)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_edge_credible_count",
            kind="gauge",
            value=float(payload.build9_meta.edge_credible_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_edge_degraded_count",
            kind="gauge",
            value=float(payload.build9_meta.edge_degraded_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_meta_edge_surveillance_count",
            kind="gauge",
            value=float(payload.build9_meta.edge_surveillance_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.build9x.status},
        ),
        _sample(
            "v53_build9x_recent_diagnostics",
            kind="gauge",
            value=float(payload.build9x.diagnostics_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_open_hypotheses",
            kind="gauge",
            value=float(payload.build9x.open_hypotheses),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_total_hypotheses",
            kind="gauge",
            value=float(payload.build9x.total_hypotheses),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_near_miss_count",
            kind="gauge",
            value=float(payload.build9x.near_miss_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_replay_candidate_count",
            kind="gauge",
            value=float(payload.build9x.replay_candidate_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_memory_record_count",
            kind="gauge",
            value=float(payload.build9x.memory_record_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_build9x_review_export_ready",
            kind="state",
            value=1.0 if payload.build9x.review_export_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_run_state",
            kind="state",
            value=1.0,
            labels={**base_labels, "state": payload.shadow.run_state},
        ),
        _sample(
            "v53_shadow_verdict",
            kind="state",
            value=1.0,
            labels={**base_labels, "verdict": payload.shadow.verdict},
        ),
        _sample(
            "v53_shadow_divergent_comparison_count",
            kind="gauge",
            value=float(payload.shadow.divergent_comparison_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_blocking_comparison_count",
            kind="gauge",
            value=float(payload.shadow.blocking_comparison_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_blocking_reason_count",
            kind="gauge",
            value=float(len(payload.shadow.blocking_reasons)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_manual_review_required",
            kind="state",
            value=1.0 if payload.shadow.manual_review_required else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_shadow_review_export_ready",
            kind="state",
            value=1.0 if payload.shadow.review_export_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_run_state",
            kind="state",
            value=1.0,
            labels={**base_labels, "state": payload.micro_live.run_state},
        ),
        _sample(
            "v53_micro_live_verdict",
            kind="state",
            value=1.0,
            labels={**base_labels, "verdict": payload.micro_live.verdict},
        ),
        _sample(
            "v53_micro_live_allowed_to_probe",
            kind="state",
            value=1.0 if payload.micro_live.allowed_to_probe else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_planned_pair_count",
            kind="gauge",
            value=float(len(payload.micro_live.planned_pairs)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_planned_engine_count",
            kind="gauge",
            value=float(len(payload.micro_live.planned_engines)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_approved_total_notional_usdt",
            kind="gauge",
            value=payload.micro_live.approved_total_notional_usdt,
            unit="usdt",
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_blocking_reason_count",
            kind="gauge",
            value=float(len(payload.micro_live.blocking_reasons)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_observability_ready",
            kind="state",
            value=1.0 if payload.micro_live.observability_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_halt_ready",
            kind="state",
            value=1.0 if payload.micro_live.halt_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_micro_live_onboarding_ready",
            kind="state",
            value=1.0 if payload.micro_live.onboarding_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_run_state",
            kind="state",
            value=1.0,
            labels={**base_labels, "state": payload.live_light.run_state},
        ),
        _sample(
            "v53_live_light_verdict",
            kind="state",
            value=1.0,
            labels={**base_labels, "verdict": payload.live_light.verdict},
        ),
        _sample(
            "v53_live_light_allowed_to_execute_small",
            kind="state",
            value=1.0 if payload.live_light.allowed_to_execute_small else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_planned_pair_count",
            kind="gauge",
            value=float(len(payload.live_light.planned_pairs)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_planned_engine_count",
            kind="gauge",
            value=float(len(payload.live_light.planned_engines)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_approved_total_notional_usdt",
            kind="gauge",
            value=payload.live_light.approved_total_notional_usdt,
            unit="usdt",
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_blocking_reason_count",
            kind="gauge",
            value=float(len(payload.live_light.blocking_reasons)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_observability_ready",
            kind="state",
            value=1.0 if payload.live_light.observability_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_halt_ready",
            kind="state",
            value=1.0 if payload.live_light.halt_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_execution_ready",
            kind="state",
            value=1.0 if payload.live_light.execution_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_broker_ready",
            kind="state",
            value=1.0 if payload.live_light.broker_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_live_light_exchange_ready",
            kind="state",
            value=1.0 if payload.live_light.exchange_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_build14_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.build14.status},
        ),
        _sample(
            "v53_build14_hard_state",
            kind="state",
            value=1.0,
            labels={**base_labels, "hard_state": payload.build14.hard_state},
        ),
        _sample(
            "v53_build14_live_promotion_eligible",
            kind="state",
            value=1.0 if payload.build14.live_promotion_eligible else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_build14_influence_mode",
            kind="state",
            value=1.0,
            labels={**base_labels, "mode": payload.build14.influence_mode},
        ),
        _sample(
            "v53_build14_action",
            kind="state",
            value=1.0,
            labels={**base_labels, "action": payload.build14.action},
        ),
        _sample(
            "v53_build14_severity",
            kind="state",
            value=1.0,
            labels={**base_labels, "severity": payload.build14.severity},
        ),
        _sample(
            "v53_build14_market_toxicity_value",
            kind="gauge",
            value=payload.build14.market_toxicity_value,
            unit="score",
            labels={**base_labels, "status": payload.build14.market_toxicity_status},
        ),
        _sample(
            "v53_build14_execution_fragility_value",
            kind="gauge",
            value=payload.build14.execution_fragility_value,
            unit="score",
            labels={**base_labels, "status": payload.build14.execution_fragility_status},
        ),
        _sample(
            "v53_build14_confidence_penalty_weight",
            kind="gauge",
            value=payload.build14.confidence_penalty_weight,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_build14_recommended_budget_factor",
            kind="gauge",
            value=payload.build14.recommended_budget_factor,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_build14_requires_manual_review",
            kind="state",
            value=1.0 if payload.build14.requires_manual_review else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_build14_reason_code_count",
            kind="gauge",
            value=float(len(payload.build14.reason_codes)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_replay_artifact_present",
            kind="state",
            value=1.0 if payload.replay_import.artifact_id != "none" else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_replay_validation_started",
            kind="state",
            value=1.0 if payload.replay_import.validation_status != "not_run" else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_replay_validation_accepted",
            kind="state",
            value=1.0 if payload.replay_import.validation_status == "accepted" else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_replay_rejection_reason_count",
            kind="gauge",
            value=float(len(payload.replay_import.rejection_reasons)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_active_count",
            kind="gauge",
            value=float(payload.alerts.active_alert_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_queue_backlog",
            kind="gauge",
            value=float(payload.alerts.queue_backlog),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_stale_pair_count",
            kind="gauge",
            value=float(payload.alerts.stale_pair_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_dtr_loss_count",
            kind="gauge",
            value=float(payload.alerts.dtr_loss_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_log_loss_count",
            kind="gauge",
            value=float(payload.alerts.log_loss_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_alert_backlog_stale_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.alerts.backlog_stale_status},
        ),
        _sample(
            "v53_alert_loss_drift_status",
            kind="state",
            value=1.0,
            labels={**base_labels, "status": payload.alerts.loss_drift_status},
        ),
    ]

    for module_name in payload.system.active_modules:
        samples.append(
            _sample(
                "v53_system_module_active",
                kind="state",
                value=1.0,
                labels={**base_labels, "module": module_name},
            )
        )

    stale_engines = set(payload.system.stale_engines)
    for engine_id in payload.system.active_engines:
        samples.append(
            _sample(
                "v53_system_engine_stale",
                kind="state",
                value=1.0 if engine_id in stale_engines else 0.0,
                labels={**base_labels, "engine": engine_id},
            )
        )

    lines = ["# V5.3 technical observability export"]
    for sample in samples:
        lines.append(f"{sample.name}{_format_labels(sample.labels)} {sample.value}")

    return ObservabilityExport(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        samples=tuple(samples),
        text_payload="\n".join(lines),
    )


__all__ = [
    "build_observability_export",
]
