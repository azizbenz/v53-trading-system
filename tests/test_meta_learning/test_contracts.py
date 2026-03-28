"""Tests for the minimal Build-9X governed scaffold."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import meta_learning
from interface_contracts import (
    EngineId,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
    StrategyClassification,
)
from meta_learning import (
    CandidateKind,
    DiagnosticResult,
    DiagnosticSeverity,
    ImprovementCandidate,
    LearningChecklist,
    LearningHypothesis,
    LearningLifecycleState,
    TradeLearningInput,
)


def test_meta_learning_exports_expected_symbols():
    assert {
        "TradeLearningInput",
        "DiagnosticResult",
        "LearningHypothesis",
        "ImprovementCandidate",
        "LearningChecklist",
    }.issubset(set(meta_learning.__all__))


def test_trade_learning_input_rejects_backtest_profile():
    with pytest.raises(ValidationError):
        TradeLearningInput(
            correlation_id="corr-1",
            dtr_ids=("dtr-1",),
            pair="BTCUSDT",
            engine_id=EngineId.A,
            profile=ProfileId.LIGHT,
            source_runtime_mode=RuntimeMode.SHADOW,
            strategy_classification=StrategyClassification.A_VARIANT,
            source_version="v5.3.0",
            backtest_profile="paper_local",
        )


def test_learning_hypothesis_targets_local_replay_only():
    with pytest.raises(ValidationError):
        LearningHypothesis(
            hypothesis_id="hyp-1",
            correlation_id="corr-1",
            title="Investigate CRA spike",
            rationale="Sterilization increased materially",
            target_runtime_mode=RuntimeMode.SHADOW,
        )


def test_improvement_candidate_blocks_live_candidate_states():
    with pytest.raises(ValidationError):
        ImprovementCandidate(
            candidate_id="cand-1",
            correlation_id="corr-1",
            classification=StrategyClassification.A_VARIANT,
            kind=CandidateKind.PARAMETER_TUNING,
            summary="Tighten spread guard after replay",
            promotion_state=PromotionState.LIVE_CANDIDATE,
        )


def test_learning_checklist_requires_local_replay_before_shadow():
    with pytest.raises(ValidationError):
        LearningChecklist(
            checklist_id="chk-1",
            correlation_id="corr-1",
            items=("export replay bundle",),
            ready_for_local_replay=False,
            ready_for_shadow=True,
        )


def test_diagnostic_contract_builds_with_structured_log_key():
    diagnostic = DiagnosticResult(
        diagnostic_id="diag-1",
        correlation_id="corr-1",
        summary="CRA sterilization elevated on engine_b",
        severity=DiagnosticSeverity.WARNING,
        lifecycle_state=LearningLifecycleState.DIAGNOSED,
        structured_log_key="learning.diag.cra",
    )

    assert diagnostic.structured_log_key == "learning.diag.cra"
    assert diagnostic.manual_review_required is True
    assert diagnostic.lifecycle_state == LearningLifecycleState.DIAGNOSED


def test_improvement_candidate_defaults_to_governed_review():
    candidate = ImprovementCandidate(
        candidate_id="cand-2",
        correlation_id="corr-2",
        classification=StrategyClassification.BUILD14_ENABLER,
        kind=CandidateKind.BUILD14_READ_ONLY,
        summary="Keep enrichments read-only in replay",
    )

    assert candidate.promotion_state == PromotionState.REPLAY_ONLY
    assert candidate.review_state == ReviewState.PENDING
    assert candidate.auto_promotion_enabled is False
