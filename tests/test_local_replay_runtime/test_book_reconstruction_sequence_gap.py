"""Gate — delta sequence-gap detection in book reconstruction (2026-06-02).

Exactness fix: book reconstruction applies deltas forward from a snapshot
anchor. If the captured delta stream has a SEQUENCE GAP (missed update_id), the
reconstructed book silently diverges from reality. These tests prove the
gap-detection calibration seam (`expected_update_id_step`):

  - OFF (default None)  -> current behaviour preserved (no over-flagging)
  - ON  (step=1, Bybit) -> a gapped chain is FLAGGED in the provenance (the
                           spread value is still returned, but the gap is VISIBLE
                           so downstream gates can refuse promotion)
  - re-anchor           -> a later snapshot AFTER the gap yields a clean chain,
                           i.e. more snapshots/day removes the gap exposure.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_economic_provenance import (
    _load_reconstruction_deltas,
    _load_reconstruction_snapshots,
    _measure_spread_via_reconstruction,
    recommended_snapshots_per_day,
)

CT = 1_700_000_000_000


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _clear() -> None:
    _load_reconstruction_snapshots.cache_clear()
    _load_reconstruction_deltas.cache_clear()


def _snapshot(uid: int, ts: int) -> dict:
    return {
        "timestamp_ms": ts, "update_id": uid,
        "bids": [["100.0", "1.0"]], "asks": [["100.2", "1.0"]],
    }


def _delta(uid: int, ts: int, bid: str, ask: str) -> dict:
    return {
        "timestamp_ms": ts, "update_id": uid,
        "bids": [[bid, "1.0"]], "asks": [[ask, "1.0"]],
    }


def test_contiguous_deltas_step1_clean_measured(tmp_path: Path) -> None:
    """Contiguous update_ids (+1) with step=1 -> clean reconstruction."""
    snap = tmp_path / "orderbook_snapshot.jsonl"
    delta = tmp_path / "orderbook_delta.jsonl"
    _write_jsonl(snap, [_snapshot(100, CT - 10_000)])
    _write_jsonl(delta, [
        _delta(101, CT - 8_000, "100.05", "100.25"),
        _delta(102, CT - 6_000, "100.06", "100.26"),
        _delta(103, CT - 4_000, "100.07", "100.27"),
    ])
    _clear()
    spread, status = _measure_spread_via_reconstruction(
        snapshot_path=snap, delta_path=delta, timestamp_ms=CT,
        tolerance_ms=60_000, expected_update_id_step=1,
    )
    assert spread is not None
    assert status == "MEASURED_FROM_BOOK_RECONSTRUCTION"


def test_gapped_deltas_step1_flags_sequence_gap(tmp_path: Path) -> None:
    """A jump in update_id (105 -> 110) with step=1 must FLAG the gap."""
    snap = tmp_path / "orderbook_snapshot.jsonl"
    delta = tmp_path / "orderbook_delta.jsonl"
    _write_jsonl(snap, [_snapshot(100, CT - 10_000)])
    _write_jsonl(delta, [
        _delta(101, CT - 9_000, "100.05", "100.25"),
        _delta(102, CT - 8_000, "100.06", "100.26"),
        # GAP: 103,104,105 missing -> jump to 106
        _delta(106, CT - 4_000, "100.07", "100.27"),
        _delta(107, CT - 2_000, "100.08", "100.28"),
    ])
    _clear()
    spread, status = _measure_spread_via_reconstruction(
        snapshot_path=snap, delta_path=delta, timestamp_ms=CT,
        tolerance_ms=60_000, expected_update_id_step=1,
    )
    # value still returned (best-effort) but the gap is VISIBLE in provenance
    assert spread is not None
    assert "SEQUENCE_GAP" in status, f"expected gap flag, got {status}"


def test_gap_detection_off_by_default_no_regression(tmp_path: Path) -> None:
    """With step=None (default) gapped deltas reconstruct as before (clean)."""
    snap = tmp_path / "orderbook_snapshot.jsonl"
    delta = tmp_path / "orderbook_delta.jsonl"
    _write_jsonl(snap, [_snapshot(100, CT - 10_000)])
    _write_jsonl(delta, [
        _delta(101, CT - 9_000, "100.05", "100.25"),
        _delta(106, CT - 4_000, "100.07", "100.27"),  # gap, but detection OFF
    ])
    _clear()
    spread, status = _measure_spread_via_reconstruction(
        snapshot_path=snap, delta_path=delta, timestamp_ms=CT,
        tolerance_ms=60_000,  # expected_update_id_step omitted -> None -> OFF
    )
    assert spread is not None
    assert status == "MEASURED_FROM_BOOK_RECONSTRUCTION"  # unchanged behaviour


def test_gap_before_later_snapshot_reanchors_clean(tmp_path: Path) -> None:
    """A later snapshot AFTER the gap is chosen as anchor -> clean chain.

    Proves the re-anchor lever: adding a snapshot after the gap removes the
    gap exposure (the chain from the post-gap anchor is contiguous)."""
    snap = tmp_path / "orderbook_snapshot.jsonl"
    delta = tmp_path / "orderbook_delta.jsonl"
    # Two anchors: an early one (uid 100) and a fresh one (uid 200) after the gap
    _write_jsonl(snap, [
        _snapshot(100, CT - 60_000),
        _snapshot(200, CT - 5_000),  # re-anchor AFTER the gap region
    ])
    _write_jsonl(delta, [
        _delta(201, CT - 4_000, "100.05", "100.25"),
        _delta(202, CT - 3_000, "100.06", "100.26"),
        _delta(203, CT - 2_000, "100.07", "100.27"),
    ])
    _clear()
    spread, status = _measure_spread_via_reconstruction(
        snapshot_path=snap, delta_path=delta, timestamp_ms=CT,
        tolerance_ms=60_000, expected_update_id_step=1,
    )
    assert spread is not None
    assert status == "MEASURED_FROM_BOOK_RECONSTRUCTION"  # clean from re-anchor


def test_recommended_snapshots_per_day_calibration() -> None:
    """The snapshots/day count is DERIVED from the delta rate + drift budget,
    not a magic number. ~430k deltas/day (observed Bybit BTCUSDT) with a 50k
    max-chain budget -> 9 anchors/day; tighter budget -> more anchors."""
    # Observed real Bybit rate ~430k deltas/day, keep chains <= 50k deltas
    assert recommended_snapshots_per_day(delta_events_per_day=430_000, max_chain_deltas=50_000) == 9
    # Hourly-ish re-anchor budget (~18k) -> 24/day
    assert recommended_snapshots_per_day(delta_events_per_day=430_000, max_chain_deltas=18_000) == 24
    # Degenerate inputs -> at least the bootstrap anchor
    assert recommended_snapshots_per_day(delta_events_per_day=0, max_chain_deltas=50_000) == 1
    assert recommended_snapshots_per_day(delta_events_per_day=430_000, max_chain_deltas=0) == 1
    # Exact division -> no off-by-one
    assert recommended_snapshots_per_day(delta_events_per_day=100_000, max_chain_deltas=25_000) == 4
