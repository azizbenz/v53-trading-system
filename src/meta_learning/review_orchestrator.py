"""Governed orchestration entrypoint for the real Build-9X layer."""

from __future__ import annotations

from pathlib import Path

from meta_learning.breakdown_report_builder import build_breakdown_report
from meta_learning.checklist_generator import build_learning_checklist
from meta_learning.contracts import (
    ImprovementCandidate,
    DiagnosticResult,
    LearningCapacitySnapshot,
    LearningChecklist,
    LearningHypothesis,
    LifecycleTransitionRecord,
    LearningMemoryRecord,
    MetaLearningReviewBundle,
    TradeLearningInput,
)
from meta_learning.enums import (
    CandidateGovernanceStage,
    DiagnosticSeverity,
    DiagnosticStatus,
    HypothesisGovernanceStage,
)
from meta_learning.hypothesis_registry import build_learning_hypotheses
from meta_learning.improvement_candidate_builder import build_improvement_candidates
from meta_learning.learning_review_exporter import export_learning_review
from meta_learning.lifecycle_registry import (
    apply_candidate_path,
    apply_diagnostic_path,
    apply_hypothesis_path,
)
from meta_learning.mistake_classifier import classify_mistakes
from meta_learning.near_miss_analyzer import analyze_near_misses
from meta_learning.persistence_store import AppendOnlyMetaLearningStore
from meta_learning.post_trade_diagnostic_engine import build_post_trade_diagnostics
from meta_learning.review_governance import (
    build_archive_eligibility,
    build_system_review_decisions,
)
from meta_learning.replay_bundle_builder import (
    build_replay_export_bundles,
    enrich_candidates_with_replay_refs,
)
from meta_minimal.break_even_dashboard.break_even_reporter import BreakEvenReport
from meta_minimal.cra_monitor.cra_reporter import CRAReport
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.dtr_reporter import DTRSummary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport


def _capacity_block_reason(capacity_snapshot: LearningCapacitySnapshot) -> str:
    reasons = ", ".join(capacity_snapshot.blocking_reasons) or "incomplete_data"
    return (
        "Build-9X review blocked while capture_minimale/incomplete data is active "
        f"({reasons})"
    )


def _block_candidates_for_incomplete_data(
    candidates: tuple[ImprovementCandidate, ...],
    capacity_snapshot: LearningCapacitySnapshot,
) -> tuple[ImprovementCandidate, ...]:
    note = _capacity_block_reason(capacity_snapshot)
    return tuple(
        candidate.model_copy(
            update={
                "validation_notes": candidate.validation_notes + (note,),
            }
        )
        for candidate in candidates
    )


def _govern_diagnostics(
    diagnostics: tuple[DiagnosticResult, ...],
    *,
    review_blocked: bool,
) -> tuple[tuple[DiagnosticResult, ...], tuple[LifecycleTransitionRecord, ...]]:
    governed: list[DiagnosticResult] = []
    transitions: list[LifecycleTransitionRecord] = []
    for diagnostic in diagnostics:
        if review_blocked:
            path = (
                (DiagnosticStatus.ESCALATED,)
                if diagnostic.manual_review_required
                else ()
            )
        else:
            path = (
                (DiagnosticStatus.ESCALATED, DiagnosticStatus.REVIEWED)
                if diagnostic.severity == DiagnosticSeverity.CRITICAL
                else (DiagnosticStatus.REVIEWED,)
            )
        updated, current_transitions = apply_diagnostic_path(
            diagnostic,
            path,
            reason=(
                "incomplete data keeps diagnostic under governed escalation"
                if review_blocked
                else "governed review export completed"
            ),
        )
        governed.append(updated)
        transitions.extend(current_transitions)
    return tuple(governed), tuple(transitions)


