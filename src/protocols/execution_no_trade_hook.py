"""Bounded executor surface for the canonical EXECUTION_NO_TRADE_FILTER hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


class ExecutionNoTradeHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the execution no-trade hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    detail: str = ""


class ExecutionNoTradeHookInput(BaseModel, frozen=True):
    """Minimal typed input required by the bounded execution no-trade hook."""

    intent_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    expected_cost: float = 0.0
    expected_gain: float = 0.0
    score: float = 0.0


class ExecutionNoTradeHookOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded execution no-trade hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_execution_no_trade_hook_payload(
    selection: CompiledHookPlanSelection,
) -> ExecutionNoTradeHookPlanPayload:
    """Load a typed no-trade hook payload from a selected compiled plan."""

    if selection.hook_id != HookId.EXECUTION_NO_TRADE_FILTER:
        raise ValueError("load_execution_no_trade_hook_payload requires EXECUTION_NO_TRADE_FILTER")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("execution no-trade hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HookId.EXECUTION_NO_TRADE_FILTER:
        raise ValueError("compiled hook plan must target EXECUTION_NO_TRADE_FILTER")
    return ExecutionNoTradeHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_execution_no_trade_hook(
    hook_input: ExecutionNoTradeHookInput,
    hook_payload: ExecutionNoTradeHookPlanPayload,
) -> ExecutionNoTradeHookOutcome:
    """Run the bounded execution no-trade hook with no dynamic code path."""

    if not hook_payload.blocked:
        return ExecutionNoTradeHookOutcome()

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled execution no-trade filter blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return ExecutionNoTradeHookOutcome(
        blocked=True,
        block_reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "ExecutionNoTradeHookPlanPayload",
    "ExecutionNoTradeHookInput",
    "ExecutionNoTradeHookOutcome",
    "load_execution_no_trade_hook_payload",
    "run_execution_no_trade_hook",
]
