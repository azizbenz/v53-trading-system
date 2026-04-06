"""Typed skeleton for the canonical RISK_MICRO_FRICTION_PRECHECK hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.RISK_MICRO_FRICTION_PRECHECK
RUNTIME_OPEN = False


class RiskMicroFrictionHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened risk hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class RiskMicroFrictionHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class RiskMicroFrictionHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened risk hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
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
    hook_input: RiskMicroFrictionHookInput,
    hook_payload: RiskMicroFrictionHookPlanPayload,
) -> RiskMicroFrictionHookOutcome:
    """Keep the hook explicitly closed until the risk artifact rail is opened."""

    raise NotImplementedError(
        "RISK_MICRO_FRICTION_PRECHECK remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "RiskMicroFrictionHookPlanPayload",
    "RiskMicroFrictionHookInput",
    "RiskMicroFrictionHookOutcome",
    "load_risk_micro_friction_hook_payload",
    "run_risk_micro_friction_hook",
]
