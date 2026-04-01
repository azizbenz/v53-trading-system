"""
7.5.3 - Queue Manager: per-consumer queues with backlog and saturation metrics.

Invariant: backlog visible per consumer. Bounded queues with explicit drops.
"""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel


class QueueStats(BaseModel, frozen=True):
    """Statistics for a single consumer queue."""

    consumer_id: str
    depth: int = 0
    max_depth: int = 0
    high_water_mark: int = 0
    capacity: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_dropped: int = 0
    utilization: float = 0.0
    drop_rate: float = 0.0


class QueueManager:
    """Manage per-consumer bounded queues."""

    def __init__(self, default_max_size: int = 10000) -> None:
        self._default_max_size = default_max_size
        self._queues: dict[str, deque[object]] = {}
        self._max_sizes: dict[str, int] = {}
        self._high_water_marks: dict[str, int] = {}
        self._enqueued: dict[str, int] = {}
        self._dequeued: dict[str, int] = {}
        self._dropped: dict[str, int] = {}

    def create_queue(self, consumer_id: str, max_size: int | None = None) -> None:
        """Create a bounded queue for a consumer."""
        size = max_size if max_size is not None else self._default_max_size
        self._queues[consumer_id] = deque()
        self._max_sizes[consumer_id] = size
        self._high_water_marks[consumer_id] = 0
        self._enqueued[consumer_id] = 0
        self._dequeued[consumer_id] = 0
        self._dropped[consumer_id] = 0

    def enqueue(self, consumer_id: str, item: object, drop_oldest: bool = True) -> bool:
        """Add item to consumer queue.

        GEM-05: drop_oldest=True (default) evicts oldest when full.
        Returns False only if the queue is unknown or policy forbids insertion.
        """
        if consumer_id not in self._queues:
            return False
        q = self._queues[consumer_id]
        if len(q) >= self._max_sizes[consumer_id]:
            if drop_oldest:
                q.popleft()
                self._dropped[consumer_id] += 1
            else:
                self._dropped[consumer_id] += 1
                return False
        q.append(item)
        self._enqueued[consumer_id] += 1
        self._high_water_marks[consumer_id] = max(
            self._high_water_marks.get(consumer_id, 0),
            len(q),
        )
        return True

    def dequeue(self, consumer_id: str, max_count: int | None = None) -> tuple[object, ...]:
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
        capacity = self._max_sizes[consumer_id]
        total_enqueued = self._enqueued.get(consumer_id, 0)
        total_dropped = self._dropped.get(consumer_id, 0)
        total_seen = total_enqueued + total_dropped
        high_water_mark = self._high_water_marks.get(consumer_id, 0)
        return QueueStats(
            consumer_id=consumer_id,
            depth=depth,
            max_depth=high_water_mark,
            high_water_mark=high_water_mark,
            capacity=capacity,
            total_enqueued=total_enqueued,
            total_dequeued=self._dequeued.get(consumer_id, 0),
            total_dropped=total_dropped,
            utilization=depth / capacity if capacity > 0 else 1.0,
            drop_rate=total_dropped / total_seen if total_seen > 0 else 0.0,
        )

    def all_stats(self) -> tuple[QueueStats, ...]:
        stats: list[QueueStats] = []
        for consumer_id in self._queues:
            stat = self.get_stats(consumer_id)
            if stat is not None:
                stats.append(stat)
        return tuple(stats)

    def is_saturated(self, consumer_id: str, threshold: float = 0.9) -> bool:
        stats = self.get_stats(consumer_id)
        if stats is None:
            return False
        return stats.utilization >= threshold

    def saturated_queues(self, threshold: float = 0.9) -> tuple[str, ...]:
        return tuple(
            cid for cid in self._queues
            if self.is_saturated(cid, threshold)
        )

    def remove_queue(self, consumer_id: str) -> bool:
        if consumer_id not in self._queues:
            return False
        del self._queues[consumer_id]
        del self._max_sizes[consumer_id]
        del self._high_water_marks[consumer_id]
        del self._enqueued[consumer_id]
        del self._dequeued[consumer_id]
        del self._dropped[consumer_id]
        return True
