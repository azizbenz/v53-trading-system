"""Post-A2 audit checklist — read the canonical V5.3 reports and emit
a structured pass/fail verdict so the operator knows whether the run is
ready for downstream B1/B2 or IA Lab training.

Exit codes:
  0  audit GREEN (anti-leakage OK, data quality OK, no critical blockers)
  1  audit YELLOW (anti-leakage OK but doctrinal blockers present — usual case)
  2  audit RED (anti-leakage failed OR data quality issue OR critical blocker)
  3  reports missing (run incomplete)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        required=True,
        help="phase_a2_data_factory directory of the completed run.",
    )
    return parser.parse_args(argv)


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _check(label: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    flag = "✓" if condition else "✗"
    color = "OK" if condition else "FAIL"
    line = f"  [{flag}] {label:48s} {color}"
    if detail:
        line += f"  ({detail})"
    return condition, line


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"[ERROR] run_dir does not exist: {run_dir}", file=sys.stderr)
        return 3

    print(f"\n=== A2 AUDIT REPORT — {run_dir} ===\n")

    progress = _load_json(run_dir / "a2_gold_progress_report.json")
    prod_safety = _load_json(run_dir / "data_factory_prod_safety_report.json")
    anti_leakage = _load_json(run_dir / "anti_leakage_precheck_report.json")
    data_quality = _load_json(run_dir / "data_quality_report.json")
    proof_matrix = _load_json(run_dir / "backtest_proof_matrix.json")

    if not progress and not prod_safety and not anti_leakage:
        print("[ERROR] none of the canonical A2 reports found — run incomplete?")
        return 3

    # === SECTION 1 : Progress / completeness ===
    print("[1] PROGRESS / COMPLETENESS")
    status = str(progress.get("status") or "?")
    stage = str(progress.get("current_stage") or "?")
    counters = progress.get("counters") or {}
    rows_processed = int(counters.get("rows_processed", 0) or 0)
    rows_rejected = int(counters.get("rows_rejected", 0) or 0)
    silver_n = int(counters.get("silver_entry_count", 0) or 0)
    gold_n = int(counters.get("gold_feature_row_count", 0) or 0)

    section1_ok = True
    ok, line = _check("A2 status == A2_COMPLETE or DATA_FACTORY_READY",
                       status in {"A2_COMPLETE", "A2_RUNNING"} and
                       "COMPLETE" in stage,
                       f"status={status} stage={stage}")
    print(line); section1_ok &= ok
    ok, line = _check("rows_processed > 0", rows_processed > 0, f"{rows_processed:,}")
    print(line); section1_ok &= ok
    ok, line = _check("rows_rejected == 0", rows_rejected == 0, f"{rows_rejected}")
    print(line); section1_ok &= ok
    ok, line = _check("silver_entry_count > 0", silver_n > 0, f"{silver_n}")
    print(line); section1_ok &= ok
    ok, line = _check("gold_feature_row_count > 0", gold_n > 0, f"{gold_n}")
    print(line); section1_ok &= ok

    # === SECTION 2 : Anti-leakage (critical) ===
    print("\n[2] ANTI-LEAKAGE (critical — fail = RED)")
    al_status = str(anti_leakage.get("status") or "MISSING")
    al_blockers = list(anti_leakage.get("blocker_codes") or [])
    section2_ok = True
    expected_checks = (
        "feature_timestamp_aligned",
        "no_future_features",
        "label_window_after_decision",
        "random_split_forbidden",
        "purge_window_declared",
        "embargo_window_declared",
        "feature_hash_stable",
        "dataset_hash_stable",
        "source_refs_non_empty",
    )
    for k in expected_checks:
        v = str(anti_leakage.get(k) or "MISSING")
        is_ok = v not in {"MISSING", ""} and "BLOCKED" not in v and "NOT" not in v
        ok, line = _check(k, is_ok, v)
        print(line); section2_ok &= ok
    ok, line = _check("blocker_codes empty", len(al_blockers) == 0,
                       str(al_blockers))
    print(line); section2_ok &= ok
    ok, line = _check("status DATA_SCIENCE_READY_FOR_RESEARCH",
                       al_status == "DATA_SCIENCE_READY_FOR_RESEARCH", al_status)
    print(line); section2_ok &= ok

    # === SECTION 3 : Prod safety verdict ===
    print("\n[3] PROD SAFETY VERDICT (doctrinal, yellow = expected)")
    ps_status = str(prod_safety.get("prod_safety_status") or "MISSING")
    ps_safe = bool(prod_safety.get("prod_safe", False))
    ps_blockers = list(prod_safety.get("blocker_codes") or [])
    print(f"  status         : {ps_status}")
    print(f"  prod_safe      : {ps_safe}")
    print(f"  blocker_codes  : {ps_blockers}")
    doctrinal_only = all(
        b in {"RAW_SOURCE_TYPE_INFERRED", "CURRENT_METADATA_PROXY",
              "SINGLE_PAIR_RESEARCH_ONLY", "MULTI_PAIR_RESEARCH_ONLY"}
        for b in ps_blockers
    )
    if doctrinal_only:
        print("  → blockers are DOCTRINAL only (provenance/scope), not A2 bugs")

    # === SECTION 4 : Data quality ===
    print("\n[4] DATA QUALITY")
    section4_ok = True
    dq_status = str(data_quality.get("data_factory_status") or "?")
    dq_rows_rejected = int(data_quality.get("rows_rejected", 0) or 0)
    ok, line = _check("data_factory_status READY",
                       "READY" in dq_status, dq_status)
    print(line); section4_ok &= ok
    ok, line = _check("rows_rejected == 0",
                       dq_rows_rejected == 0, f"{dq_rows_rejected}")
    print(line); section4_ok &= ok
    for k in ("trade_schema_status", "kline_schema_status",
              "orderbook_schema_status", "metadata_schema_status"):
        v = str(data_quality.get(k) or "?")
        is_ok = "READY" in v
        ok, line = _check(k, is_ok, v)
        print(line); section4_ok &= ok

    # === SECTION 5 : Coverage ===
    print("\n[5] COVERAGE")
    coverage = prod_safety.get("coverage") or {}
    section5_ok = True
    for kind in ("trades", "klines", "orderbook", "orderbook_depth20"):
        cov = coverage.get(kind) or {}
        cov_status = str(cov.get("status") or "?")
        observed = cov.get("observed_dates") or []
        is_ok = "COVERED" in cov_status
        ok, line = _check(f"{kind} coverage",
                           is_ok, f"{cov_status} ({len(observed)} dates)")
        print(line); section5_ok &= ok

    # === FINAL VERDICT ===
    print("\n=== VERDICT ===")
    if section2_ok and section1_ok and section4_ok and section5_ok:
        if doctrinal_only and not ps_safe:
            print("YELLOW : A2 OK pour DEV iteration (anti-leakage + quality green ;")
            print("         prod_safe=False car blockers doctrinaux upstream)")
            print("         → ready for B1+B2 backtest + B_ML training")
            return 1
        elif ps_safe:
            print("GREEN  : A2 fully prod-safe — ready for shadow/live promotion")
            return 0
        else:
            print("YELLOW : A2 OK pour DEV mais non-doctrinal blockers présents")
            return 1
    else:
        print("RED    : section(s) failed — A2 NOT suitable for downstream")
        if not section1_ok:
            print("         → progress/completeness failure")
        if not section2_ok:
            print("         → anti-leakage failure (CRITICAL)")
        if not section4_ok:
            print("         → data quality failure")
        if not section5_ok:
            print("         → coverage failure")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
