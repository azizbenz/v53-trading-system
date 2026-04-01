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
    primary_root_cause = next(
        (
            diagnostic.root_causes[0]
            for diagnostic in diagnostics
            if diagnostic.root_causes
        ),
        diagnostics[0].category if diagnostics else "",
    )
    counterfactual_summary = next(
        (
            diagnostic.counterfactual_summary
            for diagnostic in diagnostics
            if diagnostic.counterfactual_summary
        ),
        "No counterfactual summary available",
    )
    cost_reading = next(
        (
            diagnostic.economic_assessment
            for diagnostic in diagnostics
            if diagnostic.economic_assessment
        ),
        "Expected vs realized cost assessment pending review",
    )
    verdict = "review_required" if any(
        diagnostic.category != "no_issue" for diagnostic in diagnostics
    ) else "no_action"

    return BreakdownReport(
        correlation_id=correlation_id,
        diagnostics=diagnostics,
        mistake_classes=mistake_classes,
        near_miss_pairs=near_miss_pairs,
        summary=summary,
        primary_root_cause=primary_root_cause,
        expected_vs_realized_costs=cost_reading,
        break_even_reading=(
            "Break-even drift present"
            if any(diagnostic.category == "cost_drift" for diagnostic in diagnostics)
            else "No break-even drift captured"
        ),
        sterilization_reading=(
            "CRA sterilization elevated"
            if any(diagnostic.category == "sterilization" for diagnostic in diagnostics)
            else "No sterilization alert captured"
        ),
        portfolio_reading=(
            "Near-miss or edge review required"
            if near_miss_pairs
            else "No portfolio anomaly summarized"
        ),
        counterfactual_summary=counterfactual_summary,
        main_lesson=summary,
        verdict=verdict,
    )


__all__ = [
    "build_breakdown_report",
]
