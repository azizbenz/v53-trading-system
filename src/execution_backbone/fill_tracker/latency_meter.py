"""
Build-3 / fill_tracker / latency_meter
Measure submit, ack, first fill, and full fill latencies.

AckLat = (1/N) Σ (t_ack_i - t_send_i)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LatencyMeasurement(BaseModel, frozen=True):
    """Latency measurements for a single order."""

    order_id: str
    submit_to_ack_s: float | None = None
    submit_to_first_fill_s: float | None = None
    submit_to_full_fill_s: float | None = None
    ack_to_first_fill_s: float | None = None


class LatencyStats(BaseModel, frozen=True):
    """Aggregate latency statistics."""

    count: int = 0
    avg_submit_to_ack_s: float = 0.0
    avg_submit_to_first_fill_s: float = 0.0
    avg_submit_to_full_fill_s: float = 0.0
    p90_submit_to_ack_s: float = 0.0


class LatencyMeter:
    """Measure order lifecycle latencies."""

    def __init__(self) -> None:
        self._measurements: list[LatencyMeasurement] = []

    def record(
        self,
        order_id: str,
        sent_time: float | None = None,
        ack_time: float | None = None,
        first_fill_time: float | None = None,
        full_fill_time: float | None = None,
    ) -> LatencyMeasurement:
        submit_to_ack = (ack_time - sent_time) if sent_time is not None and ack_time is not None else None
        submit_to_first = (first_fill_time - sent_time) if sent_time is not None and first_fill_time is not None else None
        submit_to_full = (full_fill_time - sent_time) if sent_time is not None and full_fill_time is not None else None
        ack_to_first = (first_fill_time - ack_time) if ack_time is not None and first_fill_time is not None else None

        m = LatencyMeasurement(
            order_id=order_id,
            submit_to_ack_s=submit_to_ack,
            submit_to_first_fill_s=submit_to_first,
            submit_to_full_fill_s=submit_to_full,
            ack_to_first_fill_s=ack_to_first,
        )
        self._measurements.append(m)
        return m

    def get_stats(self) -> LatencyStats:
        if not self._measurements:
            return LatencyStats()

        ack_lats = [m.submit_to_ack_s for m in self._measurements if m.submit_to_ack_s is not None]
        first_lats = [m.submit_to_first_fill_s for m in self._measurements if m.submit_to_first_fill_s is not None]
        full_lats = [m.submit_to_full_fill_s for m in self._measurements if m.submit_to_full_fill_s is not None]

        def avg(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        def p90(vals: list[float]) -> float:
            if not vals:
                return 0.0
            s = sorted(vals)
            idx = int(len(s) * 0.9)
            return s[min(idx, len(s) - 1)]

        return LatencyStats(
            count=len(self._measurements),
            avg_submit_to_ack_s=avg(ack_lats),
            avg_submit_to_first_fill_s=avg(first_lats),
            avg_submit_to_full_fill_s=avg(full_lats),
            p90_submit_to_ack_s=p90(ack_lats),
        )
