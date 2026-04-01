"""Post-review and replay resolution helpers for governed Build-9X bundles."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from interface_contracts import PromotionState, ReviewState
from meta_learning.contracts import (
    ArchiveEligibilityRecord,
    DiagnosticResult,
    ImprovementCandidate,
    LearningHypothesis,
    MetaLearningReviewBundle,
    ReviewDecisionRecord,
)
from meta_learning.enums import (
    CandidateGovernanceStage,
    DiagnosticStatus,
    EvidenceStrength,
    HypothesisGovernanceStage,
)
from meta_learning.learning_review_exporter import export_learning_review
from meta_learning.lifecycle_registry import apply_candidate_path, apply_diagnostic_path, apply_hypothesis_path
from meta_learning.persistence_store import AppendOnlyMetaLearningStore
from meta_learning.review_governance import append_human_review_decision, build_archive_eligibility


_FINAL_HUMAN_RESOLUTIONS = {
    "replay_rejected_closed_no_action",
    "shadow_rejected_closed_no_action",
    "deployed_versioned",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _refresh_bundle(
    bundle: MetaLearningReviewBundle,
    *,
    diagnostics: tuple[DiagnosticResult, ...],
    hypotheses: tuple[LearningHypothesis, ...],
    candidates: tuple[ImprovementCandidate, ...],
    review_decisions: tuple[ReviewDecisionRecord, ...],
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...],
    lifecycle_transitions: Iterable,
    memory_verdict: str,
    memory_rejection_reason: str | None = None,
    memory_archived: bool = False,
) -> MetaLearningReviewBundle:
    memory_record = bundle.memory_record.model_copy(
        update={
            "diagnostic_id": diagnostics[0].diagnostic_id if diagnostics else None,
            "hypothesis_id": hypotheses[0].hypothesis_id if hypotheses else None,
            "candidate_id": candidates[0].candidate_id if candidates else None,
            "verdict": memory_verdict,
            "rejection_reason": memory_rejection_reason,
            "archived": memory_archived,
        }
    )
    review_export = export_learning_review(
        bundle.correlation_id,
        bundle.breakdown_report,
        bundle.checklist,
        candidates,
        hypotheses=hypotheses,
        replay_bundles=bundle.replay_bundles,
        capacity_snapshot=bundle.capacity_snapshot,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=tuple(lifecycle_transitions),
        export_ref=bundle.review_export.export_ref,
    )
    return MetaLearningReviewBundle(
        correlation_id=bundle.correlation_id,
        diagnostics=diagnostics,
        mistake_classes=bundle.mistake_classes,
        breakdown_report=bundle.breakdown_report,
        checklist=bundle.checklist,
        hypotheses=hypotheses,
        candidates=candidates,
        replay_bundles=bundle.replay_bundles,
        memory_record=memory_record,
        review_export=review_export,
        capacity_snapshot=bundle.capacity_snapshot,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=tuple(lifecycle_transitions),
    )


def _mark_archived(
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...],
) -> tuple[ArchiveEligibilityRecord, ...]:
    archived_at = _utc_now()
    return tuple(
        entry.model_copy(update={"archived_at": archived_at})
        if entry.eligible and entry.archived_at is None
        else entry
        for entry in archive_eligibility
    )


def _finalize_diagnostics_for_review(
    diagnostics: tuple[DiagnosticResult, ...],
    *,
    actor: str,
    reason: str,
) -> tuple[tuple[DiagnosticResult, ...], tuple]:
    updated: list[DiagnosticResult] = []
    transitions = []
    for diagnostic in diagnostics:
        if diagnostic.status == DiagnosticStatus.ARCHIVED:
            updated.append(diagnostic)
            continue
        path = ()
        if diagnostic.status == DiagnosticStatus.OPEN:
            path = (DiagnosticStatus.REVIEWED,)
        elif diagnostic.status == DiagnosticStatus.ESCALATED:
            path = (DiagnosticStatus.REVIEWED,)
        if not path:
            updated.append(diagnostic)
            continue
        current, current_transitions = apply_diagnostic_path(
            diagnostic,
            path,
            actor=actor,
            reason=reason,
        )
        updated.append(current)
        transitions.extend(current_transitions)
    return tuple(updated), tuple(transitions)


def _require_replay_approved_hypotheses(
    candidate: ImprovementCandidate,
    hypotheses_by_id: dict[str, LearningHypothesis],
) -> None:
    if not candidate.hypothesis_ids:
        raise ValueError(
            f"Replay resolution requires linked hypotheses for candidate {candidate.candidate_id}"
        )
    missing = sorted(
        hypothesis_id
        for hypothesis_id in candidate.hypothesis_ids
        if hypothesis_id not in hypotheses_by_id
    )
    if missing:
        raise ValueError(
            f"Replay resolution references unknown hypotheses for {candidate.candidate_id}: {missing}"
        )
    unapproved = sorted(
        hypothesis_id
        for hypothesis_id in candidate.hypothesis_ids
        if hypotheses_by_id[hypothesis_id].governance_stage
        != HypothesisGovernanceStage.REPLAY_APPROVED
    )
    if unapproved:
        raise ValueError(
            "Replay resolution requires linked hypotheses in REPLAY_APPROVED, "
            f"found non-approved hypotheses for {candidate.candidate_id}: {unapproved}"
        )


def _require_candidate_support_for_hypotheses(
    bundle: MetaLearningReviewBundle,
    *,
    hypothesis_stage: HypothesisGovernanceStage,
    candidate_stage: CandidateGovernanceStage,
    resolution: str,
) -> None:
    expected_hypothesis_ids = {
        hypothesis.hypothesis_id
        for hypothesis in bundle.hypotheses
        if hypothesis.governance_stage == hypothesis_stage
    }
    supported_hypothesis_ids = {
        hypothesis_id
        for candidate in bundle.candidates
        if candidate.governance_stage == candidate_stage
        for hypothesis_id in candidate.hypothesis_ids
    }
    missing_hypothesis_ids = sorted(expected_hypothesis_ids - supported_hypothesis_ids)
    if missing_hypothesis_ids:
        raise ValueError(
            f"{resolution} requires every {hypothesis_stage.value} hypothesis to be backed "
            f"by a {candidate_stage.value} candidate: {missing_hypothesis_ids}"
        )


def _archive_diagnostics_if_eligible(
    diagnostics: tuple[DiagnosticResult, ...],
    archive_eligibility: tuple[ArchiveEligibilityRecord, ...],
    *,
    actor: str,
    reason: str,
) -> tuple[tuple[DiagnosticResult, ...], tuple]:
    eligible_diagnostic_ids = {
        entry.entity_id
        for entry in archive_eligibility
        if entry.entity_kind == "diagnostic" and entry.eligible
    }
    updated: list[DiagnosticResult] = []
    transitions = []
    for diagnostic in diagnostics:
        if diagnostic.diagnostic_id not in eligible_diagnostic_ids:
            updated.append(diagnostic)
            continue
        if diagnostic.status == DiagnosticStatus.ARCHIVED:
            updated.append(diagnostic)
            continue
        current, current_transitions = apply_diagnostic_path(
            diagnostic,
            (DiagnosticStatus.ARCHIVED,),
            actor=actor,
            reason=reason,
        )
        updated.append(current)
        transitions.extend(current_transitions)
    return tuple(updated), tuple(transitions)


def apply_candidate_replay_results(
    bundle: MetaLearningReviewBundle,
    *,
    passed_candidate_ids: tuple[str, ...] = (),
    failed_candidate_ids: tuple[str, ...] = (),
    actor: str = "system_build9x",
    state_dir: Path | None = None,
) -> MetaLearningReviewBundle:
    """Apply canonical replay outcomes to candidate governance stages."""

    passed = set(passed_candidate_ids)
    failed = set(failed_candidate_ids)
    overlap = passed & failed
    if overlap:
        raise ValueError(f"Candidates cannot be both passed and failed: {sorted(overlap)}")

    known_candidate_ids = {candidate.candidate_id for candidate in bundle.candidates}
    unknown = (passed | failed) - known_candidate_ids
    if unknown:
        raise ValueError(f"Unknown candidate ids for replay resolution: {sorted(unknown)}")

    hypotheses_by_id = {
        hypothesis.hypothesis_id: hypothesis
        for hypothesis in bundle.hypotheses
    }
    updated_candidates: list[ImprovementCandidate] = []
    transitions = list(bundle.lifecycle_transitions)
    for candidate in bundle.candidates:
        current = candidate
        if candidate.candidate_id in passed:
            if current.governance_stage != CandidateGovernanceStage.READY_FOR_REPLAY:
                raise ValueError(
                    "Passed replay resolution requires candidates in READY_FOR_REPLAY, "
                    f"found {current.governance_stage.value} for {current.candidate_id}"
                )
            _require_replay_approved_hypotheses(current, hypotheses_by_id)
            current, running_transitions = apply_candidate_path(
                current,
                (
                    CandidateGovernanceStage.REPLAY_RUNNING,
                    CandidateGovernanceStage.REPLAY_PASSED,
                ),
                actor=actor,
                reason="governed replay passed",
            )
            current = current.model_copy(
                update={
                    "promotion_state": PromotionState.SHADOW_CANDIDATE,
                    "validation_notes": current.validation_notes + ("replay_passed",),
                }
            )
            current, shadow_ready_transitions = apply_candidate_path(
                current,
                (CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,),
                actor=actor,
                reason="candidate is ready for shadow review after replay pass",
            )
            transitions.extend(running_transitions)
            transitions.extend(shadow_ready_transitions)
        elif candidate.candidate_id in failed:
            if current.governance_stage != CandidateGovernanceStage.READY_FOR_REPLAY:
                raise ValueError(
                    "Failed replay resolution requires candidates in READY_FOR_REPLAY, "
                    f"found {current.governance_stage.value} for {current.candidate_id}"
                )
            _require_replay_approved_hypotheses(current, hypotheses_by_id)
            current, failed_transitions = apply_candidate_path(
                current,
                (
                    CandidateGovernanceStage.REPLAY_RUNNING,
                    CandidateGovernanceStage.REPLAY_FAILED,
                    CandidateGovernanceStage.RETIRED,
                ),
                actor=actor,
                reason="governed replay failed",
            )
            current = current.model_copy(
                update={
                    "validation_notes": current.validation_notes + ("replay_failed",),
                    "review_state": ReviewState.NEEDS_REVISION,
                }
            )
            transitions.extend(failed_transitions)
        updated_candidates.append(current)

    archive_eligibility = build_archive_eligibility(
        correlation_id=bundle.correlation_id,
        diagnostics=bundle.diagnostics,
        hypotheses=bundle.hypotheses,
        candidates=tuple(updated_candidates),
        review_decisions=bundle.review_decisions,
    )
    updated_bundle = _refresh_bundle(
        bundle,
        diagnostics=bundle.diagnostics,
        hypotheses=bundle.hypotheses,
        candidates=tuple(updated_candidates),
        review_decisions=bundle.review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=tuple(transitions),
        memory_verdict=(
            "replay_passed_ready_for_shadow_review"
            if passed and not failed
            else "replay_failed_retired"
            if failed and not passed
            else "replay_mixed_outcome_recorded"
        ),
        memory_rejection_reason=(
            "one_or_more_replay_failures"
            if failed
            else None
        ),
        memory_archived=False,
    )
    if state_dir is not None:
        AppendOnlyMetaLearningStore(state_dir).append_review_bundle(updated_bundle)
    return updated_bundle


def apply_human_review_resolution(
    bundle: MetaLearningReviewBundle,
    *,
    actor: str,
    resolution: str,
    rationale: str = "",
    state_dir: Path | None = None,
) -> MetaLearningReviewBundle:
    """Apply a governed human resolution and propagate terminal transitions."""

    if resolution not in {
        "replay_approved",
        "replay_rejected_closed_no_action",
        "shadow_candidate_approved",
        "shadow_rejected_closed_no_action",
        "deployed_versioned",
    }:
        raise ValueError(f"Unsupported human review resolution: {resolution}")

    updated_hypotheses: list[LearningHypothesis] = []
    transitions = list(bundle.lifecycle_transitions)
    if resolution == "replay_approved":
        review_state = ReviewState.APPROVED
        final_verdict_recorded = False
        expected_stage = HypothesisGovernanceStage.UNDER_REVIEW
        path = (HypothesisGovernanceStage.REPLAY_APPROVED,)
    elif resolution == "replay_rejected_closed_no_action":
        review_state = ReviewState.REJECTED
        final_verdict_recorded = True
        expected_stage = HypothesisGovernanceStage.UNDER_REVIEW
        path = (
            HypothesisGovernanceStage.REPLAY_REJECTED,
            HypothesisGovernanceStage.CLOSED_NO_ACTION,
        )
    elif resolution == "shadow_candidate_approved":
        review_state = ReviewState.APPROVED
        final_verdict_recorded = False
        expected_stage = HypothesisGovernanceStage.REPLAY_APPROVED
        path = (HypothesisGovernanceStage.SHADOW_CANDIDATE,)
        _require_candidate_support_for_hypotheses(
            bundle,
            hypothesis_stage=HypothesisGovernanceStage.REPLAY_APPROVED,
            candidate_stage=CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
            resolution="shadow_candidate_approved",
        )
    elif resolution == "shadow_rejected_closed_no_action":
        review_state = ReviewState.REJECTED
        final_verdict_recorded = True
        expected_stage = HypothesisGovernanceStage.SHADOW_CANDIDATE
        path = (
            HypothesisGovernanceStage.SHADOW_REJECTED,
            HypothesisGovernanceStage.CLOSED_NO_ACTION,
        )
        _require_candidate_support_for_hypotheses(
            bundle,
            hypothesis_stage=HypothesisGovernanceStage.SHADOW_CANDIDATE,
            candidate_stage=CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
            resolution="shadow_rejected_closed_no_action",
        )
    else:
        review_state = ReviewState.APPROVED
        final_verdict_recorded = True
        expected_stage = HypothesisGovernanceStage.SHADOW_CANDIDATE
        path = (HypothesisGovernanceStage.DEPLOYED_VERSIONED,)
        _require_candidate_support_for_hypotheses(
            bundle,
            hypothesis_stage=HypothesisGovernanceStage.SHADOW_CANDIDATE,
            candidate_stage=CandidateGovernanceStage.READY_FOR_SHADOW_REVIEW,
            resolution="deployed_versioned",
        )

    for hypothesis in bundle.hypotheses:
        if hypothesis.governance_stage != expected_stage:
            raise ValueError(
                f"Resolution {resolution} requires hypotheses in stage {expected_stage.value}, found {hypothesis.governance_stage.value}"
            )
        current, current_transitions = apply_hypothesis_path(
            hypothesis,
            path,
            actor=actor,
            reason=resolution,
        )
        if current.governance_stage == HypothesisGovernanceStage.REPLAY_APPROVED:
            current = current.model_copy(
                update={
                    "shadow_candidate_allowed": current.evidence_strength
                    in {
                        EvidenceStrength.REPEATABLE_PATTERN,
                        EvidenceStrength.ROBUST_CANDIDATE,
                    }
                }
            )
        updated_hypotheses.append(current)
        transitions.extend(current_transitions)

    updated_diagnostics = bundle.diagnostics
    if final_verdict_recorded:
        updated_diagnostics, review_transitions = _finalize_diagnostics_for_review(
            updated_diagnostics,
            actor=actor,
            reason=f"human review finalized: {resolution}",
        )
        transitions.extend(review_transitions)

    review_decisions = append_human_review_decision(
        bundle.review_decisions,
        review_entity_id=bundle.review_export.export_ref,
        correlation_id=bundle.correlation_id,
        actor=actor,
        review_state=review_state,
        verdict=resolution,
        rationale=rationale,
        final_verdict_recorded=final_verdict_recorded,
    )
    archive_eligibility = build_archive_eligibility(
        correlation_id=bundle.correlation_id,
        diagnostics=updated_diagnostics,
        hypotheses=tuple(updated_hypotheses),
        candidates=bundle.candidates,
        review_decisions=review_decisions,
    )
    memory_archived = False
    if final_verdict_recorded:
        updated_diagnostics, archive_transitions = _archive_diagnostics_if_eligible(
            updated_diagnostics,
            archive_eligibility,
            actor=actor,
            reason="archive applied after final governed review",
        )
        transitions.extend(archive_transitions)
        archive_eligibility = build_archive_eligibility(
            correlation_id=bundle.correlation_id,
            diagnostics=updated_diagnostics,
            hypotheses=tuple(updated_hypotheses),
            candidates=bundle.candidates,
            review_decisions=review_decisions,
        )
        archive_eligibility = _mark_archived(archive_eligibility)
        memory_archived = all(
            entry.archived_at is not None
            for entry in archive_eligibility
        ) if archive_eligibility else False

    updated_bundle = _refresh_bundle(
        bundle,
        diagnostics=updated_diagnostics,
        hypotheses=tuple(updated_hypotheses),
        candidates=bundle.candidates,
        review_decisions=review_decisions,
        archive_eligibility=archive_eligibility,
        lifecycle_transitions=tuple(transitions),
        memory_verdict=resolution,
        memory_rejection_reason=rationale or None,
        memory_archived=memory_archived,
    )
    if state_dir is not None:
        AppendOnlyMetaLearningStore(state_dir).append_review_bundle(updated_bundle)
    return updated_bundle


__all__ = [
    "apply_candidate_replay_results",
    "apply_human_review_resolution",
]
