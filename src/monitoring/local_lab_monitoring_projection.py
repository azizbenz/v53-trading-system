"""Compact future-dashboard projection for Local IA Lab packaging and dry-run handoff."""

from __future__ import annotations

from pydantic import BaseModel, Field

from monitoring.contracts import ProjectionStatus


class LocalLabMonitoringProjection(BaseModel, frozen=True):
    """Audit-ready Local IA Lab monitoring summary without coupling to UI."""

    status: ProjectionStatus
    correlation_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    runtime_mode: str = Field(default="local_replay", min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    detail: str = Field(..., min_length=1)
    review_ready: bool = False
    trade_loss_attribution_ready: bool = False
    walk_forward_review_ready: bool = False
    artifact_ablation_ready: bool = False
    artifact_proof_ready: bool = False
    edge_calibration_ready: bool = False
    release_ready_for_shadow: bool = False
    ready_for_shadow_import_dry_run: bool = False
    release_status: str = Field(..., min_length=1)
    bridge_status: str = Field(..., min_length=1)
    promotion_readiness_status: str = Field(..., min_length=1)
    activation_stage: str = Field(..., min_length=1)
    normalized_promotion_state: str = Field(..., min_length=1)
    review_state: str = Field(..., min_length=1)
    release_gate_status: str = Field(..., min_length=1)
    semantic_status: str = Field(..., min_length=1)
    scope_count: int = Field(default=0, ge=0)
    scope_ready_count: int = Field(default=0, ge=0)
    scope_blocked_count: int = Field(default=0, ge=0)
    release_scope_ready_count: int = Field(default=0, ge=0)
    release_scope_blocked_count: int = Field(default=0, ge=0)
    loss_surrogate_status: str = Field(default="not_evaluated", min_length=1)
    loss_surrogate_ready: bool = False
    loss_surrogate_scope_count: int = Field(default=0, ge=0)
    loss_surrogate_top_scope_slug: str = ""
    loss_surrogate_top_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    calibration_methods_stationarity_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_stationarity_pass: bool | None = None
    execution_review_status: str = Field(default="not_evaluated", min_length=1)
    execution_review_ready: bool = False
    execution_ready_threshold_count: int = Field(default=0, ge=0)
    execution_partial_threshold_count: int = Field(default=0, ge=0)
    execution_blocked_threshold_count: int = Field(default=0, ge=0)
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_correction: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_family_count: int = Field(default=0, ge=0)
    calibration_normalized_report_status: str = Field(default="not_evaluated", min_length=1)
    calibration_normalized_report_ready: bool = False
    calibration_normalized_threshold_count: int = Field(default=0, ge=0)
    tail_risk_review_status: str = Field(default="not_evaluated", min_length=1)
    tail_risk_review_ready: bool = False
    tail_risk_ready_breaker_count: int = Field(default=0, ge=0)
    tail_risk_partial_breaker_count: int = Field(default=0, ge=0)
    tail_risk_blocked_breaker_count: int = Field(default=0, ge=0)
    research_priority_status: str = Field(default="not_evaluated", min_length=1)
    research_priority_scope_count: int = Field(default=0, ge=0)
    research_priority_top_scope_slug: str = ""
    research_priority_top_score: float = Field(default=0.0, ge=0.0, le=1.0)
    replay_candidate_queue_status: str = Field(default="not_evaluated", min_length=1)
    replay_candidate_count: int = Field(default=0, ge=0)
    replay_candidate_ready_count: int = Field(default=0, ge=0)
    replay_candidate_top_scope_slug: str = ""
    replay_ticket_index_status: str = Field(default="not_evaluated", min_length=1)
    replay_ticket_count: int = Field(default=0, ge=0)
    replay_ticket_ready_count: int = Field(default=0, ge=0)
    replay_ticket_top_scope_slug: str = ""
    replay_dispatch_plan_status: str = Field(default="not_evaluated", min_length=1)
    replay_dispatch_ready_count: int = Field(default=0, ge=0)
    replay_dispatch_blocked_count: int = Field(default=0, ge=0)
    replay_dispatch_top_ticket_id: str = ""
    blocking_reasons: tuple[str, ...] = ()
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_reasons: tuple[str, ...] = ()
    bridge_blocking_reasons: tuple[str, ...] = ()
    scope_matrix_path: str | None = None
    artifact_release_candidate_path: str | None = None
    artifact_import_dry_run_bridge_path: str | None = None
    artifact_promotion_readiness_summary_path: str | None = None
    local_lab_loss_surrogate_path: str | None = None
    local_lab_calibration_methods_review_path: str | None = None
    local_lab_execution_review_path: str | None = None
    local_lab_execution_runtime_projection_path: str | None = None
    local_lab_multiple_testing_review_path: str | None = None
    local_lab_tail_risk_review_path: str | None = None
    local_lab_calibration_normalized_report_path: str | None = None
    local_lab_research_priority_path: str | None = None
    local_lab_replay_candidate_queue_path: str | None = None
    local_lab_replay_ticket_index_path: str | None = None
    local_lab_replay_dispatch_plan_path: str | None = None
    local_lab_replay_workflow_manifest_path: str | None = None
    local_lab_monitoring_bundle_manifest_path: str | None = None


def _dedupe(items: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _build_detail(
    *,
    status: ProjectionStatus,
    release_ready_for_shadow: bool,
    bridge_status: str,
    promotion_readiness_status: str,
    release_scope_ready_count: int,
    scope_count: int,
) -> str:
    if status == "healthy":
        return (
            "Local IA Lab dry-run handoff is ready for SHADOW import review "
            f"(scopes={release_scope_ready_count}/{scope_count})."
        )
    if release_ready_for_shadow:
        return (
            "Local IA Lab release candidate is proof-backed locally, but the governed dry-run "
            f"handoff is still pending ({bridge_status})."
        )
    if status == "critical":
        return "Local IA Lab core analysis outputs are incomplete or missing."
    return (
        "Local IA Lab remains local-only pending proof, walk-forward, or recalibration closure "
        f"({promotion_readiness_status})."
    )


def _resolve_projection_status(
    *,
    review_ready: bool,
    trade_loss_attribution_ready: bool,
    edge_calibration_ready: bool,
    ready_for_shadow_import_dry_run: bool,
    release_ready_for_shadow: bool,
    artifact_proof_ready: bool,
    walk_forward_review_ready: bool,
    artifact_ablation_ready: bool,
    release_blocking_reasons: tuple[str, ...] | list[str],
    bridge_blocking_reasons: tuple[str, ...] | list[str],
) -> ProjectionStatus:
    core_outputs_ready = review_ready and trade_loss_attribution_ready and edge_calibration_ready
    if ready_for_shadow_import_dry_run:
        return "healthy"
    if not core_outputs_ready:
        return "critical"
    if (
        release_ready_for_shadow
        or artifact_proof_ready
        or walk_forward_review_ready
        or artifact_ablation_ready
        or release_blocking_reasons
        or bridge_blocking_reasons
    ):
        return "warning"
    return "info"


def _build_projection_core_payload(
    *,
    status: ProjectionStatus,
    correlation_id: str,
    run_id: str,
    export_dir: str,
    dataset_manifest_id: str,
    artifact_id: str,
    selected_pair: str | None,
    selected_engine_id: str | None,
    review_ready: bool,
    trade_loss_attribution_ready: bool,
    walk_forward_review_ready: bool,
    artifact_ablation_ready: bool,
    artifact_proof_ready: bool,
    edge_calibration_ready: bool,
    release_ready_for_shadow: bool,
    ready_for_shadow_import_dry_run: bool,
    release_status: str,
    bridge_status: str,
    promotion_readiness_status: str,
    activation_stage: str,
    normalized_promotion_state: str,
    review_state: str,
    release_gate_status: str,
    semantic_status: str,
    scope_count: int,
    scope_ready_count: int,
    scope_blocked_count: int,
    release_scope_ready_count: int,
    release_scope_blocked_count: int,
    blocking_reasons: tuple[str, ...],
) -> dict[str, object]:
    return {
        "status": status,
        "correlation_id": correlation_id,
        "run_id": run_id,
        "export_dir": export_dir,
        "dataset_manifest_id": dataset_manifest_id,
        "artifact_id": artifact_id,
        "selected_pair": selected_pair,
        "selected_engine_id": selected_engine_id,
        "detail": _build_detail(
            status=status,
            release_ready_for_shadow=release_ready_for_shadow,
            bridge_status=bridge_status,
            promotion_readiness_status=promotion_readiness_status,
            release_scope_ready_count=release_scope_ready_count,
            scope_count=scope_count,
        ),
        "review_ready": review_ready,
        "trade_loss_attribution_ready": trade_loss_attribution_ready,
        "walk_forward_review_ready": walk_forward_review_ready,
        "artifact_ablation_ready": artifact_ablation_ready,
        "artifact_proof_ready": artifact_proof_ready,
        "edge_calibration_ready": edge_calibration_ready,
        "release_ready_for_shadow": release_ready_for_shadow,
        "ready_for_shadow_import_dry_run": ready_for_shadow_import_dry_run,
        "release_status": release_status,
        "bridge_status": bridge_status,
        "promotion_readiness_status": promotion_readiness_status,
        "activation_stage": activation_stage,
        "normalized_promotion_state": normalized_promotion_state,
        "review_state": review_state,
        "release_gate_status": release_gate_status,
        "semantic_status": semantic_status,
        "scope_count": scope_count,
        "scope_ready_count": scope_ready_count,
        "scope_blocked_count": scope_blocked_count,
        "release_scope_ready_count": release_scope_ready_count,
        "release_scope_blocked_count": release_scope_blocked_count,
        "blocking_reasons": blocking_reasons,
    }


def _build_projection_calibration_payload(
    *,
    loss_surrogate_status: str,
    loss_surrogate_ready: bool,
    loss_surrogate_scope_count: int,
    loss_surrogate_top_scope_slug: str,
    loss_surrogate_top_probability: float,
    calibration_methods_review_status: str,
    calibration_methods_review_ready: bool,
    calibration_methods_dsr_pass: bool | None,
    calibration_methods_walk_forward_plan_ready: bool,
    calibration_methods_stationarity_status: str,
    calibration_methods_stationarity_pass: bool | None,
    execution_review_status: str,
    execution_review_ready: bool,
    execution_ready_threshold_count: int,
    execution_partial_threshold_count: int,
    execution_blocked_threshold_count: int,
    multiple_testing_review_status: str,
    multiple_testing_review_ready: bool,
    multiple_testing_correction_required: bool,
    multiple_testing_correction: str,
    multiple_testing_family_count: int,
    calibration_normalized_report_status: str,
    calibration_normalized_report_ready: bool,
    calibration_normalized_threshold_count: int,
    tail_risk_review_status: str,
    tail_risk_review_ready: bool,
    tail_risk_ready_breaker_count: int,
    tail_risk_partial_breaker_count: int,
    tail_risk_blocked_breaker_count: int,
) -> dict[str, object]:
    return {
        "loss_surrogate_status": loss_surrogate_status,
        "loss_surrogate_ready": loss_surrogate_ready,
        "loss_surrogate_scope_count": loss_surrogate_scope_count,
        "loss_surrogate_top_scope_slug": loss_surrogate_top_scope_slug,
        "loss_surrogate_top_probability": loss_surrogate_top_probability,
        "calibration_methods_review_status": calibration_methods_review_status,
        "calibration_methods_review_ready": calibration_methods_review_ready,
        "calibration_methods_dsr_pass": calibration_methods_dsr_pass,
        "calibration_methods_walk_forward_plan_ready": calibration_methods_walk_forward_plan_ready,
        "calibration_methods_stationarity_status": calibration_methods_stationarity_status,
        "calibration_methods_stationarity_pass": calibration_methods_stationarity_pass,
        "execution_review_status": execution_review_status,
        "execution_review_ready": execution_review_ready,
        "execution_ready_threshold_count": execution_ready_threshold_count,
        "execution_partial_threshold_count": execution_partial_threshold_count,
        "execution_blocked_threshold_count": execution_blocked_threshold_count,
        "multiple_testing_review_status": multiple_testing_review_status,
        "multiple_testing_review_ready": multiple_testing_review_ready,
        "multiple_testing_correction_required": multiple_testing_correction_required,
        "multiple_testing_correction": multiple_testing_correction,
        "multiple_testing_family_count": multiple_testing_family_count,
        "calibration_normalized_report_status": calibration_normalized_report_status,
        "calibration_normalized_report_ready": calibration_normalized_report_ready,
        "calibration_normalized_threshold_count": calibration_normalized_threshold_count,
        "tail_risk_review_status": tail_risk_review_status,
        "tail_risk_review_ready": tail_risk_review_ready,
        "tail_risk_ready_breaker_count": tail_risk_ready_breaker_count,
        "tail_risk_partial_breaker_count": tail_risk_partial_breaker_count,
        "tail_risk_blocked_breaker_count": tail_risk_blocked_breaker_count,
    }


def _build_projection_replay_payload(
    *,
    research_priority_status: str,
    research_priority_scope_count: int,
    research_priority_top_scope_slug: str,
    research_priority_top_score: float,
    replay_candidate_queue_status: str,
    replay_candidate_count: int,
    replay_candidate_ready_count: int,
    replay_candidate_top_scope_slug: str,
    replay_ticket_index_status: str,
    replay_ticket_count: int,
    replay_ticket_ready_count: int,
    replay_ticket_top_scope_slug: str,
    replay_dispatch_plan_status: str,
    replay_dispatch_ready_count: int,
    replay_dispatch_blocked_count: int,
    replay_dispatch_top_ticket_id: str,
    artifact_proof_validation_reasons: tuple[str, ...] | list[str],
    recalibration_blocking_reasons: tuple[str, ...] | list[str],
    release_gate_reasons: tuple[str, ...] | list[str],
    bridge_blocking_reasons: tuple[str, ...] | list[str],
) -> dict[str, object]:
    return {
        "research_priority_status": research_priority_status,
        "research_priority_scope_count": research_priority_scope_count,
        "research_priority_top_scope_slug": research_priority_top_scope_slug,
        "research_priority_top_score": research_priority_top_score,
        "replay_candidate_queue_status": replay_candidate_queue_status,
        "replay_candidate_count": replay_candidate_count,
        "replay_candidate_ready_count": replay_candidate_ready_count,
        "replay_candidate_top_scope_slug": replay_candidate_top_scope_slug,
        "replay_ticket_index_status": replay_ticket_index_status,
        "replay_ticket_count": replay_ticket_count,
        "replay_ticket_ready_count": replay_ticket_ready_count,
        "replay_ticket_top_scope_slug": replay_ticket_top_scope_slug,
        "replay_dispatch_plan_status": replay_dispatch_plan_status,
        "replay_dispatch_ready_count": replay_dispatch_ready_count,
        "replay_dispatch_blocked_count": replay_dispatch_blocked_count,
        "replay_dispatch_top_ticket_id": replay_dispatch_top_ticket_id,
        "artifact_proof_validation_reasons": tuple(artifact_proof_validation_reasons),
        "recalibration_blocking_reasons": tuple(recalibration_blocking_reasons),
        "release_gate_reasons": tuple(release_gate_reasons),
        "bridge_blocking_reasons": tuple(bridge_blocking_reasons),
    }


def _build_projection_path_payload(
    *,
    scope_matrix_path: str | None,
    artifact_release_candidate_path: str | None,
    artifact_import_dry_run_bridge_path: str | None,
    artifact_promotion_readiness_summary_path: str | None,
    local_lab_loss_surrogate_path: str | None,
    local_lab_calibration_methods_review_path: str | None,
    local_lab_execution_review_path: str | None,
    local_lab_execution_runtime_projection_path: str | None,
    local_lab_multiple_testing_review_path: str | None,
    local_lab_tail_risk_review_path: str | None,
    local_lab_calibration_normalized_report_path: str | None,
    local_lab_research_priority_path: str | None,
    local_lab_replay_candidate_queue_path: str | None,
    local_lab_replay_ticket_index_path: str | None,
    local_lab_replay_dispatch_plan_path: str | None,
    local_lab_replay_workflow_manifest_path: str | None,
    local_lab_monitoring_bundle_manifest_path: str | None,
) -> dict[str, object]:
    return {
        "scope_matrix_path": scope_matrix_path,
        "artifact_release_candidate_path": artifact_release_candidate_path,
        "artifact_import_dry_run_bridge_path": artifact_import_dry_run_bridge_path,
        "artifact_promotion_readiness_summary_path": artifact_promotion_readiness_summary_path,
        "local_lab_loss_surrogate_path": local_lab_loss_surrogate_path,
        "local_lab_calibration_methods_review_path": local_lab_calibration_methods_review_path,
        "local_lab_execution_review_path": local_lab_execution_review_path,
        "local_lab_execution_runtime_projection_path": local_lab_execution_runtime_projection_path,
        "local_lab_multiple_testing_review_path": local_lab_multiple_testing_review_path,
        "local_lab_tail_risk_review_path": local_lab_tail_risk_review_path,
        "local_lab_calibration_normalized_report_path": local_lab_calibration_normalized_report_path,
        "local_lab_research_priority_path": local_lab_research_priority_path,
        "local_lab_replay_candidate_queue_path": local_lab_replay_candidate_queue_path,
        "local_lab_replay_ticket_index_path": local_lab_replay_ticket_index_path,
        "local_lab_replay_dispatch_plan_path": local_lab_replay_dispatch_plan_path,
        "local_lab_replay_workflow_manifest_path": local_lab_replay_workflow_manifest_path,
        "local_lab_monitoring_bundle_manifest_path": local_lab_monitoring_bundle_manifest_path,
    }


def build_local_lab_monitoring_projection(
    *, correlation_id: str, run_id: str, export_dir: str, dataset_manifest_id: str, artifact_id: str, selected_pair: str | None, selected_engine_id: str | None,
    review_ready: bool, trade_loss_attribution_ready: bool, walk_forward_review_ready: bool, artifact_ablation_ready: bool, artifact_proof_ready: bool, edge_calibration_ready: bool,
    scope_count: int, scope_ready_count: int, scope_blocked_count: int, release_scope_ready_count: int, release_scope_blocked_count: int, release_ready_for_shadow: bool, release_status: str,
    release_blocking_reasons: tuple[str, ...] | list[str] = (), artifact_proof_validation_reasons: tuple[str, ...] | list[str] = (), recalibration_blocking_reasons: tuple[str, ...] | list[str] = (),
    bridge_status: str = "not_built", ready_for_shadow_import_dry_run: bool = False, bridge_blocking_reasons: tuple[str, ...] | list[str] = (), release_gate_status: str = "not_evaluated",
    release_gate_reasons: tuple[str, ...] | list[str] = (), semantic_status: str = "not_evaluated", promotion_readiness_status: str = "not_evaluated", activation_stage: str = "replay_only", normalized_promotion_state: str = "replay_only", review_state: str = "needs_revision",
    loss_surrogate_status: str = "not_evaluated", loss_surrogate_ready: bool = False, loss_surrogate_scope_count: int = 0, loss_surrogate_top_scope_slug: str = "", loss_surrogate_top_probability: float = 0.0,
    calibration_methods_review_status: str = "not_evaluated", calibration_methods_review_ready: bool = False, calibration_methods_dsr_pass: bool | None = None, calibration_methods_walk_forward_plan_ready: bool = False, calibration_methods_stationarity_status: str = "not_evaluated", calibration_methods_stationarity_pass: bool | None = None,
    execution_review_status: str = "not_evaluated", execution_review_ready: bool = False, execution_ready_threshold_count: int = 0, execution_partial_threshold_count: int = 0, execution_blocked_threshold_count: int = 0,
    multiple_testing_review_status: str = "not_evaluated", multiple_testing_review_ready: bool = False, multiple_testing_correction_required: bool = False, multiple_testing_correction: str = "not_evaluated", multiple_testing_family_count: int = 0,
    calibration_normalized_report_status: str = "not_evaluated", calibration_normalized_report_ready: bool = False, calibration_normalized_threshold_count: int = 0, tail_risk_review_status: str = "not_evaluated", tail_risk_review_ready: bool = False, tail_risk_ready_breaker_count: int = 0, tail_risk_partial_breaker_count: int = 0, tail_risk_blocked_breaker_count: int = 0,
    research_priority_status: str = "not_evaluated", research_priority_scope_count: int = 0, research_priority_top_scope_slug: str = "", research_priority_top_score: float = 0.0,
    replay_candidate_queue_status: str = "not_evaluated", replay_candidate_count: int = 0, replay_candidate_ready_count: int = 0, replay_candidate_top_scope_slug: str = "", replay_ticket_index_status: str = "not_evaluated", replay_ticket_count: int = 0, replay_ticket_ready_count: int = 0, replay_ticket_top_scope_slug: str = "",
    replay_dispatch_plan_status: str = "not_evaluated", replay_dispatch_ready_count: int = 0, replay_dispatch_blocked_count: int = 0, replay_dispatch_top_ticket_id: str = "",
    scope_matrix_path: str | None = None, artifact_release_candidate_path: str | None = None, artifact_import_dry_run_bridge_path: str | None = None, artifact_promotion_readiness_summary_path: str | None = None,
    local_lab_loss_surrogate_path: str | None = None, local_lab_calibration_methods_review_path: str | None = None, local_lab_execution_review_path: str | None = None, local_lab_execution_runtime_projection_path: str | None = None,
    local_lab_multiple_testing_review_path: str | None = None, local_lab_tail_risk_review_path: str | None = None, local_lab_calibration_normalized_report_path: str | None = None, local_lab_research_priority_path: str | None = None,
    local_lab_replay_candidate_queue_path: str | None = None, local_lab_replay_ticket_index_path: str | None = None, local_lab_replay_dispatch_plan_path: str | None = None, local_lab_replay_workflow_manifest_path: str | None = None, local_lab_monitoring_bundle_manifest_path: str | None = None,
) -> LocalLabMonitoringProjection:
    """Normalize the current Local IA Lab packaging state into one monitoring sidecar."""

    status = _resolve_projection_status(
        review_ready=review_ready, trade_loss_attribution_ready=trade_loss_attribution_ready, edge_calibration_ready=edge_calibration_ready,
        ready_for_shadow_import_dry_run=ready_for_shadow_import_dry_run, release_ready_for_shadow=release_ready_for_shadow,
        artifact_proof_ready=artifact_proof_ready, walk_forward_review_ready=walk_forward_review_ready, artifact_ablation_ready=artifact_ablation_ready,
        release_blocking_reasons=release_blocking_reasons, bridge_blocking_reasons=bridge_blocking_reasons,
    )
    blocking_reasons = _dedupe([*release_blocking_reasons, *bridge_blocking_reasons])
    projection_payload = {
        **_build_projection_core_payload(
            status=status, correlation_id=correlation_id, run_id=run_id, export_dir=export_dir, dataset_manifest_id=dataset_manifest_id, artifact_id=artifact_id,
            selected_pair=selected_pair, selected_engine_id=selected_engine_id, review_ready=review_ready, trade_loss_attribution_ready=trade_loss_attribution_ready,
            walk_forward_review_ready=walk_forward_review_ready, artifact_ablation_ready=artifact_ablation_ready, artifact_proof_ready=artifact_proof_ready,
            edge_calibration_ready=edge_calibration_ready, release_ready_for_shadow=release_ready_for_shadow, ready_for_shadow_import_dry_run=ready_for_shadow_import_dry_run,
            release_status=release_status, bridge_status=bridge_status, promotion_readiness_status=promotion_readiness_status, activation_stage=activation_stage,
            normalized_promotion_state=normalized_promotion_state, review_state=review_state, release_gate_status=release_gate_status, semantic_status=semantic_status,
            scope_count=scope_count, scope_ready_count=scope_ready_count, scope_blocked_count=scope_blocked_count,
            release_scope_ready_count=release_scope_ready_count, release_scope_blocked_count=release_scope_blocked_count, blocking_reasons=blocking_reasons,
        ),
        **_build_projection_calibration_payload(
            loss_surrogate_status=loss_surrogate_status, loss_surrogate_ready=loss_surrogate_ready, loss_surrogate_scope_count=loss_surrogate_scope_count,
            loss_surrogate_top_scope_slug=loss_surrogate_top_scope_slug, loss_surrogate_top_probability=loss_surrogate_top_probability,
            calibration_methods_review_status=calibration_methods_review_status, calibration_methods_review_ready=calibration_methods_review_ready,
            calibration_methods_dsr_pass=calibration_methods_dsr_pass, calibration_methods_walk_forward_plan_ready=calibration_methods_walk_forward_plan_ready,
            calibration_methods_stationarity_status=calibration_methods_stationarity_status, calibration_methods_stationarity_pass=calibration_methods_stationarity_pass,
            execution_review_status=execution_review_status, execution_review_ready=execution_review_ready, execution_ready_threshold_count=execution_ready_threshold_count,
            execution_partial_threshold_count=execution_partial_threshold_count, execution_blocked_threshold_count=execution_blocked_threshold_count,
            multiple_testing_review_status=multiple_testing_review_status, multiple_testing_review_ready=multiple_testing_review_ready,
            multiple_testing_correction_required=multiple_testing_correction_required, multiple_testing_correction=multiple_testing_correction,
            multiple_testing_family_count=multiple_testing_family_count, calibration_normalized_report_status=calibration_normalized_report_status,
            calibration_normalized_report_ready=calibration_normalized_report_ready, calibration_normalized_threshold_count=calibration_normalized_threshold_count,
            tail_risk_review_status=tail_risk_review_status, tail_risk_review_ready=tail_risk_review_ready, tail_risk_ready_breaker_count=tail_risk_ready_breaker_count,
            tail_risk_partial_breaker_count=tail_risk_partial_breaker_count, tail_risk_blocked_breaker_count=tail_risk_blocked_breaker_count,
        ),
        **_build_projection_replay_payload(
            research_priority_status=research_priority_status, research_priority_scope_count=research_priority_scope_count,
            research_priority_top_scope_slug=research_priority_top_scope_slug, research_priority_top_score=research_priority_top_score,
            replay_candidate_queue_status=replay_candidate_queue_status, replay_candidate_count=replay_candidate_count,
            replay_candidate_ready_count=replay_candidate_ready_count, replay_candidate_top_scope_slug=replay_candidate_top_scope_slug,
            replay_ticket_index_status=replay_ticket_index_status, replay_ticket_count=replay_ticket_count,
            replay_ticket_ready_count=replay_ticket_ready_count, replay_ticket_top_scope_slug=replay_ticket_top_scope_slug,
            replay_dispatch_plan_status=replay_dispatch_plan_status, replay_dispatch_ready_count=replay_dispatch_ready_count,
            replay_dispatch_blocked_count=replay_dispatch_blocked_count, replay_dispatch_top_ticket_id=replay_dispatch_top_ticket_id,
            artifact_proof_validation_reasons=artifact_proof_validation_reasons, recalibration_blocking_reasons=recalibration_blocking_reasons,
            release_gate_reasons=release_gate_reasons, bridge_blocking_reasons=bridge_blocking_reasons,
        ),
        **_build_projection_path_payload(
            scope_matrix_path=scope_matrix_path, artifact_release_candidate_path=artifact_release_candidate_path,
            artifact_import_dry_run_bridge_path=artifact_import_dry_run_bridge_path, artifact_promotion_readiness_summary_path=artifact_promotion_readiness_summary_path,
            local_lab_loss_surrogate_path=local_lab_loss_surrogate_path, local_lab_calibration_methods_review_path=local_lab_calibration_methods_review_path,
            local_lab_execution_review_path=local_lab_execution_review_path, local_lab_execution_runtime_projection_path=local_lab_execution_runtime_projection_path,
            local_lab_multiple_testing_review_path=local_lab_multiple_testing_review_path, local_lab_tail_risk_review_path=local_lab_tail_risk_review_path,
            local_lab_calibration_normalized_report_path=local_lab_calibration_normalized_report_path, local_lab_research_priority_path=local_lab_research_priority_path,
            local_lab_replay_candidate_queue_path=local_lab_replay_candidate_queue_path, local_lab_replay_ticket_index_path=local_lab_replay_ticket_index_path,
            local_lab_replay_dispatch_plan_path=local_lab_replay_dispatch_plan_path, local_lab_replay_workflow_manifest_path=local_lab_replay_workflow_manifest_path,
            local_lab_monitoring_bundle_manifest_path=local_lab_monitoring_bundle_manifest_path,
        ),
    }
    return LocalLabMonitoringProjection(**projection_payload)


__all__ = [
    "LocalLabMonitoringProjection",
    "build_local_lab_monitoring_projection",
]
