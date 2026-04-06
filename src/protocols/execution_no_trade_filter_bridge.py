"""Thin bridge from the compiled hook-plan rail to the execution-edge veto surface."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from execution_backbone.execution_runtime import (
    ExecutionNoTradeFilterInput,
    ExecutionNoTradeFilterOutcome,
)
from interface_contracts import ArtifactActionKind, HookId

from .compiled_artifact_registry_store import CompiledArtifactRegistryStore
from .compiled_hook_plan_loader import CompiledHookPlanLoadStatus, select_current_compiled_hook_plan
from .execution_no_trade_hook import (
    ExecutionNoTradeHookInput,
    load_execution_no_trade_hook_payload,
    run_execution_no_trade_hook,
)


logger = logging.getLogger(__name__)


class ExecutionNoTradeFilterBridgeStatus(BaseModel, frozen=True):
    """Operational status of the bounded compiled no-trade bridge."""

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
    error_type: str = ""
    error_detail: str = ""


class ExecutionNoTradeFilterBridge:
    """Resolve the current compiled no-trade plan into the execution-edge filter."""

    def __init__(self, store: CompiledArtifactRegistryStore) -> None:
        self._store = store

    def __call__(self, hook_input: ExecutionNoTradeFilterInput) -> ExecutionNoTradeFilterOutcome:
        try:
            selection = select_current_compiled_hook_plan(
                self._store,
                HookId.EXECUTION_NO_TRADE_FILTER,
            )
            if selection.status != CompiledHookPlanLoadStatus.LOADED:
                return ExecutionNoTradeFilterOutcome()
            payload = load_execution_no_trade_hook_payload(selection)
            outcome = run_execution_no_trade_hook(
                ExecutionNoTradeHookInput.model_validate(hook_input.model_dump()),
                payload,
            )
            return ExecutionNoTradeFilterOutcome.model_validate(outcome.model_dump())
        except Exception as exc:
            logger.warning(
                "execution_no_trade_filter_bridge_failed",
                extra={
                    "hook_id": HookId.EXECUTION_NO_TRADE_FILTER.value,
                    "error_type": type(exc).__name__,
                },
            )
            return ExecutionNoTradeFilterOutcome()

    def status(self) -> ExecutionNoTradeFilterBridgeStatus:
        return inspect_execution_no_trade_filter_bridge(self._store)


def inspect_execution_no_trade_filter_bridge(
    store: CompiledArtifactRegistryStore,
) -> ExecutionNoTradeFilterBridgeStatus:
    """Inspect the current compiled no-trade bridge state outside the hot path."""

    pointer = store.load_pointer()
    snapshot = store.load_current_snapshot()
    binding = None
    if snapshot is not None:
        binding = next(
            (
                candidate
                for candidate in snapshot.hook_bindings
                if candidate.hook_id == HookId.EXECUTION_NO_TRADE_FILTER
            ),
            None,
        )
    if snapshot is None:
        return ExecutionNoTradeFilterBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.NO_SNAPSHOT,
        )
    if binding is None:
        return ExecutionNoTradeFilterBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.NO_BINDING,
        )
    if not binding.compiled_plan_ref:
        return ExecutionNoTradeFilterBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.BINDING_ONLY,
            binding_present=True,
            compiled_plan_ref=binding.compiled_plan_ref,
            artifact_ids=binding.artifact_ids,
            action_kinds=binding.action_kinds,
        )
    try:
        selection = select_current_compiled_hook_plan(
            store,
            HookId.EXECUTION_NO_TRADE_FILTER,
        )
        return ExecutionNoTradeFilterBridgeStatus(
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
        )
    except Exception as exc:
        return ExecutionNoTradeFilterBridgeStatus(
            state_dir=str(store.state_dir),
            current_snapshot_id=pointer.current_snapshot_id,
            previous_snapshot_id=pointer.previous_snapshot_id,
            last_known_good_snapshot_id=pointer.last_known_good_snapshot_id,
            selection_status=CompiledHookPlanLoadStatus.BINDING_ONLY,
            binding_present=True,
            compiled_plan_ref=binding.compiled_plan_ref,
            artifact_ids=binding.artifact_ids,
            action_kinds=binding.action_kinds,
            error_type=type(exc).__name__,
            error_detail=str(exc),
        )


__all__ = [
    "ExecutionNoTradeFilterBridge",
    "ExecutionNoTradeFilterBridgeStatus",
    "inspect_execution_no_trade_filter_bridge",
]
