from __future__ import annotations

import gzip
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent
from local_replay_runtime.strategy_ladder_replay_evidence import (
    build_measured_spread_payload,
    build_replay_outcome_payload,
)
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    extract_strategy_ladder_raw_windows,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _read_jsonl_any(path: Path) -> list[dict[str, object]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _silver_index_payload(
    *,
    root: Path,
    trades_path: Path,
    snapshot_path: Path,
    delta_path: Path,
    ohlcv_path: Path,
    metadata_path: Path,
    candidate_ts: int,
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "entries": [
            {
                "source_id": "source_trades",
                "source_root": str((root / "raw_a").resolve()),
                "source_priority": 10,
                "exchange": "bybit",
                "market_type": "spot",
                "data_type": "trades",
                "pair": "BTCUSDT",
                "timeframe": "",
                "date": "2024-04-09",
                "path": str(trades_path.resolve()),
                "storage_format": "jsonl",
                "min_timestamp_ms": candidate_ts - 3_900_000,
                "max_timestamp_ms": candidate_ts,
                "row_count": 4,
                "file_hash": "hash-trades",
                "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                "schema_status": "TRADE_SCHEMA_READY",
            },
            {
                "source_id": "source_book",
                "source_root": str((root / "raw_b").resolve()),
                "source_priority": 20,
                "exchange": "bybit",
                "market_type": "spot",
                "data_type": "orderbook_snapshot",
                "pair": "BTCUSDT",
                "timeframe": "",
                "date": "2024-04-09",
                "path": str(snapshot_path.resolve()),
                "storage_format": "jsonl",
                "min_timestamp_ms": candidate_ts - 60_000,
                "max_timestamp_ms": candidate_ts - 60_000,
                "row_count": 1,
                "file_hash": "hash-snapshot",
                "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                "schema_status": "ORDERBOOK_SCHEMA_READY",
            },
            {
                "source_id": "source_book",
                "source_root": str((root / "raw_b").resolve()),
                "source_priority": 20,
                "exchange": "bybit",
                "market_type": "spot",
                "data_type": "orderbook_delta",
                "pair": "BTCUSDT",
                "timeframe": "",
                "date": "2024-04-09",
                "path": str(delta_path.resolve()),
                "storage_format": "jsonl",
                "min_timestamp_ms": candidate_ts,
                "max_timestamp_ms": candidate_ts,
                "row_count": 1,
                "file_hash": "hash-delta",
                "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                "schema_status": "ORDERBOOK_SCHEMA_READY",
            },
            {
                "source_id": "source_ohlcv",
                "source_root": str((root / "raw_c").resolve()),
                "source_priority": 10,
                "exchange": "bybit",
                "market_type": "spot",
                "data_type": "ohlcv",
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "date": "2024-04-09",
                "path": str(ohlcv_path.resolve()),
                "storage_format": "jsonl",
                "min_timestamp_ms": candidate_ts - 3_900_000,
                "max_timestamp_ms": candidate_ts,
                "row_count": 6,
                "file_hash": "hash-ohlcv",
                "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                "schema_status": "KLINE_SCHEMA_READY",
            },
            {
                "source_id": "source_meta",
                "source_root": str((root / "raw_meta").resolve()),
                "source_priority": 5,
                "exchange": "bybit",
                "market_type": "spot",
                "data_type": "metadata",
                "pair": "BTCUSDT",
                "timeframe": "",
                "date": "2024-04-09",
                "path": str(metadata_path.resolve()),
                "storage_format": "jsonl",
                "min_timestamp_ms": candidate_ts,
                "max_timestamp_ms": candidate_ts,
                "row_count": 1,
                "file_hash": "hash-meta",
                "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                "schema_status": "METADATA_SCHEMA_READY",
            },
        ],
    }


def _candidate(
    *,
    engine_id: str,
    candidate_ts: int,
    timeframe: str = "5m",
) -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        run_id="run-raw-engine-c",
        candidate_id=f"cand-{engine_id}",
        timestamp_ms=candidate_ts,
        pair="BTCUSDT",
        timeframe=timeframe,
        engine_id=engine_id,
        strategy_id=engine_id,
        compatibility_payload={
            "entry_price": 100.0,
            "close_price": 100.0,
            "side": "buy",
        },
    )


