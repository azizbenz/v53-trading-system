from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engines.engine_c import EngineCVoidValidationInput
from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineCVoidHookPlanPayload,
    load_engine_c_void_hook_payload,
    run_engine_c_void_hook,
    select_current_compiled_hook_plan,
)
from tests.support_paths import repo_build_path


def _publish_engine_c_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/engine_c_void_validation.json",
    action_kinds: tuple[ArtifactActionKind, ...] = (ArtifactActionKind.NO_TRADE,),
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.ENGINE_C_VOID_VALIDATION,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> EngineCVoidValidationInput:
    return EngineCVoidValidationInput(
        context_id="BTCUSDT:1700000000000:engine_c:engine_c.shadow.v1",
        pair="BTCUSDT",
        engine_id="engine_c",
        scoring_version="engine_c.shadow.v1",
        breakout_type="range_expansion",
        continuation_context="healthy_followthrough",
        raw_score=0.72,
        penalized_score=0.68,
        expected_cost=0.001,
        expected_ce=0.004,
        conviction="high",
        tier="tier_1",
    )


def test_load_engine_c_void_hook_payload_from_loaded_selection():
    state_dir = repo_build_path("build/test_protocols_engine_c_void_hook_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_c_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_c_void_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_C_VOID_VALIDATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_VOID_BLOCK"],
                    "detail": "artifact veto on engine_c void validation",
                },
            },
        )
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_C_VOID_VALIDATION)

        payload = load_engine_c_void_hook_payload(selection)

        assert payload.blocked is True
        assert payload.block_reason_codes == ("ARTIFACT_VOID_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_engine_c_void_hook_payload_rejects_wrong_hook():
    state_dir = repo_build_path("build/test_protocols_engine_c_void_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_engine_c_void_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_engine_c_void_hook_returns_typed_acceptance():
    outcome = run_engine_c_void_hook(
        _hook_input(),
        EngineCVoidHookPlanPayload(detail="artifact approved engine_c void validation"),
    )

    assert outcome.accepted is True
    assert outcome.reason_codes == ()
    assert "approved" in outcome.detail


def test_run_engine_c_void_hook_blocks_with_typed_detail():
    outcome = run_engine_c_void_hook(
        _hook_input(),
        EngineCVoidHookPlanPayload(
            blocked=True,
            block_reason_codes=("ARTIFACT_VOID_BLOCK",),
            detail="artifact veto on engine_c void validation",
        ),
    )

    assert outcome.accepted is False
    assert outcome.reason_codes == ("ARTIFACT_VOID_BLOCK",)
    assert outcome.detail == "artifact veto on engine_c void validation"
