"""
Build-5 / penalty_aggregator / penalty_registry
List and version authorised penalties.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PenaltyType(StrEnum):
    SCORE = "score"
    SIZE = "size"


class PenaltyDefinition(BaseModel, frozen=True):
    """Definition of an authorised penalty."""

    penalty_id: str
    name: str
    penalty_type: PenaltyType
    description: str = ""
    max_value: float = 1.0


class PenaltyRegistry:
    """Registry of authorised penalties, versioned."""

    def __init__(self, version: str = "1.0") -> None:
        self._version = version
        self._penalties: dict[str, PenaltyDefinition] = {}

    @property
    def version(self) -> str:
        return self._version

    def register(self, penalty: PenaltyDefinition) -> None:
        self._penalties[penalty.penalty_id] = penalty

    def get(self, penalty_id: str) -> PenaltyDefinition | None:
        return self._penalties.get(penalty_id)

    def is_authorised(self, penalty_id: str) -> bool:
        return penalty_id in self._penalties

    def get_all(self) -> tuple[PenaltyDefinition, ...]:
        return tuple(self._penalties.values())

    @property
    def count(self) -> int:
        return len(self._penalties)
