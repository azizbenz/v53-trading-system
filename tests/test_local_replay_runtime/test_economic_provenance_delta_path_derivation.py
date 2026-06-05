"""Patch 2026-06-05 — A2 spread-staleness root-cause fix.

``_derive_orderbook_delta_path`` must resolve the **silver** layout, where
``orderbook_snapshot`` / ``orderbook_delta`` are parent DIRECTORIES
(``silver/{venue}/spot/orderbook_snapshot/{PAIR}/{Y}/{M}/{D}.jsonl.gz``) and the
filename carries no token — not only the **raw-windows** layout where the token
is in the filename and the two files sit side by side.

Measured on run 53402a08 (BTC 2025-11-16): for the silver A2 gold path the
derivation returned ``None``, so the Tier 2 spread reconstruction was silently
skipped and every window fell back to the stale snapshot. With the delta path
resolved, 47/48 windows reconstruct fresh (``MEASURED_FROM_BOOK_RECONSTRUCTION``,
~1-tick spread 0.0105 bps) instead of ``MEASURED_FROM_BOOK_SNAPSHOT_STALE``.
"""
from __future__ import annotations

from pathlib import Path

from local_replay_runtime.strategy_ladder_economic_provenance import (
    _derive_orderbook_delta_path,
)


def test_silver_layout_resolves_parallel_delta_directory(tmp_path: Path) -> None:
    """Silver A2 gold layout: token is a parent directory, delta lives in a
    PARALLEL ``orderbook_delta`` tree. This was the staleness root cause."""
    snap = tmp_path / "silver/bybit/spot/orderbook_snapshot/BTCUSDT/2025/11/16.jsonl.gz"
    delta = tmp_path / "silver/bybit/spot/orderbook_delta/BTCUSDT/2025/11/16.jsonl.gz"
    snap.parent.mkdir(parents=True)
    delta.parent.mkdir(parents=True)
    snap.write_text("x", encoding="utf-8")
    delta.write_text("x", encoding="utf-8")
    assert _derive_orderbook_delta_path(snap) == delta


def test_raw_windows_layout_still_resolves(tmp_path: Path) -> None:
    """Raw-windows (B2) layout: token in the filename, files co-located. Pins
    that the silver fix does not regress the original behaviour."""
    window_dir = tmp_path / "raw_windows/BTCUSDT/cand0"
    window_dir.mkdir(parents=True)
    snap = window_dir / "orderbook_snapshot.jsonl.gz"
    delta = window_dir / "orderbook_delta.jsonl.gz"
    snap.write_text("x", encoding="utf-8")
    delta.write_text("x", encoding="utf-8")
    assert _derive_orderbook_delta_path(snap) == delta


def test_missing_delta_returns_none(tmp_path: Path) -> None:
    """No sibling delta in either layout -> None (no false positive)."""
    snap = tmp_path / "silver/bybit/spot/orderbook_snapshot/BTCUSDT/2025/11/16.jsonl.gz"
    snap.parent.mkdir(parents=True)
    snap.write_text("x", encoding="utf-8")
    assert _derive_orderbook_delta_path(snap) is None
