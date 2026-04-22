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
import protocols.risk_micro_friction_precheck_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    RiskMicroFrictionPrecheckBridge,
    inspect_risk_micro_friction_precheck_bridge,
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


def test_risk_micro_friction_precheck_bridge_allows_without_snapshot():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = RiskMicroFrictionPrecheckBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_risk_micro_friction_precheck_bridge_reports_no_snapshot():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_risk_micro_friction_precheck_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_risk_micro_friction_precheck_bridge_applies_loaded_plan():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_loaded")
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
        bridge = RiskMicroFrictionPrecheckBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is False
        assert outcome.reason_codes == ("ARTIFACT_RISK_MICRO_FRICTION_BLOCK",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_risk_micro_friction_precheck_bridge_fails_open_on_invalid_hook_payload():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_payload_invalid")
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
                    "blocked": {"invalid": True},
                },
            },
        )
        bridge = RiskMicroFrictionPrecheckBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_risk_micro_friction_precheck_bridge_reports_invalid_plan_error():
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_risk_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "risk_micro_friction_precheck.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.NO_TRADE.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"blocked": True},
            },
        )

        status = inspect_risk_micro_friction_precheck_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_risk_micro_friction_precheck_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = repo_build_path("build/test_protocols_risk_micro_friction_bridge_hook_error")
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
                "opaque_plan_payload": {"blocked": True},
            },
        )
        bridge = RiskMicroFrictionPrecheckBridge(store)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_risk_micro_friction_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.accepted is True
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
