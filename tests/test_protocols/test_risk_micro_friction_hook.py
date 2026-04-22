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
    RiskMicroFrictionHookPlanPayload,
    load_risk_micro_friction_hook_payload,
    run_risk_micro_friction_hook,
    select_current_compiled_hook_plan,
)
from risk_backbone import RiskMicroFrictionPrecheckInput
from tests.support_paths import repo_build_path


def _publish_risk_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/risk_micro_friction_precheck.json",
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
                    hook_id=HookId.RISK_MICRO_FRICTION_PRECHECK,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> RiskMicroFrictionPrecheckInput:
    return RiskMicroFrictionPrecheckInput(
        context_id="BTCUSDT:engine_a:1700000000.000000",
        pair="BTCUSDT",
        engine_id="engine_a",
        size=100.0,
        planned_loss=10.0,
        fragility_score=0.62,
        toxicity_score=0.59,
        execution_survivability_score=0.44,
        micro_friction_score=0.71,
        pressure_state="elevated",
    )


def test_load_risk_micro_friction_hook_payload_from_loaded_selection():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_hook_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_risk_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "risk_micro_friction_precheck.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.RISK_MICRO_FRICTION_PRECHECK.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_RISK_MICRO_FRICTION_BLOCK"],
                    "detail": "artifact veto on risk micro-friction precheck",
                },
            },
        )
        selection = select_current_compiled_hook_plan(store, HookId.RISK_MICRO_FRICTION_PRECHECK)

        payload = load_risk_micro_friction_hook_payload(selection)

        assert payload.blocked is True
        assert payload.block_reason_codes == ("ARTIFACT_RISK_MICRO_FRICTION_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_risk_micro_friction_hook_payload_rejects_wrong_hook():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_risk_micro_friction_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_risk_micro_friction_hook_returns_typed_acceptance():
    outcome = run_risk_micro_friction_hook(
        _hook_input(),
        RiskMicroFrictionHookPlanPayload(detail="artifact approved risk micro-friction precheck"),
    )

    assert outcome.accepted is True
    assert outcome.reason_codes == ()
    assert "approved" in outcome.detail


def test_run_risk_micro_friction_hook_blocks_with_typed_detail():
    outcome = run_risk_micro_friction_hook(
        _hook_input(),
        RiskMicroFrictionHookPlanPayload(
            blocked=True,
            block_reason_codes=("ARTIFACT_RISK_MICRO_FRICTION_BLOCK",),
            detail="artifact veto on risk micro-friction precheck",
        ),
    )

    assert outcome.accepted is False
    assert outcome.reason_codes == ("ARTIFACT_RISK_MICRO_FRICTION_BLOCK",)
    assert outcome.detail == "artifact veto on risk micro-friction precheck"
