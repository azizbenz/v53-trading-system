"""
Build-5 / raw_score_builder / weight_registry
Provide versioned weights for raw score computation.

Every weight change must be versioned.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeightSet(BaseModel, frozen=True):
    """A versioned set of scoring weights for an engine."""

    engine_id: str
    version: str
    weights: dict[str, float] = Field(default_factory=dict)


class WeightRegistry:
    """Registry of versioned weight sets per engine."""

    def __init__(self) -> None:
        self._registry: dict[str, WeightSet] = {}
        self._history: list[WeightSet] = []

    def register(self, weight_set: WeightSet) -> None:
        self._registry[weight_set.engine_id] = weight_set
        self._history.append(weight_set)

    def get_weights(self, engine_id: str) -> WeightSet | None:
        return self._registry.get(engine_id)

    def get_version(self, engine_id: str) -> str:
        ws = self._registry.get(engine_id)
        return ws.version if ws is not None else ""

    def get_history(self) -> tuple[WeightSet, ...]:
        return tuple(self._history)

    @property
    def engine_count(self) -> int:
        return len(self._registry)
