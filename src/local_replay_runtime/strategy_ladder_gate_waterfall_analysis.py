"""Diagnostic-only gate waterfall and counterfactual analysis for Strategy Ladder B2."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    LABEL_STORE_DATASET_FILENAME,
    LABEL_STORE_QUALITY_REPORT_FILENAME,
    LABEL_STORE_SUMMARY_FILENAME,
    StrategyLadderB2LabelStoreBuilderRequest,
    StrategyLadderB2LabelStoreQualityReport,
    StrategyLadderB2LabelStoreRow,
    StrategyLadderB2LabelStoreSummary,
    build_strategy_ladder_b2_label_store,
)
from local_replay_runtime.strategy_ladder_detailed_replay import (
    load_strategy_ladder_detailed_replay_artifact,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderReportSummary,
    StrategyLadderRunManifest,
    deterministic_payload_hash,
)


GATE_WATERFALL_ANALYSIS_FILENAME = "gate_waterfall_analysis.json"
GATE_WATERFALL_ANALYSIS_MARKDOWN_FILENAME = "gate_waterfall_analysis.md"
GATE_COUNTERFACTUAL_MATRIX_FILENAME = "gate_counterfactual_matrix.json"
GATE_COUNTERFACTUAL_BY_ENGINE_FILENAME = "gate_counterfactual_by_engine.json"
GATE_COUNTERFACTUAL_BY_TIMEFRAME_FILENAME = "gate_counterfactual_by_timeframe.json"
EXPECTED_EDGE_READINESS_AUDIT_FILENAME = "expected_edge_readiness_audit.json"
EXPECTED_EDGE_READINESS_AUDIT_MARKDOWN_FILENAME = "expected_edge_readiness_audit.md"

_DIAGNOSTIC_LABELS = (
    "RESEARCH_ONLY_COUNTERFACTUAL",
    "NON_PROMOTION_GRADE",
    "DIAGNOSTIC_ONLY",
)
_NO_BLOCKING_GATE = "NO_BLOCKING_GATE"
_GATE_ORDER = (
    "direction_layer",
    "structure_layer",
    "fragility_layer",
    "microstructure_layer",
    "expected_edge_layer",
    "break_even_layer",
    "fee_aware_edge_layer",
    "spread_slippage_realism_layer",
    "adverse_selection_layer",
    "fill_realism_layer",
    "governance_promotion_layer",
)
_GATE_LABELS = {
    "direction_layer": "Direction",
    "structure_layer": "Structure",
    "fragility_layer": "Fragility",
    "microstructure_layer": "Microstructure",
    "expected_edge_layer": "Expected edge",
    "break_even_layer": "Break-even",
    "fee_aware_edge_layer": "Fee-aware edge",
    "spread_slippage_realism_layer": "Spread/slippage realism",
    "adverse_selection_layer": "Adverse selection",
    "fill_realism_layer": "Fill realism",
    "governance_promotion_layer": "Governance/promotion",
    _NO_BLOCKING_GATE: "No blocking gate",
}
_SCENARIO_ORDER = (
    "expected_edge_governed",
    "break_even_measured",
    "fee_aware_edge_governed",
    "spread_realism_measured",
    "slippage_realism_measured",
    "adverse_selection_partial_allowed",
    "execution_realism_partial",
    "engine_c_fragility_relaxed",
    "engine_d_history_available",
)
_SCENARIO_LABELS = {
    "expected_edge_governed": "Expected edge governed",
    "break_even_measured": "Break-even measured",
    "fee_aware_edge_governed": "Fee-aware edge governed",
    "spread_realism_measured": "Spread realism measured",
    "slippage_realism_measured": "Slippage realism measured",
    "adverse_selection_partial_allowed": "Adverse selection partial allowed",
    "execution_realism_partial": "Execution realism partial",
    "engine_c_fragility_relaxed": "Engine C fragility relaxed",
    "engine_d_history_available": "Engine D history available",
}
_SCENARIO_DESCRIPTIONS = {
    "expected_edge_governed": (
        "Ignore expected-edge proxy/governance blockers and recompute the gate path."
    ),
    "break_even_measured": (
        "Ignore break-even proxy blockers only; true negative break-even evidence would still block."
    ),
    "fee_aware_edge_governed": (
        "Ignore fee-aware-edge proxy blockers only; true negative fee-aware evidence would still block."
    ),
    "spread_realism_measured": "Ignore spread realism blockers only.",
    "slippage_realism_measured": "Ignore slippage realism blockers only.",
    "adverse_selection_partial_allowed": (
        "Ignore adverse-selection blockers as a bounded research-only partial-fidelity counterfactual."
    ),
    "execution_realism_partial": (
        "Ignore spread/slippage/adverse/fill realism blockers together for research-only diagnostics."
    ),
    "engine_c_fragility_relaxed": (
        "Ignore Engine C Build-14 fragility blockers only; all other blockers remain."
    ),
    "engine_d_history_available": (
        "Ignore Engine D closed-episode history blockers only; all other blockers remain."
    ),
}
_SPREAD_READY_STATUSES = frozenset({"SPREAD_MEASURED_FROM_BOOK"})
_SLIPPAGE_READY_STATUSES = frozenset(
    {
        "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
        "SLIPPAGE_MEASURED_FROM_KYLE_LAMBDA",
    }
)
_ADVERSE_READY_STATUSES = frozenset({"ADVERSE_SELECTION_READY"})
_FILL_READY_STATUSES = frozenset(
    {
        "FILL_REALISM_PROVEN",
        "FILL_REALISM_SHADOW_MEASURED",
    }
)
_EXPECTED_EDGE_GOVERNANCE_CODES = frozenset(
    {
        "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
        "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH",
    }
)
_BREAK_EVEN_PROXY_CODES = frozenset({"BREAK_EVEN_PROXY_BLOCKED"})
_FEE_AWARE_PROXY_CODES = frozenset({"FEE_AWARE_EDGE_PROXY_BLOCKED"})
_ENGINE_D_HISTORY_CODES = frozenset(
    {
        "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
        "engine_d.no_trade.history_weak",
        "history_weak",
    }
)
_ENGINE_C_FRAGILITY_PREFIXES = (
    "BUILD14_READER:execution_fragility_score:",
    "BUILD14_READER:false_breakout_model:",
    "BUILD14_READER:micro_edge_exit_governor:",
    "BUILD14_READER:micro_edge_entry_timing_layer:",
)


class StrategyLadderGateWaterfallBuildResult(BaseModel, frozen=True):
    """Resolved diagnostic output refs."""

    status: str = Field(..., min_length=1)
    gate_waterfall_analysis_path: str = Field(..., min_length=1)
    gate_counterfactual_matrix_path: str = Field(..., min_length=1)
    gate_counterfactual_by_engine_path: str = Field(..., min_length=1)
    gate_counterfactual_by_timeframe_path: str = Field(..., min_length=1)
    expected_edge_readiness_audit_path: str = Field(..., min_length=1)
    label_store_summary_path: str = Field(..., min_length=1)
    label_store_quality_report_path: str = Field(..., min_length=1)
    canonical_selected_count: int = Field(default=0, ge=0)
    canonical_executed_count: int = Field(default=0, ge=0)
    best_counterfactual_scenario: str = ""
    best_counterfactual_survival_count: int = Field(default=0, ge=0)
    expected_edge_readiness_verdict: str = Field(..., min_length=1)


@dataclass(frozen=True)
class _Blocker:
    gate_id: str
    reason_code: str
    counterfactual_tags: tuple[str, ...]


@dataclass(frozen=True)
class _ReplayRecord:
    replay_record_id: str
    candidate_id: str
    engine_id: str
    pair: str
    timeframe: str
    capital_bucket: int
    decision_timestamp_ms: int
    execution_state: str
    blocking_reason_codes: tuple[str, ...]
    blockers: tuple[_Blocker, ...]
    label_quality_status: str
    replay_grounded_status: str
    execution_fidelity_status: str


def _read_jsonl_models(path: Path, model_type: type[BaseModel]) -> tuple[BaseModel, ...]:
    if not path.is_file():
        return ()
    rows: list[BaseModel] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(model_type.model_validate_json(line))
    return tuple(rows)


def _read_candidate_events(run_dir: Path) -> dict[str, StrategyLadderCandidateEvent]:
    path = run_dir / "fast_candidates" / "candidate_events.jsonl"
    return {
        item.candidate_id: item
        for item in _read_jsonl_models(path, StrategyLadderCandidateEvent)
        if isinstance(item, StrategyLadderCandidateEvent)
    }


def _read_replay_artifacts(
    run_dir: Path,
) -> tuple[tuple[Path, StrategyLadderDetailedReplayArtifact], ...]:
    replay_root = run_dir / "detailed_replay"
    rows: list[tuple[Path, StrategyLadderDetailedReplayArtifact]] = []
    shared_payload_cache: dict[str, object] = {}
    if replay_root.is_dir():
        for path in sorted(replay_root.glob("*.json")):
            rows.append(
                (
                    path.resolve(),
                    load_strategy_ladder_detailed_replay_artifact(
                        path,
                        shared_payload_cache=shared_payload_cache,
                    ),
                )
            )
    return tuple(rows)


def _ensure_label_store(
    run_dir: Path,
    *,
    summary_path: Path | None = None,
    quality_path: Path | None = None,
) -> tuple[
    StrategyLadderB2LabelStoreSummary,
    StrategyLadderB2LabelStoreQualityReport,
    dict[str, StrategyLadderB2LabelStoreRow],
    Path,
    Path,
]:
    output_dir = run_dir / "ml_label_store"
    resolved_summary_path = summary_path or output_dir / LABEL_STORE_SUMMARY_FILENAME
    resolved_quality_path = quality_path or output_dir / LABEL_STORE_QUALITY_REPORT_FILENAME
    dataset_path = output_dir / LABEL_STORE_DATASET_FILENAME
    if not (resolved_summary_path.is_file() and resolved_quality_path.is_file() and dataset_path.is_file()):
        build_strategy_ladder_b2_label_store(
            StrategyLadderB2LabelStoreBuilderRequest(
                run_root=run_dir,
                output_dir=output_dir,
            )
        )
    summary = StrategyLadderB2LabelStoreSummary.model_validate_json(
        resolved_summary_path.read_text(encoding="utf-8-sig")
    )
    quality = StrategyLadderB2LabelStoreQualityReport.model_validate_json(
        resolved_quality_path.read_text(encoding="utf-8-sig")
    )
    row_index: dict[str, StrategyLadderB2LabelStoreRow] = {}
    for item in _read_jsonl_models(dataset_path, StrategyLadderB2LabelStoreRow):
        if isinstance(item, StrategyLadderB2LabelStoreRow):
            row_index[item.replay_record_id] = item
    return (
        summary,
        quality,
        row_index,
        resolved_summary_path.resolve(),
        resolved_quality_path.resolve(),
    )


def _reason_is_engine_c_fragility(code: str) -> bool:
    return code.startswith(_ENGINE_C_FRAGILITY_PREFIXES)


def _classify_reason_code(
    *,
    engine_id: str,
    reason_code: str,
    engine_c_fragility_present: bool,
) -> _Blocker | None:
    lower = reason_code.lower()
    if (
        not reason_code
        or reason_code == "ENGINE_NATIVE_NO_TRADE"
        or reason_code == "BUILD14_SHADOW_ENABLED_ACTIVE"
        or reason_code.startswith("BUILD14_APPLIED:")
        or reason_code.endswith(".confirmed")
    ):
        return None
    if reason_code in _EXPECTED_EDGE_GOVERNANCE_CODES:
        return _Blocker(
            gate_id="governance_promotion_layer",
            reason_code=reason_code,
            counterfactual_tags=("expected_edge_governed",),
        )
    if reason_code.startswith("EXPECTED_EDGE_"):
        return _Blocker(
            gate_id="expected_edge_layer",
            reason_code=reason_code,
            counterfactual_tags=("expected_edge_governed",),
        )
    if reason_code in _BREAK_EVEN_PROXY_CODES or "break_even_not_cleared" in lower:
        tags = ("break_even_measured",) if reason_code in _BREAK_EVEN_PROXY_CODES else ()
        return _Blocker(
            gate_id="break_even_layer",
            reason_code=reason_code,
            counterfactual_tags=tags,
        )
    if reason_code in _FEE_AWARE_PROXY_CODES or "cost_infeasible" in lower or "no_excess" in lower:
        tags = ("fee_aware_edge_governed",) if reason_code in _FEE_AWARE_PROXY_CODES else ()
        return _Blocker(
            gate_id="fee_aware_edge_layer",
            reason_code=reason_code,
            counterfactual_tags=tags,
        )
    if reason_code in _ENGINE_D_HISTORY_CODES or "closed_episode_journal" in lower:
        return _Blocker(
            gate_id="governance_promotion_layer",
            reason_code=reason_code,
            counterfactual_tags=("engine_d_history_available",),
        )
    if engine_id == "engine_c" and _reason_is_engine_c_fragility(reason_code):
        return _Blocker(
            gate_id="fragility_layer",
            reason_code=reason_code,
            counterfactual_tags=("engine_c_fragility_relaxed",),
        )
    if "microstructure.not_applied" in lower or "missing_from_replay_payload" in lower:
        return _Blocker(
            gate_id="microstructure_layer",
            reason_code=reason_code,
            counterfactual_tags=(),
        )
    if "non_long_direction" in lower or ".direction.non_long" in lower:
        return _Blocker(
            gate_id="direction_layer",
            reason_code=reason_code,
            counterfactual_tags=(),
        )
    if "structure_unfavorable" in lower or "invalid_structure" in lower:
        return _Blocker(
            gate_id="structure_layer",
            reason_code=reason_code,
            counterfactual_tags=(),
        )
    if any(
        token in lower
        for token in (
            "structured_breakout",
            "fresh_breakout",
            "non_long_breakout",
        )
    ):
        if engine_id == "engine_c" and engine_c_fragility_present:
            return None
        return _Blocker(
            gate_id="structure_layer",
            reason_code=reason_code,
            counterfactual_tags=(),
        )
    return None


def _append_unique_blocker(
    blockers: list[_Blocker],
    seen: set[tuple[str, str]],
    blocker: _Blocker | None,
) -> None:
    if blocker is None:
        return
    key = (blocker.gate_id, blocker.reason_code)
    if key in seen:
        return
    blockers.append(blocker)
    seen.add(key)


def _status_blockers(result: StrategyLadderBucketReplayResult) -> tuple[_Blocker, ...]:
    parity = result.parity_payload if isinstance(result.parity_payload, dict) else {}
    spread = dict(parity.get("measured_spread_report") or {})
    slippage = dict(parity.get("measured_slippage_report") or {})
    adverse = dict(parity.get("adverse_selection_report") or {})
    fill = dict(parity.get("fill_realism_report") or {})
    blockers: list[_Blocker] = []
    seen: set[tuple[str, str]] = set()
    spread_status = str(spread.get("status") or "")
    if spread_status and spread_status not in _SPREAD_READY_STATUSES:
        _append_unique_blocker(
            blockers,
            seen,
            _Blocker(
                gate_id="spread_slippage_realism_layer",
                reason_code=spread_status,
                counterfactual_tags=("spread_realism_measured", "execution_realism_partial"),
            ),
        )
    slippage_status = str(slippage.get("status") or "")
    if slippage_status and slippage_status not in _SLIPPAGE_READY_STATUSES:
        _append_unique_blocker(
            blockers,
            seen,
            _Blocker(
                gate_id="spread_slippage_realism_layer",
                reason_code=slippage_status,
                counterfactual_tags=("slippage_realism_measured", "execution_realism_partial"),
            ),
        )
    adverse_status = str(adverse.get("status") or "")
    if adverse_status and adverse_status not in _ADVERSE_READY_STATUSES:
        _append_unique_blocker(
            blockers,
            seen,
            _Blocker(
                gate_id="adverse_selection_layer",
                reason_code=adverse_status,
                counterfactual_tags=(
                    "adverse_selection_partial_allowed",
                    "execution_realism_partial",
                ),
            ),
        )
    fill_status = str(fill.get("status") or result.fill_realism_status or "")
    if fill_status and fill_status not in _FILL_READY_STATUSES:
        _append_unique_blocker(
            blockers,
            seen,
            _Blocker(
                gate_id="fill_realism_layer",
                reason_code=fill_status,
                counterfactual_tags=("execution_realism_partial",),
            ),
        )
    return tuple(blockers)


def _replay_record_id(result: StrategyLadderBucketReplayResult) -> str:
    dtr_record = result.dtr_record if isinstance(result.dtr_record, dict) else {}
    return str(dtr_record.get("dtr_id") or f"{result.candidate_id}:{result.capital_bucket}")


def _build_records(
    *,
    run_dir: Path,
    label_rows: dict[str, StrategyLadderB2LabelStoreRow],
) -> tuple[_ReplayRecord, ...]:
    candidate_index = _read_candidate_events(run_dir)
    replay_artifacts = _read_replay_artifacts(run_dir)
    records: list[_ReplayRecord] = []
    for replay_ref, artifact in replay_artifacts:
        candidate = candidate_index.get(artifact.candidate_id)
        timeframe = candidate.timeframe if candidate is not None and candidate.timeframe else "unknown"
        for result in artifact.bucket_results:
            engine_c_fragility_present = (
                result.engine_id == "engine_c"
                and any(_reason_is_engine_c_fragility(code) for code in result.reason_codes)
            )
            blockers: list[_Blocker] = []
            seen: set[tuple[str, str]] = set()
            for reason_code in result.reason_codes:
                _append_unique_blocker(
                    blockers,
                    seen,
                    _classify_reason_code(
                        engine_id=result.engine_id,
                        reason_code=str(reason_code),
                        engine_c_fragility_present=engine_c_fragility_present,
                    ),
                )
            for blocker in _status_blockers(result):
                _append_unique_blocker(blockers, seen, blocker)
            record_id = _replay_record_id(result)
            label_row = label_rows.get(record_id)
            records.append(
                _ReplayRecord(
                    replay_record_id=record_id,
                    candidate_id=result.candidate_id,
                    engine_id=result.engine_id,
                    pair=result.pair,
                    timeframe=timeframe,
                    capital_bucket=result.capital_bucket,
                    decision_timestamp_ms=result.timestamp_ms,
                    execution_state=str(result.execution_state or ""),
                    blocking_reason_codes=tuple(str(code) for code in result.reason_codes),
                    blockers=tuple(blockers),
                    label_quality_status=(
                        label_row.label_quality_status
                        if label_row is not None
                        else "LABEL_QUALITY_NOT_PROVEN"
                    ),
                    replay_grounded_status=(
                        label_row.replay_grounded_status
                        if label_row is not None
                        else "REPLAY_GROUNDED_NOT_AVAILABLE"
                    ),
                    execution_fidelity_status=(
                        label_row.execution_fidelity_status
                        if label_row is not None
                        else "EXECUTION_FIDELITY_NOT_PROVEN"
                    ),
                )
            )
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.decision_timestamp_ms,
                item.candidate_id,
                item.capital_bucket,
            ),
        )
    )


def _active_blockers(
    record: _ReplayRecord,
    *,
    ignored_tags: frozenset[str],
) -> tuple[_Blocker, ...]:
    if not ignored_tags:
        return record.blockers
    return tuple(
        blocker
        for blocker in record.blockers
        if not ignored_tags.intersection(blocker.counterfactual_tags)
    )


def _blocking_gate_chain(blockers: tuple[_Blocker, ...]) -> tuple[str, ...]:
    gates_present = {blocker.gate_id for blocker in blockers}
    return tuple(gate_id for gate_id in _GATE_ORDER if gate_id in gates_present)


def _first_blocking_gate(blockers: tuple[_Blocker, ...]) -> str:
    chain = _blocking_gate_chain(blockers)
    return chain[0] if chain else _NO_BLOCKING_GATE


def _primary_secondary_reasons(
    blockers: tuple[_Blocker, ...],
) -> tuple[str, str]:
    chain = _blocking_gate_chain(blockers)
    if not chain:
        return ("", "")
    first_gate = chain[0]
    primary_candidates = [item.reason_code for item in blockers if item.gate_id == first_gate]
    primary = primary_candidates[0] if primary_candidates else ""
    if len(primary_candidates) > 1:
        return (primary, primary_candidates[1])
    for gate_id in chain[1:]:
        for item in blockers:
            if item.gate_id == gate_id:
                return (primary, item.reason_code)
    return (primary, "")


def _scenario_ignored_tags(scenario_id: str) -> frozenset[str]:
    if scenario_id not in _SCENARIO_ORDER:
        return frozenset()
    return frozenset({scenario_id})


def _scenario_survives(record: _ReplayRecord, scenario_id: str) -> bool:
    active = _active_blockers(record, ignored_tags=_scenario_ignored_tags(scenario_id))
    return _first_blocking_gate(active) == _NO_BLOCKING_GATE


def _scenario_first_gate(record: _ReplayRecord, scenario_id: str) -> str:
    active = _active_blockers(record, ignored_tags=_scenario_ignored_tags(scenario_id))
    return _first_blocking_gate(active)


def _is_selected_execution_state(state: str) -> bool:
    normalized = (state or "").strip().lower()
    return normalized not in {"", "hard_blocked", "phantom"}


def _best_scenario(records: tuple[_ReplayRecord, ...]) -> tuple[str, int]:
    best_id = ""
    best_count = -1
    for scenario_id in _SCENARIO_ORDER:
        count = sum(1 for record in records if _scenario_survives(record, scenario_id))
        if count > best_count:
            best_id = scenario_id
            best_count = count
    return (best_id, max(best_count, 0))


def _funnel_rows(records: tuple[_ReplayRecord, ...]) -> tuple[dict[str, object], ...]:
    total = len(records)
    previous_remaining = total
    rows: list[dict[str, object]] = []
    gate_index = {
        gate_id: index
        for index, gate_id in enumerate(_GATE_ORDER)
    }
    first_gates = {
        record.replay_record_id: _first_blocking_gate(record.blockers)
        for record in records
    }
    for gate_id in _GATE_ORDER:
        current_index = gate_index[gate_id]
        remaining = sum(
            1
            for record in records
            if (
                first_gates[record.replay_record_id] == _NO_BLOCKING_GATE
                or gate_index.get(first_gates[record.replay_record_id], 10_000) > current_index
            )
        )
        marginal_drop = previous_remaining - remaining
        cumulative_drop = total - remaining
        rows.append(
            {
                "gate_id": gate_id,
                "gate_label": _GATE_LABELS[gate_id],
                "remaining_after_gate_count": remaining,
                "marginal_drop_by_gate": marginal_drop,
                "cumulative_drop_by_gate": cumulative_drop,
                "marginal_drop_pct": 0.0 if total <= 0 else round(marginal_drop / total, 6),
                "cumulative_drop_pct": 0.0 if total <= 0 else round(cumulative_drop / total, 6),
            }
        )
        previous_remaining = remaining
    return tuple(rows)


def _dominant_gate_rows(records: tuple[_ReplayRecord, ...]) -> tuple[dict[str, object], ...]:
    first_gate_counts: Counter[str] = Counter()
    reason_by_gate: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        active = record.blockers
        gate_id = _first_blocking_gate(active)
        if gate_id == _NO_BLOCKING_GATE:
            continue
        first_gate_counts[gate_id] += 1
        primary, secondary = _primary_secondary_reasons(active)
        if primary:
            reason_by_gate[gate_id][primary] += 1
        if secondary:
            reason_by_gate[gate_id][secondary] += 1
    total = len(records)
    rows = []
    for gate_id, count in sorted(
        first_gate_counts.items(),
        key=lambda item: (-item[1], _GATE_ORDER.index(item[0]) if item[0] in _GATE_ORDER else 10_000),
    ):
        dominant_reasons = [
            {"reason_code": reason, "count": reason_count}
            for reason, reason_count in reason_by_gate[gate_id].most_common(5)
        ]
        rows.append(
            {
                "gate_id": gate_id,
                "gate_label": _GATE_LABELS[gate_id],
                "first_blocking_count": count,
                "first_blocking_pct": 0.0 if total <= 0 else round(count / total, 6),
                "dominant_reason_codes": dominant_reasons,
            }
        )
    return tuple(rows)


def _scenario_summaries(
    records: tuple[_ReplayRecord, ...],
    *,
    canonical_selected_count: int,
) -> tuple[dict[str, object], ...]:
    total = len(records)
    rows = []
    for scenario_id in _SCENARIO_ORDER:
        survival_count = sum(1 for record in records if _scenario_survives(record, scenario_id))
        rows.append(
            {
                "scenario_id": scenario_id,
                "scenario_label": _SCENARIO_LABELS[scenario_id],
                "description": _SCENARIO_DESCRIPTIONS[scenario_id],
                "counterfactual_survival_count": survival_count,
                "counterfactual_survival_pct": 0.0 if total <= 0 else round(survival_count / total, 6),
                "canonical_selected_count": canonical_selected_count,
                "delta_vs_canonical_selected": survival_count - canonical_selected_count,
                "diagnostic_labels": _DIAGNOSTIC_LABELS,
            }
        )
    return tuple(rows)


def _record_matrix_rows(records: tuple[_ReplayRecord, ...]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for record in records:
        canonical_blockers = record.blockers
        canonical_chain = _blocking_gate_chain(canonical_blockers)
        primary_reason, secondary_reason = _primary_secondary_reasons(canonical_blockers)
        row = {
            "candidate_id": record.candidate_id,
            "engine_id": record.engine_id,
            "pair": record.pair,
            "timeframe": record.timeframe,
            "capital_bucket": record.capital_bucket,
            "decision_timestamp_ms": record.decision_timestamp_ms,
            "replay_record_id": record.replay_record_id,
            "execution_state": record.execution_state,
            "first_blocking_gate": _first_blocking_gate(canonical_blockers),
            "blocking_gate_chain": canonical_chain,
            "blocking_reason_codes": record.blocking_reason_codes,
            "blocking_reason_primary": primary_reason,
            "blocking_reason_secondary": secondary_reason,
            "label_quality_status": record.label_quality_status,
            "replay_grounded_status": record.replay_grounded_status,
            "execution_fidelity_status": record.execution_fidelity_status,
        }
        for scenario_id in _SCENARIO_ORDER:
            row[f"would_survive_if_{scenario_id}"] = _scenario_survives(record, scenario_id)
            row[f"counterfactual_first_gate_if_{scenario_id}"] = _scenario_first_gate(record, scenario_id)
        rows.append(row)
    return tuple(rows)


def _aggregate_slice(
    *,
    rows: tuple[_ReplayRecord, ...],
) -> dict[str, object]:
    gate_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    for record in rows:
        first_gate = _first_blocking_gate(record.blockers)
        if first_gate != _NO_BLOCKING_GATE:
            gate_counts[first_gate] += 1
        primary_reason, _secondary_reason = _primary_secondary_reasons(record.blockers)
        if primary_reason:
            reason_counts[primary_reason] += 1
    dominant_gate = ""
    if gate_counts:
        dominant_gate = sorted(
            gate_counts.items(),
            key=lambda item: (-item[1], _GATE_ORDER.index(item[0]) if item[0] in _GATE_ORDER else 10_000),
        )[0][0]
    best_scenario_id, best_scenario_count = _best_scenario(rows)
    return {
        "candidate_count": len({record.candidate_id for record in rows}),
        "replay_record_count": len(rows),
        "hard_blocked_count": sum(
            1 for record in rows if not _is_selected_execution_state(record.execution_state)
        ),
        "dominant_blocking_gate": dominant_gate,
        "dominant_gate_label": _GATE_LABELS.get(dominant_gate, "n/a"),
        "dominant_reason_codes": [
            {"reason_code": reason, "count": count}
            for reason, count in reason_counts.most_common(5)
        ],
        "counterfactual_survival_count": best_scenario_count,
        "counterfactual_survival_pct": (
            0.0 if not rows else round(best_scenario_count / len(rows), 6)
        ),
        "best_counterfactual_scenario": best_scenario_id,
        "scenario_survival_counts": {
            scenario_id: sum(1 for record in rows if _scenario_survives(record, scenario_id))
            for scenario_id in _SCENARIO_ORDER
        },
    }


def _by_engine_rows(records: tuple[_ReplayRecord, ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[str, list[_ReplayRecord]] = defaultdict(list)
    for record in records:
        grouped[record.engine_id].append(record)
    rows: list[dict[str, object]] = []
    for engine_id, engine_rows in sorted(grouped.items()):
        row = _aggregate_slice(rows=tuple(engine_rows))
        row.update({"engine_id": engine_id})
        rows.append(row)
    return tuple(rows)


def _by_timeframe_rows(records: tuple[_ReplayRecord, ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[str, list[_ReplayRecord]] = defaultdict(list)
    for record in records:
        grouped[record.timeframe].append(record)
    rows: list[dict[str, object]] = []
    for timeframe, timeframe_rows in sorted(
        grouped.items(),
        key=lambda item: (str(item[0]), len(item[1])),
    ):
        row = _aggregate_slice(rows=tuple(timeframe_rows))
        row.update({"timeframe": timeframe})
        rows.append(row)
    return tuple(rows)


def _expected_edge_readiness_audit(
    *,
    run_dir: Path,
    summary: StrategyLadderReportSummary,
    label_summary: StrategyLadderB2LabelStoreSummary,
    label_quality: StrategyLadderB2LabelStoreQualityReport,
    scenario_rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    scenario_index = {
        str(row.get("scenario_id") or ""): row
        for row in scenario_rows
        if isinstance(row, dict)
    }
    expected_edge_row = scenario_index.get("expected_edge_governed", {})
    expected_edge_delta = int(expected_edge_row.get("delta_vs_canonical_selected") or 0)
    label_richness_status = (
        "LABEL_RICHNESS_NOT_READY"
        if label_summary.row_count <= 0
        else "LABEL_RICHNESS_MINIMUM_READY"
        if (
            label_summary.net_positive_rate is not None
            or label_summary.break_even_clearance_rate is not None
            or label_summary.mfe_available_count > 0
            or label_summary.mae_available_count > 0
        )
        else "LABEL_RICHNESS_PARTIAL"
    )
    replay_grounded_coverage_status = (
        "REPLAY_GROUNDED_COVERAGE_BLOCKED"
        if label_summary.replay_grounded_label_count <= 0
        else "REPLAY_GROUNDED_COVERAGE_ACCEPTABLE"
        if label_summary.replay_backed_label_coverage >= 0.5
        else "REPLAY_GROUNDED_COVERAGE_PARTIAL"
    )
    mfe_mae_status = (
        "MFE_MAE_ACCEPTABLE"
        if label_quality.mfe_mae_availability == "MFE_MAE_AVAILABLE"
        else "MFE_MAE_PROXY_ONLY"
        if "PROXY" in label_quality.mfe_mae_availability
        else "MFE_MAE_NOT_READY"
    )
    anti_leakage_ready = (
        label_quality.no_future_timestamp_violations == 0
        and label_quality.post_decision_replay_only
        and bool(label_summary.dataset_hash and label_summary.feature_hash and label_summary.label_hash)
    )
    anti_leakage_path_status = (
        "ANTI_LEAKAGE_PATH_READY" if anti_leakage_ready else "ANTI_LEAKAGE_PATH_BLOCKED"
    )
    walk_forward_status = (
        "WALK_FORWARD_POSSIBLE"
        if label_summary.row_count > 0
        and label_summary.walk_forward_train_days > 0
        and label_summary.walk_forward_validation_days > 0
        and label_summary.purge_window_minutes > 0
        and label_summary.embargo_window_minutes > 0
        else "WALK_FORWARD_BLOCKED"
    )
    execution_realism_status = (
        "EXECUTION_REALISM_PARTIAL"
        if (
            label_summary.proxy_execution_label_count > 0
            or any(
                status != "EXECUTION_FIDELITY_READY"
                for status in label_quality.execution_fidelity_status_counts
            )
        )
        else "EXECUTION_REALISM_READY"
    )
    counterfactual_uplift_status = (
        "EXPECTED_EDGE_COUNTERFACTUAL_UPLIFT_PRESENT"
        if expected_edge_delta > 0
        else "EXPECTED_EDGE_COUNTERFACTUAL_UPLIFT_NOT_PROVEN"
    )
    if (
        label_summary.row_count <= 0
        or anti_leakage_path_status != "ANTI_LEAKAGE_PATH_READY"
        or walk_forward_status != "WALK_FORWARD_POSSIBLE"
        or expected_edge_delta <= 0
    ):
        verdict = "EXPECTED_EDGE_TRAINING_PREMATURE"
    elif (
        replay_grounded_coverage_status != "REPLAY_GROUNDED_COVERAGE_ACCEPTABLE"
        or mfe_mae_status != "MFE_MAE_ACCEPTABLE"
        or execution_realism_status != "EXECUTION_REALISM_READY"
        or label_summary.promotion_state != "LABEL_STORE_PROMOTION_GRADE_CANDIDATE"
    ):
        verdict = "EXPECTED_EDGE_TRAINING_RESEARCH_ONLY_ALLOWED"
    else:
        verdict = "EXPECTED_EDGE_TRAINING_READY_FOR_FIRST_FROZEN_ARTIFACT"
    key_findings = [
        f"label_source_type={label_summary.label_source_type}",
        f"replay_grounded_label_count={label_summary.replay_grounded_label_count}",
        f"proxy_execution_label_count={label_summary.proxy_execution_label_count}",
        f"mfe_mae_availability={label_quality.mfe_mae_availability}",
        f"expected_edge_counterfactual_delta={expected_edge_delta}",
        f"execution_realism_status={execution_realism_status}",
    ]
    payload = {
        "schema_version": "strategy_ladder.expected_edge_readiness_audit.v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "EXPECTED_EDGE_READINESS_AUDIT_READY",
        "run_id": summary.run_id,
        "workflow_run_id": summary.workflow_run_id,
        "phase_run_id": summary.phase_run_id,
        "final_status": summary.final_status,
        "verdict": verdict,
        "label_richness_status": label_richness_status,
        "replay_grounded_coverage_status": replay_grounded_coverage_status,
        "mfe_mae_status": mfe_mae_status,
        "anti_leakage_path_status": anti_leakage_path_status,
        "walk_forward_status": walk_forward_status,
        "execution_realism_status": execution_realism_status,
        "counterfactual_uplift_status": counterfactual_uplift_status,
        "scientifically_valid_now": verdict
        == "EXPECTED_EDGE_TRAINING_READY_FOR_FIRST_FROZEN_ARTIFACT",
        "label_store_summary_ref": str((run_dir / "ml_label_store" / LABEL_STORE_SUMMARY_FILENAME).resolve()),
        "label_store_quality_report_ref": str(
            (run_dir / "ml_label_store" / LABEL_STORE_QUALITY_REPORT_FILENAME).resolve()
        ),
        "label_store_summary": {
            "status": label_summary.status,
            "promotion_state": label_summary.promotion_state,
            "row_count": label_summary.row_count,
            "replay_grounded_label_count": label_summary.replay_grounded_label_count,
            "proxy_execution_label_count": label_summary.proxy_execution_label_count,
            "replay_backed_label_coverage": label_summary.replay_backed_label_coverage,
            "walk_forward_train_days": label_summary.walk_forward_train_days,
            "walk_forward_validation_days": label_summary.walk_forward_validation_days,
            "purge_window_minutes": label_summary.purge_window_minutes,
            "embargo_window_minutes": label_summary.embargo_window_minutes,
        },
        "quality": {
            "no_future_timestamp_violations": label_quality.no_future_timestamp_violations,
            "post_decision_replay_only": label_quality.post_decision_replay_only,
            "no_fabricated_trades": label_quality.no_fabricated_trades,
            "no_fabricated_costs": label_quality.no_fabricated_costs,
            "mfe_mae_availability": label_quality.mfe_mae_availability,
            "execution_fidelity_status_counts": label_quality.execution_fidelity_status_counts,
        },
        "expected_edge_counterfactual": dict(expected_edge_row),
        "key_findings": tuple(key_findings),
    }
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return payload


def _format_gate_waterfall_markdown(payload: dict[str, object]) -> str:
    funnel_rows = tuple(payload.get("funnel_metrics") or ())
    scenario_rows = tuple(payload.get("scenario_summaries") or ())
    dominant_gates = tuple(payload.get("dominant_blocking_gates") or ())
    best_scenario = dict(payload.get("best_counterfactual_scenario") or {})
    lines = [
        "# Gate Waterfall Analysis",
        "",
        f"- run_id: {payload.get('run_id')}",
        f"- final_status: {payload.get('final_status')}",
        f"- diagnostic_labels: {', '.join(payload.get('diagnostic_labels') or ())}",
        f"- canonical_selected_count: {payload.get('canonical_selected_count')}",
        f"- canonical_executed_count: {payload.get('canonical_executed_count')}",
        (
            f"- best_counterfactual: {best_scenario.get('scenario_id')} "
            f"({best_scenario.get('counterfactual_survival_count')})"
        ),
        "",
        "## Gate Funnel",
    ]
    for row in funnel_rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('gate_id')}: remaining={row.get('remaining_after_gate_count')}, "
            f"marginal_drop={row.get('marginal_drop_by_gate')}, "
            f"cumulative_drop={row.get('cumulative_drop_by_gate')}"
        )
    lines.extend(["", "## Dominant Blocking Gates"])
    for row in dominant_gates:
        if not isinstance(row, dict):
            continue
        reasons = ", ".join(
            f"{item.get('reason_code')}({item.get('count')})"
            for item in (row.get("dominant_reason_codes") or ())
            if isinstance(item, dict)
        )
        lines.append(
            f"- {row.get('gate_id')}: count={row.get('first_blocking_count')} / reasons={reasons or 'none'}"
        )
    lines.extend(["", "## Counterfactual Survival"])
    for row in scenario_rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('scenario_id')}: survival={row.get('counterfactual_survival_count')} "
            f"/ delta={row.get('delta_vs_canonical_selected')}"
        )
    return "\n".join(lines) + "\n"


def _format_expected_edge_readiness_markdown(payload: dict[str, object]) -> str:
    findings = tuple(payload.get("key_findings") or ())
    lines = [
        "# Expected-Edge Readiness Audit",
        "",
        f"- run_id: {payload.get('run_id')}",
        f"- verdict: {payload.get('verdict')}",
        f"- label_richness_status: {payload.get('label_richness_status')}",
        f"- replay_grounded_coverage_status: {payload.get('replay_grounded_coverage_status')}",
        f"- mfe_mae_status: {payload.get('mfe_mae_status')}",
        f"- anti_leakage_path_status: {payload.get('anti_leakage_path_status')}",
        f"- walk_forward_status: {payload.get('walk_forward_status')}",
        f"- execution_realism_status: {payload.get('execution_realism_status')}",
        f"- counterfactual_uplift_status: {payload.get('counterfactual_uplift_status')}",
        "",
        "## Key Findings",
    ]
    lines.extend(f"- {item}" for item in findings)
    return "\n".join(lines) + "\n"


def write_strategy_ladder_gate_waterfall_reports(
    *,
    run_dir: Path,
    summary: StrategyLadderReportSummary,
    run_manifest: StrategyLadderRunManifest,
    label_store_summary_path: Path | None = None,
    label_store_quality_report_path: Path | None = None,
) -> StrategyLadderGateWaterfallBuildResult:
    """Write diagnostic-only gate waterfall and readiness artifacts for one B2 run."""

    (
        label_summary,
        label_quality,
        label_rows,
        resolved_label_summary_path,
        resolved_label_quality_path,
    ) = _ensure_label_store(
        run_dir,
        summary_path=label_store_summary_path,
        quality_path=label_store_quality_report_path,
    )
    records = _build_records(run_dir=run_dir, label_rows=label_rows)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    canonical_selected_count = sum(
        1 for record in records if _is_selected_execution_state(record.execution_state)
    )
    canonical_executed_count = int(run_manifest.executed_trade_count or 0)
    scenario_rows = _scenario_summaries(
        records,
        canonical_selected_count=canonical_selected_count,
    )
    best_scenario_id, best_scenario_count = _best_scenario(records)
    best_scenario_payload = next(
        (
            dict(row)
            for row in scenario_rows
            if str(row.get("scenario_id") or "") == best_scenario_id
        ),
        {
            "scenario_id": best_scenario_id,
            "counterfactual_survival_count": best_scenario_count,
            "delta_vs_canonical_selected": best_scenario_count - canonical_selected_count,
        },
    )
    matrix_rows = _record_matrix_rows(records)
    by_engine_rows = _by_engine_rows(records)
    by_timeframe_rows = _by_timeframe_rows(records)
    gate_waterfall_payload = {
        "schema_version": "strategy_ladder.gate_waterfall_analysis.v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "GATE_WATERFALL_ANALYSIS_READY",
        "run_id": summary.run_id,
        "workflow_run_id": summary.workflow_run_id,
        "phase_run_id": summary.phase_run_id,
        "final_status": summary.final_status,
        "canonical_candidate_count": summary.candidate_count,
        "canonical_replay_record_count": len(records),
        "canonical_selected_count": canonical_selected_count,
        "canonical_executed_count": canonical_executed_count,
        "best_counterfactual_scenario": best_scenario_payload,
        "dominant_blocking_gates": _dominant_gate_rows(records),
        "funnel_metrics": _funnel_rows(records),
        "scenario_summaries": scenario_rows,
        "label_store_summary_ref": str(resolved_label_summary_path),
        "label_store_quality_report_ref": str(resolved_label_quality_path),
    }
    gate_waterfall_payload["artifact_hash"] = deterministic_payload_hash(gate_waterfall_payload)
    counterfactual_matrix_payload = {
        "schema_version": "strategy_ladder.gate_counterfactual_matrix.v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "GATE_COUNTERFACTUAL_MATRIX_READY",
        "run_id": summary.run_id,
        "row_count": len(matrix_rows),
        "rows": list(matrix_rows),
    }
    counterfactual_matrix_payload["artifact_hash"] = deterministic_payload_hash(
        counterfactual_matrix_payload
    )
    by_engine_payload = {
        "schema_version": "strategy_ladder.gate_counterfactual_by_engine.v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "GATE_COUNTERFACTUAL_BY_ENGINE_READY",
        "run_id": summary.run_id,
        "rows": list(by_engine_rows),
    }
    by_engine_payload["artifact_hash"] = deterministic_payload_hash(by_engine_payload)
    by_timeframe_payload = {
        "schema_version": "strategy_ladder.gate_counterfactual_by_timeframe.v1",
        "diagnostic_labels": _DIAGNOSTIC_LABELS,
        "status": "GATE_COUNTERFACTUAL_BY_TIMEFRAME_READY",
        "run_id": summary.run_id,
        "rows": list(by_timeframe_rows),
    }
    by_timeframe_payload["artifact_hash"] = deterministic_payload_hash(by_timeframe_payload)
    readiness_payload = _expected_edge_readiness_audit(
        run_dir=run_dir,
        summary=summary,
        label_summary=label_summary,
        label_quality=label_quality,
        scenario_rows=scenario_rows,
    )
    gate_waterfall_path = reports_dir / GATE_WATERFALL_ANALYSIS_FILENAME
    gate_waterfall_md_path = reports_dir / GATE_WATERFALL_ANALYSIS_MARKDOWN_FILENAME
    counterfactual_matrix_path = reports_dir / GATE_COUNTERFACTUAL_MATRIX_FILENAME
    by_engine_path = reports_dir / GATE_COUNTERFACTUAL_BY_ENGINE_FILENAME
    by_timeframe_path = reports_dir / GATE_COUNTERFACTUAL_BY_TIMEFRAME_FILENAME
    readiness_path = reports_dir / EXPECTED_EDGE_READINESS_AUDIT_FILENAME
    readiness_md_path = reports_dir / EXPECTED_EDGE_READINESS_AUDIT_MARKDOWN_FILENAME
    atomic_write_json(gate_waterfall_path, gate_waterfall_payload, indent=2)
    atomic_write_text(gate_waterfall_md_path, _format_gate_waterfall_markdown(gate_waterfall_payload))
    atomic_write_json(counterfactual_matrix_path, counterfactual_matrix_payload, indent=2)
    atomic_write_json(by_engine_path, by_engine_payload, indent=2)
    atomic_write_json(by_timeframe_path, by_timeframe_payload, indent=2)
    atomic_write_json(readiness_path, readiness_payload, indent=2)
    atomic_write_text(readiness_md_path, _format_expected_edge_readiness_markdown(readiness_payload))
    return StrategyLadderGateWaterfallBuildResult(
        status="GATE_WATERFALL_ANALYSIS_READY",
        gate_waterfall_analysis_path=str(gate_waterfall_path.resolve()),
        gate_counterfactual_matrix_path=str(counterfactual_matrix_path.resolve()),
        gate_counterfactual_by_engine_path=str(by_engine_path.resolve()),
        gate_counterfactual_by_timeframe_path=str(by_timeframe_path.resolve()),
        expected_edge_readiness_audit_path=str(readiness_path.resolve()),
        label_store_summary_path=str(resolved_label_summary_path),
        label_store_quality_report_path=str(resolved_label_quality_path),
        canonical_selected_count=canonical_selected_count,
        canonical_executed_count=canonical_executed_count,
        best_counterfactual_scenario=best_scenario_id,
        best_counterfactual_survival_count=best_scenario_count,
        expected_edge_readiness_verdict=str(readiness_payload.get("verdict") or ""),
    )


__all__ = [
    "EXPECTED_EDGE_READINESS_AUDIT_FILENAME",
    "GATE_COUNTERFACTUAL_BY_ENGINE_FILENAME",
    "GATE_COUNTERFACTUAL_BY_TIMEFRAME_FILENAME",
    "GATE_COUNTERFACTUAL_MATRIX_FILENAME",
    "GATE_WATERFALL_ANALYSIS_FILENAME",
    "StrategyLadderGateWaterfallBuildResult",
    "write_strategy_ladder_gate_waterfall_reports",
]
