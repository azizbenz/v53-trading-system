"""Review-decision and archive-governance helpers for Build-9X."""

from __future__ import annotations

from datetime import datetime, timezone

from interface_contracts import ReviewState
from meta_learning.contracts import (
    ArchiveEligibilityRecord,
    DiagnosticResult,
    ImprovementCandidate,
    LearningHypothesis,
    ReviewDecisionRecord,
)
from meta_learning.enums import (
    CandidateGovernanceStage,
    DiagnosticStatus,
    HypothesisGovernanceStage,
)
from meta_learning.retention_policy import (
    diagnostic_or_hypothesis_retention,
    review_or_promotion_retention,
)


_OPEN_REVIEW_STATES = {
    ReviewState.PENDING,
    ReviewState.IN_REVIEW,
    ReviewState.NEEDS_REVISION,
}

_ACTIVE_REPLAY_STAGES = {
    CandidateGovernanceStage.READY_FOR_REPLAY,
    CandidateGovernanceStage.REPLAY_RUNNING,
}

_PENDING_PROMOTION_CANDIDATE_STAGES = {
    CandidateGovernanceStage.READY_FOR_REPLAY,
    CandidateGovernanceStage.REPLAY_RUNNING,
    CandidateGovernanceStage.REPLAY_PASSED,
    CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
}

_PENDING_PROMOTION_HYPOTHESIS_STAGES = {
    HypothesisGovernanceStage.REPLAY_APPROVED,
    HypothesisGovernanceStage.SHADOW_CANDIDATE,
}

_FINAL_HYPOTHESIS_STAGES = {
    HypothesisGovernanceStage.REPLAY_REJECTED,
    HypothesisGovernanceStage.SHADOW_REJECTED,
    HypothesisGovernanceStage.CLOSED_NO_ACTION,
    HypothesisGovernanceStage.DEPLOYED_VERSIONED,
}

_ARCHIVE_READY_DIAGNOSTIC_STATES = {
    DiagnosticStatus.REVIEWED,
    DiagnosticStatus.ARCHIVED,
}

