from __future__ import annotations

import shutil
from pathlib import Path

from execution_backbone.execution_runtime import ExecutionNoTradeFilterInput
from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json
import protocols.execution_no_trade_filter_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    ExecutionNoTradeFilterBridge,
    inspect_execution_no_trade_filter_bridge,
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


def _hook_input() -> ExecutionNoTradeFilterInput:
    return ExecutionNoTradeFilterInput(
        intent_id="intent-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        expected_cost=0.001,
        expected_gain=0.004,
        score=0.81,
    )


def test_execution_no_trade_filter_bridge_allows_without_snapshot():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = ExecutionNoTradeFilterBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.blocked is False
        assert outcome.block_reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_execution_no_trade_filter_bridge_reports_no_snapshot():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_execution_no_trade_filter_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_execution_no_trade_filter_bridge_blocks_from_loaded_plan():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
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
        bridge = ExecutionNoTradeFilterBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.blocked is True
        assert outcome.block_reason_codes == ("ARTIFACT_EXECUTION_BLOCK",)
        assert outcome.detail == "artifact veto at execution boundary"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_execution_no_trade_filter_bridge_reports_loaded_plan():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_status_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
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

        status = inspect_execution_no_trade_filter_bridge(store)

        assert status.current_snapshot_id == "snap-1"
        assert status.selection_status.value == "loaded"
        assert status.binding_present is True
        assert status.compiled_plan_ref == "compiled/snap-1/execution_no_trade.json"
        assert status.loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_execution_no_trade_filter_bridge_fails_open_on_invalid_plan_binding():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )
        bridge = ExecutionNoTradeFilterBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.blocked is False
        assert outcome.block_reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_execution_no_trade_filter_bridge_reports_invalid_plan_error():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        status = inspect_execution_no_trade_filter_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_execution_no_trade_filter_bridge_fails_open_on_invalid_hook_payload():
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_payload_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": {"invalid": True},
                    "block_reason_codes": ["ARTIFACT_EXECUTION_BLOCK"],
                },
            },
        )
        bridge = ExecutionNoTradeFilterBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.blocked is False
        assert outcome.block_reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_execution_no_trade_filter_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = Path("build/test_protocols_execution_no_trade_filter_bridge_hook_error")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_execution_no_trade_snapshot(state_dir)
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
        bridge = ExecutionNoTradeFilterBridge(store)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_execution_no_trade_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.blocked is False
        assert outcome.block_reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
