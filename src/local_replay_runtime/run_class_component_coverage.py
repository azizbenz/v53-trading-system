"""Run-class component coverage for Strategy Ladder backtest runs.

This artifact answers a narrow audit question: for the current run class, which
important V5.3 components were used, explicitly out of scope, configured off, or
missing wiring. It does not promote metrics and it does not infer executions.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


class RunClassComponentCoverageEntry(BaseModel, frozen=True):
    """One component classification row for the current run class."""

    component_family: str = Field(..., min_length=1)
    component_path: str = Field(..., min_length=1)
    component_id: str = Field(..., min_length=1)
    expected_for_run_class: bool = False
    status: str = Field(..., min_length=1)
    invoked: bool = False
    consumed_by: tuple[str, ...] = ()
    proof_artifact: str = ""
    reason_codes: tuple[str, ...] = ()


class RunClassComponentCoverage(BaseModel, frozen=True):
    """Typed coverage matrix for module presence vs run-class consumption."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = ""
    run_class: str = "RUN_CLASS_NOT_PROVEN"
    run_class_id: str = "RUN_CLASS_NOT_PROVEN"
    output_root: str = ""
    ml_mode: str = "ML_MODE_OFF"
    component_status_counts: dict[str, int] = Field(default_factory=dict)
    components: tuple[RunClassComponentCoverageEntry, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None

    def by_component_id(self) -> dict[str, RunClassComponentCoverageEntry]:
        return {entry.component_id: entry for entry in self.components}


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_dicts(path: Path, *, limit: int = 10_000) -> tuple[dict[str, object], ...]:
    if not path.is_file():
        return ()
    rows: list[dict[str, object]] = []
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
                if len(rows) >= limit:
                    break
    except OSError:
        return ()
    return tuple(rows)


def _str_field(payload: dict[str, object], key: str, default: str = "") -> str:
    value = payload.get(key)
    return str(value) if isinstance(value, str) and value else default


def _int_field(payload: dict[str, object], key: str, default: int = 0) -> int:
    value = payload.get(key)
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(value, 0)
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _list_field(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if isinstance(value, list):
        return tuple(str(item) for item in value if str(item))
    if isinstance(value, tuple):
        return tuple(str(item) for item in value if str(item))
    return ()


def _candidate_reason_codes(rows: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    codes: list[str] = []
    for row in rows:
        for raw in row.get("preliminary_reason_codes") or ():
            code = str(raw)
            if code:
                codes.append(code)
        payload = row.get("compatibility_payload")
        compat = payload if isinstance(payload, dict) else {}
        for field in (
            "hard_block_reasons",
            "engine_native_reason_codes",
            "engine_native_no_trade_reasons",
            "economic_measurement_warnings",
        ):
            raw_values = compat.get(field) or ()
            if isinstance(raw_values, str):
                raw_values = tuple(part for part in raw_values.split("|") if part)
            for raw in raw_values:
                code = str(raw)
                if code:
                    codes.append(code)
    return tuple(codes)


def _candidate_engines(rows: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(row.get("engine_id") or "").strip()
                for row in rows
                if str(row.get("engine_id") or "").strip()
            }
        )
    )


def _build14_snapshot_statuses(
    rows: tuple[dict[str, object], ...],
) -> dict[str, tuple[str, ...]]:
    statuses_by_reader: dict[str, list[str]] = {}
    for row in rows:
        payload = row.get("compatibility_payload")
        compat = payload if isinstance(payload, dict) else {}
        report = compat.get("build14_shadow_report")
        if not isinstance(report, dict):
            continue
        snapshots = report.get("snapshots")
        if not isinstance(snapshots, list):
            continue
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            reader_name = str(snapshot.get("reader_name") or "").strip()
            status = str(snapshot.get("status") or "").strip()
            if reader_name and status:
                statuses_by_reader.setdefault(reader_name, []).append(status)
    return {
        reader_name: tuple(dict.fromkeys(statuses))
        for reader_name, statuses in statuses_by_reader.items()
    }


def _resolve_run_root(output_root: Path, run_id: str) -> Path | None:
    if run_id:
        candidate = output_root / "backtest_strategy_ladder" / run_id
        if candidate.exists():
            return candidate
    roots = [
        path.parent
        for path in output_root.rglob("run_manifest.json")
        if path.is_file() and path.parent.parent.name == "backtest_strategy_ladder"
    ]
    if not roots:
        return None
    roots.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0.0, reverse=True)
    return roots[0]


