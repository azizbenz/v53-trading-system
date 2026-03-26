"""
Build-8 / allocation_router / portfolio_cap_applier
Apply global and residual caps to modulated sizes.

Caps applied (tightest wins):
1. Position cap (max single position)
2. Remaining gross capacity
3. Remaining cluster capacity
4. Remaining loss budget  (proportional reduction)
5. Remaining beta budget  (proportional reduction)
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
    remaining_loss_capacity: float = float("inf"),
    remaining_beta_capacity: float = float("inf"),
    estimated_loss_at_candidate_size: float = 0.0,
    beta_impact_at_candidate_size: float = 0.0,
    candidate_size: float = 0.0,
) -> CapApplicationResult:
    """Apply the tightest cap to the modulated size.

    Caps checked (tightest wins):
    1. Position cap (max single position)
    2. Remaining gross capacity
    3. Remaining cluster capacity
    4. Loss budget: max_size = remaining_loss / (loss / candidate_size)
    5. Beta budget: max_size = remaining_beta / (|beta| / candidate_size)
    """
    final = modulated_size
    reasons: list[str] = []

    # ── 1. Position cap ──
    if final > position_cap:
        final = position_cap
        reasons.append(f"position_cap={position_cap:.2f}")

    # ── 2. Gross cap ──
    if final > remaining_gross_capacity:
        final = remaining_gross_capacity
        reasons.append(f"gross_remaining={remaining_gross_capacity:.2f}")

    # ── 3. Cluster cap ──
    if final > remaining_cluster_capacity:
        final = remaining_cluster_capacity
        reasons.append(f"cluster_remaining={remaining_cluster_capacity:.2f}")

    # ── 4. Loss budget cap (proportional) ──
    if (
        candidate_size > 0.0
        and estimated_loss_at_candidate_size > 0.0
        and remaining_loss_capacity < float("inf")
    ):
        loss_per_unit = estimated_loss_at_candidate_size / candidate_size
        max_size_for_loss = remaining_loss_capacity / loss_per_unit
        if final > max_size_for_loss:
            final = max_size_for_loss
            reasons.append(f"loss_budget={remaining_loss_capacity:.4f}")

    # ── 5. Beta budget cap (proportional) ──
    if (
        candidate_size > 0.0
        and abs(beta_impact_at_candidate_size) > 0.0
        and remaining_beta_capacity < float("inf")
    ):
        beta_per_unit = abs(beta_impact_at_candidate_size) / candidate_size
        max_size_for_beta = remaining_beta_capacity / beta_per_unit
        if final > max_size_for_beta:
            final = max_size_for_beta
            reasons.append(f"beta_budget={remaining_beta_capacity:.4f}")

    was_capped = final < modulated_size

    return CapApplicationResult(
        pair=pair,
        pre_cap_size=modulated_size,
        final_size=max(final, 0.0),
        was_capped=was_capped,
        cap_reason=", ".join(reasons) if reasons else "",
    )
