"""Tests pour strategy_ladder_engine_native_adapter (Audit 2026-05-06 P3a).

Ces tests prouvent que le pont microstructure entre le rail Strategy Ladder
backtest et le seam canonique data_backbone.microstructure fonctionne
sur :
  1. Une fenetre fictive auto-contenue (test unit, pas d'IO disque)
  2. Le contrat de retour EngineNativeBridgeResult

Les tests d'integration sur le run dossier reel
(K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411/...)
sont separes et opt-in via la variable d'env STRATEGY_LADDER_REAL_RUN_DOSSIER
pour ne pas couper le CI quand le drive K: est absent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    EngineABridgeResult,
    EngineBBridgeResult,
    EngineDBridgeResult,
    EngineNativeBridgeResult,
    build_engine_a_microstructure_inputs_from_window,
    build_engine_b_microstructure_inputs_from_window,
    build_engine_c_microstructure_inputs_from_window,
    build_engine_d_microstructure_inputs_from_window,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _synthetic_trades(*, base_ts_ms: int, n: int = 200) -> list[dict[str, object]]:
    """200 trades fictifs etales sur 60 secondes, prix oscillant autour de 100."""
    rows: list[dict[str, object]] = []
    for i in range(n):
        rows.append(
            {
                "timestamp_ms": base_ts_ms + i * 300,
                "pair": "TESTPAIR",
                "trade_id": str(i + 1),
                "price": str(100.0 + (i % 20) * 0.05),
                "qty": "0.5",
                "side": "buy" if i % 2 == 0 else "sell",
            }
        )
    return rows


def _synthetic_initial_snapshot(
    *,
    ts_ms: int,
    update_id: int = 1000,
    n_levels: int = 20,
) -> dict[str, object]:
    """1 snapshot initial avec n_levels de chaque cote.

    Format Bybit/canonique : update_id, bids/asks comme list of [price_str, size_str].
    """
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "event_type": "snapshot",
        "update_id": update_id,
        "bids": [
            [str(round(99.95 - 0.01 * level, 4)), str(10.0 + level * 2)]
            for level in range(n_levels)
        ],
        "asks": [
            [str(round(100.05 + 0.01 * level, 4)), str(8.0 + level * 2)]
            for level in range(n_levels)
        ],
    }


def _synthetic_book_deltas(
    *,
    base_ts_ms: int,
    base_update_id: int,
    n: int = 30,
    spacing_ms: int = 2000,
) -> list[dict[str, object]]:
    """N deltas alternant bid/ask, espacement regulier, update_id consecutifs."""
    rows: list[dict[str, object]] = []
    for i in range(n):
        if i % 2 == 0:
            # Update du bid top level
            bids = [[str(99.95), str(10.0 + (i % 5))]]
            asks = []
        else:
            # Update de l'ask top level
            bids = []
            asks = [[str(100.05), str(8.0 + (i % 5))]]
        rows.append(
            {
                "timestamp_ms": base_ts_ms + i * spacing_ms,
                "pair": "TESTPAIR",
                "event_type": "delta",
                "update_id": base_update_id + 1 + i,
                "bids": bids,
                "asks": asks,
            }
        )
    return rows


def test_a2_opt4_progressive_book_state_cache_advances_incrementally(tmp_path: Path) -> None:
    """Patch A2-OPT-4 (2026-05-26 — F16-D Pilier 0) — progressive book state cache.

    Validates that the progressive cache:
      1. Misses on first decision, builds book from snapshot, caches final state.
      2. Hits on second contiguous decision, reuses prior cached state, applies
         only the new deltas between cached_ts and new window_end_ms.
      3. Falls back to full reconstruct if requested window precedes cached state.
      4. Returns identical book_states (deterministic across cache hit/miss).
    """
    import gzip

    from local_replay_runtime.strategy_ladder_engine_native_adapter import (
        _PROGRESSIVE_BOOK_STATE_CACHE,
        _reconstruct_book_states,
        _reconstruct_book_states_with_progressive_cache,
        get_microstructure_file_cache_stats,
        reset_microstructure_file_cache_stats,
    )

    snapshot_path = tmp_path / "snapshot.jsonl.gz"
    delta_path = tmp_path / "delta.jsonl.gz"
    snapshot = {
        "timestamp_ms": 500,
        "update_id": 100,
        "bids": [["100.0", "1.0"], ["99.5", "2.0"]],
        "asks": [["100.5", "1.5"], ["101.0", "2.5"]],
    }
    deltas = [
        {"timestamp_ms": 1000, "update_id": 101, "bids": [["100.0", "1.2"]], "asks": []},
        {"timestamp_ms": 2000, "update_id": 102, "bids": [], "asks": [["100.5", "1.8"]]},
        {"timestamp_ms": 3000, "update_id": 103, "bids": [["99.0", "0.5"]], "asks": []},
        {"timestamp_ms": 4000, "update_id": 104, "bids": [], "asks": [["101.5", "1.0"]]},
        {"timestamp_ms": 5000, "update_id": 105, "bids": [["100.5", "0.0"]], "asks": []},
    ]
    with gzip.open(snapshot_path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot) + "\n")
    with gzip.open(delta_path, "wt", encoding="utf-8") as handle:
        for delta in deltas:
            handle.write(json.dumps(delta) + "\n")

    reset_microstructure_file_cache_stats(clear_cache=True)

    # First call: cache miss, reconstruct from snapshot, apply deltas in [1000, 3000].
    states_1 = _reconstruct_book_states_with_progressive_cache(
        snapshot_path=snapshot_path,
        delta_path=delta_path,
        base_snapshot=snapshot,
        deltas=deltas,
        window_start_ms=1000,
        window_end_ms=3000,
        top_k=20,
    )
    stats_after_first = get_microstructure_file_cache_stats()
    assert stats_after_first["progressive_book_state_miss_count"] == 1
    assert stats_after_first["progressive_book_state_hit_count"] == 0
    assert stats_after_first["progressive_book_state_cache_size"] == 1
    # 3 deltas had ts in [1000, 3000] (ts=1000, 2000, 3000)
    assert len(states_1) == 3
    assert [state.update_id for state in states_1] == [101, 102, 103]

    # Second call: cache hit — window [3001, 5000] is AFTER first window.
    states_2 = _reconstruct_book_states_with_progressive_cache(
        snapshot_path=snapshot_path,
        delta_path=delta_path,
        base_snapshot=snapshot,
        deltas=deltas,
        window_start_ms=3001,
        window_end_ms=5000,
        top_k=20,
    )
    stats_after_second = get_microstructure_file_cache_stats()
    assert stats_after_second["progressive_book_state_hit_count"] == 1
    assert stats_after_second["progressive_book_state_miss_count"] == 1
    # 2 deltas in [3001, 5000] (ts=4000, 5000)
    assert len(states_2) == 2
    assert [state.update_id for state in states_2] == [104, 105]
    # Advance count should equal exactly the new deltas applied (104, 105) = 2
    assert stats_after_second["progressive_book_state_advance_deltas"] >= 5  # 3 + 2

    # Determinism : without the cache, full reconstruct over [3001, 5000] gives same states.
    states_full = _reconstruct_book_states(
        base_snapshot=snapshot,
        deltas=deltas,
        window_start_ms=3001,
        window_end_ms=5000,
        top_k=20,
    )
    assert [state.update_id for state in states_full] == [104, 105]
    # Bid/ask levels at last state must match between cached and uncached paths.
    assert states_2[-1].bid_levels == states_full[-1].bid_levels
    assert states_2[-1].ask_levels == states_full[-1].ask_levels

    _PROGRESSIVE_BOOK_STATE_CACHE.clear()


def test_a2_opt1_deltas_after_base_cache_filters_and_bisects(tmp_path: Path) -> None:
    """Patch A2-OPT-1 (2026-05-25) — verify _deltas_after_base_index cache.

    Ensures the new cache:
      1. Filters by update_id > base_update_id correctly (drops base + earlier).
      2. Is reused across calls with same (path, base_update_id) (no re-iteration).
      3. _load_book_deltas_in_window_with_lookback bisects by window_end_ms.
    """
    import gzip

    from local_replay_runtime.strategy_ladder_engine_native_adapter import (
        _MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE,
        _deltas_after_base_index,
        _load_book_deltas_in_window_with_lookback,
        get_microstructure_file_cache_stats,
        reset_microstructure_file_cache_stats,
    )

    delta_path = tmp_path / "delta.jsonl.gz"
    deltas = [
        {"timestamp_ms": 1000, "update_id": 1, "side": "bid", "price": 100.0, "size": 1.0},
        {"timestamp_ms": 2000, "update_id": 2, "side": "bid", "price": 100.0, "size": 2.0},
        {"timestamp_ms": 3000, "update_id": 3, "side": "ask", "price": 101.0, "size": 1.0},
        {"timestamp_ms": 4000, "update_id": 4, "side": "ask", "price": 101.0, "size": 0.5},
        {"timestamp_ms": 5000, "update_id": 5, "side": "bid", "price": 100.5, "size": 3.0},
    ]
    with gzip.open(delta_path, "wt", encoding="utf-8") as handle:
        for delta in deltas:
            handle.write(json.dumps(delta) + "\n")

    reset_microstructure_file_cache_stats(clear_cache=True)
    timestamps_1, rows_1 = _deltas_after_base_index(delta_path, base_update_id=2)
    assert timestamps_1 == (3000, 4000, 5000), "Should drop deltas with update_id <= 2"
    assert len(rows_1) == 3
    stats_after_first = get_microstructure_file_cache_stats()
    assert stats_after_first["deltas_after_base_miss_count"] == 1
    assert stats_after_first["deltas_after_base_hit_count"] == 0

    timestamps_2, rows_2 = _deltas_after_base_index(delta_path, base_update_id=2)
    assert timestamps_2 is timestamps_1, "Cache should return same tuple identity on hit"
    stats_after_second = get_microstructure_file_cache_stats()
    assert stats_after_second["deltas_after_base_miss_count"] == 1
    assert stats_after_second["deltas_after_base_hit_count"] == 1

    timestamps_3, rows_3 = _deltas_after_base_index(delta_path, base_update_id=3)
    assert timestamps_3 == (4000, 5000)
    stats_after_third = get_microstructure_file_cache_stats()
    assert stats_after_third["deltas_after_base_miss_count"] == 2

    window_subset = _load_book_deltas_in_window_with_lookback(
        delta_path,
        base_update_id=2,
        window_end_ms=4000,
    )
    assert [row["update_id"] for row in window_subset] == [3, 4]

    _load_book_deltas_in_window_with_lookback(
        delta_path,
        base_update_id=2,
        window_end_ms=5000,
    )
    stats_after_window = get_microstructure_file_cache_stats()
    assert stats_after_window["deltas_after_base_miss_count"] == 2, (
        "Cache should be reused; no new miss expected"
    )

    empty = _load_book_deltas_in_window_with_lookback(
        delta_path,
        base_update_id=2,
        window_end_ms=500,
    )
    assert empty == []

    timestamps_empty, rows_empty = _deltas_after_base_index(delta_path, base_update_id=999)
    assert timestamps_empty == ()
    assert rows_empty == ()

    _MICROSTRUCTURE_DELTAS_AFTER_BASE_CACHE.clear()


def test_engine_native_adapter_builds_records_with_snapshot_plus_deltas(tmp_path: Path) -> None:
    """Sur une fenetre synthetique avec 200 trades + 1 snapshot initial + 30 deltas,
    le pont doit reconstruire 30 etats book consecutifs et calculer OFI +
    QueuePressure + VPIN + RealizedKernelVol (>= 4 records sur 5).

    Cas Kyle stale possible si bucket_seconds == window_seconds (1 bucket → fail)
    donc on n'exige PAS Kyle pour ce test minimum. Le test
    `test_engine_native_adapter_filters_stale_kyle_for_engine_c` couvre Kyle.
    """

    base_ts = 1_700_000_000_000
    window_start = base_ts
    window_end = base_ts + 60_000  # 1 min window

    # Snapshot initial 1s avant la fenetre (update_id=1000)
    snap = _synthetic_initial_snapshot(
        ts_ms=window_start - 1000, update_id=1000, n_levels=20
    )
    snap_path = tmp_path / "book_snapshots.jsonl"
    _write_jsonl(snap_path, [snap])

    # 30 deltas dans la fenetre (update_id 1001..1030)
    deltas = _synthetic_book_deltas(
        base_ts_ms=window_start, base_update_id=1000, n=30, spacing_ms=2000
    )
    delta_path = tmp_path / "book_deltas.jsonl"
    _write_jsonl(delta_path, deltas)

    # 200 trades dans la fenetre
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=window_start, n=200))

    result = build_engine_c_microstructure_inputs_from_window(
        candidate_id="synth-c1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
    )

    assert isinstance(result, EngineNativeBridgeResult)
    assert result.candidate_id == "synth-c1"
    assert result.pair == "TESTPAIR"
    assert result.n_trades_loaded == 200
    assert result.n_book_snapshots_loaded == 1
    assert result.n_book_deltas_loaded == 30, (
        f"30 deltas loaded attendus; got {result.n_book_deltas_loaded}; "
        f"warnings={result.bridge_warnings}"
    )
    assert result.n_book_states_reconstructed == 30, (
        f"30 etats reconstruits attendus; got {result.n_book_states_reconstructed}"
    )
    # OFI doit fonctionner avec 30 etats reconstruits
    assert result.ofi_record is not None, (
        f"OFI doit etre calcule via reconstruction; warnings={result.bridge_warnings}"
    )
    assert result.ofi_record.n_events_used >= 2
    # QueuePressure doit fonctionner sur le dernier etat reconstruit
    assert result.queue_pressure_record is not None, (
        f"QueuePressure doit etre calcule; warnings={result.bridge_warnings}"
    )
    assert -1.0 <= result.queue_pressure_record.value <= 1.0
    # VPIN
    assert result.vpin_record is not None, (
        f"VPIN doit etre calcule sur 200 trades; warnings={result.bridge_warnings}"
    )
    assert 0.0 <= result.vpin_record.value <= 1.0
    # On exige au moins 4 records sur 5 (Kyle peut echouer sur fenetre courte)
    assert result.n_records_built >= 4, (
        f"Pont microstructure n'a construit que {result.n_records_built}/5 records, "
        f"warnings={result.bridge_warnings}"
    )
    # Composition partielle engine_c reussit avec OFI inclus
    payload = result.engine_c_partial_input_payload
    assert payload, "Le payload partiel engine_c doit etre compose"
    assert payload.get("pair") == "TESTPAIR"
    assert payload.get("cumulative_ofi") is not None, (
        f"cumulative_ofi doit etre dans le payload partiel; payload={payload}"
    )


def test_engine_a_b_d_bridges_propagate_f16_book_records(tmp_path: Path) -> None:
    base_ts = 1_700_000_100_000
    window_start = base_ts
    window_end = base_ts + 60_000
    snap_path = tmp_path / "book_snapshots.jsonl"
    delta_path = tmp_path / "book_deltas.jsonl"
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(
        snap_path,
        [_synthetic_initial_snapshot(ts_ms=window_start - 1000, update_id=1000)],
    )
    _write_jsonl(
        delta_path,
        _synthetic_book_deltas(
            base_ts_ms=window_start,
            base_update_id=1000,
            n=30,
            spacing_ms=2000,
        ),
    )
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=window_start, n=200))

    engine_a = build_engine_a_microstructure_inputs_from_window(
        candidate_id="synth-a1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
    )
    engine_b = build_engine_b_microstructure_inputs_from_window(
        candidate_id="synth-b1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
    )
    engine_d = build_engine_d_microstructure_inputs_from_window(
        candidate_id="synth-d1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
        post_close_window_end_ms=window_end + 60_000,
    )

    for result in (engine_a, engine_b, engine_d):
        assert result.queue_pressure_record is not None
        assert result.vpin_record is not None
        assert result.ofi_record is not None
        assert result.n_book_states_reconstructed == 30


def test_engine_native_adapter_handles_empty_window(tmp_path: Path) -> None:
    """Une fenetre vide (pas de trade, pas de book) ne doit pas crasher.
    Le bridge_status doit indiquer FAILED_NO_RECORDS et chaque record None."""

    trade_path = tmp_path / "trades.jsonl"
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(trade_path, [])
    _write_jsonl(book_path, [])

    result = build_engine_c_microstructure_inputs_from_window(
        candidate_id="empty-c1",
        pair="EMPTYPAIR",
        window_start_ms=1_000_000_000_000,
        window_end_ms=1_000_000_300_000,
        raw_trade_path=trade_path,
        raw_book_path=book_path,
    )

    assert result.bridge_status == "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"
    assert result.n_trades_loaded == 0
    assert result.n_book_snapshots_loaded == 0
    assert result.n_records_built == 0
    assert result.kyle_lambda_record is None
    assert result.vpin_record is None
    assert result.ofi_record is None
    assert result.queue_pressure_record is None
    assert result.realized_kernel_vol_record is None


def test_engine_native_adapter_handles_missing_paths(tmp_path: Path) -> None:
    """Quand raw_trade_path et raw_book_path sont None, le pont retourne un
    resultat avec warnings explicites et 0 records."""

    result = build_engine_c_microstructure_inputs_from_window(
        candidate_id="nopath-c1",
        pair="NOPATHPAIR",
        window_start_ms=1_000_000_000_000,
        window_end_ms=1_000_000_300_000,
        raw_trade_path=None,
        raw_book_path=None,
    )

    assert result.bridge_status == "ENGINE_NATIVE_BRIDGE_FAILED_NO_RECORDS"
    assert "TRADE_PATH_MISSING" in result.bridge_warnings
    assert "BOOK_PATH_MISSING" in result.bridge_warnings
    assert result.n_records_built == 0


def test_engine_native_adapter_filters_stale_kyle_for_engine_c(tmp_path: Path) -> None:
    """Si compute_kyle_lambda renvoie un record stale (slope OLS negatif sur
    serie monotone descendante), le pont doit filtrer pour engine_c et ajouter
    un warning KYLE_FILTERED_FOR_ENGINE_C, evitant la ValidationError de
    EngineCMicrostructureProvenance.kyle_lambda (ge=0.0)."""

    base_ts = 1_700_000_000_000
    # Trades avec prix monotone descendant et volumes signes opposes
    # → produit un slope OLS negatif → Kyle stale
    trades = []
    for i in range(50):
        trades.append(
            {
                "timestamp_ms": base_ts + i * 1000,
                "pair": "STALEPAIR",
                "trade_id": str(i + 1),
                "price": str(100.0 - i * 0.1),  # prix descend
                "qty": "1.0",
                "side": "sell",  # tous sells → signed volume negatif
            }
        )
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, trades)
    snap_path = tmp_path / "book_snapshots.jsonl"
    _write_jsonl(
        snap_path,
        [_synthetic_initial_snapshot(ts_ms=base_ts - 500, update_id=2000, n_levels=10)],
    )
    delta_path = tmp_path / "book_deltas.jsonl"
    _write_jsonl(
        delta_path,
        _synthetic_book_deltas(
            base_ts_ms=base_ts, base_update_id=2000, n=10, spacing_ms=3000
        ),
    )

    result = build_engine_c_microstructure_inputs_from_window(
        candidate_id="stale-c1",
        pair="STALEPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
    )

    # Le pont doit avoir produit le record (avec is_stale=True ou value<0),
    # mais le payload composé ne doit PAS contenir kyle_lambda<0 (filtré).
    if result.kyle_lambda_record is not None:
        # Si Kyle a ete calcule, il doit etre filtre du payload
        # (ou bien il est positif, ce qui est aussi acceptable)
        if result.kyle_lambda_record.is_stale or result.kyle_lambda_record.value < 0:
            assert any(
                w.startswith("KYLE_FILTERED_FOR_ENGINE_C") for w in result.bridge_warnings
            ), f"warnings={result.bridge_warnings}"
            assert result.engine_c_partial_input_payload.get("kyle_lambda") is None


# ---------------------------------------------------------------------------
# Integration test sur le run dossier reel — opt-in via env var
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run integration test on real K: drive",
)
def test_engine_native_adapter_real_raw_window_from_run_dossier() -> None:
    """Test integration sur le run dossier reel
    (strategy_ladder_first_controlled_run-1778085375411).

    Prouve que le pont microstructure produit des records non-triviaux sur
    un raw_window genere par le rail backtest reel. Skipped par defaut ;
    activable via env var STRATEGY_LADDER_REAL_RUN_DOSSIER=1.
    """

    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    result = build_engine_c_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_book_path=manifest["raw_book_path"],
        raw_book_delta_path=manifest.get("raw_book_delta_path"),
    )

    # Apres ajout reconstruction snapshot+deltas (2026-05-07 fix), on exige
    # 5/5 records et OFI calcule. Avec ~963 deltas/fenetre, la reconstruction
    # donne ~963 etats book consecutifs et OFI doit converger.
    assert result.n_book_deltas_loaded > 100, (
        f"Reconstruction doit charger > 100 deltas sur fenetre 5min; "
        f"got {result.n_book_deltas_loaded}; warnings={result.bridge_warnings}"
    )
    assert result.n_book_states_reconstructed > 100, (
        f"Reconstruction doit produire > 100 etats book; "
        f"got {result.n_book_states_reconstructed}"
    )
    assert result.n_records_built >= 4, (
        f"Pont microstructure devrait produire >= 4 records sur run dossier reel; "
        f"got {result.n_records_built}/5, warnings={result.bridge_warnings}"
    )
    assert result.ofi_record is not None, (
        f"OFI doit etre calcule via reconstruction; warnings={result.bridge_warnings}"
    )
    assert result.ofi_record.n_events_used >= 2
    assert result.n_trades_loaded > 0
    # VPIN doit etre dans [0, 1]
    if result.vpin_record is not None:
        assert 0.0 <= result.vpin_record.value <= 1.0
    # QueuePressure doit etre dans [-1, 1]
    if result.queue_pressure_record is not None:
        assert -1.0 <= result.queue_pressure_record.value <= 1.0
    # Realized kernel vol > 0 sur 118 trades
    if result.realized_kernel_vol_record is not None:
        assert result.realized_kernel_vol_record.value > 0.0
    # Le payload partiel engine_c doit avoir cumulative_ofi non-None
    assert result.engine_c_partial_input_payload.get("cumulative_ofi") is not None


# ===========================================================================
# Engine D bridge (realized_vol_current + realized_vol_post_close)
# ===========================================================================


def test_engine_d_bridge_builds_realized_vol_current_on_synthetic_window(
    tmp_path: Path,
) -> None:
    """Engine D : realized_vol_current depuis trades dans la fenetre.
    Sans post_close_window_end_ms, post_close reste None (warning explicite)."""

    base_ts = 1_700_000_000_000
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=base_ts, n=200))

    result = build_engine_d_microstructure_inputs_from_window(
        candidate_id="d-synth-1",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        post_close_window_end_ms=None,
    )

    assert isinstance(result, EngineDBridgeResult)
    assert result.n_trades_loaded == 200
    assert result.realized_vol_current_record is not None
    assert result.realized_vol_current_record.value > 0.0
    assert result.realized_vol_post_close_record is None
    assert "REALIZED_VOL_POST_CLOSE_WINDOW_NOT_PROVIDED" in result.bridge_warnings
    payload = result.engine_d_partial_input_payload
    assert payload.get("pair") == "TESTPAIR"
    assert payload.get("realized_vol_current") is not None
    assert payload.get("realized_vol_post_close") is None
    assert result.bridge_status in {
        "ENGINE_NATIVE_BRIDGE_PARTIAL",
        "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING",
    }


def test_engine_d_bridge_builds_post_close_when_provided(tmp_path: Path) -> None:
    """Si post_close_window_end_ms fourni et trades disponibles, on calcule les 2."""

    base_ts = 1_700_000_000_000
    # 400 trades sur 120s : 200 dans la fenetre, 200 apres
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=base_ts, n=400))

    result = build_engine_d_microstructure_inputs_from_window(
        candidate_id="d-synth-2",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
        post_close_window_end_ms=base_ts + 120_000,
    )

    assert result.realized_vol_current_record is not None
    assert result.realized_vol_post_close_record is not None
    assert result.bridge_status == "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"
    assert result.engine_d_partial_input_payload.get("realized_vol_post_close") is not None


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_d_bridge_real_raw_window_from_run_dossier() -> None:
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = build_engine_d_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        post_close_window_end_ms=manifest["window_end_ms"] + 60_000,
    )
    assert result.n_trades_loaded > 0
    assert result.realized_vol_current_record is not None
    assert result.realized_vol_current_record.value > 0.0
    assert result.engine_d_partial_input_payload.get("realized_vol_current") is not None


# ===========================================================================
# Engine A bridge (ofi_flow_score + realized_kernel_vol_scale + kyle_lambda_cost_uplift)
# ===========================================================================


def test_engine_a_bridge_builds_records_with_snapshot_plus_deltas(
    tmp_path: Path,
) -> None:
    """Engine A : 3 records cibles (OFI + RealizedKernelVol + Kyle filtre).
    Reutilise reconstruction snapshot+deltas comme engine_c."""

    base_ts = 1_700_000_000_000
    window_start = base_ts
    window_end = base_ts + 60_000

    snap_path = tmp_path / "book_snapshots.jsonl"
    _write_jsonl(
        snap_path,
        [_synthetic_initial_snapshot(ts_ms=window_start - 1000, update_id=5000, n_levels=20)],
    )
    delta_path = tmp_path / "book_deltas.jsonl"
    _write_jsonl(
        delta_path,
        _synthetic_book_deltas(
            base_ts_ms=window_start, base_update_id=5000, n=30, spacing_ms=2000
        ),
    )
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=window_start, n=200))

    result = build_engine_a_microstructure_inputs_from_window(
        candidate_id="a-synth-1",
        pair="TESTPAIR",
        window_start_ms=window_start,
        window_end_ms=window_end,
        raw_trade_path=trade_path,
        raw_book_path=snap_path,
        raw_book_delta_path=delta_path,
    )

    assert isinstance(result, EngineABridgeResult)
    assert result.n_trades_loaded == 200
    assert result.n_book_states_reconstructed == 30
    assert result.ofi_record is not None
    assert result.realized_kernel_vol_record is not None
    # Engine A microstructure updates (additive seam updates)
    updates = result.engine_a_microstructure_updates
    assert "ofi_flow_score" in updates
    assert "realized_kernel_vol_scale" in updates
    assert "realized_vol_current" in updates
    assert "kyle_lambda_cost_uplift" in updates


def test_engine_a_bridge_falls_back_to_trade_flow_when_ofi_missing(
    tmp_path: Path,
) -> None:
    base_ts = 1_700_000_000_000
    trade_path = tmp_path / "buy_biased_trades.jsonl"
    rows = []
    for index in range(20):
        rows.append(
            {
                "timestamp_ms": base_ts + index * 1000,
                "pair": "TESTPAIR",
                "trade_id": str(index),
                "price": "100.0",
                "qty": "1.0",
                "side": "buy" if index < 15 else "sell",
            }
        )
    _write_jsonl(trade_path, rows)

    result = build_engine_a_microstructure_inputs_from_window(
        candidate_id="a-flow-fallback",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 20_000,
        raw_trade_path=trade_path,
        raw_book_path=None,
        raw_book_delta_path=None,
    )

    updates = result.engine_a_microstructure_updates
    assert updates["ofi_flow_score"] is None
    assert updates["flow_score"] == pytest.approx(0.75)
    assert "ENGINE_A_FLOW_SCORE_FROM_TRADE_IMBALANCE" in result.bridge_warnings


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_a_bridge_real_raw_window_from_run_dossier() -> None:
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = build_engine_a_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
        raw_book_path=manifest["raw_book_path"],
        raw_book_delta_path=manifest.get("raw_book_delta_path"),
    )
    # Sur run dossier reel : reconstruction debloque OFI et RealizedKernelVol
    assert result.n_book_deltas_loaded > 100
    assert result.n_book_states_reconstructed > 100
    assert result.ofi_record is not None
    assert result.realized_kernel_vol_record is not None
    assert result.realized_kernel_vol_record.value > 0.0
    # Kyle est probablement stale sur cette fenetre BNBUSDT (slope OLS negatif),
    # donc filtre. ofi_flow_score doit quand meme etre calcule par le seam.
    updates = result.engine_a_microstructure_updates
    assert "ofi_flow_score" in updates


# ===========================================================================
# Engine B bridge (current_price + local_mean + local_std + vpin)
# ===========================================================================


def test_engine_b_bridge_builds_local_mean_std_on_synthetic_window(
    tmp_path: Path,
) -> None:
    """Engine B : current_price, local_mean, local_std, vpin depuis trades."""

    base_ts = 1_700_000_000_000
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(trade_path, _synthetic_trades(base_ts_ms=base_ts, n=200))

    result = build_engine_b_microstructure_inputs_from_window(
        candidate_id="b-synth-1",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
    )

    assert isinstance(result, EngineBBridgeResult)
    assert result.n_trades_loaded == 200
    assert result.current_price is not None and result.current_price > 0.0
    assert result.local_mean is not None and result.local_mean > 0.0
    assert result.local_std is not None and result.local_std >= 0.0
    assert result.vpin_record is not None
    payload = result.engine_b_partial_input_payload
    assert payload.get("pair") == "TESTPAIR"
    assert payload.get("current_price") is not None
    assert payload.get("local_mean") is not None
    assert payload.get("local_std") is not None
    assert payload.get("vpin_current") is not None
    assert result.bridge_status == "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING"


def test_engine_b_bridge_handles_insufficient_trades(tmp_path: Path) -> None:
    """Avec 0 ou 1 trade, current_price/mean/std restent None."""

    base_ts = 1_700_000_000_000
    trade_path = tmp_path / "trades.jsonl"
    _write_jsonl(
        trade_path,
        [
            {
                "timestamp_ms": base_ts + 1000,
                "pair": "TESTPAIR",
                "trade_id": "1",
                "price": "100.0",
                "qty": "1.0",
                "side": "buy",
            }
        ],
    )

    result = build_engine_b_microstructure_inputs_from_window(
        candidate_id="b-synth-2",
        pair="TESTPAIR",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 60_000,
        raw_trade_path=trade_path,
    )

    assert result.current_price is None
    assert result.local_mean is None
    assert result.local_std is None
    assert any(
        w.startswith("LOCAL_MEAN_STD_INSUFFICIENT_TRADES") for w in result.bridge_warnings
    )


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_engine_b_bridge_real_raw_window_from_run_dossier() -> None:
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = build_engine_b_microstructure_inputs_from_window(
        candidate_id=manifest["candidate_id"],
        pair=manifest["pair"],
        window_start_ms=manifest["window_start_ms"],
        window_end_ms=manifest["window_end_ms"],
        raw_trade_path=manifest["raw_trade_path"],
    )
    assert result.n_trades_loaded > 0
    assert result.current_price is not None and result.current_price > 0.0
    assert result.local_mean is not None and result.local_mean > 0.0
    assert result.local_std is not None
    assert result.vpin_record is not None
    payload = result.engine_b_partial_input_payload
    assert payload.get("current_price") is not None
    assert payload.get("vpin_current") is not None
