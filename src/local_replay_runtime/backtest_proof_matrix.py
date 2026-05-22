"""Patch 6 backtest proof matrix / metric gap register.

Reads the deterministic Data Factory and First Controlled Run artefacts under
one ``output_root`` and emits a typed proof matrix that strictly separates
real metrics (``READY``) from remaining gaps (``NOT_PROVEN`` / ``PARTIAL`` /
``BLOCKED`` / ``MISSING`` / ``RESEARCH_ONLY`` / ``PLACEHOLDER``).

Core rule (no fake metrics):

    A metric is exploitable only if the source artefact exists, the status is
    ``READY``, the denominator/sample is explicit, blocker_codes are empty for
    that metric, and the value is not a placeholder.

This module never invents values. Missing fees, fills, drawdowns, capital
buckets, etc. remain ``NOT_PROVEN`` with explicit reason codes.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_data_factory_models import (
    finalize_hashed_model,
)


# Allowed per-metric statuses.
_ALLOWED_METRIC_STATUSES: frozenset[str] = frozenset(
    {
        "READY",
        "PARTIAL",
        "NOT_PROVEN",
        "BLOCKED",
        "MISSING",
        "RESEARCH_ONLY",
        "PLACEHOLDER",
    }
)

# Allowed overall statuses.
_OVERALL_STATUSES: frozenset[str] = frozenset(
    {
        "BACKTEST_PROOF_READY",
        "BACKTEST_PROOF_PARTIAL",
        "BACKTEST_PROOF_RESEARCH_ONLY",
        "BACKTEST_PROOF_BLOCKED",
        "BACKTEST_PROOF_NOT_PROVEN",
    }
)
_RESEARCH_ONLY_BLOCKER_CODES: frozenset[str] = frozenset(
    {
        "RAW_SOURCE_TYPE_INFERRED",
        "CURRENT_METADATA_PROXY",
        "SINGLE_PAIR_RESEARCH_ONLY",
    }
)

_MAX_DASHBOARD_ORDERBOOK_PATHS = 10


class MetricProofEntry(BaseModel, frozen=True):
    """One typed metric with its source provenance and gap status."""

    metric_name: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    value: float | int | str | None = None
    denominator: int | None = None
    source_artifact: str = ""
    blocker_codes: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class BacktestProofMatrix(BaseModel, frozen=True):
    """Strict separation of READY metrics vs remaining gaps."""

    schema_version: str = Field(default="v2", min_length=1)
    run_id: str = ""
    pair: str = ""
    pairs: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    ml_mode: str = "ML_MODE_OFF"
    output_root: str = ""

    # Data Factory layer.
    data_factory_status: str = "NOT_PROVEN"
    raw_source_provenance_status: str = "RAW_SOURCE_PROVENANCE_NOT_PROVEN"
    raw_source_typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    silver_index_status: str = "NOT_PROVEN"
    gold_feature_store_status: str = "NOT_PROVEN"
    trade_schema_status: str = "NOT_PROVEN"
    kline_schema_status: str = "NOT_PROVEN"
    orderbook_schema_status: str = "NOT_PROVEN"
    metadata_schema_status: str = "NOT_PROVEN"
    historical_metadata_status: str = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    metadata_source_mode: str = "LOCAL_METADATA_CACHE"
    metadata_cache_path: str = ""
    metadata_pairs_covered: tuple[str, ...] = ()
    missing_metadata_pairs: tuple[str, ...] = ()
    metadata_temporal_status: str = "METADATA_TEMPORAL_NOT_PROVEN"
    metadata_fetched_at_utc: str = ""
    metadata_temporal_drift_days: float | None = None

    # Patch 6 batch 1 — Orderbook snapshot/delta/recon/depth20 separation.
    orderbook_snapshot_status: str = "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    orderbook_delta_status: str = "ORDERBOOK_DELTA_NOT_PROVEN"
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    depth20_proof_status: str = "BOOK_DEPTH_NOT_PROVEN"
    snapshot_entry_count: int = Field(default=0, ge=0)
    delta_entry_count: int = Field(default=0, ge=0)
    snapshot_paths: tuple[str, ...] = ()
    delta_paths: tuple[str, ...] = ()
    sequence_gap_status: str = "BOOK_SEQUENCE_NOT_PROVEN"
    stale_book_status: str = "BOOK_DEPTH_NOT_PROVEN"
    sequence_gap_report_path: str = ""
    gap_count: int = Field(default=0, ge=0)
    gap_files: tuple[str, ...] = ()
    gap_dates: tuple[str, ...] = ()
    first_gap_expected_seq: int | None = None
    first_gap_actual_seq: int | None = None
    first_gap_previous_seq: int | None = None
    first_gap_event_timestamp_ms: int | None = None
    gap_recovery_status: str = "ORDERBOOK_SEQUENCE_NOT_PROVEN"

    pair_inference_status: str = "PAIR_NOT_DETECTED"
    ignored_source_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()

    # Patch 6 batch 1 — Two-stage backtest contract status surfacing.
    phase1_feature_discovery_status: str = "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    phase1_candidate_export_status: str = "PHASE1_CANDIDATE_EXPORT_NOT_PROVEN"
    phase2_raw_window_extraction_status: str = "PHASE2_RAW_WINDOW_EXTRACTION_NOT_PROVEN"
    phase2_detailed_replay_status: str = "PHASE2_DETAILED_REPLAY_NOT_PROVEN"

    # Patch 6 batch 1 — Storage budget + date pruning surfacing.
    storage_budget_status: str = "STORAGE_BUDGET_NOT_PROVEN"
    storage_budget_report_path: str = ""
    date_pruning_status: str = "DATE_PRUNING_NOT_PROVEN"
    silver_index_date_range_status: str = "SILVER_INDEX_DATE_RANGE_NOT_PROVEN"
    raw_scan_budget_status: str = "DRY_RUN_SCOPE_NOT_PROVEN"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    silver_bloat_ratio: float | None = None
    feature_threshold_manifest_path: str = ""

    # First controlled run / backtest layer.
    candidate_export_status: str = "NOT_PROVEN"
    raw_window_extraction_status: str = "NOT_PROVEN"
    depth_replay_status: str = "NOT_PROVEN"
    candidate_truth_status: str = "CANDIDATE_TRUTH_NOT_PROVEN"
    expected_edge_truth_status: str = "EXPECTED_EDGE_TRUTH_NOT_PROVEN"
    engine_native_status: str = "ENGINE_NATIVE_NOT_REQUESTED"
    candidate_count: int = Field(default=0, ge=0)
    candidate_engine_native_count: int = Field(default=0, ge=0)
    candidate_proxy_count: int = Field(default=0, ge=0)
    expected_edge_proxy_count: int = Field(default=0, ge=0)
    expected_edge_governed_count: int = Field(default=0, ge=0)
    engine_native_records_built: int = Field(default=0, ge=0)
    raw_window_count: int = Field(default=0, ge=0)
    detailed_replay_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    reduced_count: int = Field(default=0, ge=0)
    no_fill_count: int = Field(default=0, ge=0)

    # Economic provenance layer (kept strict — no fake values).
    fee_provenance_status: str = "NOT_PROVEN"
    capital_bucket_metadata_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    impact_provenance_status: str = "NOT_PROVEN"
    fill_realism_status: str = "NOT_PROVEN"
    executed_only_economics_status: str = "NOT_PROVEN"
    true_drawdown_status: str = "NOT_PROVEN"
    capital_bucket_status: str = "NOT_PROVEN"
    replay_fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    replay_impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    replay_fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    replay_cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    replay_executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    replay_true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    historical_replay_venue: str = "BYBIT"
    execution_target_venue: str = "BINANCE"
    backtest_class: str = "BYBIT_PROXY_BACKTEST"
    venue_transfer_status: str = "BINANCE_SHADOW_REQUIRED"
    live_trading_eligibility_status: str = "BLOCKED"

    # Promotion layer.
    promotion_artifact_status: str = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    engine_promotion_status: str = "NOT_PROVEN"
    pair_promotion_status: str = "NOT_PROVEN"
    sample_size_survival_status: str = "NOT_PROVEN"

    # Roll-up.
    overall_backtest_proof_status: str = "BACKTEST_PROOF_NOT_PROVEN"
    blocker_codes: tuple[str, ...] = ()
    metric_gaps: tuple[MetricProofEntry, ...] = ()
    ready_metrics: tuple[MetricProofEntry, ...] = ()

    artifact_hash: str | None = None
    created_at: datetime | None = None


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _str_field(payload: dict[str, object], key: str, default: str = "NOT_PROVEN") -> str:
    raw = payload.get(key)
    return str(raw) if isinstance(raw, str) and raw else default


def _list_field(payload: dict[str, object], key: str) -> tuple[str, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        return ()
    return tuple(str(item) for item in raw if str(item).strip())


def _int_field(payload: dict[str, object], key: str, default: int = 0) -> int:
    try:
        return int(payload.get(key) or default)
    except (TypeError, ValueError):
        return default


def _float_field(payload: dict[str, object], key: str) -> float | None:
    try:
        raw = payload.get(key)
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _merged_string_field(
    *payloads: dict[str, object],
    key: str,
    default: str,
) -> str:
    for payload in payloads:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return default


def _merged_list_field(
    *payloads: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    values: list[str] = []
    for payload in payloads:
        raw = payload.get(key)
        if not isinstance(raw, (list, tuple)):
            continue
        values.extend(str(item) for item in raw if str(item).strip())
    return tuple(dict.fromkeys(values))


def _classify_data_metric(source_status: str, *, ready_token: str) -> str:
    """Map a Data Factory status field onto a {READY, PARTIAL, NOT_PROVEN} bucket."""

    if not source_status:
        return "NOT_PROVEN"
    if source_status == ready_token:
        return "READY"
    if (
        "VIOLATION" in source_status
        or source_status.endswith("_FAILED")
        or source_status.endswith("_TOO_BROAD")
        or source_status.endswith("_REQUIRES_BROAD_CONFIRMATION")
    ):
        return "BLOCKED"
    if source_status.endswith("_NOT_PROVEN") or source_status.endswith("_NOT_READY"):
        return "NOT_PROVEN"
    if source_status.endswith("_PARTIAL"):
        return "PARTIAL"
    if source_status.endswith("_INVALID_TIMESTAMP") or source_status.endswith("_SCHEMA_INVALID"):
        return "BLOCKED"
    return "PARTIAL"


def _silver_orderbook_has_depth20(silver_index_payload: dict[str, object]) -> bool:
    entries = silver_index_payload.get("entries")
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        data_type = str(entry.get("data_type") or "")
        if data_type not in {"orderbook", "orderbook_snapshot", "orderbook_delta"}:
            continue
        if str(entry.get("depth_source_status") or "") == "BOOK_DEPTH20_AVAILABLE":
            return True
    return False


def _summarize_orderbook_silver(
    silver_index_payload: dict[str, object],
    *,
    blocker_codes: tuple[str, ...] = (),
    gap_report_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Extract typed snapshot/delta/recon/depth20 surface from the silver index."""

    snapshot_paths: list[str] = []
    delta_paths: list[str] = []
    snapshot_entries = 0
    delta_entries = 0
    any_depth20 = False
    any_sequence_ready = False
    any_sequence_gap = False
    any_sequence_gap_recovered = False
    any_stale = False
    entries = silver_index_payload.get("entries") if isinstance(silver_index_payload, dict) else None
    if not isinstance(entries, list):
        entries = ()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        data_type = str(entry.get("data_type") or "")
        if data_type == "orderbook_snapshot":
            snapshot_entries += int(entry.get("row_count") or 0)
            path = str(entry.get("path") or "")
            if path and Path(path).is_file():
                snapshot_paths.append(path)
        elif data_type == "orderbook_delta":
            delta_entries += int(entry.get("row_count") or 0)
            path = str(entry.get("path") or "")
            if path and Path(path).is_file():
                delta_paths.append(path)
        depth_status = str(entry.get("depth_source_status") or "")
        if depth_status == "BOOK_DEPTH20_AVAILABLE":
            any_depth20 = True
            any_sequence_ready = True
        elif depth_status == "BOOK_DEPTH_STALE":
            any_stale = True
        elif depth_status in {"BOOK_LIMITED_DEPTH_AVAILABLE", "BOOK_TOP_OF_BOOK_ONLY"}:
            any_sequence_ready = True
        elif depth_status == "BOOK_SEQUENCE_GAP":
            any_sequence_gap = True
    gap_status = ""
    gap_count = 0
    if isinstance(gap_report_payload, dict) and gap_report_payload:
        gap_status = str(gap_report_payload.get("gap_status") or "")
        try:
            gap_count = int(gap_report_payload.get("gap_count") or 0)
        except (TypeError, ValueError):
            gap_count = 0
        if gap_status == "ORDERBOOK_SEQUENCE_GAP_RECOVERED":
            any_sequence_gap_recovered = True
        elif gap_status in {
            "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
            "ORDERBOOK_SEQUENCE_GAP",
        }:
            any_sequence_gap = True
            any_stale = True
    snapshot_status = (
        "ORDERBOOK_SNAPSHOT_READY"
        if snapshot_entries > 0
        else "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    )
    delta_status = (
        "ORDERBOOK_DELTA_READY" if delta_entries > 0 else "ORDERBOOK_DELTA_NOT_PROVEN"
    )
    if snapshot_entries > 0 and any_sequence_ready:
        recon_status = "ORDERBOOK_RECONSTRUCTION_READY"
    else:
        recon_status = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    depth20_status = "BOOK_DEPTH20_AVAILABLE" if any_depth20 else "BOOK_DEPTH_NOT_PROVEN"
    if any_sequence_gap:
        sequence_gap_status = "BOOK_SEQUENCE_GAP"
    elif any_sequence_gap_recovered:
        sequence_gap_status = "BOOK_SEQUENCE_GAP_RECOVERED"
    elif any_sequence_ready:
        sequence_gap_status = "BOOK_SEQUENCE_READY"
    else:
        sequence_gap_status = "BOOK_SEQUENCE_NOT_PROVEN"
    stale_book_status = "BOOK_DEPTH_STALE" if any_stale else depth20_status
    if (
        "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN" in blocker_codes
        or "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED" in blocker_codes
        or "ORDERBOOK_SEQUENCE_GAP" in blocker_codes
    ):
        recon_status = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    if "ORDERBOOK_SEQUENCE_GAP_RECOVERED" in blocker_codes:
        sequence_gap_status = "BOOK_SEQUENCE_GAP_RECOVERED"
    if "ORDERBOOK_SEQUENCE_GAP" in blocker_codes or "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED" in blocker_codes:
        sequence_gap_status = "BOOK_SEQUENCE_GAP"
        stale_book_status = "BOOK_DEPTH_STALE"
        depth20_status = "BOOK_DEPTH_NOT_PROVEN"
    if "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN" in blocker_codes and recon_status == "ORDERBOOK_RECONSTRUCTION_READY":
        recon_status = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    return {
        "snapshot_status": snapshot_status,
        "delta_status": delta_status,
        "recon_status": recon_status,
        "depth20_status": depth20_status,
        "snapshot_entry_count": snapshot_entries,
        "delta_entry_count": delta_entries,
        "snapshot_paths": tuple(snapshot_paths[:_MAX_DASHBOARD_ORDERBOOK_PATHS]),
        "delta_paths": tuple(delta_paths[:_MAX_DASHBOARD_ORDERBOOK_PATHS]),
        "sequence_gap_status": sequence_gap_status,
        "stale_book_status": stale_book_status,
        "gap_count": gap_count,
    }


def build_backtest_proof_matrix(
    *,
    output_root: Path,
    run_id: str = "",
    pairs: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    ml_mode: str = "ML_MODE_OFF",
) -> BacktestProofMatrix:
    """Read all manifest artefacts under ``output_root`` and emit a typed matrix.

    The function is read-only with respect to inputs and writes nothing on its
    own — callers persist the result via :func:`write_backtest_proof_matrix`.
    """

    manifest_payload = _read_json(output_root / "data_factory_manifest.json")
    quality_payload = _read_json(output_root / "data_quality_report.json")
    pair_payload = _read_json(output_root / "pair_universe_report.json")
    silver_payload = _read_json(output_root / "silver_index.json")
    gap_report_payload = _read_json(output_root / "orderbook_sequence_gap_report.json")
    first_run_payload = _read_json(output_root / "first_run_manifest.json")
    first_run_summary = _read_json(output_root / "first_run_stage_summary.json")
    first_run_stage_statuses = (
        first_run_summary.get("stage_statuses")
        if isinstance(first_run_summary.get("stage_statuses"), dict)
        else {}
    )
    run_root = (
        output_root / "backtest_strategy_ladder" / run_id
        if run_id
        else None
    )
    ladder_payload: dict[str, object] = {}
    if run_root is not None:
        ladder_payload = _read_json(run_root / "reports" / "strategy_ladder_summary.json")
    if not ladder_payload:
        for ladder_path in sorted(output_root.rglob("strategy_ladder_summary.json")):
            ladder_payload = _read_json(ladder_path)
            if ladder_payload:
                break
    candidate_summary_payload: dict[str, object] = {}
    if run_root is not None:
        candidate_summary_payload = _read_json(
            run_root / "fast_candidates" / "candidate_summary.json"
        )
    if not candidate_summary_payload:
        for candidate_summary_path in sorted(output_root.rglob("candidate_summary.json")):
            candidate_summary_payload = _read_json(candidate_summary_path)
            if candidate_summary_payload:
                break
    run_manifest_payload: dict[str, object] = {}
    if run_root is not None:
        run_manifest_payload = _read_json(run_root / "run_manifest.json")
    if not run_manifest_payload:
        for run_manifest_path in sorted(output_root.rglob("run_manifest.json")):
            run_manifest_payload = _read_json(run_manifest_path)
            if run_manifest_payload:
                break
    engine_matrix_payload = _read_first_row_from_matrix(
        output_root
        / "backtest_strategy_ladder"
        / run_id
        / "reports"
        / "engine_matrix.json"
    ) if run_id else {}
    if not engine_matrix_payload:
        for engine_matrix_path in sorted(output_root.rglob("engine_matrix.json")):
            engine_matrix_payload = _read_first_row_from_matrix(engine_matrix_path)
            if engine_matrix_payload:
                break
    pair_matrix_payload = _read_first_row_from_matrix(
        output_root
        / "backtest_strategy_ladder"
        / run_id
        / "reports"
        / "pair_matrix.json"
    ) if run_id else {}
    if not pair_matrix_payload:
        for pair_matrix_path in sorted(output_root.rglob("pair_matrix.json")):
            pair_matrix_payload = _read_first_row_from_matrix(pair_matrix_path)
            if pair_matrix_payload:
                break
    candidate_count_fallback = 0
    try:
        candidate_count_fallback = int(candidate_summary_payload.get("candidate_count") or 0)
    except (TypeError, ValueError):
        candidate_count_fallback = 0
    for count_payload, key in (
        (ladder_payload, "candidate_count"),
        (run_manifest_payload, "candidate_count"),
        (first_run_summary, "candidate_count"),
    ):
        try:
            candidate_count_fallback = max(
                candidate_count_fallback, int(count_payload.get(key) or 0)
            )
        except (TypeError, ValueError):
            continue
    raw_window_count_fallback = _count_json_artifacts(output_root, "window_manifest.json")
    detailed_replay_candidate_count_fallback = sum(
        1
        for path in output_root.rglob("*.json")
        if path.is_file()
        and path.parent.name == "detailed_replay"
    )
    for count_payload, key in (
        (run_manifest_payload, "raw_window_count"),
        (first_run_summary, "raw_window_count"),
        (first_run_summary, "detailed_replay_count"),
        (ladder_payload, "detailed_replay_count"),
    ):
        try:
            if key == "raw_window_count":
                raw_window_count_fallback = max(
                    raw_window_count_fallback, int(count_payload.get(key) or 0)
                )
            else:
                detailed_replay_candidate_count_fallback = max(
                    detailed_replay_candidate_count_fallback,
                    int(count_payload.get(key) or 0),
                )
        except (TypeError, ValueError):
            continue
    run_manifest_candidate_count = _int_field(run_manifest_payload, "candidate_count")
    if run_manifest_candidate_count > 0:
        candidate_count_fallback = run_manifest_candidate_count
    run_manifest_raw_window_count = _int_field(run_manifest_payload, "raw_window_count")
    if run_manifest_raw_window_count > 0:
        raw_window_count_fallback = run_manifest_raw_window_count
    run_manifest_detailed_replay_count = _int_field(
        run_manifest_payload,
        "detailed_replay_count",
    )
    if run_manifest_detailed_replay_count > 0:
        detailed_replay_candidate_count_fallback = run_manifest_detailed_replay_count

    pre_blocker_codes = tuple(
        dict.fromkeys(
            (
                *_list_field(manifest_payload, "blocker_codes"),
                *_list_field(quality_payload, "blocker_codes"),
                *_list_field(quality_payload, "raw_scan_budget_reason_codes"),
                *_list_field(first_run_payload, "blocker_codes"),
                *_list_field(first_run_summary, "blockers"),
                *_list_field(pair_payload, "blocker_codes"),
            )
        )
    )

    # --- Data factory layer ----------------------------------------------------
    data_factory_status = _classify_data_metric(
        _str_field(manifest_payload, "data_factory_status"),
        ready_token="DATA_FACTORY_READY",
    )
    silver_index_status = _classify_data_metric(
        _str_field(manifest_payload, "silver_index_status"),
        ready_token="SILVER_INDEX_READY",
    )
    gold_feature_store_status = _classify_data_metric(
        _str_field(manifest_payload, "gold_feature_store_status"),
        ready_token="FEATURE_STORE_READY",
    )
    trade_schema_status = _classify_data_metric(
        _str_field(manifest_payload, "trade_schema_status"),
        ready_token="TRADE_SCHEMA_READY",
    )
    kline_schema_status = _classify_data_metric(
        _str_field(manifest_payload, "kline_schema_status"),
        ready_token="KLINE_SCHEMA_READY",
    )
    orderbook_schema_status = _classify_data_metric(
        _str_field(manifest_payload, "orderbook_schema_status"),
        ready_token="ORDERBOOK_SCHEMA_READY",
    )
    metadata_schema_status = _classify_data_metric(
        _str_field(manifest_payload, "metadata_schema_status"),
        ready_token="METADATA_SCHEMA_READY",
    )
    historical_metadata_status = _str_field(
        manifest_payload,
        "historical_metadata_status",
        "BYBIT_HISTORICAL_METADATA_NOT_PROVEN",
    )
    raw_source_provenance_status = _str_field(
        manifest_payload,
        "raw_source_provenance_status",
        "RAW_SOURCE_PROVENANCE_NOT_PROVEN",
    )
    raw_source_typing_status = _str_field(
        manifest_payload,
        "raw_source_typing_status",
        _str_field(
            quality_payload,
            "raw_source_typing_status",
            "RAW_SOURCE_TYPE_NOT_PROVEN",
        ),
    )
    historical_metadata_metric_status = _classify_data_metric(
        historical_metadata_status,
        ready_token="BYBIT_HISTORICAL_METADATA_READY",
    )

    # --- Patch 6 batch 1 — Orderbook snapshot/delta/recon surfacing ------------
    orderbook_summary = _summarize_orderbook_silver(
        silver_payload,
        blocker_codes=pre_blocker_codes,
        gap_report_payload=gap_report_payload,
    )

    # --- Patch 6 batch 1 — date pruning + storage governance from data quality.
    quality_payload = _read_json(output_root / "data_quality_report.json")
    date_pruning_status = _str_field(
        quality_payload, "date_pruning_status", "DATE_PRUNING_NOT_PROVEN"
    )
    silver_index_date_range_status = _str_field(
        quality_payload,
        "silver_index_date_range_status",
        "SILVER_INDEX_DATE_RANGE_NOT_PROVEN",
    )
    raw_scan_budget_status = _str_field(
        quality_payload, "raw_scan_budget_status", "DRY_RUN_SCOPE_NOT_PROVEN"
    )
    silver_storage_status = _str_field(
        quality_payload, "silver_storage_status", "SILVER_STORAGE_NOT_PROVEN"
    )
    metadata_temporal_drift_days = _float_field(
        quality_payload,
        "metadata_temporal_drift_days",
    )
    compression_payload = _read_json(output_root / "compression_report.json")
    silver_bloat_ratio_raw = compression_payload.get("silver_bloat_ratio")
    silver_bloat_ratio = (
        float(silver_bloat_ratio_raw)
        if isinstance(silver_bloat_ratio_raw, (int, float))
        else None
    )
    compression_storage_status = _str_field(
        compression_payload, "silver_storage_status", ""
    )
    if compression_storage_status:
        silver_storage_status = compression_storage_status
    metadata_source_mode = _str_field(
        quality_payload, "metadata_source_mode", "LOCAL_METADATA_CACHE"
    )
    metadata_cache_path = _str_field(quality_payload, "metadata_cache_path", "")
    metadata_pairs_covered = _list_field(quality_payload, "metadata_pairs_covered")
    missing_metadata_pairs = _list_field(quality_payload, "missing_metadata_pairs")
    metadata_temporal_status = _str_field(
        quality_payload,
        "metadata_temporal_status",
        "METADATA_TEMPORAL_NOT_PROVEN",
    )
    metadata_fetched_at_utc = _str_field(
        quality_payload, "metadata_fetched_at_utc", ""
    )
    capital_bucket_metadata_status = _str_field(
        quality_payload,
        "capital_bucket_metadata_status",
        "CAPITAL_BUCKET_NOT_PROVEN",
    )

    # --- Patch 6 batch 1 — Storage budget surfacing -----------------------------
    storage_budget_payload = _read_json(output_root / "storage_budget_report.json")
    storage_budget_status = _str_field(
        storage_budget_payload, "storage_budget_status", "STORAGE_BUDGET_NOT_PROVEN"
    )
    storage_budget_report_path = (
        str((output_root / "storage_budget_report.json").resolve())
        if (output_root / "storage_budget_report.json").is_file()
        else ""
    )
    date_pruning_metric_status = _classify_data_metric(
        date_pruning_status, ready_token="DATE_PRUNING_READY"
    )
    silver_index_date_range_metric_status = _classify_data_metric(
        silver_index_date_range_status,
        ready_token="SILVER_INDEX_DATE_RANGE_CONSISTENT",
    )
    raw_scan_budget_metric_status = _classify_data_metric(
        raw_scan_budget_status, ready_token="DRY_RUN_SCOPE_READY"
    )

    feature_threshold_path = (
        str((output_root / "feature_threshold_manifest.json").resolve())
        if (output_root / "feature_threshold_manifest.json").is_file()
        else ""
    )

    # --- Backtest layer (read-only fan-out) ------------------------------------
    candidate_export_status = "NOT_PROVEN"
    raw_window_extraction_status = "NOT_PROVEN"
    depth_replay_status = "NOT_PROVEN"
    candidate_count = candidate_count_fallback
    raw_window_count = raw_window_count_fallback
    detailed_replay_count = detailed_replay_candidate_count_fallback
    candidate_truth_status = _str_field(
        run_manifest_payload,
        "candidate_truth_status",
        _str_field(
            ladder_payload,
            "candidate_truth_status",
            _str_field(
                first_run_stage_statuses,
                "candidate_truth_status",
                "CANDIDATE_TRUTH_NOT_PROVEN",
            ),
        ),
    )
    expected_edge_truth_status = _str_field(
        run_manifest_payload,
        "expected_edge_truth_status",
        _str_field(
            ladder_payload,
            "expected_edge_truth_status",
            _str_field(
                first_run_stage_statuses,
                "expected_edge_truth_status",
                "EXPECTED_EDGE_TRUTH_NOT_PROVEN",
            ),
        ),
    )
    engine_native_status = _str_field(
        run_manifest_payload,
        "engine_native_status",
        _str_field(
            ladder_payload,
            "engine_native_status",
            _str_field(
                first_run_stage_statuses,
                "engine_native_status",
                "ENGINE_NATIVE_NOT_REQUESTED",
            ),
        ),
    )
    candidate_engine_native_count = max(
        _int_field(run_manifest_payload, "candidate_engine_native_count"),
        _int_field(ladder_payload, "candidate_engine_native_count"),
    )
    candidate_proxy_count = max(
        _int_field(run_manifest_payload, "candidate_proxy_count"),
        _int_field(ladder_payload, "candidate_proxy_count"),
    )
    expected_edge_proxy_count = max(
        _int_field(run_manifest_payload, "expected_edge_proxy_count"),
        _int_field(ladder_payload, "expected_edge_proxy_count"),
    )
    expected_edge_governed_count = max(
        _int_field(run_manifest_payload, "expected_edge_governed_count"),
        _int_field(ladder_payload, "expected_edge_governed_count"),
    )
    engine_native_records_built = max(
        _int_field(run_manifest_payload, "engine_native_records_built"),
        _int_field(ladder_payload, "engine_native_records_built"),
    )
    candidate_count = candidate_count_fallback
    raw_window_count = raw_window_count_fallback
    detailed_replay_count = detailed_replay_candidate_count_fallback
    # Patch 6 batch 1 — Phase 1/Phase 2 status aliases.
    phase1_feature_discovery_status = (
        "PHASE1_FEATURE_DISCOVERY_READY"
        if gold_feature_store_status == "READY"
        else "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    )
    phase1_candidate_export_status = "PHASE1_CANDIDATE_EXPORT_NOT_PROVEN"
    phase2_raw_window_extraction_status = "PHASE2_RAW_WINDOW_EXTRACTION_NOT_PROVEN"
    phase2_detailed_replay_status = "PHASE2_DETAILED_REPLAY_NOT_PROVEN"
    if first_run_payload or ladder_payload or run_manifest_payload or candidate_summary_payload:
        candidate_export_status_raw = _str_field(
            run_manifest_payload,
            "candidate_export_status",
            _str_field(
                first_run_stage_statuses,
                "candidate_export_status",
                _str_field(
                    ladder_payload,
                    "candidate_export_status",
                    _str_field(
                        candidate_summary_payload,
                        "candidate_export_status",
                        "CANDIDATE_EXPORT_NOT_PROVEN",
                    ),
                ),
            ),
        )
        candidate_export_status = _classify_data_metric(
            candidate_export_status_raw,
            ready_token="CANDIDATE_EXPORT_READY",
        )
        if candidate_export_status == "NOT_PROVEN" and candidate_count > 0:
            candidate_export_status = "PARTIAL"
        raw_window_status_raw = _str_field(
            run_manifest_payload,
            "raw_window_extraction_status",
            _str_field(
                first_run_stage_statuses,
                "raw_window_status",
                _str_field(
                    first_run_payload,
                    "raw_window_status",
                    "RAW_WINDOW_NOT_PROVEN",
                ),
            ),
        )
        raw_window_extraction_status = _classify_data_metric(
            raw_window_status_raw,
            ready_token="RAW_WINDOW_READY",
        )
        if raw_window_extraction_status == "NOT_PROVEN" and raw_window_count > 0:
            raw_window_extraction_status = (
                "READY"
                if candidate_count > 0 and raw_window_count >= candidate_count
                else "PARTIAL"
            )
        depth_status_raw = _str_field(
            run_manifest_payload,
            "detailed_replay_status",
            _str_field(
                first_run_stage_statuses,
                "detailed_replay_status",
                _str_field(
                    ladder_payload,
                    "detailed_replay_status",
                    "DETAILED_REPLAY_NOT_PROVEN",
                ),
            ),
        )
        if depth_status_raw == "DETAILED_REPLAY_NOT_PROVEN" and detailed_replay_count > 0:
            depth_status_raw = (
                "DETAILED_REPLAY_READY"
                if candidate_count > 0 and detailed_replay_count >= candidate_count
                else "DETAILED_REPLAY_PARTIAL"
            )
        if depth_status_raw == "DETAILED_REPLAY_READY":
            depth_replay_status = "READY"
        elif depth_status_raw.endswith("_PARTIAL"):
            depth_replay_status = "PARTIAL"
        else:
            depth_replay_status = "NOT_PROVEN"
        # Phase 1/2 surfacing.
        if candidate_export_status == "READY":
            phase1_candidate_export_status = "PHASE1_CANDIDATE_EXPORT_READY"
        elif candidate_export_status == "PARTIAL":
            phase1_candidate_export_status = "PHASE1_CANDIDATE_EXPORT_NOT_PROVEN"
        if raw_window_extraction_status == "READY":
            phase2_raw_window_extraction_status = "PHASE2_RAW_WINDOW_EXTRACTION_READY"
        elif raw_window_extraction_status == "PARTIAL":
            phase2_raw_window_extraction_status = "PHASE2_RAW_WINDOW_EXTRACTION_NOT_PROVEN"
        if depth_replay_status == "READY":
            phase2_detailed_replay_status = "PHASE2_DETAILED_REPLAY_READY"
        elif depth_replay_status == "PARTIAL":
            phase2_detailed_replay_status = "PHASE2_DETAILED_REPLAY_NOT_PROVEN"

    # --- Economic provenance — strict, no fake values --------------------------
    candidate_truth_metric_status = (
        "READY"
        if candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_READY"
        else (
            "PARTIAL"
            if candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_IN_PROGRESS"
            or candidate_engine_native_count > 0
            else "NOT_PROVEN"
        )
    )
    engine_native_metric_status = (
        "READY"
        if engine_native_status == "ENGINE_NATIVE_FULL_PATH_READY"
        else (
            "PARTIAL"
            if engine_native_status == "ENGINE_NATIVE_MATERIALIZING"
            or candidate_engine_native_count > 0
            else "NOT_PROVEN"
        )
    )
    expected_edge_truth_metric_status = (
        "READY"
        if expected_edge_truth_status == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        else ("BLOCKED" if "PROXY" in expected_edge_truth_status else "NOT_PROVEN")
    )

    metadata_ready = historical_metadata_metric_status == "READY"
    fee_provenance_status = (
        "CONFIGURED_FEE_PROVENANCE_READY" if metadata_ready else "NOT_PROVEN"
    )
    if metadata_ready and not _silver_metadata_row_count(silver_payload):
        fee_provenance_status = "NOT_PROVEN"

    impact_provenance_status = "NOT_PROVEN"  # No Kyle's lambda artefact yet.

    fill_realism_status = "NOT_PROVEN"
    if first_run_payload:
        first_run_status = _str_field(
            first_run_payload, "first_run_status", "FIRST_RUN_NOT_PROVEN"
        )
        if first_run_status == "FIRST_RUN_READY" and depth_replay_status == "READY":
            fill_realism_status = "READY"

    executed_only_economics_status = (
        "READY" if fill_realism_status == "READY" else "NOT_PROVEN"
    )
    true_drawdown_status = "NOT_PROVEN"  # Requires equity curve artefact — not present.
    executed_count = 0
    reduced_count = 0
    no_fill_count = 0
    for counts_payload in (pair_matrix_payload, engine_matrix_payload):
        try:
            executed_count = max(
                executed_count, int(counts_payload.get("executed_count") or 0)
            )
            reduced_count = max(
                reduced_count, int(counts_payload.get("reduced_count") or 0)
            )
            no_fill_count = max(
                no_fill_count, int(counts_payload.get("no_fill_count") or 0)
            )
        except (TypeError, ValueError):
            continue
    replay_fee_source_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "fee_source_status",
        "FEE_SOURCE_NOT_PROVEN",
    )
    replay_impact_source_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "impact_source_status",
        "IMPACT_SOURCE_NOT_PROVEN",
    )
    replay_fill_realism_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "fill_realism_status",
        "FILL_REALISM_NOT_PROVEN",
    )
    replay_cost_parity_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "cost_parity_status",
        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
    )
    replay_executed_only_net_return_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "executed_only_net_return_status",
        "EXECUTED_NET_RETURN_NOT_PROVEN",
    )
    replay_true_net_equity_drawdown_status = _str_field(
        pair_matrix_payload or engine_matrix_payload,
        "true_net_equity_drawdown_status",
        "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
    )
    execution_label_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="execution_label_source",
        default="REPLAY_PROXY_EXECUTION",
    )
    fee_model_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="fee_model_source",
        default="REPLAY_PROXY",
    )
    spread_model_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="spread_model_source",
        default="REPLAY_PROXY",
    )
    slippage_model_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="slippage_model_source",
        default="REPLAY_PROXY",
    )
    partial_fill_model_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="partial_fill_model_source",
        default="REPLAY_PROXY",
    )
    adverse_selection_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="adverse_selection_source",
        default="REPLAY_PROXY",
    )
    order_type_selection_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="order_type_selection_source",
        default="REPLAY_PROXY",
    )
    venue_constraints_source = _merged_string_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="venue_constraints_source",
        default="REPLAY_PROXY",
    )
    execution_fidelity_gap_codes = _merged_list_field(
        run_manifest_payload,
        ladder_payload,
        pair_matrix_payload,
        engine_matrix_payload,
        key="execution_fidelity_gap_codes",
    )
    if replay_impact_source_status == "IMPACT_SOURCE_PROVEN":
        impact_provenance_status = "READY"
    fill_realism_status = (
        "READY"
        if replay_fill_realism_status
        in {"FILL_REALISM_SHADOW_MEASURED", "FILL_REALISM_PROVEN"}
        else "NOT_PROVEN"
    )
    executed_only_economics_status = (
        "READY"
        if replay_executed_only_net_return_status
        in {"EXECUTED_NET_RETURN_PROVEN", "EXECUTED_RETURN_PROVEN"}
        and executed_count > 0
        else "NOT_PROVEN"
    )
    true_drawdown_status = (
        "READY"
        if replay_true_net_equity_drawdown_status
        in {"TRUE_NET_EQUITY_DRAWDOWN_PROVEN", "TRUE_NET_EQUITY_DRAWDOWN_READY"}
        else "NOT_PROVEN"
    )
    capital_bucket_status = (
        "READY"
        if (
            metadata_ready
            and _str_field(
                first_run_payload,
                "capital_profile_status",
                "CAPITAL_PROFILE_NOT_PROVEN",
            )
            in {"CAPITAL_PROFILE_READY", "CAPITAL_PROFILE_GENERATION_READY"}
        )
        else "NOT_PROVEN"
    )
    if metadata_ready and capital_bucket_status != "READY":
        capital_bucket_metadata_status = "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN"

    # --- Promotion layer -------------------------------------------------------
    sample_size_survival_status = _classify_data_metric(
        _merged_string_field(
            ladder_payload,
            run_manifest_payload,
            first_run_stage_statuses,
            key="sample_size_survival_status",
            default="SAMPLE_SIZE_NOT_PROVEN",
        ),
        ready_token="SAMPLE_SIZE_READY",
    )

    promotion_artifact_status = _merged_string_field(
        ladder_payload,
        run_manifest_payload,
        first_run_stage_statuses,
        key="promotion_artifact_status",
        default="PROMOTION_ARTIFACTS_NOT_PROVEN",
    )
    if (
        promotion_artifact_status == "PROMOTION_ARTIFACTS_READY"
        and sample_size_survival_status == "READY"
    ):
        engine_promotion_status = "READY"
    elif promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY":
        engine_promotion_status = "BLOCKED"
    elif promotion_artifact_status.endswith("_PARTIAL"):
        engine_promotion_status = "PARTIAL"
    else:
        engine_promotion_status = "NOT_PROVEN"
    pair_promotion_status = engine_promotion_status

    # --- Blocker propagation ---------------------------------------------------
    blocker_codes: list[str] = []
    blocker_codes.extend(_list_field(manifest_payload, "blocker_codes"))
    blocker_codes.extend(_list_field(quality_payload, "blocker_codes"))
    blocker_codes.extend(_list_field(quality_payload, "raw_scan_budget_reason_codes"))
    blocker_codes.extend(_list_field(first_run_payload, "blocker_codes"))
    blocker_codes.extend(_list_field(first_run_summary, "blockers"))
    blocker_codes.extend(_list_field(pair_payload, "blocker_codes"))
    if silver_index_date_range_status == "SILVER_INDEX_DATE_RANGE_VIOLATION":
        blocker_codes.append("SILVER_INDEX_DATE_RANGE_VIOLATION")
    if date_pruning_status in {
        "DATE_PRUNING_FAILED",
        "DATE_PRUNING_FAILED_OUTPUT_OUT_OF_RANGE",
    }:
        blocker_codes.append(date_pruning_status)
    if raw_scan_budget_status in {
        "DRY_RUN_SCOPE_TOO_BROAD",
        "DRY_RUN_REQUIRES_BROAD_CONFIRMATION",
    }:
        blocker_codes.append(raw_scan_budget_status)
    deduped_blockers = tuple(dict.fromkeys(code for code in blocker_codes if code))

    # --- Build typed metric entries -------------------------------------------
    metric_specs: tuple[tuple[str, str, str], ...] = (
        ("data_factory_status", data_factory_status, "data_factory_manifest.json"),
        ("silver_index_status", silver_index_status, "data_factory_manifest.json"),
        ("gold_feature_store_status", gold_feature_store_status, "data_factory_manifest.json"),
        ("trade_schema_status", trade_schema_status, "data_factory_manifest.json"),
        ("kline_schema_status", kline_schema_status, "data_factory_manifest.json"),
        ("orderbook_schema_status", orderbook_schema_status, "data_factory_manifest.json"),
        ("metadata_schema_status", metadata_schema_status, "data_factory_manifest.json"),
        (
            "historical_metadata_status",
            historical_metadata_metric_status,
            "data_factory_manifest.json",
        ),
        ("date_pruning_status", date_pruning_metric_status, "data_quality_report.json"),
        (
            "silver_index_date_range_status",
            silver_index_date_range_metric_status,
            "data_quality_report.json",
        ),
        (
            "raw_scan_budget_status",
            raw_scan_budget_metric_status,
            "data_quality_report.json",
        ),
        ("candidate_export_status", candidate_export_status, "strategy_ladder_summary.json"),
        ("raw_window_extraction_status", raw_window_extraction_status, "first_run_manifest.json"),
        ("depth_replay_status", depth_replay_status, "silver_index.json"),
        ("candidate_truth_status", candidate_truth_metric_status, "run_manifest.json"),
        ("engine_native_status", engine_native_metric_status, "run_manifest.json"),
        (
            "expected_edge_truth_status",
            expected_edge_truth_metric_status,
            "run_manifest.json",
        ),
        (
            "fee_provenance_status",
            (
                "READY"
                if fee_provenance_status == "CONFIGURED_FEE_PROVENANCE_READY"
                else "NOT_PROVEN"
            ),
            "metadata silver",
        ),
        ("impact_provenance_status", impact_provenance_status, ""),
        ("fill_realism_status", fill_realism_status, "first_run_manifest.json"),
        (
            "executed_only_economics_status",
            executed_only_economics_status,
            "fill_realism + executed_trades",
        ),
        ("true_drawdown_status", true_drawdown_status, ""),
        ("capital_bucket_status", capital_bucket_status, "first_run_manifest.json"),
        (
            "promotion_artifact_status",
            (
                "READY"
                if promotion_artifact_status == "PROMOTION_ARTIFACTS_READY"
                else (
                    "BLOCKED"
                    if promotion_artifact_status
                    == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
                    else (
                        "PARTIAL"
                        if promotion_artifact_status.endswith("_PARTIAL")
                        else "NOT_PROVEN"
                    )
                )
            ),
            "strategy_ladder_summary.json",
        ),
        ("engine_promotion_status", engine_promotion_status, "strategy_ladder_summary.json"),
        ("pair_promotion_status", pair_promotion_status, "strategy_ladder_summary.json"),
        (
            "sample_size_survival_status",
            sample_size_survival_status,
            "strategy_ladder_summary.json",
        ),
    )
    ready_metrics: list[MetricProofEntry] = []
    metric_gaps: list[MetricProofEntry] = []
    for metric_name, status, source_artifact in metric_specs:
        normalized_status = status if status in _ALLOWED_METRIC_STATUSES else "NOT_PROVEN"
        entry = MetricProofEntry(
            metric_name=metric_name,
            status=normalized_status,
            value=None,
            denominator=None,
            source_artifact=source_artifact,
            blocker_codes=(),
            reason_codes=(
                ()
                if normalized_status == "READY"
                else (f"{metric_name}_{normalized_status}",)
            ),
        )
        if normalized_status == "READY":
            ready_metrics.append(entry)
        else:
            metric_gaps.append(entry)

    # --- Overall roll-up -------------------------------------------------------
    research_only_blockers = tuple(
        code for code in deduped_blockers if code in _RESEARCH_ONLY_BLOCKER_CODES
    )
    hard_blockers = tuple(
        code for code in deduped_blockers if code not in _RESEARCH_ONLY_BLOCKER_CODES
    )
    if hard_blockers:
        overall = "BACKTEST_PROOF_BLOCKED"
    elif research_only_blockers:
        overall = "BACKTEST_PROOF_RESEARCH_ONLY"
    elif executed_only_economics_status == "READY" and engine_promotion_status == "READY":
        overall = "BACKTEST_PROOF_READY"
    elif data_factory_status == "READY" and (
        executed_only_economics_status != "READY"
        or fill_realism_status != "READY"
        or true_drawdown_status != "READY"
    ):
        overall = "BACKTEST_PROOF_RESEARCH_ONLY"
    elif ready_metrics:
        overall = "BACKTEST_PROOF_PARTIAL"
    else:
        overall = "BACKTEST_PROOF_NOT_PROVEN"
    if overall not in _OVERALL_STATUSES:
        overall = "BACKTEST_PROOF_NOT_PROVEN"

    matrix = BacktestProofMatrix(
        run_id=run_id or _str_field(manifest_payload, "run_id", ""),
        pair=(pairs[0] if pairs else ""),
        pairs=tuple(pairs),
        start=start or _str_field(manifest_payload, "start", ""),
        end=end or _str_field(manifest_payload, "end", ""),
        ml_mode=ml_mode,
        output_root=str(output_root.resolve()),
        data_factory_status=data_factory_status,
        raw_source_provenance_status=raw_source_provenance_status,
        raw_source_typing_status=raw_source_typing_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        trade_schema_status=trade_schema_status,
        kline_schema_status=kline_schema_status,
        orderbook_schema_status=orderbook_schema_status,
        metadata_schema_status=metadata_schema_status,
        historical_metadata_status=historical_metadata_status,
        metadata_source_mode=metadata_source_mode,
        metadata_cache_path=metadata_cache_path,
        metadata_pairs_covered=metadata_pairs_covered,
        missing_metadata_pairs=missing_metadata_pairs,
        metadata_temporal_status=metadata_temporal_status,
        metadata_fetched_at_utc=metadata_fetched_at_utc,
        metadata_temporal_drift_days=metadata_temporal_drift_days,
        # Patch 6 batch 1 — orderbook snapshot/delta separation.
        orderbook_snapshot_status=orderbook_summary["snapshot_status"],
        orderbook_delta_status=orderbook_summary["delta_status"],
        orderbook_reconstruction_status=orderbook_summary["recon_status"],
        depth20_proof_status=orderbook_summary["depth20_status"],
        snapshot_entry_count=orderbook_summary["snapshot_entry_count"],
        delta_entry_count=orderbook_summary["delta_entry_count"],
        snapshot_paths=orderbook_summary["snapshot_paths"],
        delta_paths=orderbook_summary["delta_paths"],
        sequence_gap_status=orderbook_summary["sequence_gap_status"],
        stale_book_status=orderbook_summary["stale_book_status"],
        sequence_gap_report_path=(
            str((output_root / "orderbook_sequence_gap_report.json").resolve())
            if (output_root / "orderbook_sequence_gap_report.json").is_file()
            else ""
        ),
        gap_count=orderbook_summary.get("gap_count", 0),
        gap_files=_list_field(gap_report_payload, "gap_files"),
        gap_dates=_list_field(gap_report_payload, "gap_dates"),
        first_gap_expected_seq=(
            gap_report_payload.get("first_gap", {}).get("expected_seq")
            if isinstance(gap_report_payload.get("first_gap"), dict)
            else None
        ),
        first_gap_actual_seq=(
            gap_report_payload.get("first_gap", {}).get("actual_seq")
            if isinstance(gap_report_payload.get("first_gap"), dict)
            else None
        ),
        first_gap_previous_seq=(
            gap_report_payload.get("first_gap", {}).get("previous_seq")
            if isinstance(gap_report_payload.get("first_gap"), dict)
            else None
        ),
        first_gap_event_timestamp_ms=(
            gap_report_payload.get("first_gap", {}).get("event_timestamp_ms")
            if isinstance(gap_report_payload.get("first_gap"), dict)
            else None
        ),
        gap_recovery_status=_str_field(
            gap_report_payload, "gap_status", "ORDERBOOK_SEQUENCE_NOT_PROVEN"
        ),
        pair_inference_status=_str_field(
            quality_payload, "pair_inference_status", "PAIR_NOT_DETECTED"
        ),
        ignored_source_pairs=_list_field(quality_payload, "ignored_source_pairs"),
        active_pairs_after_pruning=_list_field(
            quality_payload, "active_pairs_after_pruning"
        ),
        # Patch 6 batch 1 — Phase 1/2 surfacing.
        phase1_feature_discovery_status=phase1_feature_discovery_status,
        phase1_candidate_export_status=phase1_candidate_export_status,
        phase2_raw_window_extraction_status=phase2_raw_window_extraction_status,
        phase2_detailed_replay_status=phase2_detailed_replay_status,
        # Patch 6 batch 1 — storage / governance surfacing.
        storage_budget_status=storage_budget_status,
        storage_budget_report_path=storage_budget_report_path,
        date_pruning_status=date_pruning_status,
        silver_index_date_range_status=silver_index_date_range_status,
        raw_scan_budget_status=raw_scan_budget_status,
        silver_storage_status=silver_storage_status,
        silver_bloat_ratio=silver_bloat_ratio,
        feature_threshold_manifest_path=feature_threshold_path,
        candidate_export_status=candidate_export_status,
        raw_window_extraction_status=raw_window_extraction_status,
        depth_replay_status=depth_replay_status,
        candidate_truth_status=candidate_truth_status,
        expected_edge_truth_status=expected_edge_truth_status,
        engine_native_status=engine_native_status,
        candidate_count=candidate_count,
        candidate_engine_native_count=candidate_engine_native_count,
        candidate_proxy_count=candidate_proxy_count,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        engine_native_records_built=engine_native_records_built,
        raw_window_count=raw_window_count,
        detailed_replay_count=detailed_replay_count,
        executed_count=executed_count,
        reduced_count=reduced_count,
        no_fill_count=no_fill_count,
        fee_provenance_status=fee_provenance_status,
        capital_bucket_metadata_status=capital_bucket_metadata_status,
        impact_provenance_status=impact_provenance_status,
        fill_realism_status=fill_realism_status,
        executed_only_economics_status=executed_only_economics_status,
        true_drawdown_status=true_drawdown_status,
        capital_bucket_status=capital_bucket_status,
        replay_fee_source_status=replay_fee_source_status,
        replay_impact_source_status=replay_impact_source_status,
        replay_fill_realism_status=replay_fill_realism_status,
        replay_cost_parity_status=replay_cost_parity_status,
        replay_executed_only_net_return_status=replay_executed_only_net_return_status,
        replay_true_net_equity_drawdown_status=replay_true_net_equity_drawdown_status,
        execution_label_source=execution_label_source,
        fee_model_source=fee_model_source,
        spread_model_source=spread_model_source,
        slippage_model_source=slippage_model_source,
        partial_fill_model_source=partial_fill_model_source,
        adverse_selection_source=adverse_selection_source,
        order_type_selection_source=order_type_selection_source,
        venue_constraints_source=venue_constraints_source,
        execution_fidelity_gap_codes=execution_fidelity_gap_codes,
        historical_replay_venue="BYBIT",
        execution_target_venue="BINANCE",
        backtest_class="BYBIT_PROXY_BACKTEST",
        venue_transfer_status="BINANCE_SHADOW_REQUIRED",
        live_trading_eligibility_status="BLOCKED",
        promotion_artifact_status=promotion_artifact_status,
        engine_promotion_status=engine_promotion_status,
        pair_promotion_status=pair_promotion_status,
        sample_size_survival_status=sample_size_survival_status,
        overall_backtest_proof_status=overall,
        blocker_codes=deduped_blockers,
        metric_gaps=tuple(metric_gaps),
        ready_metrics=tuple(ready_metrics),
        created_at=datetime.now(tz=UTC),
    )
    return finalize_hashed_model(matrix)


