"""End-to-end governed flow tests for the real Build-9X layer."""

from __future__ import annotations

from interface_contracts import StrategyClassification
from meta_learning import (
    DiagnosticResult,
    LearningMemoryRecord,
    LearningMemoryStore,
    build_breakdown_report,
    build_improvement_candidates,
    build_learning_checklist,
    build_learning_hypotheses,
    export_learning_review,
)


def _diagnostics() -> tuple[DiagnosticResult, ...]:
    return (
        DiagnosticResult(
            diagnostic_id="diag-1",
            correlation_id="corr-9x",
            category="sterilization",
            summary="CRA sterilization elevated at 50%",
            structured_log_key="build9x.sterilization",
        ),
        DiagnosticResult(
            diagnostic_id="diag-2",
            correlation_id="corr-9x",
            category="near_miss",
            summary="Near miss on BTCUSDT: final_score=0.82, state=hard_blocked",
            structured_log_key="build9x.near_miss",
        ),
    )


def test_build9x_full_review_flow_stays_governed():
    diagnostics = _diagnostics()
    mistake_classes = ("economic_sterilization", "near_miss")
    report = build_breakdown_report("corr-9x", diagnostics, mistake_classes)
    checklist = build_learning_checklist("corr-9x", diagnostics, mistake_classes)
    hypotheses = build_learning_hypotheses("corr-9x", diagnostics)
    candidates = build_improvement_candidates(
        "corr-9x",
        StrategyClassification.A_VARIANT,
        hypotheses,
    )
    review_export = export_learning_review("corr-9x", report, checklist, candidates)

    store = LearningMemoryStore()
    record = LearningMemoryRecord(
        correlation_id="corr-9x",
        diagnostics_count=len(diagnostics),
        hypothesis_count=len(hypotheses),
        candidate_count=len(candidates),
        summary=report.summary,
    )
    store = store.append(record)

    assert store.latest() == record
    assert "## Summary" in review_export.markdown_body
    assert "## Candidates" in review_export.markdown_body
    assert all(candidate.auto_promotion_enabled is False for candidate in review_export.candidates)
    assert all(candidate.promotion_state.value == "replay_only" for candidate in review_export.candidates)
