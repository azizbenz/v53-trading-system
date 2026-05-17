"""Diagnostic-only B1->B2 candidate-to-trade semantics audit for Strategy Ladder.

This module explains why broad B1 discovery candidates become B2 native
``NO_TRADE`` decisions without altering any canonical replay truth.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_gate_waterfall_analysis import (
    GATE_COUNTERFACTUAL_MATRIX_FILENAME,
    GATE_WATERFALL_ANALYSIS_FILENAME,
    write_strategy_ladder_gate_waterfall_reports,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderReportSummary,
    StrategyLadderRunManifest,
    deterministic_payload_hash,
)


CANDIDATE_TRADE_SEMANTICS_AUDIT_FILENAME = "candidate_trade_semantics_audit.json"
CANDIDATE_TRADE_SEMANTICS_AUDIT_MARKDOWN_FILENAME = "candidate_trade_semantics_audit.md"
CANDIDATE_QUALITY_DISTRIBUTION_FILENAME = "candidate_quality_distribution.json"
CANDIDATE_VS_ENGINE_DECISION_MATRIX_FILENAME = (
    "candidate_vs_engine_decision_matrix.json"
)
CANDIDATE_THRESHOLD_AUDIT_FILENAME = "candidate_threshold_audit.json"

_DIAGNOSTIC_LABELS = (
    "RESEARCH_ONLY_COUNTERFACTUAL",
    "NON_PROMOTION_GRADE",
    "DIAGNOSTIC_ONLY",
)
_GENERIC_DISCOVERY_REASONS = frozenset(
    {
        "COMPAT_FEATURE_DISCOVERY",
        "NOT_LIVE_ENGINE_PARITY",
        "HARD_BLOCK_REASONS_PRESENT",
    }
)
_EXPECTED_B1_GATE_COVERAGE: dict[str, tuple[str, ...]] = {
    "engine_a": ("direction_layer", "structure_layer"),
    "engine_b": ("direction_layer", "structure_layer"),
    "engine_c": ("structure_layer", "microstructure_layer", "fragility_layer"),
    "engine_d": ("structure_layer", "governance_promotion_layer"),
}
_GATE_TO_MISSING_STATUS = {
    "direction_layer": "B1_MISSING_DIRECTION_GATE",
    "structure_layer": "B1_MISSING_STRUCTURE_GATE",
    "fragility_layer": "B1_MISSING_FRAGILITY_GATE",
    "microstructure_layer": "B1_MISSING_MICROSTRUCTURE_GATE",
    "expected_edge_layer": "B1_MISSING_EXPECTED_EDGE_GATE",
    "break_even_layer": "B1_MISSING_BREAK_EVEN_GATE",
    "fee_aware_edge_layer": "B1_MISSING_FEE_GATE",
    "spread_slippage_realism_layer": "B1_MISSING_EXECUTION_REALISM_GATE",
    "adverse_selection_layer": "B1_MISSING_EXECUTION_REALISM_GATE",
    "fill_realism_layer": "B1_MISSING_EXECUTION_REALISM_GATE",
    "governance_promotion_layer": "B1_MISSING_GOVERNANCE_GATE",
}
_COUNTERFACTUAL_FLAGS = (
    "would_survive_if_expected_edge_governed",
    "would_survive_if_break_even_measured",
    "would_survive_if_fee_aware_edge_governed",
    "would_survive_if_spread_realism_measured",
    "would_survive_if_slippage_realism_measured",
    "would_survive_if_adverse_selection_partial_allowed",
    "would_survive_if_execution_realism_partial",
    "would_survive_if_engine_c_fragility_relaxed",
    "would_survive_if_engine_d_history_available",
)
_THRESHOLD_AUDIT_DEFS: tuple[dict[str, object], ...] = (
    {
        "threshold_key": "b1_score_threshold",
        "engine_id": "all",
        "threshold_family": "score_threshold",
        "gate_id": "",
        "threshold_value": "NOT_APPLIED_IN_B1",
        "threshold_source": "src/local_replay_runtime/strategy_ladder_candidate_discovery.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "b1_timeframe_threshold",
        "engine_id": "all",
        "threshold_family": "timeframe_threshold",
        "gate_id": "",
        "threshold_value": "NOT_APPLIED_IN_B1",
        "threshold_source": "src/local_replay_runtime/strategy_ladder_candidate_discovery.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_a_direction_positive",
        "engine_id": "engine_a",
        "threshold_family": "direction_threshold",
        "gate_id": "direction_layer",
        "threshold_value": "direction_score > 0.0",
        "threshold_source": "src/engines/engine_a/engine_a_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_a_structure_thresholds",
        "engine_id": "engine_a",
        "threshold_family": "structure_threshold",
        "gate_id": "structure_layer",
        "threshold_value": "min_direction=0.20,favorable=0.60,marginal=0.30",
        "threshold_source": "src/engines/engine_a/structure_detector_a.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_a_cost_thresholds",
        "engine_id": "engine_a",
        "threshold_family": "cost_threshold",
        "gate_id": "fee_aware_edge_layer",
        "threshold_value": "delta_safe,ce_min from Engine A cost feasibility",
        "threshold_source": "src/engines/engine_a/cost_feasibility_a.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_b_direction_zscore",
        "engine_id": "engine_b",
        "threshold_family": "direction_threshold",
        "gate_id": "direction_layer",
        "threshold_value": "z_score <= 0.0",
        "threshold_source": "src/engines/engine_b/engine_b_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_b_breakout_filter",
        "engine_id": "engine_b",
        "threshold_family": "structure_threshold",
        "gate_id": "structure_layer",
        "threshold_value": "blocked/warning from Engine B anti-breakout filter",
        "threshold_source": "src/engines/engine_b/anti_breakout_filter_b.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_b_cost_thresholds",
        "engine_id": "engine_b",
        "threshold_family": "cost_threshold",
        "gate_id": "fee_aware_edge_layer",
        "threshold_value": "delta_safe,ce_min from Engine B cost feasibility",
        "threshold_source": "src/engines/engine_b/cost_feasibility_b.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_c_breakout_structure",
        "engine_id": "engine_c",
        "threshold_family": "structure_threshold",
        "gate_id": "structure_layer",
        "threshold_value": (
            "breakout_score>=0.62,breakout_strength>=0.55,"
            "range_quality>=0.50"
        ),
        "threshold_source": "src/engines/engine_c/engine_c_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_c_continuation_microstructure",
        "engine_id": "engine_c",
        "threshold_family": "liquidity_threshold",
        "gate_id": "microstructure_layer",
        "threshold_value": "continuation_score>=0.58,extension_pct<=0.72",
        "threshold_source": "src/engines/engine_c/continuation_validator_c.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_c_fragility",
        "engine_id": "engine_c",
        "threshold_family": "fragility_threshold",
        "gate_id": "fragility_layer",
        "threshold_value": "BUILD14 fragility/false_breakout elevated blocks",
        "threshold_source": "src/local_replay_runtime/strategy_ladder_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_c_cost_thresholds",
        "engine_id": "engine_c",
        "threshold_family": "cost_threshold",
        "gate_id": "fee_aware_edge_layer",
        "threshold_value": "delta_safe,ce_min from Engine C cost feasibility",
        "threshold_source": "src/engines/engine_c/cost_feasibility_c.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_d_history_threshold",
        "engine_id": "engine_d",
        "threshold_family": "structure_threshold",
        "gate_id": "governance_promotion_layer",
        "threshold_value": "history_score >= 0.55",
        "threshold_source": "src/engines/engine_d/engine_d_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_d_reformation_threshold",
        "engine_id": "engine_d",
        "threshold_family": "structure_threshold",
        "gate_id": "structure_layer",
        "threshold_value": "reformation_score >= 0.58",
        "threshold_source": "src/engines/engine_d/engine_d_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_d_concentration_threshold",
        "engine_id": "engine_d",
        "threshold_family": "liquidity_threshold",
        "gate_id": "structure_layer",
        "threshold_value": "concentration_risk < 0.64",
        "threshold_source": "src/engines/engine_d/engine_d_runner.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
    {
        "threshold_key": "engine_d_cost_thresholds",
        "engine_id": "engine_d",
        "threshold_family": "cost_threshold",
        "gate_id": "fee_aware_edge_layer",
        "threshold_value": "delta_safe,ce_min from Engine D cost feasibility",
        "threshold_source": "src/engines/engine_d/cost_feasibility_d.py",
        "threshold_source_status": "THRESHOLD_DEFAULT_TO_CALIBRATE",
    },
)


class StrategyLadderCandidateTradeSemanticsAuditBuildResult(BaseModel, frozen=True):
    status: str = Field(..., min_length=1)
    candidate_trade_semantics_audit_path: str = Field(..., min_length=1)
    candidate_quality_distribution_path: str = Field(..., min_length=1)
    candidate_vs_engine_decision_matrix_path: str = Field(..., min_length=1)
    candidate_threshold_audit_path: str = Field(..., min_length=1)
    canonical_selected_count: int = Field(default=0, ge=0)
    canonical_executed_count: int = Field(default=0, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    engine_native_no_trade_count: int = Field(default=0, ge=0)
    hard_blocked_candidate_count: int = Field(default=0, ge=0)
    dominant_semantic_mismatch_status: str = ""
    recommendation_count: int = Field(default=0, ge=0)


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_candidate_events(path: Path) -> tuple[StrategyLadderCandidateEvent, ...]:
    if not path.is_file():
        return ()
    rows: list[StrategyLadderCandidateEvent] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(StrategyLadderCandidateEvent.model_validate_json(line))
    return tuple(rows)


def _load_run_manifest(run_dir: Path) -> StrategyLadderRunManifest | None:
    path = run_dir / "run_manifest.json"
    if not path.is_file():
        return None
    try:
        return StrategyLadderRunManifest.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, TypeError, ValueError):
        return None


def _load_report_summary(run_dir: Path) -> StrategyLadderReportSummary | None:
    path = run_dir / "reports" / "strategy_ladder_summary.json"
    if not path.is_file():
        return None
    try:
        return StrategyLadderReportSummary.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, TypeError, ValueError):
        return None


def _resolve_b1_candidate_path(
    run_dir: Path,
    run_manifest: StrategyLadderRunManifest | None,
) -> Path | None:
    if run_manifest is not None and run_manifest.parent_workflow_ref:
        workflow_root = Path(run_manifest.parent_workflow_ref).resolve().parent
        candidate_path = (
            workflow_root
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / (run_manifest.run_id or run_dir.name)
            / "fast_candidates"
            / "candidate_events.jsonl"
        )
        if candidate_path.is_file():
            return candidate_path
    if len(run_dir.parents) >= 3 and run_dir.parents[1].name == "phase_b2_detailed_replay":
        workflow_root = run_dir.parents[2]
        candidate_path = (
            workflow_root
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / run_dir.name
            / "fast_candidates"
            / "candidate_events.jsonl"
        )
        if candidate_path.is_file():
            return candidate_path
    current_path = run_dir / "fast_candidates" / "candidate_events.jsonl"
    if current_path.is_file():
        rows = _read_candidate_events(current_path)
        if rows and all(row.candidate_source == "COMPAT_FEATURE_DISCOVERY" for row in rows):
            return current_path
    return None


def _load_gate_counterfactual_matrix(
    run_dir: Path,
    *,
    summary: StrategyLadderReportSummary | None,
    run_manifest: StrategyLadderRunManifest | None,
    gate_counterfactual_matrix_path: Path | None,
) -> tuple[dict[str, object], Path]:
    resolved = gate_counterfactual_matrix_path or (
        run_dir / "reports" / GATE_COUNTERFACTUAL_MATRIX_FILENAME
    )
    if resolved.is_file():
        return _read_json(resolved), resolved.resolve()
    if summary is None or run_manifest is None:
        raise ValueError(
            "Candidate trade semantics audit requires gate waterfall reports or "
            "summary/run manifest to build them."
        )
    write_strategy_ladder_gate_waterfall_reports(
        run_dir=run_dir,
        summary=summary,
        run_manifest=run_manifest,
    )
    return _read_json(resolved), resolved.resolve()


def _primary_reason(reason_codes: tuple[str, ...]) -> str:
    for reason in reason_codes:
        if reason not in _GENERIC_DISCOVERY_REASONS and reason:
            return reason
    return reason_codes[0] if reason_codes else ""


def _engine_native_decision(event: StrategyLadderCandidateEvent | None) -> str:
    if event is None:
        return "not_available"
    payload = event.compatibility_payload or {}
    decision = str(payload.get("engine_native_decision") or "").strip().lower()
    if decision:
        return decision
    for reason in event.preliminary_reason_codes:
        if reason.startswith("ENGINE_NATIVE_DECISION:"):
            return reason.split(":", 1)[1].strip().lower()
    return "not_available"


def _candidate_strength_score(
    source_event: StrategyLadderCandidateEvent | None,
    materialized_event: StrategyLadderCandidateEvent | None,
) -> float | None:
    for event in (source_event, materialized_event):
        if event is None:
            continue
        if event.preliminary_score is not None:
            return float(event.preliminary_score)
        payload = event.compatibility_payload or {}
        for key in ("final_score", "penalized_score", "raw_score"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _quality_bucket(score: float | None) -> str:
    if score is None:
        return "QUALITY_UNKNOWN"
    if score <= 0.0:
        return "QUALITY_ZERO_OR_NEGATIVE"
    if score < 0.25:
        return "QUALITY_WEAK"
    if score < 0.60:
        return "QUALITY_MEDIUM"
    return "QUALITY_STRONG"


def _reason_to_gate(engine_id: str, reason_code: str) -> str:
    lower = reason_code.lower()
    if not lower:
        return ""
    if "non_long_direction" in lower or ".direction.non_long" in lower:
        return "direction_layer"
    if (
        "structure" in lower
        or "breakout.blocked" in lower
        or "breakout.unstructured" in lower
        or "reformation_weak" in lower
    ):
        return "structure_layer"
    if reason_code.startswith("BUILD14_READER:"):
        return "fragility_layer"
    if "microstructure" in lower or "ofi_" in lower or "queue_pressure" in lower or "vpin" in lower:
        return "microstructure_layer"
    if reason_code.startswith("EXPECTED_EDGE_"):
        return "expected_edge_layer"
    if "break_even" in lower:
        return "break_even_layer"
    if "fee_aware" in lower or ".cost." in lower or "cost_infeasible" in lower:
        return "fee_aware_edge_layer"
    if "adverse_selection" in lower:
        return "adverse_selection_layer"
    if "fill_realism" in lower:
        return "fill_realism_layer"
    if "closed_episode" in lower or "history_weak" in lower:
        return "governance_promotion_layer"
    if engine_id == "engine_d" and "first_episode" in lower:
        return "governance_promotion_layer"
    return ""


def _source_gate_coverage(event: StrategyLadderCandidateEvent | None) -> tuple[str, ...]:
    if event is None:
        return ()
    payload = event.compatibility_payload or {}
    raw_codes: list[str] = list(event.preliminary_reason_codes)
    raw_codes.extend(
        str(code)
        for code in payload.get("hard_block_reasons", ())
        if str(code).strip()
    )
    primary_reason = str(payload.get("primary_reason") or "").strip()
    if primary_reason:
        raw_codes.append(primary_reason)
    gates = [
        gate
        for gate in (_reason_to_gate(event.engine_id, code) for code in raw_codes)
        if gate
    ]
    return tuple(dict.fromkeys(gates))


def _group_matrix_rows(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id:
            grouped[candidate_id].append(dict(row))
    return grouped


def _most_common_string(values: list[str]) -> str:
    filtered = [value for value in values if value]
    if not filtered:
        return ""
    return Counter(filtered).most_common(1)[0][0]


def _candidate_semantic_class(
    *,
    source_event: StrategyLadderCandidateEvent | None,
    materialized_event: StrategyLadderCandidateEvent | None,
    engine_recheck_decision: str,
    hard_blocked_replay_count: int,
    replay_record_count: int,
    first_blocking_gate: str,
) -> str:
    if materialized_event is None:
        return "DISCOVERY_PRE_CANDIDATE"
    if engine_recheck_decision == "emit" and first_blocking_gate in {"", "NO_BLOCKING_GATE"}:
        return "TRADE_ELIGIBLE_CANDIDATE"
    if engine_recheck_decision == "emit" and hard_blocked_replay_count > 0:
        return "HARD_BLOCKED_CANDIDATE"
    if engine_recheck_decision != "emit":
        return "ENGINE_NATIVE_NO_TRADE"
    if replay_record_count > 0 and hard_blocked_replay_count == replay_record_count:
        return "HARD_BLOCKED_CANDIDATE"
    if source_event is not None and source_event.candidate_source == "COMPAT_FEATURE_DISCOVERY":
        return "DISCOVERY_PRE_CANDIDATE"
    return "ENGINE_NATIVE_CANDIDATE"


def _candidate_intent(
    *,
    source_event: StrategyLadderCandidateEvent | None,
    materialized_event: StrategyLadderCandidateEvent | None,
    engine_recheck_decision: str,
) -> str:
    if source_event is not None and source_event.candidate_source == "COMPAT_FEATURE_DISCOVERY":
        return "DISCOVERY_PRE_CANDIDATE"
    if materialized_event is not None and engine_recheck_decision == "emit":
        return "TRADE_ELIGIBLE_CANDIDATE"
    if materialized_event is not None:
        return "ENGINE_NATIVE_CANDIDATE"
    return "DISCOVERY_PRE_CANDIDATE"


def _semantic_mismatch_status(
    *,
    engine_id: str,
    source_event: StrategyLadderCandidateEvent | None,
    source_gates: tuple[str, ...],
    first_blocking_gate: str,
    semantic_classification: str,
    engine_recheck_decision: str,
) -> str:
    if semantic_classification == "TRADE_ELIGIBLE_CANDIDATE":
        return "B1_B2_TRADE_ELIGIBLE_CONSISTENT"
    if semantic_classification == "HARD_BLOCKED_CANDIDATE" and engine_recheck_decision == "emit":
        return "B2_HARD_BLOCK_AFTER_ENGINE_EMIT"
    if first_blocking_gate and first_blocking_gate in source_gates:
        return "B1_B2_SAME_GATE_MISMATCH"
    expected = _EXPECTED_B1_GATE_COVERAGE.get(engine_id, ())
    if first_blocking_gate in expected:
        return _GATE_TO_MISSING_STATUS.get(first_blocking_gate, "B1_B2_SEMANTIC_MISMATCH")
    if (
        source_event is not None
        and source_event.candidate_source == "COMPAT_FEATURE_DISCOVERY"
        and semantic_classification == "ENGINE_NATIVE_NO_TRADE"
    ):
        return "B1_PRE_CANDIDATE_EXPECTED_ENGINE_RECHECK"
    return "B1_B2_SEMANTIC_MISMATCH"


def _build_candidate_rows(
    *,
    source_candidates: tuple[StrategyLadderCandidateEvent, ...],
    materialized_candidates: tuple[StrategyLadderCandidateEvent, ...],
    matrix_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    source_index = {item.candidate_id: item for item in source_candidates}
    materialized_index = {item.candidate_id: item for item in materialized_candidates}
    grouped_matrix_rows = _group_matrix_rows(matrix_rows)
    candidate_ids = tuple(
        sorted(
            {
                *source_index.keys(),
                *materialized_index.keys(),
                *grouped_matrix_rows.keys(),
            }
        )
    )
    rows: list[dict[str, object]] = []
    for candidate_id in candidate_ids:
        source_event = source_index.get(candidate_id)
        materialized_event = materialized_index.get(candidate_id)
        replay_rows = grouped_matrix_rows.get(candidate_id, [])
        engine_id = (
            materialized_event.engine_id
            if materialized_event is not None
            else (
                source_event.engine_id
                if source_event is not None
                else str(replay_rows[0].get("engine_id") or "")
            )
        )
        timeframe = (
            materialized_event.timeframe
            if materialized_event is not None and materialized_event.timeframe
            else (
                source_event.timeframe
                if source_event is not None and source_event.timeframe
                else str(replay_rows[0].get("timeframe") or "unknown")
            )
        )
        pair = (
            materialized_event.pair
            if materialized_event is not None
            else (
                source_event.pair
                if source_event is not None
                else str(replay_rows[0].get("pair") or "")
            )
        )
        decision_timestamp_ms = (
            materialized_event.resolved_timestamp_ms
            if materialized_event is not None
            else (
                source_event.resolved_timestamp_ms
                if source_event is not None
                else int(replay_rows[0].get("decision_timestamp_ms") or 0)
            )
        )
        engine_recheck_decision = _engine_native_decision(materialized_event)
        source_reason_codes = (
            source_event.preliminary_reason_codes if source_event is not None else ()
        )
        materialized_reason_codes = (
            materialized_event.preliminary_reason_codes
            if materialized_event is not None
            else ()
        )
        strength_score = _candidate_strength_score(source_event, materialized_event)
        quality_bucket = _quality_bucket(strength_score)
        first_blocking_gate = _most_common_string(
            [str(row.get("first_blocking_gate") or "") for row in replay_rows]
        )
        blocking_reason_primary = _most_common_string(
            [str(row.get("blocking_reason_primary") or "") for row in replay_rows]
        )
        blocking_reason_secondary = _most_common_string(
            [str(row.get("blocking_reason_secondary") or "") for row in replay_rows]
        )
        hard_blocked_replay_count = sum(
            1 for row in replay_rows if str(row.get("execution_state") or "") == "hard_blocked"
        )
        replay_record_count = len(replay_rows)
        source_gates = _source_gate_coverage(source_event)
        semantic_classification = _candidate_semantic_class(
            source_event=source_event,
            materialized_event=materialized_event,
            engine_recheck_decision=engine_recheck_decision,
            hard_blocked_replay_count=hard_blocked_replay_count,
            replay_record_count=replay_record_count,
            first_blocking_gate=first_blocking_gate,
        )
        semantic_mismatch_status = _semantic_mismatch_status(
            engine_id=engine_id,
            source_event=source_event,
            source_gates=source_gates,
            first_blocking_gate=first_blocking_gate,
            semantic_classification=semantic_classification,
            engine_recheck_decision=engine_recheck_decision,
        )
        counterfactual_survival_count = sum(
            1
            for row in replay_rows
            if any(bool(row.get(flag)) for flag in _COUNTERFACTUAL_FLAGS)
        )
        source_payload = source_event.compatibility_payload if source_event is not None else {}
        materialized_payload = (
            materialized_event.compatibility_payload if materialized_event is not None else {}
        )
        rows.append(
            {
                "candidate_id": candidate_id,
                "engine_id": engine_id,
                "pair": pair,
                "timeframe": timeframe or "unknown",
                "decision_timestamp_ms": decision_timestamp_ms,
                "source_candidate_source": (
                    source_event.candidate_source if source_event is not None else ""
                ),
                "materialized_candidate_source": (
                    materialized_event.candidate_source
                    if materialized_event is not None
                    else ""
                ),
                "candidate_intent": _candidate_intent(
                    source_event=source_event,
                    materialized_event=materialized_event,
                    engine_recheck_decision=engine_recheck_decision,
                ),
                "semantic_classification": semantic_classification,
                "candidate_strength_score": strength_score,
                "candidate_quality_bucket": quality_bucket,
                "candidate_generation_reason": _primary_reason(source_reason_codes),
                "engine_recheck_decision": engine_recheck_decision,
                "engine_recheck_reason": (
                    blocking_reason_primary or _primary_reason(materialized_reason_codes)
                ),
                "first_blocking_gate": first_blocking_gate or "",
                "blocking_reason_primary": blocking_reason_primary,
                "blocking_reason_secondary": blocking_reason_secondary,
                "source_gate_coverage": source_gates,
                "expected_b1_gate_coverage": _EXPECTED_B1_GATE_COVERAGE.get(engine_id, ()),
                "semantic_mismatch_status": semantic_mismatch_status,
                "source_preliminary_reasons": source_reason_codes,
                "materialized_preliminary_reasons": materialized_reason_codes,
                "replay_record_count": replay_record_count,
                "hard_blocked_replay_count": hard_blocked_replay_count,
                "counterfactual_survival_count": counterfactual_survival_count,
                "candidate_source_status": (
                    str(source_payload.get("candidate_data_source_label") or "")
                    if isinstance(source_payload, dict)
                    else ""
                ),
                "engine_native_builder_status": (
                    str(materialized_payload.get("engine_native_builder_status") or "")
                    if isinstance(materialized_payload, dict)
                    else ""
                ),
                "engine_native_input_provenance": (
                    str(materialized_payload.get("engine_native_input_provenance") or "")
                    if isinstance(materialized_payload, dict)
                    else ""
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            int(row.get("decision_timestamp_ms") or 0),
            str(row.get("pair") or ""),
            str(row.get("engine_id") or ""),
            str(row.get("candidate_id") or ""),
        ),
    )


def _candidate_quality_distribution(
    candidate_rows: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
) -> dict[str, object]:
    bucket_counts = Counter(
        str(row.get("candidate_quality_bucket") or "QUALITY_UNKNOWN")
        for row in candidate_rows
    )
    by_engine: list[dict[str, object]] = []
    for engine_id in sorted({str(row.get("engine_id") or "") for row in candidate_rows}):
        engine_rows = [row for row in candidate_rows if row.get("engine_id") == engine_id]
        by_engine.append(
            {
                "engine_id": engine_id,
                "candidate_count": len(engine_rows),
                "quality_bucket_counts": {
                    bucket: sum(
                        1
                        for row in engine_rows
                        if row.get("candidate_quality_bucket") == bucket
                    )
                    for bucket in sorted(
                        {str(row.get("candidate_quality_bucket") or "") for row in engine_rows}
                    )
                },
                "mean_candidate_strength_score": round(
                    sum(
                        float(row.get("candidate_strength_score") or 0.0)
                        for row in engine_rows
                        if row.get("candidate_strength_score") is not None
                    )
                    / max(
                        sum(
                            1
                            for row in engine_rows
                            if row.get("candidate_strength_score") is not None
                        ),
                        1,
                    ),
                    6,
                ),
            }
        )
    by_timeframe: list[dict[str, object]] = []
    for timeframe in sorted({str(row.get("timeframe") or "") for row in candidate_rows}):
        timeframe_candidates = [row for row in candidate_rows if row.get("timeframe") == timeframe]
        timeframe_replays = [row for row in matrix_rows if str(row.get("timeframe") or "") == timeframe]
        replay_count = len(timeframe_replays)
        by_timeframe.append(
            {
                "timeframe": timeframe,
                "candidate_count": len(timeframe_candidates),
                "quality_bucket_counts": {
                    bucket: sum(
                        1
                        for row in timeframe_candidates
                        if row.get("candidate_quality_bucket") == bucket
                    )
                    for bucket in sorted(
                        {
                            str(row.get("candidate_quality_bucket") or "")
                            for row in timeframe_candidates
                        }
                    )
                },
                "no_trade_rate": round(
                    sum(
                        1
                        for row in timeframe_candidates
                        if row.get("semantic_classification") == "ENGINE_NATIVE_NO_TRADE"
                    )
                    / max(len(timeframe_candidates), 1),
                    6,
                ),
                "non_long_direction_rate": round(
                    sum(
                        1
                        for row in timeframe_replays
                        if str(row.get("first_blocking_gate") or "") == "direction_layer"
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "fragility_rejection_rate": round(
                    sum(
                        1
                        for row in timeframe_replays
                        if str(row.get("first_blocking_gate") or "") == "fragility_layer"
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "expected_edge_proxy_rejection_rate": round(
                    sum(
                        1
                        for row in timeframe_replays
                        if "EXPECTED_EDGE_PROXY_BLOCKED"
                        in tuple(str(code) for code in row.get("blocking_reason_codes", ()))
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "would_survive_counterfactual_count": sum(
                    1
                    for row in timeframe_replays
                    if any(bool(row.get(flag)) for flag in _COUNTERFACTUAL_FLAGS)
                ),
            }
        )
    payload = {
        "schema_version": "v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "CANDIDATE_QUALITY_DISTRIBUTION_READY",
        "candidate_count": len(candidate_rows),
        "quality_bucket_counts": dict(sorted(bucket_counts.items())),
        "by_engine": by_engine,
        "by_timeframe": by_timeframe,
    }
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return payload


def _candidate_vs_engine_matrix(
    candidate_rows: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
) -> dict[str, object]:
    matrix_by_candidate = _group_matrix_rows(matrix_rows)
    rows: list[dict[str, object]] = []
    for engine_id in sorted({str(row.get("engine_id") or "") for row in candidate_rows}):
        engine_candidates = [row for row in candidate_rows if row.get("engine_id") == engine_id]
        reason_counter = Counter()
        mismatch_counter = Counter()
        same_gate_mismatch_count = 0
        missing_b1_gate_coverage: set[str] = set()
        for row in engine_candidates:
            reason = str(row.get("blocking_reason_primary") or "")
            if reason:
                reason_counter[reason] += 1
            mismatch_status = str(row.get("semantic_mismatch_status") or "")
            mismatch_counter[mismatch_status] += 1
            if mismatch_status == "B1_B2_SAME_GATE_MISMATCH":
                same_gate_mismatch_count += 1
            if mismatch_status.startswith("B1_MISSING_"):
                missing_b1_gate_coverage.add(str(row.get("first_blocking_gate") or ""))
        replay_rows = [
            item
            for candidate in engine_candidates
            for item in matrix_by_candidate.get(str(candidate.get("candidate_id") or ""), [])
        ]
        dominant_gate = _most_common_string(
            [str(item.get("first_blocking_gate") or "") for item in replay_rows]
        )
        rows.append(
            {
                "engine_id": engine_id,
                "candidates_exported_by_b1": len(engine_candidates),
                "candidates_rejected_by_b2": sum(
                    1
                    for row in engine_candidates
                    if row.get("semantic_classification")
                    in {"ENGINE_NATIVE_NO_TRADE", "HARD_BLOCKED_CANDIDATE"}
                ),
                "engine_native_no_trade_count": sum(
                    1
                    for row in engine_candidates
                    if row.get("semantic_classification") == "ENGINE_NATIVE_NO_TRADE"
                ),
                "trade_eligible_count": sum(
                    1
                    for row in engine_candidates
                    if row.get("semantic_classification") == "TRADE_ELIGIBLE_CANDIDATE"
                ),
                "hard_blocked_candidate_count": sum(
                    1
                    for row in engine_candidates
                    if row.get("semantic_classification") == "HARD_BLOCKED_CANDIDATE"
                ),
                "dominant_blocking_gate": dominant_gate,
                "top_b2_rejection_reasons": [
                    {"reason_code": code, "count": count}
                    for code, count in reason_counter.most_common(5)
                ],
                "same_gate_mismatch_count": same_gate_mismatch_count,
                "expected_b1_gate_coverage": _EXPECTED_B1_GATE_COVERAGE.get(engine_id, ()),
                "missing_b1_gate_coverage": tuple(
                    gate for gate in sorted(missing_b1_gate_coverage) if gate
                ),
                "semantic_mismatch_status_counts": dict(sorted(mismatch_counter.items())),
                "counterfactual_survival_count": sum(
                    1
                    for row in engine_candidates
                    if int(row.get("counterfactual_survival_count") or 0) > 0
                ),
                "counterfactual_survival_pct": round(
                    sum(
                        1
                        for row in engine_candidates
                        if int(row.get("counterfactual_survival_count") or 0) > 0
                    )
                    / max(len(engine_candidates), 1),
                    6,
                ),
            }
        )
    payload = {
        "schema_version": "v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "CANDIDATE_VS_ENGINE_DECISION_MATRIX_READY",
        "candidate_count": len(candidate_rows),
        "rows": rows,
    }
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return payload


def _candidate_threshold_audit(
    candidate_rows: list[dict[str, object]],
    *,
    source_candidates: tuple[StrategyLadderCandidateEvent, ...],
) -> dict[str, object]:
    source_by_engine = Counter(item.engine_id for item in source_candidates)
    low_score_export_count = sum(
        1 for row in candidate_rows if row.get("candidate_quality_bucket") == "QUALITY_ZERO_OR_NEGATIVE"
    )
    rows: list[dict[str, object]] = []
    for definition in _THRESHOLD_AUDIT_DEFS:
        engine_id = str(definition["engine_id"])
        gate_id = str(definition["gate_id"])
        threshold_key = str(definition["threshold_key"])
        engine_candidates = (
            candidate_rows
            if engine_id == "all"
            else [row for row in candidate_rows if row.get("engine_id") == engine_id]
        )
        exported_count = (
            len(source_candidates)
            if engine_id == "all"
            else int(source_by_engine.get(engine_id, 0))
        )
        rejected_same_gate_count = (
            sum(1 for row in engine_candidates if row.get("first_blocking_gate") == gate_id)
            if gate_id
            else 0
        )
        if threshold_key == "b1_score_threshold":
            alignment_status = "THRESHOLD_TOO_LOOSE_FOR_B2" if low_score_export_count > 0 else "THRESHOLD_MISMATCH_B1_B2"
        elif gate_id and rejected_same_gate_count > 0:
            alignment_status = "THRESHOLD_TOO_LOOSE_FOR_B2"
        else:
            alignment_status = "THRESHOLD_MISMATCH_B1_B2"
        rows.append(
            {
                **definition,
                "threshold_alignment_status": alignment_status,
                "candidates_exported_by_b1": exported_count,
                "candidates_later_rejected_by_same_gate_in_b2": rejected_same_gate_count,
                "candidate_count_with_threshold_family": len(engine_candidates),
                "low_quality_candidates_exported": (
                    low_score_export_count if threshold_key == "b1_score_threshold" else 0
                ),
                "threshold_applied_in_b1": False,
            }
        )
    payload = {
        "schema_version": "v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "CANDIDATE_THRESHOLD_AUDIT_READY",
        "candidate_count": len(candidate_rows),
        "rows": rows,
    }
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return payload


def _top_recommendations(
    candidate_rows: list[dict[str, object]],
    *,
    threshold_audit_payload: dict[str, object],
) -> list[dict[str, object]]:
    recommendations: list[dict[str, object]] = []
    mismatch_counter = Counter(
        str(row.get("semantic_mismatch_status") or "") for row in candidate_rows
    )
    class_counter = Counter(
        str(row.get("semantic_classification") or "") for row in candidate_rows
    )
    total = max(len(candidate_rows), 1)
    proxy_ratio = class_counter.get("ENGINE_NATIVE_NO_TRADE", 0) / total
    if proxy_ratio >= 0.5:
        recommendations.append(
            {
                "recommendation_id": "KEEP_B1_BROAD_BUT_RENAME_OUTPUTS_AS_PRE_CANDIDATES",
                "rationale": (
                    "Most exported B1 rows become native no-trade outcomes, which means "
                    "the current B1 semantic is discovery/proxy, not trade-eligible."
                ),
            }
        )
    if any(status.startswith("B1_MISSING_DIRECTION_GATE") for status in mismatch_counter):
        recommendations.append(
            {
                "recommendation_id": "MOVE_DIRECTION_GATE_EARLIER_INTO_B1",
                "rationale": (
                    "Direction-based native rejections are material and cheap enough to "
                    "surface earlier if B1 is ever renamed from discovery to trade intent."
                ),
            }
        )
    if any(status.startswith("B1_MISSING_FRAGILITY_GATE") for status in mismatch_counter):
        recommendations.append(
            {
                "recommendation_id": "MOVE_FRAGILITY_GATE_EARLIER_INTO_B1",
                "rationale": (
                    "Engine C fragility is dominating after native recheck; if the rail "
                    "wants fewer weak expansions, propagate that signal before B2."
                ),
            }
        )
    if mismatch_counter.get("B1_PRE_CANDIDATE_EXPECTED_ENGINE_RECHECK", 0) > 0:
        recommendations.append(
            {
                "recommendation_id": "SEPARATE_DISCOVERY_CANDIDATES_FROM_TRADE_CANDIDATES",
                "rationale": (
                    "The current output contract mixes research discovery with trade intent. "
                    "Separate the names and counts to avoid misreading B1 as executable."
                ),
            }
        )
    low_quality_rows = sum(
        1
        for row in candidate_rows
        if row.get("candidate_quality_bucket") == "QUALITY_ZERO_OR_NEGATIVE"
    )
    if low_quality_rows > 0:
        recommendations.append(
            {
                "recommendation_id": "ADD_CALIBRATED_CANDIDATE_QUALITY_SCORE",
                "rationale": (
                    "B1 still exports zero/negative-strength rows. A calibrated quality "
                    "score would make pre-candidate triage legible without changing gates."
                ),
            }
        )
    if any(
        str(row.get("threshold_alignment_status") or "") == "THRESHOLD_TOO_LOOSE_FOR_B2"
        for row in threshold_audit_payload.get("rows", ())
    ):
        recommendations.append(
            {
                "recommendation_id": "REQUIRE_ENGINE_NATIVE_PRESELECTION_BEFORE_B2_EXPANSION",
                "rationale": (
                    "The threshold audit shows that broad B1 export is still looser than "
                    "native engine semantics. Preselection would reduce waste if speed becomes critical."
                ),
            }
        )
    return recommendations


def _build_main_payload(
    *,
    candidate_rows: list[dict[str, object]],
    matrix_rows: list[dict[str, object]],
    threshold_audit_payload: dict[str, object],
    gate_waterfall_payload: dict[str, object],
    run_manifest: StrategyLadderRunManifest | None,
    summary: StrategyLadderReportSummary | None,
) -> dict[str, object]:
    semantic_counter = Counter(
        str(row.get("semantic_classification") or "") for row in candidate_rows
    )
    mismatch_counter = Counter(
        str(row.get("semantic_mismatch_status") or "") for row in candidate_rows
    )
    dominant_gate = _most_common_string(
        [str(row.get("first_blocking_gate") or "") for row in candidate_rows]
    )
    timeframe_rows = []
    for timeframe in sorted({str(row.get("timeframe") or "") for row in candidate_rows}):
        scoped_candidates = [row for row in candidate_rows if row.get("timeframe") == timeframe]
        scoped_matrix = [row for row in matrix_rows if str(row.get("timeframe") or "") == timeframe]
        replay_count = len(scoped_matrix)
        timeframe_rows.append(
            {
                "timeframe": timeframe,
                "candidate_count": len(scoped_candidates),
                "quality_score_distribution": {
                    bucket: sum(
                        1
                        for row in scoped_candidates
                        if row.get("candidate_quality_bucket") == bucket
                    )
                    for bucket in sorted(
                        {
                            str(row.get("candidate_quality_bucket") or "")
                            for row in scoped_candidates
                        }
                    )
                },
                "no_trade_rate": round(
                    sum(
                        1
                        for row in scoped_candidates
                        if row.get("semantic_classification") == "ENGINE_NATIVE_NO_TRADE"
                    )
                    / max(len(scoped_candidates), 1),
                    6,
                ),
                "non_long_direction_rate": round(
                    sum(
                        1
                        for row in scoped_matrix
                        if str(row.get("first_blocking_gate") or "") == "direction_layer"
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "fragility_rejection_rate": round(
                    sum(
                        1
                        for row in scoped_matrix
                        if str(row.get("first_blocking_gate") or "") == "fragility_layer"
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "expected_edge_proxy_rejection_rate": round(
                    sum(
                        1
                        for row in scoped_matrix
                        if "EXPECTED_EDGE_PROXY_BLOCKED"
                        in tuple(str(code) for code in row.get("blocking_reason_codes", ()))
                    )
                    / max(replay_count, 1),
                    6,
                ),
                "would_survive_counterfactual_count": sum(
                    1
                    for row in scoped_matrix
                    if any(bool(row.get(flag)) for flag in _COUNTERFACTUAL_FLAGS)
                ),
            }
        )
    recommendations = _top_recommendations(
        candidate_rows,
        threshold_audit_payload=threshold_audit_payload,
    )
    canonical_selected_count = int(
        gate_waterfall_payload.get("canonical_selected_count")
        or gate_waterfall_payload.get("selected_count")
        or 0
    )
    canonical_executed_count = int(
        gate_waterfall_payload.get("canonical_executed_count")
        or (run_manifest.executed_trade_count if run_manifest is not None else 0)
        or 0
    )
    payload = {
        "schema_version": "v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "CANDIDATE_TRADE_SEMANTICS_AUDIT_READY",
        "run_id": (run_manifest.run_id if run_manifest is not None else ""),
        "workflow_run_id": (
            run_manifest.workflow_run_id if run_manifest is not None else ""
        ),
        "phase_run_id": (run_manifest.phase_run_id if run_manifest is not None else ""),
        "final_status": (
            summary.final_status
            if summary is not None
            else (
                run_manifest.final_status
                if run_manifest is not None
                else ""
            )
        ),
        "canonical_selected_count": canonical_selected_count,
        "canonical_executed_count": canonical_executed_count,
        "candidate_count": len(candidate_rows),
        "replay_record_count": len(matrix_rows),
        "dominant_blocking_gate": dominant_gate,
        "candidate_semantic_class_counts": dict(sorted(semantic_counter.items())),
        "semantic_mismatch_status_counts": dict(sorted(mismatch_counter.items())),
        "timeframe_rows": timeframe_rows,
        "recommendations": recommendations,
        "rows": candidate_rows,
    }
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return payload


def _build_markdown(
    main_payload: dict[str, object],
    engine_matrix_payload: dict[str, object],
    threshold_audit_payload: dict[str, object],
) -> str:
    lines = [
        "# Candidate-to-Trade Semantics Audit",
        "",
        "Diagnostic labels: "
        + ", ".join(str(label) for label in main_payload.get("diagnostic_labels", ())),
        "",
        "## Canonical truth",
        f"- final_status: {main_payload.get('final_status', '')}",
        f"- canonical_selected_count: {main_payload.get('canonical_selected_count', 0)}",
        f"- canonical_executed_count: {main_payload.get('canonical_executed_count', 0)}",
        f"- candidate_count: {main_payload.get('candidate_count', 0)}",
        f"- replay_record_count: {main_payload.get('replay_record_count', 0)}",
        f"- dominant_blocking_gate: {main_payload.get('dominant_blocking_gate', '')}",
        "",
        "## Semantics",
    ]
    for key, value in dict(main_payload.get("candidate_semantic_class_counts", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Mismatches"])
    for key, value in dict(main_payload.get("semantic_mismatch_status_counts", {})).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Engines"])
    for row in engine_matrix_payload.get("rows", ()):
        lines.append(
            f"- {row.get('engine_id')}: exported_b1={row.get('candidates_exported_by_b1', 0)}, "
            f"native_no_trade={row.get('engine_native_no_trade_count', 0)}, "
            f"hard_blocked={row.get('hard_blocked_candidate_count', 0)}, "
            f"dominant_gate={row.get('dominant_blocking_gate', '')}, "
            f"missing_b1_gate_coverage={','.join(row.get('missing_b1_gate_coverage', ()))}"
        )
    lines.extend(["", "## Threshold audit"])
    for row in threshold_audit_payload.get("rows", ()):
        lines.append(
            f"- {row.get('threshold_key')}: source_status={row.get('threshold_source_status')}, "
            f"alignment={row.get('threshold_alignment_status')}, "
            f"rejected_same_gate={row.get('candidates_later_rejected_by_same_gate_in_b2', 0)}"
        )
    lines.extend(["", "## Recommendations"])
    for row in main_payload.get("recommendations", ()):
        lines.append(
            f"- {row.get('recommendation_id')}: {row.get('rationale', '')}"
        )
    return "\n".join(lines) + "\n"


def write_strategy_ladder_candidate_trade_semantics_audit(
    *,
    run_dir: Path,
    summary: StrategyLadderReportSummary | None = None,
    run_manifest: StrategyLadderRunManifest | None = None,
    source_candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
    materialized_candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
    gate_counterfactual_matrix_path: Path | None = None,
) -> StrategyLadderCandidateTradeSemanticsAuditBuildResult:
    run_dir = run_dir.resolve()
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    resolved_summary = summary or _load_report_summary(run_dir)
    resolved_run_manifest = run_manifest or _load_run_manifest(run_dir)
    gate_matrix_payload, resolved_gate_matrix_path = _load_gate_counterfactual_matrix(
        run_dir,
        summary=resolved_summary,
        run_manifest=resolved_run_manifest,
        gate_counterfactual_matrix_path=gate_counterfactual_matrix_path,
    )
    gate_waterfall_payload = _read_json(
        run_dir / "reports" / GATE_WATERFALL_ANALYSIS_FILENAME
    )
    matrix_rows = [
        dict(row) for row in gate_matrix_payload.get("rows", ()) if isinstance(row, dict)
    ]
    resolved_source_events = source_candidate_events
    if not resolved_source_events:
        source_path = _resolve_b1_candidate_path(run_dir, resolved_run_manifest)
        resolved_source_events = (
            _read_candidate_events(source_path) if source_path is not None else ()
        )
    resolved_materialized_events = materialized_candidate_events
    if not resolved_materialized_events:
        resolved_materialized_events = _read_candidate_events(
            run_dir / "fast_candidates" / "candidate_events.jsonl"
        )
    candidate_rows = _build_candidate_rows(
        source_candidates=resolved_source_events,
        materialized_candidates=resolved_materialized_events,
        matrix_rows=matrix_rows,
    )
    quality_distribution_payload = _candidate_quality_distribution(
        candidate_rows,
        matrix_rows,
    )
    engine_matrix_payload = _candidate_vs_engine_matrix(candidate_rows, matrix_rows)
    threshold_audit_payload = _candidate_threshold_audit(
        candidate_rows,
        source_candidates=resolved_source_events,
    )
    main_payload = _build_main_payload(
        candidate_rows=candidate_rows,
        matrix_rows=matrix_rows,
        threshold_audit_payload=threshold_audit_payload,
        gate_waterfall_payload=gate_waterfall_payload,
        run_manifest=resolved_run_manifest,
        summary=resolved_summary,
    )
    markdown = _build_markdown(
        main_payload,
        engine_matrix_payload,
        threshold_audit_payload,
    )
    audit_path = reports_dir / CANDIDATE_TRADE_SEMANTICS_AUDIT_FILENAME
    audit_md_path = reports_dir / CANDIDATE_TRADE_SEMANTICS_AUDIT_MARKDOWN_FILENAME
    quality_path = reports_dir / CANDIDATE_QUALITY_DISTRIBUTION_FILENAME
    engine_path = reports_dir / CANDIDATE_VS_ENGINE_DECISION_MATRIX_FILENAME
    threshold_path = reports_dir / CANDIDATE_THRESHOLD_AUDIT_FILENAME
    atomic_write_json(audit_path, main_payload)
    atomic_write_text(audit_md_path, markdown)
    atomic_write_json(quality_path, quality_distribution_payload)
    atomic_write_json(engine_path, engine_matrix_payload)
    atomic_write_json(threshold_path, threshold_audit_payload)
    mismatch_counter = Counter(
        str(row.get("semantic_mismatch_status") or "") for row in candidate_rows
    )
    return StrategyLadderCandidateTradeSemanticsAuditBuildResult(
        status="CANDIDATE_TRADE_SEMANTICS_AUDIT_READY",
        candidate_trade_semantics_audit_path=str(audit_path.resolve()),
        candidate_quality_distribution_path=str(quality_path.resolve()),
        candidate_vs_engine_decision_matrix_path=str(engine_path.resolve()),
        candidate_threshold_audit_path=str(threshold_path.resolve()),
        canonical_selected_count=int(main_payload.get("canonical_selected_count") or 0),
        canonical_executed_count=int(main_payload.get("canonical_executed_count") or 0),
        candidate_count=len(candidate_rows),
        engine_native_no_trade_count=sum(
            1
            for row in candidate_rows
            if row.get("semantic_classification") == "ENGINE_NATIVE_NO_TRADE"
        ),
        hard_blocked_candidate_count=sum(
            1
            for row in candidate_rows
            if row.get("semantic_classification") == "HARD_BLOCKED_CANDIDATE"
        ),
        dominant_semantic_mismatch_status=(
            mismatch_counter.most_common(1)[0][0] if mismatch_counter else ""
        ),
        recommendation_count=len(main_payload.get("recommendations", ())),
    )


__all__ = [
    "CANDIDATE_QUALITY_DISTRIBUTION_FILENAME",
    "CANDIDATE_THRESHOLD_AUDIT_FILENAME",
    "CANDIDATE_TRADE_SEMANTICS_AUDIT_FILENAME",
    "CANDIDATE_TRADE_SEMANTICS_AUDIT_MARKDOWN_FILENAME",
    "CANDIDATE_VS_ENGINE_DECISION_MATRIX_FILENAME",
    "StrategyLadderCandidateTradeSemanticsAuditBuildResult",
    "write_strategy_ladder_candidate_trade_semantics_audit",
]
