"""CLI launcher for Bybit raw-kline recollection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.bybit_kline_recollection import (  # noqa: E402
    recollect_bybit_kline_batch,
    recollect_bybit_kline_days,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in str(raw_value or "").split(",") if part.strip())


def _progress(message: str) -> None:
    print(message, flush=True)


def _probe_report_root_writable(path: Path) -> tuple[bool, str | None]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".write_probe_{uuid4().hex}.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return False, str(exc)
    return True, None


def _resolve_report_root(raw_value: str, *, fallback_root: Path | None = None) -> Path:
    requested = Path(raw_value).resolve()
    writable, reason = _probe_report_root_writable(requested)
    if writable:
        return requested
    fallback = (fallback_root or (REPO_ROOT / "tmp_bybit_missing_kline_repair")).resolve()
    fallback_writable, fallback_reason = _probe_report_root_writable(fallback)
    if not fallback_writable:
        raise OSError(
            "Requested report root is not writable and fallback also failed: "
            f"requested={requested} reason={reason}; fallback={fallback} reason={fallback_reason}"
        )
    _progress(f"[Warn] report root not writable: {requested}")
    if reason:
        _progress(f"[Warn] write probe failed: {reason}")
    _progress(f"[Warn] falling back to writable report root: {fallback}")
    return fallback


def _summarize_report(report: dict[str, Any]) -> None:
    mode = str(report.get("mode") or "SINGLE_SYMBOL")
    batch_status = str(report.get("batch_status") or "UNKNOWN")
    _progress("")
    _progress(f"[Summary] mode={mode} status={batch_status}")
    report_path = report.get("report_path")
    if report_path:
        _progress(f"[Summary] main report: {report_path}")
    audit_report_path = report.get("audit_report_path")
    if audit_report_path:
        _progress(f"[Summary] scope audit: {audit_report_path}")
    if mode == "AUDIT_ONLY":
        _progress(f"[Summary] eligible pairs: {report.get('eligible_pair_count', 0)}")
        return
    pair_reports = report.get("pair_reports")
    if isinstance(pair_reports, list):
        for pair_report in pair_reports:
            if not isinstance(pair_report, dict):
                continue
            symbol = str(pair_report.get("symbol") or "")
            status = str(pair_report.get("batch_status") or "")
            if status == "SKIPPED_NOT_ELIGIBLE":
                _progress(
                    f"[Summary] {symbol}: skipped ({pair_report.get('eligibility_reason', 'NOT_ELIGIBLE')})"
                )
                continue
            report_root = pair_report.get("report_root")
            if report_root:
                _progress(f"[Summary] {symbol}: pair report root -> {report_root}")
            resume_state_path = pair_report.get("resume_state_path")
            if resume_state_path:
                _progress(f"[Summary] {symbol}: resume state -> {resume_state_path}")
            entries = pair_report.get("entries")
            if isinstance(entries, list):
                repaired = 0
                dry_ready = 0
                resumed = 0
                skipped_complete = 0
                failed = 0
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    repair_status = str(entry.get("repair_status") or "")
                    if repair_status == "REPAIRED":
                        repaired += 1
                    elif repair_status == "DRY_RUN_READY":
                        dry_ready += 1
                    elif repair_status == "SKIPPED_RESUME_STATE":
                        resumed += 1
                    elif repair_status == "SKIPPED_EXISTING_COMPLETE":
                        skipped_complete += 1
                    elif repair_status in {"FETCH_FAILED", "VALIDATION_FAILED"}:
                        failed += 1
                _progress(
                    f"[Summary] {symbol}: repaired={repaired} dry_run_ready={dry_ready} resumed={resumed} skipped_complete={skipped_complete} failed={failed}"
                )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recollect incomplete raw Bybit kline day files with strict validation."
    )
    parser.add_argument(
        "--symbol",
        default="",
        help="Spot symbol to repair, for example BTCUSDT.",
    )
    parser.add_argument(
        "--pairs",
        default="",
        help="Comma-separated pair list for batch mode. Leave empty to auto-discover from kline root.",
    )
    parser.add_argument(
        "--timeframes",
        default="1m,10m",
        help="Comma-separated timeframe list, for example 1m,10m.",
    )
    parser.add_argument(
        "--start-date",
        default="",
        help="Inclusive UTC day start in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        default="",
        help="Inclusive UTC day end in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--kline-root",
        default=r"L:\klines",
        help=r"Raw kline root, for example L:\klines.",
    )
    parser.add_argument(
        "--orderbook-root",
        default="",
        help=r"Optional orderbook root, for example J:\ordre book suite.",
    )
    parser.add_argument(
        "--report-root",
        default=str(REPO_ROOT / "tmp_bybit_missing_kline_repair"),
        help="Directory where the audit report JSON is written.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="HTTP timeout per Bybit page request.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate without replacing the raw CSV files.",
    )
    parser.add_argument(
        "--force-fetch",
        action="store_true",
        help="Fetch again even if the existing file already validates as complete.",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Inspect pair/date coverage and write audit reports without downloading anything.",
    )
    parser.add_argument(
        "--require-orderbook",
        action="store_true",
        help="Restrict eligible repair windows to pairs and dates that have orderbook coverage.",
    )
    parser.add_argument(
        "--no-bound-start-to-orderbook",
        action="store_true",
        help="Do not clip the effective start date to the first orderbook day.",
    )
    parser.add_argument(
        "--no-bound-end-to-orderbook",
        action="store_true",
        help="Do not clip the effective end date to the last orderbook day.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable progress resume state and page-cache reuse.",
    )
    parser.add_argument(
        "--stop-after-targets",
        type=int,
        default=0,
        help="Testing knob: stop after N target files to verify resume behavior.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full JSON report at the end.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    timeframes = _csv_tuple(args.timeframes)
    pairs = _csv_tuple(args.pairs)
    has_batch_request = bool(args.orderbook_root or pairs)
    report_root = _resolve_report_root(args.report_root)
    _progress("[Start] Bybit missing-kline recollection")
    _progress(f"[Config] kline root: {Path(args.kline_root).resolve()}")
    if args.orderbook_root:
        _progress(f"[Config] orderbook root: {Path(args.orderbook_root).resolve()}")
    _progress(f"[Config] report root: {report_root}")
    _progress("[Config] repaired files are written in place under the kline root")
    _progress("[Config] resume/cache files are written under the report root")
    _progress(f"[Config] timeframes: {','.join(timeframes)}")
    if args.dry_run:
        _progress("[Mode] dry-run: raw CSV files will NOT be replaced")
    if args.audit_only:
        _progress("[Mode] audit-only: no download")
    if has_batch_request:
        if pairs:
            _progress(f"[Config] requested pairs: {','.join(pairs)}")
        else:
            _progress("[Config] requested pairs: auto-discovery from kline/orderbook roots")
        report = recollect_bybit_kline_batch(
            timeframes=timeframes,
            kline_root=Path(args.kline_root),
            report_root=report_root,
            orderbook_root=Path(args.orderbook_root) if args.orderbook_root else None,
            pairs=pairs or None,
            start_date=args.start_date or None,
            end_date=args.end_date or None,
            require_orderbook=bool(args.require_orderbook),
            bound_start_to_orderbook=not bool(args.no_bound_start_to_orderbook),
            bound_end_to_orderbook=not bool(args.no_bound_end_to_orderbook),
            audit_only=bool(args.audit_only),
            dry_run=bool(args.dry_run),
            force_fetch=bool(args.force_fetch),
            timeout_s=int(args.timeout_seconds),
            resume=not bool(args.no_resume),
            stop_after_targets=int(args.stop_after_targets or 0) or None,
            progress=_progress,
        )
    else:
        if not args.symbol:
            parser.error("--symbol is required when batch mode is not used.")
        if not args.start_date or not args.end_date:
            parser.error("--start-date and --end-date are required in single-symbol mode.")
        _progress(f"[Config] symbol: {args.symbol}")
        report = recollect_bybit_kline_days(
            symbol=args.symbol,
            timeframes=timeframes,
            start_date=args.start_date,
            end_date=args.end_date,
            kline_root=Path(args.kline_root),
            report_root=report_root,
            dry_run=bool(args.dry_run),
            force_fetch=bool(args.force_fetch),
            timeout_s=int(args.timeout_seconds),
            resume=not bool(args.no_resume),
            stop_after_targets=int(args.stop_after_targets or 0) or None,
            progress=_progress,
        )
    _summarize_report(report)
    if args.json:
        _progress("")
        print(json.dumps(report, indent=2), flush=True)
    if str(report.get("batch_status")) == "BYBIT_KLINE_RECOLLECTION_READY":
        return 0
    if str(report.get("batch_status")) == "BYBIT_KLINE_RECOLLECTION_PARTIAL":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
