"""Patch B2-RECON-SHARE (2026-06-04) — parity gate for the partition-shared book
reconstruction.

The B2 fix makes candidates of one ``(pair, base snapshot)`` partition reuse a
single cumulative book-state timeline instead of re-walking the day's deltas
each. The non-negotiable invariant is **bit-exact parity** with the legacy
per-window reconstruction (:func:`_reconstruct_book_states`). These tests pin
that for nested, overlapping, and out-of-order window sequences — the exact B2
window shapes that defeated the old forward-only progressive cache (0/15 hit).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from local_replay_runtime import strategy_ladder_engine_native_adapter as adp
from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    _PartitionBookTimeline,
    _reconstruct_book_states,
)


def _base_snapshot() -> dict:
    return {
        "update_id": 100,
        "timestamp_ms": 1_000,
        "bids": [[100.0, 5.0], [99.0, 3.0], [98.5, 1.0]],
        "asks": [[101.0, 4.0], [102.0, 2.0], [103.5, 6.0]],
    }


def _deltas() -> list[dict]:
    # Strictly increasing update_id + timestamp_ms; exercise add / update / remove
    # (size 0.0) on both sides so the book churns across the window.
    return [
        {"update_id": 101, "timestamp_ms": 1_100, "bids": [[100.0, 6.0]], "asks": []},
        {"update_id": 102, "timestamp_ms": 1_200, "bids": [], "asks": [[101.0, 0.0], [101.5, 7.0]]},
        {"update_id": 103, "timestamp_ms": 1_300, "bids": [[99.5, 2.0]], "asks": []},
        {"update_id": 104, "timestamp_ms": 1_400, "bids": [[100.0, 0.0]], "asks": [[102.0, 1.0]]},
        {"update_id": 105, "timestamp_ms": 1_500, "bids": [[98.0, 9.0]], "asks": [[103.0, 3.0]]},
        {"update_id": 106, "timestamp_ms": 1_600, "bids": [[99.0, 0.0]], "asks": [[101.5, 0.0]]},
    ]


def _legacy(ws: int, we: int, top_k: int = 20) -> list:
    return _reconstruct_book_states(
        base_snapshot=_base_snapshot(),
        deltas=_deltas(),
        window_start_ms=ws,
        window_end_ms=we,
        top_k=top_k,
    )


def test_partition_timeline_matches_legacy_nested_windows() -> None:
    """Nested windows (shared start, increasing end) — the B2 day-start-anchored
    shape. Each extend reuses the prior cumulative states; slices stay bit-exact."""
    base = _base_snapshot()
    deltas = _deltas()
    ws = 1_000
    timeline = _PartitionBookTimeline.from_base(base)
    for we in (1_200, 1_400, 1_600):
        timeline.extend(deltas, window_end_ms=we, top_k=20)
        assert timeline.window_slice(ws, we) == _legacy(ws, we), f"we={we}"


def test_partition_timeline_matches_legacy_overlapping_windows() -> None:
    """Overlapping windows (sliding start AND end)."""
    base = _base_snapshot()
    deltas = _deltas()
    timeline = _PartitionBookTimeline.from_base(base)
    for ws, we in [(1_000, 1_300), (1_150, 1_450), (1_250, 1_600)]:
        timeline.extend(deltas, window_end_ms=we, top_k=20)
        assert timeline.window_slice(ws, we) == _legacy(ws, we), f"({ws},{we})"


def test_partition_timeline_out_of_order_query_is_correct() -> None:
    """A shorter window queried AFTER the timeline already covers a larger end
    must still equal the legacy reconstruction (random-access safety)."""
    base = _base_snapshot()
    deltas = _deltas()
    timeline = _PartitionBookTimeline.from_base(base)
    timeline.extend(deltas, window_end_ms=1_600, top_k=20)
    for ws, we in [(1_000, 1_200), (1_100, 1_400), (1_000, 1_600), (1_300, 1_500)]:
        assert timeline.window_slice(ws, we) == _legacy(ws, we), f"({ws},{we})"


def test_partition_timeline_incremental_equals_single_shot() -> None:
    """Extending in many small steps yields the same states as one big extend."""
    base = _base_snapshot()
    deltas = _deltas()
    incremental = _PartitionBookTimeline.from_base(base)
    for we in (1_100, 1_200, 1_300, 1_400, 1_500, 1_600):
        incremental.extend(deltas, window_end_ms=we, top_k=20)
    single = _PartitionBookTimeline.from_base(base)
    single.extend(deltas, window_end_ms=1_600, top_k=20)
    assert incremental.states == single.states
    assert incremental.window_slice(1_000, 1_600) == _legacy(1_000, 1_600)


def test_partition_timeline_respects_top_k() -> None:
    """top_k truncation must match the legacy path exactly."""
    base = _base_snapshot()
    deltas = _deltas()
    timeline = _PartitionBookTimeline.from_base(base)
    timeline.extend(deltas, window_end_ms=1_600, top_k=2)
    assert timeline.window_slice(1_000, 1_600) == _legacy(1_000, 1_600, top_k=2)


def _fake_delta_loader(deltas: list[dict]) -> Callable[..., list[dict]]:
    def _load(
        delta_path: Path,
        *,
        base_update_id: int,
        window_end_ms: int,
        window_start_ms: int | None = None,
        after_update_id: int | None = None,
    ) -> list[dict]:
        # Timeline dedups by update_id, so returning a uid-superset is safe.
        return [
            d
            for d in deltas
            if int(d["update_id"]) > base_update_id
            and int(d["timestamp_ms"]) <= window_end_ms
        ]

    return _load


def test_partition_shared_helper_builds_one_timeline_per_partition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shipped helper keys by (pair, base_update_id): many candidates of one
    partition build ONE timeline (the measured B2 win: 14 candidates -> 2 builds),
    and every candidate's states stay bit-exact with the legacy reconstruction."""
    base = _base_snapshot()
    monkeypatch.setattr(
        adp, "_load_book_deltas_in_window_with_lookback", _fake_delta_loader(_deltas())
    )
    monkeypatch.setattr(adp, "_PARTITION_BOOK_TIMELINE_ENABLED", True)
    adp.reset_microstructure_file_cache_stats(clear_cache=True)

    for we in (1_200, 1_400, 1_600):
        states, _ = adp._partition_shared_book_states(
            pair="BTCUSDT",
            raw_book_path="x/orderbook_snapshot/y",
            delta_path=Path("x/orderbook_delta/y"),
            base_snapshot=base,
            window_start_ms=1_000,
            window_end_ms=we,
            top_k=20,
        )
        assert states == _legacy(1_000, we), f"we={we}"

    assert adp.get_microstructure_file_cache_stats()["partition_timeline_build_count"] == 1

    # A different pair is a different partition -> its own timeline.
    adp._partition_shared_book_states(
        pair="ETHUSDT",
        raw_book_path="x/orderbook_snapshot/y",
        delta_path=Path("x/orderbook_delta/y"),
        base_snapshot=base,
        window_start_ms=1_000,
        window_end_ms=1_600,
        top_k=20,
    )
    assert adp.get_microstructure_file_cache_stats()["partition_timeline_build_count"] == 2


def test_partition_shared_helper_toggle_off_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rollback seam: with the toggle off the helper takes the legacy progressive
    path, builds no timeline, and still returns the legacy states."""
    base = _base_snapshot()
    monkeypatch.setattr(
        adp, "_load_book_deltas_in_window_with_lookback", _fake_delta_loader(_deltas())
    )
    monkeypatch.setattr(adp, "_PARTITION_BOOK_TIMELINE_ENABLED", False)
    adp.reset_microstructure_file_cache_stats(clear_cache=True)

    states, _ = adp._partition_shared_book_states(
        pair="BTCUSDT",
        raw_book_path="x/orderbook_snapshot/y",
        delta_path=Path("x/orderbook_delta/y"),
        base_snapshot=base,
        window_start_ms=1_000,
        window_end_ms=1_600,
        top_k=20,
    )
    assert states == _legacy(1_000, 1_600)
    assert adp.get_microstructure_file_cache_stats()["partition_timeline_build_count"] == 0
