from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engines.engine_b import EngineBSweepValidationInput
from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineBSweepHookPlanPayload,
    load_engine_b_sweep_hook_payload,
    run_engine_b_sweep_hook,
    select_current_compiled_hook_plan,
)
from tests.support_paths import repo_build_path


def _publish_engine_b_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/engine_b_sweep_validation.json",
    action_kinds: tuple[ArtifactActionKind, ...] = (ArtifactActionKind.SOFT_BOOST,),
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> EngineBSweepValidationInput:
    return EngineBSweepValidationInput(
        context_id="BTCUSDT:1700000000000:engine_b.shadow.v1",
        pair="BTCUSDT",
        engine_id="engine_b",
        scoring_version="engine_b.shadow.v1",
        raw_score=0.62,
        penalized_score=0.58,
        expected_cost=0.001,
        expected_ce=0.003,
        conviction="medium",
        tier="tier_2",
    )


def test_load_engine_b_sweep_hook_payload_from_loaded_selection():
    state_dir = repo_build_path("build/test_protocols_engine_b_sweep_hook_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_b_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_b_sweep_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_B_SWEEP_VALIDATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_BOOST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "raw_score_multiplier_delta": 0.10,
                    "raw_score_add": 0.05,
                    "raw_score_cap": 0.90,
                    "detail": "boost score on confirmed sweep reversion",
                },
            },
        )
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_B_SWEEP_VALIDATION)

        payload = load_engine_b_sweep_hook_payload(selection)

        assert payload.raw_score_multiplier_delta == pytest.approx(0.10)
        assert payload.raw_score_add == pytest.approx(0.05)
        assert payload.raw_score_cap == pytest.approx(0.90)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_engine_b_sweep_hook_payload_rejects_wrong_hook():
    state_dir = repo_build_path("build/test_protocols_engine_b_sweep_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_engine_b_sweep_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_engine_b_sweep_hook_returns_adjustment_outcome():
    outcome = run_engine_b_sweep_hook(
        _hook_input(),
        EngineBSweepHookPlanPayload(
            raw_score_multiplier_delta=0.10,
            raw_score_add=0.05,
            conviction_add=0.03,
            raw_score_cap=0.90,
            detail="boost score on confirmed sweep reversion",
        ),
    )

    assert outcome.accepted is True
    assert outcome.raw_score_multiplier_delta == pytest.approx(0.10)
    assert outcome.raw_score_add == pytest.approx(0.05)
    assert outcome.conviction_add == pytest.approx(0.03)
    assert outcome.raw_score_cap == pytest.approx(0.90)
    assert "boost score" in outcome.detail


def test_run_engine_b_sweep_hook_blocks_with_typed_detail():
    outcome = run_engine_b_sweep_hook(
        _hook_input(),
        EngineBSweepHookPlanPayload(
            blocked=True,
            block_reason_codes=("ARTIFACT_SWEEP_BLOCK",),
            detail="artifact veto on sweep validation",
        ),
    )

    assert outcome.accepted is False
    assert outcome.reason_codes == ("ARTIFACT_SWEEP_BLOCK",)
    assert outcome.detail == "artifact veto on sweep validation"
