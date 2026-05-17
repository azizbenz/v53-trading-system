"""Build-17 Complete dashboard control-plane section."""

from __future__ import annotations

from typing import Protocol

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)
from monitoring.contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactVerdictBundleProjection,
)
from ui.contracts import DashboardCard, DashboardSection


class CompleteControlPlaneSupplement(Protocol):
    """Structural subset required to render the governed Build-17 control plane."""

    command_queue_snapshot: DashboardCommandQueueSnapshot | None
    active_ml_artifact: DashboardArtifactTransferManifest | None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...]
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...]
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None
    recovery_readiness_report: VpsRecoveryReadinessReport | None
    warmup_run_summary: VpsWarmupRunSummary | None
    active_binance_profile_id: str
    active_binance_environment: str
    binance_credential_validation_status: str
    credential_inventory_count: int
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
            _challenger_card(supplement),
            _comparison_card(supplement),
            _verdict_card(supplement),
            _credential_card(supplement),
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


def _challenger_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    visibility_count = len(supplement.artifact_runtime_visibility)
    return DashboardCard(
        key="complete_control_shadow_challengers",
        label="Shadow Challengers",
        value=(
            f"ml={_artifact_label(supplement.shadow_ml_challenger_artifact)} / "
            f"regime={_artifact_label(supplement.shadow_regime_detector_challenger_artifact)}"
        ),
        status="info",
        detail=(
            f"ml_hash={_artifact_hash(supplement.shadow_ml_challenger_artifact)} / "
            f"regime_hash={_artifact_hash(supplement.shadow_regime_detector_challenger_artifact)} / "
            f"visibility={visibility_count} / mode=shadow_only_non_influential"
        ),
    )


def _comparison_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    ml_status = _comparison_status_for_manifest(
        supplement.shadow_ml_challenger_artifact,
        comparisons=supplement.artifact_comparisons,
    )
    regime_status = _comparison_status_for_manifest(
        supplement.shadow_regime_detector_challenger_artifact,
        comparisons=supplement.artifact_comparisons,
    )
    return DashboardCard(
        key="complete_control_artifact_compare",
        label="Compare Status",
        value=f"ml={ml_status} / regime={regime_status}",
        status="info" if supplement.artifact_comparisons else "planned",
        detail=_join(
            tuple(
                (
                    f"{comparison.challenger_artifact_id}:"
                    f"{comparison.comparison_status}:"
                    f"{'ref' if comparison.evidence_ref else 'no_ref'}:"
                    f"halal={comparison.halal_eligible_event_count}/"
                    f"{comparison.halal_excluded_event_count}"
                )
                for comparison in supplement.artifact_comparisons
            ),
            empty="No champion/challenger evidence attached",
        ),
    )


def _verdict_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    verdict = supplement.artifact_verdict_bundle
    return DashboardCard(
        key="complete_control_shadow_verdict_bundle",
        label="Shadow Verdict",
        value=(
            "not_available"
            if verdict is None
            else f"{verdict.overall_verdict} / {verdict.operator_recommendation}"
        ),
        status=(
            "planned"
            if verdict is None
            else _verdict_status(verdict.overall_verdict)
        ),
        detail=(
            "No daily challenger verdict bundle attached"
            if verdict is None
            else (
                f"ready={verdict.ready_family_count} / "
                f"invalid={verdict.invalid_family_count} / "
                f"runtime_inputs={verdict.runtime_inputs_missing_family_count} / "
                f"blocked={verdict.sharia_blocked_family_count} / "
                f"ref={verdict.evidence_ref or 'none'}"
            )
        ),
    )


def _credential_card(supplement: CompleteControlPlaneSupplement) -> DashboardCard:
    active_profile = supplement.active_binance_profile_id or "none"
    environment = supplement.active_binance_environment or "none"
    validation_status = supplement.binance_credential_validation_status or "unknown"
    return DashboardCard(
        key="complete_control_binance_credentials",
        label="Binance Credentials",
        value=f"profile={active_profile} / env={environment}",
        status="healthy" if validation_status == "validated" else "warning",
        detail=(
            f"validation={validation_status} / "
            f"inventory_count={supplement.credential_inventory_count}"
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


def _comparison_status_for_manifest(
    manifest: DashboardArtifactTransferManifest | None,
    *,
    comparisons: tuple[ArtifactComparisonProjection, ...],
) -> str:
    if manifest is None:
        return "none"
    for comparison in comparisons:
        if comparison.challenger_artifact_id == manifest.artifact_id:
            return comparison.comparison_status
    return "pending"


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


def _verdict_status(verdict: str) -> str:
    if verdict == "shadow_validated":
        return "healthy"
    if verdict in {"shadow_inconclusive", "shadow_runtime_inputs_missing"}:
        return "warning"
    if verdict in {"sharia_scope_blocked", "invalid_evidence"}:
        return "critical"
    return "info"


__all__ = ["build_complete_control_plane_section"]
