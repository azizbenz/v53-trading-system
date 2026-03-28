"""Hypothesis, checklist, and candidate tests for Build-9X."""

from __future__ import annotations

from interface_contracts import PromotionState, StrategyClassification
from meta_learning import (
    CandidateKind,
    DiagnosticResult,
    ImprovementCandidate,
    build_improvement_candidates,
    build_learning_checklist,
    build_learning_hypotheses,
)


def _diagnostics() -> tuple[DiagnosticResult, ...]:
    return (
        DiagnosticResult(
            diagnostic_id="diag-1",
            correlation_id="corr-9x",
            category="trace_coverage",
            summary="DTR coverage too low at 50%",
            structured_log_key="build9x.trace",
        ),
        DiagnosticResult(
            diagnostic_id="diag-2",
            correlation_id="corr-9x",
            category="cost_drift",
            summary="Break-even drift observed",
            structured_log_key="build9x.cost",
        ),
    )


def test_hypotheses_target_local_replay_only():
    hypotheses = build_learning_hypotheses("corr-9x", _diagnostics())

    assert len(hypotheses) == 2
    assert all(hypothesis.target_runtime_mode.value == "local_replay" for hypothesis in hypotheses)


def test_checklist_requires_replay_first():
    checklist = build_learning_checklist(
        "corr-9x",
        _diagnostics(),
        ("observability_gap", "cost_model_drift"),
    )

    assert checklist.ready_for_local_replay is True
    assert checklist.ready_for_shadow is False
    assert any("LOCAL_REPLAY" in item for item in checklist.items)


def test_improvement_candidates_stay_replay_only_and_governed():
    hypotheses = build_learning_hypotheses("corr-9x", _diagnostics())
    candidates = build_improvement_candidates(
        "corr-9x",
        StrategyClassification.BUILD14_ENABLER,
        hypotheses,
    )

    assert len(candidates) == 2
    assert all(candidate.promotion_state == PromotionState.REPLAY_ONLY for candidate in candidates)
    assert all(candidate.auto_promotion_enabled is False for candidate in candidates)
    assert any(candidate.kind == CandidateKind.BUILD14_READ_ONLY for candidate in candidates)
    assert all(isinstance(candidate, ImprovementCandidate) for candidate in candidates)


def test_hypotheses_deduplicate_category_and_preserve_first_diagnostic_ref():
    diagnostics = _diagnostics() + (
        DiagnosticResult(
            diagnostic_id="diag-3",
            correlation_id="corr-9x",
            category="cost_drift",
            summary="Another cost drift signal",
            structured_log_key="build9x.cost.2",
        ),
    )

    hypotheses = build_learning_hypotheses("corr-9x", diagnostics)

    assert len(hypotheses) == 2
    cost_hypothesis = next(h for h in hypotheses if h.category == "cost_drift")
    assert cost_hypothesis.diagnostic_ids == ("diag-2",)


def test_unknown_category_falls_back_to_diagnostic_summary():
    diagnostics = (
        DiagnosticResult(
            diagnostic_id="diag-x",
            correlation_id="corr-9x",
            category="novel_case",
            summary="Novel governed observation",
            structured_log_key="build9x.novel",
        ),
    )

    hypotheses = build_learning_hypotheses("corr-9x", diagnostics)

    assert hypotheses[0].rationale == "Novel governed observation"


def test_checklist_stays_not_ready_when_only_no_issue_diagnostic_exists():
    diagnostics = (
        DiagnosticResult(
            diagnostic_id="diag-ok",
            correlation_id="corr-9x",
            category="no_issue",
            summary="No material post-trade issue detected",
            structured_log_key="build9x.no_issue",
        ),
    )

    checklist = build_learning_checklist("corr-9x", diagnostics, ())

    assert checklist.ready_for_local_replay is False
    assert checklist.ready_for_shadow is False
