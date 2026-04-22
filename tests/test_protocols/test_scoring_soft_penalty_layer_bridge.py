from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json
import protocols.scoring_soft_penalty_layer_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    ScoringSoftPenaltyLayerBridge,
    inspect_scoring_soft_penalty_layer_bridge,
)
from scoring_backbone import ScoringSoftPenaltyLayerInput
from tests.support_paths import repo_build_path


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


def test_scoring_soft_penalty_layer_bridge_uses_neutral_outcome_without_snapshot():
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = ScoringSoftPenaltyLayerBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.raw_score_multiplier_delta == 0.0
        assert outcome.raw_score_add == 0.0
        assert outcome.raw_score_cap is None
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_scoring_soft_penalty_layer_bridge_reports_no_snapshot():
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_scoring_soft_penalty_layer_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_scoring_soft_penalty_layer_bridge_applies_loaded_plan():
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_loaded")
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
        bridge = ScoringSoftPenaltyLayerBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.raw_score_multiplier_delta == -0.15
        assert outcome.raw_score_add == -0.05
        assert outcome.raw_score_cap == 2.1
        assert outcome.reason_codes == ("ARTIFACT_SCORING_SOFT_REDUCE",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_scoring_soft_penalty_layer_bridge_fails_open_on_invalid_hook_payload():
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_payload_invalid")
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
                    "raw_score_cap": {"invalid": True},
                },
            },
        )
        bridge = ScoringSoftPenaltyLayerBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.raw_score_multiplier_delta == 0.0
        assert outcome.raw_score_add == 0.0
        assert outcome.raw_score_cap is None
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_scoring_soft_penalty_layer_bridge_reports_invalid_plan_error():
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_scoring_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "scoring_soft_penalty_layer.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_REDUCE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"raw_score_add": -0.1},
            },
        )

        status = inspect_scoring_soft_penalty_layer_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_scoring_soft_penalty_layer_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = repo_build_path("build/test_protocols_scoring_soft_penalty_bridge_hook_error")
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
                "opaque_plan_payload": {"raw_score_add": -0.1},
            },
        )
        bridge = ScoringSoftPenaltyLayerBridge(store)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_scoring_soft_penalty_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.raw_score_multiplier_delta == 0.0
        assert outcome.raw_score_add == 0.0
        assert outcome.raw_score_cap is None
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
