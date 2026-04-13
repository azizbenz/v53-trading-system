"""Bounded executor surface for the canonical ENGINE_D_REENTRY_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel

from interface_contracts import (
    EngineDReentryValidationInput,
    EngineDReentryValidationOutcome,
    HookId,
    is_runtime_open_hook_id,
)

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_D_REENTRY_VALIDATION
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class EngineDReentryHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded Engine D re-entry validation hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
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
    hook_input: EngineDReentryValidationInput,
    hook_payload: EngineDReentryHookPlanPayload,
) -> EngineDReentryValidationOutcome:
    """Run the bounded Engine D re-entry validation hook with no dynamic code path."""

    if not hook_payload.blocked:
        detail = hook_payload.detail.strip()
        if not detail:
            detail = (
                f"compiled Engine D re-entry validation accepted {hook_input.pair} / "
                f"{hook_input.engine_id}"
            )
        return EngineDReentryValidationOutcome(
            accepted=True,
            reason_codes=hook_payload.block_reason_codes,
            detail=detail,
        )

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled Engine D re-entry validation blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return EngineDReentryValidationOutcome(
        accepted=False,
        reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineDReentryHookPlanPayload",
    "load_engine_d_reentry_hook_payload",
    "run_engine_d_reentry_hook",
]
