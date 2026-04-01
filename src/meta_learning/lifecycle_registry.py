"""Canonical Build-9X lifecycle transition helpers."""

from __future__ import annotations

from collections.abc import Iterable

from meta_learning.contracts import (
    DiagnosticResult,
    ImprovementCandidate,
    LearningHypothesis,
    LifecycleTransitionRecord,
)
from meta_learning.enums import (
    CandidateGovernanceStage,
    DiagnosticStatus,
    HypothesisGovernanceStage,
)


_DIAGNOSTIC_TRANSITIONS = {
    DiagnosticStatus.OPEN: {
        DiagnosticStatus.ESCALATED,
        DiagnosticStatus.REVIEWED,
    },
    DiagnosticStatus.ESCALATED: {
        DiagnosticStatus.REVIEWED,
    },
    DiagnosticStatus.REVIEWED: {
        DiagnosticStatus.ARCHIVED,
    },
    DiagnosticStatus.ARCHIVED: set(),
}

_HYPOTHESIS_TRANSITIONS = {
    HypothesisGovernanceStage.DRAFT: {
        HypothesisGovernanceStage.UNDER_REVIEW,
    },
    HypothesisGovernanceStage.UNDER_REVIEW: {
        HypothesisGovernanceStage.REPLAY_APPROVED,
        HypothesisGovernanceStage.REPLAY_REJECTED,
    },
    HypothesisGovernanceStage.REPLAY_APPROVED: {
        HypothesisGovernanceStage.SHADOW_CANDIDATE,
    },
    HypothesisGovernanceStage.REPLAY_REJECTED: {
        HypothesisGovernanceStage.CLOSED_NO_ACTION,
    },
    HypothesisGovernanceStage.SHADOW_CANDIDATE: {
        HypothesisGovernanceStage.SHADOW_REJECTED,
        HypothesisGovernanceStage.DEPLOYED_VERSIONED,
    },
    HypothesisGovernanceStage.SHADOW_REJECTED: {
        HypothesisGovernanceStage.CLOSED_NO_ACTION,
    },
    HypothesisGovernanceStage.CLOSED_NO_ACTION: set(),
    HypothesisGovernanceStage.DEPLOYED_VERSIONED: set(),
}

_CANDIDATE_TRANSITIONS = {
    CandidateGovernanceStage.PREPARED: {
        CandidateGovernanceStage.TESTS_PENDING,
    },
    CandidateGovernanceStage.TESTS_PENDING: {
        CandidateGovernanceStage.READY_FOR_REPLAY,
    },
    CandidateGovernanceStage.READY_FOR_REPLAY: {
        CandidateGovernanceStage.REPLAY_RUNNING,
    },
    CandidateGovernanceStage.REPLAY_RUNNING: {
        CandidateGovernanceStage.REPLAY_FAILED,
        CandidateGovernanceStage.REPLAY_PASSED,
    },
    CandidateGovernanceStage.REPLAY_FAILED: {
        CandidateGovernanceStage.RETIRED,
    },
    CandidateGovernanceStage.REPLAY_PASSED: {
        CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
    },
    CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW: set(),
    CandidateGovernanceStage.RETIRED: set(),
}


def _transition_record(
    *,
    entity_kind: str,
    entity_id: str,
    correlation_id: str,
    from_state: str,
    to_state: str,
    actor: str,
    reason: str,
) -> LifecycleTransitionRecord:
    return LifecycleTransitionRecord(
        transition_id=f"{entity_id}:{from_state}->{to_state}",
        entity_kind=entity_kind,
        entity_id=entity_id,
        correlation_id=correlation_id,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        reason=reason,
    )


def _assert_allowed(current: object, target: object, allowed: dict[object, set[object]], *, entity_kind: str) -> None:
    if target not in allowed.get(current, set()):
        raise ValueError(
            f"Forbidden {entity_kind} transition: {getattr(current, 'value', current)} -> {getattr(target, 'value', target)}"
        )


