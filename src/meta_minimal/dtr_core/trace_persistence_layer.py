"""
Build-9 / dtr_core / trace_persistence_layer
Persist DTRs without silent loss. Track persistence failures.

DTRCoverage = N_dtr / N_opportunities
DTRLossRate = N_drops / N_attempted

GEM-19: disk flush via atomic write (write-tmp-then-rename).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class PersistenceStats(BaseModel, frozen=True):
    """Statistics on DTR persistence."""

    total_attempted: int = 0
    total_persisted: int = 0
    total_dropped: int = 0
    loss_rate: float = 0.0  # N_drops / N_attempted


class DTRStore:
    """In-memory DTR persistence with loss tracking and disk flush.

    GEM-19: flush_to_disk() writes all records atomically to JSON.
    """

    def __init__(self, flush_dir: Path | None = None) -> None:
        self._records: list[DTRRecord] = []
        self._attempted: int = 0
        self._dropped: int = 0
        self._flush_dir = flush_dir
        self._last_flush_index: int = 0

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

    def flush_to_disk(self, path: Path | None = None) -> int:
        """GEM-19: atomically flush all records to JSON on disk.

        Returns the number of new records flushed since last call.
        """
        target = path or (self._flush_dir / "dtr_records.json" if self._flush_dir else None)
        if target is None:
            return 0

        new_records = self._records[self._last_flush_index:]
        if not new_records:
            return 0

        # Serialize all records (not just new — full snapshot for atomicity)
        data = [r.model_dump(mode="json") for r in self._records]
        atomic_write_json(target, data)

        flushed = len(new_records)
        self._last_flush_index = len(self._records)
        return flushed

    @property
    def pending_flush_count(self) -> int:
        """Number of records not yet flushed to disk."""
        return len(self._records) - self._last_flush_index
