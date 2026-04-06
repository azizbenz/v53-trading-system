"""Execution-edge supervision helpers for the bounded compiled no-trade bridge."""

from __future__ import annotations

from pathlib import Path

from monitoring import ExecutionNoTradeBridgeProjection
from protocols.execution_no_trade_filter_bridge import ExecutionNoTradeFilterBridgeStatus
from protocols.execution_runtime_bootstrap import inspect_execution_runtime_bootstrap


def _status_from_bridge_status(status: ExecutionNoTradeFilterBridgeStatus) -> str:
    if not status.configured:
        return "planned"
    if status.error_type:
        return "warning"
    if status.loaded:
        return "healthy"
    if status.selection_status.value == "binding_only":
        return "warning"
    if status.selection_status.value in {"no_binding", "no_snapshot"}:
        return "info"
    return "info"


def build_execution_no_trade_bridge_projection(
    *,
    compiled_registry_state_dir: str | Path | None = None,
) -> ExecutionNoTradeBridgeProjection:
    """Project the current execution bootstrap state into the governed monitoring surface."""

    status = inspect_execution_runtime_bootstrap(
        compiled_registry_state_dir=compiled_registry_state_dir
    )
    detail = status.error_detail.strip()
    if not detail:
        if not status.configured:
            detail = "Compiled execution no-trade bridge not configured"
        elif status.loaded:
            detail = "Compiled execution no-trade bridge loaded from current snapshot"
        elif status.binding_present:
            detail = "Compiled execution no-trade bridge binding published but plan not loaded"
        else:
            detail = "Compiled execution no-trade bridge configured without active binding"
    return ExecutionNoTradeBridgeProjection(
        status=_status_from_bridge_status(status),
        configured=status.configured,
        selection_status=status.selection_status.value,
        current_snapshot_id=status.current_snapshot_id,
        previous_snapshot_id=status.previous_snapshot_id,
        last_known_good_snapshot_id=status.last_known_good_snapshot_id,
        binding_present=status.binding_present,
        loaded=status.loaded,
        compiled_plan_ref=status.compiled_plan_ref,
        artifact_count=len(status.artifact_ids),
        error_type=status.error_type,
        detail=detail,
    )


__all__ = ["build_execution_no_trade_bridge_projection"]
