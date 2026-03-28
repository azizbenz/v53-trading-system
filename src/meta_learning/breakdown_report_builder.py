"""Aggregate governed diagnostics into a concise breakdown report."""

from __future__ import annotations

from meta_learning.contracts import BreakdownReport, DiagnosticResult


def build_breakdown_report(
    correlation_id: str,
    diagnostics: tuple[DiagnosticResult, ...],
    mistake_classes: tuple[str, ...],
) -> BreakdownReport:
    """Build the canonical Build-9X breakdown report."""

    near_miss_pairs = tuple(sorted({
        diagnostic.summary.split(" on ", 1)[1].split(":", 1)[0]
        for diagnostic in diagnostics
        if diagnostic.category == "near_miss" and " on " in diagnostic.summary
    }))
    summary = "; ".join(diagnostic.summary for diagnostic in diagnostics)
    if not summary:
        summary = "No diagnostic summary available"

    return BreakdownReport(
        correlation_id=correlation_id,
        diagnostics=diagnostics,
        mistake_classes=mistake_classes,
        near_miss_pairs=near_miss_pairs,
        summary=summary,
    )


__all__ = [
    "build_breakdown_report",
]
