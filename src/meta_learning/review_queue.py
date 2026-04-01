"""Review-queue builder for Build-9X governed hypotheses."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult, LearningHypothesis, ReviewQueueEntry
from meta_learning.enums import DiagnosticSeverity, HypothesisGovernanceStage


def build_review_queue(
    hypotheses: tuple[LearningHypothesis, ...],
    diagnostics: tuple[DiagnosticResult, ...],
) -> tuple[ReviewQueueEntry, ...]:
    """Build the canonical queue of hypotheses awaiting human review."""

    diagnostics_by_id = {
        diagnostic.diagnostic_id: diagnostic
        for diagnostic in diagnostics
    }
    queued: list[ReviewQueueEntry] = []
    for hypothesis in hypotheses:
        if hypothesis.governance_stage != HypothesisGovernanceStage.UNDER_REVIEW:
            continue
        severities = tuple(
            diagnostics_by_id[diagnostic_id].severity
            for diagnostic_id in hypothesis.diagnostic_ids
            if diagnostic_id in diagnostics_by_id
        )
        priority = (
            "critical"
            if any(severity == DiagnosticSeverity.CRITICAL for severity in severities)
            else "normal"
        )
        queued.append(
            ReviewQueueEntry(
                hypothesis_id=hypothesis.hypothesis_id,
                correlation_id=hypothesis.correlation_id,
                title=hypothesis.title,
                category=hypothesis.category,
                diagnostic_ids=hypothesis.diagnostic_ids,
                diagnostic_severities=severities,
                priority=priority,
                review_state=hypothesis.review_state,
                governance_stage=hypothesis.governance_stage,
                evidence_strength=hypothesis.evidence_strength,
                created_at=hypothesis.created_at,
            )
        )
    return tuple(
        sorted(
            queued,
            key=lambda entry: (
                0 if entry.priority == "critical" else 1,
                entry.created_at,
                entry.hypothesis_id,
            ),
        )
    )


__all__ = [
    "build_review_queue",
]
