"""Bounded executor surface for the canonical ENGINE_A_PRE_ENTRY_CONFIRMATION hook."""

from __future__ import annotations

from pydantic import BaseModel

from engines.engine_a import EngineAPreEntryValidationInput, EngineAPreEntryValidationOutcome
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class EngineAPreEntryHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded Engine A pre-entry hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
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
    hook_input: EngineAPreEntryValidationInput,
    hook_payload: EngineAPreEntryHookPlanPayload,
) -> EngineAPreEntryValidationOutcome:
    """Run the bounded Engine A pre-entry hook with no dynamic code path."""

    if not hook_payload.blocked:
        detail = hook_payload.detail.strip()
        if not detail:
            detail = (
                f"compiled Engine A pre-entry confirmation accepted {hook_input.pair} / "
                f"{hook_input.engine_id}"
            )
        return EngineAPreEntryValidationOutcome(
            accepted=True,
            reason_codes=hook_payload.block_reason_codes,
            detail=detail,
        )

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled Engine A pre-entry confirmation blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return EngineAPreEntryValidationOutcome(
        accepted=False,
        reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineAPreEntryHookPlanPayload",
    "load_engine_a_pre_entry_hook_payload",
    "run_engine_a_pre_entry_hook",
]
