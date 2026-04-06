from __future__ import annotations

import shutil
from pathlib import Path

from execution_backbone import (
    ExecutionOpportunity,
    ExecutionSubmissionStatus,
    RemoteExecutionState,
    SubmitReceipt,
)
from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    build_execution_runtime,
    inspect_execution_runtime_bootstrap,
)


class FakeExecutionVenue:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, object, float]] = []
        self._counter = 0
        self.constraints_by_pair: dict[str, VenueConstraintSnapshot] = {}

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        return self.constraints_by_pair.get(pair)

    def submit_order(self, intent, now: float) -> SubmitReceipt:
        self._counter += 1
        order_id = f"ord-{self._counter}"
        self.submissions.append((order_id, intent, now))
        return SubmitReceipt(order_id=order_id, submitted_at=now)

    def replace_order(self, original_order_id: str, intent, now: float):
        raise NotImplementedError

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        return None

    def poll_order_events(self) -> tuple:
        return ()

    def fetch_remote_state(self) -> RemoteExecutionState:
        return RemoteExecutionState()


def _opportunity() -> ExecutionOpportunity:
    return ExecutionOpportunity(
        intent_id="intent-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        side="buy",
        quantity=0.25,
        expected_gain=0.01,
        expected_cost=0.0015,
        score=0.82,
        justification="validated execution path",
        spread_bps=2.0,
    )


def _publish_execution_no_trade_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/execution_no_trade.json",
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                    artifact_ids=("artifact-1",),
                    action_kinds=(ArtifactActionKind.NO_TRADE,),
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def test_build_execution_runtime_without_registry_state_dir_keeps_baseline_submission():
    adapter = FakeExecutionVenue()
    runtime = build_execution_runtime(adapter)

    submission = runtime.submit_opportunity(_opportunity(), now=10.0)

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert len(adapter.submissions) == 1


def test_inspect_execution_runtime_bootstrap_reports_unconfigured_when_state_dir_missing():
    status = inspect_execution_runtime_bootstrap()

    assert status.configured is False
    assert status.selection_status.value == "no_snapshot"


def test_build_execution_runtime_with_compiled_registry_blocks_when_plan_blocks():
    state_dir = Path("build/test_protocols_execution_runtime_bootstrap_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_EXECUTION_BLOCK"],
                    "detail": "artifact veto at execution boundary",
                },
            },
        )
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            compiled_registry_state_dir=state_dir,
        )

        submission = runtime.submit_opportunity(_opportunity(), now=11.0)

        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.detail == "artifact veto at execution boundary"
        assert len(adapter.submissions) == 0

        status = inspect_execution_runtime_bootstrap(compiled_registry_state_dir=state_dir)
        assert status.configured is True
        assert status.selection_status.value == "loaded"
        assert status.loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_runtime_with_empty_registry_state_dir_fails_open():
    state_dir = Path("build/test_protocols_execution_runtime_bootstrap_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        adapter = FakeExecutionVenue()
        runtime = build_execution_runtime(
            adapter,
            compiled_registry_state_dir=state_dir,
        )

        submission = runtime.submit_opportunity(_opportunity(), now=12.0)

        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert len(adapter.submissions) == 1
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
