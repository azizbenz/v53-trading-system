"""Book Sequence Sentinel — wire gap-detection to a re-snapshot trigger.

2026-06-02 — closes the orchestration gap on the live/shadow ingest path. The
bricks already existed but nothing connected them:

  GapDetector.check()            detects an ``update_id`` discontinuity (+1)
  RestBootstrapRuntime.resync()  re-fetches a fresh snapshot anchor via REST

This sentinel observes every incoming book delta and invokes an injected
``resync_trigger`` when:

  * a SEQUENCE_GAP is detected (missed WS messages -> the local book has
    silently diverged from the exchange), or
  * the gap-free chain since the last anchor exceeds ``max_chain_deltas``
    (CHAIN_BUDGET — periodic re-anchor, defense in depth even without a gap).

Each resync writes a fresh snapshot anchor into the captured stream, so later
book reconstruction re-anchors there and the chain stays short and gap-free —
which is what makes FUTURE backtests exact. ``max_chain_deltas`` is the same
lever as ``recommended_snapshots_per_day`` (chain length <-> snapshots/day).

Doctrine: this is ingest plumbing that COMPOSES existing bricks (no new engine,
no parallel architecture). The trigger is injected so the runtime wires it to
``RestBootstrapRuntime.resync`` + the silver anchor writer; the sentinel itself
is pure and fully unit-testable.
"""
from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from pydantic import BaseModel, Field

from .gap_detector import GapDetector


class ResyncReason(StrEnum):
    SEQUENCE_GAP = "sequence_gap"
    CHAIN_BUDGET = "chain_budget"


class ResyncRequest(BaseModel, frozen=True):
    """Emitted to the injected resync trigger when a fresh anchor is needed."""

    pair: str
    stream_type: str
    reason: ResyncReason
    chain_len_at_trigger: int = Field(ge=0)
    expected_seq: int | None = None
    actual_seq: int | None = None
    gap_size: int | None = None


class SentinelObservation(BaseModel, frozen=True):
    """Per-delta result returned by ``observe``."""

    gap_detected: bool
    resync_triggered: bool
    reason: ResyncReason | None = None
    chain_len: int = Field(ge=0)


class BookSequenceSentinel:
    """Per-delta sequence monitor that triggers re-snapshots on gap / budget."""

    def __init__(
        self,
        *,
        resync_trigger: Callable[[ResyncRequest], None],
        max_chain_deltas: int | None = None,
        gap_detector: GapDetector | None = None,
    ) -> None:
        if max_chain_deltas is not None and max_chain_deltas <= 0:
            raise ValueError("max_chain_deltas must be positive when set")
        self._trigger = resync_trigger
        self._max_chain = max_chain_deltas
        self._gap_detector = gap_detector or GapDetector()
        self._chain_len: dict[tuple[str, str], int] = {}
        self._gaps_detected = 0
        self._resyncs_triggered = 0
        self._resync_failures = 0

    def on_anchor(self, pair: str, stream_type: str, sequence: int) -> None:
        """Register a fresh snapshot anchor (bootstrap or post-resync): reset the
        chain counter and re-baseline the gap detector to ``sequence``."""
        self._gap_detector.reset(pair, stream_type, sequence)
        self._chain_len[(pair, stream_type)] = 0

    def observe(self, pair: str, stream_type: str, sequence: int) -> SentinelObservation:
        """Process one incoming book delta sequence id. Returns what happened."""
        key = (pair, stream_type)
        gap = self._gap_detector.check(pair, stream_type, sequence)
        self._chain_len[key] = self._chain_len.get(key, 0) + 1

        if gap is not None:
            self._gaps_detected += 1
            self._fire(
                ResyncRequest(
                    pair=pair,
                    stream_type=stream_type,
                    reason=ResyncReason.SEQUENCE_GAP,
                    chain_len_at_trigger=self._chain_len[key],
                    expected_seq=gap.expected_seq,
                    actual_seq=gap.actual_seq,
                    gap_size=gap.gap_size,
                )
            )
            self._chain_len[key] = 0
            return SentinelObservation(
                gap_detected=True,
                resync_triggered=True,
                reason=ResyncReason.SEQUENCE_GAP,
                chain_len=0,
            )

        if self._max_chain is not None and self._chain_len[key] >= self._max_chain:
            self._fire(
                ResyncRequest(
                    pair=pair,
                    stream_type=stream_type,
                    reason=ResyncReason.CHAIN_BUDGET,
                    chain_len_at_trigger=self._chain_len[key],
                )
            )
            self._chain_len[key] = 0
            return SentinelObservation(
                gap_detected=False,
                resync_triggered=True,
                reason=ResyncReason.CHAIN_BUDGET,
                chain_len=0,
            )

        return SentinelObservation(
            gap_detected=False,
            resync_triggered=False,
            reason=None,
            chain_len=self._chain_len[key],
        )

    def _fire(self, request: ResyncRequest) -> None:
        """Invoke the injected trigger. Best-effort: a failing trigger (REST
        down, rate limited) must never crash the ingest loop — it is counted so
        the operator sees unfilled gaps, and the chain still resets."""
        self._resyncs_triggered += 1
        try:
            self._trigger(request)
        except Exception:  # noqa: BLE001 — ingest loop must survive a failed resync
            self._resync_failures += 1

    @property
    def gaps_detected(self) -> int:
        return self._gaps_detected

    @property
    def resyncs_triggered(self) -> int:
        return self._resyncs_triggered

    @property
    def resync_failures(self) -> int:
        return self._resync_failures


__all__ = [
    "BookSequenceSentinel",
    "ResyncReason",
    "ResyncRequest",
    "SentinelObservation",
]
