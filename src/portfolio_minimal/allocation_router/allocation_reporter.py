"""
Build-8 / allocation_router / allocation_reporter
Produce the final allocation report for all selected opportunities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from portfolio_minimal.allocation_router.phantom_trade_guard import PhantomVerdict


class AllocationEntry(BaseModel, frozen=True):
    """One final allocation decision."""

    pair: str
    engine_id: str
    base_size: float
    modulated_size: float
    final_size: float
    tier: str
    ranking_score: float
    is_phantom: bool = False
    cap_reason: str = ""


class AllocationReport(BaseModel, frozen=True):
    """Full allocation report for the cycle."""

    allocations: tuple[AllocationEntry, ...] = ()
    phantoms: tuple[AllocationEntry, ...] = ()
    total_allocated: float = 0.0
    total_phantom: float = 0.0
    count_allocated: int = 0
    count_phantom: int = 0


def build_report(
    entries: tuple[AllocationEntry, ...],
) -> AllocationReport:
    """Build the final allocation report, separating viable from phantom trades."""
    viable = tuple(e for e in entries if not e.is_phantom)
    phantoms = tuple(e for e in entries if e.is_phantom)

    return AllocationReport(
        allocations=viable,
        phantoms=phantoms,
        total_allocated=sum(e.final_size for e in viable),
        total_phantom=sum(e.final_size for e in phantoms),
        count_allocated=len(viable),
        count_phantom=len(phantoms),
    )
