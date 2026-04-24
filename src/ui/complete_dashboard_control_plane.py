"""Build-17 Complete dashboard control-plane section."""

from __future__ import annotations

from typing import Protocol

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)
from ui.contracts import DashboardCard, DashboardSection


class CompleteControlPlaneSupplement(Protocol):
    """Structural subset required to render the governed Build-17 control plane."""

    command_queue_snapshot: DashboardCommandQueueSnapshot | None
    active_ml_artifact: DashboardArtifactTransferManifest | None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None
    recovery_readiness_report: VpsRecoveryReadinessReport | None
    warmup_run_summary: VpsWarmupRunSummary | None
    operator_report_status: str
    operator_report_ref: str


def build_complete_control_plane_section(
    supplement: CompleteControlPlaneSupplement,
) -> DashboardSection:
    """Render only governed Build-17 queue/artifact/recovery state."""

    queue = supplement.command_queue_snapshot
    recovery = supplement.recovery_readiness_report
    warmup = supplement.warmup_run_summary
    return DashboardSection(
        title="Build-17 Control Plane",
        cards=(
            _queue_card(queue),
            _artifact_card(supplement),
            _recovery_card(recovery),
            _warmup_card(warmup),
            _operator_report_card(supplement),
        ),
    )


def _queue_card(queue: DashboardCommandQueueSnapshot | None) -> DashboardCard:
    return DashboardCard(
        key="complete_control_queue",
        label="Dashboard Queue",
        value=(
            "not configured"
            if queue is None
            else f"{queue.queue_status.value} / pending={queue.pending_request_count}"
        ),
        status="planned" if queue is None else ("healthy" if queue.healthy else "warning"),
        detail=(
            "No governed queue snapshot attached"
            if queue is None
            else (
                f"ambiguous={queue.ambiguous_pending_count} / "
                f"completed={queue.completed_result_count} / "
                f"failed={queue.failed_result_count}"
            )
        ),
    )


def _artifact_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    return DashboardCard(
        key="complete_control_artifacts",
        label="Active Artifacts",
        value=(
            f"ml={_artifact_label(supplement.active_ml_artifact)} / "
            f"regime={_artifact_label(supplement.active_regime_detector_artifact)}"
        ),
        status="info",
        detail=(
            f"ml_hash={_artifact_hash(supplement.active_ml_artifact)} / "
            f"regime_hash={_artifact_hash(supplement.active_regime_detector_artifact)}"
        ),
    )


def _recovery_card(recovery: VpsRecoveryReadinessReport | None) -> DashboardCard:
    return DashboardCard(
        key="complete_control_recovery",
        label="Recovery Readiness",
        value=(
            "not configured"
            if recovery is None
            else f"eligible_to_trade={recovery.eligible_to_trade}"
        ),
        status="planned" if recovery is None else ("healthy" if recovery.eligible_to_trade else "warning"),
        detail=(
            "No recovery readiness report attached"
            if recovery is None
            else _join(recovery.blocking_reasons, empty="No blocking reason")
        ),
    )


def _warmup_card(warmup: VpsWarmupRunSummary | None) -> DashboardCard:
    return DashboardCard(
        key="complete_control_warmup",
        label="Warmup State",
        value=(
            "not configured"
            if warmup is None
            else f"{warmup.final_state.value} / eligible={warmup.eligible_to_trade}"
        ),
        status="planned" if warmup is None else ("healthy" if warmup.eligible_to_trade else "warning"),
        detail=(
            "No warmup summary attached"
            if warmup is None
            else _join(tuple(state.value for state in warmup.phase_sequence), empty="n/a")
        ),
    )


def _operator_report_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    return DashboardCard(
        key="complete_control_operator_report",
        label="Operator Report",
        value=supplement.operator_report_status,
        status="info" if supplement.operator_report_status != "not_available" else "planned",
        detail=supplement.operator_report_ref or "No operator report attached",
    )


def _artifact_label(manifest: DashboardArtifactTransferManifest | None) -> str:
    if manifest is None:
        return "none"
    return f"{manifest.artifact_kind.value}:{manifest.artifact_id}"


def _artifact_hash(manifest: DashboardArtifactTransferManifest | None) -> str:
    if manifest is None:
        return "none"
    return manifest.artifact_hash[:12]


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


__all__ = ["build_complete_control_plane_section"]
