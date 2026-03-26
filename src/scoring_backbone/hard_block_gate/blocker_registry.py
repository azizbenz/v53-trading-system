"""
Build-5 / hard_block_gate / blocker_registry
List authorised hard blockers. Small, fatal, explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class BlockerID(StrEnum):
    """Canonical hard blocker identifiers — kept small."""

    STALE_HARD = "stale_hard"
    PAIR_SUSPENDED = "pair_suspended"
    RISK_BUDGET_EXCEEDED = "risk_budget_exceeded"
    RECONCILIATION_CRITICAL = "reconciliation_critical"
    INFRA_DOWN = "infra_down"


class BlockerDefinition(BaseModel, frozen=True):
    blocker_id: BlockerID
    description: str
    severity: str = "fatal"


# Default registry — only fatal conditions
DEFAULT_BLOCKERS: tuple[BlockerDefinition, ...] = (
    BlockerDefinition(
        blocker_id=BlockerID.STALE_HARD,
        description="Data is hard-stale beyond recovery threshold",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.PAIR_SUSPENDED,
        description="Pair health is in SUSPENDED state",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.RISK_BUDGET_EXCEEDED,
        description="Risk budget (exposure/loss/beta/cluster) is fully exhausted",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.RECONCILIATION_CRITICAL,
        description="Reconciliation divergence is at CRITICAL level",
    ),
    BlockerDefinition(
        blocker_id=BlockerID.INFRA_DOWN,
        description="Infrastructure subsystem is down",
    ),
)


class BlockerRegistry:
    """Registry of authorised hard blockers."""

    def __init__(self, blockers: tuple[BlockerDefinition, ...] = DEFAULT_BLOCKERS, version: str = "1.0") -> None:
        self._blockers = {b.blocker_id: b for b in blockers}
        self._version = version

    @property
    def version(self) -> str:
        return self._version

    def get(self, blocker_id: BlockerID) -> BlockerDefinition | None:
        return self._blockers.get(blocker_id)

    def is_registered(self, blocker_id: BlockerID) -> bool:
        return blocker_id in self._blockers

    def get_all(self) -> tuple[BlockerDefinition, ...]:
        return tuple(self._blockers.values())

    @property
    def count(self) -> int:
        return len(self._blockers)
