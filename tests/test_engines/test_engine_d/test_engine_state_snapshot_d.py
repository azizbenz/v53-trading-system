from __future__ import annotations

from pathlib import Path

import pytest

from interface_contracts import Side

from engines.engine_d import (
    ConsecutiveStopStateD,
    EngineDStateSnapshotStore,
)


NOW_NS = 1_700_000_000_000_000_000


def _state(
    *,
    consecutive_stop_count: int = 0,
    last_stop_at_ns: int | None = None,
    last_fresh_a_detection_at_ns: int | None = None,
    failsafe_override_available: bool = False,
) -> ConsecutiveStopStateD:
    return ConsecutiveStopStateD(
        consecutive_stop_count=consecutive_stop_count,
        last_stop_at_ns=last_stop_at_ns,
        last_fresh_a_detection_at_ns=last_fresh_a_detection_at_ns,
        failsafe_override_available=failsafe_override_available,
    )


def test_state_snapshot_store_append_and_latest_state() -> None:
    store = EngineDStateSnapshotStore()

    first = store.append_state(
        pair="btcusdt",
        side=Side.BUY,
        state=_state(consecutive_stop_count=1, last_stop_at_ns=NOW_NS + 10),
        captured_at_ns=NOW_NS + 10,
    )
    second = store.append_state(
        pair="BTCUSDT",
        side=Side.BUY,
        state=_state(
            consecutive_stop_count=0,
            last_stop_at_ns=NOW_NS + 10,
            last_fresh_a_detection_at_ns=NOW_NS + 20,
        ),
        captured_at_ns=NOW_NS + 20,
    )

    assert store.read() == (first, second)
    latest = store.latest_snapshot(pair="BTCUSDT", side=Side.BUY)
    assert latest is not None
    assert latest.captured_at_ns == NOW_NS + 20
    assert store.latest_state(pair="BTCUSDT", side=Side.BUY) == second.state


def test_state_snapshot_store_latest_snapshot_is_order_independent() -> None:
    store = EngineDStateSnapshotStore()
    newer = _state(consecutive_stop_count=1, last_stop_at_ns=NOW_NS + 30)
    older = _state(consecutive_stop_count=1, last_stop_at_ns=NOW_NS + 10)

    store.append_state(
        pair="BTCUSDT",
        side=Side.SELL,
        state=newer,
        captured_at_ns=NOW_NS + 30,
    )
    store.append_state(
        pair="BTCUSDT",
        side=Side.SELL,
        state=older,
        captured_at_ns=NOW_NS + 10,
    )

    latest = store.latest_snapshot(pair="BTCUSDT", side=Side.SELL)
    assert latest is not None
    assert latest.captured_at_ns == NOW_NS + 30
    assert latest.state == newer


def test_state_snapshot_store_round_trips_records_and_manifest(repo_tmp_path: Path) -> None:
    store = EngineDStateSnapshotStore(flush_dir=repo_tmp_path)
    store.append_state(
        pair="BTCUSDT",
        side=Side.BUY,
        state=_state(consecutive_stop_count=1, last_stop_at_ns=NOW_NS + 10),
        captured_at_ns=NOW_NS + 10,
    )
    store.append_state(
        pair="ETHUSDT",
        side=Side.SELL,
        state=_state(
            consecutive_stop_count=1,
            last_stop_at_ns=NOW_NS + 30,
            failsafe_override_available=True,
        ),
        captured_at_ns=NOW_NS + 30,
    )

    manifest = store.flush_to_disk()
    loaded = EngineDStateSnapshotStore.load_from_disk(repo_tmp_path)

    assert manifest is not None
    assert manifest.snapshot_count == 2
    assert loaded.read() == store.read()
    assert loaded.pending_flush_count == 0
    assert (repo_tmp_path / "engine_d_state_snapshots.jsonl").exists()
    assert (repo_tmp_path / "engine_d_state_snapshot_manifest.json").exists()


def test_state_snapshot_store_rejects_manifest_mismatch(repo_tmp_path: Path) -> None:
    store = EngineDStateSnapshotStore(flush_dir=repo_tmp_path)
    store.append_state(
        pair="BTCUSDT",
        side=Side.BUY,
        state=_state(consecutive_stop_count=1, last_stop_at_ns=NOW_NS + 10),
        captured_at_ns=NOW_NS + 10,
    )
    store.flush_to_disk()

    (repo_tmp_path / "engine_d_state_snapshots.jsonl").write_text(
        '{"tampered": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manifest hash mismatch"):
        EngineDStateSnapshotStore.load_from_disk(repo_tmp_path)
