from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engines.engine_d import EngineDReentryValidationInput
from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineDReentryHookPlanPayload,
    load_engine_d_reentry_hook_payload,
    run_engine_d_reentry_hook,
    select_current_compiled_hook_plan,
)


def _publish_engine_d_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/engine_d_reentry_validation.json",
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
                    hook_id=HookId.ENGINE_D_REENTRY_VALIDATION,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> EngineDReentryValidationInput:
    return EngineDReentryValidationInput(
        context_id="ctx-btc-01",
        trade_id="trade-btc-01",
        pair="BTCUSDT",
        engine_id="engine_d",
        scoring_version="engine_d.shadow.v1",
        link_type="prior_trade",
        structure_reformed_detected=True,
        raw_score=0.70,
        penalized_score=0.66,
        expected_cost=0.001,
        expected_ce=0.004,
        conviction="high",
        tier="tier_1",
    )


def test_load_engine_d_reentry_hook_payload_from_loaded_selection():
    state_dir = Path("build/test_protocols_engine_d_reentry_hook_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_d_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_d_reentry_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_D_REENTRY_VALIDATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_REENTRY_BLOCK"],
                    "detail": "artifact veto on engine_d re-entry",
                },
            },
        )
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_D_REENTRY_VALIDATION)

        payload = load_engine_d_reentry_hook_payload(selection)

        assert payload.blocked is True
        assert payload.block_reason_codes == ("ARTIFACT_REENTRY_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_engine_d_reentry_hook_payload_rejects_wrong_hook():
    state_dir = Path("build/test_protocols_engine_d_reentry_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_engine_d_reentry_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_engine_d_reentry_hook_returns_typed_acceptance():
    outcome = run_engine_d_reentry_hook(
        _hook_input(),
        EngineDReentryHookPlanPayload(detail="artifact approved engine_d re-entry"),
    )

    assert outcome.accepted is True
    assert outcome.reason_codes == ()
    assert "approved" in outcome.detail


def test_run_engine_d_reentry_hook_blocks_with_typed_detail():
    outcome = run_engine_d_reentry_hook(
        _hook_input(),
        EngineDReentryHookPlanPayload(
            blocked=True,
            block_reason_codes=("ARTIFACT_REENTRY_BLOCK",),
            detail="artifact veto on engine_d re-entry",
        ),
    )

    assert outcome.accepted is False
    assert outcome.reason_codes == ("ARTIFACT_REENTRY_BLOCK",)
    assert outcome.detail == "artifact veto on engine_d re-entry"
