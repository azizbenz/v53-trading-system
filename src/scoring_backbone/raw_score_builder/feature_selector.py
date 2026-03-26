"""
Build-5 / raw_score_builder / feature_selector
Select authorised features for a given engine.

No unauthorised feature may enter the score.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureConfig(BaseModel, frozen=True):
    """Defines which features an engine is allowed to use."""

    engine_id: str
    allowed_features: frozenset[str] = frozenset()


class FeatureSelection(BaseModel, frozen=True):
    """Result of feature selection."""

    engine_id: str
    selected: dict[str, float] = Field(default_factory=dict)
    rejected: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


def select_features(
    engine_id: str,
    raw_features: dict[str, float],
    allowed_features: frozenset[str],
) -> FeatureSelection:
    """Select only authorised features, track rejected and missing."""
    selected: dict[str, float] = {}
    rejected: list[str] = []

    for name, value in raw_features.items():
        if name in allowed_features:
            selected[name] = value
        else:
            rejected.append(name)

    missing = [f for f in allowed_features if f not in raw_features]

    return FeatureSelection(
        engine_id=engine_id,
        selected=selected,
        rejected=tuple(sorted(rejected)),
        missing=tuple(sorted(missing)),
    )
