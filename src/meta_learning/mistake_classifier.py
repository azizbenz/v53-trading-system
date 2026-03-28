"""Classify governed diagnostics into stable mistake classes."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult


_CATEGORY_TO_CLASS = {
    "trace_coverage": "observability_gap",
    "sterilization": "economic_sterilization",
    "cost_drift": "cost_model_drift",
    "edge_degraded": "edge_degradation",
    "near_miss": "near_miss",
    "no_issue": "no_material_issue",
}


def classify_mistakes(diagnostics: tuple[DiagnosticResult, ...]) -> tuple[str, ...]:
    """Return stable, deduplicated mistake classes for review."""

    return tuple(sorted({
        _CATEGORY_TO_CLASS.get(diagnostic.category, "generic_issue")
        for diagnostic in diagnostics
    }))


__all__ = [
    "classify_mistakes",
]
