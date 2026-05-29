"""Typed contracts for Patch 6 Data Factory and first controlled Strategy Ladder runs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from data_backbone.feature_timeframes import DEFAULT_GOLD_TIMEFRAMES
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    normalize_supported_expected_edge_feature_names,
)
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class StrategyLadderRawSource(BaseModel, frozen=True):
    """Resolved or manifest-backed raw source root."""

    schema_version: str = Field(default="v1", min_length=1)
    source_id: str = Field(..., min_length=1)
    root: str = Field(..., min_length=1)
    source_type: str = Field(default="raw", min_length=1)
    exchange: str = Field(default="bybit", min_length=1)
    market_type: str = Field(default="spot", min_length=1)
    data_types: tuple[str, ...] = ()
    priority: int = 0
    enabled: bool = True
    status: str = "RAW_SOURCE_NOT_PROVEN"
    typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    reason_codes: tuple[str, ...] = ()


class StrategyLadderRawSourceReport(BaseModel, frozen=True):
    """Canonical multi-source raw-root report."""

    schema_version: str = Field(default="v1", min_length=1)
    sources: tuple[StrategyLadderRawSource, ...] = ()
    raw_source_manifest_path: str = ""
    raw_source_provenance_status: str = "RAW_SOURCE_PROVENANCE_NOT_PROVEN"
    raw_source_status: str = "RAW_SOURCE_NOT_PROVEN"
    raw_source_typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    requested_pairs: tuple[str, ...] = ()
    detected_pairs: tuple[str, ...] = ()
    source_pair_map: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    pair_inference_sources: dict[str, str] = Field(default_factory=dict)
    pair_mismatch_reason_codes: tuple[str, ...] = ()
    ignored_source_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderRawFileClassification(BaseModel, frozen=True):
    """Detected raw-file shape before normalization."""

    schema_version: str = Field(default="v1", min_length=1)
    source_id: str = Field(..., min_length=1)
    source_root: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    pair: str | None = None
    timeframe: str | None = None
    date: str | None = None
    exchange: str = ""
    market_type: str = ""
    data_type: str = ""
    classification_status: str = "RAW_FILE_NOT_PROVEN"
    timestamp_unit: str | None = None
    timestamp_unit_status: str = "TIMESTAMP_UNIT_NOT_PROVEN"
    schema_status: str = "SCHEMA_NOT_PROVEN"
    input_hash: str | None = None


class StrategyLadderPairCoverage(BaseModel, frozen=True):
    """Per-pair raw/silver availability view."""

    pair: str = Field(..., min_length=1)
    has_trades: bool = False
    has_klines: bool = False
    has_orderbook: bool = False
    has_metadata: bool = False
    trade_date_count: int = Field(default=0, ge=0)
    kline_date_count: int = Field(default=0, ge=0)
    orderbook_date_count: int = Field(default=0, ge=0)
    coverage_start: str = ""
    coverage_end: str = ""
    coverage_status: str = "PAIR_DATA_COVERAGE_NOT_PROVEN"


class StrategyLadderPairUniverseReport(BaseModel, frozen=True):
    """Dynamic pair-universe discovery report."""

    schema_version: str = Field(default="v1", min_length=1)
    requested_pairs: tuple[str, ...] = ()
    discovered_pairs: tuple[str, ...] = ()
    available_pairs: tuple[str, ...] = ()
    missing_pairs: tuple[str, ...] = ()
    pair_data_coverage: tuple[StrategyLadderPairCoverage, ...] = ()
    pair_universe_status: str = "PAIR_UNIVERSE_NOT_PROVEN"
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    source_pair_map: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    pair_inference_sources: dict[str, str] = Field(default_factory=dict)
    pair_mismatch_reason_codes: tuple[str, ...] = ()
    ignored_source_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderSilverIndexEntry(BaseModel, frozen=True):
    """One canonical silver-index row."""

    schema_version: str = Field(default="v1", min_length=1)
    source_id: str = Field(..., min_length=1)
    source_root: str = Field(..., min_length=1)
    source_priority: int = 0
    exchange: str = Field(..., min_length=1)
    market_type: str = Field(..., min_length=1)
    data_type: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    timeframe: str = ""
    date: str = ""
    path: str = Field(..., min_length=1)
    storage_format: str = Field(default="jsonl", min_length=1)
    min_timestamp_ms: int | None = Field(default=None, ge=0)
    max_timestamp_ms: int | None = Field(default=None, ge=0)
    min_seq: int | None = None
    max_seq: int | None = None
    row_count: int = Field(default=0, ge=0)
    file_hash: str = ""
    depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    schema_status: str = "SCHEMA_NOT_PROVEN"
    timestamp_unit: str = ""
    min_trade_id: str = ""
    max_trade_id: str = ""
    side_values_seen: tuple[str, ...] = ()
    duplicate_trade_id_count: int = Field(default=0, ge=0)
    expected_interval_ms: int | None = Field(default=None, ge=0)
    missing_candle_count: int = Field(default=0, ge=0)
    duplicate_candle_count: int = Field(default=0, ge=0)


class StrategyLadderDataQualityReport(BaseModel, frozen=True):
    """Compact schema/ingestion quality report."""

    schema_version: str = Field(default="v1", min_length=1)
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    trade_schema_status: str = "TRADE_SCHEMA_NOT_PROVEN"
    kline_schema_status: str = "KLINE_SCHEMA_NOT_PROVEN"
    orderbook_schema_status: str = "ORDERBOOK_SCHEMA_NOT_PROVEN"
    metadata_schema_status: str = "METADATA_SCHEMA_NOT_PROVEN"
    historical_metadata_status: str = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    historical_data_venue: str = "BYBIT"
    historical_metadata_purpose: str = "historical_replay"
    metadata_source_mode: str = "LOCAL_METADATA_CACHE"
    metadata_cache_path: str = ""
    metadata_pairs_covered: tuple[str, ...] = ()
    missing_metadata_pairs: tuple[str, ...] = ()
    fee_provenance_status: str = "FEE_PROVENANCE_NOT_PROVEN"
    metadata_temporal_status: str = "METADATA_TEMPORAL_NOT_PROVEN"
    metadata_fetched_at_utc: str = ""
    metadata_temporal_drift_days: float | None = None
    metadata_preview_rows: tuple[dict[str, object], ...] = ()
    capital_bucket_metadata_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    timestamp_unit_status: str = "TIMESTAMP_UNIT_NOT_PROVEN"
    files_processed: int = Field(default=0, ge=0)
    files_skipped: int = Field(default=0, ge=0)
    rows_processed: int = Field(default=0, ge=0)
    rows_rejected: int = Field(default=0, ge=0)
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    requested_pairs: tuple[str, ...] = ()
    detected_pairs: tuple[str, ...] = ()
    source_pair_map: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    pair_inference_sources: dict[str, str] = Field(default_factory=dict)
    pair_mismatch_reason_codes: tuple[str, ...] = ()
    ignored_source_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    pair_generalization_status: str = "PAIR_GENERALIZATION_NOT_PROVEN"
    blocker_codes: tuple[str, ...] = ()
    # Patch 6 batch 1 — date pruning before file open.
    date_filter_start: str = ""
    date_filter_end: str = ""
    date_filter_effective_start: str = ""
    replay_context_lookback_ms: int = Field(default=0, ge=0)
    files_seen: int = Field(default=0, ge=0)
    files_skipped_by_date_filter: int = Field(default=0, ge=0)
    date_pruning_status: str = "DATE_PRUNING_NOT_PROVEN"
    silver_index_date_range_status: str = "SILVER_INDEX_DATE_RANGE_NOT_PROVEN"
    silver_index_date_range_violation_count: int = Field(default=0, ge=0)
    raw_scan_budget_status: str = "DRY_RUN_SCOPE_NOT_PROVEN"
    raw_scan_budget_limit_bytes: int = Field(default=0, ge=0)
    raw_scan_budget_reason_codes: tuple[str, ...] = ()
    # Patch 6 batch 1 — silver storage governance.
    silver_storage_format: str = "jsonl"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    raw_source_typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    ohlcv_temporal_completeness_status: str = "OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN"
    ohlcv_temporal_blocked_entry_count: int = Field(default=0, ge=0)
    ohlcv_temporal_critical_timeframes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderCompressionReport(BaseModel, frozen=True):
    """Measured compression report over Bronze/Silver/Gold."""

    schema_version: str = Field(default="v1", min_length=1)
    raw_size_bytes: int = Field(default=0, ge=0)
    silver_size_bytes: int = Field(default=0, ge=0)
    gold_size_bytes: int = Field(default=0, ge=0)
    silver_storage_format: str = "jsonl"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    silver_bloat_ratio: float | None = None
    recommendation: str = ""
    compression_ratio_raw_to_silver: float | None = None
    compression_ratio_raw_to_gold: float | None = None
    files_processed: int = Field(default=0, ge=0)
    files_skipped: int = Field(default=0, ge=0)
    rows_processed: int = Field(default=0, ge=0)
    rows_rejected: int = Field(default=0, ge=0)
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderGoldFeatureManifest(BaseModel, frozen=True):
    """Produced gold feature-store summary.

    Patch 2026-05-15 (timeframe propagation audit) — added explicit
    timeframe outcome fields so that prunes between silver and gold are
    never silent. Pre-existing fields (``timeframes_encoded``,
    ``blocker_codes``) are preserved for backward compatibility; the new
    fields are additive.
    """

    schema_version: str = Field(default="v1", min_length=1)
    gold_feature_store_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    feature_paths: tuple[str, ...] = ()
    feature_row_count: int = Field(default=0, ge=0)
    feature_groups: tuple[str, ...] = ()
    feature_groups_declared: tuple[str, ...] = ()
    feature_groups_generated: tuple[str, ...] = ()
    feature_groups_ready: tuple[str, ...] = ()
    engines_encoded: tuple[str, ...] = ()
    timeframes_encoded: tuple[str, ...] = ()
    # Patch 2026-05-15 — timeframe propagation visibility.
    silver_timeframes_detected: tuple[str, ...] = ()
    gold_timeframes_generated: tuple[str, ...] = ()
    timeframes_pruned: tuple[str, ...] = ()
    pruning_reason_by_timeframe: dict[str, str] = Field(default_factory=dict)
    timeframe_feature_row_count: dict[str, int] = Field(default_factory=dict)
    gold_decision_window_status: str = "GOLD_DECISION_WINDOW_NOT_PROVEN"
    gold_context_row_count: int = Field(default=0, ge=0)
    gold_context_rows_suppressed_count: int = Field(default=0, ge=0)
    microstructure_cache_used: bool = False
    feature_equivalence_status: str = "A2_FEATURE_EQUIVALENCE_NOT_REQUIRED"
    microstructure_streaming_status: str = "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED"
    microstructure_streaming_batch_count: int = Field(default=0, ge=0)
    microstructure_streaming_requested_row_count: int = Field(default=0, ge=0)
    microstructure_streaming_overlay_row_count: int = Field(default=0, ge=0)
    microstructure_streaming_missing_row_count: int = Field(default=0, ge=0)
    microstructure_streaming_status_counts: dict[str, int] = Field(default_factory=dict)
    blocker_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderDataFactoryManifest(BaseModel, frozen=True):
    """Top-level Data Factory manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    raw_roots: tuple[str, ...] = ()
    raw_source_manifest_path: str = ""
    raw_source_provenance_status: str = "RAW_SOURCE_PROVENANCE_NOT_PROVEN"
    raw_source_typing_status: str = "RAW_SOURCE_TYPE_NOT_PROVEN"
    historical_metadata_root: str = ""
    silver_root: str = ""
    gold_root: str = ""
    pairs: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    effective_start: str = ""
    replay_context_lookback_ms: int = Field(default=0, ge=0)
    data_types: tuple[str, ...] = ()
    compression: str = ""
    resume: bool = False
    dry_run: bool = False
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    raw_source_status: str = "RAW_SOURCE_NOT_PROVEN"
    pair_universe_status: str = "PAIR_UNIVERSE_NOT_PROVEN"
    silver_index_status: str = "SILVER_INDEX_NOT_READY"
    gold_feature_store_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    trade_schema_status: str = "TRADE_SCHEMA_NOT_PROVEN"
    kline_schema_status: str = "KLINE_SCHEMA_NOT_PROVEN"
    orderbook_schema_status: str = "ORDERBOOK_SCHEMA_NOT_PROVEN"
    metadata_schema_status: str = "METADATA_SCHEMA_NOT_PROVEN"
    historical_metadata_status: str = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    metadata_source_mode: str = "LOCAL_METADATA_CACHE"
    fee_provenance_status: str = "FEE_PROVENANCE_NOT_PROVEN"
    metadata_temporal_status: str = "METADATA_TEMPORAL_NOT_PROVEN"
    metadata_temporal_drift_days: float | None = None
    pair_generalization_status: str = "PAIR_GENERALIZATION_NOT_PROVEN"
    compression_status: str = "COMPRESSION_NOT_PROVEN"
    silver_storage_format: str = "jsonl"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    silver_bloat_ratio: float | None = None
    ohlcv_temporal_completeness_status: str = "OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN"
    ohlcv_temporal_blocked_entry_count: int = Field(default=0, ge=0)
    ohlcv_temporal_critical_timeframes: tuple[str, ...] = ()
    date_pruning_status: str = "DATE_PRUNING_NOT_PROVEN"
    silver_index_date_range_status: str = "SILVER_INDEX_DATE_RANGE_NOT_PROVEN"
    raw_scan_budget_status: str = "DRY_RUN_SCOPE_NOT_PROVEN"
    blocker_codes: tuple[str, ...] = ()
    files_processed: int = Field(default=0, ge=0)
    files_skipped: int = Field(default=0, ge=0)
    rows_processed: int = Field(default=0, ge=0)
    rows_rejected: int = Field(default=0, ge=0)
    bytes_read: int = Field(default=0, ge=0)
    bytes_written: int = Field(default=0, ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    artifact_hash: str | None = None


class StrategyLadderDataFactoryRequest(BaseModel, frozen=True):
    """Canonical Patch 6 Data Factory request."""

    run_id: str = Field(..., min_length=1)
    input_root: Path
    raw_roots: tuple[Path, ...] = ()
    raw_source_manifest_path: Path | None = None
    historical_metadata_root: Path | None = None
    silver_root: Path
    gold_root: Path
    pairs: tuple[str, ...] = ()
    engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d")
    # Patch 2026-05-15 — default now uses the canonical registry so silver
    # timeframes are no longer silently pruned when callers omit the field.
    # Callers that want a strict subset must pass it explicitly.
    timeframes: tuple[str, ...] = DEFAULT_GOLD_TIMEFRAMES
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    start: str = ""
    end: str = ""
    data_types: tuple[str, ...] = ("trades", "klines", "orderbook", "metadata")
    compression: str = "zstd"
    resume: bool = False
    dry_run: bool = False
    # Patch 6 batch 1 — silver storage format selector.
    # ``jsonl``    : legacy plain JSONL (default for backwards compatibility / debug).
    # ``jsonl-gz`` : gzip-compressed JSONL (recommended for production; ~7-10x smaller).
    storage_format: str = "jsonl"
    allow_broad_run: bool = False
    small_scope: bool = False
    debug_storage_override: bool = False
    max_gold_feature_rows: int = Field(default=0, ge=0)
    storage_budget_limit_bytes: int = Field(default=53_687_091_200, ge=0)  # default 50 GB
    # Audit 2026-05-07 (P0 CE/cost provenance) — opt-in flag pour mesurer
    # spread_bps reel depuis les snapshots orderbook au lieu des constantes
    # hardcodees (4.0/6.0/0.0 selon book_status). Default False = comportement
    # legacy. Activer via le runner quand engine_native_mode=True.
    # Quand True, le data_factory invoque compute_economic_provenance() pour
    # chaque feature_row au lieu de spread_bps = 4.0/6.0/0.0.
    use_measured_economic_provenance: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_feature_names(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        raw_feature_names = data.get("feature_names") or DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
        if isinstance(raw_feature_names, str):
            raw_feature_names = tuple(
                part.strip() for part in raw_feature_names.split(",") if part.strip()
            )
        data["feature_names"] = normalize_supported_expected_edge_feature_names(
            tuple(raw_feature_names)
        )
        return data


class StrategyLadderDataFactoryResult(BaseModel, frozen=True):
    """Canonical Patch 6 Data Factory result."""

    manifest: StrategyLadderDataFactoryManifest
    raw_source_report: StrategyLadderRawSourceReport
    pair_universe_report: StrategyLadderPairUniverseReport
    data_quality_report: StrategyLadderDataQualityReport
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...] = ()
    compression_report: StrategyLadderCompressionReport
    gold_feature_manifest: StrategyLadderGoldFeatureManifest


class StrategyLadderFirstControlledRunRequest(BaseModel, frozen=True):
    """Canonical request for the first controlled Strategy Ladder run harness."""

    run_id: str = Field(..., min_length=1)
    input_root: Path
    raw_roots: tuple[Path, ...] = ()
    raw_source_manifest_path: Path | None = None
    historical_metadata_root: Path | None = None
    output_root: Path
    silver_root: Path
    gold_root: Path
    pairs: tuple[str, ...] = ()
    engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d")
    capital_buckets: tuple[int, ...] = (400, 500, 1500, 4000)
    # Patch 2026-05-15 — aligned with the canonical timeframe registry.
    timeframes: tuple[str, ...] = DEFAULT_GOLD_TIMEFRAMES
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    start: str = ""
    end: str = ""
    dry_run: bool = False
    fixture_mode: bool = False
    small_scope: bool = False
    no_full_scan: bool = True
    allow_broad_run: bool = False
    ml_mode: str = "ML_MODE_OFF"
    frozen_ml_artifact_path: Path | None = None
    frozen_ml_artifact_hash: str | None = None
    # Audit 2026-05-07 (P0 engine bridge wire) — active le pont microstructure
    # opt-in vers les builders/bridges natifs A/B/C/D pendant le first controlled
    # run. Ce flag reste additif: il n'invente pas de candidats natifs et ne
    # retire pas la gate NO_EXECUTED_TRADES.
    engine_native_mode: bool = False
    # Taille du sample passé au pont natif. 10 reste la valeur sûre côté cockpit
    # pour prouver le câblage sans faire exploser l'IO.
    engine_native_sample_size: int = Field(default=10, ge=0)
    # Audit 2026-05-07 (P0 CE/cost provenance) — propage vers
    # StrategyLadderDataFactoryRequest.use_measured_economic_provenance.
    # Default False : comportement legacy (constantes hardcoded).
    use_measured_economic_provenance: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_feature_names(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        raw_feature_names = data.get("feature_names") or DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
        if isinstance(raw_feature_names, str):
            raw_feature_names = tuple(
                part.strip() for part in raw_feature_names.split(",") if part.strip()
            )
        data["feature_names"] = normalize_supported_expected_edge_feature_names(
            tuple(raw_feature_names)
        )
        return data


class StrategyLadderFirstControlledRunManifest(BaseModel, frozen=True):
    """Top-level first controlled run manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    first_run_status: str = "FIRST_RUN_BLOCKED_BY_DATA_FACTORY"
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    raw_window_status: str = "RAW_WINDOW_NOT_PROVEN"
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    capital_profile_status: str = "CAPITAL_PROFILE_NOT_PROVEN"
    ml_mode_status: str = "ML_MODE_OFF"
    blocker_codes: tuple[str, ...] = ()
    estimated_files_scanned: int = Field(default=0, ge=0)
    estimated_pairs_considered: int = Field(default=0, ge=0)
    allow_broad_run: bool = False
    dry_run: bool = False
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderFirstControlledRunStageSummary(BaseModel, frozen=True):
    """Compact first-run stage summary."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    stage_statuses: dict[str, str] = Field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    candidate_count: int = Field(default=0, ge=0)
    raw_window_count: int = Field(default=0, ge=0)
    detailed_replay_count: int = Field(default=0, ge=0)
    capital_profile_count: int = Field(default=0, ge=0)
    artifact_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderFirstControlledRunArtifactInventory(BaseModel, frozen=True):
    """Operator-facing artifact inventory for the first controlled run."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    artifact_refs: dict[str, str] = Field(default_factory=dict)
    artifact_hash: str | None = None
    created_at: datetime | None = None


def finalize_hashed_model(model: BaseModel) -> BaseModel:
    """Return one model copy with deterministic artifact hash and UTC timestamp fields normalized."""

    payload = model.model_dump(mode="json")
    if "created_at" in payload and payload["created_at"] is None:
        payload["created_at"] = datetime.now(tz=UTC)
    if "updated_at" in payload and payload["updated_at"] is None:
        payload["updated_at"] = datetime.now(tz=UTC)
    payload["artifact_hash"] = deterministic_payload_hash(payload)
    return model.__class__.model_validate(payload)


__all__ = [
    "StrategyLadderCompressionReport",
    "StrategyLadderDataFactoryManifest",
    "StrategyLadderDataFactoryRequest",
    "StrategyLadderDataFactoryResult",
    "StrategyLadderDataQualityReport",
    "StrategyLadderFirstControlledRunArtifactInventory",
    "StrategyLadderFirstControlledRunManifest",
    "StrategyLadderFirstControlledRunRequest",
    "StrategyLadderFirstControlledRunStageSummary",
    "StrategyLadderGoldFeatureManifest",
    "StrategyLadderPairCoverage",
    "StrategyLadderPairUniverseReport",
    "StrategyLadderRawFileClassification",
    "StrategyLadderRawSource",
    "StrategyLadderRawSourceReport",
    "StrategyLadderSilverIndexEntry",
    "finalize_hashed_model",
]
