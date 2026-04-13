"""Manifest over Local IA Lab replay workflow sidecars."""

from __future__ import annotations

from pydantic import BaseModel, Field

from local_replay_runtime.local_lab_replay_candidate_queue import LocalLabReplayCandidateQueue
from local_replay_runtime.local_lab_replay_dispatch_plan import LocalLabReplayDispatchPlan
from local_replay_runtime.local_lab_replay_ticket_index import LocalLabReplayTicketIndex


class LocalLabReplayWorkflowManifest(BaseModel, frozen=True):
    """Stable manifest for future automation over Local IA Lab replay workflow sidecars."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    replay_candidate_queue_path: str = Field(..., min_length=1)
    replay_ticket_index_path: str = Field(..., min_length=1)
    replay_dispatch_plan_path: str = Field(..., min_length=1)
    replay_candidate_queue_status: str = Field(..., min_length=1)
    replay_ticket_index_status: str = Field(..., min_length=1)
    replay_dispatch_plan_status: str = Field(..., min_length=1)
    replay_candidate_count: int = Field(default=0, ge=0)
    replay_ticket_count: int = Field(default=0, ge=0)
    replay_dispatch_ready_count: int = Field(default=0, ge=0)
    replay_dispatch_blocked_count: int = Field(default=0, ge=0)


def build_local_lab_replay_workflow_manifest(
    *,
    replay_candidate_queue: LocalLabReplayCandidateQueue,
    replay_candidate_queue_path: str,
    replay_ticket_index: LocalLabReplayTicketIndex,
    replay_ticket_index_path: str,
    replay_dispatch_plan: LocalLabReplayDispatchPlan,
    replay_dispatch_plan_path: str,
) -> LocalLabReplayWorkflowManifest:
    """Build a stable manifest over the replay workflow sidecars."""

    if replay_candidate_queue.correlation_id != replay_ticket_index.correlation_id:
        raise ValueError(
            "Replay workflow manifest requires matching correlation_id between candidate queue and ticket index"
        )
    if replay_candidate_queue.correlation_id != replay_dispatch_plan.correlation_id:
        raise ValueError(
            "Replay workflow manifest requires matching correlation_id between candidate queue and dispatch plan"
        )
    if replay_candidate_queue.export_dir != replay_ticket_index.export_dir:
        raise ValueError(
            "Replay workflow manifest requires matching export_dir between candidate queue and ticket index"
        )
    if replay_candidate_queue.export_dir != replay_dispatch_plan.export_dir:
        raise ValueError(
            "Replay workflow manifest requires matching export_dir between candidate queue and dispatch plan"
        )

    return LocalLabReplayWorkflowManifest(
        correlation_id=replay_candidate_queue.correlation_id,
        export_dir=replay_candidate_queue.export_dir,
        replay_candidate_queue_path=replay_candidate_queue_path,
        replay_ticket_index_path=replay_ticket_index_path,
        replay_dispatch_plan_path=replay_dispatch_plan_path,
        replay_candidate_queue_status=replay_candidate_queue.status,
        replay_ticket_index_status=replay_ticket_index.status,
        replay_dispatch_plan_status=replay_dispatch_plan.status,
        replay_candidate_count=replay_candidate_queue.candidate_count,
        replay_ticket_count=replay_ticket_index.ticket_count,
        replay_dispatch_ready_count=replay_dispatch_plan.ready_dispatch_count,
        replay_dispatch_blocked_count=replay_dispatch_plan.blocked_dispatch_count,
    )


__all__ = [
    "LocalLabReplayWorkflowManifest",
    "build_local_lab_replay_workflow_manifest",
]
