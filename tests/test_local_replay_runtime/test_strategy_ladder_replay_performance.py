from __future__ import annotations

import gzip
import json
from pathlib import Path
import time

from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRequest,
)
from local_replay_runtime.strategy_ladder_replay_performance_profile import (
    StrategyLadderReplayPerformanceProfiler,
)
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    extract_strategy_ladder_raw_windows,
)
from local_replay_runtime.strategy_ladder_runner import run_backtest_strategy_ladder
from local_replay_runtime.strategy_ladder_window_index import (
    StrategyLadderWindowIndex,
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


def _write_jsonl_gz(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _feature_row(
    *,
    pair: str = "BTCUSDT",
    engine_id: str = "engine_a",
    timestamp_ms: int = 1_714_000_000_000,
    timeframe: str = "5m",
) -> dict[str, object]:
    return {
        "timestamp_ms": timestamp_ms,
        "pair": pair,
        "timeframe": timeframe,
        "engine_id": engine_id,
        "feature_values": {"edge_score": 2.0},
        "feature_version": "fs.v1",
        "input_data_hash": f"hash-{pair}-{engine_id}",
        "method_version_hash": "method.v1",
        "source_ref": f"{pair}-{engine_id}.jsonl",
        "available_at_timestamp_ms": timestamp_ms,
        "raw_score": 0.72,
        "penalized_score": 0.71,
        "final_score": 0.70,
        "expected_edge_bps": 20.0,
        "spread_bps": 4.0,
        "slippage_bps": 3.0,
        "latency_penalty_bps": 1.0,
        "fill_ratio": 1.0,
        "book_depth_levels": 20,
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "book_depth_snapshot_count": 5,
        "book_depth_event_count": 5,
        "book_depth_missing_count": 0,
        "book_depth_staleness_status": "BOOK_DEPTH20_AVAILABLE",
        "candidate_size": 100.0,
        "final_size": 100.0,
        "gross_return_bps": 40.0,
        "allocation_fraction": 0.2,
        "min_notional": 50.0,
        "side": "buy",
        "close_price": 1.0,
    }


def _build_silver_index_fixture(root: Path, *, candidate_ts: int) -> Path:
    silver_root = root / "silver"
    trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
    snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
    delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
    ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
    metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"
    _write_jsonl_gz(trades_path, [{"timestamp_ms": candidate_ts, "price": 1.0}])
    _write_jsonl_gz(snapshot_path, [{"timestamp_ms": candidate_ts - 60_000, "depth_levels": 20}])
    _write_jsonl_gz(delta_path, [{"timestamp_ms": candidate_ts, "u": 2}])
    _write_jsonl_gz(
        ohlcv_path,
        [{"timestamp_ms": candidate_ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])
    silver_index_path = root / "silver_index.json"
    _write_json(
        silver_index_path,
        {
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
                    "date": "2023-01-01",
                    "path": str(trades_path.resolve()),
                    "storage_format": "jsonl_gz",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
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
                    "date": "2023-01-01",
                    "path": str(snapshot_path.resolve()),
                    "storage_format": "jsonl_gz",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts,
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
                    "date": "2023-01-01",
                    "path": str(delta_path.resolve()),
                    "storage_format": "jsonl_gz",
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
                    "date": "2023-01-01",
                    "path": str(ohlcv_path.resolve()),
                    "storage_format": "jsonl_gz",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
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
                    "date": "2023-01-01",
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
        },
    )
    return silver_index_path


def test_window_index_reuses_cached_silver_lookup() -> None:
    candidate_ts = 1_714_000_000_000
    entry = {
        "source_id": "source_trades",
        "source_root": "E:/raw",
        "source_priority": 10,
        "exchange": "bybit",
        "market_type": "spot",
        "data_type": "trades",
        "pair": "BTCUSDT",
        "timeframe": "",
        "date": "2023-01-01",
        "path": "E:/raw/trades.jsonl.gz",
        "storage_format": "jsonl_gz",
        "min_timestamp_ms": candidate_ts,
        "max_timestamp_ms": candidate_ts,
        "row_count": 1,
        "file_hash": "hash-trades",
        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
        "schema_status": "TRADE_SCHEMA_READY",
    }
    from local_replay_runtime.strategy_ladder_data_factory_models import StrategyLadderSilverIndexEntry

    index = StrategyLadderWindowIndex.from_silver_entries(
        (StrategyLadderSilverIndexEntry.model_validate(entry),)
    )
    first = index.lookup_silver_entries(
        pair="BTCUSDT",
        window_start_ms=candidate_ts - 1_000,
        window_end_ms=candidate_ts + 1_000,
        data_types=("trades",),
    )
    second = index.lookup_silver_entries(
        pair="BTCUSDT",
        window_start_ms=candidate_ts - 1_000,
        window_end_ms=candidate_ts + 1_000,
        data_types=("trades",),
    )
    metrics = index.metrics_snapshot()

    assert len(first) == 1
    assert second == first
    assert metrics.query_cache_hit_count == 1
    assert metrics.repeated_lookup_count == 1
    assert metrics.indexed_lookup_hit_count == 1


def test_replay_performance_profile_totals_use_profiler_span_not_phase_sum(
    tmp_path: Path,
) -> None:
    profiler = StrategyLadderReplayPerformanceProfiler(run_id="run-profiler-span")
    with profiler.phase("outer", status="OK"):
        time.sleep(0.01)
        with profiler.phase("inner", status="OK"):
            time.sleep(0.02)
    profile = profiler.write(tmp_path)

    summed_wall = sum(phase.wall_time_s for phase in profile.phases)
    assert profile.total_wall_time_s > 0.0
    assert summed_wall > profile.total_wall_time_s
    assert profile.total_io_wait_estimate_s >= 0.0


def test_window_index_scans_raw_root_once_for_repeated_queries(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"timestamp_ms": 1, "price": 1.0}])
    _write_jsonl(raw_root / "BTCUSDT" / "orderbook.jsonl", [{"timestamp_ms": 1, "depth_levels": 20}])
    _write_csv(raw_root / "BTCUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

    index = StrategyLadderWindowIndex.from_raw_root(raw_root)
    first = index.lookup_raw_paths(pair="BTCUSDT", token="trade")
    second = index.lookup_raw_paths(pair="BTCUSDT", token="trade")
    metrics = index.metrics_snapshot()

    assert len(first) == 1
    assert second == first
    assert metrics.fallback_scan_count == 1
    assert metrics.query_cache_hit_count == 1
    assert metrics.repeated_lookup_count == 1
    assert metrics.files_scanned == 3


def test_raw_window_cache_reuses_identical_silver_windows(tmp_path: Path) -> None:
    candidate_ts = 1_714_000_010_000
    silver_index_path = _build_silver_index_fixture(tmp_path, candidate_ts=candidate_ts)
    candidates = (
        StrategyLadderCandidateEvent(
            run_id="run-cache",
            candidate_id="cand-a",
            timestamp_ms=candidate_ts,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
        ),
        StrategyLadderCandidateEvent(
            run_id="run-cache",
            candidate_id="cand-b",
            timestamp_ms=candidate_ts,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_b",
            strategy_id="engine_b",
        ),
    )

    first = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=candidates,
        silver_index_path=silver_index_path,
    )
    second = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=candidates,
        silver_index_path=silver_index_path,
    )

    assert first.status == "RAW_WINDOW_READY"
    assert first.window_cache_metrics.cache_miss_count >= 3
    assert first.window_cache_metrics.reused_extraction_count >= 3
    assert (
        first.window_cache_metrics.hardlink_materialization_count
        + first.window_cache_metrics.copy_fallback_count
    ) >= 3
    assert len(first.manifests) == 2
    assert first.manifests[0].raw_trade_path == first.manifests[1].raw_trade_path
    assert first.manifests[0].raw_book_path == first.manifests[1].raw_book_path
    assert first.manifests[0].raw_book_delta_path == first.manifests[1].raw_book_delta_path
    assert first.manifests[0].raw_ohlcv_path == first.manifests[1].raw_ohlcv_path
    assert str(first.manifests[0].raw_book_delta_path).endswith(".jsonl.gz")
    assert second.window_cache_metrics.cache_hit_count >= 3
    assert second.window_cache_metrics.cache_reuse_ratio is not None
    assert second.window_cache_metrics.cache_reuse_ratio > 0.0