def _govern_hypotheses(
    hypotheses: tuple[LearningHypothesis, ...],
    *,
    review_blocked: bool,
) -> tuple[tuple[LearningHypothesis, ...], tuple[LifecycleTransitionRecord, ...]]:
    governed: list[LearningHypothesis] = []
    transitions: list[LifecycleTransitionRecord] = []
    for hypothesis in hypotheses:
        path = (HypothesisGovernanceStage.UNDER_REVIEW,)
        updated, current_transitions = apply_hypothesis_path(
            hypothesis,
            path,
            reason=(
                "incomplete data blocks replay approval"
                if review_blocked
                else "governed human review queue assembled before replay approval"
            ),
        )
        governed.append(updated)
        transitions.extend(current_transitions)
    return tuple(governed), tuple(transitions)


def _govern_candidates(
    candidates: tuple[ImprovementCandidate, ...],
    *,
    ready_for_replay_ids: frozenset[str],
    review_blocked: bool,
    capacity_snapshot: LearningCapacitySnapshot,
) -> tuple[tuple[ImprovementCandidate, ...], tuple[LifecycleTransitionRecord, ...]]:
    if review_blocked:
        return _block_candidates_for_incomplete_data(candidates, capacity_snapshot), ()

    governed: list[ImprovementCandidate] = []
    transitions: list[LifecycleTransitionRecord] = []
    for candidate in candidates:
        path: list[CandidateGovernanceStage] = [CandidateGovernanceStage.TESTS_PENDING]
        if candidate.candidate_id in ready_for_replay_ids:
            path.append(CandidateGovernanceStage.READY_FOR_REPLAY)
        updated, current_transitions = apply_candidate_path(
            candidate,
            path,
            reason="governed replay handoff assembled",
        )
        governed.append(updated)
        transitions.extend(current_transitions)
    return tuple(governed), tuple(transitions)


def _block_checklist_for_incomplete_data(
    checklist: LearningChecklist,
    capacity_snapshot: LearningCapacitySnapshot,
) -> LearningChecklist:
    note = _capacity_block_reason(capacity_snapshot)
    if note in checklist.items:
        return checklist.model_copy(
            update={
                "ready_for_local_replay": False,
                "ready_for_shadow": False,
            }
        )
    return checklist.model_copy(
        update={
            "items": checklist.items + (note,),
            "ready_for_local_replay": False,
            "ready_for_shadow": False,
        }
    )


