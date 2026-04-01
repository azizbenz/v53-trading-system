"""
6.5.5 — Normalization Reporter: track successes, rejections, and anomalies.

Invariant: RejectRate = N_reject / N_raw is always computable.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class NormalizationStats(BaseModel, frozen=True):
    """Aggregate normalization statistics."""

    total_raw: int = 0
    total_normalized: int = 0
    total_rejected: int = 0
    by_event_type: dict[str, int] = Field(default_factory=dict)
    by_rejection_reason: dict[str, int] = Field(default_factory=dict)
    reject_rate: float = 0.0


class NormalizationReporter:
    """Track normalization outcomes for observability."""

    def __init__(self) -> None:
        self._total_raw: int = 0
        self._total_normalized: int = 0
        self._total_rejected: int = 0
        self._by_event_type: dict[str, int] = {}
        self._by_rejection_reason: dict[str, int] = {}

    def record_normalized(self, event_type: str) -> None:
        self._total_raw += 1
        self._total_normalized += 1
        self._by_event_type[event_type] = self._by_event_type.get(event_type, 0) + 1
        logger.info(
            "normalization_event_normalized",
            extra={"event_type": event_type, "total_normalized": self._total_normalized},
        )

    def record_rejected(self, reason: str) -> None:
        self._total_raw += 1
        self._total_rejected += 1
        self._by_rejection_reason[reason] = self._by_rejection_reason.get(reason, 0) + 1
        logger.warning(
            "normalization_event_rejected",
            extra={"reason": reason, "total_rejected": self._total_rejected},
        )

    def get_stats(self) -> NormalizationStats:
        reject_rate = 0.0
        if self._total_raw > 0:
            reject_rate = self._total_rejected / self._total_raw

        return NormalizationStats(
            total_raw=self._total_raw,
            total_normalized=self._total_normalized,
            total_rejected=self._total_rejected,
            by_event_type=dict(self._by_event_type),
            by_rejection_reason=dict(self._by_rejection_reason),
            reject_rate=reject_rate,
        )

    @property
    def reject_rate(self) -> float:
        """RejectRate = N_reject / N_raw."""
        if self._total_raw == 0:
            return 0.0
        return self._total_rejected / self._total_raw

    def reset(self) -> None:
        self._total_raw = 0
        self._total_normalized = 0
        self._total_rejected = 0
        self._by_event_type.clear()
        self._by_rejection_reason.clear()
