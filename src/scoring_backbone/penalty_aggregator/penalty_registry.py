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


def validate_penalty_ids(
    penalty_ids: tuple[str, ...],
    registry: PenaltyRegistry,
) -> tuple[str, ...]:
    """Validate that penalty ids are authorised and not duplicated."""
    seen: set[str] = set()
    duplicates: list[str] = []
    unauthorised: list[str] = []

    for penalty_id in penalty_ids:
        if penalty_id in seen and penalty_id not in duplicates:
            duplicates.append(penalty_id)
        seen.add(penalty_id)

        if not registry.is_authorised(penalty_id) and penalty_id not in unauthorised:
            unauthorised.append(penalty_id)

    problems: list[str] = []
    if unauthorised:
        problems.append(
            "unauthorised penalties: " + ", ".join(sorted(unauthorised))
        )
    if duplicates:
        problems.append(
            "duplicate penalties: " + ", ".join(sorted(duplicates))
        )

    if problems:
        raise ValueError("; ".join(problems))

    return penalty_ids
