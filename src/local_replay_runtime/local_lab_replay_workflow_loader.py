"""File-based loader for Local IA Lab replay workflow sidecars."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from local_replay_runtime.local_lab_replay_candidate_queue import (
    LocalLabReplayCandidateQueue,
)
from local_replay_runtime.local_lab_replay_dispatch_plan import LocalLabReplayDispatchPlan
from local_replay_runtime.local_lab_replay_ticket_index import LocalLabReplayTicketIndex
from local_replay_runtime.local_lab_replay_workflow_manifest import (
    LocalLabReplayWorkflowManifest,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class LocalLabReplayWorkflowBundle(BaseModel, frozen=True):
    """Validated Local IA Lab replay workflow bundle loaded from one output directory."""

    bundle_dir: Path
    manifest: LocalLabReplayWorkflowManifest
    replay_candidate_queue: LocalLabReplayCandidateQueue
    replay_ticket_index: LocalLabReplayTicketIndex
    replay_dispatch_plan: LocalLabReplayDispatchPlan


def _load_model(path: Path, *, label: str, model_type: type[_ModelT]) -> _ModelT:
    if not path.is_file():
        raise FileNotFoundError(f"Missing Local IA Lab replay workflow file for {label}: {path}")
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise ValueError(
            f"Invalid Local IA Lab replay workflow file for {label}: {path.name}"
        ) from exc


def _require_aligned_bundle(
    *,
    manifest: LocalLabReplayWorkflowManifest,
    replay_candidate_queue: LocalLabReplayCandidateQueue,
    replay_ticket_index: LocalLabReplayTicketIndex,
    replay_dispatch_plan: LocalLabReplayDispatchPlan,
) -> None:
    correlation_id = manifest.correlation_id
    export_dir = manifest.export_dir
    if replay_candidate_queue.correlation_id != correlation_id:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching correlation_id between manifest and replay candidate queue"
        )
    if replay_ticket_index.correlation_id != correlation_id:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching correlation_id between manifest and replay ticket index"
        )
    if replay_dispatch_plan.correlation_id != correlation_id:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching correlation_id between manifest and replay dispatch plan"
        )
    if replay_candidate_queue.export_dir != export_dir:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching export_dir between manifest and replay candidate queue"
        )
    if replay_ticket_index.export_dir != export_dir:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching export_dir between manifest and replay ticket index"
        )
    if replay_dispatch_plan.export_dir != export_dir:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching export_dir between manifest and replay dispatch plan"
        )
    if manifest.replay_candidate_count != replay_candidate_queue.candidate_count:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching replay_candidate_count between manifest and replay candidate queue"
        )
    if manifest.replay_ticket_count != replay_ticket_index.ticket_count:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching replay_ticket_count between manifest and replay ticket index"
        )
    if manifest.replay_dispatch_ready_count != replay_dispatch_plan.ready_dispatch_count:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching replay_dispatch_ready_count between manifest and replay dispatch plan"
        )
    if manifest.replay_dispatch_blocked_count != replay_dispatch_plan.blocked_dispatch_count:
        raise ValueError(
            "Local IA Lab replay workflow bundle requires matching replay_dispatch_blocked_count between manifest and replay dispatch plan"
        )


def load_local_lab_replay_workflow_bundle(bundle_dir: Path) -> LocalLabReplayWorkflowBundle:
    """Load and validate the Local IA Lab replay workflow bundle from one directory."""

    resolved_dir = bundle_dir.resolve()
    manifest = _load_model(
        resolved_dir / "local_lab_replay_workflow_manifest.json",
        label="manifest",
        model_type=LocalLabReplayWorkflowManifest,
    )
    replay_candidate_queue = _load_model(
        resolved_dir / "local_lab_replay_candidate_queue.json",
        label="replay_candidate_queue",
        model_type=LocalLabReplayCandidateQueue,
    )
    replay_ticket_index = _load_model(
        resolved_dir / "local_lab_replay_ticket_index.json",
        label="replay_ticket_index",
        model_type=LocalLabReplayTicketIndex,
    )
    replay_dispatch_plan = _load_model(
        resolved_dir / "local_lab_replay_dispatch_plan.json",
        label="replay_dispatch_plan",
        model_type=LocalLabReplayDispatchPlan,
    )
    _require_aligned_bundle(
        manifest=manifest,
        replay_candidate_queue=replay_candidate_queue,
        replay_ticket_index=replay_ticket_index,
        replay_dispatch_plan=replay_dispatch_plan,
    )
    return LocalLabReplayWorkflowBundle(
        bundle_dir=resolved_dir,
        manifest=manifest,
        replay_candidate_queue=replay_candidate_queue,
        replay_ticket_index=replay_ticket_index,
        replay_dispatch_plan=replay_dispatch_plan,
    )


__all__ = ["LocalLabReplayWorkflowBundle", "load_local_lab_replay_workflow_bundle"]
