"""Bounded challenger-evidence alert derivation shared by monitoring surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity

from .contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactVerdictBundleProjection,
)
from .contracts_core import MonitoringSnapshot


@dataclass(frozen=True)
class ShadowChallengerAlertState:
    """Bounded aggregate challenger-evidence state derived from current projections."""

    configured: bool
    has_ready_comparison: bool
    invalid_evidence: bool
    missing_evidence: bool
    stale_evidence: bool
    sharia_scope_blocked: bool


def merge_alert_records(
    base_alerts: tuple[AlertRecord, ...],
    extra_alerts: tuple[AlertRecord, ...],
) -> tuple[AlertRecord, ...]:
    """Merge alert tuples while keeping alert ids unique and order stable."""

    merged: dict[str, AlertRecord] = {}
    for alert in base_alerts + extra_alerts:
        merged[alert.alert_id] = alert
    return tuple(merged.values())


def build_shadow_challenger_alert_state(
    *,
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = (),
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = (),
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None,
    shadow_last_completed_session_date: str = "",
) -> ShadowChallengerAlertState:
    """Resolve bounded alert booleans from the current challenger evidence surfaces."""

    configured = any(
        item.slot == "shadow_challenger" for item in artifact_runtime_visibility
    )
    has_ready_comparison = any(
        item.comparison_status == "shadow_ready" for item in artifact_comparisons
    )
    verdict_status = (
        artifact_verdict_bundle.overall_verdict
        if artifact_verdict_bundle is not None
        else "not_available"
    )
    invalid_evidence = verdict_status == "invalid_evidence" or any(
        item.comparison_status == "invalid_evidence" for item in artifact_comparisons
    )
    stale_evidence = (
        configured
        and bool(shadow_last_completed_session_date)
        and artifact_verdict_bundle is not None
        and bool(artifact_verdict_bundle.session_date)
        and artifact_verdict_bundle.session_date != shadow_last_completed_session_date
    )
    sharia_scope_blocked = (
        configured
        and not invalid_evidence
        and not stale_evidence
        and verdict_status == "sharia_scope_blocked"
    )
    missing_evidence = (
        configured
        and bool(shadow_last_completed_session_date)
        and not invalid_evidence
        and not stale_evidence
        and not sharia_scope_blocked
        and not has_ready_comparison
        and (
            artifact_verdict_bundle is None
            or verdict_status in {"not_available", "shadow_pending_evidence"}
        )
    )
    return ShadowChallengerAlertState(
        configured=configured,
        has_ready_comparison=has_ready_comparison,
        invalid_evidence=invalid_evidence,
        missing_evidence=missing_evidence,
        stale_evidence=stale_evidence,
        sharia_scope_blocked=sharia_scope_blocked,
    )


def build_shadow_challenger_alerts(
    snapshot: MonitoringSnapshot,
    *,
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = (),
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = (),
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None,
    shadow_last_completed_session_date: str = "",
) -> tuple[AlertRecord, ...]:
    """Emit bounded challenger-evidence alerts without widening the raw snapshot."""

    state = build_shadow_challenger_alert_state(
        artifact_runtime_visibility=artifact_runtime_visibility,
        artifact_comparisons=artifact_comparisons,
        artifact_verdict_bundle=artifact_verdict_bundle,
        shadow_last_completed_session_date=shadow_last_completed_session_date,
    )
    if not state.configured:
        return ()

    alerts: list[AlertRecord] = []
    if state.invalid_evidence:
        alerts.append(
            _build_alert(
                snapshot,
                suffix="shadow_challenger_invalid_evidence",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.INFRA,
                message="Shadow challenger evidence is invalid and requires operator review.",
            )
        )
    elif state.stale_evidence:
        alerts.append(
            _build_alert(
                snapshot,
                suffix="shadow_challenger_evidence_stale",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.INFRA,
                message=(
                    "Shadow challenger evidence is stale relative to the last completed "
                    f"session_date={shadow_last_completed_session_date}."
                ),
            )
        )
    elif state.sharia_scope_blocked:
        alerts.append(
            _build_alert(
                snapshot,
                suffix="shadow_challenger_sharia_scope_blocked",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.RISK,
                message="Shadow challenger verdict is blocked by the governed halal scope.",
            )
        )
    elif state.missing_evidence:
        alerts.append(
            _build_alert(
                snapshot,
                suffix="shadow_challenger_evidence_missing",
                severity=AlertSeverity.WARNING,
                category=AlertCategory.INFRA,
                message=(
                    "Shadow challengers are configured but current-session evidence is "
                    "not available yet."
                ),
            )
        )
    return tuple(alerts)


def _build_alert(
    snapshot: MonitoringSnapshot,
    *,
    suffix: str,
    severity: AlertSeverity,
    category: AlertCategory,
    message: str,
) -> AlertRecord:
    return AlertRecord(
        timestamp_ms=snapshot.timestamp_ms,
        alert_id=f"shadow_challenger:{suffix}",
        severity=severity,
        category=category,
        message=message,
        module="monitoring",
    )


__all__ = [
    "ShadowChallengerAlertState",
    "build_shadow_challenger_alert_state",
    "build_shadow_challenger_alerts",
    "merge_alert_records",
]
