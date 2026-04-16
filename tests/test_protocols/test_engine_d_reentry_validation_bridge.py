from __future__ import annotations

import shutil
from pathlib import Path

from engines.engine_d import EngineDReentryValidationInput
from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    HookId,
)
from interface_contracts.atomic_io import atomic_write_json
import protocols.engine_d_reentry_validation_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    EngineDReentryValidationBridge,
    inspect_engine_d_reentry_validation_bridge,
)


def _state_dir(repo_tmp_path: Path, name: str) -> Path:
    return repo_tmp_path / name


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


def test_engine_d_reentry_validation_bridge_allows_without_snapshot(repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = EngineDReentryValidationBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_d_reentry_validation_bridge_reports_no_snapshot(repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_engine_d_reentry_validation_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_d_reentry_validation_bridge_applies_loaded_plan(repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_loaded")
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
                    "episode_reference_id": "episode-bridge-1",
                    "anti_revenge_state": "cooldown_active",
                    "observability_tags": ["backtest.anti_revenge_state"],
                },
            },
        )
        bridge = EngineDReentryValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is False
        assert outcome.reason_codes == ("ARTIFACT_REENTRY_BLOCK",)
        assert outcome.episode_reference_id == "episode-bridge-1"
        assert outcome.anti_revenge_state == "cooldown_active"
        assert outcome.observability_tags == ("backtest.anti_revenge_state",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_d_reentry_validation_bridge_fails_open_on_invalid_hook_payload(repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_payload_invalid")
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
                    "blocked": {"invalid": True},
                },
            },
        )
        bridge = EngineDReentryValidationBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_engine_d_reentry_validation_bridge_reports_invalid_plan_error(repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_engine_d_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "engine_d_reentry_validation.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        status = inspect_engine_d_reentry_validation_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_engine_d_reentry_validation_bridge_fails_open_on_hook_execution_error(monkeypatch, repo_tmp_path: Path):
    state_dir = _state_dir(repo_tmp_path, "test_protocols_engine_d_reentry_validation_bridge_hook_error")
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
                "opaque_plan_payload": {"blocked": True},
            },
        )
        bridge = EngineDReentryValidationBridge(store)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_engine_d_reentry_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
