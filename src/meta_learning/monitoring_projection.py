"""Adapters from Build-9X governed bundles to monitoring projections."""

from __future__ import annotations

import importlib

from meta_learning.contracts import LearningCapacitySnapshot, MetaLearningReviewBundle
from meta_learning.enums import CandidateGovernanceStage, LearningBacklogState


_REPLAY_READY_STAGES = {
    CandidateGovernanceStage.READY_FOR_REPLAY,
    CandidateGovernanceStage.REPLAY_RUNNING,
    CandidateGovernanceStage.REPLAY_PASSED,
    CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
}


def _resolve_capacity_snapshot(
    snapshot: LearningCapacitySnapshot | None,
) -> LearningCapacitySnapshot:
    return snapshot or LearningCapacitySnapshot()


def _build9x_projection_type():
    return importlib.import_module("monitoring.contracts").Build9XProjection


def _status_from_bundle(
    bundle: MetaLearningReviewBundle,
    capacity_snapshot: LearningCapacitySnapshot,
) -> str:
    material_diagnostics = tuple(
        diagnostic for diagnostic in bundle.diagnostics if diagnostic.category != "no_issue"
    )
    if bundle.merge_gate_report is not None and not bundle.merge_gate_report.all_passed:
        return "critical"
    if (
        capacity_snapshot.review_blocked_due_to_incomplete_data
        or capacity_snapshot.export_failures_total > 0
        or capacity_snapshot.log_loss_total > 0
    ):
        return "critical"
    if material_diagnostics or bundle.replay_bundles or capacity_snapshot.backlog_state != LearningBacklogState.NORMAL:
        return "warning"
    return "info"


def build_build9x_projection(
    bundle: MetaLearningReviewBundle,
) -> object:
    """Project a governed Build-9X review bundle into Build-10 supervision fields."""

    capacity_snapshot = _resolve_capacity_snapshot(bundle.capacity_snapshot)
    replay_candidate_count = sum(
        candidate.governance_stage in _REPLAY_READY_STAGES for candidate in bundle.candidates
    )
    mapped_hypotheses = tuple(
        hypothesis for hypothesis in bundle.hypotheses if hypothesis.target_component
    )
    latest_hypothesis = mapped_hypotheses[-1] if mapped_hypotheses else None
    expected_replay_evidence = tuple(
        dict.fromkeys(
            evidence
            for hypothesis in mapped_hypotheses
            for evidence in hypothesis.expected_replay_evidence
        )
    )
    expected_shadow_evidence = tuple(
        dict.fromkeys(
            evidence
            for hypothesis in mapped_hypotheses
            for evidence in hypothesis.expected_shadow_evidence
        )
    )
    diagnostics_summary = bundle.breakdown_report.summary
    if capacity_snapshot.review_blocked_due_to_incomplete_data and capacity_snapshot.blocking_reasons:
        diagnostics_summary = (
            f"{diagnostics_summary} / blocked: {', '.join(capacity_snapshot.blocking_reasons)}"
        )
    if bundle.merge_gate_report is not None and not bundle.merge_gate_report.all_passed:
        failed_gates = tuple(
            gate.gate_name.value
            for gate in bundle.merge_gate_report.gates
            if not gate.passed
        )
        diagnostics_summary = (
            f"{diagnostics_summary} / merge_gates_failed: {', '.join(failed_gates)}"
        )

    return _build9x_projection_type()(
        status=_status_from_bundle(bundle, capacity_snapshot),
        diagnostics_count=len(bundle.diagnostics),
        diagnostics_summary=diagnostics_summary,
        open_hypotheses=sum(hypothesis.status != "rejected" for hypothesis in bundle.hypotheses),
        total_hypotheses=len(bundle.hypotheses),
        near_miss_count=sum(diagnostic.category == "near_miss" for diagnostic in bundle.diagnostics),
        replay_candidate_count=replay_candidate_count,
        memory_record_count=1 if bundle.memory_record.record_id or bundle.memory_record.summary else 0,
        latest_memory_summary=bundle.memory_record.rejection_reason or bundle.memory_record.summary,
        enrichment_hypothesis_count=len(mapped_hypotheses),
        latest_enrichment_target=(
            latest_hypothesis.target_component if latest_hypothesis is not None else ""
        ),
        latest_enrichment_signal_family=(
            latest_hypothesis.signal_family if latest_hypothesis is not None else ""
        ),
        expected_replay_evidence_count=len(expected_replay_evidence),
        expected_shadow_evidence_count=len(expected_shadow_evidence),
        enrichment_summary=(
            f"{latest_hypothesis.category} -> {latest_hypothesis.target_component}"
            if latest_hypothesis is not None
            else "No enrichment hypothesis mapped"
        ),
        review_export_ready=(
            bool(bundle.review_export.export_ref)
            and not bundle.review_export.review_blocked_due_to_incomplete_data
            and (bundle.merge_gate_report.all_passed if bundle.merge_gate_report is not None else True)
        ),
        review_export_ref=bundle.review_export.export_ref,
        learning_queue_depth=capacity_snapshot.queue_depth,
        learning_queue_oldest_age_ms=capacity_snapshot.queue_oldest_age_ms,
        learning_worker_cpu_pct=capacity_snapshot.worker_cpu_pct,
        learning_worker_rss_mb=capacity_snapshot.worker_rss_mb,
        learning_write_latency_ms=capacity_snapshot.write_latency_ms,
        learning_export_failures_total=capacity_snapshot.export_failures_total,
        learning_log_loss_total=capacity_snapshot.log_loss_total,
        learning_unprocessed_items_count=capacity_snapshot.unprocessed_items_count,
        learning_backlog_state=capacity_snapshot.backlog_state.value,
        learning_capture_mode=capacity_snapshot.capture_mode.value,
        learning_observability_reduced=capacity_snapshot.observability_reduced,
        learning_backpressure_active=capacity_snapshot.backpressure_active,
        review_blocked_due_to_incomplete_data=capacity_snapshot.review_blocked_due_to_incomplete_data,
        promotion_blocked_due_to_incomplete_data=capacity_snapshot.promotion_blocked_due_to_incomplete_data,
        learning_capacity_summary=(
            f"queue={capacity_snapshot.queue_depth} / "
            f"backlog={capacity_snapshot.backlog_state.value} / "
            f"mode={capacity_snapshot.capture_mode.value}"
        ),
    )


__all__ = [
    "build_build9x_projection",
]
