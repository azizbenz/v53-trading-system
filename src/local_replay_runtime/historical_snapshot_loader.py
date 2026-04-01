"""Historical market snapshot loader for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel, Field, model_validator

from interface_contracts import DepthEvent, KlineEvent, SnapshotEvent, TradeEvent
from meta_minimal.dtr_core.decision_state_encoder import DecisionState

from local_replay_runtime.historical_data_gateway import FeatureScalar

ReplayMarketEvent: TypeAlias = SnapshotEvent | DepthEvent | KlineEvent | TradeEvent


class ReplayRouteHint(BaseModel, frozen=True):
    """Thin routing metadata carried alongside raw historical market events."""

    route_id: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    raw_score: float = 0.0
    penalized_score: float | None = None
    final_score: float | None = None
    expected_edge_bps: float = 0.0
    slippage_bps: float | None = None
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
    regime: str = ""
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


class HistoricalMarketEventEnvelope(BaseModel, frozen=True):
    """Single typed historical event plus the route hint used by local replay."""

    event_type: str = Field(..., min_length=1)
    event: ReplayMarketEvent
    route_hint: ReplayRouteHint

    @property
    def timestamp_ms(self) -> int:
        return self.event.timestamp_ms

    @property
    def pair(self) -> str:
        return self.event.pair

    @property
    def route_id(self) -> str:
        return self.route_hint.route_id

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value

        data = dict(value)
        event_type = str(data.get("event_type", "")).strip().lower()
        payload = data.get("event", data.get("payload"))
        route_hint_payload = data.get("route_hint", {})
        if not route_hint_payload and "route_id" in data:
            route_hint_payload = {"route_id": data["route_id"]}
        elif "route_id" in data and isinstance(route_hint_payload, dict):
            route_hint_payload = {"route_id": data["route_id"], **route_hint_payload}
        data["event_type"] = event_type
        data["event"] = _parse_market_event(event_type, payload)
        data["route_hint"] = ReplayRouteHint.model_validate(route_hint_payload)
        return data


class HistoricalSnapshotBatch(BaseModel, frozen=True):
    """Typed batch of raw historical market events used by the local replay adapters."""

    source_path: str = Field(..., min_length=1)
    source: str = Field(default="historical_snapshot_batch", min_length=1)
    events: tuple[HistoricalMarketEventEnvelope, ...] = Field(..., min_length=1)
    event_count: int = Field(..., ge=1)
    pair_scope: tuple[str, ...] = ()
    route_scope: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    start_timestamp_ms: int = Field(..., ge=0)
    end_timestamp_ms: int = Field(..., ge=0)

    @classmethod
    def from_records(
        cls,
        *,
        source_path: str,
        records: tuple[HistoricalMarketEventEnvelope | dict[str, Any], ...]
        | list[HistoricalMarketEventEnvelope | dict[str, Any]],
        source: str = "historical_snapshot_batch",
    ) -> "HistoricalSnapshotBatch":
        events = tuple(
            item
            if isinstance(item, HistoricalMarketEventEnvelope)
            else HistoricalMarketEventEnvelope.model_validate(item)
            for item in records
        )
        if not events:
            raise ValueError("HistoricalSnapshotBatch requires at least one event")
        ordered = tuple(
            sorted(
                events,
                key=lambda item: (item.timestamp_ms, item.route_id, item.event_type, item.pair),
            )
        )
        return cls(
            source_path=source_path,
            source=source,
            events=ordered,
            event_count=len(ordered),
            pair_scope=tuple(sorted({item.pair for item in ordered})),
            route_scope=tuple(sorted({item.route_id for item in ordered})),
            event_types=tuple(sorted({item.event_type for item in ordered})),
            start_timestamp_ms=ordered[0].timestamp_ms,
            end_timestamp_ms=ordered[-1].timestamp_ms,
        )

    @model_validator(mode="after")
    def validate_batch(self) -> "HistoricalSnapshotBatch":
        if self.event_count != len(self.events):
            raise ValueError("HistoricalSnapshotBatch event_count must match events")
        if self.end_timestamp_ms < self.start_timestamp_ms:
            raise ValueError(
                "HistoricalSnapshotBatch end_timestamp_ms must be >= start_timestamp_ms"
            )
        return self


def _parse_market_event(event_type: str, payload: Any) -> ReplayMarketEvent:
    if isinstance(payload, (SnapshotEvent, DepthEvent, KlineEvent, TradeEvent)):
        return payload
    if not isinstance(payload, dict):
        raise ValueError(f"Historical market event payload must be an object for {event_type}")
    lowered = event_type.lower()
    if lowered == "snapshot":
        return SnapshotEvent.model_validate(payload)
    if lowered == "depth":
        return DepthEvent.model_validate(payload)
    if lowered == "kline":
        return KlineEvent.model_validate(payload)
    if lowered == "trade":
        return TradeEvent.model_validate(payload)
    raise ValueError(f"Unsupported historical event_type: {event_type}")


def _load_json_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
    raw = json.loads(dataset_path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, dict))
    if isinstance(raw, dict):
        records = raw.get("records", ())
        if isinstance(records, list):
            return tuple(item for item in records if isinstance(item, dict))
    raise ValueError(f"Unsupported historical snapshot JSON shape in {dataset_path}")


def _load_jsonl_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(f"Historical snapshot JSONL rows must be objects in {dataset_path}")
        records.append(payload)
    return tuple(records)


def _load_csv_records(dataset_path: Path) -> tuple[dict[str, Any], ...]:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        records: list[dict[str, Any]] = []
        for row in reader:
            normalized = dict(row)
            for key in ("event", "payload", "route_hint"):
                if key in normalized and isinstance(normalized[key], str):
                    raw = normalized[key].strip()
                    normalized[key] = json.loads(raw) if raw else {}
            records.append(normalized)
    return tuple(records)


def load_historical_snapshot_batch(
    snapshot_path: Path,
    *,
    source: str = "historical_snapshot_batch",
) -> HistoricalSnapshotBatch:
    """Load raw historical market events from JSON, JSONL, or CSV."""

    resolved = snapshot_path.resolve()
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        records = _load_json_records(resolved)
    elif suffix == ".jsonl":
        records = _load_jsonl_records(resolved)
    elif suffix == ".csv":
        records = _load_csv_records(resolved)
    else:
        raise ValueError(
            "Historical snapshot batches must use .json, .jsonl, or .csv"
        )
    return HistoricalSnapshotBatch.from_records(
        source_path=str(resolved),
        records=records,
        source=source,
    )


__all__ = [
    "ReplayRouteHint",
    "HistoricalMarketEventEnvelope",
    "HistoricalSnapshotBatch",
    "load_historical_snapshot_batch",
]
