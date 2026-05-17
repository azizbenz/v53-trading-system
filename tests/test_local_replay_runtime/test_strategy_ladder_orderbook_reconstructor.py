from __future__ import annotations

from local_replay_runtime.strategy_ladder_orderbook_reconstructor import (
    reconstruct_strategy_ladder_orderbook,
)


def _levels(side: str) -> list[list[str]]:
    base = 100.0 if side == "bid" else 101.0
    return [
        [f"{base - index * 0.1 if side == 'bid' else base + index * 0.1:.1f}", f"{10 + index:.1f}"]
        for index in range(20)
    ]


def test_snapshot_plus_deltas_reconstructs_depth20() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=2_000,
        snapshot_rows=(
            {"timestamp_ms": 1_000, "seq": 1, "b": _levels("bid"), "a": _levels("ask")},
        ),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 2, "b": [["100.0", "15.0"]], "a": [["101.0", "20.0"]]},
        ),
    )

    assert result.book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
    assert result.sequence_status == "SEQUENCE_READY"
    assert result.reconstructed_snapshot is not None
    assert len(result.reconstructed_snapshot.bids) == 20
    assert len(result.reconstructed_snapshot.asks) == 20


def test_delta_only_without_snapshot_is_not_promotion_grade_depth() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=2_000,
        snapshot_rows=(),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 2, "b": [["100.0", "15.0"]], "a": [["101.0", "20.0"]]},
        ),
    )

    assert result.book_depth_source_status == "BOOK_DEPTH_NOT_PROVEN"
    assert "MISSING_SNAPSHOT" in result.reason_codes
    assert result.reconstructed_snapshot is None


def test_qty_zero_deletes_book_level() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=2_000,
        snapshot_rows=(
            {"timestamp_ms": 1_000, "seq": 1, "b": _levels("bid"), "a": _levels("ask")},
        ),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 2, "b": [[str(100.0), "0"]], "a": []},
        ),
    )

    assert result.reconstructed_snapshot is not None
    bid_prices = {round(level.price, 1) for level in result.reconstructed_snapshot.bids}
    assert 100.0 not in bid_prices


def test_sequence_gap_blocks_promotion_grade_depth() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=2_000,
        snapshot_rows=(
            {"timestamp_ms": 1_000, "seq": 1, "b": _levels("bid"), "a": _levels("ask")},
        ),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 4, "b": [["99.9", "11.0"]], "a": [["101.1", "11.0"]]},
        ),
    )

    assert result.book_depth_source_status == "BOOK_DEPTH_STALE"
    assert "SEQUENCE_GAP" in result.reason_codes
    assert "NO_PROMOTION_GRADE_DEPTH_AFTER_GAP" in result.reason_codes
    assert result.reconstructed_snapshot is None
    assert result.gap_status == "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED"
    assert result.gap_count == 1


def test_sparse_delta_array_is_not_treated_as_full_depth() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=2_000,
        snapshot_rows=(),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 2, "b": [["100.0", "15.0"]], "a": []},
        ),
    )

    assert result.book_depth_source_status == "BOOK_DEPTH_NOT_PROVEN"
    assert "MISSING_SNAPSHOT" in result.reason_codes
    assert result.reconstructed_snapshot is None


def test_sequence_gap_can_be_marked_recovered_after_later_snapshot() -> None:
    result = reconstruct_strategy_ladder_orderbook(
        pair="BTCUSDT",
        anchor_timestamp_ms=3_000,
        snapshot_rows=(
            {"timestamp_ms": 1_000, "seq": 1, "b": _levels("bid"), "a": _levels("ask")},
            {"timestamp_ms": 2_000, "seq": 10, "b": _levels("bid"), "a": _levels("ask")},
        ),
        delta_rows=(
            {"timestamp_ms": 1_500, "u": 4, "b": [["99.9", "11.0"]], "a": [["101.1", "11.0"]]},
            {"timestamp_ms": 2_500, "u": 11, "b": [["99.8", "12.0"]], "a": [["101.2", "12.0"]]},
        ),
    )

    assert result.sequence_status == "SEQUENCE_GAP_RECOVERED"
    assert result.gap_status == "ORDERBOOK_SEQUENCE_GAP_RECOVERED"
    assert result.reconstruction_success_after_gap is True
    assert result.reconstructed_snapshot is not None
