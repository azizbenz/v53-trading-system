"""
Build-3 / execution_cost_meter / elw_meter
Measure Effective Liquidity Width (implicit cost).

ELW_i = |P_exec - Mid| / Mid
c_impl ≈ ELW_entry + ELW_exit
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ELWMeasurement(BaseModel, frozen=True):
    """Effective Liquidity Width for a single fill."""

    order_id: str
    pair: str
    exec_price: float
    mid_price: float
    elw: float  # |P_exec - Mid| / Mid
    side: str


class ImplicitCost(BaseModel, frozen=True):
    """Implicit round-trip cost estimate."""

    pair: str
    elw_entry: float
    elw_exit: float | None = None  # None if exit not yet measured
    implicit_round_trip: float  # ELW_entry + ELW_exit (0 if exit unknown)


def compute_elw(
    order_id: str,
    pair: str,
    exec_price: float,
    mid_price: float,
    side: str,
) -> ELWMeasurement:
    """Compute Effective Liquidity Width.

    ELW_i = |P_exec - Mid| / Mid
    """
    if mid_price <= 0:
        elw = 0.0
    else:
        elw = abs(exec_price - mid_price) / mid_price

    return ELWMeasurement(
        order_id=order_id,
        pair=pair,
        exec_price=exec_price,
        mid_price=mid_price,
        elw=elw,
        side=side,
    )


def compute_implicit_round_trip(
    pair: str,
    elw_entry: float,
    elw_exit: float | None = None,
) -> ImplicitCost:
    """Compute implicit round-trip cost.

    c_impl ≈ ELW_entry + ELW_exit
    """
    rt = elw_entry + (elw_exit or 0.0)
    return ImplicitCost(
        pair=pair,
        elw_entry=elw_entry,
        elw_exit=elw_exit,
        implicit_round_trip=rt,
    )
