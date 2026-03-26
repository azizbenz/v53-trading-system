"""
Build-4 / btc_factor_guard / beta_cap_guard
Refuse trade if BTC beta budget would be exceeded.

|β_port| ≤ B_max
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BetaCapVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class BetaCapResult(BaseModel, frozen=True):
    pair: str
    current_beta: float
    projected_beta: float
    beta_cap: float
    verdict: BetaCapVerdict
    reason: str = ""


def evaluate_beta_cap(
    pair: str,
    current_beta: float,
    projected_beta: float,
    beta_cap: float,
) -> BetaCapResult:
    """Evaluate whether adding a trade stays within BTC beta budget.

    |β_port_proj| ≤ B_max
    """
    if abs(projected_beta) <= beta_cap:
        return BetaCapResult(
            pair=pair,
            current_beta=current_beta,
            projected_beta=projected_beta,
            beta_cap=beta_cap,
            verdict=BetaCapVerdict.ACCEPTED,
        )

    return BetaCapResult(
        pair=pair,
        current_beta=current_beta,
        projected_beta=projected_beta,
        beta_cap=beta_cap,
        verdict=BetaCapVerdict.REJECTED,
        reason=f"{pair}: |β_port_proj|={abs(projected_beta):.4f} > B_max={beta_cap:.4f}",
    )
