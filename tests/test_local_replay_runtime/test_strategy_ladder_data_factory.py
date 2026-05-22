from __future__ import annotations

from urllib.parse import parse_qs, urlparse
import gzip
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from uuid import uuid4
import zipfile

from local_replay_runtime.bybit_historical_metadata import (
    fetch_bybit_spot_metadata_cache,
)
from local_replay_runtime import strategy_ladder_data_factory as data_factory_module
from local_replay_runtime.strategy_ladder_data_factory import (
    classify_raw_file,
    run_strategy_ladder_data_factory,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderRawSource,
    StrategyLadderDataFactoryRequest,
    StrategyLadderSilverIndexEntry,
)
from local_replay_runtime.strategy_ladder_raw_sources import (
    load_raw_source_manifest,
    normalize_raw_root_inputs,
    resolve_strategy_ladder_raw_sources,
)
from tests.support_paths import make_repo_scratch_dir


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
    if path.name.endswith(".jsonl.gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _write_gzip_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write("\n".join([header, *rows]) + "\n")


def _write_zip_text(path: Path, inner_name: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(inner_name, text)


def _write_symbol_metadata_csv(path: Path, rows: list[str]) -> None:
    _write_csv(
        path,
        "venue,exchange,market_type,symbol,base_coin,quote_coin,status,tick_size,qty_step,min_order_qty,min_notional,maker_fee_rate,taker_fee_rate,fee_source,metadata_purpose,proof_level,source,fetched_at_utc,raw_payload_hash,metadata_temporal_status",
        rows,
    )


def _book_levels(side: str) -> list[list[str]]:
    base = 1.0 if side == "bid" else 1.1
    return [
        [f"{base - index * 0.001 if side == 'bid' else base + index * 0.001:.6f}", f"{10 + index:.6f}"]
        for index in range(20)
    ]


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_data_factory_tests", label)


_ORDERBOOK_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "orderbook" / "BTCUSDT"
)


def _copy_orderbook_fixture(target_root: Path, fixture_name: str) -> Path:
    source = _ORDERBOOK_FIXTURE_ROOT / fixture_name
    destination = target_root / "ordre book part 1" / "BTCUSDT" / fixture_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _write_btcusdt_kline_fixture(raw_root: Path) -> None:
    _write_csv(
        raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
        "startTime,open,high,low,close,volume,turnover",
        [
            "1745884800000,63000,63100,62900,63050,10,630500",
            "1745884860000,63050,63120,63020,63080,9,567720",
        ],
    )


def test_multi_source_manifest_and_root_dedup_are_supported() -> None:
    scratch = _scratch_dir("raw_source_manifest")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_a = scratch / "raw_a"
        raw_b = scratch / "raw_b"
        raw_a.mkdir(parents=True, exist_ok=True)
        raw_b.mkdir(parents=True, exist_ok=True)
        manifest_path = scratch / "raw_sources.json"
        _write_json(
            manifest_path,
            {
                "schema_version": "v1",
                "sources": [
                    {
                        "source_id": "a",
                        "root": str(raw_a),
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_types": ["trades", "klines"],
                        "priority": 10,
                        "enabled": True,
                    },
                    {
                        "source_id": "b",
                        "root": str(scratch / "missing_disabled"),
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_types": ["orderbook_snapshot"],
                        "priority": 20,
                        "enabled": False,
                    },
                ],
            },
        )

        roots = normalize_raw_root_inputs(
            raw_root=raw_a,
            raw_roots=(raw_a,),
            raw_roots_csv=f"{raw_a},{raw_b}",
        )

        loaded = load_raw_source_manifest(manifest_path)
        report = resolve_strategy_ladder_raw_sources(
            raw_roots=roots,
            raw_source_manifest_path=manifest_path,
            dry_run=True,
        )

        assert len(roots) == 2
        assert len(loaded) == 2
        assert report.raw_source_status == "RAW_SOURCE_READY"
        assert report.raw_source_typing_status in {
            "RAW_SOURCE_TYPED_READY",
            "RAW_SOURCE_TYPE_INFERRED",
        }
        assert {item.source_id for item in report.sources} == {"a", "b"}
        assert any(item.status == "RAW_SOURCE_DISABLED" for item in report.sources)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_normalizes_inputs_builds_gold_and_keeps_dynamic_pair_universe() -> None:
    scratch = _scratch_dir("data_factory_success")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "ADAUSDT_2023-01-01.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1672531200000,0.245,100,buy",
                "2,1672531260000,0.246,110,sell",
            ],
        )
        _write_csv(
            raw_root / "klines" / "ADAUSDT_1_2023-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1672531200000,0.245,0.247,0.244,0.246,1000,246",
                "1672531260000,0.246,0.248,0.245,0.247,1200,296.4",
            ],
        )
        _write_jsonl(
            raw_root / "orderbook" / "snapshot" / "ADAUSDT_2023-01-01.data",
            [
                {
                    "topic": "orderbook.200.ADAUSDT",
                    "type": "snapshot",
                    "timestamp_ms": 1672531200000,
                    "seq": 1,
                    "data": {"b": _book_levels("bid"), "a": _book_levels("ask")},
                },
            ],
        )
        _write_jsonl(
            raw_root / "orderbook" / "delta" / "ADAUSDT_2023-01-01.data",
            [
                {
                    "topic": "orderbook.200.ADAUSDT",
                    "type": "delta",
                    "timestamp_ms": 1672531260000,
                    "u": 2,
                    "data": {"b": [["1.000000", "15.000000"]], "a": [["1.100000", "0"]]},
                },
            ],
        )
        _write_csv(
            raw_root / "metadata" / "symbol_filters.csv",
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["ADAUSDT,10,0.0001,0.1,0.001,0.0015"],
        )

        report_root = scratch / "factory"
        silver_root = report_root / "silver"
        gold_root = report_root / "gold"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-ok",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=silver_root,
                gold_root=gold_root,
                pairs=("ADAUSDT",),
                # Patch 6 batch 1 — non-dry-run requires explicit date range
                # or allow_broad_run; this fixture is fixed at 2023-01-01.
                start="2023-01-01",
                end="2023-01-01",
            )
        )

        gold_rows = []
        for path in result.gold_feature_manifest.feature_paths:
            gold_rows.extend(_read_jsonl_any(Path(path)))

        assert result.manifest.data_factory_status == "DATA_FACTORY_READY"
        assert result.pair_universe_report.pair_universe_status == "PAIR_UNIVERSE_READY"
        assert result.pair_universe_report.available_pairs == ("ADAUSDT",)
        assert result.manifest.trade_schema_status == "TRADE_SCHEMA_READY"
        assert result.manifest.kline_schema_status == "KLINE_SCHEMA_READY"
        assert result.manifest.silver_index_status == "SILVER_INDEX_READY"
        assert result.gold_feature_manifest.feature_row_count > 0
        assert any(entry.data_type == "trades" for entry in result.silver_index)
        assert any(entry.data_type == "ohlcv" for entry in result.silver_index)
        assert any(entry.data_type == "orderbook_snapshot" for entry in result.silver_index)
        assert any(entry.data_type == "orderbook_delta" for entry in result.silver_index)
        assert any(entry.data_type == "metadata" for entry in result.silver_index)
        assert gold_rows[0]["candidate_data_source_label"] == "ORDERBOOK_AWARE_DISCOVERY"
        assert gold_rows[0]["trade_feature_status"] == "TRADE_FEATURE_STATUS_READY"
        assert gold_rows[0]["orderbook_feature_status"] == "ORDERBOOK_FEATURE_STATUS_READY"
        assert [row["timestamp_ms"] for row in gold_rows] == sorted(row["timestamp_ms"] for row in gold_rows)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_accepts_partial_day_ohlcv_via_severity_classifier_2026_05_21() -> None:
    """Patch D1+D2 (2026-05-21) — severity classifier OHLCV temporal completeness.

    Raw Bybit L: dumps sont systématiquement tronqués à 1000 rows max
    (limite GET endpoint non-paginé). 1m=1000/1440=69%, 10m=100/144=69% :
    research-acceptable via PARTIAL_DAY_ACCEPTED, plus de fail-close.
    """
    scratch = _scratch_dir("data_factory_ohlcv_temporal_gate")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-01-01.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1735689600000,94000,0.01,buy",
                "2,1735689660000,94010,0.02,sell",
            ],
        )
        rows_1m = [
            f"{1735689600000 + index * 60_000},94000,94100,93900,94010,10,940100"
            for index in range(1000)
        ]
        rows_10m = [
            f"{1735689600000 + index * 600_000},94000,94100,93900,94010,10,940100"
            for index in range(100)
        ]
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            rows_1m,
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_10_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            rows_10m,
        )
        _write_jsonl(
            raw_root / "orderbook" / "snapshot" / "BTCUSDT_2025-01-01.data",
            [
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "type": "snapshot",
                    "timestamp_ms": 1735689600000,
                    "seq": 1,
                    "data": {"b": _book_levels("bid"), "a": _book_levels("ask")},
                },
            ],
        )
        _write_jsonl(
            raw_root / "orderbook" / "delta" / "BTCUSDT_2025-01-01.data",
            [
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "type": "delta",
                    "timestamp_ms": 1735689660000,
                    "u": 2,
                    "data": {"b": [["94000.0", "1.0"]], "a": [["94010.0", "0"]]},
                },
            ],
        )
        _write_csv(
            raw_root / "metadata" / "symbol_filters.csv",
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["BTCUSDT,10,0.10,0.001,0.001,0.001"],
        )

        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-ohlcv-gate",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                timeframes=("1m", "10m"),
                start="2025-01-01",
                end="2025-01-01",
            )
        )

        # Avec severity classifier (D1+D2 patch), 69% rows = research-acceptable
        # → data_factory_status NE PLUS BLOCKED par OHLCV temporal seul
        assert result.manifest.data_factory_status != "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS"
        # Statut OHLCV temporal devient PARTIAL_DAY_ACCEPTED (recherche-acceptable)
        assert (
            result.manifest.ohlcv_temporal_completeness_status
            == "OHLCV_TEMPORAL_COMPLETENESS_PARTIAL_DAY_ACCEPTED"
        )
        # blocked_entry_count = 0 car aucun entry n'est hard-fail (juste partial)
        assert result.manifest.ohlcv_temporal_blocked_entry_count == 0
        assert result.manifest.ohlcv_temporal_critical_timeframes == ("1m", "10m")
        # Nouveaux blocker codes : PARTIAL_DAY_ACCEPTED (research-acceptable)
        assert "OHLCV_1M_PARTIAL_DAY_ACCEPTED" in result.manifest.blocker_codes
        assert "OHLCV_10M_PARTIAL_DAY_ACCEPTED" in result.manifest.blocker_codes
        # Anciens codes _BLOCKED ne doivent PAS être présents
        assert "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED" not in result.manifest.blocker_codes
        assert "OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED" not in result.manifest.blocker_codes
        assert result.data_quality_report.raw_source_typing_status in {
            "RAW_SOURCE_TYPED_READY",
            "RAW_SOURCE_TYPE_INFERRED",
            "RAW_SOURCE_TYPE_AMBIGUOUS",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_still_fail_closes_when_ohlcv_below_research_threshold_2026_05_21() -> None:
    """Patch D1+D2 (2026-05-21) — sous le seuil 65% research, on reste BLOCKED.

    Garantit que le severity classifier ne dégrade PAS l'enforcement pour les
    cas vraiment cassés. 500/1440 = 35% → BLOCKED (sous le floor research 65%).
    """
    scratch = _scratch_dir("data_factory_ohlcv_below_research_threshold")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-01-01.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1735689600000,94000,0.01,buy",
                "2,1735689660000,94010,0.02,sell",
            ],
        )
        # 500/1440 = 35% < 65% threshold → BLOCKED
        rows_1m = [
            f"{1735689600000 + index * 60_000},94000,94100,93900,94010,10,940100"
            for index in range(500)
        ]
        # 50/144 = 35% < 65% threshold → BLOCKED
        rows_10m = [
            f"{1735689600000 + index * 600_000},94000,94100,93900,94010,10,940100"
            for index in range(50)
        ]
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            rows_1m,
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_10_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            rows_10m,
        )
        _write_jsonl(
            raw_root / "orderbook" / "snapshot" / "BTCUSDT_2025-01-01.data",
            [
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "type": "snapshot",
                    "timestamp_ms": 1735689600000,
                    "seq": 1,
                    "data": {"b": _book_levels("bid"), "a": _book_levels("ask")},
                },
            ],
        )
        _write_jsonl(
            raw_root / "orderbook" / "delta" / "BTCUSDT_2025-01-01.data",
            [
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "type": "delta",
                    "timestamp_ms": 1735689660000,
                    "u": 2,
                    "data": {"b": [["94000.0", "1.0"]], "a": [["94010.0", "0"]]},
                },
            ],
        )
        _write_csv(
            raw_root / "metadata" / "symbol_filters.csv",
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["BTCUSDT,10,0.10,0.001,0.001,0.001"],
        )

        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-ohlcv-below-floor",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                timeframes=("1m", "10m"),
                start="2025-01-01",
                end="2025-01-01",
            )
        )

        assert (
            result.manifest.data_factory_status
            == "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS"
        )
        assert (
            result.manifest.ohlcv_temporal_completeness_status
            == "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED"
        )
        assert result.manifest.ohlcv_temporal_blocked_entry_count == 2
        assert "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED" in result.manifest.blocker_codes
        assert "OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED" in result.manifest.blocker_codes
        assert "OHLCV_1M_PARTIAL_DAY_ACCEPTED" not in result.manifest.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_filters_timeframes_limits_gold_and_defers_trade_slippage(
    monkeypatch,
) -> None:
    scratch = _scratch_dir("data_factory_timeframe_limit")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-01-01.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1735689600000,94000,0.01,buy",
                "2,1735689660000,94010,0.02,sell",
            ],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_5_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1735689600000,94000,94100,93900,94010,10,940100",
                "1735689900000,94010,94110,93910,94020,11,1034220",
                "1735690200000,94020,94120,93920,94030,12,1128360",
                "1735690500000,94030,94130,93930,94040,13,1222520",
                "1735690800000,94040,94140,93940,94050,14,1316700",
            ],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_10_2025-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1735689600000,94000,94100,93900,94010,10,940100",
                "1735690200000,94010,94110,93910,94020,11,1034220",
            ],
        )
        calls: list[dict[str, object]] = []

        def _fake_compute_economic_provenance(**kwargs):
            calls.append(kwargs)
            assert kwargs["raw_trade_path"] is not None
            # Audit 2026-05-14 P3-B : le flag est passe a True par
            # data_factory pour activer la mesure Kyle lambda canonique.
            # Le warning "SLIPPAGE_DEFERRED_TO_RAW_WINDOW_REPLAY" devient
            # obsolete — la mesure se fait au feature_row time.
            assert kwargs["measure_slippage_from_trades"] is True
            return SimpleNamespace(
                expected_edge_bps=5.0,
                expected_edge_provenance="DEFAULT_TO_CALIBRATE",
                aggregated_provenance="PARTIALLY_MEASURED",
                measurement_warnings=(),
                spread_bps=0.0,
                # Audit 2026-05-14 P3-A : tier-aware spread_provenance dans le
                # contrat EconomicProvenance ; le fake doit le fournir aussi.
                spread_provenance="DEFAULT_BY_BOOK_STATUS",
                slippage_bps=2.0,
                # Audit 2026-05-14 P3-B : tier-aware slippage_provenance.
                # Fake retourne DEFAULT_TO_CALIBRATE (Kyle echoue dans test
                # synthetique sans trade tape suffisant).
                slippage_provenance="DEFAULT_TO_CALIBRATE",
                latency_penalty_bps=1.0,
            )

        monkeypatch.setattr(
            data_factory_module,
            "compute_economic_provenance",
            _fake_compute_economic_provenance,
        )

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-timeframe-limit",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("5m",),
                start="2025-01-01",
                end="2025-01-01",
                use_measured_economic_provenance=True,
                small_scope=True,
                max_gold_feature_rows=3,
            )
        )

        assert result.gold_feature_manifest.feature_row_count == 3
        assert len(calls) == 3
        assert all("features_5m" in path for path in result.gold_feature_manifest.feature_paths)
        assert not any("features_10m" in path for path in result.gold_feature_manifest.feature_paths)
        gold_rows = [
            row
            for path in result.gold_feature_manifest.feature_paths
            for row in _read_jsonl_any(Path(path))
        ]
        assert len(gold_rows) == 3
        assert {row["timeframe"] for row in gold_rows} == {"5m"}
        # Patch 2026-05-15 (timeframe propagation audit) — the silent 10m
        # prune must now be surfaced as an explicit reason code on the
        # manifest. The pre-existing assertions above are kept verbatim so
        # the legacy behaviour stays validated; the new assertions below
        # only ADD coverage on the visibility fields.
        gold_manifest = result.gold_feature_manifest
        assert "5m" in gold_manifest.silver_timeframes_detected
        assert "10m" in gold_manifest.silver_timeframes_detected
        assert gold_manifest.gold_timeframes_generated == ("5m",)
        assert "10m" in gold_manifest.timeframes_pruned
        assert (
            gold_manifest.pruning_reason_by_timeframe.get("10m")
            == "TIMEFRAME_PRUNED_NOT_REQUESTED"
        )
        assert "TIMEFRAME_PRUNED_NOT_REQUESTED" in gold_manifest.blocker_codes
        assert gold_manifest.timeframe_feature_row_count.get("5m") == 3
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_gold_features_do_not_leak_orderbook_depth_across_dates() -> None:
    scratch = _scratch_dir("gold_feature_orderbook_date_scope")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        silver_root = scratch / "silver"
        gold_root = scratch / "gold"
        trade_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2025" / "05" / "25.jsonl"
        kline_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2025" / "05" / "25.jsonl"
        book_snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2025" / "05" / "26.jsonl"
        book_delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2025" / "05" / "26.jsonl"
        metadata_path = silver_root / "metadata" / "symbol_metadata.jsonl"
        _write_jsonl(trade_path, [{"timestamp_ms": 1748131201000, "price": 107942.0, "quantity": 0.1}])
        _write_jsonl(
            kline_path,
            [
                {
                    "timestamp_ms": 1748131200000,
                    "open": 107900.0,
                    "high": 108000.0,
                    "low": 107850.0,
                    "close": 107942.0,
                    "volume": 10.0,
                }
            ],
        )
        _write_jsonl(book_snapshot_path, [{"timestamp_ms": 1748217601000, "depth_levels": 20}])
        _write_jsonl(book_delta_path, [{"timestamp_ms": 1748217602000, "u": 1}])
        _write_jsonl(
            metadata_path,
            [{"pair": "BTCUSDT", "tick_size": 0.1, "min_notional": 5.0}],
        )
        request = StrategyLadderDataFactoryRequest(
            run_id="df-no-orderbook-leak",
            input_root=scratch,
            raw_roots=(scratch,),
            silver_root=silver_root,
            gold_root=gold_root,
            pairs=("BTCUSDT",),
            start="2025-05-25",
            end="2025-05-26",
        )
        index_entries = (
            StrategyLadderSilverIndexEntry(
                source_id="trades_25",
                source_root=str(scratch.resolve()),
                source_priority=10,
                exchange="bybit",
                market_type="spot",
                data_type="trades",
                pair="BTCUSDT",
                timeframe="",
                date="2025-05-25",
                path=str(trade_path.resolve()),
                storage_format="jsonl",
                min_timestamp_ms=1748131201000,
                max_timestamp_ms=1748131201000,
                row_count=1,
                file_hash="hash-trades-25",
                depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                schema_status="TRADE_SCHEMA_READY",
            ),
            StrategyLadderSilverIndexEntry(
                source_id="kline_25",
                source_root=str(scratch.resolve()),
                source_priority=10,
                exchange="bybit",
                market_type="spot",
                data_type="ohlcv",
                pair="BTCUSDT",
                timeframe="5m",
                date="2025-05-25",
                path=str(kline_path.resolve()),
                storage_format="jsonl",
                min_timestamp_ms=1748131200000,
                max_timestamp_ms=1748131200000,
                row_count=1,
                file_hash="hash-kline-25",
                depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                schema_status="KLINE_SCHEMA_READY",
            ),
            StrategyLadderSilverIndexEntry(
                source_id="book_snapshot_26",
                source_root=str(scratch.resolve()),
                source_priority=10,
                exchange="bybit",
                market_type="spot",
                data_type="orderbook_snapshot",
                pair="BTCUSDT",
                timeframe="",
                date="2025-05-26",
                path=str(book_snapshot_path.resolve()),
                storage_format="jsonl",
                min_timestamp_ms=1748217601000,
                max_timestamp_ms=1748217601000,
                row_count=1,
                file_hash="hash-book-snapshot-26",
                depth_source_status="BOOK_DEPTH20_AVAILABLE",
                schema_status="ORDERBOOK_SCHEMA_READY",
            ),
            StrategyLadderSilverIndexEntry(
                source_id="book_delta_26",
                source_root=str(scratch.resolve()),
                source_priority=10,
                exchange="bybit",
                market_type="spot",
                data_type="orderbook_delta",
                pair="BTCUSDT",
                timeframe="",
                date="2025-05-26",
                path=str(book_delta_path.resolve()),
                storage_format="jsonl",
                min_timestamp_ms=1748217602000,
                max_timestamp_ms=1748217602000,
                row_count=1,
                file_hash="hash-book-delta-26",
                depth_source_status="BOOK_DEPTH20_AVAILABLE",
                schema_status="ORDERBOOK_SCHEMA_READY",
            ),
            StrategyLadderSilverIndexEntry(
                source_id="metadata",
                source_root=str(scratch.resolve()),
                source_priority=1,
                exchange="bybit",
                market_type="spot",
                data_type="metadata",
                pair="BTCUSDT",
                timeframe="",
                date="",
                path=str(metadata_path.resolve()),
                storage_format="jsonl",
                min_timestamp_ms=None,
                max_timestamp_ms=None,
                row_count=1,
                file_hash="hash-metadata",
                depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                schema_status="METADATA_SCHEMA_READY",
            ),
        )

        manifest = data_factory_module._write_gold_features(
            request=request,
            index_entries=index_entries,
            available_pairs=("BTCUSDT",),
        )

        gold_rows = []
        for path in manifest.feature_paths:
            gold_rows.extend(_read_jsonl_any(Path(path)))

        assert manifest.feature_row_count == 1
        assert gold_rows[0]["book_depth_source_status"] == "BOOK_DEPTH_NOT_PROVEN"
        assert gold_rows[0]["orderbook_feature_status"] == "ORDERBOOK_FEATURE_STATUS_NOT_PROVEN"
        assert gold_rows[0]["candidate_data_source_label"] == "TRADE_KLINE_DISCOVERY"
        assert gold_rows[0]["feature_sources_used"] == ["trades", "klines", "metadata"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_blocks_ambiguous_timestamp_units() -> None:
    scratch = _scratch_dir("data_factory_ambiguous_units")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2023-01-01.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1672531200,16000,0.1,buy",
                "2,1672531260000,16010,0.2,sell",
            ],
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-ambiguous",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
            )
        )

        assert result.data_quality_report.timestamp_unit_status == "TIMESTAMP_UNIT_AMBIGUOUS"
        assert result.manifest.trade_schema_status == "TRADE_SCHEMA_INVALID_TIMESTAMP"
        assert result.manifest.data_factory_status == "DATA_FACTORY_BLOCKED_BY_SCHEMA"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_scans_flat_generic_root_without_year_directories() -> None:
    scratch = _scratch_dir("data_factory_flat_generic_root")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "flat_source"
        _write_gzip_csv(
            raw_root / "BTCUSDT_2023-01-01.csv.gz",
            "id,timestamp,price,volume,side",
            [
                "1,1672531200000,16500,0.1,buy",
                "2,1672531260000,16510,0.2,sell",
            ],
        )
        _write_csv(
            raw_root / "BTCUSDT_1_2023-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1672531200000,16500,16520,16490,16510,10,165100",
                "1672531260000,16510,16530,16500,16520,8,132160",
            ],
        )

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-flat-generic-root",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                start="2023-01-01",
                end="2023-01-01",
            )
        )

        assert result.raw_source_report.raw_source_typing_status == "RAW_SOURCE_TYPE_AMBIGUOUS"
        assert result.manifest.data_factory_status == "DATA_FACTORY_READY"
        assert any(entry.data_type == "trades" for entry in result.silver_index)
        assert any(entry.data_type == "ohlcv" for entry in result.silver_index)
        assert result.pair_universe_report.available_pairs == ("BTCUSDT",)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_dynamic_pair_universe_accepts_partial_current_crypto_scope() -> None:
    scratch = _scratch_dir("data_factory_partial_universe")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        for pair in ("ADAUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "LTCUSDT"):
            _write_csv(
                raw_root / "trades" / f"{pair}_2023-01-01.csv",
                "id,timestamp,price,volume,side",
                ["1,1672531200000,1,1,buy"],
            )
            _write_csv(
                raw_root / "klines" / f"{pair}_1_2023-01-01.csv",
                "startTime,open,high,low,close,volume,turnover",
                ["1672531200000,1,1,1,1,1,1"],
            )

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-seven-pairs",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("ADAUSDT", "BTCUSDT", "MATICUSDT"),
            )
        )

        assert result.pair_universe_report.available_pairs == ("ADAUSDT", "BTCUSDT")
        assert result.pair_universe_report.missing_pairs == ("MATICUSDT",)
        assert result.pair_universe_report.pair_universe_status == "PAIR_UNIVERSE_PARTIAL"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_data_file_is_classified_by_content_and_pair_is_inferred() -> None:
    scratch = _scratch_dir("orderbook_classification")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        path = _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200.data")
        classification = classify_raw_file(
            source=StrategyLadderRawSource(
                source_id="orderbook_source",
                root=str(raw_root),
                exchange="bybit",
                market_type="spot",
                data_types=("orderbook",),
                priority=10,
                enabled=True,
                status="RAW_SOURCE_READY",
            ),
            path=path,
        )

        assert classification.classification_status == "RAW_FILE_CLASSIFIED_ORDERBOOK"
        assert classification.data_type == "orderbook"
        assert classification.pair == "BTCUSDT"
        assert classification.date == "2025-04-29"
        assert classification.schema_status == "ORDERBOOK_SCHEMA_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_accepts_single_file_raw_root_for_orderbook() -> None:
    scratch = _scratch_dir("orderbook_single_file_root")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        path = _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200.data")
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-single-file-root",
                input_root=report_root,
                raw_roots=(path,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
                start="2025-04-29",
                end="2025-04-29",
            )
        )

        assert result.manifest.data_factory_status == "DATA_FACTORY_READY"
        assert any(
            entry.data_type == "orderbook_snapshot" for entry in result.silver_index
        )
        assert any(
            entry.data_type == "orderbook_delta" for entry in result.silver_index
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_discovers_data_files_and_writes_orderbook_snapshot_and_delta_entries() -> None:
    scratch = _scratch_dir("orderbook_data_factory_valid")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200.data")
        _write_btcusdt_kline_fixture(raw_root)
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-valid",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook", "klines"),
                start="2025-04-29",
                end="2025-04-30",
            )
        )

        pair_row = next(item for item in result.pair_universe_report.pair_data_coverage if item.pair == "BTCUSDT")
        snapshot_entry = next(item for item in result.silver_index if item.data_type == "orderbook_snapshot")
        delta_entry = next(item for item in result.silver_index if item.data_type == "orderbook_delta")
        snapshot_rows = [
            json.loads(line)
            for line in Path(snapshot_entry.path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        delta_rows = [
            json.loads(line)
            for line in Path(delta_entry.path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert result.data_quality_report.orderbook_schema_status == "ORDERBOOK_SCHEMA_READY"
        assert pair_row.has_orderbook is True
        assert pair_row.orderbook_date_count > 0
        assert snapshot_entry.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
        assert delta_entry.depth_source_status == "BOOK_DEPTH_NOT_PROVEN"
        assert snapshot_rows[0]["pair"] == "BTCUSDT"
        assert snapshot_rows[0]["event_type"] == "snapshot"
        assert delta_rows[0]["event_type"] == "delta"
        assert any(row["seq"] == 101 for row in delta_rows)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_dry_run_reports_discovery_without_fake_silver_outputs() -> None:
    scratch = _scratch_dir("orderbook_dry_run")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200.data")
        _write_btcusdt_kline_fixture(raw_root)
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-dry",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook", "klines"),
                dry_run=True,
            )
        )

        snapshot_entry = next(item for item in result.silver_index if item.data_type == "orderbook_snapshot")
        assert result.data_quality_report.orderbook_schema_status == "ORDERBOOK_SCHEMA_READY"
        assert snapshot_entry.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
        assert "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN" not in result.data_quality_report.blocker_codes
        assert any(entry.data_type == "orderbook_snapshot" for entry in result.silver_index)
        assert any(entry.data_type == "orderbook_delta" for entry in result.silver_index)
        assert not (report_root / "silver" / "bybit" / "spot" / "orderbook_snapshot").exists()
        assert result.manifest.silver_index_status == "SILVER_INDEX_NOT_READY"
        assert result.gold_feature_manifest.feature_groups_declared
        assert not result.gold_feature_manifest.feature_groups_generated
        assert not result.gold_feature_manifest.feature_groups_ready
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_delta_only_file_is_not_depth20_and_surfaces_snapshot_blocker() -> None:
    scratch = _scratch_dir("orderbook_delta_only")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200_delta_only.data")
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-delta-only",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
            )
        )

        delta_entry = next(item for item in result.silver_index if item.data_type == "orderbook_delta")
        assert delta_entry.depth_source_status == "BOOK_DEPTH_NOT_PROVEN"
        assert "ORDERBOOK_SNAPSHOT_NOT_FOUND" in result.data_quality_report.blocker_codes
        assert "ORDERBOOK_DELTA_ONLY_NOT_DEPTH_PROOF" in result.data_quality_report.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_sequence_gap_is_detected_and_not_promotion_grade() -> None:
    scratch = _scratch_dir("orderbook_seq_gap")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200_seq_gap.data")
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-seq-gap",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
            )
        )

        snapshot_entry = next(item for item in result.silver_index if item.data_type == "orderbook_snapshot")
        assert snapshot_entry.depth_source_status == "BOOK_DEPTH_STALE"
        assert "ORDERBOOK_SEQUENCE_GAP" in result.data_quality_report.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_sparse_delta_and_orderbook_topic_do_not_imply_depth20() -> None:
    scratch = _scratch_dir("orderbook_sparse_delta")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200_sparse_delta.data")
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-sparse-delta",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
            )
        )

        delta_entry = next(item for item in result.silver_index if item.data_type == "orderbook_delta")
        assert delta_entry.depth_source_status == "BOOK_DEPTH_NOT_PROVEN"
        assert "ORDERBOOK_DELTA_ONLY_NOT_DEPTH_PROOF" in result.data_quality_report.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_data_zip_is_classified_and_dry_run_surfaces_snapshot_and_delta_entries() -> None:
    scratch = _scratch_dir("orderbook_zip")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        fixture_path = _ORDERBOOK_FIXTURE_ROOT / "2025-04-29_BTCUSDT_ob200.data"
        zip_path = raw_root / "ordre book part 1" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data.zip"
        _write_zip_text(zip_path, "2025-04-29_BTCUSDT_ob200.data", fixture_path.read_text(encoding="utf-8"))
        classification = classify_raw_file(
            source=StrategyLadderRawSource(
                source_id="orderbook_zip_source",
                root=str(raw_root),
                exchange="bybit",
                market_type="spot",
                data_types=("orderbook",),
                priority=10,
                enabled=True,
                status="RAW_SOURCE_READY",
            ),
            path=zip_path,
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-zip",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
                dry_run=True,
            )
        )

        assert classification.classification_status == "RAW_FILE_CLASSIFIED_ORDERBOOK"
        assert classification.pair == "BTCUSDT"
        assert any(entry.data_type == "orderbook_snapshot" for entry in result.silver_index)
        assert any(entry.data_type == "orderbook_delta" for entry in result.silver_index)
        assert result.data_quality_report.orderbook_schema_status == "ORDERBOOK_SCHEMA_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_trade_csv_gz_is_classified_and_normalized() -> None:
    scratch = _scratch_dir("trade_gz")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_gzip_csv(
            raw_root / "trades" / "BTCUSDT_2023-01-01.csv.gz",
            "id,timestamp,price,volume,side",
            [
                "1,1672531200000,16000,0.1,buy",
                "2,1672531260000,16010,0.2,sell",
            ],
        )
        classification = classify_raw_file(
            source=StrategyLadderRawSource(
                source_id="trade_gz_source",
                root=str(raw_root),
                exchange="bybit",
                market_type="spot",
                data_types=("trades",),
                priority=10,
                enabled=True,
                status="RAW_SOURCE_READY",
            ),
            path=raw_root / "trades" / "BTCUSDT_2023-01-01.csv.gz",
        )
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-trade-gz",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades",),
            )
        )

        assert classification.data_type == "trades"
        assert classification.pair == "BTCUSDT"
        assert any(entry.data_type == "trades" for entry in result.silver_index)
        assert result.manifest.trade_schema_status == "TRADE_SCHEMA_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_duplicate_zip_and_extracted_data_are_deduplicated() -> None:
    scratch = _scratch_dir("orderbook_duplicate_sources")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        fixture_text = (_ORDERBOOK_FIXTURE_ROOT / "2025-04-29_BTCUSDT_ob200.data").read_text(encoding="utf-8")
        extracted_path = raw_root / "ordre book part 1" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data" / "2025-04-29_BTCUSDT_ob200.data"
        extracted_path.parent.mkdir(parents=True, exist_ok=True)
        extracted_path.write_text(fixture_text, encoding="utf-8")
        _write_zip_text(
            raw_root / "ordre book part 1" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data.zip",
            "2025-04-29_BTCUSDT_ob200.data",
            fixture_text,
        )

        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-dedup",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
                dry_run=True,
            )
        )

        snapshot_entries = [entry for entry in result.silver_index if entry.data_type == "orderbook_snapshot"]
        delta_entries = [entry for entry in result.silver_index if entry.data_type == "orderbook_delta"]
        assert len(snapshot_entries) == 1
        assert len(delta_entries) == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_pair_inference_artifacts_are_emitted_for_folder_based_sources() -> None:
    scratch = _scratch_dir("pair_inference_artifacts")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            ["1,1745884800000,100,1,buy"],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT" / "1" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            ["1745884800000,100,101,99,100.5,10,1005"],
        )
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-pair-inference",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=(),
                data_types=("trades", "klines"),
                start="2025-04-29",
                end="2025-04-29",
            )
        )

        assert result.raw_source_report.pair_inference_status == "PAIR_AUTO_DETECTED_READY"
        assert result.raw_source_report.detected_pairs == ("BTCUSDT",)
        assert result.pair_universe_report.active_pairs_after_pruning == ("BTCUSDT",)
        assert result.data_quality_report.pair_inference_status == "PAIR_AUTO_DETECTED_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_orderbook_sequence_gap_report_is_written() -> None:
    scratch = _scratch_dir("orderbook_sequence_gap_report")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200_seq_gap.data")
        factory_root = scratch / "factory"
        run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-orderbook-gap-report",
                input_root=factory_root,
                raw_roots=(raw_root,),
                silver_root=factory_root / "silver",
                gold_root=factory_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
            )
        )

        report_path = factory_root / "orderbook_sequence_gap_report.json"
        assert report_path.is_file()
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["gap_status"] in {
            "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
            "ORDERBOOK_SEQUENCE_GAP_RECOVERED",
        }
        assert payload["gap_count"] >= 1
        assert payload["first_gap"]["expected_seq"] is not None
        assert payload["first_gap"]["actual_seq"] is not None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_manifest_propagates_silver_gap_blockers() -> None:
    scratch = _scratch_dir("manifest_propagates_silver_gap_blockers")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _copy_orderbook_fixture(raw_root, "2025-04-29_BTCUSDT_ob200_seq_gap.data")
        factory_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-manifest-silver-gap-blockers",
                input_root=factory_root,
                raw_roots=(raw_root,),
                silver_root=factory_root / "silver",
                gold_root=factory_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("orderbook",),
            )
        )

        assert "SILVER_MISSING_TRADES" in result.manifest.blocker_codes
        assert "SILVER_MISSING_OHLCV" in result.manifest.blocker_codes
        manifest_payload = json.loads(
            (factory_root / "data_factory_manifest.json").read_text(encoding="utf-8")
        )
        quality_payload = json.loads(
            (factory_root / "data_quality_report.json").read_text(encoding="utf-8")
        )
        assert "SILVER_MISSING_TRADES" in manifest_payload["blocker_codes"]
        assert "SILVER_MISSING_OHLCV" in manifest_payload["blocker_codes"]
        assert "SILVER_MISSING_TRADES" in quality_payload["blocker_codes"]
        assert "SILVER_MISSING_OHLCV" in quality_payload["blocker_codes"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_manifest_surfaces_runtime_parity_ready_when_training_and_runtime_match() -> None:
    scratch = _scratch_dir("manifest_propagates_runtime_parity_blocker")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_btcusdt_trades_sample(raw_root)
        _write_btcusdt_kline_fixture(raw_root)
        factory_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-manifest-runtime-parity",
                input_root=factory_root,
                raw_roots=(raw_root,),
                silver_root=factory_root / "silver",
                gold_root=factory_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("1m",),
                start="2025-04-29",
                end="2025-04-29",
                small_scope=True,
            )
        )

        parity_payload = json.loads(
            (factory_root / "runtime_feature_parity_manifest.json").read_text(encoding="utf-8")
        )
        assert parity_payload["status"] == "RUNTIME_PARITY_SCHEMA_MATCH_READY"
        manifest_payload = json.loads(
            (factory_root / "data_factory_manifest.json").read_text(encoding="utf-8")
        )
        quality_payload = json.loads(
            (factory_root / "data_quality_report.json").read_text(encoding="utf-8")
        )
        assert "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES" not in result.manifest.blocker_codes
        assert "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES" not in manifest_payload["blocker_codes"]
        assert "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES" not in quality_payload["blocker_codes"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_fetch_bybit_spot_metadata_cache_writes_local_cache_files() -> None:
    scratch = _scratch_dir("bybit_metadata_fetch")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        output_root = scratch / "metadata" / "bybit" / "spot"

        class _FakeResponse:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = payload

            def __enter__(self) -> _FakeResponse:
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def read(self) -> bytes:
                return json.dumps(self._payload).encode("utf-8")

        def _fake_http_get(request, timeout=20):  # noqa: ANN001
            parsed = urlparse(request.full_url)
            symbol = parse_qs(parsed.query).get("symbol", [""])[0]
            payload = {
                "retCode": 0,
                "result": {
                    "list": [
                        {
                            "symbol": symbol,
                            "baseCoin": symbol[:-4],
                            "quoteCoin": symbol[-4:],
                            "status": "Trading",
                            "priceFilter": {"tickSize": "0.10"},
                            "lotSizeFilter": {
                                "qtyStep": "0.001",
                                "minOrderQty": "0.001",
                                "minOrderAmt": "10",
                            },
                        }
                    ]
                },
            }
            return _FakeResponse(payload)

        report = fetch_bybit_spot_metadata_cache(
            pairs=("BNBUSDT", "BTCUSDT"),
            output_root=output_root,
            http_get=_fake_http_get,
        )

        csv_path = output_root / "symbol_metadata.csv"
        jsonl_path = output_root / "symbol_metadata.jsonl"
        report_path = output_root / "metadata_fetch_report.json"
        assert report["fetch_status"] == "BYBIT_PUBLIC_METADATA_FETCH_READY"
        assert csv_path.is_file()
        assert jsonl_path.is_file()
        assert report_path.is_file()
        csv_text = csv_path.read_text(encoding="utf-8")
        assert "BNBUSDT" in csv_text
        assert "BTCUSDT" in csv_text
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert report_payload["metadata_temporal_status"] == "CURRENT_METADATA_PROXY"
        assert report_payload["pairs_fetched"] == ["BNBUSDT", "BTCUSDT"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_generates_raw_source_manifest_and_numeric_expected_edge_feature_manifest() -> None:
    scratch = _scratch_dir("generated_raw_manifest_expected_edge_manifest")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            ["1,1745884800000,63000,0.01,buy"],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            ["1745884800000,63000,63050,62980,63010,5,315050"],
        )
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-generated-raw-manifest",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("1m",),
                start="2025-04-29",
                end="2025-04-29",
                small_scope=True,
            )
        )

        manifest_path = Path(result.manifest.raw_source_manifest_path)
        assert manifest_path.is_file()
        raw_source_payload = json.loads((scratch / "factory" / "raw_source_report.json").read_text(encoding="utf-8"))
        assert raw_source_payload["raw_source_manifest_path"] == str(manifest_path.resolve())
        assert raw_source_payload["raw_source_provenance_status"] == "RAW_SOURCE_MANIFEST_GENERATED"
        assert any(
            code in {"RAW_SOURCE_TYPE_INFERRED", "RAW_SOURCE_TYPE_AMBIGUOUS"}
            for code in raw_source_payload["blocker_codes"]
        )
        expected_edge_payload = json.loads((scratch / "factory" / "expected_edge_feature_manifest.json").read_text(encoding="utf-8"))
        assert expected_edge_payload["purge_window_minutes"] == 1
        assert expected_edge_payload["embargo_window_minutes"] == 1
        assert "break_even_bps" in expected_edge_payload["feature_names"]
        assert "session_tags" not in expected_edge_payload["feature_names"]
        assert result.manifest.pair_generalization_status == "SINGLE_PAIR_RESEARCH_ONLY"
        assert "SINGLE_PAIR_RESEARCH_ONLY" in result.manifest.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_reads_historical_metadata_cache_and_surfaces_bybit_status() -> None:
    scratch = _scratch_dir("historical_metadata_cache")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1745884800000,63000,0.01,buy",
                "2,1745884860000,63010,0.02,sell",
            ],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1745884800000,63000,63050,62980,63010,5,315050",
                "1745884860000,63010,63060,63000,63040,4,252160",
            ],
        )
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _write_symbol_metadata_csv(
            metadata_root / "symbol_metadata.csv",
            [
                "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.10,0.0001,0.0001,10,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-05T00:00:00+00:00,abc123,CURRENT_METADATA_PROXY",
            ],
        )

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-bybit-metadata-ready",
                input_root=report_root,
                raw_roots=(raw_root,),
                historical_metadata_root=metadata_root,
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                start="2025-04-29",
                end="2025-04-29",
            )
        )

        assert result.manifest.metadata_schema_status == "METADATA_SCHEMA_READY"
        assert (
            result.manifest.historical_metadata_status
            == "BYBIT_HISTORICAL_METADATA_READY"
        )
        assert result.data_quality_report.fee_provenance_status == (
            "CONFIGURED_FEE_PROVENANCE_READY"
        )
        assert result.data_quality_report.metadata_temporal_status == (
            "CURRENT_METADATA_PROXY"
        )
        assert result.data_quality_report.metadata_source_mode == "LOCAL_METADATA_CACHE"
        assert result.data_quality_report.historical_data_venue == "BYBIT"
        assert result.pair_universe_report.pair_data_coverage[0].has_metadata is True
        assert any(entry.data_type == "metadata" for entry in result.silver_index)
        assert result.data_quality_report.capital_bucket_metadata_status == (
            "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN"
        )
        assert result.data_quality_report.fee_provenance_status != "ACCOUNT_FEE_VERIFIED"

        gold_path = Path(result.gold_feature_manifest.feature_paths[0])
        gold_rows = _read_jsonl_any(gold_path)
        assert gold_rows
        assert gold_rows[0]["min_notional"] == 10.0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_historical_metadata_missing_requested_pair_returns_pair_not_found() -> None:
    scratch = _scratch_dir("historical_metadata_missing_pair")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            ["1,1745884800000,63000,0.01,buy"],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            ["1745884800000,63000,63050,62980,63010,5,315050"],
        )
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _write_symbol_metadata_csv(
            metadata_root / "symbol_metadata.csv",
            [
                "bybit,bybit,spot,ETHUSDT,ETH,USDT,Trading,0.01,0.001,0.001,10,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-05T00:00:00+00:00,eth123,CURRENT_METADATA_PROXY",
            ],
        )

        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-bybit-metadata-missing-pair",
                input_root=scratch / "factory",
                raw_roots=(raw_root,),
                historical_metadata_root=metadata_root,
                silver_root=scratch / "factory" / "silver",
                gold_root=scratch / "factory" / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                start="2025-04-29",
                end="2025-04-29",
            )
        )

        assert result.manifest.historical_metadata_status == "METADATA_PAIR_NOT_FOUND"
        assert result.data_quality_report.missing_metadata_pairs == ("BTCUSDT",)
        assert result.data_quality_report.fee_provenance_status == "FEE_PROVENANCE_NOT_PROVEN"
        assert result.manifest.data_factory_status in {
            "DATA_FACTORY_PARTIAL",
            "DATA_FACTORY_READY",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_uses_local_metadata_cache_without_network_calls() -> None:
    scratch = _scratch_dir("historical_metadata_local_only")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            ["1,1745884800000,63000,0.01,buy"],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            ["1745884800000,63000,63050,62980,63010,5,315050"],
        )
        metadata_root = scratch / "metadata" / "bybit" / "spot"
        _write_symbol_metadata_csv(
            metadata_root / "symbol_metadata.csv",
            [
                "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.10,0.0001,0.0001,10,0.001,0.001,bybit_configured_vip0_research,historical_replay,configured,bybit_public_instruments_info,2026-05-05T00:00:00+00:00,abc123,CURRENT_METADATA_PROXY",
            ],
        )

        import local_replay_runtime.bybit_historical_metadata as metadata_module

        original_urlopen = metadata_module.urlopen
        metadata_module.urlopen = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should not be called"))  # type: ignore[assignment]
        try:
            result = run_strategy_ladder_data_factory(
                StrategyLadderDataFactoryRequest(
                    run_id="df-bybit-local-only",
                    input_root=scratch / "factory",
                    raw_roots=(raw_root,),
                    historical_metadata_root=metadata_root,
                    silver_root=scratch / "factory" / "silver",
                    gold_root=scratch / "factory" / "gold",
                    pairs=("BTCUSDT",),
                    data_types=("trades", "klines"),
                    start="2025-04-29",
                    end="2025-04-29",
                )
            )
        finally:
            metadata_module.urlopen = original_urlopen  # type: ignore[assignment]

        assert result.manifest.historical_metadata_status == "BYBIT_HISTORICAL_METADATA_READY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_emits_fragility_false_breakout_features_and_metadata_ready_reports() -> None:
    scratch = _scratch_dir("gold_fragility_metadata")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        metadata_root = scratch / "metadata"
        report_root = scratch / "factory"
        _write_gzip_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv.gz",
            "id,timestamp,price,volume,side",
            [
                "1,1745884800000,63000,0.10,buy",
                "2,1745884860000,63020,0.18,sell",
            ],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1745884800000,63000,63120,62990,63015,12,756180",
                "1745884860000,63015,63160,62980,63010,18,1134180",
            ],
        )
        _write_jsonl(
            raw_root / "orderbook" / "snapshot" / "BTCUSDT_2025-04-29.data",
            [
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "type": "snapshot",
                    "timestamp_ms": 1745884800000,
                    "seq": 1,
                    "data": {"s": "BTCUSDT", "b": _book_levels("bid"), "a": _book_levels("ask")},
                },
            ],
        )
        _write_symbol_metadata_csv(
            metadata_root / "symbol_metadata.csv",
            [
                "bybit,bybit,spot,BTCUSDT,BTC,USDT,Trading,0.1,0.001,0.001,5,0.001,0.001,local_cfg,historical_replay,research,local,2026-05-15T00:00:00+00:00,hash-btc,CURRENT_METADATA_PROXY",
            ],
        )

        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-gold-fragility-metadata",
                input_root=report_root,
                raw_roots=(raw_root,),
                historical_metadata_root=metadata_root,
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines", "orderbook"),
                start="2025-04-29",
                end="2025-04-29",
            )
        )

        gold_rows = [
            row
            for path in result.gold_feature_manifest.feature_paths
            for row in _read_jsonl_any(Path(path))
        ]
        assert gold_rows
        first_row = gold_rows[0]
        assert "fragility_score" in first_row["feature_values"]
        assert "fragility" in first_row["feature_values"]
        assert "false_breakout_context" in first_row["feature_values"]
        assert "sweep_score" in first_row["feature_values"]
        assert "break_even_bps" in first_row["feature_values"]
        assert "session_tags" in first_row["feature_values"]
        report_payload = json.loads(
            (report_root / "raw_data_processing_report.json").read_text(encoding="utf-8")
        )
        assert "metadata" not in report_payload["raw_coverage"]["source_types_missing"]
        assert "fragility_false_breakout_features" not in report_payload["gold_feature_groups_missing"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# Patch 2026-05-15 (timeframe propagation audit) — new multi-timeframe coverage.
# Silver layer carrying 1m/5m/10m/15m must propagate every supported timeframe
# to gold by default. Any timeframe that does not materialize must carry an
# explicit reason code on the manifest. These tests harden the pipeline against
# silent prunes that previously hid 10m/15m from candidate discovery and B2.


def _stub_economic_provenance(monkeypatch) -> list[dict[str, object]]:
    """Patch out compute_economic_provenance with a deterministic fake.

    The new tests do not exercise the orderbook pipeline, so we return a
    stable SimpleNamespace and record calls for assertions. Behaviour mirrors
    the fake used in the legacy timeframe-filter test.
    """

    calls: list[dict[str, object]] = []

    def _fake(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            expected_edge_bps=5.0,
            expected_edge_provenance="DEFAULT_TO_CALIBRATE",
            aggregated_provenance="PARTIALLY_MEASURED",
            measurement_warnings=(),
            spread_bps=0.0,
            spread_provenance="DEFAULT_BY_BOOK_STATUS",
            slippage_bps=2.0,
            slippage_provenance="DEFAULT_TO_CALIBRATE",
            latency_penalty_bps=1.0,
        )

    monkeypatch.setattr(
        data_factory_module,
        "compute_economic_provenance",
        _fake,
    )
    return calls


def _write_btcusdt_kline_for_timeframe(raw_root: Path, minutes: int) -> None:
    """Emit a minimal 2-row Bybit kline CSV for the given timeframe (minutes)."""

    _write_csv(
        raw_root / "klines" / f"BTCUSDT_{minutes}_2025-01-01.csv",
        "startTime,open,high,low,close,volume,turnover",
        [
            "1735689600000,94000,94100,93900,94010,10,940100",
            f"{1735689600000 + minutes * 60_000},94010,94110,93910,94020,11,1034220",
        ],
    )


def _write_btcusdt_trades_sample(raw_root: Path) -> None:
    _write_csv(
        raw_root / "trades" / "BTCUSDT_2025-01-01.csv",
        "id,timestamp,price,volume,side",
        [
            "1,1735689600000,94000,0.01,buy",
            "2,1735689660000,94010,0.02,sell",
        ],
    )


def test_gold_materializes_every_supported_timeframe_present_in_silver(monkeypatch) -> None:
    """Silver carrying 1m/5m/10m/15m must yield gold for every timeframe."""

    scratch = _scratch_dir("gold_all_supported_timeframes")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_btcusdt_trades_sample(raw_root)
        for minutes in (1, 5, 10, 15):
            _write_btcusdt_kline_for_timeframe(raw_root, minutes)
        _stub_economic_provenance(monkeypatch)

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-all-timeframes",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("1m", "5m", "10m", "15m"),
                start="2025-01-01",
                end="2025-01-01",
                use_measured_economic_provenance=True,
                small_scope=True,
            )
        )

        manifest = result.gold_feature_manifest
        assert manifest.gold_feature_store_status == "FEATURE_STORE_READY"
        assert set(manifest.silver_timeframes_detected) == {"1m", "5m", "10m", "15m"}
        assert set(manifest.gold_timeframes_generated) == {"1m", "5m", "10m", "15m"}
        assert manifest.timeframes_pruned == ()
        assert manifest.pruning_reason_by_timeframe == {}
        for tf in ("1m", "5m", "10m", "15m"):
            assert manifest.timeframe_feature_row_count.get(tf, 0) > 0, tf
            assert any(f"features_{tf}" in path for path in manifest.feature_paths), tf
        # No timeframe-related blocker codes should leak when everything matches.
        for code in manifest.blocker_codes:
            assert not code.startswith("TIMEFRAME_"), code
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_gold_emits_input_missing_when_silver_lacks_requested_timeframe(monkeypatch) -> None:
    """Requesting a timeframe absent from silver must surface an explicit reason."""

    scratch = _scratch_dir("gold_input_missing")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_btcusdt_trades_sample(raw_root)
        # Only 1m raw klines; 5m has no silver source.
        _write_btcusdt_kline_for_timeframe(raw_root, 1)
        _stub_economic_provenance(monkeypatch)

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-input-missing",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("1m", "5m"),
                start="2025-01-01",
                end="2025-01-01",
                use_measured_economic_provenance=True,
                small_scope=True,
            )
        )

        manifest = result.gold_feature_manifest
        assert "1m" in manifest.gold_timeframes_generated
        assert "5m" not in manifest.gold_timeframes_generated
        assert manifest.pruning_reason_by_timeframe.get("5m") == "TIMEFRAME_FEATURE_INPUT_MISSING"
        assert "5m" in manifest.timeframes_pruned
        assert "TIMEFRAME_FEATURE_INPUT_MISSING" in manifest.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_gold_emits_generation_not_supported_for_unknown_timeframe(monkeypatch) -> None:
    """Requesting a timeframe outside the registry must fail-closed explicitly."""

    scratch = _scratch_dir("gold_unsupported_timeframe")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_btcusdt_trades_sample(raw_root)
        _write_btcusdt_kline_for_timeframe(raw_root, 1)
        _stub_economic_provenance(monkeypatch)

        report_root = scratch / "factory"
        # "30m" is not in SUPPORTED_GOLD_TIMEFRAMES — the request includes it
        # alongside the valid 1m so we can assert the partial outcome.
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-unsupported-tf",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                data_types=("trades", "klines"),
                timeframes=("1m", "30m"),
                start="2025-01-01",
                end="2025-01-01",
                use_measured_economic_provenance=True,
                small_scope=True,
            )
        )

        manifest = result.gold_feature_manifest
        assert "1m" in manifest.gold_timeframes_generated
        assert (
            manifest.pruning_reason_by_timeframe.get("30m")
            == "TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED"
        )
        assert "TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED" in manifest.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
