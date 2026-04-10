from __future__ import annotations

import shutil
from pathlib import Path

from engines.engine_c import EngineCVoidValidationInput
from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json
import protocols.engine_c_void_validation_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineCVoidValidationBridge,
    inspect_engine_c_void_validation_bridge,
)


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


def test_engine_c_void_validation_bridge_allows_without_snapshot():
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = EngineCVoidValidationBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_c_void_validation_bridge_reports_no_snapshot():
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_engine_c_void_validation_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_c_void_validation_bridge_applies_loaded_plan():
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_loaded")
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
        bridge = EngineCVoidValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is False
        assert outcome.reason_codes == ("ARTIFACT_VOID_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_c_void_validation_bridge_fails_open_on_invalid_hook_payload():
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_payload_invalid")
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
                    "blocked": {"invalid": True},
                },
            },
        )
        bridge = EngineCVoidValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_c_void_validation_bridge_reports_invalid_plan_error():
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_c_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_c_void_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        status = inspect_engine_c_void_validation_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_c_void_validation_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = Path("build/test_protocols_engine_c_void_validation_bridge_hook_error")
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
                "opaque_plan_payload": {"blocked": True},
            },
        )
        bridge = EngineCVoidValidationBridge(store)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_engine_c_void_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
