"""Bounded executor surface for the canonical SCORING_SOFT_PENALTY_LAYER hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from scoring_backbone import ScoringSoftPenaltyLayerInput, ScoringSoftPenaltyLayerOutcome
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.SCORING_SOFT_PENALTY_LAYER
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class ScoringSoftPenaltyHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded scoring soft-penalty hook."""

    raw_score_multiplier_delta: float = 0.0
    raw_score_add: float = 0.0
    raw_score_cap: float | None = Field(default=None, ge=0.0)
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
    hook_input: ScoringSoftPenaltyLayerInput,
    hook_payload: ScoringSoftPenaltyHookPlanPayload,
) -> ScoringSoftPenaltyLayerOutcome:
    """Run the bounded scoring soft-penalty hook with no dynamic code path."""

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled scoring soft-penalty layer evaluated {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return ScoringSoftPenaltyLayerOutcome(
        raw_score_multiplier_delta=hook_payload.raw_score_multiplier_delta,
        raw_score_add=hook_payload.raw_score_add,
        raw_score_cap=hook_payload.raw_score_cap,
        reason_codes=hook_payload.reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "ScoringSoftPenaltyHookPlanPayload",
    "load_scoring_soft_penalty_hook_payload",
    "run_scoring_soft_penalty_hook",
]
