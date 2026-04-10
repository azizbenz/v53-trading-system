"""Bounded executor surface for the canonical ENGINE_B_SWEEP_VALIDATION hook."""

from __future__ import annotations

from pydantic import BaseModel

from engines.engine_b import EngineBSweepValidationInput, EngineBSweepValidationOutcome
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.ENGINE_B_SWEEP_VALIDATION
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class EngineBSweepHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded Engine B sweep-validation hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    raw_score_multiplier_delta: float = 0.0
    raw_score_add: float = 0.0
    conviction_add: float = 0.0
    raw_score_cap: float | None = None
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
    hook_input: EngineBSweepValidationInput,
    hook_payload: EngineBSweepHookPlanPayload,
) -> EngineBSweepValidationOutcome:
    """Run the bounded Engine B sweep-validation hook with no dynamic code path."""

    if not hook_payload.blocked:
        detail = hook_payload.detail.strip()
        if not detail and (
            hook_payload.raw_score_multiplier_delta != 0.0
            or hook_payload.raw_score_add != 0.0
            or hook_payload.conviction_add != 0.0
            or hook_payload.raw_score_cap is not None
        ):
            detail = (
                f"compiled Engine B sweep validation adjusted {hook_input.pair} / "
                f"{hook_input.engine_id}"
            )
        return EngineBSweepValidationOutcome(
            accepted=True,
            reason_codes=hook_payload.block_reason_codes,
            detail=detail,
            raw_score_multiplier_delta=hook_payload.raw_score_multiplier_delta,
            raw_score_add=hook_payload.raw_score_add,
            conviction_add=hook_payload.conviction_add,
            raw_score_cap=hook_payload.raw_score_cap,
        )

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled Engine B sweep validation blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return EngineBSweepValidationOutcome(
        accepted=False,
        reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "EngineBSweepHookPlanPayload",
    "load_engine_b_sweep_hook_payload",
    "run_engine_b_sweep_hook",
]
