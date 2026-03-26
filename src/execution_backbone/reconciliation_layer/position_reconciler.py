"""
Build-3 / reconciliation_layer / position_reconciler
Compare local positions/inventories vs real exchange state.

PosDiff = |Pos_local - Pos_remote|
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PositionDivergence(BaseModel, frozen=True):
    """A divergence between local and remote position."""

    asset: str
    local_position: float
    remote_position: float
    abs_diff: float
    relative_diff: float  # |diff| / |remote| if remote != 0


class PositionReconciliationResult(BaseModel, frozen=True):
    """Result of position reconciliation."""

    aligned: bool
    total_assets_compared: int
    divergences: tuple[PositionDivergence, ...] = ()
    max_abs_diff: float = 0.0


def reconcile_positions(
    local_positions: dict[str, float],  # asset -> quantity
    remote_positions: dict[str, float],  # asset -> quantity
    tolerance: float = 1e-8,
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

        if abs_diff > tolerance:
            rel_diff = abs_diff / abs(remote) if abs(remote) > 0 else float("inf")
            divergences.append(PositionDivergence(
                asset=asset,
                local_position=local,
                remote_position=remote,
                abs_diff=abs_diff,
                relative_diff=rel_diff,
            ))
            max_diff = max(max_diff, abs_diff)

    return PositionReconciliationResult(
        aligned=len(divergences) == 0,
        total_assets_compared=len(all_assets),
        divergences=tuple(divergences),
        max_abs_diff=max_diff,
    )
