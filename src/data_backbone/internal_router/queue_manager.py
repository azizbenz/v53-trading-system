"""
7.5.3 — Queue Manager: per-consumer queues with backlog and saturation metrics.

Invariant: backlog visible per consumer. Bounded queues with explicit drops.
B_m(t+1) = B_m(t) + A_m(t) - S_m(t)
ρ_m = λ_m / μ_m
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel, Field


class QueueStats(BaseModel, frozen=True):
    """Statistics for a single consumer queue."""

    consumer_id: str
    depth: int = 0
    max_depth: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    utilization: float = 0.0  # depth / max_size


class QueueManager:
    """Manage per-consumer bounded queues."""

    def __init__(self, default_max_size: int = 10000) -> None:
        self._default_max_size = default_max_size
        self._queues: dict[str, deque] = {}
        self._max_sizes: dict[str, int] = {}
        self._enqueued: dict[str, int] = {}
        self._dequeued: dict[str, int] = {}
        self._dropped: dict[str, int] = {}

    def create_queue(self, consumer_id: str, max_size: int | None = None) -> None:
        """Create a bounded queue for a consumer."""
        size = max_size if max_size is not None else self._default_max_size
        self._queues[consumer_id] = deque()
        self._max_sizes[consumer_id] = size
        self._enqueued[consumer_id] = 0
        self._dequeued[consumer_id] = 0
        self._dropped[consumer_id] = 0

    def enqueue(self, consumer_id: str, item: object) -> bool:
        """Add item to consumer queue. Returns False if dropped (queue full)."""
        if consumer_id not in self._queues:
            return False
        q = self._queues[consumer_id]
        if len(q) >= self._max_sizes[consumer_id]:
            self._dropped[consumer_id] += 1
            return False
        q.append(item)
        self._enqueued[consumer_id] += 1
        return True

    def dequeue(self, consumer_id: str, max_count: int | None = None) -> tuple:
        """Consume items from a queue (FIFO)."""
        if consumer_id not in self._queues:
            return ()
        q = self._queues[consumer_id]
        if max_count is None:
            items = tuple(q)
            q.clear()
        else:
            items = tuple(q.popleft() for _ in range(min(max_count, len(q))))
        self._dequeued[consumer_id] += len(items)
        return items

    def get_depth(self, consumer_id: str) -> int:
        q = self._queues.get(consumer_id)
        return len(q) if q is not None else 0

    def get_stats(self, consumer_id: str) -> QueueStats | None:
        if consumer_id not in self._queues:
            return None
        depth = len(self._queues[consumer_id])
        max_size = self._max_sizes[consumer_id]
        return QueueStats(
            consumer_id=consumer_id,
            depth=depth,
            max_depth=max_size,
            total_enqueued=self._enqueued.get(consumer_id, 0),
            total_dequeued=self._dequeued.get(consumer_id, 0),
            total_dropped=self._dropped.get(consumer_id, 0),
            utilization=depth / max_size if max_size > 0 else 1.0,
        )

    def all_stats(self) -> tuple[QueueStats, ...]:
        return tuple(
            self.get_stats(cid) for cid in self._queues if self.get_stats(cid) is not None
        )

    def remove_queue(self, consumer_id: str) -> bool:
        if consumer_id not in self._queues:
            return False
        del self._queues[consumer_id]
        del self._max_sizes[consumer_id]
        return True
