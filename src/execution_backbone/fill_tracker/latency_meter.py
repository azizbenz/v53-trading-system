"""
Build-3 / fill_tracker / latency_meter
Measure submit, ack, first fill, and full fill latencies.

AckLat = (1/N) Σ (t_ack_i - t_send_i)

GEM-07: all timestamps MUST use time.monotonic() (not time.time())
to avoid NTP jumps and ensure monotone latency measurements.
"""

from __future__ import annotations

import time as _time

from pydantic import BaseModel, Field


def monotonic_now() -> float:
    """GEM-07: canonical monotonic clock for all latency measurements."""
    return _time.monotonic()


class LatencyMeasurement(BaseModel, frozen=True):
    """Latency measurements for a single order."""

    order_id: str
    signal_to_submit_s: float | None = None
    signal_to_scoring_s: float | None = None
    scoring_to_risk_s: float | None = None
    risk_to_portfolio_s: float | None = None
    portfolio_to_submit_s: float | None = None
    submit_to_ack_s: float | None = None
    submit_to_first_fill_s: float | None = None
    submit_to_full_fill_s: float | None = None
    ack_to_first_fill_s: float | None = None


class LatencyStats(BaseModel, frozen=True):
    """Aggregate latency statistics."""

    count: int = 0
    avg_signal_to_submit_s: float = 0.0
    avg_signal_to_scoring_s: float = 0.0
    avg_scoring_to_risk_s: float = 0.0
    avg_risk_to_portfolio_s: float = 0.0
    avg_portfolio_to_submit_s: float = 0.0
    avg_submit_to_ack_s: float = 0.0
    avg_submit_to_first_fill_s: float = 0.0
    avg_submit_to_full_fill_s: float = 0.0
    p90_signal_to_submit_s: float = 0.0
    p90_signal_to_scoring_s: float = 0.0
    p90_scoring_to_risk_s: float = 0.0
    p90_risk_to_portfolio_s: float = 0.0
    p90_portfolio_to_submit_s: float = 0.0
    p90_submit_to_ack_s: float = 0.0
    filtered_samples: int = 0


