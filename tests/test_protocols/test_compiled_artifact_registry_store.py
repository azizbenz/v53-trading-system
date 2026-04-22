from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from interface_contracts import ArtifactActionKind, HookId
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
)
from tests.support_paths import repo_build_path


def _snapshot(
    snapshot_id: str,
    *,
    generated_at_ms: int,
    artifact_ids: tuple[str, ...] = ("artifact-1",),
    hook_bindings: tuple[CompiledArtifactHookBinding, ...] | None = None,
) -> CompiledArtifactRegistrySnapshot:
    return CompiledArtifactRegistrySnapshot(
        snapshot_id=snapshot_id,
        generated_at_ms=generated_at_ms,
        artifact_ids=artifact_ids,
        hook_bindings=hook_bindings
        or (
            CompiledArtifactHookBinding(
                hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                artifact_ids=("artifact-1",),
                action_kinds=(ArtifactActionKind.SOFT_BOOST,),
                compiled_plan_ref=f"compiled/{snapshot_id}/engine_a.json",
            ),
        ),
    )


def test_registry_store_publish_and_load_current_snapshot():
    state_dir = repo_build_path("build/test_protocols_compiled_registry_store_publish")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        published = store.publish(_snapshot("snap-1", generated_at_ms=1000))

        assert published.current_snapshot_id == "snap-1"
        assert published.previous_snapshot_id == ""
        assert published.snapshot_path.exists()
        assert store.load_current_snapshot() is not None
        assert store.load_current_snapshot().snapshot_id == "snap-1"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_registry_store_tracks_previous_and_last_known_good_then_rolls_back():
    state_dir = repo_build_path("build/test_protocols_compiled_registry_store_rollback")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        store.publish(_snapshot("snap-1", generated_at_ms=1000))
        store.mark_last_known_good("snap-1", marked_at_ms=1010)
        published = store.publish(
            _snapshot(
                "snap-2",
                generated_at_ms=2000,
                artifact_ids=("artifact-1", "artifact-2"),
                hook_bindings=(
                    CompiledArtifactHookBinding(
                        hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                        artifact_ids=("artifact-1", "artifact-2"),
                        action_kinds=(
                            ArtifactActionKind.SOFT_BOOST,
                            ArtifactActionKind.NO_TRADE,
                        ),
                        compiled_plan_ref="compiled/snap-2/engine_a.json",
                    ),
                ),
            )
        )

        assert published.previous_snapshot_id == "snap-1"
        assert store.load_current_snapshot().snapshot_id == "snap-2"

        rolled_back = store.rollback_to_last_known_good(rollback_at_ms=3000)

        assert rolled_back.rolled_back is True
        assert rolled_back.current_snapshot_id == "snap-1"
        assert rolled_back.previous_snapshot_id == "snap-2"
        assert store.load_current_snapshot().snapshot_id == "snap-1"
        assert store.load_pointer().last_known_good_snapshot_id == "snap-1"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_registry_store_requires_last_known_good_before_rollback():
    state_dir = repo_build_path("build/test_protocols_compiled_registry_store_no_lkg")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        store.publish(_snapshot("snap-1", generated_at_ms=1000))

        with pytest.raises(ValueError):
            store.rollback_to_last_known_good(rollback_at_ms=2000)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_registry_snapshot_rejects_hook_binding_with_unknown_artifact_id():
    with pytest.raises(ValueError):
        _snapshot(
            "snap-bad",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
                    artifact_ids=("artifact-missing",),
                    action_kinds=(ArtifactActionKind.SOFT_BOOST,),
                    compiled_plan_ref="compiled/snap-bad/engine_a.json",
                ),
            ),
        )
