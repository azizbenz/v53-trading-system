"""Patch 6 batch 1 — date pruning, gzip storage, storage budget, proof matrix v2.

These tests cover:

- Filename-only date pruning fires *before* classify_raw_file (no full sha256
  on out-of-range files).
- ``--storage-format jsonl-gz`` actually compresses silver outputs through the
  Python ``gzip`` stdlib module.
- Storage budget pre-flight estimator returns sane bounds and a typed report.
- Proof matrix v2 surfaces orderbook_snapshot_status / orderbook_delta_status /
  orderbook_reconstruction_status / depth20_proof_status as separate fields.

No raw L:/J: data is touched. All fixtures are tiny synthetic JSON/CSV.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from local_replay_runtime.backtest_proof_matrix import (
    build_backtest_proof_matrix,
    emit_backtest_proof_matrix,
)
from local_replay_runtime.storage_budget_report import (
    StorageBudgetReport,
    build_storage_budget_report,
    estimate_silver_size_for_paths,
    write_storage_budget_report,
)
from local_replay_runtime.strategy_ladder_data_factory import (
    _date_in_range,
    _probe_filename_date,
    _resolve_silver_path,
    _write_rows,
    run_strategy_ladder_data_factory,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / ".test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{label}_{uuid4().hex}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Part A — date pruning helpers
# ---------------------------------------------------------------------------


def test_probe_filename_date_finds_iso_date_in_real_bybit_filenames() -> None:
    assert _probe_filename_date(Path("2025-04-29_BTCUSDT_ob200.data.zip")) == "2025-04-29"
    assert _probe_filename_date(Path("BTCUSDT_2023-01-01.csv.gz")) == "2023-01-01"
    assert _probe_filename_date(Path("BTCUSDT_1_2025-04-30.csv")) == "2025-04-30"
    assert _probe_filename_date(Path("nodate_file.csv")) == ""


def test_date_in_range_keeps_files_inside_window() -> None:
    start_ms = int(
        __import__("datetime").datetime.fromisoformat("2025-04-29T00:00:00+00:00").timestamp()
        * 1000
    )
    end_ms = int(
        __import__("datetime").datetime.fromisoformat("2025-04-30T23:59:59+00:00").timestamp()
        * 1000
    )
    assert _date_in_range("2025-04-29", start_ms=start_ms, end_ms=end_ms) is True
    assert _date_in_range("2025-04-30", start_ms=start_ms, end_ms=end_ms) is True
    assert _date_in_range("2024-05-17", start_ms=start_ms, end_ms=end_ms) is False
    assert _date_in_range("2026-04-12", start_ms=start_ms, end_ms=end_ms) is False
    # Empty date or empty range returns True (caller decides).
    assert _date_in_range("", start_ms=start_ms, end_ms=end_ms) is True
    assert _date_in_range("2025-04-29", start_ms=None, end_ms=None) is True


def test_data_factory_skips_2024_file_when_range_is_2025_04_29_to_30() -> None:
    scratch = _scratch_dir("date_pruning")
    try:
        raw_root = scratch / "raw"
        # In-range file (2025-04-29) — would be processed.
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume",
            ["1,1745884800000,94000.0,0.5"],
        )
        # Out-of-range file (2024-05-17) — must NEVER be opened.
        # We populate it with garbage that would fail classification if read,
        # which proves the pruning happens before classify_raw_file.
        garbage_path = raw_root / "trades" / "BTCUSDT_2024-05-17.csv"
        garbage_path.parent.mkdir(parents=True, exist_ok=True)
        garbage_path.write_text("THIS_IS_NOT_VALID_CSV_AND_MUST_NOT_BE_PARSED\n", encoding="utf-8")

        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="date-pruning-test",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                start="2025-04-29",
                end="2025-04-30",
                dry_run=True,
            )
        )
        # The garbage 2024 file must have been counted as skipped-by-date,
        # never as a schema-invalid file.
        quality = result.data_quality_report
        assert quality.files_skipped_by_date_filter >= 1
        assert quality.date_pruning_status == "DATE_PRUNING_READY"
        assert "2025-04-29" == quality.date_filter_start
        assert "2025-04-30" == quality.date_filter_end
        # Schema status for trades must be READY (only the 2025 file was opened).
        assert quality.trade_schema_status != "TRADE_SCHEMA_INVALID_TIMESTAMP"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_blocks_non_dry_run_without_dates() -> None:
    scratch = _scratch_dir("non_dry_no_dates")
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume",
            ["1,1745884800000,94000.0,0.5"],
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="non-dry-no-dates",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                start="",
                end="",
                dry_run=False,
            )
        )
        assert "DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN" in result.data_quality_report.blocker_codes
        assert result.manifest.data_factory_status in {
            "DATA_FACTORY_BLOCKED_BY_DATE_RANGE",
            "DATA_FACTORY_BLOCKED_BY_RAW_DATA",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_passes_with_explicit_allow_broad_run() -> None:
    scratch = _scratch_dir("broad_run_explicit")
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume",
            ["1,1745884800000,94000.0,0.5"],
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="broad-run-ok",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                start="",
                end="",
                dry_run=False,
                allow_broad_run=True,
            )
        )
        assert "DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN" not in result.data_quality_report.blocker_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Part C-LITE — gzip storage format
# ---------------------------------------------------------------------------


def test_resolve_silver_path_appends_gz_suffix_for_jsonl_gz() -> None:
    base = Path("/tmp/silver/foo.jsonl")
    assert _resolve_silver_path(base, "jsonl") == base
    assert _resolve_silver_path(base, "jsonl-gz") == Path("/tmp/silver/foo.jsonl.gz")
    # Unknown formats fall back to plain JSONL.
    assert _resolve_silver_path(base, "parquet") == base


def test_write_rows_jsonl_gz_produces_a_valid_gzip_stream() -> None:
    scratch = _scratch_dir("write_rows_gz")
    try:
        out_path = scratch / "demo.jsonl.gz"
        rows = [{"id": i, "v": f"value_{i}"} for i in range(50)]
        bytes_written = _write_rows(out_path, rows, storage_format="jsonl-gz")
        assert bytes_written > 0
        assert out_path.exists()
        # Decompress and verify content.
        with gzip.open(out_path, "rt", encoding="utf-8") as handle:
            decoded = handle.read()
        recovered = [json.loads(line) for line in decoded.splitlines() if line.strip()]
        assert recovered == rows
        # Compressed size should be much smaller than the plain JSONL we'd
        # have written (50 rows of small JSON ~= 1.5KB plain, ~200B gz).
        assert bytes_written < 600
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_data_factory_with_jsonl_gz_writes_compressed_silver() -> None:
    scratch = _scratch_dir("df_jsonl_gz")
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume",
            [f"{i},{1745884800000 + i},{94000 + i},0.5" for i in range(20)],
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-gz",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                start="2025-04-29",
                end="2025-04-29",
                storage_format="jsonl-gz",
            )
        )
        # Silver path must end with .jsonl.gz, and the file must be valid gzip.
        trade_entries = [
            entry for entry in result.silver_index if entry.data_type == "trades"
        ]
        assert trade_entries, "no trade silver entry produced"
        path = Path(trade_entries[0].path)
        assert path.suffix == ".gz"
        assert path.exists()
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            content = handle.read()
        assert "trade_id" in content
        # Quality report tags storage status correctly.
        assert result.data_quality_report.silver_storage_format == "jsonl_gz"
        assert (
            result.data_quality_report.silver_storage_status
            == "SILVER_STORAGE_READY_COMPRESSED"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Part E — storage budget pre-flight
# ---------------------------------------------------------------------------


def test_data_factory_with_jsonl_gz_can_build_gold_features_from_compressed_silver() -> None:
    scratch = _scratch_dir("df_jsonl_gz_gold")
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv",
            "id,timestamp,price,volume,side",
            [
                "1,1745884800000,94000,0.5,buy",
                "2,1745884860000,94010,0.4,sell",
            ],
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            "startTime,open,high,low,close,volume,turnover",
            [
                "1745884800000,94000,94020,93990,94010,10,940100",
                "1745884860000,94010,94030,94000,94020,9,846180",
            ],
        )
        report_root = scratch / "factory"
        result = run_strategy_ladder_data_factory(
            StrategyLadderDataFactoryRequest(
                run_id="df-gz-gold",
                input_root=report_root,
                raw_roots=(raw_root,),
                silver_root=report_root / "silver",
                gold_root=report_root / "gold",
                pairs=("BTCUSDT",),
                start="2025-04-29",
                end="2025-04-29",
                storage_format="jsonl-gz",
            )
        )

        assert result.manifest.data_factory_status == "DATA_FACTORY_READY"
        assert result.gold_feature_manifest.feature_row_count > 0
        assert result.gold_feature_manifest.feature_paths
        gold_path = Path(result.gold_feature_manifest.feature_paths[0])
        gold_rows = [
            json.loads(line)
            for line in gold_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert gold_rows
        kline_entries = [entry for entry in result.silver_index if entry.data_type == "ohlcv"]
        assert kline_entries
        assert Path(kline_entries[0].path).suffix == ".gz"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_estimate_silver_size_uses_pessimistic_orderbook_ratio() -> None:
    scratch = _scratch_dir("budget_estimate")
    try:
        raw = scratch / "orderbook" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\x00" * (1_000_000))  # 1 MB raw
        raw_size, silver_size = estimate_silver_size_for_paths((raw,), storage_format="jsonl")
        assert raw_size == 1_000_000
        # Orderbook expansion ratio is 7×.
        assert silver_size >= 6_000_000 and silver_size <= 8_000_000
        # gz mode should be ~8× smaller than jsonl mode.
        _, silver_gz = estimate_silver_size_for_paths((raw,), storage_format="jsonl-gz")
        assert silver_gz < silver_size / 4
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_storage_budget_report_flags_exceeded() -> None:
    scratch = _scratch_dir("budget_exceeded")
    try:
        raw = scratch / "orderbook" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\x00" * (50_000_000))  # 50 MB
        report = build_storage_budget_report(
            run_id="budget-test",
            output_root=scratch,
            raw_paths=(raw,),
            storage_format="jsonl",
            storage_budget_limit_bytes=10_000_000,  # 10 MB hard limit
        )
        assert report.storage_budget_status == "STORAGE_BUDGET_EXCEEDED"
        assert "STORAGE_BUDGET_EXCEEDED" in report.storage_budget_reason_codes
        assert report.blocker_severity == "BLOCKER"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_storage_budget_report_marks_small_scope_jsonl_as_warning_not_blocker() -> None:
    scratch = _scratch_dir("budget_small_scope_warning")
    try:
        raw = scratch / "orderbook" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\x00" * 1_000_000)
        report = build_storage_budget_report(
            run_id="budget-small-scope",
            output_root=scratch,
            raw_paths=(raw,),
            storage_format="jsonl_debug",
            debug_jsonl_allowed=True,
        )
        assert report.silver_storage_status == "SILVER_STORAGE_BLOAT_WARNING"
        assert report.blocker_severity == "WARNING"
        assert report.silver_bloat_ratio is not None
        assert report.recommendation
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_storage_budget_report_marks_broad_jsonl_as_blocker() -> None:
    scratch = _scratch_dir("budget_broad_blocker")
    try:
        raw = scratch / "orderbook" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\x00" * 1_000_000)
        report = build_storage_budget_report(
            run_id="budget-broad",
            output_root=scratch,
            raw_paths=(raw,),
            storage_format="jsonl",
            broad_scope=True,
        )
        assert report.silver_storage_status == "SILVER_STORAGE_BLOAT_BLOCKER"
        assert report.blocker_severity == "BLOCKER"
        assert "SILVER_STORAGE_BLOAT_BLOCKER" in report.storage_budget_reason_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_storage_budget_report_writes_json_artefact() -> None:
    scratch = _scratch_dir("budget_artefact")
    try:
        report = build_storage_budget_report(
            run_id="budget-write",
            output_root=scratch,
            raw_paths=(),
            storage_format="jsonl-gz",
        )
        path = write_storage_budget_report(scratch, report)
        assert path.is_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["run_id"] == "budget-write"
        assert payload["storage_format"] == "jsonl-gz"
        assert payload["silver_storage_format"] == "jsonl_gz"
        assert payload["silver_storage_status"] == "SILVER_STORAGE_READY_COMPRESSED"
        assert payload["blocker_severity"] == "READY"
        assert "storage_budget_status" in payload
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Part F+H — proof matrix v2 surfaces snapshot/delta separation
# ---------------------------------------------------------------------------


def _write_manifest(output_root: Path, payload: dict) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "data_factory_manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_silver_index(output_root: Path, entries: list[dict]) -> None:
    (output_root / "silver_index.json").write_text(
        json.dumps({"schema_version": "v1", "entries": entries, "status": "SILVER_INDEX_READY"}),
        encoding="utf-8",
    )


def test_proof_matrix_v2_separates_orderbook_snapshot_and_delta_status() -> None:
    scratch = _scratch_dir("matrix_v2_snapshot_delta")
    try:
        _write_manifest(
            scratch,
            {
                "run_id": "v2-test",
                "data_factory_status": "DATA_FACTORY_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "trade_schema_status": "TRADE_SCHEMA_READY",
                "kline_schema_status": "KLINE_SCHEMA_READY",
                "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
                "metadata_schema_status": "METADATA_SCHEMA_NOT_PROVEN",
                "blocker_codes": [],
            },
        )
        _write_silver_index(
            scratch,
            [
                {
                    "data_type": "orderbook_snapshot",
                    "row_count": 5,
                    "path": str(scratch / "snap.jsonl"),
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                },
                {
                    "data_type": "orderbook_delta",
                    "row_count": 1234,
                    "path": str(scratch / "delta.jsonl"),
                    "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                },
            ],
        )
        (scratch / "snap.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "delta.jsonl").write_text("{}\n", encoding="utf-8")
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="v2-test")
        assert matrix.orderbook_snapshot_status == "ORDERBOOK_SNAPSHOT_READY"
        assert matrix.orderbook_delta_status == "ORDERBOOK_DELTA_READY"
        assert matrix.orderbook_reconstruction_status == "ORDERBOOK_RECONSTRUCTION_READY"
        assert matrix.depth20_proof_status == "BOOK_DEPTH20_AVAILABLE"
        assert matrix.snapshot_entry_count == 5
        assert matrix.delta_entry_count == 1234
        assert matrix.snapshot_paths == (str(scratch / "snap.jsonl"),)
        assert matrix.delta_paths == (str(scratch / "delta.jsonl"),)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_v2_depth20_not_promoted_without_reconstruction() -> None:
    scratch = _scratch_dir("matrix_v2_no_recon")
    try:
        _write_manifest(
            scratch,
            {
                "run_id": "v2-no-recon",
                "data_factory_status": "DATA_FACTORY_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "trade_schema_status": "TRADE_SCHEMA_READY",
                "kline_schema_status": "KLINE_SCHEMA_READY",
                "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
                "metadata_schema_status": "METADATA_SCHEMA_NOT_PROVEN",
                "blocker_codes": [],
            },
        )
        # Delta-only — no snapshot row → reconstruction NOT_PROVEN.
        _write_silver_index(
            scratch,
            [
                {
                    "data_type": "orderbook_delta",
                    "row_count": 100,
                    "path": str(scratch / "delta.jsonl"),
                    "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                },
            ],
        )
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="v2-no-recon")
        assert matrix.orderbook_snapshot_status == "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
        assert matrix.orderbook_reconstruction_status == "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
        assert matrix.depth20_proof_status == "BOOK_DEPTH_NOT_PROVEN"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_v2_surfaces_storage_budget_and_date_pruning() -> None:
    scratch = _scratch_dir("matrix_v2_storage")
    try:
        _write_manifest(
            scratch,
            {
                "run_id": "v2-storage",
                "data_factory_status": "DATA_FACTORY_READY",
                "blocker_codes": [],
            },
        )
        # Quality report carries the date pruning + silver storage status.
        (scratch / "data_quality_report.json").write_text(
            json.dumps(
                {
                    "date_pruning_status": "DATE_PRUNING_READY",
                    "silver_index_date_range_status": "SILVER_INDEX_DATE_RANGE_CONSISTENT",
                    "raw_scan_budget_status": "DRY_RUN_SCOPE_READY",
                    "silver_storage_status": "SILVER_STORAGE_READY_COMPRESSED",
                }
            ),
            encoding="utf-8",
        )
        # Storage budget report surfaces too.
        (scratch / "storage_budget_report.json").write_text(
            json.dumps({"storage_budget_status": "STORAGE_BUDGET_READY"}),
            encoding="utf-8",
        )
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="v2-storage")
        assert matrix.date_pruning_status == "DATE_PRUNING_READY"
        assert (
            matrix.silver_index_date_range_status
            == "SILVER_INDEX_DATE_RANGE_CONSISTENT"
        )
        assert matrix.raw_scan_budget_status == "DRY_RUN_SCOPE_READY"
        assert matrix.silver_storage_status == "SILVER_STORAGE_READY_COMPRESSED"
        assert matrix.storage_budget_status == "STORAGE_BUDGET_READY"
        assert matrix.storage_budget_report_path.endswith("storage_budget_report.json")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_v2_surfaces_engine_native_progress_status() -> None:
    scratch = _scratch_dir("matrix_v2_engine_native")
    try:
        run_id = "v2-engine-native"
        _write_manifest(
            scratch,
            {
                "run_id": run_id,
                "data_factory_status": "DATA_FACTORY_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "trade_schema_status": "TRADE_SCHEMA_READY",
                "kline_schema_status": "KLINE_SCHEMA_READY",
                "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
                "blocker_codes": [],
            },
        )
        run_dir = scratch / "backtest_strategy_ladder" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "candidate_count": 100,
                    "candidate_truth_status": "CANDIDATE_ENGINE_NATIVE_IN_PROGRESS",
                    "candidate_engine_native_count": 25,
                    "candidate_proxy_count": 75,
                    "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
                    "expected_edge_proxy_count": 25,
                    "expected_edge_governed_count": 0,
                    "engine_native_status": "ENGINE_NATIVE_MATERIALIZING",
                    "engine_native_records_built": 125,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "raw_window_extraction_status": "RAW_WINDOW_READY",
                    "detailed_replay_status": "DETAILED_REPLAY_NOT_PROVEN",
                    "raw_window_count": 100,
                }
            ),
            encoding="utf-8",
        )

        matrix = build_backtest_proof_matrix(output_root=scratch, run_id=run_id)

        assert matrix.engine_native_status == "ENGINE_NATIVE_MATERIALIZING"
        assert matrix.candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_IN_PROGRESS"
        assert matrix.candidate_engine_native_count == 25
        assert matrix.candidate_proxy_count == 75
        assert matrix.engine_native_records_built == 125
        gaps = {entry.metric_name: entry.status for entry in matrix.metric_gaps}
        assert gaps["engine_native_status"] == "PARTIAL"
        assert gaps["expected_edge_truth_status"] == "BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
