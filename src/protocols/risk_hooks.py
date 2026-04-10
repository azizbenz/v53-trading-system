"""Bounded executor surface for the canonical RISK_MICRO_FRICTION_PRECHECK hook."""

from __future__ import annotations

from pydantic import BaseModel

from risk_backbone import RiskMicroFrictionPrecheckInput, RiskMicroFrictionPrecheckOutcome
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.RISK_MICRO_FRICTION_PRECHECK
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class RiskMicroFrictionHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded risk micro-friction hook."""

    blocked: bool = False
    block_reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_risk_micro_friction_hook_payload(
    selection: CompiledHookPlanSelection,
) -> RiskMicroFrictionHookPlanPayload:
    """Load a typed payload for the canonical risk hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_risk_micro_friction_hook_payload requires RISK_MICRO_FRICTION_PRECHECK")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("risk hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target RISK_MICRO_FRICTION_PRECHECK")
    return RiskMicroFrictionHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_risk_micro_friction_hook(
    hook_input: RiskMicroFrictionPrecheckInput,
    hook_payload: RiskMicroFrictionHookPlanPayload,
) -> RiskMicroFrictionPrecheckOutcome:
    """Run the bounded risk micro-friction hook with no dynamic code path."""

    if not hook_payload.blocked:
        detail = hook_payload.detail.strip()
        if not detail:
            detail = (
                f"compiled risk micro-friction precheck accepted {hook_input.pair} / "
                f"{hook_input.engine_id}"
            )
        return RiskMicroFrictionPrecheckOutcome(
            accepted=True,
            reason_codes=hook_payload.block_reason_codes,
            detail=detail,
        )

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled risk micro-friction precheck blocked {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return RiskMicroFrictionPrecheckOutcome(
        accepted=False,
        reason_codes=hook_payload.block_reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "RiskMicroFrictionHookPlanPayload",
    "load_risk_micro_friction_hook_payload",
    "run_risk_micro_friction_hook",
]
