"""Bounded executor surface for the canonical PORTFOLIO_RELATIVE_RANK_ADJUSTMENT hook."""

from __future__ import annotations

from pydantic import BaseModel

from portfolio_minimal import (
    PortfolioRelativeRankAdjustmentInput,
    PortfolioRelativeRankAdjustmentOutcome,
)
from interface_contracts import HookId, is_runtime_open_hook_id

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT
RUNTIME_OPEN = is_runtime_open_hook_id(HOOK_ID)


class PortfolioRelativeRankHookPlanPayload(BaseModel, frozen=True):
    """Typed compiled payload for the bounded portfolio rank-adjustment hook."""

    rank_delta: float = 0.0
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


def load_portfolio_relative_rank_hook_payload(
    selection: CompiledHookPlanSelection,
) -> PortfolioRelativeRankHookPlanPayload:
    """Load a typed payload for the canonical portfolio hook."""

    if selection.hook_id != HOOK_ID:
        raise ValueError(
            "load_portfolio_relative_rank_hook_payload requires PORTFOLIO_RELATIVE_RANK_ADJUSTMENT"
        )
    if selection.status != CompiledHookPlanLoadStatus.LOADED or selection.plan is None:
        raise ValueError("portfolio hook payload requires a loaded compiled plan")
    if selection.plan.hook_id != HOOK_ID:
        raise ValueError("compiled hook plan must target PORTFOLIO_RELATIVE_RANK_ADJUSTMENT")
    return PortfolioRelativeRankHookPlanPayload.model_validate(selection.plan.opaque_plan_payload)


def run_portfolio_relative_rank_hook(
    hook_input: PortfolioRelativeRankAdjustmentInput,
    hook_payload: PortfolioRelativeRankHookPlanPayload,
) -> PortfolioRelativeRankAdjustmentOutcome:
    """Run the bounded portfolio relative-rank hook with no dynamic code path."""

    detail = hook_payload.detail.strip()
    if not detail:
        detail = (
            f"compiled portfolio relative-rank adjustment evaluated {hook_input.pair} / "
            f"{hook_input.engine_id}"
        )
    return PortfolioRelativeRankAdjustmentOutcome(
        rank_delta=hook_payload.rank_delta,
        reason_codes=hook_payload.reason_codes,
        detail=detail,
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "PortfolioRelativeRankHookPlanPayload",
    "load_portfolio_relative_rank_hook_payload",
    "run_portfolio_relative_rank_hook",
]
