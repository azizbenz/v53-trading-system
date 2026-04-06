"""Typed skeleton for the canonical ENGINE_B_SWEEP_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_B_SWEEP_VALIDATION
RUNTIME_OPEN = False


class EngineBSweepHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened Engine B hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineBSweepHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class EngineBSweepHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened Engine B hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_engine_b_sweep_hook_payload(
    selection: CompiledHookPlanSelection,
) -> EngineBSweepHookPlanPayload:
    """Load a typed payload for the canonical Engine B hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_engine_b_sweep_hook_payload requires ENGINE_B_SWEEP_VALIDATION")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("engine_b hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target ENGINE_B_SWEEP_VALIDATION")
    return EngineBSweepHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_engine_b_sweep_hook(
    hook_input: EngineBSweepHookInput,
    hook_payload: EngineBSweepHookPlanPayload,
) -> EngineBSweepHookOutcome:
    """Keep the hook explicitly closed until the Engine B artifact rail is opened."""

    raise NotImplementedError(
        "ENGINE_B_SWEEP_VALIDATION remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineBSweepHookPlanPayload",
    "EngineBSweepHookInput",
    "EngineBSweepHookOutcome",
    "load_engine_b_sweep_hook_payload",
    "run_engine_b_sweep_hook",
]
