"""
4.5.5 - Raw Message Emitter: emit raw messages with recv_time metadata.

Invariant: every raw message MUST have a recv_time. No silent reordering.
"""

from __future__ import annotations

from collections import deque
import logging

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class RawMessage(BaseModel, frozen=True):
    """A raw WS message with reception metadata."""

    pair: str
    stream_type: str  # "trade" | "depth" | "kline" | "heartbeat"
    payload: dict[str, object]  # raw exchange data opaque to business modules
    recv_time: float  # local reception timestamp (mandatory)
    source: str = ""  # exchange identifier
    sequence: int | None = None  # optional exchange sequence number


class RawMessageReorderingEvent(BaseModel, frozen=True):
    """Visible anomaly when upstream frames arrive out of recv_time order."""

    pair: str
    stream_type: str
    previous_recv_time: float
    recv_time: float
    source: str = ""
    sequence: int | None = None


class RawMessageEmitter:
    """Collect and emit raw messages. Tracks counts and drops."""

    def __init__(self, max_buffer_size: int = 10000) -> None:
        self._max_buffer = max(0, max_buffer_size)
        self._buffer: deque[RawMessage] = deque(maxlen=self._max_buffer)
        self._reordering_events: deque[RawMessageReorderingEvent] = deque(maxlen=512)
        self._last_recv_times: dict[tuple[str, str], float] = {}
        self._total_emitted: int = 0
        self._total_dropped: int = 0
        self._total_reordered: int = 0
        self._high_water_mark: int = 0

    def emit(self, message: RawMessage) -> bool:
        """Add a message to the buffer.

        GEM-05: keep the newest message by evicting the oldest when full.
        Returns False only if the buffer cannot retain any message.
        """
        if not message.recv_time:
            raise ValueError("RawMessage must have recv_time set")

        self._track_upstream_reordering(message)

        if self._max_buffer == 0:
            self._total_dropped += 1
            logger.warning(
                "raw_message_dropped_no_capacity",
                extra={
                    "pair": message.pair,
                    "stream_type": message.stream_type,
                    "recv_time": message.recv_time,
                    "capacity": self._max_buffer,
                },
            )
            return False

        if len(self._buffer) == self._max_buffer:
            self._total_dropped += 1
            logger.warning(
                "raw_message_buffer_drop_oldest",
                extra={
                    "pair": message.pair,
                    "stream_type": message.stream_type,
                    "recv_time": message.recv_time,
                    "capacity": self._max_buffer,
                    "total_dropped": self._total_dropped,
                },
            )

        self._buffer.append(message)
        self._total_emitted += 1
        self._high_water_mark = max(self._high_water_mark, len(self._buffer))
        return True

    def consume(self, max_count: int | None = None) -> tuple[RawMessage, ...]:
        """Consume messages from the buffer (FIFO)."""
        if max_count is None:
            msgs = tuple(self._buffer)
            self._buffer.clear()
            return msgs
        return tuple(self._buffer.popleft() for _ in range(min(max_count, len(self._buffer))))

    @property
    def backlog(self) -> int:
        return len(self._buffer)

    @property
    def total_emitted(self) -> int:
        return self._total_emitted

    @property
    def total_dropped(self) -> int:
        return self._total_dropped

    @property
    def total_reordered(self) -> int:
        return self._total_reordered

    @property
    def utilization(self) -> float:
        if self._max_buffer == 0:
            return 1.0
        return len(self._buffer) / self._max_buffer

    @property
    def capacity(self) -> int:
        return self._max_buffer

    @property
    def high_water_mark(self) -> int:
        return self._high_water_mark

    @property
    def drop_rate(self) -> float:
        total = self._total_emitted + self._total_dropped
        if total == 0:
            return 0.0
        return self._total_dropped / total

    def get_reordering_events(self) -> tuple[RawMessageReorderingEvent, ...]:
        return tuple(self._reordering_events)

    def _track_upstream_reordering(self, message: RawMessage) -> None:
        key = (message.pair, message.stream_type)
        previous_recv_time = self._last_recv_times.get(key)
        if previous_recv_time is not None and message.recv_time < previous_recv_time:
            self._total_reordered += 1
            event = RawMessageReorderingEvent(
                pair=message.pair,
                stream_type=message.stream_type,
                previous_recv_time=previous_recv_time,
                recv_time=message.recv_time,
                source=message.source,
                sequence=message.sequence,
            )
            self._reordering_events.append(event)
            logger.warning(
                "raw_message_upstream_reordered",
                extra={
                    "pair": event.pair,
                    "stream_type": event.stream_type,
                    "previous_recv_time": event.previous_recv_time,
                    "recv_time": event.recv_time,
                    "source": event.source,
                    "sequence": event.sequence,
                    "total_reordered": self._total_reordered,
                },
            )
            self._last_recv_times[key] = max(previous_recv_time, message.recv_time)
            return

        self._last_recv_times[key] = message.recv_time
