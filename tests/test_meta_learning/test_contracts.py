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
    ArchiveEligibilityRecord,
    apply_candidate_path,
    apply_hypothesis_path,
    CandidateGovernanceStage,
    CandidateKind,
    DiagnosticResult,
    DiagnosticStatus,
    DiagnosticSeverity,
    EvidenceStrength,
    HypothesisGovernanceStage,
    ImprovementCandidate,
    LearningBacklogState,
    LearningCapacitySnapshot,
    LearningCaptureMode,
    LearningChecklist,
    LearningHypothesis,
    LearningLifecycleState,
    ReviewDecisionRecord,
    TradeLearningInput,
    evaluate_learning_capacity,
)


def test_meta_learning_exports_expected_symbols():
    assert {
        "TradeLearningInput",
        "DiagnosticResult",
        "LearningHypothesis",
        "ImprovementCandidate",
        "LearningChecklist",
        "ReviewQueueEntry",
        "build_review_queue",
        "MetaLearningFacadeProtocol",
        "MetaLearningFacade",
        "MetaLearningReviewBundle",
        "apply_candidate_replay_results",
        "apply_human_review_resolution",
        "run_meta_learning_review",
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
        status=DiagnosticStatus.OPEN,
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
        kind=CandidateKind.BUILD14_ENABLER,
        summary="Keep Build-14 enrichments governed in replay",
    )

    assert candidate.promotion_state == PromotionState.REPLAY_ONLY
    assert candidate.review_state == ReviewState.PENDING
    assert candidate.auto_promotion_enabled is False


def test_replay_approved_hypothesis_requires_statistical_fields():
    with pytest.raises(ValidationError, match="REPLAY_APPROVED"):
        LearningHypothesis(
            hypothesis_id="hyp-2",
            correlation_id="corr-2",
            title="Replay candidate",
            rationale="Needs replay",
            governance_stage=HypothesisGovernanceStage.REPLAY_APPROVED,
        )


def test_replay_approved_hypothesis_accepts_complete_governance_payload():
    hypothesis = LearningHypothesis(
        hypothesis_id="hyp-3",
        correlation_id="corr-3",
        title="Replay candidate",
        rationale="Evidence is sufficient for governed replay",
        target_component="meta_minimal.cra_monitor",
        signal_family="economics",
        expected_replay_evidence=("ce_net_delta", "sterilization_rate_delta"),
        expected_shadow_evidence=("shadow_sterilization_rate",),
        sample_size=2,
        segmentation_used=("engine_scope", "pair_scope"),
        risk_of_regression="medium",
        comparison_metrics=("ce_net", "dtr_coverage"),
        rejection_criteria=("economic regression",),
        evidence_strength=EvidenceStrength.WEAK_PATTERN,
        governance_stage=HypothesisGovernanceStage.REPLAY_APPROVED,
    )

    assert hypothesis.governance_stage == HypothesisGovernanceStage.REPLAY_APPROVED
    assert hypothesis.target_component == "meta_minimal.cra_monitor"


def test_replay_approved_hypothesis_requires_enrichment_mapping_fields():
    with pytest.raises(ValidationError, match="target_component"):
        LearningHypothesis(
            hypothesis_id="hyp-3b",
            correlation_id="corr-3b",
            title="Replay candidate",
            rationale="Evidence is sufficient for governed replay",
            sample_size=2,
            segmentation_used=("engine_scope", "pair_scope"),
            risk_of_regression="medium",
            comparison_metrics=("ce_net", "dtr_coverage"),
            rejection_criteria=("economic regression",),
            evidence_strength=EvidenceStrength.WEAK_PATTERN,
            governance_stage=HypothesisGovernanceStage.REPLAY_APPROVED,
        )


def test_ready_for_replay_candidate_requires_replay_refs():
    with pytest.raises(ValidationError, match="Replay-ready candidate stages"):
        ImprovementCandidate(
            candidate_id="cand-3",
            correlation_id="corr-3",
            classification=StrategyClassification.A_VARIANT,
            kind=CandidateKind.PARAMETER_TUNING,
            summary="Ready candidate without refs",
            governance_stage=CandidateGovernanceStage.READY_FOR_REPLAY,
        )


def test_capacity_snapshot_requires_backpressure_signal_when_active():
    with pytest.raises(ValidationError, match="backpressure_signal_key"):
        LearningCapacitySnapshot(
            backpressure_active=True,
            capture_mode=LearningCaptureMode.CAPTURE_MINIMALE,
            backlog_state=LearningBacklogState.PROTECTION,
        )


def test_evaluate_learning_capacity_degrades_to_capture_minimale_on_protection_threshold():
    snapshot = evaluate_learning_capacity(
        queue_depth=6200,
        queue_oldest_age_ms=1200,
        log_loss_total=1,
    )

    assert snapshot.backlog_state == LearningBacklogState.PROTECTION
    assert snapshot.capture_mode == LearningCaptureMode.CAPTURE_MINIMALE
    assert snapshot.backpressure_active is True
    assert snapshot.review_blocked_due_to_incomplete_data is True
    assert "learning.storage.backpressure" in snapshot.blocking_reasons


def test_hypothesis_canonical_path_accepts_under_review_then_replay_approved():
    hypothesis = LearningHypothesis(
        hypothesis_id="hyp-4",
        correlation_id="corr-4",
        title="Governed lifecycle path",
        rationale="Enough evidence for governed pathing",
        sample_size=2,
        segmentation_used=("engine_scope", "pair_scope"),
        risk_of_regression="medium",
        comparison_metrics=("ce_net",),
        rejection_criteria=("economic regression",),
    )

    updated, transitions = apply_hypothesis_path(
        hypothesis,
        (
            HypothesisGovernanceStage.UNDER_REVIEW,
            HypothesisGovernanceStage.REPLAY_APPROVED,
        ),
    )

    assert updated.governance_stage == HypothesisGovernanceStage.REPLAY_APPROVED
    assert transitions[0].from_state == "draft"
    assert transitions[1].to_state == "replay_approved"


def test_candidate_canonical_path_rejects_skipping_tests_pending():
    candidate = ImprovementCandidate(
        candidate_id="cand-4",
        correlation_id="corr-4",
        classification=StrategyClassification.A_VARIANT,
        kind=CandidateKind.PARAMETER_TUNING,
        summary="Invalid lifecycle shortcut",
        tests_required=("tests/test_meta_learning/test_contracts.py",),
        replay_scope="cost_drift:local_replay",
        replay_bundle_reference="bundle-1",
        comparison_protocol_reference="proto-1",
        shared_core_hash="abc123",
    )

    with pytest.raises(ValueError, match="Forbidden candidate transition"):
        apply_candidate_path(
            candidate,
            (CandidateGovernanceStage.READY_FOR_REPLAY,),
        )


def test_human_review_decision_requires_non_system_actor():
    with pytest.raises(ValidationError, match="non-system actor"):
        ReviewDecisionRecord(
            decision_id="decision-1",
            review_entity_id="meta_learning_review:corr-1",
            correlation_id="corr-1",
            actor="system_build9x",
            is_human_review=True,
            review_state=ReviewState.APPROVED,
            verdict="accepted",
            final_verdict_recorded=True,
        )


def test_archive_eligibility_rejects_blocking_reasons_when_eligible():
    with pytest.raises(ValidationError, match="Archive-eligible"):
        ArchiveEligibilityRecord(
            entity_kind="diagnostic",
            entity_id="diag-1",
            correlation_id="corr-1",
            eligible=True,
            blocking_reasons=("review_open",),
        )
