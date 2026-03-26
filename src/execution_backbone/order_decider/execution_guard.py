"""
Build-3 / order_decider / execution_guard
Refuse execution if cost, pair health, or infrastructure state make it non-credible.

Invariant: no order bypasses hard blockers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GuardVerdict(StrEnum):
    PASS = "pass"
    BLOCK = "block"


class BlockReason(StrEnum):
    PAIR_SUSPENDED = "pair_suspended"
    PAIR_HEALTH_LOW = "pair_health_low"
    RISK_BUDGET_EXHAUSTED = "risk_budget_exhausted"
    INFRASTRUCTURE_DOWN = "infrastructure_down"
    STALE_DATA = "stale_data"
    COST_TOO_HIGH = "cost_too_high"


class GuardResult(BaseModel, frozen=True):
    """Result of execution guard check."""

    verdict: GuardVerdict
    blocks: tuple[BlockReason, ...] = ()
    detail: str = ""


def check_execution_guards(
    pair_suspended: bool = False,
    pair_health_score: float = 1.0,
    pair_health_min: float = 0.3,
    risk_budget_available: bool = True,
    infrastructure_ok: bool = True,
    data_stale: bool = False,
    expected_cost: float = 0.0,
    max_acceptable_cost: float = 0.01,
) -> GuardResult:
    """Check all hard blockers before execution.

    Returns BLOCK with reasons if any condition fails.
    """
    blocks: list[BlockReason] = []
    details: list[str] = []

    if pair_suspended:
        blocks.append(BlockReason.PAIR_SUSPENDED)
        details.append("pair is suspended")

    if pair_health_score < pair_health_min:
        blocks.append(BlockReason.PAIR_HEALTH_LOW)
        details.append(f"pair health {pair_health_score:.3f} < min {pair_health_min:.3f}")

    if not risk_budget_available:
        blocks.append(BlockReason.RISK_BUDGET_EXHAUSTED)
        details.append("risk budget exhausted")

    if not infrastructure_ok:
        blocks.append(BlockReason.INFRASTRUCTURE_DOWN)
        details.append("infrastructure not operational")

    if data_stale:
        blocks.append(BlockReason.STALE_DATA)
        details.append("data is stale (hard block)")

    if expected_cost > max_acceptable_cost:
        blocks.append(BlockReason.COST_TOO_HIGH)
        details.append(f"expected cost {expected_cost:.6f} > max {max_acceptable_cost:.6f}")

    if blocks:
        return GuardResult(
            verdict=GuardVerdict.BLOCK,
            blocks=tuple(blocks),
            detail="; ".join(details),
        )

    return GuardResult(verdict=GuardVerdict.PASS)
