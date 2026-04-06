"""Canonical execution hook module wrapper aligned with HOOK_MODULE_BY_ID."""

from __future__ import annotations

from interface_contracts import HookId

from .execution_no_trade_hook import (
    ExecutionNoTradeHookInput,
    ExecutionNoTradeHookOutcome,
    ExecutionNoTradeHookPlanPayload,
    load_execution_no_trade_hook_payload,
    run_execution_no_trade_hook,
)


HOOK_ID = HookId.EXECUTION_NO_TRADE_FILTER
RUNTIME_OPEN = True

ExecutionHookPlanPayload = ExecutionNoTradeHookPlanPayload
ExecutionHookInput = ExecutionNoTradeHookInput
ExecutionHookOutcome = ExecutionNoTradeHookOutcome
load_execution_hook_payload = load_execution_no_trade_hook_payload
run_execution_hook = run_execution_no_trade_hook


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "ExecutionHookPlanPayload",
    "ExecutionHookInput",
    "ExecutionHookOutcome",
    "load_execution_hook_payload",
    "run_execution_hook",
]
