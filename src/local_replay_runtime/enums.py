"""Enums for the LOCAL_REPLAY scaffold."""

from __future__ import annotations

from enum import StrEnum


class ReplayArtifactKind(StrEnum):
    """Kinds of replay artifacts supported by the unified plan."""

    DIAGNOSTIC_BUNDLE = "diagnostic_bundle"
    HYPOTHESIS_BUNDLE = "hypothesis_bundle"
    IMPROVEMENT_CANDIDATE = "improvement_candidate"
    REVIEW_PACKET = "review_packet"


class ReplayLifecycleState(StrEnum):
    """Lifecycle of an exported replay bundle."""

    DRAFT = "draft"
    VALIDATED = "validated"
    EXPORTED = "exported"
    IMPORTED = "imported"


__all__ = [
    "ReplayArtifactKind",
    "ReplayLifecycleState",
]
