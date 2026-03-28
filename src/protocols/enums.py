"""Enums for the minimal real Build-11/12 protocol runtimes."""

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


class MicroLiveRunState(StrEnum):
    """Lifecycle state of a governed Build-12 Micro-live run."""

    PREPARED = "prepared"
    READY_TO_PROBE = "ready_to_probe"
    BLOCKED = "blocked"


class MicroLiveVerdict(StrEnum):
    """Minimal gating verdict for Build-12 Micro-live."""

    ALLOWED_TO_PROBE = "allowed_to_probe"
    DRY_RUN_ONLY = "dry_run_only"
    BLOCKED = "blocked"


__all__ = [
    "ShadowRunState",
    "ShadowVerdict",
    "ShadowComparisonStatus",
    "ShadowDivergenceSeverity",
    "MicroLiveRunState",
    "MicroLiveVerdict",
]
