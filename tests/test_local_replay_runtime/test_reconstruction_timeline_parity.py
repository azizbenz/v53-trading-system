"""A2-RECON-SHARE (2026-06-05) — parity proof for the partition-shared
reconstruction-state timeline.

The fast path (`_build_reconstruction_state_timeline` + bisect) must return
byte-identical ``(spread_bps, status)`` to the legacy per-row walk for every
target timestamp, across: multi-snapshot base selection, cross-book purge,
sequence-gap detection, and the non-monotonic-ts fallback guard.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from local_replay_runtime import strategy_ladder_economic_provenance as m

_ReconResult = tuple[float | None, str]


def _write_jsonl_gz(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _clear_caches() -> None:
    m._load_reconstruction_snapshots.cache_clear()
    m._load_reconstruction_deltas.cache_clear()
    m._build_reconstruction_state_timeline.cache_clear()


def _measure_all(
    snapshot_path: Path,
    delta_path: Path,
    targets: list[int],
    *,
    enabled: bool,
    step: int | None,
    monkeypatch: pytest.MonkeyPatch,
) -> list[_ReconResult]:
    monkeypatch.setattr(m, "_RECONSTRUCTION_TIMELINE_ENABLED", enabled)
    _clear_caches()
    return [
        m._measure_spread_via_reconstruction(
            snapshot_path=snapshot_path,
            delta_path=delta_path,
            timestamp_ms=t,
            tolerance_ms=60_000,
            expected_update_id_step=step,
        )
        for t in targets
    ]


def _build_two_snapshot_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """Two snapshot anchors (re-anchor) + 150 consecutive-uid deltas with
    monotonic ts; every ~17th delta injects a stale crossing bid (W0 purge)."""
    snapshots = [
        {
            "timestamp_ms": 1000,
            "update_id": 100,
            "bids": [[99.0, 5.0], [98.0, 5.0], [97.0, 5.0]],
            "asks": [[101.0, 5.0], [102.0, 5.0], [103.0, 5.0]],
        },
        {
            "timestamp_ms": 2000,
            "update_id": 200,
            "bids": [[99.5, 4.0], [99.0, 4.0]],
            "asks": [[100.5, 4.0], [101.0, 4.0]],
        },
    ]
    snapshot_path = tmp_path / "orderbook_snapshot.jsonl.gz"
    _write_jsonl_gz(snapshot_path, snapshots)

    deltas = []
    for i in range(150):
        uid = 101 + i
        ts = 1010 + i * 10
        move = ((i % 10) - 5) * 0.05
        best_ask = max(100.2, 101.0 + move)
        best_bid = min(99.8, 99.0 - move)
        bids = [[round(best_bid, 4), 4.0]]
        asks = [[round(best_ask, 4), 4.0]]
        if i % 17 == 16:
            bids.append([round(best_ask + 0.5, 4), 1.0])  # stale crossing -> purge
        deltas.append(
            {"timestamp_ms": ts, "update_id": uid, "bids": bids, "asks": asks}
        )
    delta_path = tmp_path / "orderbook_delta.jsonl.gz"
    _write_jsonl_gz(delta_path, deltas)
    return snapshot_path, delta_path


@pytest.mark.parametrize("step", [None, 1])
def test_timeline_parity_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: int | None
) -> None:
    snapshot_path, delta_path = _build_two_snapshot_dataset(tmp_path)
    # Sweep: before base, between deltas, across the re-anchor, after the stream.
    targets = list(range(950, 2700, 7))

    legacy = _measure_all(
        snapshot_path, delta_path, targets, enabled=False, step=step, monkeypatch=monkeypatch
    )
    fast = _measure_all(
        snapshot_path, delta_path, targets, enabled=True, step=step, monkeypatch=monkeypatch
    )

    assert fast == legacy
    # The optimisation must actually run (not silently all-fallback) and produce
    # measured reconstructions for a meaningful share of the sweep.
    measured = [s for _v, s in fast if s.startswith("MEASURED_FROM_BOOK_RECONSTRUCTION")]
    assert len(measured) >= len(targets) // 2


def test_timeline_parity_with_uid_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing update_id (gap) must yield identical SEQUENCE_GAP provenance in
    both paths when expected_update_id_step=1."""
    snapshots = [
        {
            "timestamp_ms": 1000,
            "update_id": 100,
            "bids": [[99.0, 5.0]],
            "asks": [[101.0, 5.0]],
        }
    ]
    snapshot_path = tmp_path / "orderbook_snapshot.jsonl.gz"
    _write_jsonl_gz(snapshot_path, snapshots)

    deltas = []
    uid = 101
    for i in range(40):
        if i == 20:
            uid += 1  # SKIP one update_id -> sequence gap
        ts = 1010 + i * 10
        deltas.append(
            {
                "timestamp_ms": ts,
                "update_id": uid,
                "bids": [[round(99.0 + (i % 5) * 0.05, 4), 4.0]],
                "asks": [[round(101.0 - (i % 5) * 0.05, 4), 4.0]],
            }
        )
        uid += 1
    delta_path = tmp_path / "orderbook_delta.jsonl.gz"
    _write_jsonl_gz(delta_path, deltas)

    targets = list(range(1000, 1420, 5))
    legacy = _measure_all(
        snapshot_path, delta_path, targets, enabled=False, step=1, monkeypatch=monkeypatch
    )
    fast = _measure_all(
        snapshot_path, delta_path, targets, enabled=True, step=1, monkeypatch=monkeypatch
    )

    assert fast == legacy
    assert any("SEQUENCE_GAP" in s for _v, s in fast)


def test_timeline_falls_back_when_ts_non_monotonic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Out-of-order delta ts (vs update_id) must trip the monotonic guard so the
    caller uses the legacy walk — results stay identical either way."""
    snapshots = [
        {
            "timestamp_ms": 1000,
            "update_id": 100,
            "bids": [[99.0, 5.0]],
            "asks": [[101.0, 5.0]],
        }
    ]
    snapshot_path = tmp_path / "orderbook_snapshot.jsonl.gz"
    _write_jsonl_gz(snapshot_path, snapshots)

    # ts jumps backward at uid 105 (1050 -> 1025) while uid keeps increasing.
    ts_by_offset = [1010, 1020, 1030, 1040, 1025, 1060, 1070, 1080]
    deltas = [
        {
            "timestamp_ms": ts_by_offset[i],
            "update_id": 101 + i,
            "bids": [[round(99.0 + i * 0.02, 4), 4.0]],
            "asks": [[round(101.0 - i * 0.02, 4), 4.0]],
        }
        for i in range(len(ts_by_offset))
    ]
    delta_path = tmp_path / "orderbook_delta.jsonl.gz"
    _write_jsonl_gz(delta_path, deltas)

    _clear_caches()
    _ts, _sp, _gap, monotonic = m._build_reconstruction_state_timeline(
        str(snapshot_path), str(delta_path), 100, None
    )
    assert monotonic is False

    targets = list(range(1000, 1100, 3))
    legacy = _measure_all(
        snapshot_path, delta_path, targets, enabled=False, step=None, monkeypatch=monkeypatch
    )
    fast = _measure_all(
        snapshot_path, delta_path, targets, enabled=True, step=None, monkeypatch=monkeypatch
    )
    assert fast == legacy
