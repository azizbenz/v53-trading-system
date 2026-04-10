"""Thin bridge from the compiled hook-plan rail to the portfolio relative-rank hook."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from interface_contracts import (
    ArtifactActionKind,
    ArtifactRuntimeFailureMode,
    ArtifactRuntimeFailureStage,
    CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY,
    HookId,
)
from portfolio_minimal import (
    PortfolioRelativeRankAdjustmentInput,
    PortfolioRelativeRankAdjustmentOutcome,
)

from .compiled_artifact_registry_store import CompiledArtifactRegistryStore
from .compiled_hook_plan_loader import CompiledHookPlanLoadStatus, select_current_compiled_hook_plan
from .portfolio_hooks import (
    load_portfolio_relative_rank_hook_payload,
    run_portfolio_relative_rank_hook,
)


logger = logging.getLogger(__name__)


class PortfolioRelativeRankAdjustmentBridgeStatus(BaseModel, frozen=True):
    """Operational status of the bounded compiled portfolio rank-adjustment bridge."""

    configured: bool = True
    state_dir: str = ""
    current_snapshot_id: str = ""
    previous_snapshot_id: str = ""
    last_known_good_snapshot_id: str = ""
    selection_status: CompiledHookPlanLoadStatus = CompiledHookPlanLoadStatus.NO_SNAPSHOT
    binding_present: bool = False
    compiled_plan_ref: str = ""
    artifact_ids: tuple[str, ...] = ()
    action_kinds: tuple[ArtifactActionKind, ...] = ()
    loaded: bool = False
    failure_mode: ArtifactRuntimeFailureMode = (
        CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode
    )
    error_stage: ArtifactRuntimeFailureStage | None = None
    error_type: str = ""
    error_detail: str = ""


class PortfolioRelativeRankAdjustmentBridge:
    """Resolve the current compiled portfolio plan into the runtime rank hook."""

    def __init__(self, store: CompiledArtifactRegistryStore) -> None:
        self._store = store

    def __call__(
        self,
        hook_input: PortfolioRelativeRankAdjustmentInput,
    ) -> PortfolioRelativeRankAdjustmentOutcome:
        selection = select_current_compiled_hook_plan(
            self._store,
            HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
        )
        if selection.status == CompiledHookPlanLoadStatus.LOAD_ERROR:
            return _fail_open_outcome(
                ArtifactRuntimeFailureStage.PLAN_SELECTION,
                error_type=selection.error_type or "LoadError",
                error_detail=selection.error_detail,
            )
        if selection.status != CompiledHookPlanLoadStatus.LOADED:
            return PortfolioRelativeRankAdjustmentOutcome()
        try:
            payload = load_portfolio_relative_rank_hook_payload(selection)
        except Exception as exc:
            return _fail_open_outcome(
                ArtifactRuntimeFailureStage.PAYLOAD_LOAD,
                error_type=type(exc).__name__,
                error_detail=str(exc),
            )
        try:
            return run_portfolio_relative_rank_hook(hook_input, payload)
        except Exception as exc:
            return _fail_open_outcome(
                ArtifactRuntimeFailureStage.HOOK_EXECUTION,
                error_type=type(exc).__name__,
                error_detail=str(exc),
            )

    def status(self) -> PortfolioRelativeRankAdjustmentBridgeStatus:
        return inspect_portfolio_relative_rank_adjustment_bridge(self._store)


def inspect_portfolio_relative_rank_adjustment_bridge(
    store: CompiledArtifactRegistryStore,
) -> PortfolioRelativeRankAdjustmentBridgeStatus:
    """Inspect the current compiled portfolio rank-adjustment bridge state."""

    pointer = store.load_pointer()
    snapshot = store.load_current_snapshot()
    binding = None
    if snapshot is not None:
        binding = next(
            (
                candidate
                for candidate in snapshot.hook_bindings
                if candidate.hook_id == HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT
            ),
            None,
        )
    if snapshot is None:
        return PortfolioRelativeRankAdjustmentBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.NO_SNAPSHOT,
            failure_mode=CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode,
        )
    if binding is None:
        return PortfolioRelativeRankAdjustmentBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.NO_BINDING,
            failure_mode=CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode,
        )
    if not binding.compiled_plan_ref:
        return PortfolioRelativeRankAdjustmentBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.BINDING_ONLY,
            binding_present=True,
            compiled_plan_ref=binding.compiled_plan_ref,
            artifact_ids=binding.artifact_ids,
            action_kinds=binding.action_kinds,
            failure_mode=CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode,
        )
    selection = select_current_compiled_hook_plan(
        store,
        HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
    )
    return PortfolioRelativeRankAdjustmentBridgeStatus(
        state_dir=str(store.state_dir),
        current_snapshot_id=pointer.current_snapshot_id,
        previous_snapshot_id=pointer.previous_snapshot_id,
        last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
        selection_status=selection.status,
        binding_present=selection.binding is not None,
        compiled_plan_ref=selection.binding.compiled_plan_ref if selection.binding is not None else "",
        artifact_ids=selection.binding.artifact_ids if selection.binding is not None else (),
        action_kinds=selection.binding.action_kinds if selection.binding is not None else (),
        loaded=selection.status == CompiledHookPlanLoadStatus.LOADED,
        failure_mode=CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode,
        error_stage=(
            ArtifactRuntimeFailureStage.PLAN_SELECTION
            if selection.status == CompiledHookPlanLoadStatus.LOAD_ERROR
            else None
        ),
        error_type=selection.error_type,
        error_detail=selection.error_detail,
    )


def _fail_open_outcome(
    stage: ArtifactRuntimeFailureStage,
    *,
    error_type: str,
    error_detail: str = "",
) -> PortfolioRelativeRankAdjustmentOutcome:
    failure_mode = {
        ArtifactRuntimeFailureStage.PLAN_SELECTION: (
            CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.selection_failure_mode
        ),
        ArtifactRuntimeFailureStage.PAYLOAD_LOAD: (
            CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.payload_load_failure_mode
        ),
        ArtifactRuntimeFailureStage.HOOK_EXECUTION: (
            CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY.hook_execution_failure_mode
        ),
    }[stage]
    logger.warning(
        "portfolio_relative_rank_adjustment_bridge_failed",
        extra={
            "hook_id": HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT.value,
            "error_stage": stage.value,
            "failure_mode": failure_mode.value,
            "error_type": error_type,
        },
    )
    return PortfolioRelativeRankAdjustmentOutcome()


__all__ = [
    "PortfolioRelativeRankAdjustmentBridge",
    "PortfolioRelativeRankAdjustmentBridgeStatus",
    "inspect_portfolio_relative_rank_adjustment_bridge",
]
