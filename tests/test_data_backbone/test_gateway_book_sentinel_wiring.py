"""Gate — BookSequenceSentinel wired into WebSocketGatewayRuntime.poll_once.

Point 2 integration step: the gateway, when given a sentinel + the set of book
stream types, observes each book delta's sequence and triggers a resync on a
gap. Opt-in: with no sentinel (default) behaviour is unchanged.
"""
from __future__ import annotations

from data_backbone.consistency_checker.book_sequence_sentinel import (
    BookSequenceSentinel,
    ResyncReason,
    ResyncRequest,
)
from data_backbone.websocket_gateway.runtime_gateway import (
    AdapterMessage,
    WebSocketGatewayRuntime,
)

EP = "wss://stream"


class _FakeAdapter:
    def __init__(self) -> None:
        self.connected: set[str] = set()
        self.frames: dict[str, list[AdapterMessage]] = {}

    def connect(self, endpoint: str) -> None:
        self.connected.add(endpoint)

    def disconnect(self, endpoint: str) -> None:
        self.connected.discard(endpoint)

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        pass

    def recv(self, endpoint: str):
        q = self.frames.get(endpoint, [])
        return q.pop(0) if q else None


def _book_msg(seq: int) -> AdapterMessage:
    return AdapterMessage(
        pair="BTCUSDT", stream_type="orderbook",
        payload={"u": seq}, recv_time=float(seq), source="bybit", sequence=seq,
    )


def _runtime_with_sentinel():
    calls: list[ResyncRequest] = []
    sentinel = BookSequenceSentinel(resync_trigger=calls.append)
    adapter = _FakeAdapter()
    rt = WebSocketGatewayRuntime(
        adapter,
        book_sequence_sentinel=sentinel,
        book_stream_types=frozenset({"orderbook"}),
    )
    rt.subscribe("BTCUSDT", "orderbook", EP)
    rt.connect(EP, now=0.0)
    return rt, adapter, sentinel, calls


def test_contiguous_book_stream_no_resync() -> None:
    rt, adapter, sentinel, calls = _runtime_with_sentinel()
    sentinel.on_anchor("BTCUSDT", "orderbook", 100)
    adapter.frames[EP] = [_book_msg(s) for s in range(101, 106)]
    for _ in range(5):
        res = rt.poll_once(EP, now=1.0)
        assert res.sequence_gap_detected is False
        assert res.book_resync_triggered is False
    assert calls == []


def test_gapped_book_stream_triggers_resync() -> None:
    rt, adapter, sentinel, calls = _runtime_with_sentinel()
    sentinel.on_anchor("BTCUSDT", "orderbook", 100)
    adapter.frames[EP] = [_book_msg(101), _book_msg(106)]  # gap 102..105
    r1 = rt.poll_once(EP, now=1.0)
    assert r1.sequence_gap_detected is False
    r2 = rt.poll_once(EP, now=2.0)
    assert r2.sequence_gap_detected is True
    assert r2.book_resync_triggered is True
    assert len(calls) == 1
    assert calls[0].reason == ResyncReason.SEQUENCE_GAP
    assert calls[0].expected_seq == 102
    assert calls[0].actual_seq == 106


def test_non_book_stream_not_observed() -> None:
    """A trade stream (not in book_stream_types) must not drive book resync."""
    rt, adapter, sentinel, calls = _runtime_with_sentinel()
    sentinel.on_anchor("BTCUSDT", "orderbook", 100)
    adapter.frames[EP] = [
        AdapterMessage(pair="BTCUSDT", stream_type="trade", payload={},
                       recv_time=1.0, source="bybit", sequence=9999),
    ]
    res = rt.poll_once(EP, now=1.0)
    assert res.sequence_gap_detected is False
    assert res.book_resync_triggered is False
    assert calls == []
    assert sentinel.gaps_detected == 0


def test_default_no_sentinel_unchanged() -> None:
    """No sentinel injected -> poll_once behaves exactly as before."""
    adapter = _FakeAdapter()
    rt = WebSocketGatewayRuntime(adapter)
    rt.subscribe("BTCUSDT", "orderbook", EP)
    rt.connect(EP, now=0.0)
    adapter.frames[EP] = [_book_msg(101), _book_msg(900)]  # big gap, but no sentinel
    res = rt.poll_once(EP, now=1.0)
    assert res.raw_message is not None
    assert res.sequence_gap_detected is False
    assert res.book_resync_triggered is False
