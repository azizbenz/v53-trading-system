"""Read-only Backbone parity audit for Strategy Ladder B2 backtests.

The builder in this module inspects existing run artifacts and source imports.
It does not modify replay records, trading decisions, engines, or thresholds.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from typing import Any

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


BACKTEST_BACKBONE_PARITY_AUDIT_FILENAME = "backtest_backbone_parity_audit.json"
BACKTEST_DECISION_SOURCE_MATRIX_FILENAME = "backtest_decision_source_matrix.json"
BACKBONE_MODULE_USAGE_MATRIX_FILENAME = "backbone_module_usage_matrix.json"
BACKTEST_LOCAL_REPLAY_DEPENDENCY_AUDIT_FILENAME = (
    "backtest_local_replay_dependency_audit.json"
)
PARALLEL_LOGIC_AND_PROXY_SURFACE_AUDIT_FILENAME = (
    "parallel_logic_and_proxy_surface_audit.json"
)
COUNT_SEMANTICS_DEEP_AUDIT_FILENAME = "count_semantics_deep_audit.json"
REASON_CODE_TAXONOMY_AUDIT_FILENAME = "reason_code_taxonomy_audit.json"
EXECUTED_REASON_CODE_CONSISTENCY_AUDIT_FILENAME = (
    "executed_reason_code_consistency_audit.json"
)
ENGINE_NATIVE_RUNNER_INVOCATION_AUDIT_FILENAME = (
    "engine_native_runner_invocation_audit.json"
)
B2_COST_BLOCKER_COMPONENT_AUDIT_FILENAME = "b2_cost_blocker_component_audit.json"
ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY_FILENAME = "engine_a_executed_candidate_autopsy.json"
EXECUTED_RECORD_INVARIANT_REPORT_FILENAME = "executed_record_invariant_report.json"
BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME = (
    "backtest_backbone_parity_final_report.json"
)
BACKTEST_BACKBONE_PARITY_PATCH_FINAL_VERDICT_FILENAME = (
    "backtest_backbone_parity_patch_final_verdict.json"
)

BACKBONE_MODULES = (
    "data_backbone",
    "execution_backbone",
    "meta_learning",
    "portfolio_minimal",
    "protocols",
    "complete_enablers",
    "risk_backbone",
    "regime_classifier",
    "scoring_backbone",
    "local_replay_runtime",
)

SELECTED_STATES = frozenset({"executed", "reduced"})
# Patch P0-RENAME-1 (2026-05-27) — both legacy and renamed codes are listed
# so this audit module remains compatible with bucket records produced
# before the runner-not-invoked rename was applied in the strategy ladder
# runner (`B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1`).
LEGACY_ENGINE_NATIVE_NOT_INVOKED_CODES = frozenset(
    {
        "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
        "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1",
    }
)
# Patch P0-SPLIT-1 (2026-05-27) — the legacy `B2_COST_MEASUREMENT_BLOCKED`
# was too coarse: the operator could not tell, from the reason code alone,
# whether the blockage came from a missing spread measurement, a missing
# slippage measurement, or both. The split variants emitted by
# `strategy_ladder_replay_evidence.py` are now listed so this audit
# remains compatible with historical bucket records produced before the
# split was applied.
B2_COST_MEASUREMENT_BLOCKED_SPLIT_VARIANTS = frozenset(
    {
        "B2_COST_MEASUREMENT_BLOCKED",
        "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE",
        "B2_COST_MEASUREMENT_BLOCKED_SPREAD_ONLY",
        "B2_COST_MEASUREMENT_BLOCKED_SLIPPAGE_ONLY",
    }
)
CONTRADICTORY_EXECUTED_BLOCKERS = frozenset(
    {
        "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
        "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1",
        "ENGINE_NATIVE_NO_TRADE",
        "B2_COST_MEASUREMENT_BLOCKED",
        "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE",
        "B2_COST_MEASUREMENT_BLOCKED_SPREAD_ONLY",
        "B2_COST_MEASUREMENT_BLOCKED_SLIPPAGE_ONLY",
        "cost_infeasible",
        "break_even_not_cleared",
        "non_long_direction",
    }
)
PROMOTION_READY_FILL_STATUSES = frozenset(
    {"FILL_REALISM_SHADOW_MEASURED", "FILL_REALISM_PROVEN"}
)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
    except OSError:
        return []
    return rows


def _json_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.rglob("*.json") if path.is_file()))


def _load_bucket_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _json_files(run_dir / "detailed_replay" / "by_bucket"):
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            row = dict(payload)
            row["_artifact_path"] = str(path.resolve())
            rows.append(row)
    return rows


def _load_candidate_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in (
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        run_dir / "preselection_candidates.jsonl",
    ):
        for row in _read_jsonl(path):
            candidate_id = str(row.get("candidate_id") or "")
            key = f"{candidate_id}:{path.name}"
            if candidate_id and key not in seen:
                item = dict(row)
                item["_source_path"] = str(path.resolve())
                rows.append(item)
                seen.add(key)
    return rows


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _as_reason_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return ()


def _reports_dir(run_dir: Path) -> Path:
    return run_dir / "reports"


def _repo_scan_files(repo_root: Path) -> tuple[Path, ...]:
    roots = [repo_root / "src" / "local_replay_runtime", repo_root / "src" / "cockpit", repo_root / "scripts"]
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(path for path in root.rglob("*.py") if path.is_file())
    return tuple(sorted(files))


def _source_lines_for_module(repo_root: Path, module: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    import_tokens = (f"from {module}", f"import {module}")
    text_tokens = (module,)
    for path in _repo_scan_files(repo_root):
        if path.name == "backtest_backbone_parity_audit.py":
            continue
        try:
            content = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(content, start=1):
            stripped = line.strip()
            if any(stripped.startswith(token) for token in import_tokens):
                usage_type = "import"
            elif any(token in stripped for token in text_tokens):
                usage_type = "text_reference"
            else:
                continue
            lines.append(
                {
                    "path": str(path.relative_to(repo_root)),
                    "line": index,
                    "usage_type": usage_type,
                    "text": stripped[:220],
                }
            )
    return lines


def _phase_from_entrypoint(path: str) -> str:
    if "data_factory" in path or "gold_microstructure" in path:
        return "A2"
    if "candidate" in path:
        return "B1"
    if "detailed_replay" in path or "runner" in path or "shadow_execution_simulator" in path:
        return "B2"
    if "b_ml" in path or "expected_edge_training" in path or "ml_lab" in path:
        return "B_ML"
    if "decision_report" in path or "audit" in path or "operator" in path:
        return "DecisionReport"
    return "unknown"


def _usage_level(module: str, entries: list[dict[str, Any]]) -> str:
    import_paths = [
        str(entry["path"]).replace("\\", "/")
        for entry in entries
        if entry["usage_type"] == "import"
    ]
    if not import_paths:
        return "not_used"
    if all(path.startswith("scripts/") for path in import_paths) and not any(
        "run_backtest" in path or "strategy_ladder" in path for path in import_paths
    ):
        return "shadow_only"
    if module == "local_replay_runtime":
        return "direct"
    if module in {"protocols", "risk_backbone", "regime_classifier"} and all(
        "shadow" in path or path.startswith("scripts/") for path in import_paths
    ):
        return "shadow_only"
    if module == "execution_backbone" and any(
        "shadow_execution_simulator.py" in path or "replay_execution" in path
        for path in import_paths
    ):
        return "adapter"
    if module in {"scoring_backbone"}:
        return "manifest_only" if not any("shadow" in path for path in import_paths) else "shadow_only"
    if module in {"meta_learning"}:
        return "adapter"
    return "direct"


def _decision_authority(module: str, usage_level: str) -> str:
    if module == "local_replay_runtime":
        return "partial"
    if usage_level == "direct" and module in {"data_backbone"}:
        return "canonical"
    if usage_level in {"direct", "adapter"} and module in {
        "execution_backbone",
        "portfolio_minimal",
        "complete_enablers",
    }:
        return "partial"
    if usage_level in {"shadow_only", "manifest_only", "not_used"}:
        return "none"
    return "proxy"


def _module_gaps(module: str, usage_level: str) -> list[str]:
    gaps_by_module = {
        "data_backbone": ["A2 features and B2 market microstructure are surfaced, but B2 still requires depth/freshness proof before treating them as truth."],
        "execution_backbone": ["B2 uses canonical pieces through a replay/shadow adapter; live parity and adverse selection remain partial."],
        "portfolio_minimal": ["Capital buckets are present and surfaced; independent-signal vs bucket-record counts must remain explicit."],
        "complete_enablers": ["Build-14 support is surfaced as bounded context; upstream filtering must be reported instead of shown as engine absence."],
        "meta_learning": ["Correctly outside B2 training authority; expected-edge artifact remains required for profitability truth."],
        "protocols": ["B2 may reuse protocol contracts/refusal semantics, but transport/runtime services must remain out of B2."],
        "risk_backbone": ["Risk filter is surfaced when explicit limits are supplied; drawdown/loss-budget parity remains partial."],
        "regime_classifier": ["Regime classifier is surfaced when explicit inputs/thresholds are supplied; most B2 records still lack regime-ready features."],
        "scoring_backbone": ["Ranking and hard-block gate surfaces exist, but break-even/ranking parity is not yet canonical end-to-end."],
        "local_replay_runtime": ["Dominant rail; backtest still risks diverging from future shadow/live logical path."],
    }
    if usage_level == "not_used":
        return [*gaps_by_module.get(module, ()), "No effective backtest import found."]
    return gaps_by_module.get(module, [])


def _build_module_usage_matrix(repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for module in BACKBONE_MODULES:
        entries = _source_lines_for_module(repo_root, module)
        level = _usage_level(module, entries)
        phases = tuple(
            sorted(
                {
                    phase
                    for phase in (_phase_from_entrypoint(str(entry["path"])) for entry in entries)
                    if phase != "unknown"
                }
            )
        )
        rows.append(
            {
                "module": f"src/{module}",
                "used_by_backtest": level not in {"not_used", "shadow_only"},
                "usage_level": level,
                "used_in_phase": phases,
                "entrypoints": entries[:25],
                "entrypoint_count": len(entries),
                "decision_authority": _decision_authority(module, level),
                "gaps": _module_gaps(module, level),
                "patch_needed": module
                in {
                    "execution_backbone",
                    "scoring_backbone",
                    "risk_backbone",
                    "regime_classifier",
                    "portfolio_minimal",
                    "meta_learning",
                    "protocols",
                    "complete_enablers",
                    "local_replay_runtime",
                },
            }
        )
    return {
        "schema_version": "v53.backbone_module_usage_matrix.v1",
        "generated_at": _now_iso(),
        "rows": rows,
    }


def _decision_source_matrix() -> dict[str, Any]:
    rows = [
        ("data_loading", "local_replay_runtime+data_backbone", "data_backbone", "partial_canonical", ("strategy_ladder_data_factory.py",), (), "PARITY_PARTIAL"),
        ("feature_computation", "data_backbone via A2 builders", "data_backbone", "partial_canonical", ("strategy_ladder_data_factory.py", "strategy_ladder_engine_native_adapter.py"), (), "PARITY_PARTIAL"),
        ("market_microstructure_context", "data_backbone_market_microstructure surface", "data_backbone", "partial_canonical", ("shadow_execution_simulator.py",), ("DATA_BACKBONE_BOOK_DEPTH20_NOT_PROVEN",), "PARITY_PARTIAL"),
        ("candidate_generation", "local_replay_runtime", "engines A/B/C/D + scoring_backbone", "adapter", ("strategy_ladder_candidate_discovery.py",), ("ENGINE_NATIVE_A_B_C_D_RUNNER",), "PARITY_PARTIAL"),
        ("engine_decision", "engines via local_replay_runtime adapter", "engines A/B/C/D", "partial_canonical", ("strategy_ladder_engine_native_adapter.py",), (), "PARITY_PARTIAL"),
        ("scoring", "scoring_backbone surfaces plus engine/local reports", "scoring_backbone", "partial_canonical", ("shadow_execution_simulator.py", "strategy_ladder_runner.py"), (), "PARITY_PARTIAL"),
        ("break_even", "engine/replay economics", "scoring_backbone", "proxy", ("strategy_ladder_runner.py",), ("BREAK_EVEN_PROXY_BLOCKED",), "PARITY_CONFLICT"),
        ("risk_filtering", "risk_backbone surface when explicit limits supplied", "risk_backbone", "partial_canonical", ("shadow_execution_simulator.py",), (), "PARITY_PARTIAL"),
        ("execution_intent", "execution_backbone adapter", "execution_backbone", "partial_canonical", ("shadow_execution_simulator.py",), (), "PARITY_PARTIAL"),
        ("spread_measurement", "replay evidence/book reconstruction", "execution_backbone", "partial_canonical", ("strategy_ladder_replay_evidence.py",), ("SPREAD_MODEL_PROXY",), "PARITY_PARTIAL"),
        ("slippage_measurement", "execution_backbone depth20 via replay adapter", "execution_backbone", "partial_canonical", ("shadow_execution_simulator.py",), ("SLIPPAGE_MODEL_PROXY",), "PARITY_PARTIAL"),
        ("fee_measurement", "execution_backbone fee meter / metadata", "execution_backbone", "partial_canonical", ("shadow_execution_simulator.py",), (), "PARITY_PARTIAL"),
        ("partial_fill", "execution_backbone partial fill meter", "execution_backbone", "partial_canonical", ("shadow_execution_simulator.py",), (), "PARITY_PARTIAL"),
        ("adverse_selection", "execution_backbone meter blocked by entry dependency", "execution_backbone", "proxy", ("shadow_execution_simulator.py",), ("ADVERSE_SELECTION_PROXY",), "PARITY_CONFLICT"),
        ("portfolio_update", "portfolio_minimal capital viability surface", "portfolio_minimal", "partial_canonical", ("shadow_execution_simulator.py", "strategy_ladder_runner.py"), (), "PARITY_PARTIAL"),
        ("regime_classification", "regime_classifier surface when inputs are present", "regime_classifier", "partial_canonical", ("shadow_execution_simulator.py",), ("REGIME_CLASSIFIER_INPUTS_MISSING",), "PARITY_PARTIAL"),
        ("expected_edge_ml_overlay", "meta_learning surface; B2 training disabled", "meta_learning", "adapter", ("shadow_execution_simulator.py", "strategy_ladder_runner.py"), ("EXPECTED_EDGE_PROXY_BLOCKED",), "PARITY_PARTIAL"),
        ("build14_complete_enablers", "complete_enablers context surface", "complete_enablers", "adapter", ("shadow_execution_simulator.py",), ("COMPLETE_ENABLERS_FILTERED_UPSTREAM",), "PARITY_PARTIAL"),
        ("refusal_logging", "protocol contracts/refusal ledgers without transport", "protocols", "adapter", ("shadow_execution_simulator.py", "strategy_ladder_operator_artifacts.py"), (), "PARITY_PARTIAL"),
        ("promotion_verdict", "local promotion reports", "risk/scoring/protocols", "partial_canonical", ("promotion_artifact_builder.py",), (), "PARITY_PARTIAL"),
    ]
    return {
        "schema_version": "v53.backtest_decision_source_matrix.v1",
        "generated_at": _now_iso(),
        "rows": [
            {
                "surface": surface,
                "current_source": current,
                "canonical_expected_source": expected,
                "actual_status": status,
                "evidence_files": evidence,
                "reason_codes": reason_codes,
                "parity_status": parity,
            }
            for surface, current, expected, status, evidence, reason_codes, parity in rows
        ],
    }


def _count_semantics(
    *,
    summary: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_rows = [
        row for row in bucket_rows if str(row.get("execution_state") or "").lower() in SELECTED_STATES
    ]
    executed_rows = [
        row for row in bucket_rows if str(row.get("execution_state") or "").lower() == "executed"
    ]
    selected_candidates = {str(row.get("candidate_id") or "") for row in selected_rows if row.get("candidate_id")}
    executed_candidates = {str(row.get("candidate_id") or "") for row in executed_rows if row.get("candidate_id")}
    capital_buckets = {str(row.get("capital_bucket") or "") for row in bucket_rows if row.get("capital_bucket") is not None}
    factor = (
        round(len(executed_rows) / len(executed_candidates), 6)
        if executed_candidates
        else 0.0
    )
    legacy_executed = _as_int(summary.get("executed_trade_count")) or len(executed_rows)
    verdict = "COUNT_SEMANTICS_OK"
    if len(executed_rows) != len(executed_candidates) and executed_candidates:
        verdict = "COUNT_SEMANTICS_BUCKET_EXPANSION_CONFUSING"
    if legacy_executed not in {0, len(executed_rows), len(executed_candidates)}:
        verdict = "COUNT_SEMANTICS_INCONSISTENT"
    return {
        "schema_version": "v53.count_semantics_deep_audit.v1",
        "generated_at": _now_iso(),
        "candidate_count": _as_int(summary.get("candidate_count")) or len(candidate_rows),
        "unique_candidate_count": len({str(row.get("candidate_id") or "") for row in candidate_rows if row.get("candidate_id")}),
        "selected_candidate_count": len(selected_candidates),
        "selected_bucket_record_count": len(selected_rows),
        "executed_candidate_count": len(executed_candidates),
        "executed_bucket_record_count": len(executed_rows),
        "independent_signal_count": len(executed_candidates),
        "independent_executed_signal_count": len(executed_candidates),
        "capital_bucket_count": len(capital_buckets),
        "capital_bucket_expansion_factor": factor,
        "legacy_executed_count_reported": legacy_executed,
        "operator_note": (
            f"{len(executed_rows)} bucket execution records, not "
            f"{len(executed_candidates)} independent trading signals"
            if executed_candidates
            else "no executed signals"
        ),
        "verdict": verdict,
    }


def _classify_reason_code(code: str, *, execution_state: str) -> str:
    if execution_state == "executed" and code in CONTRADICTORY_EXECUTED_BLOCKERS:
        return "previous_stage_reason_codes"
    if code in {
        "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
        "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1",
        "ENGINE_NATIVE_INPUT_BUILDER_FAILED_NO_RAW_WINDOW",
    }:
        return "previous_stage_reason_codes"
    lower = code.lower()
    if (
        "blocked" in lower
        or "not_cleared" in lower
        or "infeasible" in lower
        or "no_trade" in lower
        or "non_long" in lower
        or "missing" in lower
    ):
        return "blocking_reason_codes"
    if "emit.valid" in lower or ".feasible" in lower or "conviction" in lower:
        return "diagnostic_reason_codes"
    if "proxy" in lower or "partial" in lower or "not_proven" in lower:
        return "advisory_reason_codes"
    if "engine_internal" in lower:
        return "diagnostic_reason_codes"
    return "diagnostic_reason_codes"


def _reason_taxonomy(bucket_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    executed_inconsistencies: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    code_counts: Counter[str] = Counter()
    for row in bucket_rows:
        state = str(row.get("execution_state") or "").lower()
        reason_codes = _as_reason_tuple(row.get("reason_codes"))
        classes: dict[str, list[str]] = {
            "blocking_reason_codes": [],
            "diagnostic_reason_codes": [],
            "advisory_reason_codes": [],
            "historical_reason_codes": [],
            "previous_stage_reason_codes": [],
        }
        contradictory = []
        for code in reason_codes:
            code_counts[code] += 1
            cls = _classify_reason_code(code, execution_state=state)
            classes[cls].append(code)
            class_counts[cls] += 1
            if state == "executed" and code in CONTRADICTORY_EXECUTED_BLOCKERS:
                contradictory.append(code)
        status = "REASON_CODE_CLASSES_READY"
        if contradictory:
            status = "INCONSISTENT_EXECUTION_RECORD"
            executed_inconsistencies.append(
                {
                    "candidate_id": row.get("candidate_id"),
                    "capital_bucket": row.get("capital_bucket"),
                    "execution_state": state,
                    "contradictory_reason_codes": contradictory,
                    "artifact_path": row.get("_artifact_path", ""),
                }
            )
        rows.append(
            {
                "candidate_id": row.get("candidate_id"),
                "engine_id": row.get("engine_id"),
                "capital_bucket": row.get("capital_bucket"),
                "execution_state": state,
                **classes,
                "status": status,
            }
        )
    taxonomy_verdict = (
        "REASON_CODE_PATCH_REQUIRED"
        if executed_inconsistencies
        else "REASON_CODE_TAXONOMY_OK"
    )
    consistency_verdict = (
        "EXECUTED_RECORD_HAS_CONTRADICTORY_BLOCKERS"
        if executed_inconsistencies
        else "REASON_CODE_TAXONOMY_OK"
    )
    taxonomy = {
        "schema_version": "v53.reason_code_taxonomy_audit.v1",
        "generated_at": _now_iso(),
        "class_counts": dict(sorted(class_counts.items())),
        "top_reason_codes": dict(code_counts.most_common(25)),
        "row_count": len(rows),
        "verdict": taxonomy_verdict,
        "rows": rows,
    }
    consistency = {
        "schema_version": "v53.executed_reason_code_consistency_audit.v1",
        "generated_at": _now_iso(),
        "executed_record_count": sum(1 for row in bucket_rows if str(row.get("execution_state") or "").lower() == "executed"),
        "inconsistent_executed_record_count": len(executed_inconsistencies),
        "verdict": consistency_verdict,
        "rows": executed_inconsistencies,
    }
    invariant = {
        "schema_version": "v53.executed_record_invariant_report.v1",
        "generated_at": _now_iso(),
        "invariant": "executed records must not carry final contradictory blockers",
        "contradictory_blockers": sorted(CONTRADICTORY_EXECUTED_BLOCKERS),
        "violation_count": len(executed_inconsistencies),
        "status": "EXECUTED_RECORD_INVARIANT_VIOLATED" if executed_inconsistencies else "EXECUTED_RECORD_INVARIANT_OK",
        "rows": executed_inconsistencies,
    }
    return taxonomy, consistency, invariant


def _status_from_report(report: dict[str, Any], *, measured: str, proxy: str, missing: str) -> str:
    status = str(report.get("status") or "").upper()
    if not status:
        return "UNKNOWN"
    if "MEASURED" in status or "ESTIMATED_FROM_DEPTH20" in status:
        return measured
    if "PROXY" in status or "STALE" in status:
        return proxy
    if "MISSING" in status or "BLOCKED" in status or "NOT_PROVEN" in status:
        return missing
    return "UNKNOWN"


def _cost_component_row(row: dict[str, Any]) -> dict[str, Any]:
    parity = row.get("parity_payload") if isinstance(row.get("parity_payload"), dict) else {}
    measured_spread = parity.get("measured_spread_report") if isinstance(parity.get("measured_spread_report"), dict) else {}
    measured_slippage = parity.get("measured_slippage_report") if isinstance(parity.get("measured_slippage_report"), dict) else {}
    adverse = parity.get("adverse_selection_report") if isinstance(parity.get("adverse_selection_report"), dict) else {}
    fill = parity.get("fill_realism_report") if isinstance(parity.get("fill_realism_report"), dict) else {}
    book_status = str(row.get("book_depth_source_status") or parity.get("book_depth_source_status") or "")
    fill_status = str(row.get("fill_realism_status") or parity.get("fill_realism_status") or fill.get("status") or "")
    spread_status = _status_from_report(measured_spread, measured="MEASURED", proxy="PROXY", missing="MISSING")
    if spread_status == "UNKNOWN":
        spread_status = "MEASURED" if str(parity.get("spread_model_source") or "").startswith("CANONICAL") else "UNKNOWN"
    slippage_status = _status_from_report(measured_slippage, measured="MEASURED", proxy="PROXY", missing="MISSING")
    fee_status = "MEASURED" if "FEE_SOURCE" in str(row.get("fee_source_status") or "") and "MISSING" not in str(row.get("fee_source_status") or "") else "UNKNOWN"
    partial_fill_status = str(parity.get("partial_fill_status") or "")
    partial_fill_class = "MEASURED" if partial_fill_status in {"FULL_DEPTH_FILL", "PARTIAL_DEPTH_FILL"} else "UNKNOWN"
    adverse_status = _status_from_report(adverse, measured="MEASURED", proxy="PROXY", missing="MISSING")
    live_parity_status = (
        "PROVEN"
        if str(row.get("cost_parity_status") or "") in {"REPLAY_LIVE_COST_PARITY_PROVEN", "REPLAY_SHADOW_COST_PARITY_PROVEN"}
        else "BLOCKED"
        if "BLOCKED" in str(row.get("cost_parity_status") or "")
        else "MISSING"
    )
    components: list[str] = []
    if book_status != "BOOK_DEPTH20_AVAILABLE":
        components.append("B2_COST_BLOCKED_BY_DEPTH20_MISSING")
    if fill_status not in PROMOTION_READY_FILL_STATUSES:
        components.append("B2_COST_BLOCKED_BY_FILL_REALISM_MISSING")
    if spread_status == "PROXY":
        components.append("B2_COST_BLOCKED_BY_SPREAD_PROXY")
    if spread_status in {"MISSING", "UNKNOWN"}:
        components.append("B2_COST_BLOCKED_BY_SPREAD_PROXY")
    if slippage_status == "PROXY":
        components.append("B2_COST_BLOCKED_BY_SLIPPAGE_PROXY")
    if slippage_status in {"MISSING", "UNKNOWN"}:
        components.append("B2_COST_BLOCKED_BY_SLIPPAGE_PROXY")
    if fee_status in {"MISSING", "UNKNOWN"}:
        components.append("B2_COST_BLOCKED_BY_FEE_MISSING")
    if adverse_status != "MEASURED":
        components.append("B2_COST_BLOCKED_BY_ADVERSE_SELECTION_PROXY")
    if live_parity_status != "PROVEN":
        components.append("B2_COST_BLOCKED_BY_LIVE_PARITY_TELEMETRY")
    if components and spread_status == "MEASURED" and slippage_status == "MEASURED":
        components.append("B2_COST_MEASURED_BUT_NOT_PROMOTION_GRADE")
    if components:
        components.append("B2_COST_GOVERNANCE_BLOCKED_PARTIAL_MEASUREMENT")
    if not components:
        final = "FULLY_MEASURED"
    elif spread_status == "MEASURED" or slippage_status == "MEASURED" or fill_status in PROMOTION_READY_FILL_STATUSES:
        final = "PARTIAL_MEASURED"
    elif "PROXY" in " ".join(components):
        final = "PROXY"
    else:
        final = "MISSING"
    return {
        "candidate_id": row.get("candidate_id"),
        "engine_id": row.get("engine_id"),
        "capital_bucket": row.get("capital_bucket"),
        "execution_state": row.get("execution_state"),
        "book_depth20_status": book_status or "UNKNOWN",
        "fill_realism_status": fill_status or "UNKNOWN",
        "spread_status": spread_status,
        "slippage_status": slippage_status,
        "fee_status": fee_status,
        "partial_fill_status": partial_fill_class,
        "adverse_selection_status": adverse_status,
        "live_parity_status": live_parity_status,
        "cost_blocker_components": tuple(dict.fromkeys(components)),
        "final_cost_truth_status": final,
        "blocker_legitimate": bool(components),
        # Patch P0-SPLIT-1 (2026-05-27) — accept the renamed split variants
        # alongside the legacy name so this audit recognizes the blocker
        # presence regardless of which run produced the bucket.
        "parent_blocker_present": bool(
            B2_COST_MEASUREMENT_BLOCKED_SPLIT_VARIANTS.intersection(
                _as_reason_tuple(row.get("reason_codes"))
            )
        ),
    }


def _cost_component_audit(bucket_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_cost_component_row(row) for row in bucket_rows]
    component_counts: Counter[str] = Counter()
    truth_counts: Counter[str] = Counter()
    for row in rows:
        truth_counts[str(row["final_cost_truth_status"])] += 1
        for code in row["cost_blocker_components"]:
            component_counts[str(code)] += 1
    return {
        "schema_version": "v53.b2_cost_blocker_component_audit.v1",
        "generated_at": _now_iso(),
        "row_count": len(rows),
        "component_counts": dict(component_counts.most_common()),
        "final_cost_truth_status_counts": dict(sorted(truth_counts.items())),
        "verdict": "B2_COST_BLOCKER_COMPONENTS_ADDED",
        "rows": rows,
    }


def _engine_native_runner_invocation_audit(bucket_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Patch P0-RENAME-1 (2026-05-27) — bucket records produced after the
    # runner-not-invoked rename land with `B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1`
    # instead of the legacy `ENGINE_NATIVE_RUNNER_NOT_INVOKED`. Both codes
    # are accepted here so this audit keeps producing meaningful output on
    # historical runs while also flagging that the rename has been applied
    # to the current pipeline (verdict `_RECLASSIFIED_DONE`).
    candidate_index = {str(row.get("candidate_id") or ""): row for row in candidate_rows if row.get("candidate_id")}
    rows: list[dict[str, Any]] = []
    verdict = "ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED_DIAGNOSTIC"
    legacy_match_count = 0
    renamed_match_count = 0
    for row in bucket_rows:
        codes = _as_reason_tuple(row.get("reason_codes"))
        matched_code = ""
        if "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1" in codes:
            matched_code = "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1"
            renamed_match_count += 1
        elif "ENGINE_NATIVE_RUNNER_NOT_INVOKED" in codes:
            matched_code = "ENGINE_NATIVE_RUNNER_NOT_INVOKED"
            legacy_match_count += 1
        else:
            continue
        candidate_id = str(row.get("candidate_id") or "")
        candidate = candidate_index.get(candidate_id, {})
        compat = candidate.get("compatibility_payload") if isinstance(candidate.get("compatibility_payload"), dict) else {}
        engine_native_status = str(compat.get("engine_native_status") or "")
        state = str(row.get("execution_state") or "").lower()
        replacement = (
            "B2_ENGINE_NATIVE_REEVALUATION_NOT_REQUESTED"
            if state in SELECTED_STATES
            else "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1"
        )
        if matched_code == "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1":
            row_verdict = "ENGINE_NATIVE_RUNNER_NOT_INVOKED_RECLASSIFIED_DONE"
        elif state in SELECTED_STATES or engine_native_status == "ENGINE_NATIVE_RUNNER_INVOKED":
            row_verdict = "ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED_DIAGNOSTIC"
        else:
            row_verdict = "ENGINE_NATIVE_RUNNER_REASON_CODE_TOO_COARSE"
        if row_verdict == "ENGINE_NATIVE_RUNNER_REASON_CODE_TOO_COARSE":
            verdict = row_verdict
        rows.append(
            {
                "candidate_id": candidate_id,
                "engine_id": row.get("engine_id"),
                "capital_bucket": row.get("capital_bucket"),
                "execution_state": row.get("execution_state"),
                "candidate_engine_native_status": engine_native_status or "MISSING_IN_ARTIFACT",
                "candidate_engine_native_decision": str(compat.get("engine_native_decision") or "MISSING_IN_ARTIFACT"),
                "current_code": matched_code,
                "recommended_reclassification": replacement,
                "reason_code_class": "previous_stage_reason_codes",
                "verdict": row_verdict,
            }
        )
    if rows and legacy_match_count == 0 and renamed_match_count > 0:
        verdict = "ENGINE_NATIVE_RUNNER_NOT_INVOKED_RECLASSIFIED_DONE"
    return {
        "schema_version": "v53.engine_native_runner_invocation_audit.v1",
        "generated_at": _now_iso(),
        "row_count": len(rows),
        "legacy_match_count": legacy_match_count,
        "renamed_match_count": renamed_match_count,
        "verdict": verdict if rows else "ENGINE_NATIVE_RUNNER_NOT_INVOKED_NOT_PRESENT",
        "rows": rows,
    }


def _engine_a_autopsy(bucket_rows: list[dict[str, Any]]) -> dict[str, Any]:
    target_id = "ae5c57f5197f33fcab27b346"
    rows = [row for row in bucket_rows if str(row.get("candidate_id") or "") == target_id]
    executed = [row for row in rows if str(row.get("execution_state") or "").lower() == "executed"]
    buckets = sorted({_as_int(row.get("capital_bucket")) for row in executed})
    sample = executed[0] if executed else (rows[0] if rows else {})
    codes = _as_reason_tuple(sample.get("reason_codes"))
    contradictory = [code for code in codes if code in CONTRADICTORY_EXECUTED_BLOCKERS]
    fwd_h1 = _as_float(sample.get("forward_return_h1"))
    mfe = _as_float(sample.get("mfe_bps"))
    mae = _as_float(sample.get("mae_bps"))
    loss_cause = "UNKNOWN"
    if fwd_h1 is not None and fwd_h1 < 0 and (mfe is None or mfe <= 0):
        loss_cause = "PRICE_ADVERSE_MOVE"
    elif _as_float(sample.get("executed_only_net_return")) is not None and _as_float(sample.get("executed_only_net_return")) < 0:
        loss_cause = "COST_OR_PRICE_ADVERSE_MOVE"
    verdict_parts = ["BUCKET_EXPANDED_SINGLE_SIGNAL"] if len(executed) > 1 else []
    if contradictory:
        verdict_parts.append("INCONSISTENT_RECORD")
    elif executed:
        verdict_parts.append("VALID_BUT_LOSSMAKING")
    return {
        "schema_version": "v53.engine_a_executed_candidate_autopsy.v1",
        "generated_at": _now_iso(),
        "candidate_id": target_id,
        "engine_id": "engine_a",
        "distinct_signal_count": 1 if executed else 0,
        "bucket_execution_count": len(executed),
        "capital_buckets": buckets,
        "engine_emit_status": "engine_a.emit.valid" if "engine_a.emit.valid" in codes else "NOT_FOUND",
        "why_emit_valid": [code for code in codes if code.startswith("engine_a.") or code.startswith("engine_internal.engine_a")],
        "why_selected": [code for code in codes if "feasible" in code or "conviction" in code or "emit.valid" in code],
        "why_executed": [str(sample.get("dtr_record", {}).get("primary_reason") if isinstance(sample.get("dtr_record"), dict) else "")],
        "fwd_h1_bps": fwd_h1,
        "mfe_bps": mfe,
        "mae_bps": mae,
        "loss_cause": loss_cause,
        "contradictory_reason_codes": contradictory,
        "verdict": "|".join(verdict_parts) if verdict_parts else "TARGET_CANDIDATE_NOT_FOUND",
        "rows": [
            {
                "capital_bucket": row.get("capital_bucket"),
                "execution_state": row.get("execution_state"),
                "executed_only_net_return": row.get("executed_only_net_return"),
                "artifact_path": row.get("_artifact_path", ""),
            }
            for row in rows
        ],
    }


def _parallel_logic_audit() -> dict[str, Any]:
    rows = [
        {
            "surface": "cost_feasibility",
            "parallel_paths": ["engine cost feasibility", "B2 replay cost governance"],
            "risk": "cost feasible can coexist with B2 partial measurement blocker",
            "verdict": "PARALLEL_LOGIC_PATCH_REQUIRED",
        },
        {
            "surface": "break_even",
            "parallel_paths": ["engine economics", "expected-edge proxy gate", "scoring_backbone target"],
            "risk": "break-even reason codes may be proxy-governed in ML_OFF",
            "verdict": "PARALLEL_LOGIC_PATCH_REQUIRED",
        },
        {
            "surface": "spread_slippage",
            "parallel_paths": ["A2 research features", "B2 measured replay evidence"],
            "risk": "research features must not be promoted as replay truth",
            "verdict": "PARALLEL_LOGIC_REPORTING_ONLY",
        },
        {
            "surface": "count_semantics",
            "parallel_paths": ["candidate counts", "bucket record counts"],
            "risk": "1 signal x 4 buckets displayed as 4 trades",
            "verdict": "PARALLEL_LOGIC_PATCH_REQUIRED",
        },
        {
            "surface": "execution_truth",
            "parallel_paths": ["local_replay_runtime", "shadow_execution_simulator", "execution_backbone pieces"],
            "risk": "B2 tests a partial adapter rail, not full future shadow/live parity",
            "verdict": "PARALLEL_LOGIC_PATCH_REQUIRED",
        },
    ]
    return {
        "schema_version": "v53.parallel_logic_and_proxy_surface_audit.v1",
        "generated_at": _now_iso(),
        "verdict": "PARALLEL_LOGIC_PATCH_REQUIRED",
        "rows": rows,
    }


def _local_replay_dependency_audit(module_matrix: dict[str, Any]) -> dict[str, Any]:
    local_row = next((row for row in module_matrix["rows"] if row["module"] == "src/local_replay_runtime"), {})
    return {
        "schema_version": "v53.backtest_local_replay_dependency_audit.v1",
        "generated_at": _now_iso(),
        "local_replay_entrypoint_count": local_row.get("entrypoint_count", 0),
        "dominant_runtime": True,
        "shadow_execution_simulator_truth_adapter": True,
        "verdict": "BACKTEST_LOCAL_REPLAY_DOMINANT",
        "risk": "B2 remains a local replay dominant rail with partial canonical backbone adapters.",
    }


def _final_report(
    *,
    run_id: str,
    module_matrix: dict[str, Any],
    decision_matrix: dict[str, Any],
    count_report: dict[str, Any],
    taxonomy: dict[str, Any],
    invocation: dict[str, Any],
    cost: dict[str, Any],
    autopsy: dict[str, Any],
) -> dict[str, Any]:
    parity_statuses = [str(row.get("parity_status") or "") for row in decision_matrix["rows"]]
    overall = "PARITY_PARTIAL"
    if any(status == "PARITY_CONFLICT" for status in parity_statuses):
        overall = "PARITY_CONFLICT"
    elif any(status == "PARITY_MISSING" for status in parity_statuses):
        overall = "PARITY_MISSING"
    return {
        "schema_version": "v53.backtest_backbone_parity.v1",
        "run_id": run_id,
        "audit_mode": "READ_ONLY_THEN_PATCH",
        "trading_logic_modified": False,
        "thresholds_modified": False,
        "modules": {row["module"]: row for row in module_matrix["rows"]},
        "decision_source_matrix": decision_matrix["rows"],
        "count_semantics_verdict": count_report["verdict"],
        "reason_code_taxonomy_verdict": taxonomy["verdict"],
        "engine_native_runner_invocation_verdict": invocation["verdict"],
        "b2_cost_blocker_component_verdict": cost["verdict"],
        "engine_a_autopsy_verdict": autopsy["verdict"],
        "backbone_parity_overall": overall,
        "surfaces_still_local_or_proxy": [
            row["surface"]
            for row in decision_matrix["rows"]
            if row["actual_status"] in {"proxy", "missing", "adapter"}
            or row["parity_status"] in {"PARITY_CONFLICT", "PARITY_MISSING"}
        ],
        "shadow_live_logical_parity_verdict": "B2_PARTIAL_BACKBONE_ADAPTER_NOT_FULL_SHADOW_LIVE_PARITY",
        "root_causes_ranked": [
            "BACKTEST_LOCAL_REPLAY_DOMINANT",
            "EXECUTION_BACKBONE_PARTIAL_ADAPTER",
            "COUNT_SEMANTICS_BUCKET_EXPANSION_CONFUSING",
            "REASON_CODE_TAXONOMY_PATCH_REQUIRED",
            "B2_COST_MEASUREMENT_BLOCKED_TOO_COARSE",
            "EXPECTED_EDGE_ML_ARTIFACT_REQUIRED",
            "RISK_SCORING_REGIME_PROTOCOLS_BUILD14_PARTIAL_SURFACES",
        ],
        "patch_plan": [
            "PATCH_COUNT_SEMANTICS_REPORTING",
            "PATCH_REASON_CODE_TAXONOMY_REPORTING",
            "PATCH_ENGINE_NATIVE_RUNNER_NOT_INVOKED_RECLASSIFICATION",
            "PATCH_B2_COST_BLOCKER_COMPONENTS",
            "PATCH_SINGLE_SCOPE_RANKING_WORDING",
            "ADD_EXECUTED_RECORD_INVARIANT_REPORT",
            "SURFACE_META_LEARNING_EXPECTED_EDGE_ARTIFACT_STATE",
            "SURFACE_PROTOCOL_CONTRACTS_WITHOUT_LIVE_TRANSPORT",
            "SURFACE_COMPLETE_ENABLERS_BUILD14_CONTEXT_AND_UPSTREAM_FILTERING",
        ],
    }


def _write_docs(
    *,
    docs_dir: Path,
    final_report: dict[str, Any],
    autopsy: dict[str, Any],
) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Backtest Backbone Parity Audit",
        "",
        f"Run: `{final_report['run_id']}`",
        f"Generated at: `{_now_iso()}`",
        "",
        "## Verdict",
        "",
        f"- Overall parity: `{final_report['backbone_parity_overall']}`",
        f"- Count semantics: `{final_report['count_semantics_verdict']}`",
        f"- Reason taxonomy: `{final_report['reason_code_taxonomy_verdict']}`",
        f"- Engine native invocation: `{final_report['engine_native_runner_invocation_verdict']}`",
        f"- Cost blocker components: `{final_report['b2_cost_blocker_component_verdict']}`",
        "",
        "No trading logic, threshold, engine output, or replay record is modified by this audit.",
        "",
        "## Root Causes",
        "",
        *[f"- `{item}`" for item in final_report["root_causes_ranked"]],
        "",
        "## Patch Plan",
        "",
        *[f"- `{item}`" for item in final_report["patch_plan"]],
        "",
    ]
    atomic_write_text(docs_dir / "BACKTEST_BACKBONE_PARITY_AUDIT.md", "\n".join(lines), encoding="utf-8")
    atomic_write_text(docs_dir / "BACKTEST_BACKBONE_PARITY_FINAL_REPORT.md", "\n".join(lines), encoding="utf-8")
    autopsy_lines = [
        "# Engine A Executed Candidate Autopsy",
        "",
        f"Candidate: `{autopsy['candidate_id']}`",
        f"Verdict: `{autopsy['verdict']}`",
        "",
        f"Distinct signals: `{autopsy['distinct_signal_count']}`",
        f"Bucket executions: `{autopsy['bucket_execution_count']}`",
        f"Capital buckets: `{autopsy['capital_buckets']}`",
        f"Forward H1 bps: `{autopsy['fwd_h1_bps']}`",
        f"MFE bps: `{autopsy['mfe_bps']}`",
        f"MAE bps: `{autopsy['mae_bps']}`",
        f"Loss cause: `{autopsy['loss_cause']}`",
        "",
        "The four executions are bucket-expanded records for one signal, not four independent trading signals.",
    ]
    atomic_write_text(
        docs_dir / "ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY.md",
        "\n".join(autopsy_lines),
        encoding="utf-8",
    )


def write_backtest_backbone_parity_audit_reports(
    run_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
    docs_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write read-only Backbone parity audit reports for an existing B2 run."""

    resolved_run_dir = Path(run_dir).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    resolved_reports = _reports_dir(resolved_run_dir)
    resolved_reports.mkdir(parents=True, exist_ok=True)
    resolved_docs = (
        Path(docs_dir).resolve()
        if docs_dir is not None
        else resolved_repo_root / "docs" / "audit"
    )

    summary = _read_json(resolved_reports / "strategy_ladder_summary.json", {})
    if not isinstance(summary, dict):
        summary = {}
    run_manifest = _read_json(resolved_run_dir / "run_manifest.json", {})
    if not isinstance(run_manifest, dict):
        run_manifest = {}
    run_id = str(summary.get("run_id") or run_manifest.get("run_id") or resolved_run_dir.name)
    candidate_rows = _load_candidate_rows(resolved_run_dir)
    bucket_rows = _load_bucket_rows(resolved_run_dir)

    module_matrix = _build_module_usage_matrix(resolved_repo_root)
    decision_matrix = _decision_source_matrix()
    local_replay_audit = _local_replay_dependency_audit(module_matrix)
    parallel_audit = _parallel_logic_audit()
    count_report = _count_semantics(
        summary=summary,
        candidate_rows=candidate_rows,
        bucket_rows=bucket_rows,
    )
    taxonomy, consistency, invariant = _reason_taxonomy(bucket_rows)
    invocation = _engine_native_runner_invocation_audit(bucket_rows, candidate_rows)
    cost = _cost_component_audit(bucket_rows)
    autopsy = _engine_a_autopsy(bucket_rows)
    final_report = _final_report(
        run_id=run_id,
        module_matrix=module_matrix,
        decision_matrix=decision_matrix,
        count_report=count_report,
        taxonomy=taxonomy,
        invocation=invocation,
        cost=cost,
        autopsy=autopsy,
    )
    main_audit = {
        "schema_version": "v53.backtest_backbone_parity_audit.v1",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "audit_mode": "READ_ONLY",
        "trading_logic_modified": False,
        "thresholds_modified": False,
        "module_usage_matrix_ref": str((resolved_reports / BACKBONE_MODULE_USAGE_MATRIX_FILENAME).resolve()),
        "decision_source_matrix_ref": str((resolved_reports / BACKTEST_DECISION_SOURCE_MATRIX_FILENAME).resolve()),
        "count_semantics_ref": str((resolved_reports / COUNT_SEMANTICS_DEEP_AUDIT_FILENAME).resolve()),
        "reason_code_taxonomy_ref": str((resolved_reports / REASON_CODE_TAXONOMY_AUDIT_FILENAME).resolve()),
        "final_report_ref": str((resolved_reports / BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME).resolve()),
        "overall": final_report["backbone_parity_overall"],
    }
    patch_verdict = {
        "schema_version": "v53.backtest_backbone_parity_patch_final_verdict.v1",
        "generated_at": _now_iso(),
        "run_id": run_id,
        "verdicts": [
            "BACKTEST_BACKBONE_PARITY_DIAGNOSED",
            "BACKTEST_BACKBONE_PARITY_PARTIAL",
            "BACKTEST_LOCAL_REPLAY_DOMINANT",
            "NO_TRADING_LOGIC_CHANGED",
        ],
        "trading_logic_modified": False,
        "thresholds_modified": False,
        "next_patch_plan": final_report["patch_plan"],
    }
    payloads = {
        BACKTEST_BACKBONE_PARITY_AUDIT_FILENAME: main_audit,
        BACKTEST_DECISION_SOURCE_MATRIX_FILENAME: decision_matrix,
        BACKBONE_MODULE_USAGE_MATRIX_FILENAME: module_matrix,
        BACKTEST_LOCAL_REPLAY_DEPENDENCY_AUDIT_FILENAME: local_replay_audit,
        PARALLEL_LOGIC_AND_PROXY_SURFACE_AUDIT_FILENAME: parallel_audit,
        COUNT_SEMANTICS_DEEP_AUDIT_FILENAME: count_report,
        REASON_CODE_TAXONOMY_AUDIT_FILENAME: taxonomy,
        EXECUTED_REASON_CODE_CONSISTENCY_AUDIT_FILENAME: consistency,
        ENGINE_NATIVE_RUNNER_INVOCATION_AUDIT_FILENAME: invocation,
        B2_COST_BLOCKER_COMPONENT_AUDIT_FILENAME: cost,
        ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY_FILENAME: autopsy,
        EXECUTED_RECORD_INVARIANT_REPORT_FILENAME: invariant,
        BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME: final_report,
        BACKTEST_BACKBONE_PARITY_PATCH_FINAL_VERDICT_FILENAME: patch_verdict,
    }
    written: dict[str, str] = {}
    for filename, payload in payloads.items():
        path = resolved_reports / filename
        atomic_write_json(path, payload, indent=2)
        written[filename] = str(path.resolve())
    _write_docs(docs_dir=resolved_docs, final_report=final_report, autopsy=autopsy)
    written["BACKTEST_BACKBONE_PARITY_AUDIT.md"] = str(
        (resolved_docs / "BACKTEST_BACKBONE_PARITY_AUDIT.md").resolve()
    )
    written["BACKTEST_BACKBONE_PARITY_FINAL_REPORT.md"] = str(
        (resolved_docs / "BACKTEST_BACKBONE_PARITY_FINAL_REPORT.md").resolve()
    )
    written["ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY.md"] = str(
        (resolved_docs / "ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY.md").resolve()
    )
    return written


__all__ = [
    "B2_COST_BLOCKER_COMPONENT_AUDIT_FILENAME",
    "BACKBONE_MODULE_USAGE_MATRIX_FILENAME",
    "BACKTEST_BACKBONE_PARITY_AUDIT_FILENAME",
    "BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME",
    "BACKTEST_DECISION_SOURCE_MATRIX_FILENAME",
    "COUNT_SEMANTICS_DEEP_AUDIT_FILENAME",
    "ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY_FILENAME",
    "ENGINE_NATIVE_RUNNER_INVOCATION_AUDIT_FILENAME",
    "EXECUTED_REASON_CODE_CONSISTENCY_AUDIT_FILENAME",
    "EXECUTED_RECORD_INVARIANT_REPORT_FILENAME",
    "PARALLEL_LOGIC_AND_PROXY_SURFACE_AUDIT_FILENAME",
    "REASON_CODE_TAXONOMY_AUDIT_FILENAME",
    "write_backtest_backbone_parity_audit_reports",
]
