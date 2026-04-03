"""Explicit merge-gate evaluators for the governed Build-9X layer."""

from __future__ import annotations

from pathlib import Path

from interface_contracts import PromotionState, ReviewState, RuntimeMode

from meta_learning.contracts import LearningCapacitySnapshot, MetaLearningReviewBundle
from meta_learning.enums import CandidateGovernanceStage, LearningBacklogState
from meta_learning.merge_gate_contracts import (
    Build9XMergeGateName,
    Build9XMergeGateReport,
    Build9XMergeGateResult,
)
from meta_learning.monitoring_projection import build_build9x_projection
from meta_learning.persistence_store import (
    AppendOnlyMetaLearningStore,
    _CANDIDATE_FILE,
    _DIAGNOSTIC_FILE,
    _EVENT_FILE,
    _EXPORT_BUNDLE_FILE,
    _HYPOTHESIS_FILE,
    _MEMORY_FILE,
    _REVIEW_FILE,
)


def _gate_log_key(gate_name: Build9XMergeGateName) -> str:
    return f"build9x.merge_gate.{gate_name.value.lower()}"


def _build_gate_result(
    gate_name: Build9XMergeGateName,
    *,
    blocking_reasons: tuple[str, ...],
    summary_ok: str,
    summary_fail: str,
    evidence_refs: tuple[str, ...] = (),
) -> Build9XMergeGateResult:
    passed = not blocking_reasons
    summary = summary_ok if passed else f"{summary_fail}: {', '.join(blocking_reasons)}"
    return Build9XMergeGateResult(
        gate_name=gate_name,
        passed=passed,
        summary=summary,
        blocking_reasons=blocking_reasons,
        evidence_refs=evidence_refs,
        structured_log_key=_gate_log_key(gate_name),
    )


def _records_for_correlation(
    store: AppendOnlyMetaLearningStore,
    filename: str,
    correlation_id: str,
) -> tuple[dict[str, object], ...]:
    return tuple(
        record
        for record in store.read_records(filename)
        if str(record.get("correlation_id", "")) == correlation_id
    )


