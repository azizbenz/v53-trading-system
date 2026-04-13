"""Bounded Local IA Lab replay/research queue derived from current planning truth."""

from __future__ import annotations

from pydantic import BaseModel, Field

from local_replay_runtime.local_lab_recalibration_plan import LocalLabRecalibrationPlan
from local_replay_runtime.local_lab_research_priority import (
    LocalLabResearchPriorityReport,
    LocalLabResearchPriorityScope,
)


class LocalLabReplayCandidate(BaseModel, frozen=True):
    """One bounded Local IA Lab replay/research candidate."""

    replay_rank: int = Field(..., ge=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    priority_rank: int = Field(..., ge=1)
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    priority_band: str = Field(..., min_length=1)
    recommended_next_action: str = Field(..., min_length=1)
    queue_status: str = Field(..., min_length=1)
    surrogate_top_risk_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_threshold_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()


class LocalLabReplayCandidateQueue(BaseModel, frozen=True):
    """Audit-ready queue of next bounded Local IA Lab replay steps."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    candidate_count: int = Field(default=0, ge=0)
    ready_candidate_count: int = Field(default=0, ge=0)
    blocked_candidate_count: int = Field(default=0, ge=0)
    top_scope_slug: str = ""
    top_priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    candidates: tuple[LocalLabReplayCandidate, ...] = ()


def build_local_lab_replay_candidate_queue(
    *,
    correlation_id: str,
    export_dir: str,
    research_priority_report: LocalLabResearchPriorityReport,
    recalibration_plan: LocalLabRecalibrationPlan,
    max_candidates: int = 5,
) -> LocalLabReplayCandidateQueue:
    """Build a bounded local-only queue for next replay/research cycles."""

    ranked_candidates: list[LocalLabReplayCandidate] = []
    for scope in research_priority_report.scopes:
        if not _should_enqueue(scope):
            continue
        queue_status, blocking_reasons = _build_queue_status(scope, recalibration_plan)
        ranked_candidates.append(
            LocalLabReplayCandidate(
                replay_rank=1,
                pair=scope.pair,
                engine_id=scope.engine_id,
                scope_slug=scope.scope_slug,
                priority_rank=scope.priority_rank,
                priority_score=scope.priority_score,
                priority_band=scope.priority_band,
                recommended_next_action=scope.recommended_next_action,
                queue_status=queue_status,
                surrogate_top_risk_probability=scope.features.surrogate_top_risk_probability,
                recommended_threshold_ids=scope.recommended_threshold_ids,
                reason_codes=scope.reason_codes,
                blocking_reasons=blocking_reasons,
            )
        )

    ranked_candidates = sorted(
        ranked_candidates,
        key=lambda candidate: (-candidate.priority_score, candidate.priority_rank, candidate.scope_slug),
    )[:max_candidates]
    replay_candidates = tuple(
        candidate.model_copy(update={"replay_rank": index + 1})
        for index, candidate in enumerate(ranked_candidates)
    )
    ready_candidate_count = sum(
        1 for candidate in replay_candidates if candidate.queue_status == "ready_for_local_replay"
    )
    blocked_candidate_count = sum(
        1 for candidate in replay_candidates if candidate.queue_status != "ready_for_local_replay"
    )
    if not replay_candidates:
        status = "no_candidates"
        top_scope_slug = ""
        top_priority_score = 0.0
    elif ready_candidate_count > 0:
        status = "ready"
        top_scope_slug = replay_candidates[0].scope_slug
        top_priority_score = replay_candidates[0].priority_score
    else:
        status = "blocked_only"
        top_scope_slug = replay_candidates[0].scope_slug
        top_priority_score = replay_candidates[0].priority_score

    return LocalLabReplayCandidateQueue(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=status,
        candidate_count=len(replay_candidates),
        ready_candidate_count=ready_candidate_count,
        blocked_candidate_count=blocked_candidate_count,
        top_scope_slug=top_scope_slug,
        top_priority_score=top_priority_score,
        candidates=replay_candidates,
    )


def _should_enqueue(scope: LocalLabResearchPriorityScope) -> bool:
    if scope.priority_band in {"research_now", "research_next"}:
        return True
    return scope.recommended_next_action in {
        "replay_high_risk_scope",
        "replay_recalibration_candidate",
        "improve_trace_capture",
        "review_scope_sterilization",
        "manual_loss_review",
    }


def _build_queue_status(
    scope: LocalLabResearchPriorityScope,
    recalibration_plan: LocalLabRecalibrationPlan,
) -> tuple[str, tuple[str, ...]]:
    blocking_reasons: list[str] = []
    if scope.recommended_next_action == "improve_trace_capture":
        blocking_reasons.append("TRACE_CAPTURE_REQUIRED")
        return "blocked_on_trace_capture", tuple(blocking_reasons)
    if scope.recommended_next_action == "review_scope_sterilization":
        blocking_reasons.append("HUMAN_SCOPE_REVIEW_REQUIRED")
        return "needs_human_scope_review", tuple(blocking_reasons)
    if scope.recommended_next_action == "manual_loss_review":
        blocking_reasons.append("MANUAL_LOSS_REVIEW_REQUIRED")
        return "needs_manual_review", tuple(blocking_reasons)
    if scope.recommended_next_action == "replay_recalibration_candidate":
        if "TRACE_COVERAGE_BLOCKS_RECALIBRATION" in recalibration_plan.blocking_reasons:
            blocking_reasons.append("TRACE_COVERAGE_BLOCKS_REPLAY")
        if "SCOPE_MATRIX_NOT_FULLY_READY" in recalibration_plan.blocking_reasons:
            blocking_reasons.append("SCOPE_MATRIX_NOT_FULLY_READY")
    return (
        "ready_for_local_replay" if not blocking_reasons else "blocked_for_local_replay",
        tuple(dict.fromkeys(blocking_reasons)),
    )


__all__ = [
    "LocalLabReplayCandidate",
    "LocalLabReplayCandidateQueue",
    "build_local_lab_replay_candidate_queue",
]
