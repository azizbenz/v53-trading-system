"""Typed skeleton for the canonical SCORING_SOFT_PENALTY_LAYER hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.SCORING_SOFT_PENALTY_LAYER
RUNTIME_OPEN = False


class ScoringSoftPenaltyHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened scoring hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class ScoringSoftPenaltyHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class ScoringSoftPenaltyHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened scoring hook rail."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_scoring_soft_penalty_hook_payload(
    selection: CompiledHookPlanSelection,
) -> ScoringSoftPenaltyHookPlanPayload:
    """Load a typed payload for the canonical scoring hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError("load_scoring_soft_penalty_hook_payload requires SCORING_SOFT_PENALTY_LAYER")
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("scoring hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target SCORING_SOFT_PENALTY_LAYER")
    return ScoringSoftPenaltyHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_scoring_soft_penalty_hook(
    hook_input: ScoringSoftPenaltyHookInput,
    hook_payload: ScoringSoftPenaltyHookPlanPayload,
) -> ScoringSoftPenaltyHookOutcome:
    """Keep the hook explicitly closed until the scoring artifact rail is opened."""

    raise NotImplementedError(
        "SCORING_SOFT_PENALTY_LAYER remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "ScoringSoftPenaltyHookPlanPayload",
    "ScoringSoftPenaltyHookInput",
    "ScoringSoftPenaltyHookOutcome",
    "load_scoring_soft_penalty_hook_payload",
    "run_scoring_soft_penalty_hook",
]
