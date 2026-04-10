"""Enums for the minimal real Build-11/12/13 protocol runtimes."""

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


class ShadowComponentKind(StrEnum):
    """Canonical component families evaluated during the 30-day Shadow."""

    ENGINE = "engine"
    BUILD14_ENABLER = "build14_enabler"


class ShadowComponentHardState(StrEnum):
    """Canonical Shadow entry hard state for Build-11 components."""

    SHADOW_ENABLED = "shadow_enabled"


class ShadowComponentVerdict(StrEnum):
    """Canonical per-component verdict rendered at the end of Shadow."""

    SHADOW_VALIDATED = "shadow_validated"
    DORMANT = "dormant"


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


class LiveLightRunState(StrEnum):
    """Lifecycle state of a governed Build-13 Live-Light run."""

    PREPARED = "prepared"
    READY_TO_EXECUTE_SMALL = "ready_to_execute_small"
    BLOCKED = "blocked"


class LiveLightVerdict(StrEnum):
    """Minimal gating verdict for Build-13 Live-Light."""

    ALLOWED_TO_EXECUTE_SMALL = "allowed_to_execute_small"
    DRY_RUN_ONLY = "dry_run_only"
    BLOCKED = "blocked"


LiveRunState = LiveLightRunState
LiveVerdict = LiveLightVerdict


__all__ = [
    "ShadowRunState",
    "ShadowVerdict",
    "ShadowComponentKind",
    "ShadowComponentHardState",
    "ShadowComponentVerdict",
    "ShadowComparisonStatus",
    "ShadowDivergenceSeverity",
    "MicroLiveRunState",
    "MicroLiveVerdict",
    "LiveRunState",
    "LiveVerdict",
    "LiveLightRunState",
    "LiveLightVerdict",
]
