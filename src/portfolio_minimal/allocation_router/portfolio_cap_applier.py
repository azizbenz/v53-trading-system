"""
Build-8 / allocation_router / portfolio_cap_applier
Apply global and residual caps to modulated sizes.

Ensures no single allocation exceeds remaining portfolio capacity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapApplicationResult(BaseModel, frozen=True):
    """Result after applying portfolio-level caps."""

    pair: str
    pre_cap_size: float
    final_size: float
    was_capped: bool = False
    cap_reason: str = ""


def apply_caps(
    pair: str,
    modulated_size: float,
    remaining_gross_capacity: float,
    remaining_cluster_capacity: float,
    position_cap: float = 500.0,
) -> CapApplicationResult:
    """Apply the tightest cap to the modulated size.

    Caps checked (tightest wins):
    1. Position cap (max single position)
    2. Remaining gross capacity
    3. Remaining cluster capacity
    """
    final = modulated_size
    reasons: list[str] = []

    if final > position_cap:
        final = position_cap
        reasons.append(f"position_cap={position_cap:.2f}")

    if final > remaining_gross_capacity:
        final = remaining_gross_capacity
        reasons.append(f"gross_remaining={remaining_gross_capacity:.2f}")

    if final > remaining_cluster_capacity:
        final = remaining_cluster_capacity
        reasons.append(f"cluster_remaining={remaining_cluster_capacity:.2f}")

    was_capped = final < modulated_size

    return CapApplicationResult(
        pair=pair,
        pre_cap_size=modulated_size,
        final_size=max(final, 0.0),
        was_capped=was_capped,
        cap_reason=", ".join(reasons) if reasons else "",
    )