class LatencyMeter:
    """Measure order lifecycle latencies."""

    def __init__(self, max_latency_s: float = 60.0) -> None:
        self._measurements: dict[str, LatencyMeasurement] = {}
        self._max_latency_s = max_latency_s
        self._filtered_samples = 0

    def record_submit(
        self,
        order_id: str,
        *,
        signal_arrival_time: float | None = None,
        scoring_completed_time: float | None = None,
        risk_completed_time: float | None = None,
        portfolio_completed_time: float | None = None,
        submit_time: float | None = None,
    ) -> LatencyMeasurement | None:
        signal_to_submit = self._sanitize_latency(
            (submit_time - signal_arrival_time)
            if signal_arrival_time is not None and submit_time is not None
            else None,
        )
        signal_to_scoring = self._sanitize_latency(
            (scoring_completed_time - signal_arrival_time)
            if signal_arrival_time is not None and scoring_completed_time is not None
            else None,
        )
        scoring_to_risk = self._sanitize_latency(
            (risk_completed_time - scoring_completed_time)
            if scoring_completed_time is not None and risk_completed_time is not None
            else None,
        )
        risk_to_portfolio = self._sanitize_latency(
            (portfolio_completed_time - risk_completed_time)
            if risk_completed_time is not None and portfolio_completed_time is not None
            else None,
        )
        portfolio_to_submit = self._sanitize_latency(
            (submit_time - portfolio_completed_time)
            if portfolio_completed_time is not None and submit_time is not None
            else None,
        )
        update = {
            "signal_to_submit_s": signal_to_submit,
            "signal_to_scoring_s": signal_to_scoring,
            "scoring_to_risk_s": scoring_to_risk,
            "risk_to_portfolio_s": risk_to_portfolio,
            "portfolio_to_submit_s": portfolio_to_submit,
        }
        if all(value is None for value in update.values()):
            return None
        existing = self._measurements.get(order_id, LatencyMeasurement(order_id=order_id))
        updated = existing.model_copy(update=update)
        self._measurements[order_id] = updated
        return updated

    def _sanitize_latency(self, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > self._max_latency_s:
            self._filtered_samples += 1
            return None
        return value

    def record(
        self,
        order_id: str,
        sent_time: float | None = None,
        ack_time: float | None = None,
        first_fill_time: float | None = None,
        full_fill_time: float | None = None,
    ) -> LatencyMeasurement:
        existing = self._measurements.get(order_id, LatencyMeasurement(order_id=order_id))
        submit_to_ack = self._sanitize_latency(
            (ack_time - sent_time) if sent_time is not None and ack_time is not None else None,
        )
        submit_to_first = self._sanitize_latency(
            (first_fill_time - sent_time)
            if sent_time is not None and first_fill_time is not None
            else None,
        )
        submit_to_full = self._sanitize_latency(
            (full_fill_time - sent_time)
            if sent_time is not None and full_fill_time is not None
            else None,
        )
        ack_to_first = self._sanitize_latency(
            (first_fill_time - ack_time)
            if ack_time is not None and first_fill_time is not None
            else None,
        )

        m = existing.model_copy(
            update={
                "submit_to_ack_s": submit_to_ack,
                "submit_to_first_fill_s": submit_to_first,
                "submit_to_full_fill_s": submit_to_full,
                "ack_to_first_fill_s": ack_to_first,
            }
        )
        self._measurements[order_id] = m
        return m

    def get_stats(self) -> LatencyStats:
        if not self._measurements:
            return LatencyStats(filtered_samples=self._filtered_samples)

        measurements = tuple(self._measurements.values())
        signal_submit_lats = [m.signal_to_submit_s for m in measurements if m.signal_to_submit_s is not None]
        signal_scoring_lats = [m.signal_to_scoring_s for m in measurements if m.signal_to_scoring_s is not None]
        scoring_risk_lats = [m.scoring_to_risk_s for m in measurements if m.scoring_to_risk_s is not None]
        risk_portfolio_lats = [m.risk_to_portfolio_s for m in measurements if m.risk_to_portfolio_s is not None]
        portfolio_submit_lats = [m.portfolio_to_submit_s for m in measurements if m.portfolio_to_submit_s is not None]
        ack_lats = [m.submit_to_ack_s for m in measurements if m.submit_to_ack_s is not None]
        first_lats = [m.submit_to_first_fill_s for m in measurements if m.submit_to_first_fill_s is not None]
        full_lats = [m.submit_to_full_fill_s for m in measurements if m.submit_to_full_fill_s is not None]

        def avg(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        def p90(vals: list[float]) -> float:
            if not vals:
                return 0.0
            s = sorted(vals)
            idx = int(len(s) * 0.9)
            return s[min(idx, len(s) - 1)]

        return LatencyStats(
            count=len(measurements),
            avg_signal_to_submit_s=avg(signal_submit_lats),
            avg_signal_to_scoring_s=avg(signal_scoring_lats),
            avg_scoring_to_risk_s=avg(scoring_risk_lats),
            avg_risk_to_portfolio_s=avg(risk_portfolio_lats),
            avg_portfolio_to_submit_s=avg(portfolio_submit_lats),
            avg_submit_to_ack_s=avg(ack_lats),
            avg_submit_to_first_fill_s=avg(first_lats),
            avg_submit_to_full_fill_s=avg(full_lats),
            p90_signal_to_submit_s=p90(signal_submit_lats),
            p90_signal_to_scoring_s=p90(signal_scoring_lats),
            p90_scoring_to_risk_s=p90(scoring_risk_lats),
            p90_risk_to_portfolio_s=p90(risk_portfolio_lats),
            p90_portfolio_to_submit_s=p90(portfolio_submit_lats),
            p90_submit_to_ack_s=p90(ack_lats),
            filtered_samples=self._filtered_samples,
        )
