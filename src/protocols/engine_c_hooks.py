"""Typed skeleton for the canonical ENGINE_C_VOID_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_C_VOID_VALIDATION
RUNTIME_OPEN = False


class EngineCVoidHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened Engine C hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineCVoidHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class EngineCVoidHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened Engine C hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_engine_c_void_hook_payload(
    selection: CompiledHookPlanSelection,
) -> EngineCVoidHookPlanPayload:
    """Load a typed payload for the canonical Engine C hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_engine_c_void_hook_payload requires ENGINE_C_VOID_VALIDATION")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("engine_c hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target ENGINE_C_VOID_VALIDATION")
    return EngineCVoidHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_engine_c_void_hook(
    hook_input: EngineCVoidHookInput,
    hook_payload: EngineCVoidHookPlanPayload,
) -> EngineCVoidHookOutcome:
    """Keep the hook explicitly closed until the Engine C artifact rail is opened."""

    raise NotImplementedError(
        "ENGINE_C_VOID_VALIDATION remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineCVoidHookPlanPayload",
    "EngineCVoidHookInput",
    "EngineCVoidHookOutcome",
    "load_engine_c_void_hook_payload",
    "run_engine_c_void_hook",
]
