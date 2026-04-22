from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    CompiledHookPlanLoadStatus,
    select_current_compiled_hook_plan,
)
from tests.support_paths import repo_build_path


def _snapshot(
    snapshot_id: str,
    *,
    binding: CompiledArtifactHookBinding | None,
) -> CompiledArtifactRegistrySnapshot:
    return CompiledArtifactRegistrySnapshot(
        snapshot_id=snapshot_id,
        generated_at_ms=1000,
        artifact_ids=("artifact-1",) if binding is not None else (),
        hook_bindings=((binding,) if binding is not None else ()),
    )


def test_select_current_compiled_hook_plan_returns_no_snapshot_when_store_is_empty():
    state_dir = repo_build_path("build/test_protocols_compiled_hook_plan_loader_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(
            store,
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        )

        assert selection.status == CompiledHookPlanLoadStatus.NO_SNAPSHOT
        assert selection.plan is None
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_select_current_compiled_hook_plan_returns_no_binding_when_snapshot_has_other_hooks():
    state_dir = repo_build_path("build/test_protocols_compiled_hook_plan_loader_no_binding")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        store.publish(
            _snapshot(
                "snap-1",
                binding=CompiledArtifactHookBinding(
                    hook_id=HookId.ENGINE_B_SWEEP_VALIDATION,
                    artifact_ids=("artifact-1",),
                    action_kinds=(ArtifactActionKind.SOFT_BOOST,),
                    compiled_plan_ref="compiled/snap-1/engine_b.json",
                ),
            )
        )
        selection = select_current_compiled_hook_plan(
            store,
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        )

        assert selection.status == CompiledHookPlanLoadStatus.NO_BINDING
        assert selection.snapshot_id == "snap-1"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_select_current_compiled_hook_plan_returns_binding_only_when_ref_is_empty():
    state_dir = repo_build_path("build/test_protocols_compiled_hook_plan_loader_binding_only")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        binding = CompiledArtifactHookBinding(
            hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
            artifact_ids=("artifact-1",),
            action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            compiled_plan_ref="",
        )
        store.publish(_snapshot("snap-1", binding=binding))
        selection = select_current_compiled_hook_plan(
            store,
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        )

        assert selection.status == CompiledHookPlanLoadStatus.BINDING_ONLY
        assert selection.binding == binding
        assert selection.plan is None
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_select_current_compiled_hook_plan_loads_plan_and_validates_binding_match():
    state_dir = repo_build_path("build/test_protocols_compiled_hook_plan_loader_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        binding = CompiledArtifactHookBinding(
            hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
            artifact_ids=("artifact-1",),
            action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            compiled_plan_ref="compiled/snap-1/engine_a.json",
        )
        store.publish(_snapshot("snap-1", binding=binding))
        plan_path = state_dir / "compiled" / "snap-1" / "engine_a.json"
        atomic_write_json(
            plan_path,
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.SOFT_BOOST.value],
                "generated_at_ms": 1000,
                "compiled_action_count": 1,
                "opaque_plan_payload": {"kind": "demo"},
            },
        )

        selection = select_current_compiled_hook_plan(
            store,
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        )

        assert selection.status == CompiledHookPlanLoadStatus.LOADED
        assert selection.compiled_plan_path == plan_path.resolve()
        assert selection.plan is not None
        assert selection.plan.snapshot_id == "snap-1"
        assert selection.plan.compiled_action_count == 1
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_select_current_compiled_hook_plan_returns_load_error_on_plan_binding_mismatch():
    state_dir = repo_build_path("build/test_protocols_compiled_hook_plan_loader_mismatch")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        binding = CompiledArtifactHookBinding(
            hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
            artifact_ids=("artifact-1",),
            action_kinds=(ArtifactActionKind.SOFT_BOOST,),
            compiled_plan_ref="compiled/snap-1/engine_a.json",
        )
        store.publish(_snapshot("snap-1", binding=binding))
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_a.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-other"],
                "action_kinds": [ArtifactActionKind.SOFT_BOOST.value],
                "generated_at_ms": 1000,
            },
        )

        selection = select_current_compiled_hook_plan(
            store,
            HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        )

        assert selection.status == CompiledHookPlanLoadStatus.LOAD_ERROR
        assert selection.binding == binding
        assert selection.plan is None
        assert selection.error_type == "ValueError"
        assert "artifact_ids must match binding artifact_ids" in selection.error_detail
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
