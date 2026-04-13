from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from local_replay_runtime.local_lab_replay_workflow_loader import load_local_lab_replay_workflow_bundle


def test_load_local_lab_replay_workflow_bundle():
    bundle_dir = Path("tests") / "_tmp_local_lab_replay_workflow_loader" / uuid4().hex
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "local_lab_replay_candidate_queue.json").write_text(
        """{
  "correlation_id": "corr-workflow",
  "export_dir": "E:/lab/export_dir",
  "status": "ready",
  "candidate_count": 1,
  "ready_candidate_count": 1,
  "blocked_candidate_count": 0,
  "top_scope_slug": "btcusdt__engine_a",
  "top_priority_score": 0.8,
  "candidates": []
}""",
        encoding="utf-8",
    )
    (bundle_dir / "local_lab_replay_ticket_index.json").write_text(
        """{
  "correlation_id": "corr-workflow",
  "export_dir": "E:/lab/export_dir",
  "status": "ready",
  "ticket_count": 1,
  "ready_ticket_count": 1,
  "blocked_ticket_count": 0,
  "top_ticket_id": "corr-workflow:btcusdt__engine_a:replay_ticket",
  "top_scope_slug": "btcusdt__engine_a",
  "tickets": []
}""",
        encoding="utf-8",
    )
    (bundle_dir / "local_lab_replay_dispatch_plan.json").write_text(
        """{
  "correlation_id": "corr-workflow",
  "export_dir": "E:/lab/export_dir",
  "status": "ready",
  "ticket_count": 1,
  "ready_dispatch_count": 1,
  "blocked_dispatch_count": 0,
  "top_ticket_id": "corr-workflow:btcusdt__engine_a:replay_ticket",
  "items": []
}""",
        encoding="utf-8",
    )
    (bundle_dir / "local_lab_replay_workflow_manifest.json").write_text(
        """{
  "correlation_id": "corr-workflow",
  "export_dir": "E:/lab/export_dir",
  "replay_candidate_queue_path": "E:/lab/export_dir/local_lab_replay_candidate_queue.json",
  "replay_ticket_index_path": "E:/lab/export_dir/local_lab_replay_ticket_index.json",
  "replay_dispatch_plan_path": "E:/lab/export_dir/local_lab_replay_dispatch_plan.json",
  "replay_candidate_queue_status": "ready",
  "replay_ticket_index_status": "ready",
  "replay_dispatch_plan_status": "ready",
  "replay_candidate_count": 1,
  "replay_ticket_count": 1,
  "replay_dispatch_ready_count": 1,
  "replay_dispatch_blocked_count": 0
}""",
        encoding="utf-8",
    )

    bundle = load_local_lab_replay_workflow_bundle(bundle_dir)

    assert bundle.manifest.correlation_id == "corr-workflow"
    assert bundle.replay_candidate_queue.candidate_count == 1
    assert bundle.replay_ticket_index.ticket_count == 1
    assert bundle.replay_dispatch_plan.ready_dispatch_count == 1
