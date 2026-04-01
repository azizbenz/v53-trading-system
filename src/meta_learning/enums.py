"""Canonical enums for the governed Build-9X meta-learning layer."""

from __future__ import annotations

from enum import StrEnum


class LearningLifecycleState(StrEnum):
    """Lifecycle states for governed learning artifacts."""

    CAPTURED = "captured"
    DIAGNOSED = "diagnosed"
    HYPOTHESIS_REGISTERED = "hypothesis_registered"
    CHECKLIST_READY = "checklist_ready"
    CANDIDATE_READY = "candidate_ready"
    EXPORTED = "exported"


class DiagnosticStatus(StrEnum):
    """Canonical diagnostic review states for Build-9X."""

    OPEN = "open"
    ESCALATED = "escalated"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class DiagnosticSeverity(StrEnum):
    """Severity used by diagnostics and review exports."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HypothesisStatus(StrEnum):
    """Lifecycle state for a governed learning hypothesis."""

    OPEN = "open"
    QUEUED_FOR_LOCAL_REPLAY = "queued_for_local_replay"
    VALIDATED_IN_REPLAY = "validated_in_replay"
    REJECTED = "rejected"


class EvidenceStrength(StrEnum):
    """Statistical support level attached to a governed hypothesis."""

    ANECDOTAL = "anecdotal"
    WEAK_PATTERN = "weak_pattern"
    REPEATABLE_PATTERN = "repeatable_pattern"
    ROBUST_CANDIDATE = "robust_candidate"


class LearningCaptureMode(StrEnum):
    """Capture mode used when Build-9X capacity degrades under pressure."""

    FULL_CAPTURE = "full_capture"
    CAPTURE_MINIMALE = "capture_minimale"


class LearningBacklogState(StrEnum):
    """Queue state used to distinguish normal, alert, and protection zones."""

    NORMAL = "normal"
    ALERT = "alert"
    PROTECTION = "protection"


class HypothesisGovernanceStage(StrEnum):
    """Canonical governance states for hypotheses."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    REPLAY_APPROVED = "replay_approved"
    SHADOW_CANDIDATE = "shadow_candidate"
    REPLAY_REJECTED = "replay_rejected"
    SHADOW_REJECTED = "shadow_rejected"
    CLOSED_NO_ACTION = "closed_no_action"
    DEPLOYED_VERSIONED = "deployed_versioned"


class CandidateGovernanceStage(StrEnum):
    """Canonical governance states for candidates."""

    PREPARED = "prepared"
    TESTS_PENDING = "tests_pending"
    READY_FOR_REPLAY = "ready_for_replay"
    REPLAY_RUNNING = "replay_running"
    REPLAY_FAILED = "replay_failed"
    REPLAY_PASSED = "replay_passed"
    READY_FOR_SHADOW_REVIEW = "ready_for_shadow_review"
    RETIRED = "retired"


class CandidateKind(StrEnum):
    """Kinds of improvement candidates produced by Build-9X."""

    OBSERVABILITY_ONLY = "observability_only"
    PARAMETER_TUNING = "parameter_tuning"
    GUARD_TIGHTENING = "guard_tightening"
    BUILD14_ENABLER = "build14_enabler"


__all__ = [
    "LearningLifecycleState",
    "DiagnosticStatus",
    "DiagnosticSeverity",
    "HypothesisStatus",
    "EvidenceStrength",
    "LearningCaptureMode",
    "LearningBacklogState",
    "HypothesisGovernanceStage",
    "CandidateGovernanceStage",
    "CandidateKind",
]
