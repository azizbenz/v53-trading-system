"""Enums for Build-14 complete enablers."""

from __future__ import annotations

from enum import StrEnum


class Build14InfluenceMode(StrEnum):
    """Governed activation modes for Build-14 enrichments."""

    SHADOW_ENABLED = "shadow_enabled"
    READ_ONLY = "read_only"
    LIMITED_INFLUENCE = "limited_influence"


class Build14InfluenceAction(StrEnum):
    """Allowed Build-14 actions across Shadow and post-Shadow live gates."""

    SHADOW_APPLY = "shadow_apply"
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
    RISK = "risk"


class Build14HardState(StrEnum):
    """Canonical hard states for Build-14 enablers."""

    CODED = "coded"
    SHADOW_ENABLED = "shadow_enabled"
    SHADOW_VALIDATED = "shadow_validated"
    DORMANT = "dormant"


__all__ = [
    "Build14InfluenceMode",
    "Build14InfluenceAction",
    "Build14Severity",
    "Build14SignalFamily",
    "Build14HardState",
]
