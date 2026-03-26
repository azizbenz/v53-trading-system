"""
9.5.4 — Contradiction Checker: detect incompatible events.

Invariant: every contradiction is visible. No silent tolerance.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ContradictionType(StrEnum):
    PRICE_REVERSAL = "price_reversal"  # impossible price jump
    TIMESTAMP_REVERSAL = "timestamp_reversal"  # exchange time goes backwards
    VOLUME_ANOMALY = "volume_anomaly"  # negative or impossible volume
    BID_ASK_CROSS = "bid_ask_cross"  # best bid > best ask


class ContradictionEvent(BaseModel, frozen=True):
    """A detected contradiction between events."""

    pair: str
    contradiction_type: ContradictionType
    detail: str
    timestamp: float


class ContradictionChecker:
    """Detect contradictions in event streams."""

    def __init__(self) -> None:
        self._contradictions: list[ContradictionEvent] = []
        self._last_exchange_time: dict[tuple[str, str], float] = {}
        self._total_checked: int = 0

    def check_timestamp_order(
        self, pair: str, stream_type: str, exchange_time: float, recv_time: float,
    ) -> ContradictionEvent | None:
        """Check for timestamp reversal (exchange time going backwards)."""
        self._total_checked += 1
        key = (pair, stream_type)
        last = self._last_exchange_time.get(key)
        self._last_exchange_time[key] = exchange_time

        if last is not None and exchange_time < last:
            event = ContradictionEvent(
                pair=pair,
                contradiction_type=ContradictionType.TIMESTAMP_REVERSAL,
                detail=f"Exchange time {exchange_time} < previous {last}",
                timestamp=recv_time,
            )
            self._contradictions.append(event)
            return event
        return None

    def check_bid_ask_cross(
        self, pair: str, best_bid: float, best_ask: float, recv_time: float,
    ) -> ContradictionEvent | None:
        """Check for crossed book (best bid > best ask)."""
        self._total_checked += 1
        if best_bid > best_ask and best_ask > 0:
            event = ContradictionEvent(
                pair=pair,
                contradiction_type=ContradictionType.BID_ASK_CROSS,
                detail=f"Bid {best_bid} > Ask {best_ask}",
                timestamp=recv_time,
            )
            self._contradictions.append(event)
            return event
        return None

    def get_contradictions(self, pair: str | None = None) -> tuple[ContradictionEvent, ...]:
        if pair is None:
            return tuple(self._contradictions)
        return tuple(c for c in self._contradictions if c.pair == pair)

    @property
    def total_contradictions(self) -> int:
        return len(self._contradictions)

    @property
    def total_checked(self) -> int:
        return self._total_checked
