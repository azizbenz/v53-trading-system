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
    ScoringSoftPenaltyHookPlanPayload,
    load_scoring_soft_penalty_hook_payload,
    run_scoring_soft_penalty_hook,
    select_current_compiled_hook_plan,
)
from scoring_backbone import ScoringSoftPenaltyLayerInput


def _publish_scoring_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/scoring_soft_penalty_layer.json",
    action_kinds: tuple[ArtifactActionKind, ...] = (ArtifactActionKind.SOFT_REDUCE,),
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.SCORING_SOFT_PENALTY_LAYER,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> ScoringSoftPenaltyLayerInput:
    return ScoringSoftPenaltyLayerInput(
        context_id="eng_a:BTCUSDT:5.0",
        pair="BTCUSDT",
        engine_id="eng_a",
        scoring_version="5.0",
        expected_cost=0.2,
        expected_ce=0.1,
        corr_penalty=0.05,
        risk_penalty=0.03,
        fragility_score=0.62,
        toxicity_score=0.58,
        execution_survivability_score=0.44,
        micro_friction_score=0.71,
        pressure_state="elevated",
    )


def test_load_scoring_soft_penalty_hook_payload_from_loaded_selection():
    state_dir = Path("build/test_protocols_scoring_soft_penalty_hook_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_scoring_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "scoring_soft_penalty_layer.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.SCORING_SOFT_PENALTY_LAYER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_REDUCE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "raw_score_multiplier_delta": -0.15,
                    "raw_score_add": -0.05,
                    "raw_score_cap": 2.1,
                    "reason_codes": ["ARTIFACT_SCORING_SOFT_REDUCE"],
                    "detail": "artifact scoring soft penalty applied",
                },
            },
        )
        selection = select_current_compiled_hook_plan(store, HookId.SCORING_SOFT_PENALTY_LAYER)

        payload = load_scoring_soft_penalty_hook_payload(selection)

        assert payload.raw_score_multiplier_delta == pytest.approx(-0.15)
        assert payload.raw_score_add == pytest.approx(-0.05)
        assert payload.raw_score_cap == pytest.approx(2.1)
        assert payload.reason_codes == ("ARTIFACT_SCORING_SOFT_REDUCE",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_scoring_soft_penalty_hook_payload_rejects_wrong_hook():
    state_dir = Path("build/test_protocols_scoring_soft_penalty_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_scoring_soft_penalty_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_scoring_soft_penalty_hook_returns_typed_adjustment():
    outcome = run_scoring_soft_penalty_hook(
        _hook_input(),
        ScoringSoftPenaltyHookPlanPayload(
            raw_score_multiplier_delta=-0.10,
            raw_score_add=-0.05,
            raw_score_cap=2.0,
            reason_codes=("ARTIFACT_SCORING_SOFT_REDUCE",),
            detail="artifact scoring soft penalty applied",
        ),
    )

    assert outcome.raw_score_multiplier_delta == pytest.approx(-0.10)
    assert outcome.raw_score_add == pytest.approx(-0.05)
    assert outcome.raw_score_cap == pytest.approx(2.0)
    assert outcome.reason_codes == ("ARTIFACT_SCORING_SOFT_REDUCE",)
    assert outcome.detail == "artifact scoring soft penalty applied"


def test_run_scoring_soft_penalty_hook_uses_neutral_defaults():
    outcome = run_scoring_soft_penalty_hook(
        _hook_input(),
        ScoringSoftPenaltyHookPlanPayload(),
    )

    assert outcome.raw_score_multiplier_delta == pytest.approx(0.0)
    assert outcome.raw_score_add == pytest.approx(0.0)
    assert outcome.raw_score_cap is None
    assert outcome.reason_codes == ()
