"""Typed skeleton for the canonical PORTFOLIO_RELATIVE_RANK_ADJUSTMENT hook."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import HookId

from .compiled_hook_plan_loader import (
    CompiledHookPlanLoadStatus,
    CompiledHookPlanSelection,
)


HOOK_ID = HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT
RUNTIME_OPEN = False


class PortfolioRelativeRankHookPlanPayload(BaseModel, frozen=True):
    """Minimal compiled payload shape for the unopened portfolio hook rail."""

    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class PortfolioRelativeRankHookInput(BaseModel, frozen=True):
    """Minimal typed input kept intentionally narrow until the rail is opened."""

    context_id: str = Field(..., min_length=1)
    pair: str = ""
    engine_id: str = ""


class PortfolioRelativeRankHookOutcome(BaseModel, frozen=True):
    """Placeholder typed outcome for the unopened portfolio hook rail."""

    accepted: bool = True
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
    hook_input: PortfolioRelativeRankHookInput,
    hook_payload: PortfolioRelativeRankHookPlanPayload,
) -> PortfolioRelativeRankHookOutcome:
    """Keep the hook explicitly closed until the portfolio artifact rail is opened."""

    raise NotImplementedError(
        "PORTFOLIO_RELATIVE_RANK_ADJUSTMENT remains a typed skeleton until this hook rail is opened"
    )


__all__ = [
    "HOOK_ID",
    "RUNTIME_OPEN",
    "PortfolioRelativeRankHookPlanPayload",
    "PortfolioRelativeRankHookInput",
    "PortfolioRelativeRankHookOutcome",
    "load_portfolio_relative_rank_hook_payload",
    "run_portfolio_relative_rank_hook",
]
