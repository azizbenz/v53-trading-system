"""
Build-9 / dtr_core / trace_persistence_layer
Persist DTRs without silent loss. Track persistence failures.

DTRCoverage = N_dtr / N_opportunities
DTRLossRate = N_drops / N_attempted

GEM-19: disk flush via atomic write (write-tmp-then-rename).
"""

from __future__ import annotations

import atexit
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
        self._serialized: list[dict] = []  # BS-62: cache to avoid O(N²) re-serialization
        self._records_by_pair: dict[str, list[DTRRecord]] = {}
        self._records_by_engine: dict[str, list[DTRRecord]] = {}
        self._records_by_state: dict[str, list[DTRRecord]] = {}
        self._attempted: int = 0
        self._dropped: int = 0
        self._flush_dir = flush_dir
        self._last_flush_index: int = 0
        atexit.register(self.flush_to_disk)  # BS-62: flush on clean exit / unhandled exception

    def persist(self, record: DTRRecord) -> bool:
        """Persist a DTR. Returns True on success, False on failure.

        Never silently drops — failures are counted.
        """
        self._attempted += 1
        try:
            serialized = record.model_dump(mode="json")  # BS-62: serialize once at persist time
            self._records.append(record)
            self._serialized.append(serialized)
            # BS-67: maintain append-only secondary indexes to avoid O(N) scans on hot lookups.
            self._records_by_pair.setdefault(record.pair, []).append(record)
            self._records_by_engine.setdefault(record.engine_id, []).append(record)
            self._records_by_state.setdefault(str(record.decision_state), []).append(record)
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
        return tuple(self._records_by_pair.get(pair, ()))

    def get_by_engine(self, engine_id: str) -> tuple[DTRRecord, ...]:
        """Return DTRs for a specific engine."""
        return tuple(self._records_by_engine.get(engine_id, ()))

    def get_by_state(self, state: str) -> tuple[DTRRecord, ...]:
        """Return DTRs with a specific decision state."""
        return tuple(self._records_by_state.get(str(state), ()))

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

        # BS-62: use pre-serialized cache — O(1) per record instead of O(N) re-serialization.
        # Full snapshot written for JSON atomicity (readers expect a valid array).
        atomic_write_json(target, self._serialized)

        flushed = len(new_records)
        self._last_flush_index = len(self._records)
        return flushed

    @property
    def pending_flush_count(self) -> int:
        """Number of records not yet flushed to disk."""
        return len(self._records) - self._last_flush_index
