from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    ExecutionNoTradeHookInput,
    ExecutionNoTradeHookPlanPayload,
    load_execution_no_trade_hook_payload,
    run_execution_no_trade_hook,
    select_current_compiled_hook_plan,
)
from tests.support_paths import repo_build_path


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


def test_load_execution_no_trade_hook_payload_from_loaded_selection():
    state_dir = repo_build_path("build/test_protocols_execution_no_trade_hook_loaded")
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
        selection = select_current_compiled_hook_plan(store, HookId.EXECUTION_NO_TRADE_FILTER)

        payload = load_execution_no_trade_hook_payload(selection)

        assert payload.blocked is True
        assert payload.block_reason_codes == ("ARTIFACT_EXECUTION_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_execution_no_trade_hook_payload_rejects_wrong_hook():
    state_dir = repo_build_path("build/test_protocols_execution_no_trade_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_execution_no_trade_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_execution_no_trade_hook_blocks_with_typed_detail():
    outcome = run_execution_no_trade_hook(
        ExecutionNoTradeHookInput(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.001,
            expected_gain=0.004,
            score=0.8,
        ),
        ExecutionNoTradeHookPlanPayload(
            blocked=True,
            block_reason_codes=("ARTIFACT_EXECUTION_BLOCK",),
            detail="artifact veto at execution boundary",
        ),
    )

    assert outcome.blocked is True
    assert outcome.block_reason_codes == ("ARTIFACT_EXECUTION_BLOCK",)
    assert outcome.detail == "artifact veto at execution boundary"


def test_run_execution_no_trade_hook_allows_when_payload_is_not_blocking():
    outcome = run_execution_no_trade_hook(
        ExecutionNoTradeHookInput(
            intent_id="intent-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            expected_cost=0.0015,
            expected_gain=0.006,
            score=0.72,
        ),
        ExecutionNoTradeHookPlanPayload(blocked=False),
    )

    assert outcome.blocked is False
    assert outcome.block_reason_codes == ()
    assert outcome.detail == ""
