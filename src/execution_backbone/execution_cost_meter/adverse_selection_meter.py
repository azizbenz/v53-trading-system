"""
Build-3 / execution_cost_meter / adverse_selection_meter
Measure post-fill unfavorable movement (adverse selection).

AS_i(Δ) = sign(side) · (Mid_{t+Δ} - P_exec) / P_exec
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator


class AdverseSelectionDelayPolicy(BaseModel, frozen=True):
    """Typed delay policy for post-fill adverse selection measurement."""

    policy_id: str = Field(..., min_length=1)
    default_delay_s: float = Field(..., gt=0.0)
    pair_delay_overrides_s: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_delays(self) -> "AdverseSelectionDelayPolicy":
        if not math.isfinite(self.default_delay_s):
            raise ValueError("default_delay_s must be finite")
        for pair, delay_s in self.pair_delay_overrides_s.items():
            if not pair:
                raise ValueError("pair_delay_overrides_s keys must be non-empty")
            if not math.isfinite(delay_s) or delay_s <= 0.0:
                raise ValueError("pair_delay_overrides_s values must be finite and > 0")
        return self

    def resolve_for_pair(self, pair: str) -> float:
        return self.pair_delay_overrides_s.get(pair, self.default_delay_s)


CANONICAL_ADVERSE_SELECTION_DELAY_POLICY = AdverseSelectionDelayPolicy(
    policy_id="adverse_selection_delay_policy.v1",
    default_delay_s=5.0,
)


class AdverseSelectionMeasurement(BaseModel, frozen=True):
    """Adverse selection measurement for a single trade."""

    order_id: str
    pair: str
    side: str
    exec_price: float
    mid_after: float
    delay_s: float  # Δ — time after fill
    adverse_selection: float  # AS_i(Δ)


def resolve_adverse_selection_delay_s(
    *,
    pair: str,
    event_delay_s: float | None,
    policy: AdverseSelectionDelayPolicy,
) -> float:
    """Resolve the measurement delay from explicit event data or typed policy."""
    if event_delay_s is not None:
        if not math.isfinite(event_delay_s) or event_delay_s <= 0.0:
            raise ValueError("event_delay_s must be finite and > 0 when provided")
        return event_delay_s
    return policy.resolve_for_pair(pair)


def compute_adverse_selection(
    order_id: str,
    pair: str,
    side: str,
    exec_price: float,
    mid_after: float,
    delay_s: float,
) -> AdverseSelectionMeasurement:
    """Compute adverse selection.

    AS_i(Δ) = sign(side) · (Mid_{t+Δ} - P_exec) / P_exec

    sign(buy) = +1, sign(sell) = -1.

    For a buy (sign=+1):
      - Mid rises after fill  → AS > 0 (favorable: bought before price went up)
      - Mid drops after fill   → AS < 0 (unfavorable: bought before price went down)
    For a sell (sign=-1):
      - Mid rises after fill  → AS < 0 (unfavorable: sold before price went up)
      - Mid drops after fill   → AS > 0 (favorable: sold before price went down)

    Positive AS = favorable post-fill movement. Negative AS = adverse movement.
    """
    if exec_price <= 0:
        as_value = 0.0
    else:
        sign = 1.0 if side.lower() == "buy" else -1.0
        as_value = sign * (mid_after - exec_price) / exec_price

    return AdverseSelectionMeasurement(
        order_id=order_id,
        pair=pair,
        side=side,
        exec_price=exec_price,
        mid_after=mid_after,
        delay_s=delay_s,
        adverse_selection=as_value,
    )
