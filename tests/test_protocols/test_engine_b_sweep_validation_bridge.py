from __future__ import annotations

import shutil
from pathlib import Path

from engines.engine_b import EngineBSweepValidationInput
from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json
import protocols.engine_b_sweep_validation_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineBSweepValidationBridge,
    inspect_engine_b_sweep_validation_bridge,
)


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


def test_engine_b_sweep_validation_bridge_allows_without_snapshot():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = EngineBSweepValidationBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
        assert outcome.raw_score_multiplier_delta == 0.0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_b_sweep_validation_bridge_reports_no_snapshot():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_engine_b_sweep_validation_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_b_sweep_validation_bridge_applies_loaded_plan():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_loaded")
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
                    "raw_score_cap": 0.85,
                    "detail": "boost score on confirmed sweep reversion",
                },
            },
        )
        bridge = EngineBSweepValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.raw_score_multiplier_delta == 0.10
        assert outcome.raw_score_add == 0.05
        assert outcome.raw_score_cap == 0.85
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_b_sweep_validation_bridge_reports_loaded_plan():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_status_loaded")
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
                },
            },
        )

        status = inspect_engine_b_sweep_validation_bridge(store)

        assert status.current_snapshot_id == "snap-1"
        assert status.selection_status.value == "loaded"
        assert status.binding_present is True
        assert status.compiled_plan_ref == "compiled/snap-1/engine_b_sweep_validation.json"
        assert status.loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_b_sweep_validation_bridge_fails_open_on_invalid_plan_binding():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_b_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_b_sweep_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_BOOST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"raw_score_multiplier_delta": 0.10},
            },
        )
        bridge = EngineBSweepValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
        assert outcome.raw_score_multiplier_delta == 0.0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_b_sweep_validation_bridge_reports_invalid_plan_error():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_b_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_b_sweep_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_BOOST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"raw_score_multiplier_delta": 0.10},
            },
        )

        status = inspect_engine_b_sweep_validation_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_b_sweep_validation_bridge_fails_open_on_invalid_hook_payload():
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_payload_invalid")
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
                    "raw_score_multiplier_delta": {"invalid": True},
                },
            },
        )
        bridge = EngineBSweepValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
        assert outcome.raw_score_multiplier_delta == 0.0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_b_sweep_validation_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = Path("build/test_protocols_engine_b_sweep_validation_bridge_hook_error")
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
                "opaque_plan_payload": {"raw_score_multiplier_delta": 0.10},
            },
        )
        bridge = EngineBSweepValidationBridge(store)

        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_engine_b_sweep_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
        assert outcome.raw_score_multiplier_delta == 0.0
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
