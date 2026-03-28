"""Export governed Build-9X review packets."""

from __future__ import annotations

from meta_learning.contracts import (
    BreakdownReport,
    ImprovementCandidate,
    LearningChecklist,
    LearningReviewExport,
)


def export_learning_review(
    correlation_id: str,
    report: BreakdownReport,
    checklist: LearningChecklist,
    candidates: tuple[ImprovementCandidate, ...],
) -> LearningReviewExport:
    """Render the governed review packet into a markdown export."""

    lines = [
        f"# Build-9X Review — {correlation_id}",
        "",
        "## Summary",
        report.summary,
        "",
        "## Mistake Classes",
        *(f"- {item}" for item in report.mistake_classes),
        "",
        "## Checklist",
        *(f"- {item}" for item in checklist.items),
        "",
        "## Candidates",
        *(f"- {candidate.summary}" for candidate in candidates),
    ]

    return LearningReviewExport(
        correlation_id=correlation_id,
        markdown_body="\n".join(lines),
        checklist=checklist,
        candidates=candidates,
    )


__all__ = [
    "export_learning_review",
]
