"""Typed contracts for the canonical raw -> bronze -> silver -> gold data rail."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class RawMarketFileManifest(BaseModel, frozen=True):
    """One typed raw-market file manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    source_exchange: str = Field(default="bybit", min_length=1)
    market_type: str = Field(default="spot", min_length=1)
    symbol: str = Field(..., min_length=1)
    source_type: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    format: str = Field(default="csv", min_length=1)
    start_timestamp_ms: int | None = Field(default=None, ge=0)
    end_timestamp_ms: int | None = Field(default=None, ge=0)
    row_count: int = Field(default=0, ge=0)
    file_size_bytes: int = Field(default=0, ge=0)
    sha256: str | None = None
    compression: str = Field(default="none", min_length=1)
    created_at: datetime | None = None
    source_status: str = Field(default="RAW_FILE_MISSING", min_length=1)
    artifact_hash: str | None = None


class BronzeMarketIndexManifest(BaseModel, frozen=True):
    """Aggregated bronze index summary across raw manifests."""

    schema_version: str = Field(default="v1", min_length=1)
    exchange: str = Field(default="bybit", min_length=1)
    market_type: str = Field(default="spot", min_length=1)
    symbol: str = Field(..., min_length=1)
    coverage_start_ms: int | None = Field(default=None, ge=0)
    coverage_end_ms: int | None = Field(default=None, ge=0)
    source_files_count: int = Field(default=0, ge=0)
    source_types_present: tuple[str, ...] = ()
    source_types_missing: tuple[str, ...] = ()
    gap_count: int = Field(default=0, ge=0)
    largest_gap_ms: int = Field(default=0, ge=0)
    duplicate_timestamp_count: int = Field(default=0, ge=0)
    out_of_order_count: int = Field(default=0, ge=0)
    index_status: str = Field(default="BRONZE_INDEX_BLOCKED_BY_MISSING_RAW", min_length=1)
    source_file_refs: tuple[str, ...] = ()
    artifact_hash: str | None = None


class SilverSynchronizedMarketManifest(BaseModel, frozen=True):
    """Typed silver synchronization truth surface."""

    schema_version: str = Field(default="v1", min_length=1)
    exchange: str = Field(default="bybit", min_length=1)
    market_type: str = Field(default="spot", min_length=1)
    symbol: str = Field(..., min_length=1)
    coverage_start_ms: int | None = Field(default=None, ge=0)
    coverage_end_ms: int | None = Field(default=None, ge=0)
    trades_status: str = "TRADES_NOT_PROVEN"
    orderbook_snapshot_status: str = "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    orderbook_delta_status: str = "ORDERBOOK_DELTA_NOT_PROVEN"
    ohlcv_status: str = "OHLCV_NOT_PROVEN"
    depth20_status: str = "DEPTH20_NOT_PROVEN"
    timestamp_alignment_status: str = "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
    book_trade_alignment_status: str = "BOOK_TRADE_ALIGNMENT_NOT_PROVEN"
    stale_book_count: int = Field(default=0, ge=0)
    missing_book_count: int = Field(default=0, ge=0)
    missing_trade_count: int = Field(default=0, ge=0)
    missing_ohlcv_count: int = Field(default=0, ge=0)
    rows_written: int = Field(default=0, ge=0)
    silver_sync_status: str = "SILVER_SYNC_BLOCKED_BY_MISSING_RAW"
    blocker_codes: tuple[str, ...] = ()
    source_file_refs: tuple[str, ...] = ()
    artifact_hash: str | None = None