def _classify_run_class(
    *,
    data_factory_payload: dict[str, object],
    first_run_payload: dict[str, object],
    run_manifest_payload: dict[str, object],
    proof_payload: dict[str, object],
) -> tuple[str, str]:
    candidate_native_count = max(
        _int_field(run_manifest_payload, "candidate_engine_native_count"),
        _int_field(proof_payload, "candidate_engine_native_count"),
    )
    candidate_count = max(
        _int_field(run_manifest_payload, "candidate_count"),
        _int_field(proof_payload, "candidate_count"),
    )
    detailed_count = max(
        _int_field(run_manifest_payload, "detailed_replay_count"),
        _int_field(proof_payload, "detailed_replay_count"),
    )
    engine_native_status = _str_field(
        run_manifest_payload,
        "engine_native_status",
        _str_field(proof_payload, "engine_native_status"),
    )
    if candidate_native_count > 0 or engine_native_status in {
        "ENGINE_NATIVE_FULL_PATH_READY",
        "ENGINE_NATIVE_MATERIALIZING",
    }:
        return "ENGINE_NATIVE_DECISION_REPLAY", "CLASS_C_ENGINE_NATIVE_DECISION_REPLAY"
    if candidate_count > 0 or detailed_count > 0:
        return (
            "STRATEGY_LADDER_RESEARCH_REPLAY",
            "CLASS_B_STRATEGY_LADDER_RESEARCH_REPLAY",
        )
    if data_factory_payload or first_run_payload:
        return "DATA_FACTORY_ONLY", "CLASS_A_DATA_FACTORY_ONLY"
    return "RUN_CLASS_NOT_PROVEN", "RUN_CLASS_NOT_PROVEN"


def _component(
    *,
    family: str,
    path: str,
    component_id: str,
    expected: bool,
    status: str,
    invoked: bool = False,
    consumed_by: tuple[str, ...] = (),
    proof_artifact: str = "",
    reason_codes: tuple[str, ...] = (),
) -> RunClassComponentCoverageEntry:
    normalized_reason_codes = (reason_codes,) if isinstance(reason_codes, str) else reason_codes
    return RunClassComponentCoverageEntry(
        component_family=family,
        component_path=path,
        component_id=component_id,
        expected_for_run_class=expected,
        status=status,
        invoked=invoked,
        consumed_by=tuple(dict.fromkeys(item for item in consumed_by if item)),
        proof_artifact=proof_artifact,
        reason_codes=tuple(dict.fromkeys(code for code in normalized_reason_codes if code)),
    )


def _status_counts(
    components: tuple[RunClassComponentCoverageEntry, ...],
) -> dict[str, int]:
    return dict(sorted(Counter(entry.status for entry in components).items()))


def _has_ready_status(payload: dict[str, object], key: str, ready_token: str) -> bool:
    return _str_field(payload, key) == ready_token


