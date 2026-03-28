"""Append-only in-memory storage for governed learning reviews."""

from __future__ import annotations

from pydantic import BaseModel

from meta_learning.contracts import LearningMemoryRecord


class LearningMemoryStore(BaseModel, frozen=True):
    """Small immutable store used by tests and offline review flows."""

    records: tuple[LearningMemoryRecord, ...] = ()

    def append(self, record: LearningMemoryRecord) -> "LearningMemoryStore":
        return LearningMemoryStore(records=self.records + (record,))

    def latest(self) -> LearningMemoryRecord | None:
        if not self.records:
            return None
        return self.records[-1]


__all__ = [
    "LearningMemoryStore",
]
