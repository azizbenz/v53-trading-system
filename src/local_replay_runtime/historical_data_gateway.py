"""Historical dataset loader for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    CANONICAL_PHYSICS_FEATURE_DICTIONARY,
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
    CANONICAL_TRANSFORM_WHITELIST,
    FeatureLineageLock,
    FeatureLineageRecord,
    PhysicsFeatureFamily,
    TransformWhitelistId,
    TransformWhitelistLock,
    canonical_feature_ids,
    canonical_transform_ids,
    validate_feature_lineage_lock,
    validate_transform_whitelist_lock,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState

FeatureScalar = str | int | float | bool
ReplayRecord = dict[str, object]
FeatureBridgePayload = dict[str, object]


class HistoricalReplayOpportunity(BaseModel, frozen=True):
    """Single historical opportunity consumed by the local replay adapters."""

    opportunity_id: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    close_price: float = Field(default=0.0, ge=0.0)
    regime: str = ""
    raw_score: float = 0.0
    penalized_score: float | None = None
    final_score: float | None = None
    expected_edge_bps: float = 0.0
    spread_bps: float = Field(default=0.0, ge=0.0)
    # Audit 2026-05-14 P3-A wiring : tier-aware spread provenance.
    # Valeurs : "MEASURED_FROM_BOOK_SNAPSHOT", "MEASURED_FROM_BOOK_RECONSTRUCTION",
    # "MEASURED_FROM_BOOK_SNAPSHOT_STALE" (audit-only, gate reste actif),
    # "DEFAULT_BY_BOOK_STATUS", ou "" (legacy/missing). Consomme par
    # _build_row_component_sources pour determiner spread_model_source au
    # manifest level.
    spread_provenance: str = ""
    slippage_bps: float = Field(default=0.0, ge=0.0)
    latency_penalty_bps: float = Field(default=0.0, ge=0.0)
    fill_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    side: str = "buy"
    maker_fee_rate: float | None = Field(default=None, ge=0.0)
    taker_fee_rate: float | None = Field(default=None, ge=0.0)
    tick_size: float | None = Field(default=None, gt=0.0)
    step_size: float | None = Field(default=None, gt=0.0)
    min_notional: float | None = Field(default=None, ge=0.0)
    mid_price: float | None = Field(default=None, gt=0.0)
    post_fill_mid_price: float | None = Field(default=None, gt=0.0)
    adverse_selection_delay_s: float | None = Field(default=None, gt=0.0)
    fill_prices: tuple[float, ...] = ()
    fill_quantities: tuple[float, ...] = ()
    target_decision_state: DecisionState | None = None
    production_decision_state: DecisionState | None = None
    production_final_score: float | None = None
    production_expected_cost: float | None = None
    book_depth_levels: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    book_depth_snapshot_count: int | None = Field(default=None, ge=0)
    book_depth_event_count: int | None = Field(default=None, ge=0)
    book_depth_missing_count: int | None = Field(default=None, ge=0)
    book_depth_staleness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    hard_block_reasons: tuple[str, ...] = ()
    ranking_position: int = Field(default=0, ge=0)
    candidate_size: float = Field(default=0.0, ge=0.0)
    final_size: float = Field(default=0.0, ge=0.0)
    tier: str = ""
    gross_return_bps: float = 0.0
    primary_reason: str = ""
    feature_values: dict[str, FeatureScalar] = {}
    shared_core_match: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value

        data = dict(value)
        if data.get("penalized_score") is None:
            data["penalized_score"] = data.get("raw_score", 0.0)
        if data.get("final_score") is None:
            data["final_score"] = data.get("penalized_score", data.get("raw_score", 0.0))
        if isinstance(data.get("hard_block_reasons"), str):
            raw_reasons = data["hard_block_reasons"].strip()
            data["hard_block_reasons"] = (
                tuple(part for part in raw_reasons.split("|") if part)
                if raw_reasons
                else ()
            )
        if isinstance(data.get("feature_values"), str):
            raw_features = data["feature_values"].strip()
            data["feature_values"] = json.loads(raw_features) if raw_features else {}
        for field_name in ("fill_prices", "fill_quantities"):
            if isinstance(data.get(field_name), str):
                raw_items = data[field_name].strip()
                data[field_name] = tuple(
                    float(item)
                    for item in (json.loads(raw_items) if raw_items else [])
                )
        return data

    @model_validator(mode="after")
    def validate_sizes(self) -> "HistoricalReplayOpportunity":
        if self.candidate_size > 0.0 and self.final_size > self.candidate_size:
            raise ValueError(
                "HistoricalReplayOpportunity final_size must stay <= candidate_size"
            )
        if self.fill_prices and self.fill_quantities and (
            len(self.fill_prices) != len(self.fill_quantities)
        ):
            raise ValueError(
                "HistoricalReplayOpportunity fill_prices and fill_quantities must align"
            )
        return self


class HistoricalReplayDataset(BaseModel, frozen=True):
    """Normalized historical dataset used by the replay adapters."""

    dataset_id: str = Field(..., min_length=1)
    source_path: str = Field(..., min_length=1)
    source: str = Field(default="local_dataset", min_length=1)
    rows: tuple[HistoricalReplayOpportunity, ...] = Field(..., min_length=1)
    record_count: int = Field(..., ge=1)
    pair_scope: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    feature_keys: tuple[str, ...] = ()
    start_timestamp_ms: int = Field(..., ge=0)
    end_timestamp_ms: int = Field(..., ge=0)
    shared_core_match: bool = True

    @classmethod
    def from_records(
        cls,
        *,
        dataset_id: str,
        source_path: str,
        records: tuple[HistoricalReplayOpportunity | ReplayRecord, ...]
        | list[HistoricalReplayOpportunity | ReplayRecord],
        source: str = "local_dataset",
    ) -> "HistoricalReplayDataset":
        normalized_rows = tuple(
            record
            if isinstance(record, HistoricalReplayOpportunity)
            else HistoricalReplayOpportunity.model_validate(record)
            for record in records
        )
        if not normalized_rows:
            raise ValueError("HistoricalReplayDataset requires at least one record")
        ordered_rows = tuple(
            sorted(normalized_rows, key=lambda row: (row.timestamp_ms, row.opportunity_id))
        )
        return cls(
            dataset_id=dataset_id,
            source_path=source_path,
            source=source,
            rows=ordered_rows,
            record_count=len(ordered_rows),
            pair_scope=tuple(sorted({row.pair for row in ordered_rows})),
            engine_scope=tuple(sorted({row.engine_id for row in ordered_rows})),
            feature_keys=tuple(
                sorted(
                    {
                        key
                        for row in ordered_rows
                        for key in row.feature_values
                    }
                )
            ),
            start_timestamp_ms=ordered_rows[0].timestamp_ms,
            end_timestamp_ms=ordered_rows[-1].timestamp_ms,
            shared_core_match=all(row.shared_core_match for row in ordered_rows),
        )

    @property
    def rows_with_features(self) -> int:
        return sum(1 for row in self.rows if row.feature_values)

    @property
    def missing_feature_rows(self) -> int:
        return self.record_count - self.rows_with_features

    @model_validator(mode="after")
    def validate_dataset(self) -> "HistoricalReplayDataset":
        if self.record_count != len(self.rows):
            raise ValueError("HistoricalReplayDataset record_count must match rows")
        if self.end_timestamp_ms < self.start_timestamp_ms:
            raise ValueError(
                "HistoricalReplayDataset end_timestamp_ms must be >= start_timestamp_ms"
            )
        return self


def _load_json_records(dataset_path: Path) -> tuple[ReplayRecord, ...]:
    raw = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, dict))
    if isinstance(raw, dict):
        records = raw.get("records", ())
        if isinstance(records, list):
            return tuple(item for item in records if isinstance(item, dict))
    raise ValueError(f"Unsupported JSON dataset shape in {dataset_path}")


def _load_jsonl_records(dataset_path: Path) -> tuple[ReplayRecord, ...]:
    records: list[ReplayRecord] = []
    for line in dataset_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(f"Historical JSONL rows must be objects in {dataset_path}")
        records.append(payload)
    return tuple(records)


def _load_csv_records(dataset_path: Path) -> tuple[ReplayRecord, ...]:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(dict(row) for row in reader)


def load_historical_replay_dataset(
    dataset_path: Path,
    *,
    dataset_id: str | None = None,
    source: str = "local_dataset",
) -> HistoricalReplayDataset:
    """Load a local replay dataset from JSON, JSONL, or CSV."""

    resolved = dataset_path.resolve()
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        records = _load_json_records(resolved)
    elif suffix == ".jsonl":
        records = _load_jsonl_records(resolved)
    elif suffix == ".csv":
        records = _load_csv_records(resolved)
    else:
        raise ValueError(
            "Historical replay datasets must use .json, .jsonl, or .csv"
        )
    normalized_dataset_id = dataset_id or resolved.stem.replace(" ", "_")
    return HistoricalReplayDataset.from_records(
        dataset_id=normalized_dataset_id,
        source_path=str(resolved),
        records=records,
        source=source,
    )


def build_feature_bridge_payload(
    dataset: HistoricalReplayDataset,
    *,
    feature_lineage_lock: FeatureLineageLock | None = None,
    transform_whitelist_lock: TransformWhitelistLock | None = None,
    auto_materialize_feature_locks: bool = False,
) -> FeatureBridgePayload:
    """Summarize whether the historical dataset materialized the feature bridge."""

    bridge_status = (
        "ok"
        if dataset.shared_core_match and dataset.missing_feature_rows == 0
        else "warning"
    )
    resolved_feature_lineage_lock = feature_lineage_lock
    resolved_transform_whitelist_lock = transform_whitelist_lock
    if resolved_feature_lineage_lock is None and auto_materialize_feature_locks:
        (
            resolved_feature_lineage_lock,
            resolved_transform_whitelist_lock,
        ) = _materialize_feature_locks(dataset.feature_keys)
    elif (
        resolved_feature_lineage_lock is not None
        and resolved_transform_whitelist_lock is None
    ):
        resolved_transform_whitelist_lock = _build_transform_whitelist_lock_from_lineage(
            resolved_feature_lineage_lock
        )
    lineage_reasons = validate_feature_lineage_lock(
        dataset.feature_keys,
        resolved_feature_lineage_lock,
    )
    transform_ids = _transform_ids_for_feature_keys(dataset.feature_keys)
    transform_reasons = validate_transform_whitelist_lock(
        transform_ids,
        resolved_transform_whitelist_lock,
    )
    canonical_ids = set(canonical_feature_ids())
    recognized_feature_keys = tuple(
        key for key in dataset.feature_keys if key in canonical_ids
    )
    unrecognized_feature_keys = tuple(
        key for key in dataset.feature_keys if key not in canonical_ids
    )
    return {
        "bridge_status": bridge_status,
        "dataset_id": dataset.dataset_id,
        "source": dataset.source,
        "source_path": dataset.source_path,
        "feature_set_version": CANONICAL_FEATURE_SET_VERSION,
        "transform_set_version": CANONICAL_TRANSFORM_SET_VERSION,
        "canonical_feature_dictionary_size": len(canonical_ids),
        "canonical_transform_whitelist_size": len(CANONICAL_TRANSFORM_WHITELIST),
        "record_count": dataset.record_count,
        "pairs": list(dataset.pair_scope),
        "engines": list(dataset.engine_scope),
        "feature_keys": list(dataset.feature_keys),
        "recognized_feature_keys": list(recognized_feature_keys),
        "unrecognized_feature_keys": list(unrecognized_feature_keys),
        "rows_with_features": dataset.rows_with_features,
        "missing_feature_rows": dataset.missing_feature_rows,
        "shared_core_match": dataset.shared_core_match,
        "lineage_lock_present": resolved_feature_lineage_lock is not None,
        "lineage_lock_status": "ok" if not lineage_reasons else "missing",
        "lineage_lock_reasons": list(lineage_reasons),
        "feature_lineage_lock": (
            resolved_feature_lineage_lock.model_dump(mode="json")
            if resolved_feature_lineage_lock is not None
            else None
        ),
        "transform_whitelist_present": resolved_transform_whitelist_lock is not None,
        "transform_whitelist_status": "ok" if not transform_reasons else "missing",
        "transform_whitelist_reasons": list(transform_reasons),
        "transform_whitelist_lock": (
            resolved_transform_whitelist_lock.model_dump(mode="json")
            if resolved_transform_whitelist_lock is not None
            else None
        ),
        "path_materialized": dataset.rows_with_features > 0,
        "feature_to_engine_path": "historical_prices -> computed_features -> engines -> scoring",
    }


def _materialize_feature_locks(
    feature_keys: tuple[str, ...],
) -> tuple[FeatureLineageLock, TransformWhitelistLock]:
    records = tuple(
        _build_feature_lineage_record(feature_id)
        for feature_id in feature_keys
    )
    feature_lineage_lock = FeatureLineageLock(
        feature_set_version=CANONICAL_FEATURE_SET_VERSION,
        transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
        records=records,
    )
    return (
        feature_lineage_lock,
        _build_transform_whitelist_lock_from_lineage(feature_lineage_lock),
    )


def _build_transform_whitelist_lock_from_lineage(
    feature_lineage_lock: FeatureLineageLock,
) -> TransformWhitelistLock:
    transform_ids = tuple(
        dict.fromkeys(
            transform_id
            for record in feature_lineage_lock.records
            for transform_id in record.transform_ids
        )
    ) or canonical_transform_ids()
    return TransformWhitelistLock(
        transform_set_version=feature_lineage_lock.transform_set_version,
        allowed_transform_ids=transform_ids,
    )


def _build_feature_lineage_record(feature_id: str) -> FeatureLineageRecord:
    canonical_entry = CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(feature_id)
    if canonical_entry is not None:
        return FeatureLineageRecord(
            feature_id=feature_id,
            family=canonical_entry.family,
            source_inputs=("historical_prices",),
            transform_ids=canonical_entry.default_transform_ids,
            equation_id=canonical_entry.equation_id,
            feature_set_version=CANONICAL_FEATURE_SET_VERSION,
            transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
        )
    family, transform_ids, source_inputs = _fallback_lineage_spec(feature_id)
    return FeatureLineageRecord(
        feature_id=feature_id,
        family=family,
        source_inputs=source_inputs,
        transform_ids=transform_ids,
        equation_id=f"shadow.live.derived.{feature_id}",
        feature_set_version=CANONICAL_FEATURE_SET_VERSION,
        transform_set_version=CANONICAL_TRANSFORM_SET_VERSION,
    )


def _transform_ids_for_feature_keys(
    feature_keys: tuple[str, ...],
) -> tuple[TransformWhitelistId, ...]:
    return tuple(
        dict.fromkeys(
            transform_id
            for feature_id in feature_keys
            for transform_id in _lineage_transform_ids(feature_id)
        )
    )


def _lineage_transform_ids(feature_id: str) -> tuple[TransformWhitelistId, ...]:
    canonical_entry = CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(feature_id)
    if canonical_entry is not None:
        return canonical_entry.default_transform_ids
    _, transform_ids, _ = _fallback_lineage_spec(feature_id)
    return transform_ids


def _fallback_lineage_spec(
    feature_id: str,
) -> tuple[
    PhysicsFeatureFamily,
    tuple[TransformWhitelistId, ...],
    tuple[str, ...],
]:
    normalized = feature_id.strip().lower()
    if normalized.startswith("snapshot_"):
        source_inputs = ("snapshot_event",)
    elif normalized.startswith("depth_"):
        source_inputs = ("depth_event",)
    elif normalized.startswith("trade_"):
        source_inputs = ("trade_event",)
    elif normalized.startswith("kline_"):
        source_inputs = ("kline_event",)
    else:
        source_inputs = ("route_hint_feature_values",)

    if "spread" in normalized:
        return (
            PhysicsFeatureFamily.SPREAD_REGIME,
            (TransformWhitelistId.CLIP01,),
            source_inputs,
        )
    if "volume" in normalized or "notional" in normalized or "quantity" in normalized:
        return (
            PhysicsFeatureFamily.VOLUME_PROFILE,
            (TransformWhitelistId.CAPRATIO,),
            source_inputs,
        )
    if "maker" in normalized or "imbalance" in normalized:
        return (
            PhysicsFeatureFamily.ORDER_FLOW_IMBALANCE,
            (TransformWhitelistId.ZPLUS,),
            source_inputs,
        )
    if "price" in normalized or "bid" in normalized or "ask" in normalized:
        return (
            PhysicsFeatureFamily.MICROPRICE_DEVIATION,
            (TransformWhitelistId.CAPRATIO,),
            source_inputs,
        )
    return (
        PhysicsFeatureFamily.REGIME_HURST_CONTEXT_ENRICHMENT,
        (TransformWhitelistId.CLIP01,),
        source_inputs,
    )


__all__ = [
    "HistoricalReplayOpportunity",
    "HistoricalReplayDataset",
    "load_historical_replay_dataset",
    "build_feature_bridge_payload",
]
