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
    seen_categories: set[str] = set()

    for index, diagnostic in enumerate(diagnostics, start=1):
        if diagnostic.category in seen_categories:
            continue
        seen_categories.add(diagnostic.category)
        hypotheses.append(LearningHypothesis(
            hypothesis_id=f"{correlation_id}:hypothesis:{index}",
            correlation_id=correlation_id,
            category=diagnostic.category,
            title=f"Hypothesis for {diagnostic.category}",
            rationale=_RATIONALE_BY_CATEGORY.get(diagnostic.category, diagnostic.summary),
            diagnostic_ids=(diagnostic.diagnostic_id,),
        ))

    return tuple(hypotheses)


__all__ = [
    "build_learning_hypotheses",
]
