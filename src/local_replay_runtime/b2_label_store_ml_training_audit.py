"""Audit B2 label-store eligibility for governed expected-edge ML training.

This module is reporting-only. It reads existing A2/B1/B2/label-store artifacts
and classifies whether rows are usable as scientific X/y training samples.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.feature_grounding_registry import (
    LABEL_OR_OUTCOME_FEATURE_NAMES,
    feature_grounding_entry,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
)
from local_replay_runtime.training_source_contract import (
    ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED,
    build_training_source_contract_report,
)


B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME = "b2_label_store_ml_training_audit.json"
A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME = (
    "a2_b2_feature_label_alignment_report.json"
)
ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME = "ml_training_label_fidelity_report.json"
ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME = (
    "ml_target_policy_consistency_report.json"
)
ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME = (
    "ml_training_row_eligibility_report.json"
)
ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME = "ml_feature_label_leakage_report.json"
ML_TRAIN_EVAL_WINDOW_OVERLAP_REPORT_FILENAME = "ml_train_eval_window_overlap_report.json"

LABEL_STORE_DATASET_FILENAME = "strategy_ladder_replay_label_store.jsonl"
LEGACY_LABEL_STORE_DATASET_FILENAMES = ("strategy_ladder_b2_label_store.jsonl",)

FEATURE_VALUE_OK = "FEATURE_VALUE_OK"
FEATURE_MISSING = "FEATURE_MISSING"
FEATURE_POST_DECISION_LEAKAGE_BLOCKED = "FEATURE_POST_DECISION_LEAKAGE_BLOCKED"
FEATURE_GROUNDING_UNKNOWN_BLOCKED = "FEATURE_GROUNDING_UNKNOWN_BLOCKED"
FEATURE_PROXY_ALLOWED_FOR_RESEARCH_ONLY = "FEATURE_PROXY_ALLOWED_FOR_RESEARCH_ONLY"
FEATURE_PROXY_BLOCKED_FOR_TRAINING = "FEATURE_PROXY_BLOCKED_FOR_TRAINING"

LABEL_REPLAY_GROUNDED = "LABEL_REPLAY_GROUNDED"
LABEL_PROXY_DISCOVERY_ONLY = "LABEL_PROXY_DISCOVERY_ONLY"
LABEL_BLOCKED_BY_MISSING_POST_WINDOW = "LABEL_BLOCKED_BY_MISSING_POST_WINDOW"
LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN = (
    "LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN"
)
LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY = "LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY"
LABEL_NOT_AVAILABLE = "LABEL_NOT_AVAILABLE"

TRAINING_ROW_ELIGIBLE = "TRAINING_ROW_ELIGIBLE"
TRAINING_ROW_RESEARCH_ONLY = "TRAINING_ROW_RESEARCH_ONLY"
TRAINING_ROW_BLOCKED = "TRAINING_ROW_BLOCKED"

TARGET_POLICY_MISMATCH_BLOCKED = "TARGET_POLICY_MISMATCH_BLOCKED"
TARGET_POLICY_MATCH = "TARGET_POLICY_MATCH"
TARGET_POLICY_NOT_PROVEN = "TARGET_POLICY_NOT_PROVEN"
TARGET_POLICY_UNSATISFIED_FOR_TRAINING = "TARGET_POLICY_UNSATISFIED_FOR_TRAINING"

B2_LABEL_STORE_TRAINING_READY = "B2_LABEL_STORE_TRAINING_READY"
B2_LABEL_STORE_RESEARCH_ONLY = "B2_LABEL_STORE_RESEARCH_ONLY"
B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS = "B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS"
B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW = (
    "B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW"
)
B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH = (
    "B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH"
)
B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP = (
    "B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP"
)
B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE = "B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE"
B2_LABEL_STORE_BLOCKED_BY_COST_FILL_NOT_READY = (
    "B2_LABEL_STORE_BLOCKED_BY_COST_FILL_NOT_READY"
)
B2_LABEL_STORE_INSUFFICIENT_ROWS = "B2_LABEL_STORE_INSUFFICIENT_ROWS"

_LABEL_FIELDS = (
    "executed_only_net_return",
    "expected_ce_net",
    "label_net_positive",
    "label_break_even_cleared",
    "label_survived_mae",
    "label_forward_return_h1",
    "label_forward_return_h5",
    "label_forward_return_h10",
    "mfe_bps",
    "mae_bps",
)


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_dicts(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        return ()
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return ()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return tuple(rows)


def _first_existing(paths: tuple[Path, ...]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def _resolve_label_store_path(run_dir: Path, label_store_path: Path | None = None) -> Path | None:
    if label_store_path is not None:
        return label_store_path if label_store_path.is_file() else None
    candidates = (
        run_dir / "ml_label_store" / LABEL_STORE_DATASET_FILENAME,
        run_dir / LABEL_STORE_DATASET_FILENAME,
        *((run_dir / "ml_label_store" / name) for name in LEGACY_LABEL_STORE_DATASET_FILENAMES),
        *(run_dir / name for name in LEGACY_LABEL_STORE_DATASET_FILENAMES),
    )
    direct = _first_existing(candidates)
    if direct is not None:
        return direct
    try:
        for name in (LABEL_STORE_DATASET_FILENAME, *LEGACY_LABEL_STORE_DATASET_FILENAMES):
            matches = sorted(run_dir.rglob(name))
            if matches:
                return matches[0]
    except OSError:
        return None
    return None


def _candidate_paths(run_dir: Path) -> tuple[Path, ...]:
    paths: list[Path] = [
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        run_dir / "candidate_events.jsonl",
        run_dir / "preselection_candidates.jsonl",
    ]
    try:
        paths.extend(sorted(run_dir.rglob("candidate_events.jsonl")))
        paths.extend(sorted(run_dir.rglob("preselection_candidates.jsonl")))
    except OSError:
        pass
    return tuple(dict.fromkeys(paths))


def _load_candidate_index(run_dir: Path) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for path in _candidate_paths(run_dir):
        for row in _read_jsonl_dicts(path):
            candidate_id = str(row.get("candidate_id") or "").strip()
            if candidate_id and candidate_id not in candidates:
                candidates[candidate_id] = {**row, "_source_ref": str(path.resolve())}
    return candidates


def _as_int(raw_value: Any) -> int | None:
    if isinstance(raw_value, bool):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _has_value(raw_value: Any) -> bool:
    return raw_value is not None and raw_value != ""


def _non_null_labels(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(name for name in _LABEL_FIELDS if _has_value(row.get(name)))


def _row_actual_target_policy(row: dict[str, Any]) -> str:
    if _has_value(row.get("executed_only_net_return")):
        if str(row.get("execution_fidelity_status") or "") == "EXECUTION_FIDELITY_READY":
            return STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY
        return "B2_REPLAY_EXECUTION_AWARE_NET_EDGE_PARTIAL.v1"
    if _has_value(row.get("expected_ce_net")):
        return "B2_REPLAY_EXPECTED_CE_NET_PROXY"
    if any(_has_value(row.get(name)) for name in ("label_forward_return_h1", "label_forward_return_h5", "label_forward_return_h10")):
        return "ABS_FORWARD_CLOSE_RETURN"
    return TARGET_POLICY_NOT_PROVEN


def _aggregate_actual_target_policy(row_policies: tuple[str, ...]) -> str:
    non_empty = tuple(policy for policy in row_policies if policy)
    if not non_empty:
        return TARGET_POLICY_NOT_PROVEN
    unique = tuple(dict.fromkeys(non_empty))
    return unique[0] if len(unique) == 1 else "MIXED_TARGET_POLICY"


def _target_policy_status(*, declared_policy: str, actual_policy: str) -> str:
    if not declared_policy or actual_policy == TARGET_POLICY_NOT_PROVEN:
        return TARGET_POLICY_NOT_PROVEN
    if declared_policy == actual_policy:
        return TARGET_POLICY_MATCH
    if declared_policy == STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY and actual_policy in {
        "B2_REPLAY_EXECUTION_AWARE_NET_EDGE_PARTIAL.v1",
        "B2_REPLAY_EXPECTED_CE_NET_PROXY",
    }:
        return TARGET_POLICY_UNSATISFIED_FOR_TRAINING
    return TARGET_POLICY_MISMATCH_BLOCKED


def _feature_audit_rows(row: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    decision_ts = _as_int(row.get("decision_timestamp_ms")) or 0
    feature_ts = _as_int(row.get("feature_timestamp_ms"))
    feature_values = row.get("feature_values")
    if not isinstance(feature_values, dict):
        feature_values = {}
    out: list[dict[str, Any]] = []
    for feature_name, value in sorted(feature_values.items()):
        entry = feature_grounding_entry(str(feature_name))
        status = FEATURE_VALUE_OK
        blocker = ""
        if feature_name in LABEL_OR_OUTCOME_FEATURE_NAMES or (
            entry is not None and entry.is_label_or_outcome
        ):
            status = FEATURE_POST_DECISION_LEAKAGE_BLOCKED
            blocker = "ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED"
        elif entry is None:
            status = FEATURE_GROUNDING_UNKNOWN_BLOCKED
            blocker = FEATURE_GROUNDING_UNKNOWN_BLOCKED
        elif feature_ts is not None and feature_ts > decision_ts:
            status = FEATURE_POST_DECISION_LEAKAGE_BLOCKED
            blocker = "FEATURE_TIMESTAMP_AFTER_DECISION"
        out.append(
            {
                "candidate_id": str(row.get("candidate_id") or ""),
                "feature_name": str(feature_name),
                "value": value,
                "unit": "MISSING_IN_ARTIFACT",
                "grounding": "MISSING_IN_ARTIFACT" if entry is None else entry.grounding.value,
                "source_status": "MISSING_IN_ARTIFACT",
                "timestamp_ms": feature_ts if feature_ts is not None else "MISSING_IN_ARTIFACT",
                "available_at_decision_time": False if entry is None else entry.available_at_decision_time,
                "proxy_or_measured": "MISSING_IN_ARTIFACT",
                "used_for_training": status == FEATURE_VALUE_OK,
                "status": status,
                "blocker": blocker,
            }
        )
    if not out:
        out.append(
            {
                "candidate_id": str(row.get("candidate_id") or ""),
                "feature_name": "MISSING_IN_ARTIFACT",
                "status": FEATURE_MISSING,
                "blocker": "FEATURE_VALUES_MISSING",
            }
        )
    return tuple(out)


def _label_audit_row(row: dict[str, Any]) -> dict[str, Any]:
    label_names = _non_null_labels(row)
    replay_grounded = bool(row.get("replay_grounded_label_flag"))
    proxy_label = bool(row.get("proxy_execution_label_flag"))
    execution_fidelity_status = str(row.get("execution_fidelity_status") or "")
    label_quality_status = str(row.get("label_quality_status") or "")
    replay_quality_status = str(row.get("replay_quality_status") or "")
    if not label_names:
        status = LABEL_BLOCKED_BY_MISSING_POST_WINDOW
    elif proxy_label:
        status = LABEL_PROXY_DISCOVERY_ONLY
    elif replay_grounded and execution_fidelity_status == "EXECUTION_FIDELITY_READY":
        status = LABEL_REPLAY_GROUNDED
    elif replay_grounded:
        status = LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN
    else:
        status = LABEL_NOT_AVAILABLE
    if _has_value(row.get("expected_ce_net")) and not _has_value(row.get("executed_only_net_return")):
        status = LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY
    return {
        "candidate_id": str(row.get("candidate_id") or ""),
        "capital_bucket": row.get("capital_bucket"),
        "labels_present": label_names,
        "label_truth_status": status,
        "label_fidelity": label_quality_status or "MISSING_IN_ARTIFACT",
        "post_window_available": (
            "POST_WINDOW_READY"
            if label_names
            else LABEL_BLOCKED_BY_MISSING_POST_WINDOW
        ),
        "execution_replay_available": replay_quality_status or "MISSING_IN_ARTIFACT",
        "cost_source_used": execution_fidelity_status or "MISSING_IN_ARTIFACT",
        "fill_realism_status": execution_fidelity_status or "MISSING_IN_ARTIFACT",
        "adverse_selection_status": (
            "ADVERSE_SELECTION_PRESENT"
            if _has_value(row.get("adverse_selection_bps"))
            else "ADVERSE_SELECTION_MISSING_IN_ARTIFACT"
        ),
    }


def _alignment_row(
    row: dict[str, Any],
    *,
    candidate_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate_id = str(row.get("candidate_id") or "").strip()
    candidate = candidate_index.get(candidate_id)
    blockers: list[str] = []
    if candidate is None:
        blockers.append("B1_CANDIDATE_REF_NOT_FOUND")
    for field_name in ("pair", "timeframe", "engine_id"):
        row_value = str(row.get(field_name) or "").strip()
        candidate_value = str((candidate or {}).get(field_name) or "").strip()
        if candidate is not None and candidate_value and row_value and candidate_value != row_value:
            blockers.append(f"{field_name.upper()}_MISMATCH")
    if not str(row.get("feature_vector_ref") or "").strip():
        blockers.append("A2_FEATURE_REF_MISSING")
    if not str(row.get("replay_ref") or "").strip():
        blockers.append("B2_REPLAY_RECORD_REF_MISSING")
    if not str(row.get("raw_window_ref") or "").strip():
        blockers.append("POST_OR_RAW_WINDOW_REF_MISSING")
    return {
        "candidate_id": candidate_id,
        "pair": row.get("pair", "MISSING_IN_ARTIFACT"),
        "timeframe": row.get("timeframe", "MISSING_IN_ARTIFACT"),
        "engine_id": row.get("engine_id", "MISSING_IN_ARTIFACT"),
        "decision_timestamp_ms": row.get("decision_timestamp_ms", "MISSING_IN_ARTIFACT"),
        "a2_feature_ref": row.get("feature_vector_ref") or "MISSING_IN_ARTIFACT",
        "b1_candidate_ref": (
            str(candidate.get("_source_ref"))
            if candidate is not None and candidate.get("_source_ref")
            else "NOT_FOUND"
        ),
        "b2_replay_record_ref": row.get("replay_ref") or "MISSING_IN_ARTIFACT",
        "raw_trade_window_ref": row.get("raw_window_ref") or "MISSING_IN_ARTIFACT",
        "raw_orderbook_window_ref": row.get("raw_window_ref") or "MISSING_IN_ARTIFACT",
        "raw_ohlcv_window_ref": row.get("raw_window_ref") or "MISSING_IN_ARTIFACT",
        "post_window_ref": row.get("raw_window_ref") or "MISSING_IN_ARTIFACT",
        "alignment_status": "A2_B1_B2_ALIGNMENT_OK" if not blockers else "A2_B1_B2_ALIGNMENT_BLOCKED",
        "blocker_codes": tuple(dict.fromkeys(blockers)),
    }


def _eligibility_status(
    row: dict[str, Any],
    *,
    feature_rows: tuple[dict[str, Any], ...],
    label_row: dict[str, Any],
    alignment_row: dict[str, Any],
    declared_target_policy: str,
    actual_target_policy: str,
    target_policy_status: str,
    train_eval_overlap_blocked: bool,
    train_eval_split_not_proven: bool,
) -> tuple[str, tuple[str, ...]]:
    blockers: list[str] = []
    if any(item.get("status") == FEATURE_POST_DECISION_LEAKAGE_BLOCKED for item in feature_rows):
        blockers.append("FEATURE_OR_LABEL_LEAKAGE_BLOCKED")
    if any(item.get("status") == FEATURE_GROUNDING_UNKNOWN_BLOCKED for item in feature_rows):
        blockers.append(FEATURE_GROUNDING_UNKNOWN_BLOCKED)
    if alignment_row.get("alignment_status") != "A2_B1_B2_ALIGNMENT_OK":
        blockers.extend(str(item) for item in alignment_row.get("blocker_codes") or ())
    if train_eval_overlap_blocked:
        blockers.append(ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED)
    if train_eval_split_not_proven:
        blockers.append("TRAIN_EVAL_SPLIT_NOT_PROVEN")
    if target_policy_status == TARGET_POLICY_MISMATCH_BLOCKED:
        blockers.append(TARGET_POLICY_MISMATCH_BLOCKED)
    label_truth_status = str(label_row.get("label_truth_status") or "")
    if label_truth_status == LABEL_BLOCKED_BY_MISSING_POST_WINDOW:
        blockers.append(LABEL_BLOCKED_BY_MISSING_POST_WINDOW)
    if label_truth_status == LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY:
        blockers.append(LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY)
    if label_truth_status == LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN:
        blockers.append(LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN)
    if not _non_null_labels(row):
        blockers.append("LABEL_TARGET_MISSING")

    unique_blockers = tuple(dict.fromkeys(blockers))
    if not unique_blockers and actual_target_policy == STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY:
        return TRAINING_ROW_ELIGIBLE, ()
    research_only_blockers = {
        LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY,
        LABEL_BLOCKED_BY_FILL_REALISM_NOT_PROVEN,
        TARGET_POLICY_MISMATCH_BLOCKED,
    }
    if unique_blockers and set(unique_blockers).issubset(research_only_blockers):
        return TRAINING_ROW_RESEARCH_ONLY, unique_blockers
    if label_truth_status in {LABEL_PROXY_DISCOVERY_ONLY, LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY}:
        return TRAINING_ROW_RESEARCH_ONLY, unique_blockers
    return TRAINING_ROW_BLOCKED, unique_blockers


def _final_verdict(
    *,
    row_count: int,
    eligible_count: int,
    research_only_count: int,
    feature_leakage_count: int,
    target_policy_mismatch_count: int,
    missing_post_window_count: int,
    proxy_label_count: int,
    train_eval_overlap_blocked: bool,
    cost_fill_not_ready_count: int,
) -> str:
    if row_count <= 0:
        return B2_LABEL_STORE_INSUFFICIENT_ROWS
    if train_eval_overlap_blocked:
        return B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP
    if feature_leakage_count > 0:
        return B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE
    if missing_post_window_count >= row_count:
        return B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW
    if target_policy_mismatch_count > 0 and eligible_count == 0:
        return B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH
    if proxy_label_count > 0 and eligible_count == 0:
        return B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS
    if cost_fill_not_ready_count > 0 and eligible_count == 0:
        return B2_LABEL_STORE_BLOCKED_BY_COST_FILL_NOT_READY
    if eligible_count > 0 and research_only_count == 0:
        return B2_LABEL_STORE_TRAINING_READY
    return B2_LABEL_STORE_RESEARCH_ONLY


def write_b2_label_store_ml_training_audit_reports(
    run_dir: Path | str,
    *,
    label_store_path: Path | str | None = None,
    reports_dir: Path | str | None = None,
    target_policy_declared: str = STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
    training_manifest_root_or_path: Path | str | None = None,
    train_start: str = "",
    train_end: str = "",
    validation_start: str = "",
    validation_end: str = "",
    backtest_start: str = "",
    backtest_end: str = "",
) -> dict[str, Any]:
    """Write B2 label-store ML training audit reports and return the main payload."""

    resolved_run_dir = Path(run_dir).resolve()
    resolved_reports_dir = (
        Path(reports_dir).resolve() if reports_dir is not None else resolved_run_dir / "reports"
    )
    resolved_reports_dir.mkdir(parents=True, exist_ok=True)
    resolved_label_store_path = _resolve_label_store_path(
        resolved_run_dir,
        None if label_store_path is None else Path(label_store_path).resolve(),
    )
    generated_at = _now_iso()
    if resolved_label_store_path is None:
        main = {
            "schema_version": "v53.b2_label_store_ml_training_audit.v1",
            "generated_at": generated_at,
            "run_id": resolved_run_dir.name,
            "workflow_root": str(resolved_run_dir),
            "label_store_path": "NOT_FOUND",
            "row_count": 0,
            "feature_count": 0,
            "label_count": 0,
            "training_row_eligible_count": 0,
            "training_row_research_only_count": 0,
            "training_row_blocked_count": 0,
            "feature_leakage_count": 0,
            "target_policy_mismatch_count": 0,
            "missing_post_window_count": 0,
            "proxy_label_count": 0,
            "replay_grounded_label_count": 0,
            "execution_aware_label_count": 0,
            "cost_aware_label_count": 0,
            "fill_realism_proven_count": 0,
            "train_eval_overlap_status": "INSUFFICIENT_DATA",
            "label_fidelity_status": "LABEL_STORE_NOT_FOUND",
            "scientifically_valid_for_training": False,
            "scientifically_valid_for_promotion": False,
            "final_verdict": B2_LABEL_STORE_INSUFFICIENT_ROWS,
        }
        atomic_write_json(
            resolved_reports_dir / B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME,
            main,
            indent=2,
        )
        return main

    rows = _read_jsonl_dicts(resolved_label_store_path)
    candidate_index = _load_candidate_index(resolved_run_dir)
    training_report = build_training_source_contract_report(
        manifest_root_or_path=(
            None
            if training_manifest_root_or_path is None
            else Path(training_manifest_root_or_path).resolve()
        ),
        source_type="B2_REPLAY_GROUNDED_LABEL_STORE",
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        backtest_start=backtest_start,
        backtest_end=backtest_end,
    )
    train_eval_overlap_blocked = (
        ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED in training_report.blocker_reasons
    )
    train_eval_split_not_proven = training_report.overlap_status != "TRAINING_SOURCE_CONTRACT_OK"

    all_feature_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    alignment_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    eligibility_rows: list[dict[str, Any]] = []
    actual_policies: list[str] = []

    for row in rows:
        feature_rows = _feature_audit_rows(row)
        label_row = _label_audit_row(row)
        alignment = _alignment_row(row, candidate_index=candidate_index)
        actual_policy = _row_actual_target_policy(row)
        actual_policies.append(actual_policy)
        policy_status = _target_policy_status(
            declared_policy=target_policy_declared,
            actual_policy=actual_policy,
        )
        eligibility, blockers = _eligibility_status(
            row,
            feature_rows=feature_rows,
            label_row=label_row,
            alignment_row=alignment,
            declared_target_policy=target_policy_declared,
            actual_target_policy=actual_policy,
            target_policy_status=policy_status,
            train_eval_overlap_blocked=train_eval_overlap_blocked,
            train_eval_split_not_proven=train_eval_split_not_proven,
        )
        all_feature_rows.extend(feature_rows)
        label_rows.append(label_row)
        alignment_rows.append(alignment)
        target_rows.append(
            {
                "candidate_id": str(row.get("candidate_id") or ""),
                "target_policy_declared": target_policy_declared,
                "target_policy_actual": actual_policy,
                "status": policy_status,
                "label_fidelity": row.get("label_quality_status") or "MISSING_IN_ARTIFACT",
                "scientifically_valid_for_expected_edge": (
                    policy_status == TARGET_POLICY_MATCH
                    and eligibility == TRAINING_ROW_ELIGIBLE
                ),
                "allowed_for_training": eligibility == TRAINING_ROW_ELIGIBLE,
                "allowed_for_promotion": (
                    eligibility == TRAINING_ROW_ELIGIBLE
                    and row.get("label_quality_status")
                    == "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE"
                ),
            }
        )
        eligibility_rows.append(
            {
                "candidate_id": str(row.get("candidate_id") or ""),
                "capital_bucket": row.get("capital_bucket"),
                "eligibility_status": eligibility,
                "blocker_codes": blockers,
            }
        )

    row_count = len(rows)
    feature_count = len({item.get("feature_name") for item in all_feature_rows if item.get("feature_name") not in {"", "MISSING_IN_ARTIFACT"}})
    label_count = len({label for row in rows for label in _non_null_labels(row)})
    eligible_count = sum(1 for row in eligibility_rows if row["eligibility_status"] == TRAINING_ROW_ELIGIBLE)
    research_only_count = sum(1 for row in eligibility_rows if row["eligibility_status"] == TRAINING_ROW_RESEARCH_ONLY)
    blocked_count = sum(1 for row in eligibility_rows if row["eligibility_status"] == TRAINING_ROW_BLOCKED)
    feature_leakage_count = sum(
        1
        for item in all_feature_rows
        if item.get("status") == FEATURE_POST_DECISION_LEAKAGE_BLOCKED
    )
    target_policy_mismatch_count = sum(
        1 for row in target_rows if row["status"] == TARGET_POLICY_MISMATCH_BLOCKED
    )
    target_policy_unsatisfied_count = sum(
        1
        for row in target_rows
        if row["status"] == TARGET_POLICY_UNSATISFIED_FOR_TRAINING
    )
    missing_post_window_count = sum(
        1
        for row in label_rows
        if row["label_truth_status"] == LABEL_BLOCKED_BY_MISSING_POST_WINDOW
    )
    proxy_label_count = sum(
        1
        for row in label_rows
        if row["label_truth_status"]
        in {LABEL_PROXY_DISCOVERY_ONLY, LABEL_BLOCKED_BY_EXPECTED_EDGE_PROXY}
    )
    replay_grounded_label_count = sum(
        1 for row in rows if bool(row.get("replay_grounded_label_flag"))
    )
    execution_aware_label_count = sum(
        1 for row in rows if _has_value(row.get("executed_only_net_return"))
    )
    cost_aware_label_count = sum(
        1
        for row in rows
        if str(row.get("execution_fidelity_status") or "") == "EXECUTION_FIDELITY_READY"
    )
    fill_realism_proven_count = cost_aware_label_count
    cost_fill_not_ready_count = sum(
        1
        for row in rows
        if _has_value(row.get("executed_only_net_return"))
        and str(row.get("execution_fidelity_status") or "")
        != "EXECUTION_FIDELITY_READY"
    )
    final_verdict = _final_verdict(
        row_count=row_count,
        eligible_count=eligible_count,
        research_only_count=research_only_count,
        feature_leakage_count=feature_leakage_count,
        target_policy_mismatch_count=target_policy_mismatch_count,
        missing_post_window_count=missing_post_window_count,
        proxy_label_count=proxy_label_count,
        train_eval_overlap_blocked=train_eval_overlap_blocked,
        cost_fill_not_ready_count=cost_fill_not_ready_count,
    )
    target_policy_actual = _aggregate_actual_target_policy(tuple(actual_policies))
    main = {
        "schema_version": "v53.b2_label_store_ml_training_audit.v1",
        "generated_at": generated_at,
        "run_id": resolved_run_dir.name,
        "workflow_root": str(resolved_run_dir),
        "label_store_path": str(resolved_label_store_path.resolve()),
        "row_count": row_count,
        "feature_count": feature_count,
        "label_count": label_count,
        "training_row_eligible_count": eligible_count,
        "training_row_research_only_count": research_only_count,
        "training_row_blocked_count": blocked_count,
        "feature_leakage_count": feature_leakage_count,
        "target_policy_mismatch_count": target_policy_mismatch_count,
        "target_policy_unsatisfied_count": target_policy_unsatisfied_count,
        "missing_post_window_count": missing_post_window_count,
        "proxy_label_count": proxy_label_count,
        "replay_grounded_label_count": replay_grounded_label_count,
        "execution_aware_label_count": execution_aware_label_count,
        "cost_aware_label_count": cost_aware_label_count,
        "fill_realism_proven_count": fill_realism_proven_count,
        "train_eval_overlap_status": training_report.overlap_status,
        "label_fidelity_status": (
            "LABEL_FIDELITY_TRAINING_READY"
            if eligible_count > 0 and blocked_count == 0 and research_only_count == 0
            else "LABEL_FIDELITY_RESEARCH_ONLY_OR_BLOCKED"
        ),
        "target_policy_declared": target_policy_declared,
        "target_policy_actual": target_policy_actual,
        "scientifically_valid_for_training": final_verdict == B2_LABEL_STORE_TRAINING_READY,
        "scientifically_valid_for_promotion": (
            final_verdict == B2_LABEL_STORE_TRAINING_READY
            and all(row.get("allowed_for_promotion") for row in target_rows)
        ),
        "final_verdict": final_verdict,
    }

    alignment_report = {
        "schema_version": "v53.a2_b2_feature_label_alignment_report.v1",
        "generated_at": generated_at,
        "label_store_path": str(resolved_label_store_path.resolve()),
        "candidate_count": len(candidate_index),
        "row_count": row_count,
        "mismatch_count": sum(
            1
            for row in alignment_rows
            if row["alignment_status"] != "A2_B1_B2_ALIGNMENT_OK"
        ),
        "rows": alignment_rows,
    }
    label_fidelity_report = {
        "schema_version": "v53.ml_training_label_fidelity_report.v1",
        "generated_at": generated_at,
        "row_count": row_count,
        "proxy_label_count": proxy_label_count,
        "replay_grounded_label_count": replay_grounded_label_count,
        "execution_aware_label_count": execution_aware_label_count,
        "cost_aware_label_count": cost_aware_label_count,
        "rows": label_rows,
    }
    target_policy_report = {
        "schema_version": "v53.ml_target_policy_consistency_report.v1",
        "generated_at": generated_at,
        "target_policy_declared": target_policy_declared,
        "target_policy_actual": target_policy_actual,
        "target_policy_mismatch_count": target_policy_mismatch_count,
        "target_policy_unsatisfied_count": target_policy_unsatisfied_count,
        "rows": target_rows,
    }
    eligibility_report = {
        "schema_version": "v53.ml_training_row_eligibility_report.v1",
        "generated_at": generated_at,
        "row_count": row_count,
        "training_row_eligible_count": eligible_count,
        "training_row_research_only_count": research_only_count,
        "training_row_blocked_count": blocked_count,
        "rows": eligibility_rows,
    }
    feature_leakage_report = {
        "schema_version": "v53.ml_feature_label_leakage_report.v1",
        "generated_at": generated_at,
        "feature_leakage_count": feature_leakage_count,
        "rows": all_feature_rows,
    }
    overlap_report = training_report.model_dump(mode="json")

    atomic_write_json(resolved_reports_dir / B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME, main, indent=2)
    atomic_write_json(resolved_reports_dir / A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME, alignment_report, indent=2)
    atomic_write_json(resolved_reports_dir / ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME, label_fidelity_report, indent=2)
    atomic_write_json(resolved_reports_dir / ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME, target_policy_report, indent=2)
    atomic_write_json(resolved_reports_dir / ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME, eligibility_report, indent=2)
    atomic_write_json(resolved_reports_dir / ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME, feature_leakage_report, indent=2)
    atomic_write_json(resolved_reports_dir / ML_TRAIN_EVAL_WINDOW_OVERLAP_REPORT_FILENAME, overlap_report, indent=2)
    return main


__all__ = [
    "A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME",
    "B2_LABEL_STORE_BLOCKED_BY_COST_FILL_NOT_READY",
    "B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE",
    "B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW",
    "B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS",
    "B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH",
    "B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP",
    "B2_LABEL_STORE_INSUFFICIENT_ROWS",
    "B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME",
    "B2_LABEL_STORE_RESEARCH_ONLY",
    "B2_LABEL_STORE_TRAINING_READY",
    "FEATURE_POST_DECISION_LEAKAGE_BLOCKED",
    "LABEL_BLOCKED_BY_MISSING_POST_WINDOW",
    "ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME",
    "ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME",
    "ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME",
    "ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME",
    "TARGET_POLICY_MISMATCH_BLOCKED",
    "TARGET_POLICY_UNSATISFIED_FOR_TRAINING",
    "TRAINING_ROW_BLOCKED",
    "TRAINING_ROW_ELIGIBLE",
    "TRAINING_ROW_RESEARCH_ONLY",
    "write_b2_label_store_ml_training_audit_reports",
]
