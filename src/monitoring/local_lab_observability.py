"""Structured observability export for Local IA Lab packaging runs."""

from __future__ import annotations

from interface_contracts.domain_types import ProfileId, RuntimeMode
from monitoring.contracts import MetricSample, ObservabilityExport
from monitoring.local_lab_monitoring_projection import LocalLabMonitoringProjection


_STATUS_VALUE = {
    "planned": 0.0,
    "info": 1.0,
    "warning": 2.0,
    "healthy": 3.0,
    "critical": 4.0,
}


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


def _labels(
    projection: LocalLabMonitoringProjection,
    *,
    profile: ProfileId,
    runtime_mode: RuntimeMode,
) -> dict[str, str]:
    labels = {
        "correlation_id": projection.correlation_id,
        "profile": profile.value,
        "runtime_mode": runtime_mode.value,
        "promotion_readiness_status": projection.promotion_readiness_status,
        "release_status": projection.release_status,
        "bridge_status": projection.bridge_status,
    }
    if projection.selected_pair:
        labels["pair"] = projection.selected_pair
    if projection.selected_engine_id:
        labels["engine_id"] = projection.selected_engine_id
    return labels


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    joined = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    return f"{{{joined}}}"


def build_local_lab_observability_export(
    *,
    projection: LocalLabMonitoringProjection,
    profile: ProfileId,
    runtime_mode: RuntimeMode,
    timestamp_ms: int,
) -> ObservabilityExport:
    """Emit a stable Local IA Lab observability surface from the compact monitoring projection."""

    base_labels = _labels(projection, profile=profile, runtime_mode=runtime_mode)
    samples = (
        _sample(
            "v53_local_lab_monitoring_status",
            kind="state",
            value=_STATUS_VALUE[projection.status],
            labels={**base_labels, "status": projection.status},
        ),
        _sample(
            "v53_local_lab_review_ready",
            kind="state",
            value=1.0 if projection.review_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_trade_loss_attribution_ready",
            kind="state",
            value=1.0 if projection.trade_loss_attribution_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_walk_forward_ready",
            kind="state",
            value=1.0 if projection.walk_forward_review_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_artifact_ablation_ready",
            kind="state",
            value=1.0 if projection.artifact_ablation_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_artifact_proof_ready",
            kind="state",
            value=1.0 if projection.artifact_proof_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_edge_calibration_ready",
            kind="state",
            value=1.0 if projection.edge_calibration_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_release_ready_for_shadow",
            kind="state",
            value=1.0 if projection.release_ready_for_shadow else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_dry_run_ready_for_shadow",
            kind="state",
            value=1.0 if projection.ready_for_shadow_import_dry_run else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_scope_count",
            kind="gauge",
            value=float(projection.scope_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_scope_ready_count",
            kind="gauge",
            value=float(projection.scope_ready_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_scope_blocked_count",
            kind="gauge",
            value=float(projection.scope_blocked_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_release_scope_ready_count",
            kind="gauge",
            value=float(projection.release_scope_ready_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_release_scope_blocked_count",
            kind="gauge",
            value=float(projection.release_scope_blocked_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_loss_surrogate_ready",
            kind="state",
            value=1.0 if projection.loss_surrogate_ready else 0.0,
            labels={**base_labels, "loss_surrogate_status": projection.loss_surrogate_status},
        ),
        _sample(
            "v53_local_lab_loss_surrogate_scope_count",
            kind="gauge",
            value=float(projection.loss_surrogate_scope_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_loss_surrogate_top_probability",
            kind="gauge",
            value=projection.loss_surrogate_top_probability,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_calibration_methods_review_ready",
            kind="state",
            value=1.0 if projection.calibration_methods_review_ready else 0.0,
            labels={
                **base_labels,
                "calibration_review_status": projection.calibration_methods_review_status,
            },
        ),
        _sample(
            "v53_local_lab_calibration_methods_dsr_pass",
            kind="state",
            value=(
                0.0
                if projection.calibration_methods_dsr_pass is not True
                else 1.0
            ),
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_calibration_methods_walkforward_plan_ready",
            kind="state",
            value=1.0 if projection.calibration_methods_walk_forward_plan_ready else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_calibration_methods_stationarity_pass",
            kind="state",
            value=(0.0 if projection.calibration_methods_stationarity_pass is not True else 1.0),
            labels={
                **base_labels,
                "stationarity_status": projection.calibration_methods_stationarity_status,
            },
        ),
        _sample(
            "v53_local_lab_execution_review_ready",
            kind="state",
            value=1.0 if projection.execution_review_ready else 0.0,
            labels={**base_labels, "execution_review_status": projection.execution_review_status},
        ),
        _sample(
            "v53_local_lab_execution_ready_threshold_count",
            kind="gauge",
            value=float(projection.execution_ready_threshold_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_execution_partial_threshold_count",
            kind="gauge",
            value=float(projection.execution_partial_threshold_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_execution_blocked_threshold_count",
            kind="gauge",
            value=float(projection.execution_blocked_threshold_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_multiple_testing_review_ready",
            kind="state",
            value=1.0 if projection.multiple_testing_review_ready else 0.0,
            labels={
                **base_labels,
                "multiple_testing_status": projection.multiple_testing_review_status,
                "multiple_testing_correction": projection.multiple_testing_correction,
            },
        ),
        _sample(
            "v53_local_lab_multiple_testing_correction_required",
            kind="state",
            value=1.0 if projection.multiple_testing_correction_required else 0.0,
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_multiple_testing_family_count",
            kind="gauge",
            value=float(projection.multiple_testing_family_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_calibration_normalized_report_ready",
            kind="state",
            value=1.0 if projection.calibration_normalized_report_ready else 0.0,
            labels={
                **base_labels,
                "calibration_normalized_status": projection.calibration_normalized_report_status,
            },
        ),
        _sample(
            "v53_local_lab_calibration_normalized_threshold_count",
            kind="gauge",
            value=float(projection.calibration_normalized_threshold_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_tail_risk_review_ready",
            kind="state",
            value=1.0 if projection.tail_risk_review_ready else 0.0,
            labels={**base_labels, "tail_risk_status": projection.tail_risk_review_status},
        ),
        _sample(
            "v53_local_lab_tail_risk_ready_breaker_count",
            kind="gauge",
            value=float(projection.tail_risk_ready_breaker_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_tail_risk_partial_breaker_count",
            kind="gauge",
            value=float(projection.tail_risk_partial_breaker_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_tail_risk_blocked_breaker_count",
            kind="gauge",
            value=float(projection.tail_risk_blocked_breaker_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_research_priority_scope_count",
            kind="gauge",
            value=float(projection.research_priority_scope_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_research_priority_top_score",
            kind="gauge",
            value=projection.research_priority_top_score,
            unit="ratio",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_replay_candidate_count",
            kind="gauge",
            value=float(projection.replay_candidate_count),
            unit="count",
            labels={**base_labels, "queue_status": projection.replay_candidate_queue_status},
        ),
        _sample(
            "v53_local_lab_replay_candidate_ready_count",
            kind="gauge",
            value=float(projection.replay_candidate_ready_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_replay_ticket_count",
            kind="gauge",
            value=float(projection.replay_ticket_count),
            unit="count",
            labels={**base_labels, "ticket_status": projection.replay_ticket_index_status},
        ),
        _sample(
            "v53_local_lab_replay_ticket_ready_count",
            kind="gauge",
            value=float(projection.replay_ticket_ready_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_replay_dispatch_ready_count",
            kind="gauge",
            value=float(projection.replay_dispatch_ready_count),
            unit="count",
            labels={**base_labels, "dispatch_status": projection.replay_dispatch_plan_status},
        ),
        _sample(
            "v53_local_lab_replay_dispatch_blocked_count",
            kind="gauge",
            value=float(projection.replay_dispatch_blocked_count),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_blocking_reason_count",
            kind="gauge",
            value=float(len(projection.blocking_reasons)),
            unit="count",
            labels=base_labels,
        ),
        _sample(
            "v53_local_lab_release_gate_reason_count",
            kind="gauge",
            value=float(len(projection.release_gate_reasons)),
            unit="count",
            labels=base_labels,
        ),
    )

    lines = [
        "# V5.3 Local IA Lab observability export",
        f"# detail: {projection.detail}",
    ]
    for sample in samples:
        lines.append(f"{sample.name}{_format_labels(sample.labels)} {sample.value}")

    return ObservabilityExport(
        timestamp_ms=timestamp_ms,
        correlation_id=projection.correlation_id,
        profile=profile,
        runtime_mode=runtime_mode,
        samples=samples,
        text_payload="\n".join(lines),
    )


__all__ = ["build_local_lab_observability_export"]
