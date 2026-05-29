"""Offline threshold sensitivity reports for V5.3 Strategy Ladder runs.

This module is reporting-only. It reads existing B1/B2 artifacts, computes
counterfactual threshold sensitivity, and never mutates trading decisions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME = "no_shadow_threshold_challenge_report.json"
THRESHOLD_SWEEP_BY_ENGINE_FILENAME = "threshold_sweep_by_engine.json"
THRESHOLD_RESPONSE_SURFACE_FILENAME = "threshold_response_surface.json"
THRESHOLD_NEAR_MISS_FAR_FAIL_FILENAME = "threshold_near_miss_far_fail_report.json"
THRESHOLD_GOVERNANCE_SURVIVAL_FILENAME = "threshold_governance_survival_report.json"
THRESHOLD_CHANGE_CANDIDATE_PACK_FILENAME = "threshold_change_candidate_pack.jsonl"
NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT_FILENAME = (
    "no_shadow_threshold_challenge_final_verdict.json"
)

OFFLINE_MODE = "OFFLINE_COUNTERFACTUAL_ONLY"
TEST_MODE = "TEST"
_SCHEMA_VERSION = "v53.no_shadow_threshold_challenge.v1"

_SELECTED_STATES = {"selected", "executed", "reduced", "phantom"}
_EXECUTED_STATES = {"executed", "reduced"}
_PROXY_OR_COST_TOKENS = (
    "PROXY",
    "DEFAULT_TO_CALIBRATE",
    "DEFAULT_BY_BOOK_STATUS",
    "FILL_REALISM_NOT_PROVEN",
    "FILL_REALISM_PARTIAL",
    "COST_FILL_REALISM_PARTIAL",
    "ADVERSE_SELECTION_PROXY",
    "FEE_MODEL_PROXY",
    "SLIPPAGE_MODEL_PROXY",
)
_GLOBAL_BLOCKER_TOKENS = (
    "EXPECTED_EDGE_PROXY_BLOCKED",
    "EXPECTED_EDGE_NOT_GOVERNED",
    "FEE_AWARE_EDGE_PROXY_BLOCKED",
    "BREAK_EVEN_PROXY_BLOCKED",
    "FEE_MODEL_PROXY",
    "SLIPPAGE_MODEL_PROXY",
    "ADVERSE_SELECTION_PROXY",
    "FILL_REALISM_NOT_PROVEN",
    "FILL_REALISM_PARTIAL",
    "BOOK_DEPTH_MISSING",
    "COST_REALISM_NOT_PROVEN",
    "BREAK_EVEN_NOT_CLEARED",
    "SHARIA",
    "SPOT_ONLY",
    "LONG_ONLY",
    "NO_SHORT",
    "MIN_NOTIONAL",
    "EXECUTION_BLOCKED",
)


@dataclass(frozen=True)
class ThresholdConfig:
    engine_id: str
    threshold_name: str
    metric_name: str
    comparison: str
    sweep_values: tuple[float, ...]
    source_family: str


@dataclass(frozen=True)
class ThresholdSpec:
    engine_id: str
    threshold_name: str
    metric_name: str
    comparison: str
    sweep_values: tuple[float, ...]
    current_value: float | None
    source_status: str
    source_family: str


@dataclass(frozen=True)
class CandidateObservation:
    candidate_id: str
    engine_id: str
    pair: str
    timeframe: str
    timestamp_ms: int | None
    sources: tuple[dict[str, Any], ...]
    reason_codes: tuple[str, ...]
    bucket_rows: tuple[dict[str, Any], ...]
    reconstruction_status: str


_SHARED_DELTA_SAFE_SWEEP = (0.0003, 0.0005, 0.0008, 0.0010, 0.0012)
_SHARED_CE_MIN_SWEEP = (0.00005, 0.0001, 0.0002, 0.0003)

_THRESHOLD_CONFIGS: tuple[ThresholdConfig, ...] = (
    ThresholdConfig(
        "engine_a",
        "min_direction",
        "direction_score",
        ">=",
        (0.10, 0.15, 0.20, 0.25, 0.30),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_a",
        "marginal",
        "structure_score",
        ">=",
        (0.20, 0.25, 0.30, 0.35, 0.40),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_a",
        "favorable",
        "structure_score",
        ">=",
        (0.50, 0.55, 0.60, 0.65, 0.70),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_a",
        "delta_safe",
        "expected_gain_minus_expected_cost",
        ">",
        _SHARED_DELTA_SAFE_SWEEP,
        "native_cost",
    ),
    ThresholdConfig(
        "engine_a",
        "ce_min",
        "ce_expected",
        ">=",
        _SHARED_CE_MIN_SWEEP,
        "native_cost",
    ),
    ThresholdConfig(
        "engine_b",
        "z_marginal",
        "abs_z_score",
        ">=",
        (0.60, 0.75, 0.90, 1.00, 1.10, 1.25),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_b",
        "z_star",
        "abs_z_score",
        ">=",
        (1.20, 1.35, 1.50, 1.65, 1.80),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_b",
        "delta_safe",
        "expected_gain_minus_expected_cost",
        ">",
        _SHARED_DELTA_SAFE_SWEEP,
        "native_cost",
    ),
    ThresholdConfig(
        "engine_b",
        "ce_min",
        "ce_expected",
        ">=",
        _SHARED_CE_MIN_SWEEP,
        "native_cost",
    ),
    ThresholdConfig(
        "engine_c",
        "breakout_score_min",
        "breakout_score",
        ">=",
        (0.50, 0.56, 0.62, 0.68, 0.74),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_c",
        "breakout_strength_min",
        "breakout_strength",
        ">=",
        (0.45, 0.50, 0.55, 0.60, 0.65),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_c",
        "range_quality_min",
        "range_quality",
        ">=",
        (0.40, 0.45, 0.50, 0.55, 0.60),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_c",
        "fake_breakout_risk_max",
        "fake_breakout_risk",
        "<",
        (0.55, 0.60, 0.65, 0.70, 0.75),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_d",
        "history_min",
        "history_score",
        ">=",
        (0.45, 0.50, 0.55, 0.60, 0.65),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_d",
        "reformation_min",
        "reformation_score",
        ">=",
        (0.48, 0.53, 0.58, 0.63, 0.68),
        "native_structure",
    ),
    ThresholdConfig(
        "engine_d",
        "concentration_max",
        "concentration_risk",
        "<",
        (0.54, 0.59, 0.64, 0.69, 0.74),
        "native_structure",
    ),
)


def _utc_now_iso() -> str:
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
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
    except OSError:
        return rows
    return rows


def _json_files(root: Path) -> tuple[Path, ...]:
    if not root.is_dir():
        return ()
    return tuple(sorted(path for path in root.rglob("*.json") if path.is_file()))


def _reports_dir(run_dir: Path) -> Path:
    return run_dir / "reports"


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


def _as_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return ()


def _candidate_rows(run_dir: Path) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in (
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        run_dir / "preselection_candidates.jsonl",
        run_dir / "fast_candidates" / "preselection_candidates.jsonl",
    ):
        for row in _read_jsonl(path):
            candidate_id = str(row.get("candidate_id") or "")
            if candidate_id:
                merged = dict(by_id.get(candidate_id) or {})
                merged.update(row)
                by_id[candidate_id] = merged
    return list(by_id.values())


def _bucket_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _json_files(run_dir / "detailed_replay" / "by_bucket"):
        payload = _read_json(path, {})
        if isinstance(payload, dict):
            row = dict(payload)
            row["_artifact_path"] = str(path.resolve())
            rows.append(row)
    return rows


def _refusal_rows(run_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir / "refusal_ledger.jsonl")


def _flatten_sources(*values: Any) -> tuple[dict[str, Any], ...]:
    sources: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        sources.append(value)
        for key in (
            "compatibility_payload",
            "feature_values",
            "dtr_record",
            "parity_payload",
            "entry_ref",
            "exit_ref",
            "invalidation_ref",
        ):
            nested = value.get(key)
            if isinstance(nested, dict):
                sources.append(nested)
    return tuple(sources)


def _infer_workflow_root(run_dir: Path) -> Path | None:
    resolved = run_dir.resolve()
    if (
        resolved.parent.name == "backtest_strategy_ladder"
        and resolved.parent.parent.name == "phase_b2_detailed_replay"
    ):
        return resolved.parent.parent.parent
    return None


def _load_reconstructed_sources(
    *,
    run_dir: Path,
    pairs: tuple[str, ...],
) -> tuple[dict[str, tuple[dict[str, Any], ...]], str, tuple[str, ...]]:
    workflow_root = _infer_workflow_root(run_dir)
    if workflow_root is None:
        return {}, "WORKFLOW_ROOT_NOT_INFERRED", ("MISSING_WORKFLOW_ROOT_LAYOUT",)

    try:
        from local_replay_runtime.engine_math_canary_audit import (  # noqa: PLC0415
            _load_scoped_candidate_contexts,
        )
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return {}, "RECONSTRUCTION_IMPORT_FAILED", (type(exc).__name__,)

    reconstructed: dict[str, tuple[dict[str, Any], ...]] = {}
    warnings: list[str] = []
    for pair in pairs or ("BTCUSDT",):
        try:
            contexts = _load_scoped_candidate_contexts(
                workflow_root=workflow_root,
                pair_filter=pair,
                start_ms=None,
                end_ms=None,
            )
        except Exception as exc:  # pragma: no cover - data-dependent safety
            warnings.append(f"{pair}:{type(exc).__name__}")
            continue
        for context in contexts:
            candidate_id = str(context.candidate.candidate_id)
            case = context.case
            reconstructed[candidate_id] = (
                dict(case.engine_input_payload),
                dict(case.output_payload),
                {
                    "engine_native_decision": case.decision,
                    "engine_native_reason_codes": list(case.reason_codes),
                    "engine_native_no_trade_reasons": list(case.no_trade_reasons),
                    "engine_native_builder_status": case.builder_status,
                    "engine_native_records_built": case.records_built,
                },
            )
    status = "RECONSTRUCTED_FROM_RAW_WINDOWS" if reconstructed else "RECONSTRUCTION_EMPTY"
    return reconstructed, status, tuple(warnings)


def _build_observations(
    *,
    run_dir: Path,
    candidate_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
    refusal_rows: list[dict[str, Any]],
) -> tuple[list[CandidateObservation], str, tuple[str, ...]]:
    bucket_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in bucket_rows:
        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id:
            bucket_by_candidate[candidate_id].append(row)

    refusal_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in refusal_rows:
        candidate_id = str(row.get("candidate_id") or "")
        if candidate_id:
            refusal_by_candidate[candidate_id].append(row)

    pairs = tuple(
        sorted({str(row.get("pair") or "").upper() for row in candidate_rows if row.get("pair")})
    )
    reconstructed, reconstruction_status, reconstruction_warnings = _load_reconstructed_sources(
        run_dir=run_dir,
        pairs=pairs,
    )

    observations: list[CandidateObservation] = []
    for row in candidate_rows:
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id:
            continue
        candidate_buckets = tuple(bucket_by_candidate.get(candidate_id) or ())
        candidate_refusals = tuple(refusal_by_candidate.get(candidate_id) or ())
        compat = row.get("compatibility_payload")
        reason_codes: list[str] = []
        for source in (row, compat if isinstance(compat, dict) else {}, *candidate_buckets, *candidate_refusals):
            if not isinstance(source, dict):
                continue
            for key in (
                "reason_codes",
                "preliminary_reason_codes",
                "hard_block_reasons",
                "engine_native_reason_codes",
                "engine_native_no_trade_reasons",
                "blocker_codes",
                "min_notional_reason_codes",
                "profitability_blocker_reasons",
            ):
                reason_codes.extend(_as_codes(source.get(key)))
        sources = list(_flatten_sources(row))
        for bucket in candidate_buckets:
            sources.extend(_flatten_sources(bucket))
        for refusal in candidate_refusals:
            sources.extend(_flatten_sources(refusal))
        sources.extend(reconstructed.get(candidate_id, ()))
        observations.append(
            CandidateObservation(
                candidate_id=candidate_id,
                engine_id=str(row.get("engine_id") or "").strip().lower(),
                pair=str(row.get("pair") or ""),
                timeframe=str(row.get("timeframe") or ""),
                timestamp_ms=_as_int(row.get("timestamp_ms")) or None,
                sources=tuple(sources),
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                bucket_rows=candidate_buckets,
                reconstruction_status=(
                    "RECONSTRUCTED_FROM_RAW_WINDOWS"
                    if candidate_id in reconstructed
                    else reconstruction_status
                ),
            )
        )
    return observations, reconstruction_status, reconstruction_warnings


def _load_current_thresholds() -> dict[tuple[str, str], tuple[float, str]]:
    thresholds: dict[tuple[str, str], tuple[float, str]] = {}
    try:
        from local_replay_runtime.engine_math_canary_audit import (  # noqa: PLC0415
            build_engine_equation_feature_registry,
            build_engine_threshold_boundary_report,
        )
    except Exception:
        return thresholds

    boundary = build_engine_threshold_boundary_report()
    for row in boundary.get("rows", ()):
        if not isinstance(row, dict):
            continue
        engine_id = str(row.get("engine_id") or "").strip().lower()
        threshold_name = str(row.get("threshold_name") or "").strip()
        value = _as_float(row.get("threshold_value"))
        if engine_id and threshold_name and value is not None:
            thresholds[(engine_id, threshold_name)] = (value, "ENGINE_THRESHOLD_BOUNDARY_REPORT")

    registry = build_engine_equation_feature_registry()
    for row in registry.get("rows", ()):
        if not isinstance(row, dict):
            continue
        engine_id = str(row.get("engine_id") or "").strip().lower()
        names = str(row.get("threshold_name") or "")
        value = str(row.get("threshold_value") or "")
        if engine_id == "engine_a" and names == "delta_safe/ce_min":
            parts = value.split("/")
            if len(parts) == 2:
                delta_safe = _as_float(parts[0])
                ce_min = _as_float(parts[1])
                if delta_safe is not None:
                    thresholds[(engine_id, "delta_safe")] = (
                        delta_safe,
                        "ENGINE_EQUATION_FEATURE_REGISTRY",
                    )
                if ce_min is not None:
                    thresholds[(engine_id, "ce_min")] = (
                        ce_min,
                        "ENGINE_EQUATION_FEATURE_REGISTRY",
                    )
    return thresholds


def _threshold_specs(
    current_thresholds: dict[tuple[str, str], tuple[float, str]] | None = None,
) -> tuple[ThresholdSpec, ...]:
    current = current_thresholds if current_thresholds is not None else _load_current_thresholds()
    specs: list[ThresholdSpec] = []
    for config in _THRESHOLD_CONFIGS:
        value_source = current.get((config.engine_id, config.threshold_name))
        current_value = value_source[0] if value_source is not None else None
        source_status = value_source[1] if value_source is not None else "NOT_FOUND"
        specs.append(
            ThresholdSpec(
                engine_id=config.engine_id,
                threshold_name=config.threshold_name,
                metric_name=config.metric_name,
                comparison=config.comparison,
                sweep_values=config.sweep_values,
                current_value=current_value,
                source_status=source_status,
                source_family=config.source_family,
            )
        )
    return tuple(specs)


def _source_float(sources: tuple[dict[str, Any], ...], *keys: str) -> float | None:
    for source in sources:
        for key in keys:
            value = _as_float(source.get(key))
            if value is not None:
                return value
    return None


def _metric_value(observation: CandidateObservation, metric_name: str) -> float | None:
    sources = observation.sources
    direct = _source_float(sources, metric_name)
    if direct is not None:
        return direct
    if metric_name == "abs_z_score":
        z_score = _source_float(sources, "z_score")
        if z_score is not None:
            return abs(z_score)
        current = _source_float(sources, "current_price")
        local_mean = _source_float(sources, "local_mean")
        local_std = _source_float(sources, "local_std")
        if current is not None and local_mean is not None and local_std and local_std > 0.0:
            return abs((current - local_mean) / local_std)
    if metric_name == "structure_score":
        raw_score = _source_float(sources, "structure_score", "raw_score")
        if raw_score is not None:
            return raw_score
        direction = _source_float(sources, "direction_score")
        continuation = _source_float(sources, "continuation_score")
        quality = _source_float(sources, "structure_quality")
        zone = _source_float(sources, "zone_proximity")
        stability = _source_float(sources, "trend_stability")
        if None not in (direction, continuation, quality, zone, stability):
            return (
                0.30 * abs(float(direction))
                + 0.25 * float(continuation)
                + 0.20 * float(quality)
                + 0.10 * float(zone)
                + 0.15 * float(stability)
            )
    if metric_name == "breakout_score":
        raw_score = _source_float(sources, "breakout_score", "raw_score")
        if raw_score is not None:
            return raw_score
    if metric_name == "expected_gain_minus_expected_cost":
        gain = _source_float(sources, "expected_gain", "engine_input_expected_gain")
        cost = _source_float(sources, "expected_cost", "production_expected_cost")
        if gain is not None and cost is not None:
            return gain - cost
    if metric_name == "ce_expected":
        ce_expected = _source_float(sources, "ce_expected", "expected_ce_net")
        if ce_expected is not None:
            return ce_expected
        gain = _source_float(sources, "expected_gain", "engine_input_expected_gain")
        cost = _source_float(sources, "expected_cost", "production_expected_cost")
        holding = _source_float(sources, "holding_period", "holding_hours", "expected_holding_hours")
        if gain is not None and cost is not None and holding and holding > 0.0:
            return (gain - cost) / holding
    if metric_name == "concentration_risk":
        concentration = _source_float(sources, "concentration_risk", "marginal_concentration")
        if concentration is not None:
            return concentration
        headroom = _source_float(sources, "concentration_headroom")
        lateness = _source_float(sources, "reentry_lateness")
        if headroom is not None and lateness is not None:
            return max(0.0, min(1.0, 0.60 * (1.0 - headroom) + 0.40 * lateness))
    return None


def _passes(value: float, threshold: float, comparison: str) -> bool:
    if comparison == "<":
        return value < threshold
    if comparison == "<=":
        return value <= threshold
    if comparison == ">":
        return value > threshold
    return value >= threshold


def _distance(value: float, threshold: float, comparison: str) -> float:
    if comparison in {"<", "<="}:
        return threshold - value
    return value - threshold


def _near_tolerance(threshold: float | None) -> float:
    if threshold is None:
        return 0.02
    absolute = abs(threshold)
    if absolute < 0.01:
        return max(absolute * 0.25, 0.00005)
    return 0.02


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _global_blockers(observation: CandidateObservation) -> tuple[str, ...]:
    blockers: list[str] = []
    for code in observation.reason_codes:
        upper = code.upper()
        if any(token in upper for token in _GLOBAL_BLOCKER_TOKENS):
            blockers.append(code)
    for row in observation.bucket_rows:
        for key in (
            "fill_realism_status",
            "fee_source_status",
            "impact_source_status",
            "cost_parity_status",
            "replay_outcome_status",
        ):
            value = str(row.get(key) or "")
            if any(token in value.upper() for token in _GLOBAL_BLOCKER_TOKENS):
                blockers.append(value)
    return tuple(dict.fromkeys(blockers))


def _candidate_full_native_pass(
    observation: CandidateObservation,
    specs: tuple[ThresholdSpec, ...],
    *,
    override: tuple[str, float] | None = None,
) -> tuple[bool, str]:
    engine_specs = [spec for spec in specs if spec.engine_id == observation.engine_id]
    if not engine_specs:
        return False, "NO_ENGINE_THRESHOLD_SPECS"
    for spec in engine_specs:
        if spec.current_value is None:
            return False, "THRESHOLD_NOT_FOUND"
        threshold = override[1] if override and override[0] == spec.threshold_name else spec.current_value
        value = _metric_value(observation, spec.metric_name)
        if value is None:
            return False, "MISSING_IN_ARTIFACT"
        if not _passes(value, threshold, spec.comparison):
            return False, "NATIVE_THRESHOLD_FAIL"
    return True, "NATIVE_COUNTERFACTUAL_PASS"


def _real_counts(
    *,
    summary: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
) -> dict[str, int]:
    selected_ids = {
        str(row.get("candidate_id") or "")
        for row in bucket_rows
        if str(row.get("execution_state") or "").lower() in _SELECTED_STATES
    }
    executed_ids = {
        str(row.get("candidate_id") or "")
        for row in bucket_rows
        if str(row.get("execution_state") or "").lower() in _EXECUTED_STATES
    }
    hard_blocked_ids = {
        str(row.get("candidate_id") or "")
        for row in bucket_rows
        if str(row.get("execution_state") or "").lower() == "hard_blocked"
    }
    return {
        "candidate_count": _as_int(summary.get("candidate_count")) or len(candidate_rows),
        "selected_count": len({item for item in selected_ids if item}),
        "executed_count": (
            _as_int(summary.get("executed_trade_count"))
            or _as_int(summary.get("executed_count"))
            or len({item for item in executed_ids if item})
        ),
        "hard_blocked_count": len({item for item in hard_blocked_ids if item}),
    }


def _cost_fill_ready(summary: dict[str, Any], reports: dict[str, Any]) -> tuple[bool, tuple[str, ...]]:
    blockers: list[str] = []
    values: list[Any] = [
        summary.get("blocker_codes"),
        summary.get("execution_fidelity_gap_codes"),
        summary.get("expected_edge_truth_status"),
        summary.get("expected_edge_label_fidelity"),
        summary.get("fee_model_source"),
        summary.get("spread_model_source"),
        summary.get("slippage_model_source"),
        summary.get("partial_fill_model_source"),
        summary.get("adverse_selection_source"),
    ]
    for payload in reports.values():
        if isinstance(payload, dict):
            values.append(payload.get("status"))
            values.append(payload.get("proxy_contamination_present"))
            values.append(payload.get("execution_fidelity_gap_codes"))
    joined = " ".join(
        str(item)
        for value in values
        for item in (value if isinstance(value, (list, tuple, set)) else (value,))
    ).upper()
    for token in _PROXY_OR_COST_TOKENS:
        if token in joined:
            blockers.append(token)
    ready = not blockers
    return ready, tuple(dict.fromkeys(blockers))


def _label_support_available(bucket_rows: list[dict[str, Any]]) -> bool:
    for row in bucket_rows:
        if str(row.get("executed_only_net_return_status") or "") == "EXECUTED_NET_RETURN_PROVEN":
            return True
        if _as_float(row.get("forward_return_h1")) is not None:
            return True
        if _as_float(row.get("mfe_bps")) is not None or _as_float(row.get("mae_bps")) is not None:
            return True
    return False


def _build_threshold_analysis(
    *,
    specs: tuple[ThresholdSpec, ...],
    observations: list[CandidateObservation],
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
]:
    by_engine: dict[str, list[CandidateObservation]] = defaultdict(list)
    for observation in observations:
        by_engine[observation.engine_id].append(observation)

    engine_payload: dict[str, dict[str, Any]] = {}
    response_surface: list[dict[str, Any]] = []
    near_rows: list[dict[str, Any]] = []
    candidate_pack: list[dict[str, Any]] = []
    governance_counter: Counter[str] = Counter()
    max_governance_survival = 0
    for observation in observations:
        governance_counter.update(_global_blockers(observation))

    specs_by_engine = {
        engine_id: tuple(spec for spec in specs if spec.engine_id == engine_id)
        for engine_id in sorted({spec.engine_id for spec in specs})
    }

    for engine_id in ("engine_a", "engine_b", "engine_c", "engine_d"):
        engine_specs = specs_by_engine.get(engine_id, ())
        engine_observations = by_engine.get(engine_id, [])
        threshold_results: list[dict[str, Any]] = []
        engine_near = 0
        engine_far = 0
        engine_missing = 0
        engine_governance_survival = 0

        for spec in engine_specs:
            distances: list[float] = []
            metric_rows: list[tuple[CandidateObservation, float, float]] = []
            missing_count = 0
            baseline_pass_count = 0
            tolerance = _near_tolerance(spec.current_value)
            if spec.current_value is None:
                missing_count = len(engine_observations)
            else:
                for observation in engine_observations:
                    metric = _metric_value(observation, spec.metric_name)
                    if metric is None:
                        missing_count += 1
                        continue
                    distance = _distance(metric, spec.current_value, spec.comparison)
                    distances.append(distance)
                    metric_rows.append((observation, metric, distance))
                    if _passes(metric, spec.current_value, spec.comparison):
                        baseline_pass_count += 1

            near_miss_count = sum(1 for _, _, distance in metric_rows if -tolerance <= distance < 0.0)
            far_fail_count = sum(1 for _, _, distance in metric_rows if distance < -tolerance)
            engine_near += near_miss_count
            engine_far += far_fail_count
            engine_missing += missing_count

            sweep_rows: list[dict[str, Any]] = []
            for tested_value in spec.sweep_values:
                threshold_native_pass = 0
                full_native_pass = 0
                governance_survival = 0
                slight_adjustment_pass = 0
                strong_adjustment_pass = 0
                for observation, metric, _ in metric_rows:
                    if _passes(metric, tested_value, spec.comparison):
                        threshold_native_pass += 1
                    full_pass, _ = _candidate_full_native_pass(
                        observation,
                        specs,
                        override=(spec.threshold_name, tested_value),
                    )
                    if not full_pass:
                        continue
                    full_native_pass += 1
                    blockers = _global_blockers(observation)
                    if blockers:
                        governance_counter.update(blockers)
                    else:
                        governance_survival += 1
                    if spec.current_value is not None:
                        relaxation = (
                            spec.current_value - tested_value
                            if spec.comparison in {">=", ">"}
                            else tested_value - spec.current_value
                        )
                        if 0.0 < relaxation <= tolerance:
                            slight_adjustment_pass += 1
                        elif relaxation > tolerance:
                            strong_adjustment_pass += 1
                max_governance_survival = max(max_governance_survival, governance_survival)
                engine_governance_survival = max(engine_governance_survival, governance_survival)
                row = {
                    "engine_id": engine_id,
                    "threshold_name": spec.threshold_name,
                    "tested_value": tested_value,
                    "current_value": spec.current_value,
                    "current_value_status": spec.source_status,
                    "metric_name": spec.metric_name,
                    "comparison": spec.comparison,
                    "candidate_count": len(engine_observations),
                    "metric_available_count": len(metric_rows),
                    "missing_metric_count": missing_count,
                    "native_pass_count": threshold_native_pass,
                    "native_fail_count": len(metric_rows) - threshold_native_pass,
                    "baseline_native_pass_count": baseline_pass_count,
                    "counterfactual_pass_count": full_native_pass,
                    "governance_survival_count": governance_survival,
                    "remaining_blockers": [
                        code for code, _ in governance_counter.most_common(8)
                    ],
                    "mean_distance_to_current_threshold": mean(distances) if distances else None,
                    "median_distance_to_current_threshold": median(distances) if distances else None,
                    "distance_distribution": {
                        "p10": _percentile(distances, 0.10),
                        "p50": _percentile(distances, 0.50),
                        "p90": _percentile(distances, 0.90),
                    },
                    "near_miss_count": near_miss_count,
                    "far_fail_count": far_fail_count,
                    "slight_adjustment_pass_count": slight_adjustment_pass,
                    "strong_adjustment_pass_count": strong_adjustment_pass,
                    "mode": OFFLINE_MODE,
                }
                sweep_rows.append(row)
                response_surface.append(row)

            for observation, metric, distance in metric_rows:
                blockers = _global_blockers(observation)
                full_current_pass, full_current_status = _candidate_full_native_pass(
                    observation,
                    specs,
                    override=None,
                )
                affected_values = [
                    row["tested_value"]
                    for row in sweep_rows
                    if spec.current_value is not None
                    and _passes(metric, float(row["tested_value"]), spec.comparison)
                    and not _passes(metric, spec.current_value, spec.comparison)
                ]
                if affected_values or (-tolerance <= distance < 0.0):
                    candidate_pack.append(
                        {
                            "candidate_id": observation.candidate_id,
                            "engine_id": engine_id,
                            "pair": observation.pair,
                            "timeframe": observation.timeframe,
                            "threshold_name": spec.threshold_name,
                            "current_value": spec.current_value,
                            "metric_name": spec.metric_name,
                            "measured_metric": metric,
                            "distance_to_current_threshold": distance,
                            "affected_tested_values": affected_values,
                            "native_pass_current": full_current_pass,
                            "native_status_current": full_current_status,
                            "governance_survives": not blockers,
                            "remaining_blockers": list(blockers),
                            "mode": OFFLINE_MODE,
                        }
                    )

            threshold_result = {
                "threshold_name": spec.threshold_name,
                "metric_name": spec.metric_name,
                "comparison": spec.comparison,
                "current_value": spec.current_value,
                "current_value_status": spec.source_status,
                "source_family": spec.source_family,
                "candidate_count": len(engine_observations),
                "metric_available_count": len(metric_rows),
                "missing_metric_count": missing_count,
                "near_miss_count": near_miss_count,
                "far_fail_count": far_fail_count,
                "baseline_native_pass_count": baseline_pass_count,
                "sweeps": sweep_rows,
                "status": (
                    "NOT_FOUND"
                    if spec.current_value is None
                    else "INSUFFICIENT_DATA"
                    if not metric_rows
                    else "OFFLINE_COUNTERFACTUAL_READY"
                ),
            }
            threshold_results.append(threshold_result)
            near_rows.append(
                {
                    "engine_id": engine_id,
                    "threshold_name": spec.threshold_name,
                    "current_value": spec.current_value,
                    "current_value_status": spec.source_status,
                    "near_miss_count": near_miss_count,
                    "far_fail_count": far_fail_count,
                    "missing_metric_count": missing_count,
                    "near_tolerance": tolerance,
                    "status": threshold_result["status"],
                }
            )

        engine_payload[engine_id] = {
            "candidate_count": len(engine_observations),
            "thresholds": threshold_results,
            "near_miss_count": engine_near,
            "far_fail_count": engine_far,
            "missing_metric_count": engine_missing,
            "max_governance_survival_count": engine_governance_survival,
            "recommendation": "CALIBRATION_PREMATURE",
        }

    governance = {
        "selected_count_after_counterfactual": max_governance_survival,
        "executed_count_after_counterfactual": 0,
        "execution_status": "NOT_REPLAYED_OFFLINE_COUNTERFACTUAL_ONLY",
        "dominant_remaining_blockers": [
            {"reason_code": code, "count": count}
            for code, count in governance_counter.most_common(10)
        ],
        "governance_preserved": True,
    }
    return engine_payload, response_surface, near_rows, governance, candidate_pack


def _apply_engine_recommendations(
    *,
    engine_results: dict[str, dict[str, Any]],
    cost_fill_ready: bool,
    label_support_available: bool,
) -> None:
    for engine_id, payload in engine_results.items():
        candidate_count = int(payload.get("candidate_count") or 0)
        near = int(payload.get("near_miss_count") or 0)
        far = int(payload.get("far_fail_count") or 0)
        survival = int(payload.get("max_governance_survival_count") or 0)
        missing = int(payload.get("missing_metric_count") or 0)
        if candidate_count < 30 or missing >= max(candidate_count, 1):
            recommendation = "CALIBRATION_PREMATURE"
        elif not cost_fill_ready or not label_support_available:
            recommendation = "CALIBRATION_PREMATURE"
        elif near > 0 and near >= far and survival > 0:
            recommendation = "REVIEW_THRESHOLD"
        else:
            recommendation = "KEEP_CURRENT"
        payload["recommendation"] = recommendation
        payload["recommendation_reason"] = (
            "INSUFFICIENT_SAMPLE_OR_MISSING_METRICS"
            if candidate_count < 30 or missing >= max(candidate_count, 1)
            else "COST_FILL_OR_LABEL_SUPPORT_NOT_READY"
            if not cost_fill_ready or not label_support_available
            else "NEAR_MISS_WITH_GOVERNANCE_SURVIVAL"
            if recommendation == "REVIEW_THRESHOLD"
            else "FAR_FAIL_OR_NO_GOVERNANCE_SURVIVAL"
        )
        payload["label_support_available"] = label_support_available
        payload["cost_fill_ready"] = cost_fill_ready
        payload["engine_id"] = engine_id


def _final_verdict(
    *,
    counts: dict[str, int],
    engine_results: dict[str, dict[str, Any]],
    cost_fill_ready: bool,
    cost_fill_blockers: tuple[str, ...],
) -> str:
    if counts["candidate_count"] <= 0:
        return "INSUFFICIENT_SAMPLE_FOR_THRESHOLD_CHALLENGE"
    if not cost_fill_ready:
        return "CALIBRATION_PREMATURE_COST_FILL_NOT_READY"
    review_engines = [
        engine_id
        for engine_id, payload in engine_results.items()
        if payload.get("recommendation") == "REVIEW_THRESHOLD"
    ]
    if review_engines:
        return f"THRESHOLD_REVIEW_NEEDED_{review_engines[0].upper()}"
    if counts["candidate_count"] < 30:
        return "INSUFFICIENT_SAMPLE_FOR_THRESHOLD_CHALLENGE"
    if cost_fill_blockers:
        return "CALIBRATION_PREMATURE_COST_FILL_NOT_READY"
    return "THRESHOLD_PATCH_NOT_JUSTIFIED"


def _load_support_reports(run_dir: Path) -> dict[str, Any]:
    reports = _reports_dir(run_dir)
    filenames = (
        "cost_fill_realism_report.json",
        "candidate_threshold_audit.json",
        "gate_counterfactual_matrix.json",
        "gate_waterfall_analysis.json",
        "feature_grounding_contract_report.json",
        "measured_spread_report.json",
        "measured_slippage_report.json",
        "fill_realism_report.json",
    )
    payloads: dict[str, Any] = {}
    for filename in filenames:
        payload = _read_json(reports / filename, {})
        if isinstance(payload, dict):
            payloads[filename] = payload
    return payloads


def _synthetic_governed_oracle(
    *,
    runtime_mode: str,
    synthetic_records: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if synthetic_records is None:
        return {"status": "NOT_REQUESTED"}
    if runtime_mode != TEST_MODE:
        raise ValueError("Synthetic governed oracle is allowed only in runtime_mode=TEST")
    return {
        "status": "SYNTHETIC_ORACLE_ONLY",
        "runtime_mode": TEST_MODE,
        "record_count": len(synthetic_records),
        "profitability_evidence_status": "NOT_REAL_BACKTEST_EVIDENCE",
    }


def build_no_shadow_threshold_challenge_payloads(
    run_dir: str | Path,
    *,
    runtime_mode: str = OFFLINE_MODE,
    synthetic_records: list[dict[str, Any]] | None = None,
    current_thresholds: dict[tuple[str, str], tuple[float, str]] | None = None,
) -> dict[str, Any]:
    """Build all no-shadow threshold challenge payloads without writing files."""

    if runtime_mode not in {OFFLINE_MODE, TEST_MODE}:
        runtime_mode = OFFLINE_MODE
    synthetic_oracle = _synthetic_governed_oracle(
        runtime_mode=runtime_mode,
        synthetic_records=synthetic_records,
    )
    resolved_run_dir = Path(run_dir)
    reports = _reports_dir(resolved_run_dir)
    summary = _read_json(reports / "strategy_ladder_summary.json", {})
    if not isinstance(summary, dict):
        summary = {}
    run_manifest = _read_json(resolved_run_dir / "run_manifest.json", {})
    if not isinstance(run_manifest, dict):
        run_manifest = {}

    candidates = _candidate_rows(resolved_run_dir)
    buckets = _bucket_rows(resolved_run_dir)
    refusals = _refusal_rows(resolved_run_dir)
    observations, reconstruction_status, reconstruction_warnings = _build_observations(
        run_dir=resolved_run_dir,
        candidate_rows=candidates,
        bucket_rows=buckets,
        refusal_rows=refusals,
    )
    specs = _threshold_specs(current_thresholds)
    support_reports = _load_support_reports(resolved_run_dir)
    counts = _real_counts(summary=summary, candidate_rows=candidates, bucket_rows=buckets)
    cost_ready, cost_blockers = _cost_fill_ready(summary, support_reports)
    labels_ready = _label_support_available(buckets) and counts["executed_count"] > 0
    (
        engine_results,
        response_surface_rows,
        near_miss_rows,
        governance_survival,
        candidate_pack_rows,
    ) = _build_threshold_analysis(specs=specs, observations=observations)
    _apply_engine_recommendations(
        engine_results=engine_results,
        cost_fill_ready=cost_ready,
        label_support_available=labels_ready,
    )
    verdict = _final_verdict(
        counts=counts,
        engine_results=engine_results,
        cost_fill_ready=cost_ready,
        cost_fill_blockers=cost_blockers,
    )

    thresholds_tested = [
        {
            "engine_id": spec.engine_id,
            "threshold_name": spec.threshold_name,
            "metric_name": spec.metric_name,
            "comparison": spec.comparison,
            "current_value": spec.current_value,
            "current_value_status": spec.source_status,
            "sweep_values": list(spec.sweep_values),
        }
        for spec in specs
    ]
    generated_at = _utc_now_iso()
    run_id = str(summary.get("run_id") or run_manifest.get("run_id") or resolved_run_dir.name)
    main_report = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": generated_at,
        "run_id": run_id,
        "run_dir": str(resolved_run_dir.resolve()),
        "mode": OFFLINE_MODE,
        "runtime_mode": runtime_mode,
        "shadow_used": False,
        "micro_live_used": False,
        "orders_sent": False,
        "trading_decisions_modified": False,
        "selected_count_real": counts["selected_count"],
        "executed_count_real": counts["executed_count"],
        "hard_blocked_count_real": counts["hard_blocked_count"],
        "candidate_count_real": counts["candidate_count"],
        "profitability_claim_allowed": False,
        "thresholds_tested": thresholds_tested,
        "reconstruction_status": reconstruction_status,
        "reconstruction_warnings": list(reconstruction_warnings),
        "source_artifact_status": {
            "candidate_events": "READY" if candidates else "MISSING_IN_ARTIFACT",
            "by_bucket_records": "READY" if buckets else "MISSING_IN_ARTIFACT",
            "refusal_ledger": "READY" if refusals else "MISSING_IN_ARTIFACT",
        },
        "cost_fill_ready": cost_ready,
        "cost_fill_blockers": list(cost_blockers),
        "label_support_available": labels_ready,
        "engine_results": engine_results,
        "governance_survival": governance_survival,
        "synthetic_governed_oracle": synthetic_oracle,
        "final_verdict": verdict,
    }
    sweep_by_engine = {
        "schema_version": "v53.threshold_sweep_by_engine.v1",
        "generated_at": generated_at,
        "run_id": run_id,
        "mode": OFFLINE_MODE,
        "engines": engine_results,
    }
    response_surface = {
        "schema_version": "v53.threshold_response_surface.v1",
        "generated_at": generated_at,
        "run_id": run_id,
        "mode": OFFLINE_MODE,
        "rows": response_surface_rows,
    }
    near_miss_far_fail = {
        "schema_version": "v53.threshold_near_miss_far_fail_report.v1",
        "generated_at": generated_at,
        "run_id": run_id,
        "mode": OFFLINE_MODE,
        "rows": near_miss_rows,
        "engine_summary": {
            engine_id: {
                "near_miss_count": payload.get("near_miss_count", 0),
                "far_fail_count": payload.get("far_fail_count", 0),
                "missing_metric_count": payload.get("missing_metric_count", 0),
                "recommendation": payload.get("recommendation"),
            }
            for engine_id, payload in engine_results.items()
        },
    }
    governance_payload = {
        "schema_version": "v53.threshold_governance_survival_report.v1",
        "generated_at": generated_at,
        "run_id": run_id,
        "mode": OFFLINE_MODE,
        **governance_survival,
        "real_selected_count": counts["selected_count"],
        "real_executed_count": counts["executed_count"],
        "trading_decisions_modified": False,
    }
    final_verdict = {
        "schema_version": "v53.no_shadow_threshold_challenge_final_verdict.v1",
        "generated_at": generated_at,
        "run_id": run_id,
        "verdict": verdict,
        "profitability_backtest_ready": False,
        "profitability_claim_allowed": False,
        "shadow_used": False,
        "trading_decisions_modified": False,
        "selected_count_real": counts["selected_count"],
        "executed_count_real": counts["executed_count"],
        "cost_fill_ready": cost_ready,
        "cost_fill_blockers": list(cost_blockers),
        "next_required_patch": (
            "GOVERN_COST_FILL_AND_LABELS_BEFORE_THRESHOLD_PATCH"
            if verdict == "CALIBRATION_PREMATURE_COST_FILL_NOT_READY"
            else "COLLECT_MORE_CANDIDATES_FOR_THRESHOLD_CHALLENGE"
            if verdict == "INSUFFICIENT_SAMPLE_FOR_THRESHOLD_CHALLENGE"
            else "NONE"
            if verdict == "THRESHOLD_PATCH_NOT_JUSTIFIED"
            else "OFFLINE_REVIEW_REQUIRED_FOR_LISTED_ENGINE"
        ),
    }
    return {
        NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME: main_report,
        THRESHOLD_SWEEP_BY_ENGINE_FILENAME: sweep_by_engine,
        THRESHOLD_RESPONSE_SURFACE_FILENAME: response_surface,
        THRESHOLD_NEAR_MISS_FAR_FAIL_FILENAME: near_miss_far_fail,
        THRESHOLD_GOVERNANCE_SURVIVAL_FILENAME: governance_payload,
        NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT_FILENAME: final_verdict,
        THRESHOLD_CHANGE_CANDIDATE_PACK_FILENAME: candidate_pack_rows,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows
    )
    path.write_text((payload + "\n") if payload else "", encoding="utf-8")


def _render_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# NO_SHADOW_THRESHOLD_CHALLENGE_REPORT",
        "",
        f"- run_id: {report.get('run_id', '')}",
        f"- mode: {report.get('mode', '')}",
        f"- shadow_used: {report.get('shadow_used')}",
        f"- trading_decisions_modified: {report.get('trading_decisions_modified')}",
        f"- selected_count_real: {report.get('selected_count_real', 0)}",
        f"- executed_count_real: {report.get('executed_count_real', 0)}",
        f"- profitability_claim_allowed: {report.get('profitability_claim_allowed')}",
        f"- final_verdict: {report.get('final_verdict', '')}",
        f"- cost_fill_ready: {report.get('cost_fill_ready')}",
        "",
        "## Engine recommendations",
        "",
    ]
    engine_results = report.get("engine_results") if isinstance(report, dict) else {}
    if isinstance(engine_results, dict):
        for engine_id, payload in engine_results.items():
            if not isinstance(payload, dict):
                continue
            lines.append(
                f"- {engine_id}: {payload.get('recommendation')} "
                f"(near={payload.get('near_miss_count', 0)}, "
                f"far={payload.get('far_fail_count', 0)}, "
                f"missing={payload.get('missing_metric_count', 0)})"
            )
    lines.extend(
        [
            "",
            "This report is offline counterfactual evidence only. It cannot be used as a",
            "profitability claim, live approval, shadow approval, or threshold patch by itself.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_final_verdict_markdown(verdict: dict[str, Any]) -> str:
    lines = [
        "# NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT",
        "",
        f"- run_id: {verdict.get('run_id', '')}",
        f"- verdict: {verdict.get('verdict', '')}",
        f"- profitability_backtest_ready: {verdict.get('profitability_backtest_ready')}",
        f"- profitability_claim_allowed: {verdict.get('profitability_claim_allowed')}",
        f"- shadow_used: {verdict.get('shadow_used')}",
        f"- trading_decisions_modified: {verdict.get('trading_decisions_modified')}",
        f"- selected_count_real: {verdict.get('selected_count_real', 0)}",
        f"- executed_count_real: {verdict.get('executed_count_real', 0)}",
        f"- next_required_patch: {verdict.get('next_required_patch', '')}",
        "",
        "No Engine A/B/C/D threshold is changed by this verdict.",
        "",
    ]
    return "\n".join(lines)


def write_no_shadow_threshold_challenge_reports(
    run_dir: str | Path,
    *,
    runtime_mode: str = OFFLINE_MODE,
    synthetic_records: list[dict[str, Any]] | None = None,
    docs_audit_dir: str | Path | None = None,
) -> dict[str, str]:
    """Write no-shadow threshold challenge reports for an existing B2 run."""

    resolved_run_dir = Path(run_dir)
    reports = _reports_dir(resolved_run_dir)
    reports.mkdir(parents=True, exist_ok=True)
    payloads = build_no_shadow_threshold_challenge_payloads(
        resolved_run_dir,
        runtime_mode=runtime_mode,
        synthetic_records=synthetic_records,
    )
    refs: dict[str, str] = {}
    for filename, payload in payloads.items():
        path = reports / filename
        refs[filename] = str(path.resolve())
        if filename == THRESHOLD_CHANGE_CANDIDATE_PACK_FILENAME:
            _write_jsonl(path, list(payload if isinstance(payload, list) else []))
        else:
            atomic_write_json(path, payload, indent=2)

    if docs_audit_dir is not None:
        docs_dir = Path(docs_audit_dir)
        docs_dir.mkdir(parents=True, exist_ok=True)
        report_payload = payloads[NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME]
        verdict_payload = payloads[NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT_FILENAME]
        if isinstance(report_payload, dict):
            report_path = docs_dir / "NO_SHADOW_THRESHOLD_CHALLENGE_REPORT.md"
            atomic_write_text(report_path, _render_report_markdown(report_payload))
            refs["NO_SHADOW_THRESHOLD_CHALLENGE_REPORT.md"] = str(report_path.resolve())
        if isinstance(verdict_payload, dict):
            verdict_path = docs_dir / "NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT.md"
            atomic_write_text(verdict_path, _render_final_verdict_markdown(verdict_payload))
            refs["NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT.md"] = str(verdict_path.resolve())
    return refs


__all__ = [
    "NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME",
    "NO_SHADOW_THRESHOLD_CHALLENGE_FINAL_VERDICT_FILENAME",
    "OFFLINE_MODE",
    "TEST_MODE",
    "build_no_shadow_threshold_challenge_payloads",
    "write_no_shadow_threshold_challenge_reports",
]