def transition_diagnostic(
    diagnostic: DiagnosticResult,
    target_status: DiagnosticStatus,
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[DiagnosticResult, LifecycleTransitionRecord]:
    """Advance a diagnostic along the canonical Build-9X state machine."""

    _assert_allowed(diagnostic.status, target_status, _DIAGNOSTIC_TRANSITIONS, entity_kind="diagnostic")
    updated = diagnostic.model_copy(update={"status": target_status})
    transition = _transition_record(
        entity_kind="diagnostic",
        entity_id=diagnostic.diagnostic_id,
        correlation_id=diagnostic.correlation_id,
        from_state=diagnostic.status.value,
        to_state=target_status.value,
        actor=actor,
        reason=reason,
    )
    return updated, transition


def transition_hypothesis(
    hypothesis: LearningHypothesis,
    target_stage: HypothesisGovernanceStage,
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[LearningHypothesis, LifecycleTransitionRecord]:
    """Advance a hypothesis along the canonical Build-9X state machine."""

    _assert_allowed(
        hypothesis.governance_stage,
        target_stage,
        _HYPOTHESIS_TRANSITIONS,
        entity_kind="hypothesis",
    )
    updated = hypothesis.model_copy(update={"governance_stage": target_stage})
    transition = _transition_record(
        entity_kind="hypothesis",
        entity_id=hypothesis.hypothesis_id,
        correlation_id=hypothesis.correlation_id,
        from_state=hypothesis.governance_stage.value,
        to_state=target_stage.value,
        actor=actor,
        reason=reason,
    )
    return updated, transition


def transition_candidate(
    candidate: ImprovementCandidate,
    target_stage: CandidateGovernanceStage,
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[ImprovementCandidate, LifecycleTransitionRecord]:
    """Advance a candidate along the canonical Build-9X state machine."""

    _assert_allowed(
        candidate.governance_stage,
        target_stage,
        _CANDIDATE_TRANSITIONS,
        entity_kind="candidate",
    )
    updated = candidate.model_copy(update={"governance_stage": target_stage})
    transition = _transition_record(
        entity_kind="candidate",
        entity_id=candidate.candidate_id,
        correlation_id=candidate.correlation_id,
        from_state=candidate.governance_stage.value,
        to_state=target_stage.value,
        actor=actor,
        reason=reason,
    )
    return updated, transition


def apply_diagnostic_path(
    diagnostic: DiagnosticResult,
    path: Iterable[DiagnosticStatus],
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[DiagnosticResult, tuple[LifecycleTransitionRecord, ...]]:
    current = diagnostic
    transitions: list[LifecycleTransitionRecord] = []
    for target in path:
        current, transition = transition_diagnostic(
            current,
            target,
            actor=actor,
            reason=reason,
        )
        transitions.append(transition)
    return current, tuple(transitions)


def apply_hypothesis_path(
    hypothesis: LearningHypothesis,
    path: Iterable[HypothesisGovernanceStage],
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[LearningHypothesis, tuple[LifecycleTransitionRecord, ...]]:
    current = hypothesis
    transitions: list[LifecycleTransitionRecord] = []
    for target in path:
        current, transition = transition_hypothesis(
            current,
            target,
            actor=actor,
            reason=reason,
        )
        transitions.append(transition)
    return current, tuple(transitions)


def apply_candidate_path(
    candidate: ImprovementCandidate,
    path: Iterable[CandidateGovernanceStage],
    *,
    actor: str = "system_build9x",
    reason: str = "",
) -> tuple[ImprovementCandidate, tuple[LifecycleTransitionRecord, ...]]:
    current = candidate
    transitions: list[LifecycleTransitionRecord] = []
    for target in path:
        current, transition = transition_candidate(
            current,
            target,
            actor=actor,
            reason=reason,
        )
        transitions.append(transition)
    return current, tuple(transitions)


__all__ = [
    "apply_candidate_path",
    "apply_diagnostic_path",
    "apply_hypothesis_path",
    "transition_candidate",
    "transition_diagnostic",
    "transition_hypothesis",
]
