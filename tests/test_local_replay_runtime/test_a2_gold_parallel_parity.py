"""Gain 2 parity gate — parallel A2 gold build == serial, byte-for-byte on the
GOLD FILES (what B1/B2 consume). 2 pairs -> 2 partition tasks -> MP engages.
"""
from __future__ import annotations

import gzip
import json
import shutil
import tempfile
from pathlib import Path

from local_replay_runtime.strategy_ladder_a2_gold_parallel import (
    build_gold_features_parallel,
    partition_gold_tasks,
)
from local_replay_runtime.strategy_ladder_data_factory import _write_gold_features
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
    StrategyLadderSilverIndexEntry,
)

BASE = 1_748_131_200_000  # 2025-05-25 00:00 UTC-ish
DAY = 86_400_000


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _pair_entries(silver: Path, pair: str, dates: list[str], day_base: list[int]):
    entries = []
    scratch = silver.parent
    for date, base in zip(dates, day_base):
        y, m, dd = date.split("-")
        kline = silver / "bybit" / "spot" / "ohlcv" / "5m" / pair / y / m / f"{dd}.jsonl"
        trades = silver / "bybit" / "spot" / "trades" / pair / y / m / f"{dd}.jsonl"
        _write_jsonl(kline, [
            {"timestamp_ms": base + i * 300_000, "open": 100.0 + i, "high": 101.0 + i,
             "low": 99.0 + i, "close": 100.5 + i, "volume": 10.0 + i}
            for i in range(3)
        ])
        _write_jsonl(trades, [
            {"timestamp_ms": base + i * 30_000, "price": 100.0 + i * 0.1, "qty": 0.5 + i * 0.01,
             "side": "buy" if i % 2 else "sell"}
            for i in range(40)
        ])
        entries.append(StrategyLadderSilverIndexEntry(
            source_id=f"k_{pair}_{date}", source_root=str(scratch.resolve()), source_priority=10,
            exchange="bybit", market_type="spot", data_type="ohlcv", pair=pair, timeframe="5m",
            date=date, path=str(kline.resolve()), storage_format="jsonl",
            min_timestamp_ms=base, max_timestamp_ms=base + 600_000, row_count=3,
            file_hash=f"hk-{pair}-{date}", depth_source_status="BOOK_DEPTH_NOT_PROVEN",
            schema_status="KLINE_SCHEMA_READY"))
        entries.append(StrategyLadderSilverIndexEntry(
            source_id=f"t_{pair}_{date}", source_root=str(scratch.resolve()), source_priority=10,
            exchange="bybit", market_type="spot", data_type="trades", pair=pair, timeframe="",
            date=date, path=str(trades.resolve()), storage_format="jsonl",
            min_timestamp_ms=base, max_timestamp_ms=base + 1_200_000, row_count=40,
            file_hash=f"ht-{pair}-{date}", depth_source_status="BOOK_DEPTH_NOT_PROVEN",
            schema_status="TRADE_SCHEMA_READY"))
    return entries


def _read_gold_tree(gold_root: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    root_abs = str(gold_root.resolve())
    for f in sorted(gold_root.rglob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8-sig") as h:
            rows = [json.loads(line) for line in h if line.strip()]
        # `source_ref` is the row's OWN output path -> root-dependent by design.
        # Normalise to a path relative to this gold_root so serial vs parallel
        # (written to different roots) compare apples-to-apples.
        for r in rows:
            sr = r.get("source_ref")
            if isinstance(sr, str):
                r["source_ref"] = sr.replace(root_abs, "<GOLD_ROOT>")
        out[str(f.relative_to(gold_root))] = rows
    return out


def _request(scratch: Path, silver: Path, gold: Path) -> StrategyLadderDataFactoryRequest:
    return StrategyLadderDataFactoryRequest(
        run_id="a2par", input_root=scratch, raw_roots=(scratch,), silver_root=silver,
        gold_root=gold, pairs=("BTCUSDT", "BNBUSDT"), timeframes=("5m",),
        start="2025-05-25", end="2025-05-26", use_measured_economic_provenance=True,
    )


def _build_fixture(scratch: Path):
    silver = scratch / "silver"
    dates = ["2025-05-25", "2025-05-26"]
    bases = [BASE, BASE + DAY]
    entries = []
    for pair in ("BTCUSDT", "BNBUSDT"):
        entries += _pair_entries(silver, pair, dates, bases)
    meta = silver / "metadata" / "symbol_metadata.jsonl"
    _write_jsonl(meta, [{"pair": "BTCUSDT", "min_notional": 5.0}, {"pair": "BNBUSDT", "min_notional": 5.0}])
    for pair in ("BTCUSDT", "BNBUSDT"):
        entries.append(StrategyLadderSilverIndexEntry(
            source_id=f"meta_{pair}", source_root=str(scratch.resolve()), source_priority=1,
            exchange="bybit", market_type="spot", data_type="metadata", pair=pair, timeframe="",
            date="", path=str(meta.resolve()), storage_format="jsonl",
            row_count=2, file_hash="hmeta", schema_status="METADATA_SCHEMA_READY"))
    return silver, tuple(entries)


def test_partition_gold_tasks_splits_by_pair_tf_month() -> None:
    scratch = Path(tempfile.mkdtemp(prefix="a2par_part_"))
    try:
        silver, entries = _build_fixture(scratch)
        req = _request(scratch, silver, scratch / "gold")
        tasks = partition_gold_tasks(req, entries, ("BTCUSDT", "BNBUSDT"))
        # 2 pairs x 1 tf x 1 month (both days in 2025-05) = 2 tasks
        assert len(tasks) == 2
        assert {t.pair for t in tasks} == {"BTCUSDT", "BNBUSDT"}
        assert all(t.timeframe == "5m" and t.year_month == "2025-05" for t in tasks)
        # each task scoped to its single pair
        assert all(t.request.pairs == (t.pair,) for t in tasks)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_parallel_gold_build_matches_serial_byte_for_byte() -> None:
    scratch = Path(tempfile.mkdtemp(prefix="a2par_parity_"))
    try:
        silver, entries = _build_fixture(scratch)
        serial = _write_gold_features(
            request=_request(scratch, silver, scratch / "gold_serial"),
            index_entries=entries, available_pairs=("BTCUSDT", "BNBUSDT"),
        )
        parallel = build_gold_features_parallel(
            _request(scratch, silver, scratch / "gold_parallel"),
            entries, ("BTCUSDT", "BNBUSDT"), max_workers=2,
        )
        tree_serial = _read_gold_tree(scratch / "gold_serial")
        tree_parallel = _read_gold_tree(scratch / "gold_parallel")

        assert tree_serial, "serial produced no gold files"
        assert set(tree_serial) == set(tree_parallel), "gold file set diverged"
        for rel, rows_s in tree_serial.items():
            assert rows_s == tree_parallel[rel], f"gold rows diverged for {rel}"
        assert serial.feature_row_count == parallel.feature_row_count > 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
