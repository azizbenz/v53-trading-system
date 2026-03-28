"""Generate governed checklists from diagnostics and mistake classes."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult, LearningChecklist


def build_learning_checklist(
    correlation_id: str,
    diagnostics: tuple[DiagnosticResult, ...],
    mistake_classes: tuple[str, ...],
) -> LearningChecklist:
    """Create the human checklist required before any replay handoff."""

    items = [
        "confirm no live mutation path is enabled",
        "review diagnostics with structured logs",
        "prepare LOCAL_REPLAY candidate bundle",
    ]

    if "observability_gap" in mistake_classes:
        items.append("improve DTR coverage before any further promotion")
    if "cost_model_drift" in mistake_classes:
        items.append("compare expected vs realized costs in LOCAL_REPLAY")
    if "economic_sterilization" in mistake_classes:
        items.append("review CRA sterilization causes and thresholds")
    if any(diagnostic.category == "near_miss" for diagnostic in diagnostics):
        items.append("inspect near-miss DTR records for missed edge")

    return LearningChecklist(
        checklist_id=f"{correlation_id}:checklist",
        correlation_id=correlation_id,
        items=tuple(items),
        ready_for_local_replay=any(diagnostic.category != "no_issue" for diagnostic in diagnostics),
        ready_for_shadow=False,
    )


__all__ = [
    "build_learning_checklist",
]
