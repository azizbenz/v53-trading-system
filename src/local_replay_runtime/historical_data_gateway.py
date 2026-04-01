"""Historical dataset loader for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from meta_minimal.dtr_core.decision_state_encoder import DecisionState

FeatureScalar = str | int | float | bool


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
    slippage_bps: float = Field(default=0.0, ge=0.0)
    latency_penalty_bps: float = Field(default=0.0, ge=0.0)
    fill_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    target_decision_state: DecisionState | None = None
    production_decision_state: DecisionState | None = None
    production_final_score: float | None = None
    production_expected_cost: float | None = None
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
    def normalize_input(cls, value: Any) -> Any:
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
        return data

    @model_validator(mode="after")
    def validate_sizes(self) -> "HistoricalReplayOpportunity":
        if self.candidate_size > 0.0 and self.final_size > self.candidate_size:
            raise ValueError(
                "HistoricalReplayOpportunity final_size must stay <= candidate_size"
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
        records: tuple[HistoricalReplayOpportunity | dict[str, Any], ...]
        | list[HistoricalReplayOpportunity | dict[str, Any]],
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


def _load_json_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
    raw = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, dict))
    if isinstance(raw, dict):
        records = raw.get("records", ())
        if isinstance(records, list):
            return tuple(item for item in records if isinstance(item, dict))
    raise ValueError(f"Unsupported JSON dataset shape in {dataset_path}")


def _load_jsonl_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(f"Historical JSONL rows must be objects in {dataset_path}")
        records.append(payload)
    return tuple(records)


def _load_csv_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
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


def build_feature_bridge_payload(dataset: HistoricalReplayDataset) -> dict[str, Any]:
    """Summarize whether the historical dataset materialized the feature bridge."""

    bridge_status = (
        "ok"
        if dataset.shared_core_match and dataset.missing_feature_rows == 0
        else "warning"
    )
    return {
        "bridge_status": bridge_status,
        "dataset_id": dataset.dataset_id,
        "source": dataset.source,
        "source_path": dataset.source_path,
        "record_count": dataset.record_count,
        "pairs": list(dataset.pair_scope),
        "engines": list(dataset.engine_scope),
        "feature_keys": list(dataset.feature_keys),
        "rows_with_features": dataset.rows_with_features,
        "missing_feature_rows": dataset.missing_feature_rows,
        "shared_core_match": dataset.shared_core_match,
        "path_materialized": dataset.rows_with_features > 0,
        "feature_to_engine_path": "historical_prices -> computed_features -> engines -> scoring",
    }


__all__ = [
    "HistoricalReplayOpportunity",
    "HistoricalReplayDataset",
    "load_historical_replay_dataset",
    "build_feature_bridge_payload",
]
