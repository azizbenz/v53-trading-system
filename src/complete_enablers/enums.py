"""Enums for Build-14 complete enablers."""

from __future__ import annotations

from enum import StrEnum


class Build14InfluenceMode(StrEnum):
    """Governed introduction modes for Build-14 enrichments."""

    READ_ONLY = "read_only"
    LIMITED_INFLUENCE = "limited_influence"


class Build14InfluenceAction(StrEnum):
    """Allowed limited-influence actions for Build-14 phase 2."""

    OBSERVE = "observe"
    DOWNGRADE_CONFIDENCE = "downgrade_confidence"
    REVIEW_ONLY = "review_only"
    SOFT_VETO = "soft_veto"


class Build14Severity(StrEnum):
    """Normalized severity scale for Build-14 observations and influence."""

    NOMINAL = "nominal"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class Build14SignalFamily(StrEnum):
    """Families of Build-14 enablers tracked by the addendum."""

    AI_EDGE = "ai_edge"
    MICROSTRUCTURE = "microstructure"
    REGIME = "regime"


__all__ = [
    "Build14InfluenceMode",
    "Build14InfluenceAction",
    "Build14Severity",
    "Build14SignalFamily",
]
