"""
Build-9 / dtr_core / trace_persistence_layer
Persist DTRs without silent loss. Track persistence failures.

DTRCoverage = N_dtr / N_opportunities
DTRLossRate = N_drops / N_attempted
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class PersistenceStats(BaseModel, frozen=True):
    """Statistics on DTR persistence."""

    total_attempted: int = 0
    total_persisted: int = 0
    total_dropped: int = 0
    loss_rate: float = 0.0  # N_drops / N_attempted


class DTRStore:
    """In-memory DTR persistence with loss tracking.

    Production would use a database; this provides the contract.
    """

    def __init__(self) -> None:
        self._records: list[DTRRecord] = []
        self._attempted: int = 0
        self._dropped: int = 0

    def persist(self, record: DTRRecord) -> bool:
        """Persist a DTR. Returns True on success, False on failure.

        Never silently drops — failures are counted.
        """
        self._attempted += 1
        try:
            self._records.append(record)
            return True
        except Exception:
            self._dropped += 1
            return False

    def persist_batch(self, records: tuple[DTRRecord, ...]) -> int:
        """Persist multiple DTRs. Returns count of successful persists."""
        success = 0
        for r in records:
            if self.persist(r):
                success += 1
        return success

    def get_all(self) -> tuple[DTRRecord, ...]:
        """Return all persisted DTRs."""
        return tuple(self._records)

    def get_by_pair(self, pair: str) -> tuple[DTRRecord, ...]:
        """Return DTRs for a specific pair."""
        return tuple(r for r in self._records if r.pair == pair)

    def get_by_engine(self, engine_id: str) -> tuple[DTRRecord, ...]:
        """Return DTRs for a specific engine."""
        return tuple(r for r in self._records if r.engine_id == engine_id)

    def get_by_state(self, state: str) -> tuple[DTRRecord, ...]:
        """Return DTRs with a specific decision state."""
        return tuple(r for r in self._records if r.decision_state == state)

    def get_stats(self) -> PersistenceStats:
        """Return persistence statistics."""
        persisted = self._attempted - self._dropped
        loss_rate = self._dropped / self._attempted if self._attempted > 0 else 0.0
        return PersistenceStats(
            total_attempted=self._attempted,
            total_persisted=persisted,
            total_dropped=self._dropped,
            loss_rate=loss_rate,
        )

    @property
    def size(self) -> int:
        return len(self._records)
