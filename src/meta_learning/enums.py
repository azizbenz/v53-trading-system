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


class CandidateKind(StrEnum):
    """Kinds of improvement candidates produced by Build-9X."""

    OBSERVABILITY_ONLY = "observability_only"
    PARAMETER_TUNING = "parameter_tuning"
    GUARD_TIGHTENING = "guard_tightening"
    BUILD14_READ_ONLY = "build14_read_only"


__all__ = [
    "LearningLifecycleState",
    "DiagnosticSeverity",
    "HypothesisStatus",
    "CandidateKind",
]