def build_run_class_component_coverage(
    *,
    output_root: Path,
    run_id: str = "",
    ml_mode: str = "ML_MODE_OFF",
) -> RunClassComponentCoverage:
    """Build a run-class component coverage matrix from existing run artifacts."""

    output_root = output_root.resolve()
    data_factory_payload = _read_json(output_root / "data_factory_manifest.json")
    first_run_payload = _read_json(output_root / "first_run_manifest.json")
    proof_payload = _read_json(output_root / "backtest_proof_matrix.json")
    run_root = _resolve_run_root(output_root, run_id)
    run_manifest_payload = _read_json(run_root / "run_manifest.json") if run_root else {}
    ladder_payload = (
        _read_json(run_root / "reports" / "strategy_ladder_summary.json")
        if run_root
        else {}
    )
    candidate_rows = (
        _read_jsonl_dicts(run_root / "fast_candidates" / "candidate_events.jsonl")
        if run_root
        else ()
    )
    reason_codes = _candidate_reason_codes(candidate_rows)
    reason_set = set(reason_codes)
    engines = _candidate_engines(candidate_rows)
    effective_run_id = (
        run_id
        or _str_field(run_manifest_payload, "run_id")
        or _str_field(first_run_payload, "run_id")
        or _str_field(data_factory_payload, "run_id")
    )
    effective_ml_mode = (
        ml_mode
        or _str_field(run_manifest_payload, "ml_mode_status")
        or _str_field(first_run_payload, "ml_mode_status")
        or "ML_MODE_OFF"
    )
    run_class, run_class_id = _classify_run_class(
        data_factory_payload=data_factory_payload,
        first_run_payload=first_run_payload,
        run_manifest_payload=run_manifest_payload,
        proof_payload=proof_payload,
    )
    candidate_native_count = max(
        _int_field(run_manifest_payload, "candidate_engine_native_count"),
        _int_field(proof_payload, "candidate_engine_native_count"),
    )
    engine_records = max(
        _int_field(run_manifest_payload, "engine_native_records_built"),
        _int_field(proof_payload, "engine_native_records_built"),
    )
    executed_count = max(
        _int_field(run_manifest_payload, "executed_trade_count"),
        _int_field(proof_payload, "executed_count"),
    )
    reduced_count = _int_field(proof_payload, "reduced_count")
    metadata_ready = (
        _str_field(proof_payload, "fee_provenance_status")
        == "CONFIGURED_FEE_PROVENANCE_READY"
        or _str_field(data_factory_payload, "historical_metadata_status")
        == "BYBIT_HISTORICAL_METADATA_READY"
    )
    expected_edge_governed_count = max(
        _int_field(run_manifest_payload, "expected_edge_governed_count"),
        _int_field(proof_payload, "expected_edge_governed_count"),
    )
    expected_edge_status = _str_field(
        run_manifest_payload,
        "expected_edge_truth_status",
        _str_field(proof_payload, "expected_edge_truth_status"),
    )
    expected_edge_model_status = _str_field(
        run_manifest_payload,
        "expected_edge_model_status",
        _str_field(ladder_payload, "expected_edge_model_status"),
    )
    replay_impact_status = _str_field(
        proof_payload, "replay_impact_source_status", "IMPACT_SOURCE_NOT_PROVEN"
    )
    replay_cost_status = _str_field(
        proof_payload,
        "replay_cost_parity_status",
        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
    )
    feature_groups = set(_list_field(_read_json(output_root / "gold_feature_manifest.json"), "feature_groups_declared"))
    build14_snapshot_statuses = _build14_snapshot_statuses(candidate_rows)
    build14_expected = any(engine in {"engine_c", "engine_d"} for engine in engines)
    normalized_engines = {str(engine).strip().lower() for engine in engines if str(engine).strip()}
    expected_edge_proxy_blocked = expected_edge_status in {
        "EXPECTED_EDGE_PROXY_BLOCKED",
        "EXPECTED_EDGE_MODEL_BLOCKED",
        "EXPECTED_EDGE_MIXED_PROXY_BLOCKED",
    }
    fee_gate_proxy_blocked = (
        expected_edge_proxy_blocked
        or "expected_edge_proxy_blocked" in reason_set
        or "fee_aware_edge_proxy_blocked" in reason_set
    )
    break_even_proxy_blocked = (
        expected_edge_proxy_blocked
        or "expected_edge_proxy_blocked" in reason_set
        or "break_even_proxy_blocked" in reason_set
    )
    engine_d_history_required = (
        "engine_d" in normalized_engines
        and (
            "history_weak" in reason_set
            or "engine_d.no_trade.history_weak" in reason_set
            or "engine_d_history_blocked_by_missing_closed_episode_journal"
            in reason_set
        )
    )
    ml_component_status = (
        "USED"
        if effective_ml_mode == "ML_MODE_OVERLAY_FROZEN"
        and expected_edge_model_status == "GOVERNED_EDGE_MODEL_READY"
        else "CONFIGURED_OFF"
        if effective_ml_mode == "ML_MODE_OFF"
        else "MISSING_WIRING"
    )
    microstructure_status = "USED" if engine_records > 0 else "MISSING_WIRING"
    scoring_trace_status = (
        "USED"
        if any(code.startswith("ENGINE_NATIVE_DECISION:") for code in reason_codes)
        else "MISSING_WIRING"
    )
    hard_block_status = "USED" if reason_codes else "MISSING_WIRING"
    closed_episode_status = (
        "REQUIRED_FOR_ENGINE_D_HISTORY_BUT_NO_EPISODE_SOURCE"
        if engine_d_history_required
        else "NOT_APPLICABLE_NO_EXECUTED_TRADES"
        if executed_count == 0 and reduced_count == 0
        else (
            "REQUIRED_FOR_ENGINE_D_HISTORY_BUT_NO_EPISODE_SOURCE"
            if engine_d_history_required
            else "EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS"
        )
    )
    components = (
        _component(
            family="data_factory",
            path="src/local_replay_runtime/strategy_ladder_data_factory.py",
            component_id="local_replay_runtime.strategy_ladder_data_factory",
            expected=True,
            status=(
                "USED"
                if _has_ready_status(data_factory_payload, "data_factory_status", "DATA_FACTORY_READY")
                else "MISSING_WIRING"
            ),
            invoked=bool(data_factory_payload),
            consumed_by=("strategy_ladder_runner",),
            proof_artifact="data_factory_manifest.json",
            reason_codes=("DATA_FACTORY_READY" if data_factory_payload else "DATA_FACTORY_NOT_PROVEN",),
        ),
        _component(
            family="microstructure",
            path="src/data_backbone/microstructure",
            component_id="data_backbone.microstructure",
            expected=run_class_id in {
                "CLASS_B_STRATEGY_LADDER_RESEARCH_REPLAY",
                "CLASS_C_ENGINE_NATIVE_DECISION_REPLAY",
            },
            status=microstructure_status,
            invoked=engine_records > 0,
            consumed_by=engines,
            proof_artifact="run_manifest.json",
            reason_codes=(f"engine_native_records_built={engine_records}",),
        ),
        _component(
            family="calibration",
            path="src/calibration_methods/psr.py",
            component_id="calibration_methods.psr",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            proof_artifact="run_class_component_coverage.json",
            reason_codes=("engine_native_replay_not_calibration_run",),
        ),
        _component(
            family="calibration",
            path="src/calibration_methods/energy_distance.py",
            component_id="calibration_methods.energy_distance",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            proof_artifact="run_class_component_coverage.json",
            reason_codes=("shadow_transfer_calibration_not_requested",),
        ),
        _component(
            family="calibration",
            path="src/calibration_methods/hansen_spa.py",
            component_id="calibration_methods.hansen_spa",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            proof_artifact="run_class_component_coverage.json",
            reason_codes=("sample_survival_calibration_not_requested",),
        ),
        _component(
            family="calibration",
            path="src/calibration_methods/walkforward.py",
            component_id="calibration_methods.walkforward",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            proof_artifact="run_class_component_coverage.json",
            reason_codes=("walkforward_not_requested_for_this_run",),
        ),
        _component(
            family="complete_enablers",
            path="src/complete_enablers/ml_confidence_enabler.py",
            component_id="complete_enablers.ml_confidence",
            expected=effective_ml_mode == "ML_MODE_OVERLAY_FROZEN",
            status=ml_component_status,
            invoked=ml_component_status == "USED",
            consumed_by=("expected_edge_model_provider",) if ml_component_status == "USED" else (),
            proof_artifact="run_manifest.json",
            reason_codes=(expected_edge_model_status or effective_ml_mode,),
        ),
        _component(
            family="complete_enablers",
            path="src/complete_enablers/market_toxicity_snapshot.py",
            component_id="complete_enablers.market_toxicity",
            expected=build14_expected,
            status=(
                "USED"
                if "market_toxicity_snapshot" in build14_snapshot_statuses
                else "MISSING_WIRING"
                if build14_expected
                else "CONFIGURED_OFF"
            ),
            invoked="market_toxicity_snapshot" in build14_snapshot_statuses,
            consumed_by=tuple(
                sorted(engine for engine in engines if engine in {"engine_c", "engine_d"})
            ),
            proof_artifact="candidate_events.jsonl",
            reason_codes=(
                build14_snapshot_statuses.get("market_toxicity_snapshot")
                or ("build14_shadow_report_missing",)
            ),
        ),
        _component(
            family="complete_enablers",
            path="src/complete_enablers/lob_deep_filter_vwa.py",
            component_id="complete_enablers.lob_deep_filter",
            expected=build14_expected,
            status=(
                "USED"
                if "lob_deep_filter_vwa" in build14_snapshot_statuses
                else "MISSING_WIRING"
                if build14_expected
                else "CONFIGURED_OFF"
            ),
            invoked="lob_deep_filter_vwa" in build14_snapshot_statuses,
            consumed_by=tuple(
                sorted(engine for engine in engines if engine in {"engine_c", "engine_d"})
            ),
            proof_artifact="candidate_events.jsonl",
            reason_codes=(
                build14_snapshot_statuses.get("lob_deep_filter_vwa")
                or ("build14_shadow_report_missing",)
            ),
        ),
        _component(
            family="complete_enablers",
            path="src/complete_enablers/execution_fragility_score.py",
            component_id="complete_enablers.execution_fragility",
            expected=build14_expected,
            status=(
                "USED"
                if "execution_fragility_score" in build14_snapshot_statuses
                else "MISSING_WIRING"
                if build14_expected
                else "CONFIGURED_OFF"
            ),
            invoked="execution_fragility_score" in build14_snapshot_statuses,
            consumed_by=tuple(
                sorted(engine for engine in engines if engine in {"engine_c", "engine_d"})
            ),
            proof_artifact="candidate_events.jsonl",
            reason_codes=(
                build14_snapshot_statuses.get("execution_fragility_score")
                or ("build14_shadow_report_missing",)
            ),
        ),
        _component(
            family="backtest_artifact_import",
            path="src/backtest_artifact_import",
            component_id="backtest_artifact_import.export_dir_bridge",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=("artifact_transport_not_candidate_decision_logic",),
        ),
        _component(
            family="dag_validator",
            path="src/dag_validator",
            component_id="dag_validator.artifact_graph",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=("artifact_dag_validation_not_requested",),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/execution_cost_meter",
            component_id="execution_backbone.execution_cost_meter",
            expected=True,
            status="USED" if metadata_ready else "MISSING_WIRING",
            invoked=metadata_ready,
            consumed_by=engines,
            proof_artifact="backtest_proof_matrix.json",
            reason_codes=(f"fee_provenance_status={_str_field(proof_payload, 'fee_provenance_status', 'NOT_PROVEN')}",),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/fee_aware_edge_gate.py",
            component_id="execution_backbone.fee_aware_edge_gate",
            expected=True,
            status=(
                "USED"
                if expected_edge_governed_count > 0
                or any("cost_infeasible" in code for code in reason_codes)
                else "BLOCKED_BY_EXPECTED_EDGE_PROXY"
                if fee_gate_proxy_blocked
                else "MISSING_WIRING"
            ),
            invoked=expected_edge_governed_count > 0,
            consumed_by=engines,
            proof_artifact="run_manifest.json",
            reason_codes=(
                *(("FEE_AWARE_EDGE_PROXY_BLOCKED",) if fee_gate_proxy_blocked else ()),
                expected_edge_status or "EXPECTED_EDGE_TRUTH_NOT_PROVEN",
            ),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/spread_guard.py",
            component_id="execution_backbone.spread_guard",
            expected=True,
            status="USED" if metadata_ready or replay_cost_status != "REPLAY_LIVE_COST_PARITY_NOT_PROVEN" else "MISSING_WIRING",
            invoked=metadata_ready,
            consumed_by=engines,
            proof_artifact="backtest_proof_matrix.json",
            reason_codes=(replay_cost_status,),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/slippage_model.py",
            component_id="execution_backbone.slippage_model",
            expected=True,
            status="USED" if replay_impact_status != "IMPACT_SOURCE_NOT_PROVEN" else "MISSING_WIRING",
            invoked=replay_impact_status != "IMPACT_SOURCE_NOT_PROVEN",
            consumed_by=engines,
            proof_artifact="backtest_proof_matrix.json",
            reason_codes=(replay_impact_status,),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/venue_constraints_provider.py",
            component_id="execution_backbone.venue_constraints_provider",
            expected=True,
            status="USED" if metadata_ready else "MISSING_WIRING",
            invoked=metadata_ready,
            consumed_by=engines,
            proof_artifact="data_quality_report.json",
            reason_codes=("BYBIT_HISTORICAL_METADATA_READY" if metadata_ready else "BYBIT_HISTORICAL_METADATA_NOT_PROVEN",),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/order_decider",
            component_id="execution_backbone.order_decider",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=(f"run_class={run_class}", "full_system_replay_required_before_order_decider_proof"),
        ),
        _component(
            family="execution_backbone",
            path="src/execution_backbone/reconciliation_layer",
            component_id="execution_backbone.reconciliation_layer",
            expected=False,
            status="SHADOW_LIVE_ONLY",
            reason_codes=("historical_replay_does_not_reconcile_live_exchange_state",),
        ),
        _component(
            family="venue_adapters",
            path="src/venue_adapters/binance_spot",
            component_id="venue_adapters.binance_spot.live_submission",
            expected=False,
            status="SHADOW_LIVE_ONLY",
            reason_codes=("bybit_historical_replay_must_not_submit_binance_orders",),
        ),
        _component(
            family="meta_learning",
            path="src/meta_learning",
            component_id="meta_learning.post_trade_review",
            expected=executed_count > 0,
            status=(
                "MISSING_WIRING"
                if executed_count > 0
                else "EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS"
            ),
            reason_codes=(f"executed_trade_count={executed_count}",),
        ),
        _component(
            family="meta_minimal",
            path="src/meta_minimal/refusal_journal",
            component_id="meta_minimal.refusal_journal",
            expected=True,
            status=(
                "USED"
                if run_root is not None and (run_root / "refusal_ledger.jsonl").is_file()
                else "MISSING_WIRING"
            ),
            invoked=run_root is not None and (run_root / "refusal_ledger.jsonl").is_file(),
            proof_artifact="refusal_ledger.jsonl",
            reason_codes=("refusal_ledger_materialized" if run_root is not None and (run_root / "refusal_ledger.jsonl").is_file() else "refusal_ledger_missing",),
        ),
        _component(
            family="monitoring",
            path="src/monitoring",
            component_id="monitoring.dashboard",
            expected=True,
            status="USED" if proof_payload or first_run_payload else "MISSING_WIRING",
            invoked=bool(proof_payload or first_run_payload),
            proof_artifact="backtest_proof_matrix.json",
            reason_codes=("operator_dashboard_artifacts_present" if proof_payload or first_run_payload else "dashboard_artifacts_missing",),
        ),
        _component(
            family="portfolio_minimal",
            path="src/portfolio_minimal",
            component_id="portfolio_minimal.opportunity_selector",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=(f"run_class={run_class}", "portfolio_selection_not_part_of_engine_native_decision_replay"),
        ),
        _component(
            family="protocols",
            path="src/protocols/shadow_runtime.py",
            component_id="protocols.shadow_runtime",
            expected=False,
            status="SHADOW_LIVE_ONLY",
            reason_codes=("shadow_runtime_not_expected_in_bybit_historical_replay",),
        ),
        _component(
            family="protocols",
            path="src/protocols/micro_live_runtime.py",
            component_id="protocols.micro_live_runtime",
            expected=False,
            status="SHADOW_LIVE_ONLY",
            reason_codes=("micro_live_runtime_not_expected_in_bybit_historical_replay",),
        ),
        _component(
            family="protocols",
            path="src/protocols/live_light_runtime.py",
            component_id="protocols.live_light_runtime",
            expected=False,
            status="SHADOW_LIVE_ONLY",
            reason_codes=("live_runtime_not_expected_in_bybit_historical_replay",),
        ),
        _component(
            family="protocols",
            path="src/protocols/closed_episode_journal.py",
            component_id="protocols.closed_episode_journal",
            expected=closed_episode_status == "REQUIRED_FOR_ENGINE_D_HISTORY_BUT_NO_EPISODE_SOURCE",
            status=closed_episode_status,
            proof_artifact="candidate_events.jsonl",
            reason_codes=(
                (
                    "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL"
                    if closed_episode_status
                    == "REQUIRED_FOR_ENGINE_D_HISTORY_BUT_NO_EPISODE_SOURCE"
                    else (
                        "no_executed_or_reduced_episodes_available"
                        if closed_episode_status == "NOT_APPLICABLE_NO_EXECUTED_TRADES"
                        else "no_history_weak_reason_observed"
                    )
                ),
            ),
        ),
        _component(
            family="protocols",
            path="src/protocols/engine_coordination_rules.py",
            component_id="protocols.engine_coordination_rules",
            expected=run_class_id == "CLASS_D_GOVERNED_FULL_SYSTEM_REPLAY",
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=(f"run_class={run_class}",),
        ),
        _component(
            family="risk_backbone",
            path="src/risk_backbone/risk_runtime.py",
            component_id="risk_backbone.risk_runtime",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=(f"run_class={run_class}", "portfolio_risk_runtime_requires_full_system_replay"),
        ),
        _component(
            family="risk_backbone",
            path="src/risk_backbone/drawdown",
            component_id="risk_backbone.true_drawdown",
            expected=executed_count > 0,
            status="MISSING_WIRING" if executed_count > 0 else "NOT_APPLICABLE_NO_EXECUTED_TRADES",
            proof_artifact="backtest_proof_matrix.json",
            reason_codes=(f"true_drawdown_status={_str_field(proof_payload, 'true_drawdown_status', 'NOT_PROVEN')}",),
        ),
        _component(
            family="scoring_backbone",
            path="src/scoring_backbone/forecast_normalizer.py",
            component_id="scoring_backbone.forecast_normalizer",
            expected=True,
            status=scoring_trace_status,
            invoked=scoring_trace_status == "USED",
            consumed_by=engines,
            proof_artifact="candidate_events.jsonl",
            reason_codes=("engine_native_decision_trace_present" if scoring_trace_status == "USED" else "SCORING_DECOMPOSITION_MISSING",),
        ),
        _component(
            family="scoring_backbone",
            path="src/scoring_backbone/break_even_filter.py",
            component_id="scoring_backbone.break_even_filter",
            expected=True,
            status=(
                "USED"
                if expected_edge_governed_count > 0
                else "BLOCKED_BY_EXPECTED_EDGE_PROXY"
                if break_even_proxy_blocked
                else "MISSING_WIRING"
            ),
            invoked=expected_edge_governed_count > 0,
            consumed_by=engines,
            proof_artifact="run_manifest.json",
            reason_codes=(
                *(("BREAK_EVEN_PROXY_BLOCKED",) if break_even_proxy_blocked else ()),
                expected_edge_status or "EXPECTED_EDGE_TRUTH_NOT_PROVEN",
            ),
        ),
        _component(
            family="scoring_backbone",
            path="src/scoring_backbone/hard_block_gate",
            component_id="scoring_backbone.hard_block_gate",
            expected=True,
            status=hard_block_status,
            invoked=hard_block_status == "USED",
            consumed_by=engines,
            proof_artifact="candidate_events.jsonl",
            reason_codes=("hard_block_reason_codes_present" if hard_block_status == "USED" else "hard_block_trace_missing",),
        ),
        _component(
            family="smoke_bootstrap_recovery",
            path="src/smoke_bootstrap_recovery",
            component_id="smoke_bootstrap_recovery",
            expected=False,
            status="EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS",
            reason_codes=("boot_recovery_proof_not_requested_for_backtest_replay",),
        ),
    )
    matrix = RunClassComponentCoverage(
        run_id=effective_run_id,
        run_class=run_class,
        run_class_id=run_class_id,
        output_root=str(output_root),
        ml_mode=effective_ml_mode,
        component_status_counts=_status_counts(components),
        components=components,
        created_at=datetime.now(tz=UTC),
    )
    return matrix.model_copy(
        update={"artifact_hash": deterministic_payload_hash(matrix.model_dump(mode="json"))}
    )


def write_run_class_component_coverage(
    output_root: Path,
    matrix: RunClassComponentCoverage,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "run_class_component_coverage.json"
    atomic_write_json(path, matrix.model_dump(mode="json"), indent=2)
    return path


def emit_run_class_component_coverage(
    *,
    output_root: Path,
    run_id: str = "",
    ml_mode: str = "ML_MODE_OFF",
) -> tuple[RunClassComponentCoverage, Path]:
    matrix = build_run_class_component_coverage(
        output_root=output_root,
        run_id=run_id,
        ml_mode=ml_mode,
    )
    path = write_run_class_component_coverage(output_root, matrix)
    return matrix, path


__all__ = [
    "RunClassComponentCoverage",
    "RunClassComponentCoverageEntry",
    "build_run_class_component_coverage",
    "emit_run_class_component_coverage",
    "write_run_class_component_coverage",
]
