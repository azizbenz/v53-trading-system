from __future__ import annotations

import shutil
from pathlib import Path

from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    build_execution_no_trade_bridge_projection,
)


def _publish_execution_no_trade_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/execution_no_trade.json",
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.EXECUTION_NO_TRADE_FILTER,
                    artifact_ids=("artifact-1",),
                    action_kinds=(ArtifactActionKind.NO_TRADE,),
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def test_build_execution_no_trade_bridge_projection_returns_planned_when_unconfigured():
    projection = build_execution_no_trade_bridge_projection()

    assert projection.status == "planned"
    assert projection.configured is False
    assert projection.selection_status == "no_snapshot"


def test_build_execution_no_trade_bridge_projection_returns_healthy_when_loaded():
    state_dir = Path("build/test_protocols_execution_runtime_dashboard_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "blocked": True,
                    "block_reason_codes": ["ARTIFACT_EXECUTION_BLOCK"],
                    "detail": "artifact veto at execution boundary",
                },
            },
        )

        projection = build_execution_no_trade_bridge_projection(
            compiled_registry_state_dir=state_dir
        )

        assert projection.status == "healthy"
        assert projection.configured is True
        assert projection.selection_status == "loaded"
        assert projection.loaded is True
        assert projection.artifact_count == 1
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_build_execution_no_trade_bridge_projection_returns_warning_on_invalid_plan():
    state_dir = Path("build/test_protocols_execution_runtime_dashboard_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        _publish_execution_no_trade_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "execution_no_trade.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        projection = build_execution_no_trade_bridge_projection(
            compiled_registry_state_dir=state_dir
        )

        assert projection.status == "warning"
        assert projection.selection_status == "binding_only"
        assert projection.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
