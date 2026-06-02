"""Gate — BookSequenceSentinel: wire gap-detection -> re-snapshot trigger (point 2).

The live-ingest bricks already exist but were never wired:
  - GapDetector.check()       detects update_id discontinuity (+1 contiguity)
  - RestBootstrapRuntime.resync()  re-fetches a fresh snapshot anchor on a gap

BookSequenceSentinel closes the orchestration gap: per incoming book delta it
checks contiguity and, on a gap OR when the gap-free chain exceeds the re-anchor
budget, invokes the injected resync trigger so a fresh anchor is captured. Each
anchor bounds the reconstruction chain -> future backtests reconstruct exactly.
"""
from __future__ import annotations

from data_backbone.consistency_checker.book_sequence_sentinel import (
    BookSequenceSentinel,
    ResyncReason,
    ResyncRequest,
)


def _collector():
    calls: list[ResyncRequest] = []
    return calls, calls.append


def test_contiguous_stream_never_triggers_resync() -> None:
    calls, trigger = _collector()
    s = BookSequenceSentinel(resync_trigger=trigger)
    s.on_anchor("BTCUSDT", "orderbook", 100)  # bootstrap anchor uid=100
    for seq in range(101, 121):  # contiguous +1
        obs = s.observe("BTCUSDT", "orderbook", seq)
        assert obs.gap_detected is False
        assert obs.resync_triggered is False
    assert calls == []
    assert s.resyncs_triggered == 0
    assert s.gaps_detected == 0


def test_sequence_gap_triggers_resync() -> None:
    calls, trigger = _collector()
    s = BookSequenceSentinel(resync_trigger=trigger)
    s.on_anchor("BTCUSDT", "orderbook", 100)
    assert s.observe("BTCUSDT", "orderbook", 101).resync_triggered is False
    # GAP: 102,103 missing -> jump to 104
    obs = s.observe("BTCUSDT", "orderbook", 104)
    assert obs.gap_detected is True
    assert obs.resync_triggered is True
    assert obs.reason == ResyncReason.SEQUENCE_GAP
    assert len(calls) == 1
    req = calls[0]
    assert req.pair == "BTCUSDT"
    assert req.reason == ResyncReason.SEQUENCE_GAP
    assert req.expected_seq == 102
    assert req.actual_seq == 104
    assert req.gap_size == 2
    assert s.gaps_detected == 1
    assert s.resyncs_triggered == 1


def test_chain_resets_after_gap_resync() -> None:
    """After a gap triggers resync, the chain restarts from the next sequence
    (no cascade of resyncs on the post-gap contiguous stream)."""
    calls, trigger = _collector()
    s = BookSequenceSentinel(resync_trigger=trigger)
    s.on_anchor("BTCUSDT", "orderbook", 100)
    s.observe("BTCUSDT", "orderbook", 101)
    s.observe("BTCUSDT", "orderbook", 110)  # gap -> resync #1
    # operator's resync wrote a fresh anchor at, say, uid 110; sentinel re-anchors
    s.on_anchor("BTCUSDT", "orderbook", 110)
    for seq in range(111, 130):  # contiguous after re-anchor
        assert s.observe("BTCUSDT", "orderbook", seq).resync_triggered is False
    assert s.resyncs_triggered == 1


def test_chain_budget_triggers_periodic_reanchor() -> None:
    """Even with NO gap, exceeding max_chain_deltas forces a re-anchor (defense
    in depth, bounds drift) — this is the snapshots/day cadence in action."""
    calls, trigger = _collector()
    s = BookSequenceSentinel(resync_trigger=trigger, max_chain_deltas=5)
    s.on_anchor("BTCUSDT", "orderbook", 100)
    triggers = 0
    for seq in range(101, 112):  # 11 contiguous deltas, budget 5
        obs = s.observe("BTCUSDT", "orderbook", seq)
        if obs.resync_triggered:
            triggers += 1
            assert obs.reason == ResyncReason.CHAIN_BUDGET
            s.on_anchor("BTCUSDT", "orderbook", seq)  # operator re-anchors
    assert triggers >= 1
    assert all(c.reason == ResyncReason.CHAIN_BUDGET for c in calls)


def test_per_pair_stream_isolation() -> None:
    """Sequences are tracked per (pair, stream) — a gap on one pair does not
    affect another."""
    calls, trigger = _collector()
    s = BookSequenceSentinel(resync_trigger=trigger)
    s.on_anchor("BTCUSDT", "orderbook", 100)
    s.on_anchor("ETHUSDT", "orderbook", 500)
    s.observe("BTCUSDT", "orderbook", 101)
    s.observe("ETHUSDT", "orderbook", 501)
    obs = s.observe("BTCUSDT", "orderbook", 105)  # gap on BTC only
    assert obs.resync_triggered is True
    assert s.observe("ETHUSDT", "orderbook", 502).resync_triggered is False
    assert [c.pair for c in calls] == ["BTCUSDT"]


def test_resync_trigger_failure_is_isolated() -> None:
    """A failing resync trigger must not crash the ingest loop (best-effort);
    the gap is still recorded."""
    def boom(_req: ResyncRequest) -> None:
        raise RuntimeError("REST down")

    s = BookSequenceSentinel(resync_trigger=boom)
    s.on_anchor("BTCUSDT", "orderbook", 100)
    s.observe("BTCUSDT", "orderbook", 101)
    obs = s.observe("BTCUSDT", "orderbook", 109)  # gap; trigger raises
    assert obs.gap_detected is True
    assert obs.resync_triggered is True  # attempted
    assert s.gaps_detected == 1
    assert s.resync_failures == 1