def _silver_metadata_row_count(silver_payload: dict[str, object]) -> int:
    entries = silver_payload.get("entries")
    if not isinstance(entries, list):
        return 0
    total = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("data_type") or "") != "metadata":
            continue
        try:
            total += int(entry.get("row_count") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _count_json_artifacts(root: Path, pattern: str) -> int:
    return sum(1 for path in root.rglob(pattern) if path.is_file())


def _read_first_row_from_matrix(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return {}


def _format_markdown(matrix: BacktestProofMatrix) -> str:
    """Render a compact human-readable summary for ``backtest_proof_matrix.md``."""

    lines: list[str] = []
    lines.append(f"# Backtest Proof Matrix — {matrix.run_id or 'unnamed'}")
    lines.append("")
    lines.append(f"- output_root: `{matrix.output_root}`")
    lines.append(f"- pairs: {', '.join(matrix.pairs) if matrix.pairs else '(none)'}")
    lines.append(f"- start / end: {matrix.start or '(none)'} / {matrix.end or '(none)'}")
    lines.append(f"- ml_mode: `{matrix.ml_mode}`")
    lines.append(f"- overall: **{matrix.overall_backtest_proof_status}**")
    lines.append(
        f"- replay doctrine: fee={matrix.replay_fee_source_status}, "
        f"impact={matrix.replay_impact_source_status}, "
        f"fill={matrix.replay_fill_realism_status}, "
        f"cost={matrix.replay_cost_parity_status}"
    )
    lines.append(
        f"- execution fidelity: label={matrix.execution_label_source}, "
        f"fee_model={matrix.fee_model_source}, "
        f"spread_model={matrix.spread_model_source}, "
        f"slippage_model={matrix.slippage_model_source}"
    )
    lines.append(
        f"- execution fill/order fidelity: partial_fill={matrix.partial_fill_model_source}, "
        f"adverse_selection={matrix.adverse_selection_source}, "
        f"order_type={matrix.order_type_selection_source}, "
        f"venue_constraints={matrix.venue_constraints_source}"
    )
    lines.append(
        "- execution fidelity gaps: "
        + (
            ", ".join(matrix.execution_fidelity_gap_codes)
            if matrix.execution_fidelity_gap_codes
            else "none"
        )
    )
    lines.append(
        f"- venue split: historical={matrix.historical_replay_venue}, "
        f"target={matrix.execution_target_venue}, "
        f"transfer={matrix.venue_transfer_status}, "
        f"live={matrix.live_trading_eligibility_status}"
    )
    lines.append(
        f"- engine native: status={matrix.engine_native_status}, "
        f"native_candidates={matrix.candidate_engine_native_count}, "
        f"proxy_candidates={matrix.candidate_proxy_count}, "
        f"records_built={matrix.engine_native_records_built}"
    )
    lines.append(
        f"- candidate truth: {matrix.candidate_truth_status}; "
        f"expected_edge={matrix.expected_edge_truth_status} "
        f"(proxy={matrix.expected_edge_proxy_count}, governed={matrix.expected_edge_governed_count})"
    )
    if matrix.silver_bloat_ratio is not None:
        lines.append(f"- silver_bloat_ratio: {matrix.silver_bloat_ratio}")
    if matrix.blocker_codes:
        lines.append("")
        lines.append("## Blockers")
        for code in matrix.blocker_codes:
            lines.append(f"- {code}")
    lines.append("")
    lines.append("## Ready metrics")
    if matrix.ready_metrics:
        for entry in matrix.ready_metrics:
            lines.append(f"- {entry.metric_name} ({entry.source_artifact or 'n/a'})")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Gaps")
    for entry in matrix.metric_gaps:
        reason = "; ".join(entry.reason_codes) if entry.reason_codes else entry.status
        lines.append(f"- {entry.metric_name}: {entry.status} — {reason}")
    return "\n".join(lines) + "\n"


def write_backtest_proof_matrix(
    output_root: Path,
    matrix: BacktestProofMatrix,
    *,
    write_markdown: bool = True,
) -> Path:
    """Persist the matrix as ``backtest_proof_matrix.json`` (and optional .md)."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "backtest_proof_matrix.json"
    atomic_write_json(json_path, matrix.model_dump(mode="json"), indent=2)
    if write_markdown:
        atomic_write_text(output_root / "backtest_proof_matrix.md", _format_markdown(matrix))
    return json_path


def emit_backtest_proof_matrix(
    *,
    output_root: Path,
    run_id: str = "",
    pairs: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    ml_mode: str = "ML_MODE_OFF",
    write_markdown: bool = True,
) -> tuple[BacktestProofMatrix, Path]:
    """Build and persist the proof matrix in one call. Returns ``(matrix, json_path)``."""

    matrix = build_backtest_proof_matrix(
        output_root=output_root,
        run_id=run_id,
        pairs=pairs,
        start=start,
        end=end,
        ml_mode=ml_mode,
    )
    json_path = write_backtest_proof_matrix(output_root, matrix, write_markdown=write_markdown)
    return matrix, json_path


__all__ = [
    "BacktestProofMatrix",
    "MetricProofEntry",
    "build_backtest_proof_matrix",
    "emit_backtest_proof_matrix",
    "write_backtest_proof_matrix",
]
