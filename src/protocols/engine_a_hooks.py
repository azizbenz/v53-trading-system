"""Typed skeleton for the canonical ENGINE_A_PRE_ENTRY_CONFIRMATION hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION
RUNTIME_OPEN = False


class EngineAPreEntryHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened Engine A hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineAPreEntryHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class EngineAPreEntryHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened Engine A hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_engine_a_pre_entry_hook_payload(
    selection: CompiledHookPlanSelection,
) -> EngineAPreEntryHookPlanPayload:
    """Load a typed payload for the canonical Engine A hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_engine_a_pre_entry_hook_payload requires ENGINE_A_PRE_ENTRY_CONFIRMATION")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("engine_a hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target ENGINE_A_PRE_ENTRY_CONFIRMATION")
    return EngineAPreEntryHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_engine_a_pre_entry_hook(
    hook_input: EngineAPreEntryHookInput,
    hook_payload: EngineAPreEntryHookPlanPayload,
) -> EngineAPreEntryHookOutcome:
    """Keep the hook explicitly closed until the Engine A artifact rail is opened."""

    raise NotImplementedError(
        "ENGINE_A_PRE_ENTRY_CONFIRMATION remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineAPreEntryHookPlanPayload",
    "EngineAPreEntryHookInput",
    "EngineAPreEntryHookOutcome",
    "load_engine_a_pre_entry_hook_payload",
    "run_engine_a_pre_entry_hook",
]