def test_raw_window_extraction_reuses_shared_multi_entry_orderbook_delta_windows(
    tmp_path: Path,
) -> None:
    candidate_ts = 1_714_000_010_000
    prior_day_delta_path = (
        tmp_path
        / "silver"
        / "bybit"
        / "spot"
        / "orderbook_delta"
        / "BTCUSDT"
        / "2024"
        / "04"
        / "08.jsonl"
    )
    current_day_delta_path = (
        tmp_path
        / "silver"
        / "bybit"
        / "spot"
        / "orderbook_delta"
        / "BTCUSDT"
        / "2024"
        / "04"
        / "09.jsonl"
    )
    snapshot_path = (
        tmp_path
        / "silver"
        / "bybit"
        / "spot"
        / "orderbook_snapshot"
        / "BTCUSDT"
        / "2024"
        / "04"
        / "09.jsonl"
    )
    trades_path = (
        tmp_path
        / "silver"
        / "bybit"
        / "spot"
        / "trades"
        / "BTCUSDT"
        / "2024"
        / "04"
        / "09.jsonl"
    )
    ohlcv_path = (
        tmp_path
        / "silver"
        / "bybit"
        / "spot"
        / "ohlcv"
        / "5m"
        / "BTCUSDT"
        / "2024"
        / "04"
        / "09.jsonl"
    )
    metadata_path = tmp_path / "silver" / "metadata" / "symbol_filters.jsonl"
    _write_jsonl(
        prior_day_delta_path,
        [{"timestamp_ms": candidate_ts - 60_000, "u": 1}],
    )
    _write_jsonl(
        current_day_delta_path,
        [{"timestamp_ms": candidate_ts, "u": 2}],
    )
    _write_jsonl(
        snapshot_path,
        [{"timestamp_ms": candidate_ts - 120_000, "depth_levels": 20}],
    )
    _write_jsonl(trades_path, [{"timestamp_ms": candidate_ts, "price": 1.0}])
    _write_jsonl(
        ohlcv_path,
        [{"timestamp_ms": candidate_ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}],
    )
    _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])
    silver_index_path = tmp_path / "silver_index.json"
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
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-trades",
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "TRADE_SCHEMA_READY",
                },
                {
                    "source_id": "source_snapshot",
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
                    "min_timestamp_ms": candidate_ts - 120_000,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-snapshot",
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_delta_prev",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-08",
                    "path": str(prior_day_delta_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts - 60_000,
                    "max_timestamp_ms": candidate_ts - 60_000,
                    "row_count": 1,
                    "file_hash": "hash-delta-prev",
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "schema_status": "ORDERBOOK_SCHEMA_READY",
                },
                {
                    "source_id": "source_delta_curr",
                    "source_root": str((tmp_path / "raw_book").resolve()),
                    "source_priority": 20,
                    "exchange": "bybit",
                    "market_type": "spot",
                    "data_type": "orderbook_delta",
                    "pair": "BTCUSDT",
                    "timeframe": "",
                    "date": "2024-04-09",
                    "path": str(current_day_delta_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-delta-curr",
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
                    "date": "2024-04-09",
                    "path": str(ohlcv_path.resolve()),
                    "storage_format": "jsonl",
                    "min_timestamp_ms": candidate_ts,
                    "max_timestamp_ms": candidate_ts,
                    "row_count": 1,
                    "file_hash": "hash-ohlcv",
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
                    "file_hash": "hash-meta",
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                    "schema_status": "METADATA_SCHEMA_READY",
                },
            ],
        },
    )
    candidates = (
        StrategyLadderCandidateEvent(
            run_id="run-shared-delta",
            candidate_id="cand-a",
            timestamp_ms=candidate_ts,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
        ),
        StrategyLadderCandidateEvent(
            run_id="run-shared-delta",
            candidate_id="cand-b",
            timestamp_ms=candidate_ts,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_b",
            strategy_id="engine_b",
        ),
    )

    result = extract_strategy_ladder_raw_windows(
        tmp_path / "raw_windows",
        candidate_events=candidates,
        silver_index_path=silver_index_path,
    )

    assert result.status == "RAW_WINDOW_READY"
    assert len(result.manifests) == 2
    assert result.manifests[0].raw_book_delta_path == result.manifests[1].raw_book_delta_path
    assert "_shared_windows" in str(result.manifests[0].raw_book_delta_path)
    assert "orderbook_delta" in str(result.manifests[0].raw_book_delta_path)
    assert not list((tmp_path / "raw_windows" / "BTCUSDT").rglob("orderbook_delta.jsonl"))
    delta_rows = [
        json.loads(line)
        for line in Path(str(result.manifests[0].raw_book_delta_path)).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [row["timestamp_ms"] for row in delta_rows] == [candidate_ts - 60_000, candidate_ts]


def test_strategy_ladder_runner_writes_replay_performance_profile(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    feature_root = input_root / "feature_store"
    raw_root = input_root / "raw"
    output_root = tmp_path / "output"
    candidate_timestamp_ms = 1_714_000_000_000
    candidate_events_path = input_root / "candidate_events.jsonl"
    _write_jsonl(
        candidate_events_path,
        [
            StrategyLadderCandidateEvent(
                run_id="run-perf-profile",
                candidate_id="cand-perf",
                timestamp_ms=candidate_timestamp_ms,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_a",
                strategy_id="engine_a",
                compatibility_payload=_feature_row(timestamp_ms=candidate_timestamp_ms),
            ).model_dump(mode="json")
        ],
    )
    _write_jsonl(feature_root / "features.jsonl", [_feature_row(timestamp_ms=candidate_timestamp_ms)])
    _write_json(raw_root / "BTCUSDT" / "book_depth20.json", {"depth_levels": 20})
    _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"timestamp_ms": candidate_timestamp_ms, "price": 1.0}])
    _write_csv(raw_root / "BTCUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

    result = run_backtest_strategy_ladder(
        StrategyLadderRequest(
            run_id="run-perf-profile",
            input_root=input_root,
            feature_store_root=feature_root,
            raw_root=raw_root,
            output_root=output_root,
            pairs=("BTCUSDT",),
            engines=("engine_a",),
            timeframes=("5m",),
            start="2024-04-24",
            end="2024-04-24",
            candidate_events_path=candidate_events_path,
            detailed_only=True,
            candidate_sample_cap=1,
            engine_native_sample_size=1,
            small_scope_enabled=True,
            full_scan_enabled=False,
            no_full_scan_enabled=True,
        )
    )
    profile_path = result.run_manifest.output_root
    performance_profile_path = Path(profile_path) / "replay_performance_profile.json"
    payload = json.loads(performance_profile_path.read_text(encoding="utf-8"))

    assert performance_profile_path.is_file()
    assert payload["status"] == "REPLAY_PERFORMANCE_PROFILE_READY"
    assert any(phase["phase_name"] == "raw_window_extraction" for phase in payload["phases"])
    assert any(phase["phase_name"] == "replay_orchestration" for phase in payload["phases"])
    assert any(phase["phase_name"] == "matrix_generation" for phase in payload["phases"])
    assert "shared_payload_build_seconds" in payload
    assert "engine_dataset_build_seconds" in payload
    assert "evaluate_replay_execution_seconds" in payload
    assert "replay_evidence_seconds" in payload
    assert "by_bucket_write_seconds" in payload
    assert "candidate_wrapper_write_seconds" in payload
    assert "cache_hits_book_state" in payload
    assert "cache_misses_book_state" in payload
    assert "cache_hits_ohlcv" in payload
    assert "cache_misses_ohlcv" in payload