class GoldMicrostructureFeatureManifest(BaseModel, frozen=True):
    """Typed gold microstructure feature manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    symbol_scope: tuple[str, ...] = ()
    timeframe_scope: tuple[str, ...] = ()
    feature_row_count: int = Field(default=0, ge=0)
    feature_groups_declared: tuple[str, ...] = ()
    feature_groups_generated: tuple[str, ...] = ()
    feature_groups_missing: tuple[str, ...] = ()
    feature_timestamp_policy: str = "FEATURE_TIMESTAMP_POLICY_NOT_PROVEN"
    max_feature_timestamp_ms: int | None = Field(default=None, ge=0)
    min_feature_timestamp_ms: int | None = Field(default=None, ge=0)
    feature_hash: str | None = None
    feature_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    output_paths: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    modules_used: tuple[str, ...] = ()
    quant_equation_refs: tuple[str, ...] = ()
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


class ExpectedEdgeFeatureManifest(BaseModel, frozen=True):
    """IA Lab dataset export manifest built from the governed gold store."""

    schema_version: str = Field(default="v1", min_length=1)
    dataset_id: str = Field(..., min_length=1)
    status: str = "EXPECTED_EDGE_FEATURE_DATASET_BLOCKED"
    row_count: int = Field(default=0, ge=0)
    pair_scope: tuple[str, ...] = ()
    timeframe_scope: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    feature_groups_generated: tuple[str, ...] = ()
    feature_groups_missing: tuple[str, ...] = ()
    feature_hash: str | None = None
    dataset_hash: str | None = None
    feature_timestamp_policy: str = "FEATURE_TIMESTAMP_POLICY_NOT_PROVEN"
    purge_window_minutes: int = Field(default=0, ge=0)
    embargo_window_minutes: int = Field(default=0, ge=0)
    source_refs_count: int = Field(default=0, ge=0)
    output_path: str = ""
    source_gold_feature_refs: tuple[str, ...] = ()
    source_silver_index_ref: str = ""
    modules_used: tuple[str, ...] = ()
    quant_equation_refs: tuple[str, ...] = ()
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


class BacktestReplayDatasetManifest(BaseModel, frozen=True):
    """Backtest/replay consumer compatibility manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    status: str = "BACKTEST_REPLAY_DATASET_NOT_READY"
    pair_scope: tuple[str, ...] = ()
    timeframe_scope: tuple[str, ...] = ()
    candidate_feature_snapshot_refs: tuple[str, ...] = ()
    raw_window_refs: tuple[str, ...] = ()
    silver_index_ref: str = ""
    gold_feature_refs: tuple[str, ...] = ()
    venue_metadata_refs: tuple[str, ...] = ()
    feature_hash: str | None = None
    replay_compatibility_status: str = "FEATURE_PARITY_NOT_PROVEN"
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


class RuntimeFeatureParityManifest(BaseModel, frozen=True):
    """Reserved runtime/shadow parity placeholder contract."""

    schema_version: str = Field(default="v1", min_length=1)
    status: str = "RUNTIME_PARITY_NOT_PROVEN"
    source_gold_feature_refs: tuple[str, ...] = ()
    source_silver_index_ref: str = ""
    feature_hash: str | None = None
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


class DataScienceQualityReport(BaseModel, frozen=True):
    """Anti-leakage and deterministic dataset quality report."""

    schema_version: str = Field(default="v1", min_length=1)
    status: str = "DATA_SCIENCE_BLOCKED_BY_MISSING_SOURCE_REFS"
    feature_timestamp_aligned: str = "FEATURE_TIMESTAMP_ALIGNED_NOT_PROVEN"
    no_future_features: str = "NO_FUTURE_FEATURES_NOT_PROVEN"
    label_window_after_decision: str = "LABEL_WINDOW_AFTER_DECISION_NOT_PROVEN"
    random_split_forbidden: str = "RANDOM_SPLIT_FORBIDDEN_NOT_PROVEN"
    purge_window_declared: str = "PURGE_WINDOW_NOT_DECLARED"
    embargo_window_declared: str = "EMBARGO_WINDOW_NOT_DECLARED"
    feature_hash_stable: str = "FEATURE_HASH_NOT_PROVEN"
    dataset_hash_stable: str = "DATASET_HASH_NOT_PROVEN"
    source_refs_non_empty: str = "SOURCE_REFS_NON_EMPTY_NOT_PROVEN"
    feature_hash: str | None = None
    dataset_hash: str | None = None
    row_count: int = Field(default=0, ge=0)
    source_refs_count: int = Field(default=0, ge=0)
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


def finalize_hashed_model(model: BaseModel) -> BaseModel:
    """Return one model copy with deterministic artifact hash and UTC timestamps."""

    payload = model.model_dump(mode="json")
    if "created_at" in payload and payload["created_at"] is None:
        payload["created_at"] = datetime.now(tz=UTC)
    if "artifact_hash" in payload:
        payload["artifact_hash"] = deterministic_payload_hash(payload)
    return model.__class__.model_validate(payload)


__all__ = [
    "BacktestReplayDatasetManifest",
    "BronzeMarketIndexManifest",
    "DataScienceQualityReport",
    "ExpectedEdgeFeatureManifest",
    "GoldMicrostructureFeatureManifest",
    "RawMarketFileManifest",
    "RuntimeFeatureParityManifest",
    "SilverSynchronizedMarketManifest",
    "finalize_hashed_model",
]
