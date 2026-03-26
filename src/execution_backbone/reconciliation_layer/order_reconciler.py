"""
Build-3 / reconciliation_layer / order_reconciler
Compare local orders vs real exchange orders.

Invariant: no critical divergence should be silent.
OrderDiff = N_local_open - N_remote_open
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OrderDivergenceType(StrEnum):
    LOCAL_ONLY = "local_only"  # order exists locally but not on exchange
    REMOTE_ONLY = "remote_only"  # order exists on exchange but not locally
    STATE_MISMATCH = "state_mismatch"  # different states
    QUANTITY_MISMATCH = "quantity_mismatch"


class OrderDivergence(BaseModel, frozen=True):
    """A divergence between local and remote order state."""

    order_id: str
    divergence_type: OrderDivergenceType
    local_state: str = ""
    remote_state: str = ""
    detail: str = ""


class OrderReconciliationResult(BaseModel, frozen=True):
    """Result of order reconciliation."""

    aligned: bool
    local_open_count: int
    remote_open_count: int
    order_diff: int  # local - remote
    divergences: tuple[OrderDivergence, ...] = ()


def reconcile_orders(
    local_orders: dict[str, str],  # order_id -> state
    remote_orders: dict[str, str],  # order_id -> state
) -> OrderReconciliationResult:
    """Compare local vs remote order states.

    OrderDiff = N_local_open - N_remote_open
    """
    divergences: list[OrderDivergence] = []

    local_ids = set(local_orders.keys())
    remote_ids = set(remote_orders.keys())

    # Local-only orders (phantom local orders)
    for oid in local_ids - remote_ids:
        divergences.append(OrderDivergence(
            order_id=oid,
            divergence_type=OrderDivergenceType.LOCAL_ONLY,
            local_state=local_orders[oid],
            detail=f"Order {oid} exists locally ({local_orders[oid]}) but not on exchange",
        ))

    # Remote-only orders (unknown orders on exchange)
    for oid in remote_ids - local_ids:
        divergences.append(OrderDivergence(
            order_id=oid,
            divergence_type=OrderDivergenceType.REMOTE_ONLY,
            remote_state=remote_orders[oid],
            detail=f"Order {oid} exists on exchange ({remote_orders[oid]}) but not locally",
        ))

    # State mismatches
    for oid in local_ids & remote_ids:
        if local_orders[oid] != remote_orders[oid]:
            divergences.append(OrderDivergence(
                order_id=oid,
                divergence_type=OrderDivergenceType.STATE_MISMATCH,
                local_state=local_orders[oid],
                remote_state=remote_orders[oid],
                detail=f"Order {oid}: local={local_orders[oid]}, remote={remote_orders[oid]}",
            ))

    return OrderReconciliationResult(
        aligned=len(divergences) == 0,
        local_open_count=len(local_orders),
        remote_open_count=len(remote_orders),
        order_diff=len(local_orders) - len(remote_orders),
        divergences=tuple(divergences),
    )
