from __future__ import annotations

import csv
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlparse

from scripts import run_bybit_kline_recollection as bybit_kline_cli
from local_replay_runtime.bybit_kline_recollection import (
    audit_bybit_recollection_scope,
    recollect_bybit_kline_batch,
    recollect_bybit_kline_days,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("bybit_kline_recollection_tests", label)


def _write_csv_day(
    path: Path,
    *,
    start_timestamp_ms: int,
    rows: int,
    interval_ms: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("startTime", "open", "high", "low", "close", "volume", "turnover"))
        for index in range(rows):
            start_ms = start_timestamp_ms + (index * interval_ms)
            writer.writerow((start_ms, "63000", "63001", "62999", "63000", "1", "63000"))


def _build_kline_rows(day: date, *, interval_ms: int) -> list[list[str]]:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    rows: list[list[str]] = []
    cursor = start
    end = start + timedelta(days=1)
    while cursor < end:
        start_ms = int(cursor.timestamp() * 1000)
        rows.append(
            [
                str(start_ms),
                "63000",
                "63050",
                "62950",
                "63010",
                "12.5",
                "787625",
            ]
        )
        cursor += timedelta(milliseconds=interval_ms)
    return rows


def _write_orderbook_day(root: Path, symbol: str, day: date) -> None:
    target = root / symbol / f"{day.isoformat()}_{symbol}_ob200.data"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{day.isoformat()}_{symbol}_ob200.data").write_text(
        '{"ts":1,"type":"snapshot","data":{"s":"%s"}}\n' % symbol,
        encoding="utf-8",
    )


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_recollection_paginates_1m_and_repairs_file() -> None:
    scratch = _scratch_dir("paginate_1m")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "klines"
        report_root = scratch / "reports"
        target_path = raw_root / "BTCUSDT" / "1" / "2025" / "BTCUSDT_1_2025-07-25.csv"
        day = date(2025, 7, 25)
        full_rows = _build_kline_rows(day, interval_ms=60_000)

        def _fake_http_get(request, timeout=20):  # noqa: ANN001
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            end_ms = int(query["end"][0])
            day_start_ms = int(query["start"][0])
            first_page_floor = day_start_ms + (440 * 60_000)
            if end_ms >= day_start_ms + (1439 * 60_000):
                rows = [row for row in full_rows if int(row[0]) >= first_page_floor]
            else:
                rows = [row for row in full_rows if int(row[0]) < first_page_floor]
            rows = list(reversed(rows))
            return _FakeResponse({"retCode": 0, "result": {"list": rows}})

        report = recollect_bybit_kline_days(
            symbol="BTCUSDT",
            timeframes=("1m",),
            start_date="2025-07-25",
            end_date="2025-07-25",
            kline_root=raw_root,
            report_root=report_root,
            http_get=_fake_http_get,
        )

        assert report["batch_status"] == "BYBIT_KLINE_RECOLLECTION_READY"
        assert target_path.is_file()
        written_lines = target_path.read_text(encoding="utf-8").splitlines()
        assert len(written_lines) == 1441
        entry = report["entries"][0]
        assert entry["repair_status"] == "REPAIRED"
        assert entry["fetched_page_count"] == 2
        assert entry["validation"]["row_count"] == 1440
        assert entry["validation"]["first_timestamp_utc"] == "2025-07-25T00:00:00+00:00"
        assert entry["validation"]["last_timestamp_utc"] == "2025-07-25T23:59:00+00:00"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_recollection_validates_10m_full_day() -> None:
    scratch = _scratch_dir("validate_10m")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "klines"
        report_root = scratch / "reports"
        day = date(2025, 7, 26)
        full_rows = list(reversed(_build_kline_rows(day, interval_ms=60_000)))

        def _fake_http_get(request, timeout=20):  # noqa: ANN001
            return _FakeResponse({"retCode": 0, "result": {"list": full_rows}})

        report = recollect_bybit_kline_days(
            symbol="BTCUSDT",
            timeframes=("10m",),
            start_date="2025-07-26",
            end_date="2025-07-26",
            kline_root=raw_root,
            report_root=report_root,
            http_get=_fake_http_get,
        )

        entry = report["entries"][0]
        assert report["batch_status"] == "BYBIT_KLINE_RECOLLECTION_READY"
        assert entry["repair_status"] == "REPAIRED"
        assert entry["collection_mode"] == "BYBIT_PUBLIC_1M_AGGREGATED_TO_10M"
        assert entry["validation"]["row_count"] == 144
        assert entry["validation"]["first_timestamp_utc"] == "2025-07-26T00:00:00+00:00"
        assert entry["validation"]["last_timestamp_utc"] == "2025-07-26T23:50:00+00:00"
        assert (raw_root / "BTCUSDT" / "10" / "BTCUSDT_10_2025-07-26.csv").is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_recollection_dry_run_preserves_existing_incomplete_file() -> None:
    scratch = _scratch_dir("dry_run_existing")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "klines"
        report_root = scratch / "reports"
        target_path = raw_root / "BTCUSDT" / "1" / "2025" / "BTCUSDT_1_2025-07-25.csv"
        _write_csv_day(
            target_path,
            start_timestamp_ms=int(datetime(2025, 7, 25, 7, 20, tzinfo=UTC).timestamp() * 1000),
            rows=1000,
            interval_ms=60_000,
        )
        original_text = target_path.read_text(encoding="utf-8")
        day = date(2025, 7, 25)
        full_rows = list(reversed(_build_kline_rows(day, interval_ms=60_000)))

        def _fake_http_get(request, timeout=20):  # noqa: ANN001
            return _FakeResponse({"retCode": 0, "result": {"list": full_rows}})

        report = recollect_bybit_kline_days(
            symbol="BTCUSDT",
            timeframes=("1m",),
            start_date="2025-07-25",
            end_date="2025-07-25",
            kline_root=raw_root,
            report_root=report_root,
            dry_run=True,
            http_get=_fake_http_get,
        )

        entry = report["entries"][0]
        assert report["batch_status"] == "BYBIT_KLINE_RECOLLECTION_READY"
        assert entry["repair_status"] == "DRY_RUN_READY"
        assert entry["existing_file"]["status"] == "INCOMPLETE"
        assert entry["existing_file"]["validation"]["row_count"] == 1000
        assert target_path.read_text(encoding="utf-8") == original_text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_audit_scope_uses_orderbook_bounded_window_and_flags_missing_orderbook_pairs() -> None:
    scratch = _scratch_dir("audit_scope")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "klines"
        orderbook_root = scratch / "orderbook"
        start_day = date(2025, 4, 29)
        next_day = date(2025, 4, 30)
        _write_orderbook_day(orderbook_root, "SOLUSDT", start_day)
        _write_orderbook_day(orderbook_root, "SOLUSDT", next_day)
        _write_csv_day(
            raw_root / "SOLUSDT" / "1" / "2025" / "SOLUSDT_1_2025-04-29.csv",
            start_timestamp_ms=int(datetime(2025, 4, 29, 7, 20, tzinfo=UTC).timestamp() * 1000),
            rows=1000,
            interval_ms=60_000,
        )
        _write_csv_day(
            raw_root / "SOLUSDT" / "1" / "2025" / "SOLUSDT_1_2025-04-30.csv",
            start_timestamp_ms=int(datetime(2025, 4, 30, 7, 20, tzinfo=UTC).timestamp() * 1000),
            rows=1000,
            interval_ms=60_000,
        )
        _write_csv_day(
            raw_root / "ADAUSDT" / "1" / "2025" / "ADAUSDT_1_2025-04-29.csv",
            start_timestamp_ms=int(datetime(2025, 4, 29, 7, 20, tzinfo=UTC).timestamp() * 1000),
            rows=1000,
            interval_ms=60_000,
        )

        report = audit_bybit_recollection_scope(
            kline_root=raw_root,
            timeframes=("1m",),
            orderbook_root=orderbook_root,
            require_orderbook=True,
        )

        assert report["eligible_pair_count"] == 1
        sol_report = next(item for item in report["pair_reports"] if item["symbol"] == "SOLUSDT")
        ada_report = next(item for item in report["pair_reports"] if item["symbol"] == "ADAUSDT")
        assert sol_report["effective_start_date"] == "2025-04-29"
        assert sol_report["effective_end_date"] == "2025-04-30"
        assert sol_report["timeframe_reports"]["1m"]["incomplete_day_count"] == 2
        assert not ada_report["eligible_for_v53_orderbook_bounded_recollection"]
        assert ada_report["eligibility_reason"] == "ORDERBOOK_MISSING"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_batch_resume_reuses_state_and_continues_after_stop() -> None:
    scratch = _scratch_dir("batch_resume")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "klines"
        orderbook_root = scratch / "orderbook"
        report_root = scratch / "reports"
        for symbol in ("SOLUSDT", "XRPUSDT"):
            for day in (date(2025, 4, 29), date(2025, 4, 30)):
                _write_orderbook_day(orderbook_root, symbol, day)

        call_counter = {"count": 0}

        def _fake_http_get(request, timeout=20):  # noqa: ANN001
            call_counter["count"] += 1
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            day_start_ms = int(query["start"][0])
            end_ms = int(query["end"][0])
            day = datetime.fromtimestamp(day_start_ms / 1000, tz=UTC).date()
            full_rows = _build_kline_rows(day, interval_ms=60_000)
            first_page_floor = day_start_ms + (440 * 60_000)
            if end_ms >= day_start_ms + (1439 * 60_000):
                rows = [row for row in full_rows if int(row[0]) >= first_page_floor]
            else:
                rows = [row for row in full_rows if int(row[0]) < first_page_floor]
            rows = list(reversed(rows))
            return _FakeResponse({"retCode": 0, "result": {"list": rows}})

        first_run = recollect_bybit_kline_batch(
            timeframes=("1m",),
            kline_root=raw_root,
            report_root=report_root,
            orderbook_root=orderbook_root,
            require_orderbook=True,
            dry_run=True,
            http_get=_fake_http_get,
            stop_after_targets=1,
        )

        assert first_run["batch_status"] == "BYBIT_KLINE_RECOLLECTION_PARTIAL"
        first_call_count = call_counter["count"]
        second_run = recollect_bybit_kline_batch(
            timeframes=("1m",),
            kline_root=raw_root,
            report_root=report_root,
            orderbook_root=orderbook_root,
            require_orderbook=True,
            dry_run=True,
            http_get=_fake_http_get,
        )

        assert second_run["batch_status"] == "BYBIT_KLINE_RECOLLECTION_READY"
        assert call_counter["count"] > first_call_count
        sol_report = next(item for item in second_run["pair_reports"] if item["symbol"] == "SOLUSDT")
        assert any(entry["repair_status"] == "SKIPPED_RESUME_STATE" for entry in sol_report["entries"])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_cli_report_root_falls_back_to_writable_location(monkeypatch) -> None:
    scratch = _scratch_dir("cli_report_root_fallback")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        requested = (scratch / "blocked").resolve()
        fallback = (scratch / "fallback").resolve()
        messages: list[str] = []

        def _fake_probe(path: Path) -> tuple[bool, str | None]:
            if path == requested:
                return False, "access denied"
            if path == fallback:
                path.mkdir(parents=True, exist_ok=True)
                return True, None
            raise AssertionError(f"Unexpected probe path: {path}")

        monkeypatch.setattr(bybit_kline_cli, "_probe_report_root_writable", _fake_probe)
        monkeypatch.setattr(bybit_kline_cli, "_progress", messages.append)

        resolved = bybit_kline_cli._resolve_report_root(str(requested), fallback_root=fallback)

        assert resolved == fallback
        assert any("report root not writable" in message for message in messages)
        assert any(str(fallback) in message for message in messages)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
