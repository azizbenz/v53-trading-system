"""
Build-3 / reconciliation_layer / fill_reconciler
Compare local fills vs real exchange fills.

Invariant: every fill divergence is detected and classified.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FillReconciliationPolicy(BaseModel, frozen=True):
    """Typed tolerance policy for fill reconciliation."""

    policy_id: str = Field(..., min_length=1)
    quantity_tolerance: float = Field(..., ge=0.0)


CANONICAL_FILL_RECONCILIATION_POLICY = FillReconciliationPolicy(
    policy_id="fill_reconciliation.tolerance.v1",
    quantity_tolerance=1e-8,
)


class FillDivergence(BaseModel, frozen=True):
    """A divergence between local and remote fill data."""

    order_id: str
    local_filled_qty: float
    remote_filled_qty: float
    qty_diff: float
    detail: str = ""


class FillReconciliationResult(BaseModel, frozen=True):
    """Result of fill reconciliation."""

    policy_id: str = Field(..., min_length=1)
    aligned: bool
    total_compared: int
    divergences: tuple[FillDivergence, ...] = ()
    max_qty_diff: float = 0.0


def reconcile_fills(
    local_fills: dict[str, float],  # order_id -> filled_qty
    remote_fills: dict[str, float],  # order_id -> filled_qty
    policy: FillReconciliationPolicy = CANONICAL_FILL_RECONCILIATION_POLICY,
) -> FillReconciliationResult:
    """Compare local vs remote fill quantities."""
    divergences: list[FillDivergence] = []
    all_ids = set(local_fills.keys()) | set(remote_fills.keys())
    max_diff = 0.0

    for oid in all_ids:
        local_qty = local_fills.get(oid, 0.0)
        remote_qty = remote_fills.get(oid, 0.0)
        diff = abs(local_qty - remote_qty)

        if diff > policy.quantity_tolerance:
            divergences.append(FillDivergence(
                order_id=oid,
                local_filled_qty=local_qty,
                remote_filled_qty=remote_qty,
                qty_diff=diff,
                detail=f"Order {oid}: local={local_qty}, remote={remote_qty}, diff={diff}",
            ))
            max_diff = max(max_diff, diff)

    return FillReconciliationResult(
        policy_id=policy.policy_id,
        aligned=len(divergences) == 0,
        total_compared=len(all_ids),
        divergences=tuple(divergences),
        max_qty_diff=max_diff,
    )