_TERMINAL_FINAL_VERDICTS = {
    "replay_rejected_closed_no_action",
    "shadow_rejected_closed_no_action",
    "deployed_versioned",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_system_review_decisions(
    *,
    correlation_id: str,
    review_entity_id: str,
    review_blocked_due_to_incomplete_data: bool,
    has_candidates: bool,
) -> tuple[ReviewDecisionRecord, ...]:
    """Create the system-side review decision emitted during orchestration."""

    created_at = _utc_now()
    if review_blocked_due_to_incomplete_data:
        review_state = ReviewState.NEEDS_REVISION
        verdict = "blocked_incomplete_data"
        rationale = "Build-9X review cannot proceed while data completeness is degraded."
        final_verdict_recorded = False
    elif has_candidates:
        review_state = ReviewState.PENDING
        verdict = "human_review_required"
        rationale = "Governed candidates exist and require explicit human review."
        final_verdict_recorded = False
    else:
        review_state = ReviewState.APPROVED
        verdict = "no_action"
        rationale = "No governed candidate requires replay handoff."
        final_verdict_recorded = True

    return (
        ReviewDecisionRecord(
            decision_id=f"{review_entity_id}:system_review",
            review_entity_id=review_entity_id,
            correlation_id=correlation_id,
            actor="system_build9x",
            is_human_review=False,
            review_state=review_state,
            verdict=verdict,
            rationale=rationale,
            final_verdict_recorded=final_verdict_recorded,
            created_at=created_at,
        ),
    )


def append_human_review_decision(
    decisions: tuple[ReviewDecisionRecord, ...],
    *,
    review_entity_id: str,
    correlation_id: str,
    actor: str,
    review_state: ReviewState,
    verdict: str,
    rationale: str = "",
    final_verdict_recorded: bool = False,
) -> tuple[ReviewDecisionRecord, ...]:
    """Append an explicit human review decision to the governed review history."""

    return decisions + (
        ReviewDecisionRecord(
            decision_id=f"{review_entity_id}:human_review:{len(decisions) + 1}",
            review_entity_id=review_entity_id,
            correlation_id=correlation_id,
            actor=actor,
            is_human_review=True,
            review_state=review_state,
            verdict=verdict,
            rationale=rationale,
            final_verdict_recorded=final_verdict_recorded,
            created_at=_utc_now(),
        ),
    )


def build_archive_eligibility(
    *,
    correlation_id: str,
    diagnostics: tuple[DiagnosticResult, ...],
    hypotheses: tuple[LearningHypothesis, ...],
    candidates: tuple[ImprovementCandidate, ...],
    review_decisions: tuple[ReviewDecisionRecord, ...],
) -> tuple[ArchiveEligibilityRecord, ...]:
    """Evaluate whether diagnostics and hypotheses are eligible for archival."""

    latest_decision = review_decisions[-1] if review_decisions else None
    final_verdict_recorded = bool(latest_decision and latest_decision.final_verdict_recorded)
    review_open = (
        latest_decision is None
        or (
            latest_decision.review_state in _OPEN_REVIEW_STATES
            and not latest_decision.final_verdict_recorded
        )
    )
    promotion_closed_by_final_review = bool(
        latest_decision
        and latest_decision.final_verdict_recorded
        and latest_decision.verdict in _TERMINAL_FINAL_VERDICTS
    )
    replay_active = any(
        candidate.governance_stage in _ACTIVE_REPLAY_STAGES
        for candidate in candidates
    )
    pending_promotion = False
    if not promotion_closed_by_final_review:
        pending_promotion = any(
            candidate.governance_stage in _PENDING_PROMOTION_CANDIDATE_STAGES
            for candidate in candidates
        ) or any(
            hypothesis.governance_stage in _PENDING_PROMOTION_HYPOTHESIS_STAGES
            for hypothesis in hypotheses
        )

    assessments: list[ArchiveEligibilityRecord] = []
    for diagnostic in diagnostics:
        retention_until, retention_policy = diagnostic_or_hypothesis_retention(
            diagnostic.created_at,
        )
        blocking_reasons: list[str] = []
        if diagnostic.status not in _ARCHIVE_READY_DIAGNOSTIC_STATES:
            blocking_reasons.append("diagnostic_not_reviewed")
        if not final_verdict_recorded:
            blocking_reasons.append("final_verdict_missing")
        if review_open:
            blocking_reasons.append("review_open")
        if replay_active:
            blocking_reasons.append("replay_active")
        if pending_promotion:
            blocking_reasons.append("promotion_pending")
        assessments.append(
            ArchiveEligibilityRecord(
                entity_kind="diagnostic",
                entity_id=diagnostic.diagnostic_id,
                correlation_id=correlation_id,
                eligible=not blocking_reasons,
                final_verdict_recorded=final_verdict_recorded,
                replay_active=replay_active,
                review_open=review_open,
                pending_promotion=pending_promotion,
                blocking_reasons=tuple(blocking_reasons),
                retention_until=retention_until,
                retention_policy=retention_policy,
            )
        )

    for hypothesis in hypotheses:
        retention_until, retention_policy = diagnostic_or_hypothesis_retention(
            hypothesis.created_at,
        )
        blocking_reasons: list[str] = []
        if hypothesis.governance_stage not in _FINAL_HYPOTHESIS_STAGES:
            blocking_reasons.append("hypothesis_not_final")
        if not final_verdict_recorded:
            blocking_reasons.append("final_verdict_missing")
        if review_open:
            blocking_reasons.append("review_open")
        if replay_active:
            blocking_reasons.append("replay_active")
        if pending_promotion:
            blocking_reasons.append("promotion_pending")
        assessments.append(
            ArchiveEligibilityRecord(
                entity_kind="hypothesis",
                entity_id=hypothesis.hypothesis_id,
                correlation_id=correlation_id,
                eligible=not blocking_reasons,
                final_verdict_recorded=final_verdict_recorded,
                replay_active=replay_active,
                review_open=review_open,
                pending_promotion=pending_promotion,
                blocking_reasons=tuple(blocking_reasons),
                retention_until=retention_until,
                retention_policy=retention_policy,
            )
        )

    return tuple(assessments)


__all__ = [
    "append_human_review_decision",
    "build_archive_eligibility",
    "build_system_review_decisions",
]
