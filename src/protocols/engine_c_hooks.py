"""Bounded executor surface for the canonical ENGINE_C_VOID_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel

from engines.engine_c import EngineCVoidValidationInput, EngineCVoidValidationOutcome
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_C_VOID_VALIDATION
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class EngineCVoidHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded Engine C void-validation hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
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
    hook_input: EngineCVoidValidationInput,
    hook_payload: EngineCVoidHookPlanPayload,
) -> EngineCVoidValidationOutcome:
    """Run the bounded Engine C void-validation hook with no dynamic code path."""

    if not hook_payload.blocked:
        detail = hook_payload.detail.strip()
        if not detail:
            detail = (
                f"compiled Engine C void validation accepted {hook_input.pair} / "
                f"{hook_input.engine_id}"
            )
        return EngineCVoidValidationOutcome(
            accepted=True,
            reason_codes=hook_payload.block_reason_codes,
            detail=detail,
        )

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled Engine C void validation blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return EngineCVoidValidationOutcome(
        accepted=False,
        reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineCVoidHookPlanPayload",
    "load_engine_c_void_hook_payload",
    "run_engine_c_void_hook",
]
