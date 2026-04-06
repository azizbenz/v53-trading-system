"""Typed skeleton for the canonical ENGINE_D_REENTRY_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_D_REENTRY_VALIDATION
RUNTIME_OPEN = False


class EngineDReentryHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened Engine D hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineDReentryHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class EngineDReentryHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened Engine D hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_engine_d_reentry_hook_payload(
    selection: CompiledHookPlanSelection,
) -> EngineDReentryHookPlanPayload:
    """Load a typed payload for the canonical Engine D hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_engine_d_reentry_hook_payload requires ENGINE_D_REENTRY_VALIDATION")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("engine_d hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target ENGINE_D_REENTRY_VALIDATION")
    return EngineDReentryHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_engine_d_reentry_hook(
    hook_input: EngineDReentryHookInput,
    hook_payload: EngineDReentryHookPlanPayload,
) -> EngineDReentryHookOutcome:
    """Keep the hook explicitly closed until the Engine D artifact rail is opened."""

    raise NotImplementedError(
        "ENGINE_D_REENTRY_VALIDATION remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineDReentryHookPlanPayload",
    "EngineDReentryHookInput",
    "EngineDReentryHookOutcome",
    "load_engine_d_reentry_hook_payload",
    "run_engine_d_reentry_hook",
]
