"""Enums for Build-14 complete enablers."""

from __future__ import annotations

from enum import StrEnum


class Build14InfluenceMode(StrEnum):
    """Governed introduction modes for Build-14 enrichments."""

    READ_ONLY = "read_only"
    LIMITED_INFLUENCE = "limited_influence"


class Build14SignalFamily(StrEnum):
    """Families of Build-14 enablers tracked by the addendum."""

    AI_EDGE = "ai_edge"
    MICROSTRUCTURE = "microstructure"
    REGIME = "regime"


__all__ = [
    "Build14InfluenceMode",
    "Build14SignalFamily",
]
