from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from interface_contracts import ArtifactActionKind, HookId
from interface_contracts.atomic_io import atomic_write_json
from portfolio_minimal import PortfolioRelativeRankAdjustmentInput
from protocols import (
    CompiledArtifactHookBinding,
    CompiledArtifactRegistrySnapshot,
    CompiledArtifactRegistryStore,
    PortfolioRelativeRankHookPlanPayload,
    load_portfolio_relative_rank_hook_payload,
    run_portfolio_relative_rank_hook,
    select_current_compiled_hook_plan,
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


def test_load_portfolio_relative_rank_hook_payload_from_loaded_selection():
    state_dir = repo_build_path("build/test_protocols_portfolio_relative_rank_hook_loaded")
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
        selection = select_current_compiled_hook_plan(store, HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT)

        payload = load_portfolio_relative_rank_hook_payload(selection)

        assert payload.rank_delta == pytest.approx(0.20)
        assert payload.reason_codes == ("ARTIFACT_PORTFOLIO_RANK_BOOST",)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_load_portfolio_relative_rank_hook_payload_rejects_wrong_hook():
    state_dir = repo_build_path("build/test_protocols_portfolio_relative_rank_hook_wrong_hook")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        store = CompiledArtifactRegistryStore(state_dir)
        selection = select_current_compiled_hook_plan(store, HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION)
        with pytest.raises(ValueError):
            load_portfolio_relative_rank_hook_payload(selection)
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


def test_run_portfolio_relative_rank_hook_returns_typed_adjustment():
    outcome = run_portfolio_relative_rank_hook(
        _hook_input(),
        PortfolioRelativeRankHookPlanPayload(
            rank_delta=0.20,
            reason_codes=("ARTIFACT_PORTFOLIO_RANK_BOOST",),
            detail="artifact portfolio rank adjustment applied",
        ),
    )

    assert outcome.rank_delta == pytest.approx(0.20)
    assert outcome.reason_codes == ("ARTIFACT_PORTFOLIO_RANK_BOOST",)
    assert outcome.detail == "artifact portfolio rank adjustment applied"


def test_run_portfolio_relative_rank_hook_uses_neutral_defaults():
    outcome = run_portfolio_relative_rank_hook(
        _hook_input(),
        PortfolioRelativeRankHookPlanPayload(),
    )

    assert outcome.rank_delta == pytest.approx(0.0)
    assert outcome.reason_codes == ()
