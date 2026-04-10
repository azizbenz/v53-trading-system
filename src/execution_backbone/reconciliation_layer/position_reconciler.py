"""
Build-3 / reconciliation_layer / position_reconciler
Compare local positions/inventories vs real exchange state.

PosDiff = |Pos_local - Pos_remote|
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PositionReconciliationPolicy(BaseModel, frozen=True):
    """Typed tolerance and scaling policy for position reconciliation."""

    policy_id: str = Field(..., min_length=1)
    absolute_tolerance: float = Field(..., ge=0.0)
    relative_scale_floor: float = Field(..., gt=0.0)


CANONICAL_POSITION_RECONCILIATION_POLICY = PositionReconciliationPolicy(
    policy_id="position_reconciliation.tolerance.v1",
    absolute_tolerance=1e-8,
    relative_scale_floor=1e-8,
)


class PositionDivergence(BaseModel, frozen=True):
    """A divergence between local and remote position."""

    asset: str
    local_position: float
    remote_position: float
    abs_diff: float
    relative_diff: float  # |diff| / |remote| if remote != 0
    relative_scale: float = Field(..., gt=0.0)


class PositionReconciliationResult(BaseModel, frozen=True):
    """Result of position reconciliation."""

    policy_id: str = Field(..., min_length=1)
    aligned: bool
    total_assets_compared: int
    divergences: tuple[PositionDivergence, ...] = ()
    max_abs_diff: float = 0.0


def reconcile_positions(
    local_positions: dict[str, float],  # asset -> quantity
    remote_positions: dict[str, float],  # asset -> quantity
    policy: PositionReconciliationPolicy = CANONICAL_POSITION_RECONCILIATION_POLICY,
) -> PositionReconciliationResult:
    """Compare local vs remote positions.

    PosDiff = |Pos_local - Pos_remote|
    """
    divergences: list[PositionDivergence] = []
    all_assets = set(local_positions.keys()) | set(remote_positions.keys())
    max_diff = 0.0

    for asset in all_assets:
        local = local_positions.get(asset, 0.0)
        remote = remote_positions.get(asset, 0.0)
        abs_diff = abs(local - remote)

        if abs_diff > policy.absolute_tolerance:
            relative_scale = max(abs(remote), policy.relative_scale_floor)
            rel_diff = abs_diff / relative_scale
            divergences.append(PositionDivergence(
                asset=asset,
                local_position=local,
                remote_position=remote,
                abs_diff=abs_diff,
                relative_diff=rel_diff,
                relative_scale=relative_scale,
            ))
            max_diff = max(max_diff, abs_diff)

    return PositionReconciliationResult(
        policy_id=policy.policy_id,
        aligned=len(divergences) == 0,
        total_assets_compared=len(all_assets),
        divergences=tuple(divergences),
        max_abs_diff=max_diff,
    )