def _evaluate_no_live_mutation_path(bundle: MetaLearningReviewBundle) -> Build9XMergeGateResult:
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []

    for hypothesis in bundle.hypotheses:
        if hypothesis.target_runtime_mode != RuntimeMode.LOCAL_REPLAY:
            blocking_reasons.append(
                f"hypothesis:{hypothesis.hypothesis_id}:target_runtime_mode={hypothesis.target_runtime_mode.value}"
            )
            evidence_refs.append(hypothesis.hypothesis_id)

    for candidate in bundle.candidates:
        if candidate.auto_promotion_enabled:
            blocking_reasons.append(
                f"candidate:{candidate.candidate_id}:auto_promotion_enabled"
            )
            evidence_refs.append(candidate.candidate_id)
        if candidate.promotion_state in {
            PromotionState.MICRO_LIVE_CANDIDATE,
            PromotionState.LIVE_CANDIDATE,
        }:
            blocking_reasons.append(
                f"candidate:{candidate.candidate_id}:promotion_state={candidate.promotion_state.value}"
            )
            evidence_refs.append(candidate.candidate_id)

    return _build_gate_result(
        Build9XMergeGateName.NO_LIVE_MUTATION_PATH,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="All governed hypotheses stay on LOCAL_REPLAY and all candidates remain replay/shadow only.",
        summary_fail="Ungoverned live mutation path detected",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def _evaluate_end_to_end_id_correlation(
    bundle: MetaLearningReviewBundle,
    *,
    state_dir: Path | None,
) -> Build9XMergeGateResult:
    correlation_id = bundle.correlation_id
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []
    hypothesis_ids = {hypothesis.hypothesis_id for hypothesis in bundle.hypotheses}
    candidate_ids = {candidate.candidate_id for candidate in bundle.candidates}
    replay_bundles_by_candidate = {
        replay_bundle.candidate_id: replay_bundle
        for replay_bundle in bundle.replay_bundles
    }

    if not bundle.review_export.export_ref:
        blocking_reasons.append("review_export_missing_export_ref")
    else:
        evidence_refs.append(bundle.review_export.export_ref)

    for candidate in bundle.candidates:
        missing_hypotheses = sorted(set(candidate.hypothesis_ids) - hypothesis_ids)
        if missing_hypotheses:
            blocking_reasons.append(
                f"candidate:{candidate.candidate_id}:unknown_hypotheses={','.join(missing_hypotheses)}"
            )
            evidence_refs.append(candidate.candidate_id)
        replay_bundle = replay_bundles_by_candidate.get(candidate.candidate_id)
        if candidate.replay_bundle_reference:
            if replay_bundle is None:
                blocking_reasons.append(
                    f"candidate:{candidate.candidate_id}:missing_replay_bundle"
                )
                evidence_refs.append(candidate.candidate_id)
            elif candidate.replay_bundle_reference != replay_bundle.bundle_id:
                blocking_reasons.append(
                    f"candidate:{candidate.candidate_id}:replay_bundle_ref_mismatch"
                )
                evidence_refs.extend((candidate.candidate_id, replay_bundle.bundle_id))
        if candidate.comparison_protocol_reference:
            if replay_bundle is None:
                blocking_reasons.append(
                    f"candidate:{candidate.candidate_id}:missing_comparison_protocol"
                )
                evidence_refs.append(candidate.candidate_id)
            elif (
                candidate.comparison_protocol_reference
                != replay_bundle.comparison_protocol.protocol_id
            ):
                blocking_reasons.append(
                    f"candidate:{candidate.candidate_id}:comparison_protocol_ref_mismatch"
                )
                evidence_refs.extend(
                    (candidate.candidate_id, replay_bundle.comparison_protocol.protocol_id)
                )

    for replay_bundle in bundle.replay_bundles:
        if replay_bundle.candidate_id not in candidate_ids:
            blocking_reasons.append(
                f"replay_bundle:{replay_bundle.bundle_id}:unknown_candidate={replay_bundle.candidate_id}"
            )
            evidence_refs.append(replay_bundle.bundle_id)
        if replay_bundle.comparison_protocol.candidate_id != replay_bundle.candidate_id:
            blocking_reasons.append(
                f"replay_bundle:{replay_bundle.bundle_id}:comparison_protocol_candidate_mismatch"
            )
            evidence_refs.append(replay_bundle.bundle_id)
        missing_hypotheses = sorted(set(replay_bundle.hypothesis_ids) - hypothesis_ids)
        if missing_hypotheses:
            blocking_reasons.append(
                f"replay_bundle:{replay_bundle.bundle_id}:unknown_hypotheses={','.join(missing_hypotheses)}"
            )
            evidence_refs.append(replay_bundle.bundle_id)

    if bundle.review_export.export_ref:
        for decision in bundle.review_decisions:
            if decision.review_entity_id != bundle.review_export.export_ref:
                blocking_reasons.append(
                    f"review_decision:{decision.decision_id}:review_entity_mismatch"
                )
                evidence_refs.extend((decision.decision_id, bundle.review_export.export_ref))

    for archive_entry in bundle.archive_eligibility:
        if archive_entry.correlation_id != correlation_id:
            blocking_reasons.append(
                f"archive_eligibility:{archive_entry.entity_id}:correlation_mismatch"
            )
            evidence_refs.append(archive_entry.entity_id)

    for transition in bundle.lifecycle_transitions:
        if transition.correlation_id != correlation_id:
            blocking_reasons.append(
                f"transition:{transition.transition_id}:correlation_mismatch"
            )
            evidence_refs.append(transition.transition_id)

    if state_dir is not None:
        store = AppendOnlyMetaLearningStore(state_dir)
        diagnostic_records = _records_for_correlation(store, _DIAGNOSTIC_FILE, correlation_id)
        hypothesis_records = _records_for_correlation(store, _HYPOTHESIS_FILE, correlation_id)
        candidate_records = _records_for_correlation(store, _CANDIDATE_FILE, correlation_id)
        review_records = _records_for_correlation(store, _REVIEW_FILE, correlation_id)
        export_records = _records_for_correlation(store, _EXPORT_BUNDLE_FILE, correlation_id)
        memory_records = _records_for_correlation(store, _MEMORY_FILE, correlation_id)
        event_records = _records_for_correlation(store, _EVENT_FILE, correlation_id)

        if bundle.diagnostics and len(diagnostic_records) < len(bundle.diagnostics):
            blocking_reasons.append("persistence:diagnostic_records_incomplete")
        if bundle.hypotheses and len(hypothesis_records) < len(bundle.hypotheses):
            blocking_reasons.append("persistence:hypothesis_records_incomplete")
        if bundle.candidates and len(candidate_records) < len(bundle.candidates):
            blocking_reasons.append("persistence:candidate_records_incomplete")
        if not review_records:
            blocking_reasons.append("persistence:review_records_missing")
        if bundle.replay_bundles and len(export_records) < len(bundle.replay_bundles):
            blocking_reasons.append("persistence:export_bundle_records_incomplete")
        if not memory_records:
            blocking_reasons.append("persistence:memory_records_missing")
        if not event_records:
            blocking_reasons.append("persistence:event_records_missing")
        evidence_refs.append(str(state_dir))

    return _build_gate_result(
        Build9XMergeGateName.END_TO_END_ID_CORRELATION,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="Correlation IDs, replay references, review export refs, and append-only ledgers stay coherent end-to-end.",
        summary_fail="End-to-end identifier correlation is incomplete",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def _evaluate_structured_learning_logs_present(
    bundle: MetaLearningReviewBundle,
    *,
    state_dir: Path | None,
) -> Build9XMergeGateResult:
    correlation_id = bundle.correlation_id
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []

    for diagnostic in bundle.diagnostics:
        if not diagnostic.structured_log_key:
            blocking_reasons.append(
                f"diagnostic:{diagnostic.diagnostic_id}:missing_structured_log_key"
            )
            evidence_refs.append(diagnostic.diagnostic_id)

    if not bundle.review_export.export_ref:
        blocking_reasons.append("review_export_missing_export_ref")
    else:
        evidence_refs.append(bundle.review_export.export_ref)

    if state_dir is not None:
        store = AppendOnlyMetaLearningStore(state_dir)
        event_records = _records_for_correlation(store, _EVENT_FILE, correlation_id)
        event_types = {str(record.get("event_type", "")) for record in event_records}
        required_event_types = {"review_exported", "memory_recorded"}
        if bundle.review_decisions:
            required_event_types.add("review_decision_recorded")
        if bundle.diagnostics:
            required_event_types.add("diagnostic_created")
        if bundle.hypotheses:
            required_event_types.add("hypothesis_registered")
        if bundle.candidates:
            required_event_types.add("candidate_prepared")
        if bundle.capacity_snapshot is not None and bundle.capacity_snapshot.backpressure_signal_key:
            required_event_types.add(bundle.capacity_snapshot.backpressure_signal_key)

        missing_event_types = sorted(required_event_types - event_types)
        if missing_event_types:
            blocking_reasons.append(
                f"missing_event_types={','.join(missing_event_types)}"
            )
        if bundle.lifecycle_transitions and not any(
            event_type.endswith("_state_changed") for event_type in event_types
        ):
            blocking_reasons.append("missing_lifecycle_state_change_events")
        evidence_refs.append(str(state_dir / _EVENT_FILE))

    return _build_gate_result(
        Build9XMergeGateName.STRUCTURED_LEARNING_LOGS_PRESENT,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="Structured diagnostic keys and append-only learning events are present for the governed lifecycle.",
        summary_fail="Structured learning logs are incomplete",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def _evaluate_learning_backpressure_handled(
    bundle: MetaLearningReviewBundle,
) -> Build9XMergeGateResult:
    snapshot = bundle.capacity_snapshot or LearningCapacitySnapshot()
    projection = build_build9x_projection(bundle)
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []
    degraded = bool(
        snapshot.review_blocked_due_to_incomplete_data
        or snapshot.backpressure_active
        or snapshot.unprocessed_items_count > 0
        or snapshot.log_loss_total > 0
        or snapshot.export_failures_total > 0
    )

    if degraded:
        if not bundle.review_export.review_blocked_due_to_incomplete_data:
            blocking_reasons.append("review_export_not_blocked_under_degraded_capture")
        if bundle.review_export.capture_mode != snapshot.capture_mode:
            blocking_reasons.append("review_export_capture_mode_mismatch")
        if bundle.replay_bundles:
            blocking_reasons.append("replay_handoff_not_suppressed_under_degraded_capture")
        if not any(
            decision.review_state == ReviewState.NEEDS_REVISION
            for decision in bundle.review_decisions
        ):
            blocking_reasons.append("needs_revision_decision_missing")
        if any(
            candidate.governance_stage
            in {
                CandidateGovernanceStage.READY_FOR_REPLAY,
                CandidateGovernanceStage.REPLAY_RUNNING,
                CandidateGovernanceStage.REPLAY_PASSED,
                CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
            }
            for candidate in bundle.candidates
        ):
            blocking_reasons.append("candidates_not_held_below_replay_under_degraded_capture")
        if projection.status != "critical":
            blocking_reasons.append("monitoring_projection_not_critical")
        if snapshot.backpressure_active and not snapshot.backpressure_signal_key:
            blocking_reasons.append("backpressure_signal_key_missing")
        if snapshot.blocking_reasons:
            evidence_refs.extend(snapshot.blocking_reasons)
    elif bundle.review_export.review_blocked_due_to_incomplete_data:
        blocking_reasons.append("review_export_blocked_without_degraded_capture")

    return _build_gate_result(
        Build9XMergeGateName.LEARNING_BACKPRESSURE_HANDLED,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="Backpressure and incomplete-data states are translated into governed blocking rather than silent promotion.",
        summary_fail="Backpressure handling is incomplete or inconsistent",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def _evaluate_resource_budgets_respected(
    bundle: MetaLearningReviewBundle,
) -> Build9XMergeGateResult:
    snapshot = bundle.capacity_snapshot or LearningCapacitySnapshot()
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []

    if snapshot.queue_depth > snapshot.backlog_protection_threshold:
        expected_backlog_state = LearningBacklogState.PROTECTION
    elif snapshot.queue_depth > snapshot.backlog_alert_threshold:
        expected_backlog_state = LearningBacklogState.ALERT
    else:
        expected_backlog_state = LearningBacklogState.NORMAL

    if snapshot.backlog_state != expected_backlog_state:
        blocking_reasons.append(
            f"backlog_state_expected_{expected_backlog_state.value}_got_{snapshot.backlog_state.value}"
        )
    if expected_backlog_state == LearningBacklogState.PROTECTION and not snapshot.backpressure_active:
        blocking_reasons.append("protection_threshold_without_backpressure")
    if expected_backlog_state != LearningBacklogState.PROTECTION and snapshot.backpressure_active:
        blocking_reasons.append("backpressure_active_without_protection_threshold")
    if snapshot.log_loss_total > 0 and "learning_log_loss_total" not in snapshot.blocking_reasons:
        blocking_reasons.append("log_loss_not_reflected_in_blocking_reasons")
    if (
        snapshot.export_failures_total > 0
        and "learning_export_failures_total" not in snapshot.blocking_reasons
    ):
        blocking_reasons.append("export_failures_not_reflected_in_blocking_reasons")
    if (
        snapshot.unprocessed_items_count > 0
        and "learning_unprocessed_items_count" not in snapshot.blocking_reasons
        and not snapshot.backpressure_active
    ):
        blocking_reasons.append("unprocessed_items_not_reflected_in_blocking_reasons")
    if (
        snapshot.review_blocked_due_to_incomplete_data
        != snapshot.promotion_blocked_due_to_incomplete_data
    ):
        blocking_reasons.append("review_and_promotion_block_flags_diverge")

    evidence_refs.extend(
        (
            f"queue_depth={snapshot.queue_depth}",
            f"alert_threshold={snapshot.backlog_alert_threshold}",
            f"protection_threshold={snapshot.backlog_protection_threshold}",
        )
    )

    return _build_gate_result(
        Build9XMergeGateName.RESOURCE_BUDGETS_RESPECTED,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="Resource thresholds, backlog states, and blocking propagation remain internally coherent.",
        summary_fail="Resource budgets or threshold propagation are inconsistent",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def _evaluate_statistical_governance_present(
    bundle: MetaLearningReviewBundle,
) -> Build9XMergeGateResult:
    blocking_reasons: list[str] = []
    evidence_refs: list[str] = []

    for hypothesis in bundle.hypotheses:
        if hypothesis.sample_size <= 0:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:sample_size_missing")
            evidence_refs.append(hypothesis.hypothesis_id)
        if not hypothesis.segmentation_used:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:segmentation_missing")
            evidence_refs.append(hypothesis.hypothesis_id)
        if not hypothesis.comparison_metrics:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:comparison_metrics_missing")
            evidence_refs.append(hypothesis.hypothesis_id)
        if not hypothesis.rejection_criteria:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:rejection_criteria_missing")
            evidence_refs.append(hypothesis.hypothesis_id)
        if not hypothesis.risk_of_regression:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:regression_risk_missing")
            evidence_refs.append(hypothesis.hypothesis_id)
        if not hypothesis.expected_effect:
            blocking_reasons.append(f"hypothesis:{hypothesis.hypothesis_id}:expected_effect_missing")
            evidence_refs.append(hypothesis.hypothesis_id)

    for candidate in bundle.candidates:
        if not candidate.tests_required:
            blocking_reasons.append(f"candidate:{candidate.candidate_id}:tests_required_missing")
            evidence_refs.append(candidate.candidate_id)
        if not candidate.replay_scope:
            blocking_reasons.append(f"candidate:{candidate.candidate_id}:replay_scope_missing")
            evidence_refs.append(candidate.candidate_id)
        if not candidate.requires_manual_review:
            blocking_reasons.append(f"candidate:{candidate.candidate_id}:manual_review_flag_missing")
            evidence_refs.append(candidate.candidate_id)

    for replay_bundle in bundle.replay_bundles:
        if not replay_bundle.tests_required:
            blocking_reasons.append(f"replay_bundle:{replay_bundle.bundle_id}:tests_required_missing")
            evidence_refs.append(replay_bundle.bundle_id)
        if not replay_bundle.comparison_protocol.comparison_metrics:
            blocking_reasons.append(
                f"replay_bundle:{replay_bundle.bundle_id}:comparison_metrics_missing"
            )
            evidence_refs.append(replay_bundle.bundle_id)
        if not replay_bundle.comparison_protocol.rejection_criteria:
            blocking_reasons.append(
                f"replay_bundle:{replay_bundle.bundle_id}:rejection_criteria_missing"
            )
            evidence_refs.append(replay_bundle.bundle_id)
        if not replay_bundle.shared_core_hash:
            blocking_reasons.append(f"replay_bundle:{replay_bundle.bundle_id}:shared_core_hash_missing")
            evidence_refs.append(replay_bundle.bundle_id)
        if not replay_bundle.bundle_checksum:
            blocking_reasons.append(f"replay_bundle:{replay_bundle.bundle_id}:bundle_checksum_missing")
            evidence_refs.append(replay_bundle.bundle_id)

    if (bundle.hypotheses or bundle.candidates) and not bundle.review_decisions:
        blocking_reasons.append("review_decisions_missing")

    return _build_gate_result(
        Build9XMergeGateName.STATISTICAL_GOVERNANCE_PRESENT,
        blocking_reasons=tuple(blocking_reasons),
        summary_ok="Hypotheses, candidates, replay bundles, and review decisions carry the evidence needed for governed comparison.",
        summary_fail="Statistical governance evidence is incomplete",
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
    )


def evaluate_build9x_merge_gates(
    bundle: MetaLearningReviewBundle,
    *,
    state_dir: Path | None = None,
) -> Build9XMergeGateReport:
    """Evaluate the explicit Build-9X V2 merge gates on a governed review bundle."""

    gates = (
        _evaluate_no_live_mutation_path(bundle),
        _evaluate_end_to_end_id_correlation(bundle, state_dir=state_dir),
        _evaluate_structured_learning_logs_present(bundle, state_dir=state_dir),
        _evaluate_learning_backpressure_handled(bundle),
        _evaluate_resource_budgets_respected(bundle),
        _evaluate_statistical_governance_present(bundle),
    )
    return Build9XMergeGateReport(
        correlation_id=bundle.correlation_id,
        all_passed=all(gate.passed for gate in gates),
        gates=gates,
        state_dir=str(state_dir) if state_dir is not None else "",
    )


__all__ = [
    "Build9XMergeGateName",
    "Build9XMergeGateResult",
    "Build9XMergeGateReport",
    "evaluate_build9x_merge_gates",
]