def test_engine_c_raw_window_extraction_pads_trades_and_ohlcv_with_prebreak_lookback(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_000_000
    logical_window_start_ms = candidate_ts - 300_000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "price": 100.0},
            {"timestamp_ms": candidate_ts - 3_000_000, "price": 100.2},
            {"timestamp_ms": candidate_ts - 300_000, "price": 100.4},
            {"timestamp_ms": candidate_ts, "price": 100.5},
        ],
    )
    _write_jsonl(
        snapshot_path,
        [{"timestamp_ms": candidate_ts - 60_000, "depth_levels": 20}],
    )
    _write_jsonl(
        delta_path,
        [{"timestamp_ms": candidate_ts, "u": 2}],
    )
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10.0},
            {"timestamp_ms": candidate_ts - 3_600_000, "open": 100.0, "high": 100.2, "low": 99.95, "close": 100.1, "volume": 11.0},
            {"timestamp_ms": candidate_ts - 3_300_000, "open": 100.1, "high": 100.25, "low": 100.0, "close": 100.2, "volume": 12.0},
            {"timestamp_ms": candidate_ts - 600_000, "open": 100.2, "high": 100.4, "low": 100.15, "close": 100.35, "volume": 13.0},
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.35, "high": 100.6, "low": 100.3, "close": 100.55, "volume": 14.0},
            {"timestamp_ms": candidate_ts, "open": 100.55, "high": 100.8, "low": 100.5, "close": 100.75, "volume": 15.0},
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index.json"
    _write_json(
        silver_index_path,
        _silver_index_payload(
            root=tmp_path,
            trades_path=trades_path,
            snapshot_path=snapshot_path,
            delta_path=delta_path,
            ohlcv_path=ohlcv_path,
            metadata_path=metadata_path,
            candidate_ts=candidate_ts,
        ),
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=(_candidate(engine_id="engine_c", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    assert manifest.window_start_ms == logical_window_start_ms
    trade_rows = [json.loads(line) for line in Path(manifest.raw_trade_path or "").read_text(encoding="utf-8").splitlines()]
    ohlcv_rows = [json.loads(line) for line in Path(manifest.raw_ohlcv_path or "").read_text(encoding="utf-8").splitlines()]
    assert trade_rows[0]["timestamp_ms"] < manifest.window_start_ms
    assert ohlcv_rows[0]["timestamp_ms"] < manifest.window_start_ms


def test_engine_a_raw_window_extraction_keeps_trade_slice_logical_but_pads_ohlcv_for_edge_lookback(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_000_000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "price": 100.0},
            {"timestamp_ms": candidate_ts - 300_000, "price": 100.4},
            {"timestamp_ms": candidate_ts, "price": 100.5},
        ],
    )
    _write_jsonl(snapshot_path, [{"timestamp_ms": candidate_ts - 60_000, "depth_levels": 20}])
    _write_jsonl(delta_path, [{"timestamp_ms": candidate_ts, "u": 2}])
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10.0},
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.35, "high": 100.6, "low": 100.3, "close": 100.55, "volume": 14.0},
            {"timestamp_ms": candidate_ts, "open": 100.55, "high": 100.8, "low": 100.5, "close": 100.75, "volume": 15.0},
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index.json"
    _write_json(
        silver_index_path,
        _silver_index_payload(
            root=tmp_path,
            trades_path=trades_path,
            snapshot_path=snapshot_path,
            delta_path=delta_path,
            ohlcv_path=ohlcv_path,
            metadata_path=metadata_path,
            candidate_ts=candidate_ts,
        ),
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=(_candidate(engine_id="engine_a", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    trade_rows = [json.loads(line) for line in Path(manifest.raw_trade_path or "").read_text(encoding="utf-8").splitlines()]
    ohlcv_rows = [json.loads(line) for line in Path(manifest.raw_ohlcv_path or "").read_text(encoding="utf-8").splitlines()]
    assert trade_rows[0]["timestamp_ms"] >= manifest.window_start_ms
    assert ohlcv_rows[0]["timestamp_ms"] < manifest.window_start_ms


def test_engine_b_raw_window_extraction_pads_ohlcv_for_edge_fallback_without_padding_trades(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_000_000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "price": 100.0},
            {"timestamp_ms": candidate_ts - 300_000, "price": 100.4},
            {"timestamp_ms": candidate_ts, "price": 100.5},
        ],
    )
    _write_jsonl(snapshot_path, [{"timestamp_ms": candidate_ts - 60_000, "depth_levels": 20}])
    _write_jsonl(delta_path, [{"timestamp_ms": candidate_ts, "u": 2}])
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10.0},
            {"timestamp_ms": candidate_ts - 3_600_000, "open": 100.0, "high": 100.2, "low": 99.95, "close": 100.1, "volume": 11.0},
            {"timestamp_ms": candidate_ts - 3_300_000, "open": 100.1, "high": 100.25, "low": 100.0, "close": 100.2, "volume": 12.0},
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.35, "high": 100.6, "low": 100.3, "close": 100.55, "volume": 14.0},
            {"timestamp_ms": candidate_ts, "open": 100.55, "high": 100.8, "low": 100.5, "close": 100.75, "volume": 15.0},
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index.json"
    _write_json(
        silver_index_path,
        _silver_index_payload(
            root=tmp_path,
            trades_path=trades_path,
            snapshot_path=snapshot_path,
            delta_path=delta_path,
            ohlcv_path=ohlcv_path,
            metadata_path=metadata_path,
            candidate_ts=candidate_ts,
        ),
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=(_candidate(engine_id="engine_b", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    trade_rows = [json.loads(line) for line in Path(manifest.raw_trade_path or "").read_text(encoding="utf-8").splitlines()]
    ohlcv_rows = [json.loads(line) for line in Path(manifest.raw_ohlcv_path or "").read_text(encoding="utf-8").splitlines()]
    assert trade_rows[0]["timestamp_ms"] >= manifest.window_start_ms
    assert ohlcv_rows[0]["timestamp_ms"] < manifest.window_start_ms


def test_raw_window_extractor_concatenates_cross_midnight_orderbook_deltas(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_752_797_100_000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2025" / "07" / "18.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2025" / "07" / "17.jsonl"
    delta_day17_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2025" / "07" / "17.jsonl"
    delta_day18_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2025" / "07" / "18.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2025" / "07" / "18.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"
    window_start_ms = candidate_ts - 300_000

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 60_000, "price": 100.0},
            {"timestamp_ms": candidate_ts, "price": 100.1},
        ],
    )
    _write_jsonl(
        snapshot_path,
        [
            {
                "timestamp_ms": window_start_ms,
                "update_id": 10,
                "bids": [[99.9, 2.0], [99.8, 1.0]],
                "asks": [[100.1, 2.0], [100.2, 1.0]],
            }
        ],
    )
    _write_jsonl(
        delta_day17_path,
        [
            {
                "timestamp_ms": window_start_ms + 1_000,
                "update_id": 11,
                "bids": [[100.0, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(
        delta_day18_path,
        [
            {
                "timestamp_ms": candidate_ts,
                "update_id": 12,
                "bids": [[100.0, 2.5]],
                "asks": [[100.2, 2.0]],
            }
        ],
    )
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.0, "high": 100.2, "low": 99.9, "close": 100.1, "volume": 10.0},
            {"timestamp_ms": candidate_ts, "open": 100.1, "high": 100.3, "low": 100.0, "close": 100.2, "volume": 11.0},
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index_cross_midnight_book.json"
    _write_json(
        silver_index_path,
        {
            "schema_version": "v1",
            "entries": [
                {
                    "source_id": "source_trades",
                    "source_root": str((tmp_path / "raw_trades").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "trades",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2025-07-18",
                    "path": str(trades_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "TRADE_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_snapshot",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2025-07-17",
                    "path": str(snapshot_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": window_start_ms,
                    "max_timestamp_ms": window_start_ms,
                    "row_count": 1,
                    "file_hash": "hash-snapshot-17",
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2025-07-17",
                    "path": str(delta_day17_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": window_start_ms + 1_000,
                    "max_timestamp_ms": window_start_ms + 1_000,
                    "row_count": 1,
                    "file_hash": "hash-delta-17",
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2025-07-18",
                    "path": str(delta_day18_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-delta-18",
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_ohlcv",
                    "source_root": str((tmp_path / "raw_ohlcv").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "ohlcv",
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "date": "2025-07-18",
                    "path": str(ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 300_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "file_hash": "hash-ohlcv-18",
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "KLINE_SCHEMA_READY",
                },
                {
                    "source_id": "source_meta",
                    "source_root": str((tmp_path / "raw_meta").resolve()),
                    "source_priority": 5,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "metadata",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2025-07-18",
                    "path": str(metadata_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-meta-18",
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "METADATA_SCHEMA_READY",
                },
            ],
        },
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows_cross_midnight_book",
        candidate_events=(_candidate(engine_id="engine_b", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    delta_rows = [
        row
        for row in _read_jsonl_any(Path(manifest.raw_book_delta_path or ""))
    ]
    assert [row["update_id"] for row in delta_rows] == [11, 12]


def test_raw_window_extractor_keeps_prewindow_deltas_needed_for_snapshot_book_reconstruction(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_000_000
    window_start_ms = candidate_ts - 300_000
    snapshot_ts = candidate_ts - 3_600_000
    prewindow_delta_ts = window_start_ms - 1_000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 600_000, "price": 100.0},
            {"timestamp_ms": candidate_ts - 300_000, "price": 100.1},
            {"timestamp_ms": candidate_ts, "price": 100.2},
        ],
    )
    _write_jsonl(
        snapshot_path,
        [
            {
                "timestamp_ms": snapshot_ts,
                "update_id": 10,
                "bids": [[100.0, 1.0]],
                "asks": [[100.1, 1.0]],
            }
        ],
    )
    _write_jsonl(
        delta_path,
        [
            {
                "timestamp_ms": prewindow_delta_ts,
                "update_id": 11,
                "bids": [],
                "asks": [[100.1, 0.0], [100.6, 1.0]],
            },
            {
                "timestamp_ms": candidate_ts,
                "update_id": 12,
                "bids": [[100.5, 1.0]],
                "asks": [],
            },
        ],
    )
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 600_000, "open": 100.0, "high": 100.2, "low": 99.9, "close": 100.1, "volume": 10.0},
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.1, "high": 100.3, "low": 100.0, "close": 100.2, "volume": 11.0},
            {"timestamp_ms": candidate_ts, "open": 100.2, "high": 100.6, "low": 100.1, "close": 100.5, "volume": 12.0},
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index_snapshot_delta.json"
    _write_json(
        silver_index_path,
        {
            "schema_version": "v1",
            "entries": [
                {
                    "source_id": "source_trades",
                    "source_root": str((tmp_path / "raw_trades").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "trades",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(trades_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 600_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 3,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "TRADE_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_snapshot",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(snapshot_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": snapshot_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                    "file_hash": "hash-snapshot-reconstruct",
                },
                {
                    "source_id": "source_book_delta",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(delta_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": prewindow_delta_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                    "file_hash": "hash-delta-reconstruct",
                },
                {
                    "source_id": "source_ohlcv",
                    "source_root": str((tmp_path / "raw_ohlcv").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "ohlcv",
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "date": "2024-04-09",
                    "path": str(ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 600_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 3,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "KLINE_SCHEMA_READY",
                    "file_hash": "hash-ohlcv-reconstruct",
                },
                {
                    "source_id": "source_meta",
                    "source_root": str((tmp_path / "raw_meta").resolve()),
                    "source_priority": 5,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "metadata",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(metadata_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "METADATA_SCHEMA_READY",
                    "file_hash": "hash-meta-reconstruct",
                },
            ],
        },
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows_snapshot_delta",
        candidate_events=(_candidate(engine_id="engine_a", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    delta_rows = [
        row
        for row in _read_jsonl_any(Path(manifest.raw_book_delta_path or ""))
    ]
    assert [row["timestamp_ms"] for row in delta_rows] == [prewindow_delta_ts, candidate_ts]

    measured_spread = build_measured_spread_payload(
        window_manifest=manifest,
        decision_timestamp_ms=candidate_ts,
    )
    assert measured_spread["status"] == "SPREAD_MEASURED_FROM_BOOK"
    assert measured_spread["best_bid"] == 100.5
    assert measured_spread["best_ask"] == 100.6


def test_engine_b_raw_window_extraction_concatenates_cross_midnight_ohlcv_entries(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_100_000
    silver_root = tmp_path / "silver"
    day0_ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "08.jsonl"
    day1_ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        day0_ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 3_900_000, "open": 99.8, "high": 100.0, "low": 99.7, "close": 99.9, "volume": 9.0},
            {"timestamp_ms": candidate_ts - 3_600_000, "open": 99.9, "high": 100.1, "low": 99.8, "close": 100.0, "volume": 10.0},
            {"timestamp_ms": candidate_ts - 3_300_000, "open": 100.0, "high": 100.2, "low": 99.9, "close": 100.1, "volume": 11.0},
        ],
    )
    _write_jsonl(
        day1_ohlcv_path,
        [
            {"timestamp_ms": candidate_ts - 300_000, "open": 100.1, "high": 100.3, "low": 100.0, "close": 100.2, "volume": 12.0},
            {"timestamp_ms": candidate_ts, "open": 100.2, "high": 100.4, "low": 100.1, "close": 100.3, "volume": 13.0},
        ],
    )
    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 300_000, "price": 100.2},
            {"timestamp_ms": candidate_ts, "price": 100.3},
        ],
    )
    _write_jsonl(snapshot_path, [{"timestamp_ms": candidate_ts - 60_000, "depth_levels": 20}])
    _write_jsonl(delta_path, [{"timestamp_ms": candidate_ts, "u": 2}])
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index.json"
    _write_json(
        silver_index_path,
        {
            "schema_version": "v1",
            "entries": [
                {
                    "source_id": "source_ohlcv_day0",
                    "source_root": str((tmp_path / "raw_c").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "ohlcv",
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "date": "2024-04-08",
                    "path": str(day0_ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 3_900_000,
                    "max_timestamp_ms": candidate_ts - 3_300_000,
                    "row_count": 3,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "KLINE_SCHEMA_READY",
                },
                {
                    "source_id": "source_ohlcv_day1",
                    "source_root": str((tmp_path / "raw_c").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "ohlcv",
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "date": "2024-04-09",
                    "path": str(day1_ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 300_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "KLINE_SCHEMA_READY",
                },
                {
                    "source_id": "source_trades",
                    "source_root": str((tmp_path / "raw_a").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "trades",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(trades_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 300_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "TRADE_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_b").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_snapshot",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(snapshot_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts - 60_000,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_book_delta",
                    "source_root": str((tmp_path / "raw_b").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(delta_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_meta",
                    "source_root": str((tmp_path / "raw_meta").resolve()),
                    "source_priority": 5,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "metadata",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(metadata_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "METADATA_SCHEMA_READY",
                },
            ],
        },
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=(_candidate(engine_id="engine_b", candidate_ts=candidate_ts),),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    ohlcv_rows = [
        json.loads(line)
        for line in Path(manifest.raw_ohlcv_path or "").read_text(encoding="utf-8").splitlines()
    ]
    assert len(ohlcv_rows) == 5
    assert ohlcv_rows[0]["timestamp_ms"] < manifest.window_start_ms
    assert ohlcv_rows[-1]["timestamp_ms"] == candidate_ts


def test_raw_window_extractor_keeps_ohlcv_post_window_for_replay_outcome_horizons(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_712_620_000_000
    bar_ms = 15 * 60 * 1000
    silver_root = tmp_path / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "15m" / "BTCUSDT" / "2024" / "04" / "09.jsonl"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"

    _write_jsonl(
        trades_path,
        [
            {"timestamp_ms": candidate_ts - 60_000, "price": 100.0},
            {"timestamp_ms": candidate_ts, "price": 100.1},
        ],
    )
    _write_jsonl(
        snapshot_path,
        [
            {
                "timestamp_ms": candidate_ts - 60_000,
                "update_id": 10,
                "bids": [[99.9, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(
        delta_path,
        [
            {
                "timestamp_ms": candidate_ts,
                "update_id": 11,
                "bids": [[100.0, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(
        ohlcv_path,
        [
            {
                "timestamp_ms": candidate_ts + offset * bar_ms,
                "open": 100.0 + offset,
                "high": 100.5 + offset,
                "low": 99.5 + offset,
                "close": 100.2 + offset,
                "volume": 10.0 + offset,
            }
            for offset in range(-4, 11)
        ],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])

    silver_index_path = tmp_path / "silver_index_post_window.json"
    _write_json(
        silver_index_path,
        {
            "schema_version": "v1",
            "entries": [
                {
                    "source_id": "source_trades",
                    "source_root": str((tmp_path / "raw_trades").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "trades",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(trades_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 2,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "TRADE_SCHEMA_READY",
                },
                {
                    "source_id": "source_book",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_snapshot",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(snapshot_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts - 60_000,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_book_delta",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(delta_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_ohlcv",
                    "source_root": str((tmp_path / "raw_ohlcv").resolve()),
                    "source_priority": 10,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "ohlcv",
                    "pair": "BTCUSDT",
                    "timeframe": "15m",
                    "date": "2024-04-09",
                    "path": str(ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 4 * bar_ms,
                    "max_timestamp_ms": candidate_ts + 10 * bar_ms,
                    "row_count": 15,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "KLINE_SCHEMA_READY",
                },
                {
                    "source_id": "source_meta",
                    "source_root": str((tmp_path / "raw_meta").resolve()),
                    "source_priority": 5,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "metadata",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(metadata_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "METADATA_SCHEMA_READY",
                },
            ],
        },
    )

    candidate = _candidate(
        engine_id="engine_d",
        candidate_ts=candidate_ts,
        timeframe="15m",
    )
    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows_post_window",
        candidate_events=(candidate,),
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    manifest = result.manifests[0]
    ohlcv_rows = [
        json.loads(line)
        for line in Path(manifest.raw_ohlcv_path or "").read_text(encoding="utf-8").splitlines()
    ]
    future_timestamps = [
        row["timestamp_ms"] for row in ohlcv_rows if row["timestamp_ms"] > candidate_ts
    ]
    assert len(future_timestamps) >= 10
    assert future_timestamps[9] == candidate_ts + 10 * bar_ms

    replay_outcome = build_replay_outcome_payload(
        candidate=candidate,
        window_manifest=manifest,
        decision_timestamp_ms=candidate_ts,
    )

    assert replay_outcome["status"] == "REPLAY_OUTCOME_RESEARCH_ONLY"
    assert replay_outcome["mfe_mae_status"] == "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE"
    assert replay_outcome["forward_return_h1"] is not None
    assert replay_outcome["forward_return_h5"] is not None
    assert replay_outcome["forward_return_h10"] is not None
