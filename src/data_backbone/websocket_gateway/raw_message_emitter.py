"""
4.5.5 — Raw Message Emitter: emit raw messages with recv_time metadata.

Invariant: every raw message MUST have a recv_time. No silent reordering.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RawMessage(BaseModel, frozen=True):
    """A raw WS message with reception metadata.

    Invariant: recv_time is always set. No raw payload leaks to business modules.
    """

    pair: str
    stream_type: str  # "trade" | "depth" | "kline" | "heartbeat"
    payload: dict  # raw exchange data — opaque to business modules
    recv_time: float  # local reception timestamp (mandatory)
    source: str = ""  # exchange identifier
    sequence: int | None = None  # optional exchange sequence number


class RawMessageEmitter:
    """Collect and emit raw messages. Tracks counts and drops."""

    def __init__(self, max_buffer_size: int = 10000) -> None:
        self._buffer: list[RawMessage] = []
        self._max_buffer = max_buffer_size
        self._total_emitted: int = 0
        self._total_dropped: int = 0

    def emit(self, message: RawMessage) -> bool:
        """Add a message to the buffer. Returns False if dropped (buffer full)."""
        if not message.recv_time:
            raise ValueError("RawMessage must have recv_time set")

        if len(self._buffer) >= self._max_buffer:
            self._total_dropped += 1
            return False

        self._buffer.append(message)
        self._total_emitted += 1
        return True

    def consume(self, max_count: int | None = None) -> tuple[RawMessage, ...]:
        """Consume messages from the buffer (FIFO). Non-destructive read is not supported."""
        if max_count is None:
            msgs = tuple(self._buffer)
            self._buffer.clear()
            return msgs
        msgs = tuple(self._buffer[:max_count])
        self._buffer = self._buffer[max_count:]
        return msgs

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
    def utilization(self) -> float:
        """ρ_q = backlog / max_buffer."""
        if self._max_buffer == 0:
            return 1.0
        return len(self._buffer) / self._max_buffer
