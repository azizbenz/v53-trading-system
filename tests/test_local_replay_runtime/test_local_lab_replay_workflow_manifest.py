from __future__ import annotations

from local_replay_runtime import (
    LocalLabReplayCandidateQueue,
    LocalLabReplayDispatchPlan,
    LocalLabReplayTicketIndex,
)
from local_replay_runtime.local_lab_replay_workflow_manifest import (
    build_local_lab_replay_workflow_manifest,
)


def test_build_local_lab_replay_workflow_manifest_aligns_workflow_sidecars():
    queue = LocalLabReplayCandidateQueue(
        correlation_id="corr-workflow",
        export_dir="E:/lab/export_dir",
        status="ready",
        candidate_count=2,
        ready_candidate_count=1,
        blocked_candidate_count=1,
    )
    ticket_index = LocalLabReplayTicketIndex(
        correlation_id="corr-workflow",
        export_dir="E:/lab/export_dir",
        status="ready",
        ticket_count=2,
        ready_ticket_count=1,
        blocked_ticket_count=1,
    )
    dispatch_plan = LocalLabReplayDispatchPlan(
        correlation_id="corr-workflow",
        export_dir="E:/lab/export_dir",
        status="ready",
        ticket_count=2,
        ready_dispatch_count=1,
        blocked_dispatch_count=1,
    )

    manifest = build_local_lab_replay_workflow_manifest(
        replay_candidate_queue=queue,
        replay_candidate_queue_path="E:/lab/export_dir/local_lab_replay_candidate_queue.json",
        replay_ticket_index=ticket_index,
        replay_ticket_index_path="E:/lab/export_dir/local_lab_replay_ticket_index.json",
        replay_dispatch_plan=dispatch_plan,
        replay_dispatch_plan_path="E:/lab/export_dir/local_lab_replay_dispatch_plan.json",
    )

    assert manifest.correlation_id == "corr-workflow"
    assert manifest.replay_candidate_queue_status == "ready"
    assert manifest.replay_ticket_index_status == "ready"
    assert manifest.replay_dispatch_plan_status == "ready"
    assert manifest.replay_candidate_count == 2
    assert manifest.replay_ticket_count == 2
    assert manifest.replay_dispatch_ready_count == 1
