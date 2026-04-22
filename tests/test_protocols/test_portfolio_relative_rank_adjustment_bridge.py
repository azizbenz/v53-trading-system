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
from portfolio_minimal import PortfolioRelativeRankAdjustmentInput
import protocols.portfolio_relative_rank_adjustment_bridge as bridge_module
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    PortfolioRelativeRankAdjustmentBridge,
    inspect_portfolio_relative_rank_adjustment_bridge,
)
from tests.support_paths import repo_build_path


def _publish_portfolio_snapshot(
    state_dir: Path,
    *,
    compiled_plan_ref: str = "compiled/snap-1/portfolio_relative_rank_adjustment.json",
    action_kinds: tuple[ArtifactActionKind, ...] = (ArtifactActionKind.RANK_ADJUST,),
) -> CompiledArtifactRegistryStore:
    store = CompiledArtifactRegistryStore(state_dir)
    store.publish(
        CompiledArtifactRegistrySnapshot(
            snapshot_id="snap-1",
            generated_at_ms=1000,
            artifact_ids=("artifact-1",),
            hook_bindings=(
                CompiledArtifactHookBinding(
                    hook_id=HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
                    artifact_ids=("artifact-1",),
                    action_kinds=action_kinds,
                    compiled_plan_ref=compiled_plan_ref,
                ),
            ),
        )
    )
    return store


def _hook_input() -> PortfolioRelativeRankAdjustmentInput:
    return PortfolioRelativeRankAdjustmentInput(
        context_id="engine_a:BTC/USDT:build8_rank_v1:1",
        pair="BTC/USDT",
        engine_id="engine_a",
        ranking_score=0.55,
        rank=1,
        ranking_version="build8_rank_v1",
        penalized_score=0.8,
        expected_cost=0.01,
        expected_ce=0.05,
        ev_net=4.0,
        cluster_id="btc_cluster",
        tier_suggestion="tier_1",
    )


def test_portfolio_relative_rank_adjustment_bridge_uses_neutral_outcome_without_snapshot():
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        bridge = PortfolioRelativeRankAdjustmentBridge(CompiledArtifactRegistryStore(state_dir))

        outcome = bridge(_hook_input())

        assert outcome.rank_delta == 0.0
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_portfolio_relative_rank_adjustment_bridge_reports_no_snapshot():
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_status_empty")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        status = inspect_portfolio_relative_rank_adjustment_bridge(
            CompiledArtifactRegistryStore(state_dir)
        )

        assert status.configured is True
        assert status.selection_status.value == "no_snapshot"
        assert status.binding_present is False
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_portfolio_relative_rank_adjustment_bridge_applies_loaded_plan():
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_loaded")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_portfolio_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "portfolio_relative_rank_adjustment.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.RANK_ADJUST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "rank_delta": 0.20,
                    "reason_codes": ["ARTIFACT_PORTFOLIO_RANK_BOOST"],
                    "detail": "artifact portfolio rank adjustment applied",
                },
            },
        )
        bridge = PortfolioRelativeRankAdjustmentBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.rank_delta == 0.20
        assert outcome.reason_codes == ("ARTIFACT_PORTFOLIO_RANK_BOOST",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_portfolio_relative_rank_adjustment_bridge_fails_open_on_invalid_hook_payload():
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_payload_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_portfolio_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "portfolio_relative_rank_adjustment.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.RANK_ADJUST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {
                    "rank_delta": {"invalid": True},
                },
            },
        )
        bridge = PortfolioRelativeRankAdjustmentBridge(store)

        outcome = bridge(_hook_input())

        assert outcome.rank_delta == 0.0
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_inspect_portfolio_relative_rank_adjustment_bridge_reports_invalid_plan_error():
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_status_invalid")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_portfolio_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "portfolio_relative_rank_adjustment.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.RANK_ADJUST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"rank_delta": 0.1},
            },
        )

        status = inspect_portfolio_relative_rank_adjustment_bridge(store)

        assert status.selection_status.value == "load_error"
        assert status.binding_present is True
        assert status.loaded is False
        assert status.failure_mode == ArtifactRuntimeFailureMode.FAIL_OPEN_BASELINE_SKIP_ARTIFACT
        assert status.error_stage == ArtifactRuntimeFailureStage.PLAN_SELECTION
        assert status.error_type == "ValueError"
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_portfolio_relative_rank_adjustment_bridge_fails_open_on_hook_execution_error(monkeypatch):
    state_dir = repo_build_path("build/test_protocols_portfolio_rank_bridge_hook_error")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = _publish_portfolio_snapshot(state_dir)
        atomic_write_json(
            state_dir / "compiled" / "snap-1" / "portfolio_relative_rank_adjustment.json",
            {
                "snapshot_id": "snap-1",
                "hook_id": HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT.value,
                "artifact_ids": ["artifact-1"],
                "action_kinds": [ArtifactActionKind.RANK_ADJUST.value],
                "generated_at_ms": 1000,
                "opaque_plan_payload": {"rank_delta": 0.1},
            },
        )
        bridge = PortfolioRelativeRankAdjustmentBridge(store)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(bridge_module, "run_portfolio_relative_rank_hook", _boom)

        outcome = bridge(_hook_input())

        assert outcome.rank_delta == 0.0
        assert outcome.reason_codes == ()
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
