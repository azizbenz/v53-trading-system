"""Enums for the minimal Build-11 Shadow runtime."""

from __future__ import annotations

from enum import StrEnum


class ShadowRunState(StrEnum):
    """Lifecycle state of a governed Shadow run."""

    PREPARED = "prepared"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ShadowVerdict(StrEnum):
    """Minimal gating verdict for Build-11 Shadow."""

    ACCEPTED = "accepted"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class ShadowComparisonStatus(StrEnum):
    """Status of a single baseline-vs-candidate comparison."""

    MATCHING = "matching"
    DIVERGENT = "divergent"
    BLOCKING = "blocking"


class ShadowDivergenceSeverity(StrEnum):
    """Severity used by Shadow comparisons."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


__all__ = [
    "ShadowRunState",
    "ShadowVerdict",
    "ShadowComparisonStatus",
    "ShadowDivergenceSeverity",
]
