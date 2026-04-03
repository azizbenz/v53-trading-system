"""Export governed Build-9X review packets."""

from __future__ import annotations

from meta_learning.contracts import (
    ArchiveEligibilityRecord,
    BreakdownReport,
    ImprovementCandidate,
    LearningCapacitySnapshot,
    LearningChecklist,
    LearningHypothesis,
    LearningReviewExport,
    LifecycleTransitionRecord,
    ReplayExportBundle,
    ReviewDecisionRecord,
)
from meta_learning.enums import LearningCaptureMode
from meta_learning.merge_gate_contracts import Build9XMergeGateReport


def export_learning_review(
    correlation_id: str,
    report: BreakdownReport,
    checklist: LearningChecklist,
    candidates: tuple[ImprovementCandidate, ...],
    *,
    hypotheses: tuple[LearningHypothesis, ...] = (),
    replay_bundles: tuple[ReplayExportBundle, ...] = (),
    capacity_snapshot: LearningCapacitySnapshot | None = None,
    review_decisions: tuple[ReviewDecisionRecord, ...] = (),
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...] = (),
    lifecycle_transitions: tuple[LifecycleTransitionRecord, ...] = (),
    merge_gate_report: Build9XMergeGateReport | None = None,
    export_ref: str = "",
) -> LearningReviewExport:
    """Render the governed review packet into a markdown export."""

    mistake_lines = tuple(f"- {item}" for item in report.mistake_classes) or ("- none",)
    checklist_lines = tuple(f"- {item}" for item in checklist.items) or ("- none",)
    candidate_lines = tuple(f"- {candidate.summary}" for candidate in candidates) or ("- none",)
    hypothesis_lines = (
        tuple(
            (
                f"- {getattr(hypothesis, 'title', 'unknown')} "
                f"(strength={getattr(getattr(hypothesis, 'evidence_strength', ''), 'value', getattr(hypothesis, 'evidence_strength', ''))}, "
                f"stage={getattr(getattr(hypothesis, 'governance_stage', ''), 'value', getattr(hypothesis, 'governance_stage', ''))})"
            )
            for hypothesis in hypotheses
        )
        or ("- none",)
    )
    candidate_detail_lines = (
        tuple(
            (
                f"- {candidate.candidate_id} "
                f"(stage={candidate.governance_stage.value}, "
                f"tests={len(candidate.tests_required)})"
            )
            for candidate in candidates
        )
        or ("- none",)
    )
    replay_bundle_lines = (
        tuple(
            (
                f"- {bundle.bundle_id} "
                f"(candidate={bundle.candidate_id}, "
                f"source={bundle.source_version}, "
                f"contracts={bundle.contracts_version}, "
                f"validation_ready={bundle.execution_plan.validation_ready})"
            )
            for bundle in replay_bundles
        )
        or ("- none",)
    )
    review_decision_lines = (
        tuple(
            (
                f"- {decision.actor} "
                f"(state={decision.review_state.value}, "
                f"verdict={decision.verdict}, "
                f"final={'yes' if decision.final_verdict_recorded else 'no'})"
            )
            for decision in review_decisions
        )
        or ("- none",)
    )
    archive_lines = (
        tuple(
            (
                f"- {entry.entity_kind}:{entry.entity_id} "
                f"(eligible={'yes' if entry.eligible else 'no'}, "
                f"archived={'yes' if entry.archived_at else 'no'}, "
                f"reasons={', '.join(entry.blocking_reasons) or 'none'})"
            )
            for entry in archive_eligibility
        )
        or ("- none",)
    )
    if capacity_snapshot is None:
        capacity_lines = ("- queue=0 / backlog=normal / mode=full_capture", "- none")
    else:
        capacity_lines = (
            (
                f"- queue={capacity_snapshot.queue_depth} / "
                f"backlog={capacity_snapshot.backlog_state.value} / "
                f"mode={capacity_snapshot.capture_mode.value}"
            ),
            (
                f"- oldest={capacity_snapshot.queue_oldest_age_ms}ms / "
                f"unprocessed={capacity_snapshot.unprocessed_items_count} / "
                f"blocked={'yes' if capacity_snapshot.review_blocked_due_to_incomplete_data else 'no'} / "
                f"reasons={', '.join(capacity_snapshot.blocking_reasons) or 'none'}"
            ),
        )
    transition_lines = (
        tuple(
            (
                f"- {transition.entity_kind}:{transition.entity_id} "
                f"{transition.from_state}->{transition.to_state} "
                f"(actor={transition.actor})"
            )
            for transition in lifecycle_transitions
        )
        or ("- none",)
    )
    merge_gate_lines = (
        tuple(
            (
                f"- {gate.gate_name.value}: "
                f"{'pass' if gate.passed else 'fail'} "
                f"(log={gate.structured_log_key}, "
                f"reasons={', '.join(gate.blocking_reasons) or 'none'})"
            )
            for gate in merge_gate_report.gates
        )
        if merge_gate_report is not None
        else ("- not_evaluated",)
    )

    lines = [
        f"# Build-9X Review - {correlation_id}",
        "",
        "## Summary",
        report.summary,
        "",
        "## Mistake Classes",
        *mistake_lines,
        "",
        "## Checklist",
        *checklist_lines,
        "",
        "## Hypotheses",
        *hypothesis_lines,
        "",
        "## Candidates",
        *candidate_lines,
        "",
        "## Candidate States",
        *candidate_detail_lines,
        "",
        "## Capacity Guard",
        *capacity_lines,
        "",
        "## Review Decisions",
        *review_decision_lines,
        "",
        "## Archive Eligibility",
        *archive_lines,
        "",
        "## Lifecycle Transitions",
        *transition_lines,
        "",
        "## Merge Gates",
        *merge_gate_lines,
        "",
        "## Replay Bundles",
        *replay_bundle_lines,
    ]

    return LearningReviewExport(
        correlation_id=correlation_id,
        export_ref=export_ref or f"meta_learning_review:{correlation_id}",
        markdown_body="\n".join(lines),
        checklist=checklist,
        candidates=candidates,
        replay_bundles=replay_bundles,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=lifecycle_transitions,
        merge_gate_report=merge_gate_report,
        capture_mode=(
            capacity_snapshot.capture_mode
            if capacity_snapshot
            else LearningCaptureMode.FULL_CAPTURE
        ),
        review_blocked_due_to_incomplete_data=(
            capacity_snapshot.review_blocked_due_to_incomplete_data
            if capacity_snapshot
            else False
        ),
        blocking_reasons=capacity_snapshot.blocking_reasons if capacity_snapshot else (),
    )


__all__ = [
    "export_learning_review",
]
