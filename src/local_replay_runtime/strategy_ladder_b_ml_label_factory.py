"""B_ML counterfactual label factory for Strategy Ladder ML training.

The B_ML rail is data-only. It creates supervised training rows from A2 gold
features and post-decision price windows without changing trading decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import gzip
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from calibration_methods import MlTrainingRow
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.feature_grounding_registry import (
    LABEL_OR_OUTCOME_FEATURE_NAMES,
    feature_grounding_entry,
)
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    normalize_supported_expected_edge_feature_names,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent
from local_replay_runtime.tabular_artifacts import (
    read_tabular_mirror_rows_if_ready,
    write_tabular_mirror,
)
from local_replay_runtime.training_source_contract import (
    ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED,
    build_training_source_contract_report,
)


BML_TARGET_POLICY = "BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1"
BML_PHASE = "B_ML_COUNTERFACTUAL_LABEL_FACTORY"
BML_SCHEMA_VERSION = "v53.b_ml_label_store_row.v1"
BML_LABEL_STORE_DATASET_FILENAME = "b_ml_label_store.jsonl"
BML_LABEL_SUMMARY_FILENAME = "b_ml_label_summary.json"
BML_TARGET_POLICY_REPORT_FILENAME = "b_ml_target_policy_report.json"
BML_EVENT_LOG_FILENAME = "b_ml_event_log.jsonl"

BML_READY_GOVERNED = "B_ML_DATASET_READY_FOR_GOVERNED_TRAINING"
BML_READY_RESEARCH = "B_ML_DATASET_READY_FOR_RESEARCH_TRAINING"
BML_RESEARCH_COST_PARTIAL = "B_ML_DATASET_RESEARCH_ONLY_COST_PARTIAL"
BML_BLOCKED_MISSING_POST_WINDOW = "B_ML_DATASET_BLOCKED_BY_MISSING_POST_WINDOW"
BML_BLOCKED_MISSING_BOOK = "B_ML_DATASET_BLOCKED_BY_MISSING_BOOK"
BML_BLOCKED_LABEL_LEAKAGE = "B_ML_DATASET_BLOCKED_BY_LABEL_LEAKAGE"
BML_BLOCKED_TARGET_POLICY = "B_ML_DATASET_BLOCKED_BY_TARGET_POLICY_MISMATCH"
BML_BLOCKED_TRAIN_EVAL_OVERLAP = "B_ML_DATASET_BLOCKED_BY_TRAIN_EVAL_OVERLAP"
BML_INSUFFICIENT_ROWS = "B_ML_DATASET_INSUFFICIENT_ROWS"

TRAINING_ROW_ELIGIBLE = "TRAINING_ROW_ELIGIBLE"
TRAINING_ROW_RESEARCH_ONLY = "TRAINING_ROW_RESEARCH_ONLY"
TRAINING_ROW_BLOCKED = "TRAINING_ROW_BLOCKED"

LABEL_COUNTERFACTUAL_REPLAY_GROUNDED = "LABEL_COUNTERFACTUAL_REPLAY_GROUNDED"
LABEL_COUNTERFACTUAL_COST_AWARE = "LABEL_COUNTERFACTUAL_COST_AWARE"
LABEL_COUNTERFACTUAL_EXECUTION_AWARE_PARTIAL = (
    "LABEL_COUNTERFACTUAL_EXECUTION_AWARE_PARTIAL"
)
LABEL_BLOCKED_BY_MISSING_POST_WINDOW = "LABEL_BLOCKED_BY_MISSING_POST_WINDOW"
LABEL_BLOCKED_BY_MISSING_BOOK = "LABEL_BLOCKED_BY_MISSING_BOOK"
LABEL_BLOCKED_BY_STALE_BOOK = "LABEL_BLOCKED_BY_STALE_BOOK"
LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT = "LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT"
LABEL_BLOCKED_BY_INSUFFICIENT_DEPTH = "LABEL_BLOCKED_BY_INSUFFICIENT_DEPTH"
LABEL_RESEARCH_ONLY_PROXY_COST = "LABEL_RESEARCH_ONLY_PROXY_COST"

FEATURE_EX_ANTE_AVAILABLE_AT_DECISION = "FEATURE_EX_ANTE_AVAILABLE_AT_DECISION"
FEATURE_POST_DECISION_LEAKAGE_BLOCKED = "FEATURE_POST_DECISION_LEAKAGE_BLOCKED"
FEATURE_TRUTH_BOUNDARY_NOT_PROVEN = "FEATURE_TRUTH_BOUNDARY_NOT_PROVEN"
A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH = (
    "A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH"
)
A2_GOLD_FEATURE_USAGE_NOT_PROVEN = "A2_GOLD_FEATURE_USAGE_NOT_PROVEN"
A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH = (
    "A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH"
)
A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH = (
    "A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH"
)
COST_FEATURE_TRUTH_NOT_PROVEN = "COST_FEATURE_TRUTH_NOT_PROVEN"

_LOGGER = logging.getLogger(__name__)

_BML_BACKGROUND_SAMPLER_MODES = {
    "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
    "ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID",
}
_BML_REUSE_B1_SAMPLER_MODES = {
    "REUSE_B1_FAST_CANDIDATES",
    "ENGINE_NATIVE_DRY_EVAL",
    "ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID",
}
_BML_SUPPORTED_SAMPLER_MODES = (
    *_BML_BACKGROUND_SAMPLER_MODES,
    *_BML_REUSE_B1_SAMPLER_MODES,
)

_SPREAD_MEASURED_STATUSES = {
    "MEASURED_FROM_BOOK_SNAPSHOT",
    "MEASURED_FROM_BOOK_RECONSTRUCTION",
}
_SPREAD_STALE_STATUSES = {"MEASURED_FROM_BOOK_SNAPSHOT_STALE"}
_SLIPPAGE_MEASURED_STATUSES = {
    "MEASURED_FROM_KYLE_LAMBDA",
    "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE",
    "MEASURED_FROM_DEPTH20_BOOK_WALK",
}
_SLIPPAGE_STALE_STATUSES = {"MEASURED_FROM_DEPTH20_BOOK_WALK_STALE"}
_BOOK_READY_STATUSES = {
    "BOOK_DEPTH20_AVAILABLE",
    "BOOK_LIMITED_DEPTH_AVAILABLE",
    "BOOK_TOP_OF_BOOK_ONLY",
}


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _parse_boundary_ms(raw_value: str, *, end_of_day: bool = False) -> int | None:
    value = (raw_value or "").strip()
    if not value:
        return None
    try:
        if "T" not in value and " " not in value:
            parsed = datetime.fromisoformat(value)
            if end_of_day:
                parsed = parsed + timedelta(days=1) - timedelta(milliseconds=1)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def _datetime_from_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)


def _horizon_to_ms(raw_value: str) -> int:
    value = str(raw_value or "").strip().lower()
    if value.endswith("ms"):
        return max(int(value[:-2]), 1)
    if value.endswith("m"):
        return max(int(value[:-1]), 1) * 60_000
    if value.endswith("h"):
        return max(int(value[:-1]), 1) * 3_600_000
    return max(int(value), 1) * 60_000


def _read_jsonl_any(path: Path) -> tuple[dict[str, Any], ...]:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        else:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return ()
    rows: list[dict[str, Any]] = []
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


def _read_dataset_rows_any(path: Path) -> tuple[dict[str, Any], ...]:
    tabular_rows = read_tabular_mirror_rows_if_ready(path)
    if tabular_rows is not None:
        return tabular_rows
    return _read_jsonl_any(path)


def _maybe_json_mapping(raw_value: Any) -> dict[str, Any] | None:
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            return None
        try:
            payload = json.loads(stripped)
        except (TypeError, ValueError):
            return None
        if isinstance(payload, dict):
            return payload
    return None


def _write_jsonl(path: Path, rows: tuple[BaseModel, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(row.model_dump_json() for row in rows)
    atomic_write_text(path, payload + ("\n" if payload else ""))
    return path


def _write_tabular_mirror_non_blocking(
    *,
    rows: tuple[Any, ...] | list[dict[str, Any]],
    artifact_name: str,
    output_dir: Path,
    source_path: Path | None = None,
) -> dict[str, Any]:
    try:
        return write_tabular_mirror(
            rows=rows,
            artifact_name=artifact_name,
            output_dir=output_dir,
            source_path=source_path,
        )
    except Exception as exc:  # pragma: no cover - optional performance mirror
        manifest_path = output_dir / f"{artifact_name}.tabular_manifest.json"
        payload = {
            "schema_version": "v53.tabular_artifact_mirror.v1",
            "artifact_name": artifact_name,
            "source_path": None if source_path is None else str(source_path.resolve()),
            "status": "TABULAR_MIRROR_FAILED_NON_BLOCKING",
            "error_type": type(exc).__name__,
            "audit_jsonl_preserved": source_path is None or source_path.is_file(),
        }
        atomic_write_json(manifest_path, payload, indent=2)
        return payload


def _finite_float(raw_value: Any) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _int_value(raw_value: Any) -> int | None:
    if isinstance(raw_value, bool):
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value


def _feature_source_status(name: str, row: dict[str, Any]) -> str:
    entry = feature_grounding_entry(name)
    if entry is None:
        return "FEATURE_GROUNDING_UNKNOWN_BLOCKED"
    sources = row.get("feature_sources_used")
    if isinstance(sources, list):
        sources = tuple(str(item) for item in sources)
    elif not isinstance(sources, tuple):
        sources = ()
    if entry.requires_a2_orderbook and "orderbook" not in sources:
        return "FEATURE_MISSING_ORDERBOOK_SOURCE"
    if entry.requires_trade_window and "trades" not in sources:
        return "FEATURE_MISSING_TRADE_SOURCE"
    return "FEATURE_VALUE_OK"


def _is_label_feature_name(name: str) -> bool:
    entry = feature_grounding_entry(name)
    return name in LABEL_OR_OUTCOME_FEATURE_NAMES or (
        entry is not None and entry.is_label_or_outcome
    )


class BmlLabelFactoryRequest(BaseModel, frozen=True):
    workflow_run_id: str = Field(..., min_length=1)
    a2_run_root: Path
    output_root: Path
    pair_list: tuple[str, ...]
    timeframes: tuple[str, ...]
    start: str = Field(..., min_length=1)
    end: str = Field(..., min_length=1)
    label_horizons: tuple[str, ...] = ("5m", "15m", "1h")
    capital_buckets: tuple[int, ...] = (400, 500, 1500, 4000)
    candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    b1_candidate_events_path: Path | None = None
    existing_b1_candidates_root: Path | None = None
    existing_b2_raw_windows_root: Path | None = None
    allow_reuse_existing_raw_windows: bool = True
    allow_generate_new_raw_windows: bool = False
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    target_policy: str = BML_TARGET_POLICY
    runtime_mode: str = "RESEARCH_DATASET_ONLY"
    max_candidates_per_day: int = Field(default=0, ge=0)
    train_start: str = ""
    train_end: str = ""
    validation_start: str = ""
    validation_end: str = ""
    allowed_backtest_start_after: str = ""

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return normalize_supported_expected_edge_feature_names(value)

    @model_validator(mode="after")
    def _validate_runtime(self) -> "BmlLabelFactoryRequest":
        if self.runtime_mode != "RESEARCH_DATASET_ONLY":
            raise ValueError("B_ML only supports runtime_mode=RESEARCH_DATASET_ONLY")
        if self.target_policy != BML_TARGET_POLICY:
            raise ValueError(f"B_ML target_policy must be {BML_TARGET_POLICY}")
        if self.candidate_sampler_mode not in _BML_SUPPORTED_SAMPLER_MODES:
            raise ValueError(
                "B_ML unsupported candidate_sampler_mode: "
                f"{self.candidate_sampler_mode}"
            )
        return self


class BmlLabelStoreRow(BaseModel, frozen=True):
    schema_version: str = BML_SCHEMA_VERSION
    candidate_id: str
    candidate_source: str
    pair: str
    timeframe: str
    engine_id: str = "background"
    side: str = "buy"
    decision_timestamp_ms: int
    horizon: str
    capital_bucket: int
    feature_values: dict[str, float]
    feature_provenance: dict[str, str] = Field(default_factory=dict)
    feature_truth_boundary_status: str = FEATURE_TRUTH_BOUNDARY_NOT_PROVEN
    feature_usage_policy: str = A2_GOLD_FEATURE_USAGE_NOT_PROVEN
    cost_feature_truth_status: str = COST_FEATURE_TRUTH_NOT_PROVEN
    entry_reference_price: float
    post_window_status: str
    spread_bps_measured: float | None = None
    spread_source_status: str = ""
    slippage_bps_measured: float | None = None
    slippage_source_status: str = ""
    fee_bps: float | None = None
    fee_source_status: str = ""
    latency_penalty_bps: float | None = None
    depth_fill_ratio: float | None = None
    forward_return_bps: float | None = None
    mfe_bps: float | None = None
    mae_bps: float | None = None
    net_return_after_cost_bps: float | None = None
    break_even_cleared: bool | None = None
    label_value: float | None = None
    label_name: str = "net_return_after_cost_bps"
    target_policy: str = BML_TARGET_POLICY
    label_truth_status: str = ""
    training_row_status: str = TRAINING_ROW_BLOCKED
    promotion_allowed: bool = False
    raw_window_refs: dict[str, str] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_no_label_features(self) -> "BmlLabelStoreRow":
        blocked = tuple(name for name in self.feature_values if _is_label_feature_name(name))
        if blocked:
            raise ValueError(f"B_ML feature_values contain label/outcome fields: {blocked}")
        return self


class BmlLabelFactoryResult(BaseModel, frozen=True):
    status: str
    manifest_path: str
    label_store_path: str
    audit_report_path: str
    row_count: int = 0
    training_row_eligible_count: int = 0
    training_row_research_only_count: int = 0
    training_row_blocked_count: int = 0
    final_verdict: str


def _gold_feature_paths(a2_run_root: Path, pair: str, timeframe: str) -> tuple[Path, ...]:
    root = a2_run_root / "gold" / f"features_{timeframe}" / pair
    if not root.is_dir():
        return ()
    return tuple(sorted([*root.rglob("*.jsonl"), *root.rglob("*.jsonl.gz")]))


def _load_a2_feature_points(request: BmlLabelFactoryRequest) -> dict[tuple[str, str], list[dict[str, Any]]]:
    start_ms = _parse_boundary_ms(request.start, end_of_day=False)
    end_ms = _parse_boundary_ms(request.end, end_of_day=True)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for pair in request.pair_list:
        normalized_pair = pair.strip().upper()
        for timeframe in request.timeframes:
            key = (normalized_pair, timeframe)
            rows: list[dict[str, Any]] = []
            for path in _gold_feature_paths(request.a2_run_root, normalized_pair, timeframe):
                for row in _read_jsonl_any(path):
                    timestamp_ms = _int_value(row.get("timestamp_ms"))
                    if timestamp_ms is None:
                        continue
                    if start_ms is not None and timestamp_ms < start_ms:
                        continue
                    if end_ms is not None and timestamp_ms > end_ms:
                        continue
                    rows.append({**row, "_source_ref": str(path.resolve())})
            rows.sort(key=lambda item: int(item.get("timestamp_ms") or 0))
            grouped[key] = rows
    return grouped


def _resolve_b1_candidate_events_path(request: BmlLabelFactoryRequest) -> Path | None:
    if request.b1_candidate_events_path is not None:
        candidate = request.b1_candidate_events_path.resolve()
        return candidate if candidate.is_file() else None
    if request.existing_b1_candidates_root is None:
        return None
    root = request.existing_b1_candidates_root.resolve()
    if root.is_file():
        return root
    direct_candidates = (
        root / "candidate_events.jsonl",
        root / "fast_candidates" / "candidate_events.jsonl",
        root / "preselection_candidates.jsonl",
    )
    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate
    for filename in ("candidate_events.jsonl", "preselection_candidates.jsonl"):
        matches = tuple(sorted(root.rglob(filename)))
        if matches:
            return matches[0]
    return None


def _load_reused_b1_events(request: BmlLabelFactoryRequest) -> tuple[StrategyLadderCandidateEvent, ...]:
    path = _resolve_b1_candidate_events_path(request)
    if path is None:
        return ()
    start_ms = _parse_boundary_ms(request.start, end_of_day=False)
    end_ms = _parse_boundary_ms(request.end, end_of_day=True)
    pairs = {pair.strip().upper() for pair in request.pair_list if pair.strip()}
    timeframes = {timeframe.strip() for timeframe in request.timeframes if timeframe.strip()}
    events: list[StrategyLadderCandidateEvent] = []
    for payload in _read_jsonl_any(path):
        try:
            event = StrategyLadderCandidateEvent.model_validate(payload)
        except ValueError:
            continue
        timestamp_ms = event.resolved_timestamp_ms
        if start_ms is not None and timestamp_ms < start_ms:
            continue
        if end_ms is not None and timestamp_ms > end_ms:
            continue
        if event.pair.strip().upper() not in pairs:
            continue
        event_timeframe = (event.timeframe or "").strip()
        if timeframes and event_timeframe not in timeframes:
            continue
        events.append(event)
    return tuple(
        sorted(
            events,
            key=lambda item: (
                item.resolved_timestamp_ms,
                item.pair,
                item.timeframe or "",
                item.engine_id,
                item.candidate_id,
            ),
        )
    )


def _sample_candidates(
    rows: list[dict[str, Any]],
    *,
    max_candidates_per_day: int,
) -> list[dict[str, Any]]:
    if max_candidates_per_day <= 0:
        return rows
    selected: list[dict[str, Any]] = []
    per_day: dict[str, int] = {}
    for row in rows:
        timestamp_ms = int(row.get("timestamp_ms") or 0)
        day = _datetime_from_ms(timestamp_ms).date().isoformat()
        count = per_day.get(day, 0)
        if count >= max_candidates_per_day:
            continue
        selected.append(row)
        per_day[day] = count + 1
    return selected


def _future_row(rows: list[dict[str, Any]], target_timestamp_ms: int) -> dict[str, Any] | None:
    for row in rows:
        timestamp_ms = int(row.get("timestamp_ms") or 0)
        if timestamp_ms >= target_timestamp_ms:
            return row
    return None


def _post_window_rows(rows: list[dict[str, Any]], start_ms: int, end_ms: int) -> tuple[dict[str, Any], ...]:
    return tuple(
        row
        for row in rows
        if start_ms < int(row.get("timestamp_ms") or 0) <= end_ms
    )


def _row_at_or_before(rows: list[dict[str, Any]], timestamp_ms: int) -> dict[str, Any] | None:
    selected: dict[str, Any] | None = None
    for row in rows:
        row_timestamp_ms = int(row.get("timestamp_ms") or 0)
        if row_timestamp_ms > timestamp_ms:
            break
        selected = row
    return selected


def _selected_feature_values(
    row: dict[str, Any],
    feature_names: tuple[str, ...],
    *,
    decision_timestamp_ms: int,
) -> tuple[dict[str, float], dict[str, str], list[str]]:
    raw_features = row.get("feature_values")
    if not isinstance(raw_features, dict):
        raw_features = {}
    values: dict[str, float] = {}
    provenance: dict[str, str] = {}
    warnings: list[str] = []
    available_at = _int_value(row.get("available_at_timestamp_ms"))
    for name in feature_names:
        if _is_label_feature_name(name):
            warnings.append(f"FEATURE_POST_DECISION_LEAKAGE:{name}")
            continue
        if available_at is not None and available_at > decision_timestamp_ms:
            warnings.append(f"FEATURE_POST_DECISION_LEAKAGE:{name}")
            continue
        value = _finite_float(raw_features.get(name))
        if value is None and name in row:
            value = _finite_float(row.get(name))
        if value is None:
            warnings.append(f"FEATURE_MISSING:{name}")
            continue
        status = _feature_source_status(name, row)
        if status != "FEATURE_VALUE_OK":
            warnings.append(f"{status}:{name}")
        values[name] = value
        provenance[name] = status
    return values, provenance, warnings


def _feature_truth_boundary_status(
    row: dict[str, Any],
    *,
    decision_timestamp_ms: int,
) -> str:
    feature_timestamp = _int_value(row.get("available_at_timestamp_ms"))
    if feature_timestamp is None:
        feature_timestamp = _int_value(row.get("timestamp_ms"))
    if feature_timestamp is not None and feature_timestamp > decision_timestamp_ms:
        return FEATURE_POST_DECISION_LEAKAGE_BLOCKED
    explicit = str(row.get("feature_truth_boundary_status") or "").strip()
    if explicit:
        return explicit
    if feature_timestamp is None:
        return FEATURE_TRUTH_BOUNDARY_NOT_PROVEN
    return FEATURE_EX_ANTE_AVAILABLE_AT_DECISION


def _feature_usage_policy(row: dict[str, Any]) -> str:
    explicit = str(row.get("feature_usage_policy") or "").strip()
    if explicit:
        return explicit
    return A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH


def _cost_feature_truth_status(row: dict[str, Any], *, cost_truth: str) -> str:
    explicit = str(row.get("cost_feature_truth_status") or "").strip()
    if explicit:
        return explicit
    if cost_truth == LABEL_COUNTERFACTUAL_COST_AWARE:
        return A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH
    if cost_truth in {
        LABEL_COUNTERFACTUAL_REPLAY_GROUNDED,
        LABEL_COUNTERFACTUAL_EXECUTION_AWARE_PARTIAL,
        LABEL_RESEARCH_ONLY_PROXY_COST,
    }:
        return A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH
    return COST_FEATURE_TRUTH_NOT_PROVEN


def _source_refs(rows: tuple[dict[str, Any], ...]) -> str:
    refs = tuple(
        dict.fromkeys(
            str(row.get("_source_ref") or row.get("source_ref") or "").strip()
            for row in rows
            if str(row.get("_source_ref") or row.get("source_ref") or "").strip()
        )
    )
    return "|".join(refs) if refs else "MISSING_IN_ARTIFACT"


def _cost_truth(
    row: dict[str, Any],
) -> tuple[str, float | None, str, float | None, str, float | None, str, float | None, list[str]]:
    warnings: list[str] = []
    book_status = str(row.get("book_depth_source_status") or "").strip()
    spread_provenance = str(row.get("spread_provenance") or "").strip()
    slippage_provenance = str(row.get("slippage_provenance") or "").strip()
    spread_bps = _finite_float(row.get("spread_bps"))
    slippage_bps = _finite_float(row.get("slippage_bps"))
    latency_bps = _finite_float(row.get("latency_penalty_bps"))
    taker_fee_rate = _finite_float(row.get("taker_fee_rate"))
    fee_bps = None if taker_fee_rate is None else max(taker_fee_rate * 10_000.0, 0.0)
    if not book_status:
        return (
            LABEL_BLOCKED_BY_MISSING_BOOK,
            spread_bps,
            spread_provenance,
            slippage_bps,
            slippage_provenance,
            fee_bps,
            "MISSING_IN_ARTIFACT" if fee_bps is None else "FEE_FROM_A2_METADATA",
            latency_bps,
            ["MISSING_BOOK_STATUS"],
        )
    if book_status and book_status not in _BOOK_READY_STATUSES:
        return (
            LABEL_BLOCKED_BY_MISSING_BOOK,
            spread_bps,
            spread_provenance,
            slippage_bps,
            slippage_provenance,
            fee_bps,
            "MISSING_IN_ARTIFACT" if fee_bps is None else "FEE_FROM_A2_METADATA",
            latency_bps,
            [f"MISSING_BOOK:{book_status}"],
        )
    if not book_status:
        warnings.append("MISSING_BOOK_STATUS")
    if spread_provenance in _SPREAD_STALE_STATUSES or slippage_provenance in _SLIPPAGE_STALE_STATUSES:
        warnings.append("STALE_BOOK")
        truth = LABEL_BLOCKED_BY_STALE_BOOK
    elif spread_provenance in _SPREAD_MEASURED_STATUSES and slippage_provenance in _SLIPPAGE_MEASURED_STATUSES:
        if fee_bps is None:
            warnings.append("FEE_MODEL_MISSING_RESEARCH_ONLY")
            truth = LABEL_RESEARCH_ONLY_PROXY_COST
        else:
            truth = LABEL_COUNTERFACTUAL_COST_AWARE
    elif spread_bps is not None and slippage_bps is not None:
        warnings.append("PROXY_COST_RESEARCH_ONLY")
        truth = LABEL_RESEARCH_ONLY_PROXY_COST
    else:
        warnings.append("SLIPPAGE_NOT_MEASURED")
        truth = LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT
    return (
        truth,
        spread_bps,
        spread_provenance,
        slippage_bps,
        slippage_provenance,
        fee_bps,
        "MISSING_IN_ARTIFACT" if fee_bps is None else "FEE_FROM_A2_METADATA",
        latency_bps,
        warnings,
    )


def _candidate_id(*parts: object) -> str:
    return "bml-" + _hash_payload(parts)[:20]


def _bml_candidate_source_for_event(
    request: BmlLabelFactoryRequest,
    event: StrategyLadderCandidateEvent,
) -> str:
    if request.candidate_sampler_mode == "REUSE_B1_FAST_CANDIDATES":
        return "REUSED_B1_DISCOVERY"
    event_source = str(event.candidate_source or "").upper()
    reasons = {str(reason).upper() for reason in event.preliminary_reason_codes}
    if "ENGINE_NATIVE" in event_source or any("ENGINE_NATIVE" in reason for reason in reasons):
        return "ENGINE_NATIVE_DRY_EVAL_REUSED_B1"
    if request.candidate_sampler_mode == "ENGINE_NATIVE_DRY_EVAL":
        return "ENGINE_NATIVE_DRY_EVAL_REUSED_B1"
    return "REUSED_B1_DISCOVERY"


def _candidate_seeds(
    request: BmlLabelFactoryRequest,
    grouped: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[str, Any], ...]:
    seeds: list[dict[str, Any]] = []
    mode = request.candidate_sampler_mode
    if mode in _BML_REUSE_B1_SAMPLER_MODES:
        for event in _load_reused_b1_events(request):
            key = (event.pair.strip().upper(), (event.timeframe or "").strip())
            source_row = _row_at_or_before(grouped.get(key, []), event.resolved_timestamp_ms)
            if source_row is None:
                continue
            seeds.append(
                {
                    "candidate_id": event.candidate_id,
                    "candidate_source": _bml_candidate_source_for_event(request, event),
                    "engine_id": event.engine_id,
                    "side": str(
                        (event.compatibility_payload or {}).get("side")
                        if isinstance(event.compatibility_payload, dict)
                        else ""
                    ).strip()
                    or "buy",
                    "pair": key[0],
                    "timeframe": key[1],
                    "decision_timestamp_ms": event.resolved_timestamp_ms,
                    "source_row": source_row,
                    "native_reason_codes": tuple(event.preliminary_reason_codes),
                }
            )
    if mode in _BML_BACKGROUND_SAMPLER_MODES:
        for (pair, timeframe), rows in grouped.items():
            sampled = _sample_candidates(
                rows,
                max_candidates_per_day=request.max_candidates_per_day,
            )
            for source_row in sampled:
                decision_ts = int(source_row.get("timestamp_ms") or 0)
                seeds.append(
                    {
                        "candidate_id": _candidate_id(
                            request.workflow_run_id,
                            pair,
                            timeframe,
                            decision_ts,
                        ),
                        "candidate_source": "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
                        "engine_id": "background",
                        "side": "buy",
                        "pair": pair,
                        "timeframe": timeframe,
                        "decision_timestamp_ms": decision_ts,
                        "source_row": source_row,
                        "native_reason_codes": (),
                    }
                )
    deduped: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    for index, seed in enumerate(seeds):
        deduped[
            (
                str(seed["candidate_id"]),
                int(seed["decision_timestamp_ms"]),
                str(seed["candidate_source"]),
                index if mode == "ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID" else 0,
            )
        ] = seed
    return tuple(deduped.values())


def _build_label_rows(request: BmlLabelFactoryRequest) -> tuple[BmlLabelStoreRow, ...]:
    grouped = _load_a2_feature_points(request)
    rows_out: list[BmlLabelStoreRow] = []
    seeds = _candidate_seeds(request, grouped)
    for seed in seeds:
            source_row = seed["source_row"]
            pair = str(seed["pair"])
            timeframe = str(seed["timeframe"])
            rows = grouped.get((pair, timeframe), [])
            decision_ts = int(seed["decision_timestamp_ms"])
            entry_price = _finite_float(source_row.get("close_price"))
            if entry_price is None or entry_price <= 0.0:
                continue
            features, feature_provenance, feature_warnings = _selected_feature_values(
                source_row,
                request.feature_names,
                decision_timestamp_ms=decision_ts,
            )
            feature_truth_status = _feature_truth_boundary_status(
                source_row,
                decision_timestamp_ms=decision_ts,
            )
            feature_usage_policy = _feature_usage_policy(source_row)
            if feature_truth_status != FEATURE_EX_ANTE_AVAILABLE_AT_DECISION:
                feature_warnings.append(
                    f"{feature_truth_status}:feature_truth_boundary"
                )
            for horizon in request.label_horizons:
                horizon_ms = _horizon_to_ms(horizon)
                target_ts = decision_ts + horizon_ms
                target_row = _future_row(rows, target_ts)
                post_rows = _post_window_rows(rows, decision_ts, target_ts)
                post_window_ready = target_row is not None and bool(post_rows)
                future_close = (
                    None
                    if target_row is None
                    else _finite_float(target_row.get("close_price"))
                )
                forward_return_bps = None
                mfe_bps = None
                mae_bps = None
                if post_window_ready and future_close is not None:
                    forward_return_bps = ((future_close - entry_price) / entry_price) * 10_000.0
                    closes = tuple(
                        value
                        for value in (_finite_float(item.get("close_price")) for item in post_rows)
                        if value is not None
                    )
                    if closes:
                        mfe_bps = ((max(closes) - entry_price) / entry_price) * 10_000.0
                        mae_bps = ((min(closes) - entry_price) / entry_price) * 10_000.0
                (
                    cost_truth,
                    spread_bps,
                    spread_status,
                    slippage_bps,
                    slippage_status,
                    fee_bps,
                    fee_status,
                    latency_bps,
                    cost_warnings,
                ) = _cost_truth(source_row)
                cost_feature_status = _cost_feature_truth_status(
                    source_row,
                    cost_truth=cost_truth,
                )
                warnings = [*feature_warnings, *cost_warnings]
                label_truth_status = cost_truth
                training_status = TRAINING_ROW_ELIGIBLE
                if not post_window_ready or forward_return_bps is None:
                    label_truth_status = LABEL_BLOCKED_BY_MISSING_POST_WINDOW
                    training_status = TRAINING_ROW_BLOCKED
                    warnings.append("MISSING_POST_WINDOW")
                elif feature_warnings:
                    training_status = TRAINING_ROW_BLOCKED
                elif cost_truth in {
                    LABEL_BLOCKED_BY_MISSING_BOOK,
                    LABEL_BLOCKED_BY_STALE_BOOK,
                    LABEL_BLOCKED_BY_SLIPPAGE_MEASUREMENT,
                }:
                    training_status = TRAINING_ROW_BLOCKED
                elif cost_truth == LABEL_RESEARCH_ONLY_PROXY_COST:
                    training_status = TRAINING_ROW_RESEARCH_ONLY
                net_return = None
                break_even_cleared = None
                if forward_return_bps is not None:
                    total_cost = sum(
                        value
                        for value in (
                            spread_bps,
                            slippage_bps,
                            fee_bps,
                            latency_bps,
                        )
                        if value is not None
                    )
                    net_return = forward_return_bps - total_cost
                    break_even_cleared = net_return > 0.0
                raw_ref = str(source_row.get("_source_ref") or source_row.get("source_ref") or "")
                post_window_ref = _source_refs(post_rows)
                target_ref = (
                    "MISSING_IN_ARTIFACT"
                    if target_row is None
                    else _source_refs((target_row,))
                )
                for bucket in request.capital_buckets:
                    rows_out.append(
                        BmlLabelStoreRow(
                            candidate_id=str(seed["candidate_id"]),
                            candidate_source=str(seed["candidate_source"]),
                            pair=pair,
                            timeframe=timeframe,
                            engine_id=str(seed["engine_id"]),
                            side=str(seed["side"]) or "buy",
                            decision_timestamp_ms=decision_ts,
                            horizon=horizon,
                            capital_bucket=bucket,
                            feature_values=features,
                            feature_provenance=feature_provenance,
                            feature_truth_boundary_status=feature_truth_status,
                            feature_usage_policy=feature_usage_policy,
                            cost_feature_truth_status=cost_feature_status,
                            entry_reference_price=entry_price,
                            post_window_status=(
                                "POST_WINDOW_READY"
                                if post_window_ready
                                else LABEL_BLOCKED_BY_MISSING_POST_WINDOW
                            ),
                            spread_bps_measured=spread_bps,
                            spread_source_status=spread_status or "MISSING_IN_ARTIFACT",
                            slippage_bps_measured=slippage_bps,
                            slippage_source_status=slippage_status or "MISSING_IN_ARTIFACT",
                            fee_bps=fee_bps,
                            fee_source_status=fee_status,
                            latency_penalty_bps=latency_bps,
                            depth_fill_ratio=1.0 if cost_truth not in {LABEL_BLOCKED_BY_MISSING_BOOK} else None,
                            forward_return_bps=forward_return_bps,
                            mfe_bps=mfe_bps,
                            mae_bps=mae_bps,
                            net_return_after_cost_bps=net_return,
                            break_even_cleared=break_even_cleared,
                            label_value=net_return,
                            label_truth_status=label_truth_status,
                            training_row_status=training_status,
                            promotion_allowed=False,
                            raw_window_refs={
                                "orderbook": raw_ref or "MISSING_IN_ARTIFACT",
                                "trades": raw_ref or "MISSING_IN_ARTIFACT",
                                "ohlcv": raw_ref or "MISSING_IN_ARTIFACT",
                                "post_window": post_window_ref,
                                "target_row": target_ref,
                            },
                            warnings=tuple(dict.fromkeys(warnings)),
                        )
                    )
    return tuple(rows_out)


def _status_counts(rows: tuple[BmlLabelStoreRow, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.training_row_status] = counts.get(row.training_row_status, 0) + 1
    return counts


def _count_values(values: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "MISSING_IN_ARTIFACT")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _final_verdict(rows: tuple[BmlLabelStoreRow, ...], *, overlap_blocked: bool) -> str:
    if not rows:
        return BML_INSUFFICIENT_ROWS
    if overlap_blocked:
        return BML_BLOCKED_TRAIN_EVAL_OVERLAP
    if any(
        any(warning.startswith("FEATURE_POST_DECISION_LEAKAGE") for warning in row.warnings)
        for row in rows
    ):
        return BML_BLOCKED_LABEL_LEAKAGE
    if all(row.label_truth_status == LABEL_BLOCKED_BY_MISSING_POST_WINDOW for row in rows):
        return BML_BLOCKED_MISSING_POST_WINDOW
    if all(row.label_truth_status == LABEL_BLOCKED_BY_MISSING_BOOK for row in rows):
        return BML_BLOCKED_MISSING_BOOK
    if any(row.training_row_status == TRAINING_ROW_ELIGIBLE for row in rows):
        if all(row.training_row_status == TRAINING_ROW_ELIGIBLE for row in rows):
            return BML_READY_GOVERNED
        return BML_READY_RESEARCH
    if any(row.training_row_status == TRAINING_ROW_RESEARCH_ONLY for row in rows):
        return BML_RESEARCH_COST_PARTIAL
    return BML_INSUFFICIENT_ROWS


def _write_manifest(
    request: BmlLabelFactoryRequest,
    *,
    output_root: Path,
    rows: tuple[BmlLabelStoreRow, ...],
    final_verdict: str,
) -> Path:
    train_end = request.train_end or request.end
    allowed_start = request.allowed_backtest_start_after
    if not allowed_start:
        parsed_end = _parse_boundary_ms(train_end, end_of_day=False)
        if parsed_end is not None:
            allowed_start = (_datetime_from_ms(parsed_end) + timedelta(days=1)).date().isoformat()
    training_allowed = (
        any(row.training_row_status == TRAINING_ROW_ELIGIBLE for row in rows)
        and final_verdict in {BML_READY_GOVERNED, BML_READY_RESEARCH}
    )
    manifest = {
        "schema_version": "v53.b_ml_training_dataset_manifest.v1",
        "dataset_role": "ML_TRAINING_SOURCE",
        "phase": BML_PHASE,
        "workflow_run_id": request.workflow_run_id,
        "dataset_name": f"bml_dataset_train_{request.start}_to_{request.end}",
        "source_type": "A2_FEATURES_PLUS_COUNTERFACTUAL_REPLAY_LABELS",
        "a2_run_root": str(request.a2_run_root.resolve()),
        "b_ml_run_root": str(output_root.resolve()),
        "train_start": request.train_start or request.start,
        "train_end": train_end,
        "validation_start": request.validation_start,
        "validation_end": request.validation_end,
        "allowed_backtest_start_after": allowed_start,
        "forbidden_eval_overlap": True,
        "target_policy": request.target_policy,
        "label_truth_status": (
            "COUNTERFACTUAL_REPLAY_GROUNDED_COST_AWARE"
            if final_verdict == BML_READY_GOVERNED
            else "COUNTERFACTUAL_REPLAY_RESEARCH_ONLY_OR_BLOCKED"
        ),
        "promotion_allowed": False,
        "training_allowed": training_allowed,
        "row_count": len(rows),
        "notes": "Training dataset only. Not a profitability backtest. No selected/executed claims.",
    }
    path = output_root / "manifest.json"
    atomic_write_json(path, manifest, indent=2)
    return path


def project_bml_rows_to_ml_training_rows(
    label_store_path: Path,
    *,
    require_training_allowed: bool = True,
    pair: str = "",
    timeframe: str = "",
    start: str = "",
    end: str = "",
    feature_names: tuple[str, ...] = (),
) -> tuple[MlTrainingRow, ...]:
    start_ms = _parse_boundary_ms(start, end_of_day=False) if start else None
    end_ms = _parse_boundary_ms(end, end_of_day=True) if end else None
    normalized_pair = pair.strip().upper()
    normalized_timeframe = timeframe.strip()
    rows = []
    for payload in _read_dataset_rows_any(label_store_path):
        status = str(payload.get("training_row_status") or "")
        if require_training_allowed and status != TRAINING_ROW_ELIGIBLE:
            continue
        features = _maybe_json_mapping(payload.get("feature_values"))
        if features is None:
            continue
        target = _finite_float(payload.get("label_value"))
        timestamp_ms = _int_value(payload.get("decision_timestamp_ms"))
        payload_pair = str(payload.get("pair") or "").strip().upper()
        payload_timeframe = str(payload.get("timeframe") or "").strip()
        if normalized_pair and payload_pair != normalized_pair:
            continue
        if normalized_timeframe and payload_timeframe != normalized_timeframe:
            continue
        if start_ms is not None and timestamp_ms is not None and timestamp_ms < start_ms:
            continue
        if end_ms is not None and timestamp_ms is not None and timestamp_ms > end_ms:
            continue
        if target is None or timestamp_ms is None or not payload_pair:
            continue
        selected_names = feature_names or tuple(str(name) for name in features)
        numeric_features: dict[str, float] = {}
        missing_feature = False
        for name in selected_names:
            value = _finite_float(features.get(name))
            if value is None:
                missing_feature = True
                break
            numeric_features[str(name)] = float(value)
        if missing_feature:
            continue
        rows.append(
            MlTrainingRow(
                timestamp=_datetime_from_ms(timestamp_ms),
                pair=payload_pair,
                features=numeric_features,
                target=target,
            )
        )
    return tuple(rows)


def run_bml_label_factory(request: BmlLabelFactoryRequest) -> BmlLabelFactoryResult:
    output_root = request.output_root.resolve()
    _LOGGER.info("b_ml.run.started", extra={"workflow_run_id": request.workflow_run_id})
    rows = _build_label_rows(request)
    _LOGGER.info("b_ml.label.computed", extra={"row_count": len(rows)})
    overlap_report = build_training_source_contract_report(
        manifest_root_or_path=None,
        source_type="A2_FEATURES_PLUS_COUNTERFACTUAL_REPLAY_LABELS",
        train_start=request.train_start or request.start,
        train_end=request.train_end or request.end,
        validation_start=request.validation_start,
        validation_end=request.validation_end,
        backtest_start=request.allowed_backtest_start_after,
    )
    overlap_blocked = ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED in overlap_report.blocker_reasons
    final_verdict = _final_verdict(rows, overlap_blocked=overlap_blocked)
    labels_dir = output_root / "labels"
    reports_dir = output_root / "reports"
    candidates_dir = output_root / "candidates"
    features_dir = output_root / "features"
    docs_dir = output_root / "docs"
    label_store_path = _write_jsonl(labels_dir / BML_LABEL_STORE_DATASET_FILENAME, rows)
    tabular_artifact_manifests: dict[str, dict[str, Any]] = {
        "b_ml_label_store": _write_tabular_mirror_non_blocking(
            rows=rows,
            artifact_name="b_ml_label_store",
            output_dir=labels_dir,
            source_path=label_store_path,
        )
    }
    status_counts = _status_counts(rows)
    eligible_count = status_counts.get(TRAINING_ROW_ELIGIBLE, 0)
    research_count = status_counts.get(TRAINING_ROW_RESEARCH_ONLY, 0)
    blocked_count = status_counts.get(TRAINING_ROW_BLOCKED, 0)
    training_allowed = eligible_count > 0 and final_verdict in {BML_READY_GOVERNED, BML_READY_RESEARCH}
    candidate_map = {
        row.candidate_id: {
            "candidate_id": row.candidate_id,
            "candidate_source": row.candidate_source,
            "pair": row.pair,
            "timeframe": row.timeframe,
            "engine_id": row.engine_id,
            "side": row.side,
            "decision_timestamp_ms": row.decision_timestamp_ms,
        }
        for row in rows
    }
    feature_map = {
        row.candidate_id: {
            "candidate_id": row.candidate_id,
            "decision_timestamp_ms": row.decision_timestamp_ms,
            "feature_values": row.feature_values,
            "feature_provenance": row.feature_provenance,
            "feature_truth_boundary_status": row.feature_truth_boundary_status,
            "feature_usage_policy": row.feature_usage_policy,
            "cost_feature_truth_status": row.cost_feature_truth_status,
        }
        for row in rows
    }
    candidate_rows = list(candidate_map.values())
    feature_rows = list(feature_map.values())
    raw_window_index_rows = [
        {
            "candidate_id": row.candidate_id,
            "pair": row.pair,
            "timeframe": row.timeframe,
            "decision_timestamp_ms": row.decision_timestamp_ms,
            "orderbook_ref": row.raw_window_refs.get("orderbook", "MISSING_IN_ARTIFACT"),
            "trades_ref": row.raw_window_refs.get("trades", "MISSING_IN_ARTIFACT"),
            "ohlcv_ref": row.raw_window_refs.get("ohlcv", "MISSING_IN_ARTIFACT"),
            "status": "RAW_WINDOW_INDEXED_FROM_A2_FEATURE_ROW",
        }
        for row in rows
    ]
    post_window_index_rows = [
        {
            "candidate_id": row.candidate_id,
            "pair": row.pair,
            "timeframe": row.timeframe,
            "decision_timestamp_ms": row.decision_timestamp_ms,
            "horizon": row.horizon,
            "capital_bucket": row.capital_bucket,
            "post_window_ref": row.raw_window_refs.get("post_window", "MISSING_IN_ARTIFACT"),
            "target_row_ref": row.raw_window_refs.get("target_row", "MISSING_IN_ARTIFACT"),
            "post_window_status": row.post_window_status,
        }
        for row in rows
    ]
    audit = {
        "schema_version": "v53.b_ml_training_dataset_audit.v1",
        "generated_at": _now_iso(),
        "run_id": request.workflow_run_id,
        "row_count": len(rows),
        "candidate_count": len(candidate_rows),
        "training_row_eligible_count": eligible_count,
        "training_row_research_only_count": research_count,
        "training_row_blocked_count": blocked_count,
        "feature_leakage_count": sum(
            1
            for row in rows
            if any(warning.startswith("FEATURE_POST_DECISION_LEAKAGE") for warning in row.warnings)
        ),
        "target_policy_mismatch_count": sum(1 for row in rows if row.target_policy != BML_TARGET_POLICY),
        "missing_post_window_count": sum(1 for row in rows if row.label_truth_status == LABEL_BLOCKED_BY_MISSING_POST_WINDOW),
        "missing_book_count": sum(1 for row in rows if row.label_truth_status == LABEL_BLOCKED_BY_MISSING_BOOK),
        "cost_aware_label_count": sum(1 for row in rows if row.label_truth_status == LABEL_COUNTERFACTUAL_COST_AWARE),
        "execution_aware_partial_label_count": sum(1 for row in rows if row.label_truth_status == LABEL_COUNTERFACTUAL_EXECUTION_AWARE_PARTIAL),
        "proxy_label_count": sum(1 for row in rows if row.label_truth_status == LABEL_RESEARCH_ONLY_PROXY_COST),
        "feature_truth_boundary_status_counts": _count_values(
            row.feature_truth_boundary_status for row in rows
        ),
        "cost_feature_truth_status_counts": _count_values(
            row.cost_feature_truth_status for row in rows
        ),
        "feature_to_label_truth_promotion_blocked_count": sum(
            1
            for row in rows
            if row.cost_feature_truth_status
            in {
                A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH,
                A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH,
            }
        ),
        "train_eval_overlap_status": overlap_report.status,
        "train_eval_overlap_blocked": overlap_blocked,
        "target_policy_declared": request.target_policy,
        "target_policy_actual": BML_TARGET_POLICY,
        "training_allowed": training_allowed,
        "scientifically_valid_for_training": eligible_count > 0 and not overlap_blocked,
        "scientifically_valid_for_promotion": False,
        "final_verdict": final_verdict,
    }
    event_rows = (
        {
            "event": "b_ml.run.started",
            "workflow_run_id": request.workflow_run_id,
            "candidate_sampler_mode": request.candidate_sampler_mode,
        },
        {
            "event": "b_ml.a2_root.validated",
            "a2_run_root": str(request.a2_run_root.resolve()),
        },
        {
            "event": "b_ml.feature_grounding.loaded",
            "feature_names": list(request.feature_names),
        },
        {
            "event": "b_ml.candidate_sampler.started",
            "candidate_sampler_mode": request.candidate_sampler_mode,
        },
        {
            "event": "b_ml.candidate_sampler.completed",
            "candidate_count": len(candidate_rows),
        },
        {
            "event": "b_ml.raw_window.extracted",
            "raw_window_count": len(raw_window_index_rows),
            "source": "A2_FEATURE_ROW_INDEX",
        },
        {
            "event": "b_ml.post_window.extracted",
            "post_window_count": len(post_window_index_rows),
            "source": "A2_FEATURE_ROW_INDEX",
        },
        {
            "event": "b_ml.label.computed",
            "row_count": len(rows),
        },
        {
            "event": "b_ml.row.eligible",
            "count": eligible_count,
        },
        {
            "event": "b_ml.row.research_only",
            "count": research_count,
        },
        {
            "event": "b_ml.row.blocked",
            "count": blocked_count,
        },
        {
            "event": "b_ml.leakage.blocked",
            "count": audit["feature_leakage_count"],
        },
        {
            "event": "b_ml.target_policy.mismatch",
            "count": audit["target_policy_mismatch_count"],
        },
        {
            "event": "b_ml.final_verdict",
            "final_verdict": final_verdict,
        },
    )
    manifest_path = _write_manifest(
        request,
        output_root=output_root,
        rows=rows,
        final_verdict=final_verdict,
    )
    atomic_write_json(output_root / "b_ml_run_request.json", request.model_dump(mode="json"), indent=2)
    atomic_write_json(output_root / "b_ml_run_summary.json", audit, indent=2)
    atomic_write_json(
        candidates_dir / "b_ml_candidate_sampling_report.json",
        {
            "candidate_count": len(candidate_rows),
            "candidate_sampler_mode": request.candidate_sampler_mode,
            "b1_candidate_events_path": (
                None
                if _resolve_b1_candidate_events_path(request) is None
                else str(_resolve_b1_candidate_events_path(request))
            ),
            "requires_b1_candidates": request.candidate_sampler_mode in _BML_REUSE_B1_SAMPLER_MODES,
            "b1_candidate_source_status": (
                "B1_CANDIDATE_SOURCE_READY"
                if _resolve_b1_candidate_events_path(request) is not None
                else "B1_CANDIDATE_SOURCE_NOT_PROVIDED"
            ),
        },
        indent=2,
    )
    candidate_events_path = candidates_dir / "b_ml_candidate_events.jsonl"
    feature_matrix_path = features_dir / "b_ml_feature_matrix.jsonl"
    atomic_write_text(
        candidate_events_path,
        "\n".join(json.dumps(row, sort_keys=True) for row in candidate_rows) + ("\n" if candidate_rows else ""),
    )
    tabular_artifact_manifests["b_ml_candidate_events"] = _write_tabular_mirror_non_blocking(
        rows=candidate_rows,
        artifact_name="b_ml_candidate_events",
        output_dir=candidates_dir,
        source_path=candidate_events_path,
    )
    atomic_write_text(
        feature_matrix_path,
        "\n".join(json.dumps(row, sort_keys=True) for row in feature_rows) + ("\n" if feature_rows else ""),
    )
    tabular_artifact_manifests["b_ml_feature_matrix"] = _write_tabular_mirror_non_blocking(
        rows=feature_rows,
        artifact_name="b_ml_feature_matrix",
        output_dir=features_dir,
        source_path=feature_matrix_path,
    )
    audit["tabular_artifact_manifests"] = {
        name: manifest.get("manifest_path", "")
        for name, manifest in sorted(tabular_artifact_manifests.items())
    }
    audit["tabular_artifact_status_counts"] = _count_values(
        str(manifest.get("status") or "TABULAR_MIRROR_STATUS_UNKNOWN")
        for manifest in tabular_artifact_manifests.values()
    )
    atomic_write_json(features_dir / "b_ml_feature_contract_report.json", {"feature_names": request.feature_names, "row_count": len(feature_rows)}, indent=2)
    atomic_write_json(labels_dir / BML_LABEL_SUMMARY_FILENAME, audit, indent=2)
    atomic_write_json(labels_dir / BML_TARGET_POLICY_REPORT_FILENAME, {"target_policy_declared": request.target_policy, "target_policy_actual": BML_TARGET_POLICY, "target_policy_mismatch_count": 0}, indent=2)
    raw_window_index_path = output_root / "windows" / "raw_window_index.jsonl"
    post_window_index_path = output_root / "windows" / "post_window_index.jsonl"
    atomic_write_text(
        raw_window_index_path,
        "\n".join(json.dumps(row, sort_keys=True) for row in raw_window_index_rows)
        + ("\n" if raw_window_index_rows else ""),
    )
    tabular_artifact_manifests["raw_window_index"] = _write_tabular_mirror_non_blocking(
        rows=raw_window_index_rows,
        artifact_name="raw_window_index",
        output_dir=output_root / "windows",
        source_path=raw_window_index_path,
    )
    atomic_write_text(
        post_window_index_path,
        "\n".join(json.dumps(row, sort_keys=True) for row in post_window_index_rows)
        + ("\n" if post_window_index_rows else ""),
    )
    tabular_artifact_manifests["post_window_index"] = _write_tabular_mirror_non_blocking(
        rows=post_window_index_rows,
        artifact_name="post_window_index",
        output_dir=output_root / "windows",
        source_path=post_window_index_path,
    )
    tabular_artifact_index = {
        "schema_version": "v53.b_ml_tabular_artifact_index.v1",
        "generated_at": _now_iso(),
        "run_id": request.workflow_run_id,
        "artifacts": {
            name: {
                "status": manifest.get("status", "TABULAR_MIRROR_STATUS_UNKNOWN"),
                "storage_format": manifest.get("storage_format", "UNKNOWN"),
                "manifest_path": manifest.get("manifest_path", ""),
                "mirror_path": manifest.get("mirror_path", ""),
                "row_count": manifest.get("row_count", 0),
                "column_count": manifest.get("column_count", 0),
                "source_to_mirror_size_ratio": manifest.get("source_to_mirror_size_ratio"),
            }
            for name, manifest in sorted(tabular_artifact_manifests.items())
        },
    }
    atomic_write_json(
        reports_dir / "b_ml_tabular_artifact_index.json",
        tabular_artifact_index,
        indent=2,
    )
    audit["tabular_artifact_manifests"] = {
        name: manifest.get("manifest_path", "")
        for name, manifest in sorted(tabular_artifact_manifests.items())
    }
    audit["tabular_artifact_status_counts"] = _count_values(
        str(manifest.get("status") or "TABULAR_MIRROR_STATUS_UNKNOWN")
        for manifest in tabular_artifact_manifests.values()
    )
    audit["tabular_artifact_index_path"] = str(
        (reports_dir / "b_ml_tabular_artifact_index.json").resolve()
    )
    atomic_write_json(output_root / "b_ml_run_summary.json", audit, indent=2)
    atomic_write_json(labels_dir / BML_LABEL_SUMMARY_FILENAME, audit, indent=2)
    atomic_write_json(reports_dir / "b_ml_training_dataset_audit.json", audit, indent=2)
    atomic_write_json(reports_dir / "b_ml_training_row_eligibility_report.json", {"rows": [row.model_dump(mode="json") for row in rows]}, indent=2)
    atomic_write_json(reports_dir / "b_ml_feature_label_leakage_report.json", {"feature_leakage_count": audit["feature_leakage_count"]}, indent=2)
    atomic_write_json(reports_dir / "b_ml_cost_label_fidelity_report.json", {"cost_aware_label_count": audit["cost_aware_label_count"], "proxy_label_count": audit["proxy_label_count"]}, indent=2)
    atomic_write_json(
        reports_dir / "b_ml_feature_label_truth_boundary_report.json",
        {
            "schema_version": "v53.b_ml_feature_label_truth_boundary_report.v1",
            "row_count": len(rows),
            "feature_truth_boundary_status_counts": audit[
                "feature_truth_boundary_status_counts"
            ],
            "cost_feature_truth_status_counts": audit[
                "cost_feature_truth_status_counts"
            ],
            "feature_to_label_truth_promotion_blocked_count": audit[
                "feature_to_label_truth_promotion_blocked_count"
            ],
            "promotion_allowed": False,
            "status": "FEATURE_LABEL_TRUTH_BOUNDARY_REPORTED",
        },
        indent=2,
    )
    atomic_write_json(reports_dir / "b_ml_train_eval_overlap_report.json", overlap_report.model_dump(mode="json"), indent=2)
    atomic_write_json(reports_dir / "b_ml_final_verdict.json", audit, indent=2)
    atomic_write_text(
        reports_dir / BML_EVENT_LOG_FILENAME,
        "\n".join(json.dumps(row, sort_keys=True) for row in event_rows) + "\n",
    )
    _LOGGER.info("b_ml.final_verdict", extra={"final_verdict": final_verdict})
    docs_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        docs_dir / "B_ML_TRAINING_DATASET_AUDIT.md",
        "# B_ML Training Dataset Audit\n\n"
        f"Final verdict: `{final_verdict}`\n\n"
        "This dataset is for ML training research only. It is not a profitability backtest.\n",
    )
    return BmlLabelFactoryResult(
        status=final_verdict,
        manifest_path=str(manifest_path),
        label_store_path=str(label_store_path),
        audit_report_path=str(reports_dir / "b_ml_training_dataset_audit.json"),
        row_count=len(rows),
        training_row_eligible_count=eligible_count,
        training_row_research_only_count=research_count,
        training_row_blocked_count=blocked_count,
        final_verdict=final_verdict,
    )


__all__ = [
    "BML_TARGET_POLICY",
    "BML_LABEL_STORE_DATASET_FILENAME",
    "BML_LABEL_SUMMARY_FILENAME",
    "BML_TARGET_POLICY_REPORT_FILENAME",
    "BmlLabelFactoryRequest",
    "BmlLabelFactoryResult",
    "BmlLabelStoreRow",
    "project_bml_rows_to_ml_training_rows",
    "run_bml_label_factory",
]
