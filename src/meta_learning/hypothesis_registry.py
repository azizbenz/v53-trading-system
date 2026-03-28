"""Build governed hypotheses from diagnostics."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult, LearningHypothesis


_RATIONALE_BY_CATEGORY = {
    "trace_coverage": "Low trace coverage suggests observability is too weak for governed promotion.",
    "sterilization": "Elevated CRA sterilization suggests economic viability is being destroyed downstream.",
    "cost_drift": "Break-even drift indicates the current cost model is no longer representative.",
    "edge_degraded": "Edge degradation suggests the previously credible edge is no longer stable.",
    "near_miss": "Near-miss records suggest valid edge may be blocked by current thresholds.",
    "no_issue": "No material issue detected; keep surveillance and collect more evidence.",
}


def build_learning_hypotheses(
    correlation_id: str,
    diagnostics: tuple[DiagnosticResult, ...],
) -> tuple[LearningHypothesis, ...]:
    """Convert diagnostics into governed replay hypotheses."""

    hypotheses: list[LearningHypothesis] = []
    categories_in_order: list[str] = []
    refs_by_category: dict[str, list[str]] = {}
    summary_by_category: dict[str, str] = {}

    for diagnostic in diagnostics:
        if diagnostic.category == "no_issue":
            continue
        if diagnostic.category not in refs_by_category:
            categories_in_order.append(diagnostic.category)
            refs_by_category[diagnostic.category] = []
            summary_by_category[diagnostic.category] = diagnostic.summary
        refs_by_category[diagnostic.category].append(diagnostic.diagnostic_id)

    for index, category in enumerate(categories_in_order, start=1):
        hypotheses.append(LearningHypothesis(
            hypothesis_id=f"{correlation_id}:hypothesis:{index}",
            correlation_id=correlation_id,
            category=category,
            title=f"Hypothesis for {category}",
            rationale=_RATIONALE_BY_CATEGORY.get(category, summary_by_category[category]),
            diagnostic_ids=tuple(refs_by_category[category]),
        ))

    return tuple(hypotheses)


__all__ = [
    "build_learning_hypotheses",
]