def run_meta_learning_review(
    trade_input: TradeLearningInput,
    *,
    dtr_records: tuple[DTRRecord, ...],
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
    near_miss_threshold: float = 0.70,
    dataset_ref: object | None = None,
    clock_ref: object | None = None,
    capacity_snapshot: LearningCapacitySnapshot | None = None,
    state_dir: Path | None = None,
) -> MetaLearningReviewBundle:
    """Run the governed Build-9X review pipeline end-to-end."""

    diagnostics = build_post_trade_diagnostics(
        trade_input,
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
    ) + analyze_near_misses(
        trade_input.correlation_id,
        dtr_records,
        final_score_threshold=near_miss_threshold,
    )
    mistake_classes = classify_mistakes(diagnostics)
    breakdown_report = build_breakdown_report(
        trade_input.correlation_id,
        diagnostics,
        mistake_classes,
    )
    checklist = build_learning_checklist(
        trade_input.correlation_id,
        diagnostics,
        mistake_classes,
    )
    raw_hypotheses = build_learning_hypotheses(
        trade_input.correlation_id,
        diagnostics,
        source_version=trade_input.source_version,
    )
    resolved_capacity_snapshot = capacity_snapshot or LearningCapacitySnapshot()
    checklist_for_export = checklist
    diagnostics, diagnostic_transitions = _govern_diagnostics(
        diagnostics,
        review_blocked=resolved_capacity_snapshot.review_blocked_due_to_incomplete_data,
    )
    hypotheses, hypothesis_transitions = _govern_hypotheses(
        raw_hypotheses,
        review_blocked=resolved_capacity_snapshot.review_blocked_due_to_incomplete_data,
    )
    raw_candidates = build_improvement_candidates(
        trade_input.correlation_id,
        trade_input.strategy_classification,
        hypotheses,
    )
    review_export_ref = f"meta_learning_review:{trade_input.correlation_id}"
    if resolved_capacity_snapshot.review_blocked_due_to_incomplete_data:
        checklist_for_export = _block_checklist_for_incomplete_data(
            checklist,
            resolved_capacity_snapshot,
        )
        replay_bundles = ()
        ready_for_replay_ids: frozenset[str] = frozenset()
        candidates = enrich_candidates_with_replay_refs(raw_candidates, replay_bundles)
    else:
        replay_bundles = build_replay_export_bundles(
            trade_input,
            hypotheses,
            raw_candidates,
            review_export_ref=review_export_ref,
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
        )
        ready_for_replay_ids = frozenset(
            replay_bundle.candidate_id
            for replay_bundle in replay_bundles
            if replay_bundle.execution_plan.validation_ready
        )
        candidates = enrich_candidates_with_replay_refs(raw_candidates, replay_bundles)
    candidates, candidate_transitions = _govern_candidates(
        candidates,
        ready_for_replay_ids=ready_for_replay_ids,
        review_blocked=resolved_capacity_snapshot.review_blocked_due_to_incomplete_data,
        capacity_snapshot=resolved_capacity_snapshot,
    )
    lifecycle_transitions = (
        diagnostic_transitions
        + hypothesis_transitions
        + candidate_transitions
    )
    review_decisions = build_system_review_decisions(
        correlation_id=trade_input.correlation_id,
        review_entity_id=review_export_ref,
        review_blocked_due_to_incomplete_data=resolved_capacity_snapshot.review_blocked_due_to_incomplete_data,
        has_candidates=bool(candidates),
    )
    archive_eligibility = build_archive_eligibility(
        correlation_id=trade_input.correlation_id,
        diagnostics=diagnostics,
        hypotheses=hypotheses,
        candidates=candidates,
        review_decisions=review_decisions,
    )
    memory_record = LearningMemoryRecord(
        record_id=f"{trade_input.correlation_id}:memory_record",
        correlation_id=trade_input.correlation_id,
        diagnostic_id=diagnostics[0].diagnostic_id if diagnostics else None,
        hypothesis_id=hypotheses[0].hypothesis_id if hypotheses else None,
        candidate_id=candidates[0].candidate_id if candidates else None,
        diagnostics_count=len(diagnostics),
        hypothesis_count=len(hypotheses),
        candidate_count=len(candidates),
        verdict=(
            "incomplete_capture_blocked"
            if resolved_capacity_snapshot.review_blocked_due_to_incomplete_data
            else "review_required"
            if candidates
            else "no_action"
        ),
        rejection_reason=(
            _capacity_block_reason(resolved_capacity_snapshot)
            if resolved_capacity_snapshot.review_blocked_due_to_incomplete_data
            else None
        ),
        summary=breakdown_report.summary,
    )
    review_export = export_learning_review(
        trade_input.correlation_id,
        breakdown_report,
        checklist_for_export,
        candidates,
        hypotheses=hypotheses,
        replay_bundles=replay_bundles,
        capacity_snapshot=resolved_capacity_snapshot,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=lifecycle_transitions,
        export_ref=review_export_ref,
    )

    bundle = MetaLearningReviewBundle(
        correlation_id=trade_input.correlation_id,
        diagnostics=diagnostics,
        mistake_classes=mistake_classes,
        breakdown_report=breakdown_report,
        checklist=checklist_for_export,
        hypotheses=hypotheses,
        candidates=candidates,
        replay_bundles=replay_bundles,
        memory_record=memory_record,
        review_export=review_export,
        capacity_snapshot=resolved_capacity_snapshot,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=lifecycle_transitions,
    )
    if state_dir is not None:
        AppendOnlyMetaLearningStore(state_dir).append_review_bundle(bundle)
    return bundle


__all__ = [
    "run_meta_learning_review",
]
