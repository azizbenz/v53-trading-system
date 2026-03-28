"""Governed orchestration entrypoint for the real Build-9X layer."""

from __future__ import annotations

from meta_learning.breakdown_report_builder import build_breakdown_report
from meta_learning.checklist_generator import build_learning_checklist
from meta_learning.contracts import (
    LearningMemoryRecord,
    MetaLearningReviewBundle,
    TradeLearningInput,
)
from meta_learning.hypothesis_registry import build_learning_hypotheses
from meta_learning.improvement_candidate_builder import build_improvement_candidates
from meta_learning.learning_review_exporter import export_learning_review
from meta_learning.mistake_classifier import classify_mistakes
from meta_learning.near_miss_analyzer import analyze_near_misses
from meta_learning.post_trade_diagnostic_engine import build_post_trade_diagnostics
from meta_minimal.break_even_dashboard.break_even_reporter import BreakEvenReport
from meta_minimal.cra_monitor.cra_reporter import CRAReport
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.dtr_reporter import DTRSummary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport


def run_meta_learning_review(
    trade_input: TradeLearningInput,
    *,
    dtr_records: tuple[DTRRecord, ...],
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
    near_miss_threshold: float = 0.70,
) -> MetaLearningReviewBundle:
    """Run the governed Build-9X review pipeline end-to-end."""

    diagnostics = build_post_trade_diagnostics(
        trade_input,
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
    ) + analyze_near_misses(
        trade_input.correlation_id,
        dtr_records,
        final_score_threshold=near_miss_threshold,
    )
    mistake_classes = classify_mistakes(diagnostics)
    breakdown_report = build_breakdown_report(
        trade_input.correlation_id,
        diagnostics,
        mistake_classes,
    )
    checklist = build_learning_checklist(
        trade_input.correlation_id,
        diagnostics,
        mistake_classes,
    )
    hypotheses = build_learning_hypotheses(trade_input.correlation_id, diagnostics)
    candidates = build_improvement_candidates(
        trade_input.correlation_id,
        trade_input.strategy_classification,
        hypotheses,
    )
    memory_record = LearningMemoryRecord(
        correlation_id=trade_input.correlation_id,
        diagnostics_count=len(diagnostics),
        hypothesis_count=len(hypotheses),
        candidate_count=len(candidates),
        summary=breakdown_report.summary,
    )
    review_export = export_learning_review(
        trade_input.correlation_id,
        breakdown_report,
        checklist,
        candidates,
    )

    return MetaLearningReviewBundle(
        correlation_id=trade_input.correlation_id,
        diagnostics=diagnostics,
        mistake_classes=mistake_classes,
        breakdown_report=breakdown_report,
        checklist=checklist,
        hypotheses=hypotheses,
        candidates=candidates,
        memory_record=memory_record,
        review_export=review_export,
    )


__all__ = [
    "run_meta_learning_review",
]
