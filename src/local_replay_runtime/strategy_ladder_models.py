"""Typed models for the canonical V5.3 Backtest Strategy Ladder runner."""

from __future__ import annotations

from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from local_replay_runtime.strategy_ladder_edge_model_provider_multi_pair import (
    EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY,
    EXPECTED_EDGE_ARTIFACT_MODES,
)


FeatureScalar = str | int | float | bool | None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _parse_boundary_date(raw_value: str) -> date | None:
    value = (raw_value or "").strip().replace("Z", "+00:00")
    if not value:
        return None
    if value.isdigit():
        numeric = int(value)
        if len(value) >= 13:
            return datetime.fromtimestamp(numeric / 1000.0, tz=UTC).date()
        return datetime.fromtimestamp(numeric, tz=UTC).date()
    try:
        if "T" not in value and " " not in value:
            return date.fromisoformat(value)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).date()
    except ValueError:
        return None


def _backtest_days_covered(start: str, end: str) -> int | None:
    start_date = _parse_boundary_date(start)
    end_date = _parse_boundary_date(end)
    if start_date is None or end_date is None or end_date < start_date:
        return None
    return (end_date - start_date).days + 1


def deterministic_payload_hash(payload: object) -> str:
    """Return one deterministic SHA-256 digest for a JSON-compatible payload."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class StrategyLadderRequest(BaseModel, frozen=True):
    """Canonical input for the Strategy Ladder runner."""

    run_id: str = Field(..., min_length=1)
    input_root: Path
    feature_store_root: Path
    raw_root: Path
    raw_roots: tuple[Path, ...] = ()
    raw_source_manifest_path: Path | None = None
    silver_index_path: Path | None = None
    output_root: Path
    workflow_run_id: str = ""
    phase_run_id: str = ""
    parent_workflow_ref: str = ""
    pairs: tuple[str, ...] = ()
    engines: tuple[str, ...] = ()
    capital_buckets: tuple[int, ...] = (400, 500, 1500, 4000)
    timeframes: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    fast_only: bool = False
    detailed_only: bool = False
    resume: bool = False
    dry_run: bool = False
    ml_mode: str = "ML_MODE_OFF"
    frozen_ml_artifact_path: Path | None = None
    frozen_ml_artifact_hash: str | None = None
    expected_edge_artifact_mode: str = EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY
    rolling_ml_window_plan_path: Path | None = None
    ml_artifact_freshness_days: int = Field(default=30, ge=1)
    execution_runtime_projection_path: Path | None = None
    # Audit 2026-05-06 (P3a) — opt-in flag pour activer le pont microstructure
    # vers les engine runners natifs. Quand True, le rail invoque l'adapter
    # `strategy_ladder_engine_native_adapter` qui calcule les 5 records canoniques
    # (Kyle, VPIN, OFI, QueuePressure, RealizedKernelVol) depuis raw_windows et
    # compose un input partiel engine_a/b/c/d via compose_engine_*_input_payload.
    # NOTE : les calls finaux run_engine_X() restent bloques tant que les
    # champs structurels par engine (breakout_strength pour engine_c,
    # prior_trade_quality pour engine_d, etc.) n'ont pas de structure resolver
    # canonique. Ce flag NE retire PAS la gate
    # STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES.
    engine_native_mode: bool = False
    # Audit 2026-05-07 (P3a wire) — taille du sample sur lequel invoquer le pont
    # Legacy bridge sample knob retained for backward-compatible requests.
    # Phase A deproxy no longer uses this value to limit candidate truth.
    engine_native_sample_size: int = Field(default=10, ge=0)
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_sample_cap: int = Field(default=10, ge=0)
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    b1_5_policy_mode: str = "conservative_hard_only"
    raw_window_materialization_mode: str = "MATERIALIZE"
    candidate_events_path: Path | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_roots(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        raw_root = data.get("raw_root")
        raw_roots = data.get("raw_roots")
        if not raw_roots:
            data["raw_roots"] = (raw_root,) if raw_root else ()
        elif isinstance(raw_roots, (list, tuple)):
            normalized: list[Path] = []
            seen: set[str] = set()
            if raw_root:
                candidate = Path(raw_root)
                resolved = str(candidate)
                if resolved not in seen:
                    normalized.append(candidate)
                    seen.add(resolved)
            for item in raw_roots:
                if not item:
                    continue
                candidate = Path(item)
                resolved = str(candidate)
                if resolved in seen:
                    continue
                normalized.append(candidate)
                seen.add(resolved)
            data["raw_roots"] = tuple(normalized)
        return data

    @model_validator(mode="before")
    @classmethod
    def normalize_b1_5_policy_mode(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        resolved_mode = str(data.get("b1_5_policy_mode") or "").strip().lower()
        if not resolved_mode:
            resolved_mode = (
                "diagnostic_full_replay"
                if bool(data.get("diagnostic_full_replay"))
                else "conservative_hard_only"
            )
        if resolved_mode == "diagnostic_full_replay":
            data["diagnostic_full_replay"] = True
            data["preselected_only"] = False
        elif resolved_mode in {
            "conservative_hard_only",
            "strict_fail_closed",
        }:
            data["diagnostic_full_replay"] = False
            data["preselected_only"] = True
        data["b1_5_policy_mode"] = resolved_mode
        raw_window_mode = str(
            data.get("raw_window_materialization_mode") or "MATERIALIZE"
        ).strip().upper().replace("-", "_")
        data["raw_window_materialization_mode"] = (
            "REFS_ONLY"
            if raw_window_mode in {"REFS_ONLY", "REFERENCE_ONLY"}
            else "MATERIALIZE"
        )
        return data

    @model_validator(mode="after")
    def validate_modes(self) -> "StrategyLadderRequest":
        if self.fast_only and self.detailed_only:
            raise ValueError("StrategyLadderRequest cannot combine fast_only and detailed_only")
        if self.preselected_only and self.diagnostic_full_replay:
            raise ValueError(
                "StrategyLadderRequest cannot enable preselected_only and diagnostic_full_replay simultaneously"
            )
        if self.ml_mode not in {
            "ML_MODE_OFF",
            "ML_MODE_OVERLAY_FROZEN",
            "ML_MODE_TRAINING_LAB_ONLY",
        }:
            raise ValueError(f"StrategyLadderRequest unsupported ml_mode: {self.ml_mode}")
        if self.ml_mode == "ML_MODE_TRAINING_LAB_ONLY":
            raise ValueError("StrategyLadderRequest baseline Strategy Ladder forbids ML_MODE_TRAINING_LAB_ONLY")
        if self.ml_mode == "ML_MODE_OVERLAY_FROZEN" and (
            self.frozen_ml_artifact_path is None or not self.frozen_ml_artifact_hash
        ):
            raise ValueError("StrategyLadderRequest ML_MODE_OVERLAY_FROZEN requires artifact path and hash")
        if self.expected_edge_artifact_mode not in EXPECTED_EDGE_ARTIFACT_MODES:
            raise ValueError(
                f"StrategyLadderRequest unsupported expected_edge_artifact_mode: "
                f"{self.expected_edge_artifact_mode!r} (allowed: {EXPECTED_EDGE_ARTIFACT_MODES})"
            )
        if self.b1_5_policy_mode not in {
            "conservative_hard_only",
            "strict_fail_closed",
            "diagnostic_full_replay",
        }:
            raise ValueError(
                f"StrategyLadderRequest unsupported b1_5_policy_mode: {self.b1_5_policy_mode}"
            )
        if self.raw_window_materialization_mode not in {"MATERIALIZE", "REFS_ONLY"}:
            raise ValueError(
                "StrategyLadderRequest unsupported raw_window_materialization_mode: "
                f"{self.raw_window_materialization_mode}"
            )
        covered_days = _backtest_days_covered(self.start, self.end)
        if (
            self.ml_mode == "ML_MODE_OVERLAY_FROZEN"
            and covered_days is not None
            and covered_days > self.ml_artifact_freshness_days
            and self.rolling_ml_window_plan_path is None
        ):
            raise ValueError(
                "StrategyLadderRequest ML_MODE_OVERLAY_FROZEN long backtests require rolling_ml_window_plan_path"
            )
        return self

    @property
    def run_dir(self) -> Path:
        return self.output_root / "backtest_strategy_ladder" / self.run_id


class StrategyLadderFeatureRow(BaseModel, frozen=True):
    """One row from a Strategy Ladder feature/gold-store input."""

    schema_version: str = Field(default="v1", min_length=1)
    timestamp_ns: int | None = Field(default=None, ge=0)
    timestamp_ms: int | None = Field(default=None, ge=0)
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    engine_id: str | None = None
    engine_scope: tuple[str, ...] = ()
    eligible_engines: tuple[str, ...] = ()
    strategy_id: str | None = None
    strategy_role: str | None = None
    feature_values: dict[str, FeatureScalar] = Field(default_factory=dict)
    feature_version: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    # Patch P1 (2026-05-29) — A4 raw_catalog_ref + A6 feature_set_hash for full
    # gold row reproducibility. Both optional (back-compat) but populated by the
    # canonical gold row builder. Audit trace: raw_catalog_ref ties row back to
    # silver index entry; feature_set_hash detects silent feature drift.
    raw_catalog_ref: str | None = None
    feature_set_hash: str | None = None
    # Patch P2 (2026-05-29) — A7 venue metadata temporal proof. Populated when
    # the gold row builder resolves a matching metadata silver entry. When
    # metadata is missing, all three remain None and downstream audit can flag
    # `VENUE_METADATA_TEMPORAL_PROOF_MISSING`.
    metadata_effective_at: str | None = None  # ISO date of the metadata snapshot
    metadata_source: str | None = None  # canonical silver-catalog ref
    metadata_hash: str | None = None  # SHA256 of the metadata file content
    # Patch P3 (2026-05-29) — book freshness temporal proof. Populated from
    # EconomicProvenance. Audit C5 calibration: tolerance per timeframe.
    # `book_freshness_status`: BOOK_DEPTH20_AVAILABLE_FRESH / AVAILABLE_STALE
    # / MISSING / BOOK_FRESHNESS_NOT_PROVEN.
    book_snapshot_age_ms: int | None = Field(default=None, ge=0)
    book_freshness_status: str = "BOOK_FRESHNESS_NOT_PROVEN"
    book_freshness_tolerance_ms: int | None = Field(default=None, ge=0)
    # Patch P5 (2026-05-29) — A9 expected-edge schema split. Separates the
    # proxy value (research only) from the model value (governed). Only
    # `expected_edge_model_bps` is allowed as truth for promotion gates.
    # `expected_edge_truth_status` is derived from `expected_edge_provenance`
    # via `derive_expected_edge_truth_status` (enum: MODEL_GOVERNED /
    # MODEL_OVERRIDE / PROXY / DEFAULT_PROXY / BLOCKED / NOT_PROVEN).
    expected_edge_proxy_bps: float | None = None
    expected_edge_model_bps: float | None = None
    expected_edge_row_truth_status: str = "EXPECTED_EDGE_NOT_PROVEN"
    # Patch P4 (2026-05-29) — slippage explicit truth status. Separates A2
    # research-quality slippage (Kyle estimate / default fallback) from B2
    # replay-time truth (depth20 book walk during execution). Derived from
    # `slippage_provenance` via `derive_slippage_truth_status`. P5 validators
    # will block promotion when not in the prod-safe whitelist.
    slippage_truth_status: str = "SLIPPAGE_NOT_PROVEN"
    source_ref: str = Field(..., min_length=1)
    available_at_timestamp_ms: int | None = Field(default=None, ge=0)
    source_record_id: str | None = None
    close_price: float = Field(default=0.0, ge=0.0)
    regime: str = ""
    raw_score: float = 0.0
    penalized_score: float | None = None
    final_score: float | None = None
    expected_edge_bps: float = 0.0
    spread_bps: float = Field(default=0.0, ge=0.0)
    slippage_bps: float = Field(default=0.0, ge=0.0)
    latency_penalty_bps: float = Field(default=0.0, ge=0.0)
    expected_edge_provenance: str = "EXPECTED_EDGE_PROVENANCE_NOT_PROVEN"
    economic_provenance: str = "ECONOMIC_PROVENANCE_NOT_PROVEN"
    economic_measurement_warnings: tuple[str, ...] = ()
    # Audit 2026-05-14 P3-A wiring : tier-aware spread provenance (per-row).
    # Valeurs possibles : "MEASURED_FROM_BOOK_SNAPSHOT", "MEASURED_FROM_BOOK_RECONSTRUCTION",
    # "MEASURED_FROM_BOOK_SNAPSHOT_STALE" (audit-only, ne leve PAS le gate
    # SPREAD_MODEL_PROXY), "DEFAULT_BY_BOOK_STATUS", ou
    # "SPREAD_PROVENANCE_NOT_PROVEN" (legacy/missing).
    spread_provenance: str = "SPREAD_PROVENANCE_NOT_PROVEN"
    # Audit 2026-05-14 P3-B wiring : tier-aware slippage provenance (per-row).
    # Valeurs : "MEASURED_FROM_KYLE_LAMBDA" (canonical), "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE"
    # (caller-supplied, e.g. live API), "DEFAULT_TO_CALIBRATE" (fallback), ou
    # "SLIPPAGE_PROVENANCE_NOT_PROVEN" (legacy/missing).
    slippage_provenance: str = "SLIPPAGE_PROVENANCE_NOT_PROVEN"
    fill_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    side: str = "buy"
    tick_size: float | None = Field(default=None, gt=0.0)
    step_size: float | None = Field(default=None, gt=0.0)
    maker_fee_rate: float | None = Field(default=None, ge=0.0)
    taker_fee_rate: float | None = Field(default=None, ge=0.0)
    # Patch P7 (2026-05-29) — B5 fee schedule temporal proof. ISO date when
    # the venue published the fee schedule used by this row. Validator P7
    # blocks if drift vs row.timestamp_ms exceeds PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS.
    fee_schedule_date: str | None = None
    target_decision_state: str | None = None
    production_decision_state: str | None = None
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
    planned_notional: float | None = Field(default=None, ge=0.0)
    allocation_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    min_notional: float | None = Field(default=None, ge=0.0)
    shared_core_match: bool = True
    feature_sources_used: tuple[str, ...] = ()
    trade_feature_status: str = "TRADE_FEATURE_STATUS_NOT_PROVEN"
    kline_feature_status: str = "KLINE_FEATURE_STATUS_NOT_PROVEN"
    orderbook_feature_status: str = "ORDERBOOK_FEATURE_STATUS_NOT_PROVEN"
    candidate_data_source_label: str = "COMPAT_FEATURE_DISCOVERY"
    feature_truth_boundary_status: str = "FEATURE_TRUTH_BOUNDARY_NOT_PROVEN"
    feature_usage_policy: str = "A2_GOLD_FEATURE_USAGE_NOT_PROVEN"
    cost_feature_truth_status: str = "COST_FEATURE_TRUTH_NOT_PROVEN"
    compatibility_notes: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("timestamp_ms") is None and data.get("timestamp_ns") is not None:
            data["timestamp_ms"] = int(int(data["timestamp_ns"]) / 1_000_000)
        if data.get("timestamp_ns") is None and data.get("timestamp_ms") is not None:
            data["timestamp_ns"] = int(data["timestamp_ms"]) * 1_000_000
        if isinstance(data.get("engine_scope"), str):
            data["engine_scope"] = tuple(
                part for part in str(data["engine_scope"]).split("|") if part
            )
        if isinstance(data.get("eligible_engines"), str):
            data["eligible_engines"] = tuple(
                part for part in str(data["eligible_engines"]).split("|") if part
            )
        if isinstance(data.get("hard_block_reasons"), str):
            raw_reasons = str(data["hard_block_reasons"]).strip()
            data["hard_block_reasons"] = (
                tuple(part for part in raw_reasons.split("|") if part)
                if raw_reasons
                else ()
            )
        if isinstance(data.get("feature_sources_used"), str):
            raw_sources = str(data["feature_sources_used"]).strip()
            data["feature_sources_used"] = (
                tuple(part for part in raw_sources.split("|") if part)
                if raw_sources
                else ()
            )
        if isinstance(data.get("compatibility_notes"), str):
            raw_notes = str(data["compatibility_notes"]).strip()
            data["compatibility_notes"] = (
                tuple(part for part in raw_notes.split("|") if part)
                if raw_notes
                else ()
            )
        if isinstance(data.get("economic_measurement_warnings"), str):
            raw_warnings = str(data["economic_measurement_warnings"]).strip()
            data["economic_measurement_warnings"] = (
                tuple(part for part in raw_warnings.split("|") if part)
                if raw_warnings
                else ()
            )
        if data.get("penalized_score") is None:
            data["penalized_score"] = data.get("raw_score", 0.0)
        if data.get("final_score") is None:
            data["final_score"] = data.get("penalized_score", data.get("raw_score", 0.0))
        if isinstance(data.get("feature_values"), str):
            raw_features = str(data["feature_values"]).strip()
            data["feature_values"] = json.loads(raw_features) if raw_features else {}
        return data

    @model_validator(mode="after")
    def validate_required_fields(self) -> "StrategyLadderFeatureRow":
        if self.timestamp_ms is None and self.timestamp_ns is None:
            raise ValueError("StrategyLadderFeatureRow requires timestamp_ms or timestamp_ns")
        if self.available_at_timestamp_ms is not None and self.available_at_timestamp_ms > self.resolved_timestamp_ms:
            raise ValueError("StrategyLadderFeatureRow available_at_timestamp_ms cannot exceed event timestamp")
        if not self.resolved_engine_ids:
            raise ValueError("StrategyLadderFeatureRow requires engine_id or eligible engine scope")
        return self

    @property
    def resolved_timestamp_ms(self) -> int:
        if self.timestamp_ms is not None:
            return self.timestamp_ms
        return int((self.timestamp_ns or 0) / 1_000_000)

    @property
    def resolved_engine_ids(self) -> tuple[str, ...]:
        values = tuple(
            dict.fromkeys(
                value
                for value in (
                    self.engine_id,
                    *self.engine_scope,
                    *self.eligible_engines,
                )
                if value
            )
        )
        return values

    def resolved_strategy_id(self, engine_id: str) -> str:
        return self.strategy_id or engine_id


class StrategyLadderFeatureStoreResult(BaseModel, frozen=True):
    """Resolved feature/gold-store stage output."""

    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    rows: tuple[StrategyLadderFeatureRow, ...] = ()
    input_paths: tuple[str, ...] = ()
    invalid_row_count: int = Field(default=0, ge=0)
    rejected_future_leak_count: int = Field(default=0, ge=0)
    blocker_codes: tuple[str, ...] = ()

    @property
    def row_count(self) -> int:
        return len(self.rows)


class StrategyLadderCandidateEvent(BaseModel, frozen=True):
    """Canonical fast-candidate export event."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    candidate_id: str = Field(..., min_length=1)
    timestamp_ns: int | None = Field(default=None, ge=0)
    timestamp_ms: int | None = Field(default=None, ge=0)
    pair: str = Field(..., min_length=1)
    timeframe: str | None = None
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    capital_bucket: int | None = Field(default=None, ge=1)
    candidate_source: str = "COMPAT_FEATURE_DISCOVERY"
    feature_refs: tuple[str, ...] = ()
    preliminary_score: float | None = None
    preliminary_reason_codes: tuple[str, ...] = ()
    feature_version: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    compatibility_payload: dict[str, object] | None = None
    feature_sources_used: tuple[str, ...] = ()
    trade_feature_status: str = "TRADE_FEATURE_STATUS_NOT_PROVEN"
    kline_feature_status: str = "KLINE_FEATURE_STATUS_NOT_PROVEN"
    orderbook_feature_status: str = "ORDERBOOK_FEATURE_STATUS_NOT_PROVEN"
    candidate_data_source_label: str = "COMPAT_FEATURE_DISCOVERY"

    @model_validator(mode="before")
    @classmethod
    def normalize_candidate_input(cls, value: object) -> object:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for key in ("feature_refs", "preliminary_reason_codes", "feature_sources_used"):
            raw_value = data.get(key)
            if isinstance(raw_value, str):
                stripped = raw_value.strip()
                data[key] = tuple(part for part in stripped.split("|") if part) if stripped else ()
        return data

    @property
    def resolved_timestamp_ms(self) -> int:
        if self.timestamp_ms is not None:
            return self.timestamp_ms
        return int((self.timestamp_ns or 0) / 1_000_000)


class StrategyLadderCandidateSummary(BaseModel, frozen=True):
    """Compact export summary for candidate discovery output."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    candidate_count: int = Field(default=0, ge=0)
    unique_candidate_count: int = Field(default=0, ge=0)
    base_event_count: int = Field(default=0, ge=0)
    per_engine_candidate_count: int | None = Field(default=None, ge=0)
    engine_native_candidate_count: int = Field(default=0, ge=0)
    candidate_source_status: str = "CANDIDATE_SOURCE_NOT_PROVEN"
    requested_pairs: tuple[str, ...] = ()
    pairs_with_feature_rows: tuple[str, ...] = ()
    pairs_seen: tuple[str, ...] = ()
    missing_requested_pairs: tuple[str, ...] = ()
    pair_candidate_coverage_status: str = "PAIR_CANDIDATE_COVERAGE_NOT_PROVEN"
    pair_candidate_blocker_codes: tuple[str, ...] = ()
    candidate_count_by_pair: dict[str, int] = Field(default_factory=dict)
    candidate_count_by_pair_engine: dict[str, int] = Field(default_factory=dict)
    candidate_count_by_pair_timeframe: dict[str, int] = Field(default_factory=dict)
    engines_seen: tuple[str, ...] = ()
    strategies_seen: tuple[str, ...] = ()
    timeframes_seen: tuple[str, ...] = ()
    start_timestamp: int | None = Field(default=None, ge=0)
    end_timestamp: int | None = Field(default=None, ge=0)
    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    candidate_discovery_status: str = "CANDIDATE_DISCOVERY_NOT_PROVEN"
    candidate_export_status: str = "CANDIDATE_EXPORT_NOT_PROVEN"
    candidate_sample_cap: int = Field(default=0, ge=0)
    effective_engine_native_sample_size: int = Field(default=10, ge=0)
    engine_count: int = Field(default=4, ge=0)
    candidate_cap_formula: str = ""
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    candidate_discovery_limited: bool = True
    candidate_discovery_limit_reason: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
    temporal_bucket_granularity: str = ""
    temporal_bucket_count_available: int = Field(default=0, ge=0)
    temporal_bucket_count_selected: int = Field(default=0, ge=0)
    temporal_bucket_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    preselection_status: str = "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN"
    replay_input_mode_status: str = "PRESELECTED_ONLY"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    b1_5_policy_mode: str = "conservative_hard_only"
    discovery_pre_candidate_count: int = Field(default=0, ge=0)
    engine_native_preselected_count: int = Field(default=0, ge=0)
    preselection_hard_rejected_count: int = Field(default=0, ge=0)
    preselection_soft_flagged_count: int = Field(default=0, ge=0)
    preselection_passed_count: int = Field(default=0, ge=0)
    b2_replay_candidate_count: int = Field(default=0, ge=0)
    trade_eligible_candidate_count: int = Field(default=0, ge=0)
    preselection_rejection_count: int = Field(default=0, ge=0)
    replay_savings_estimate_count: int = Field(default=0, ge=0)
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    created_at: datetime | None = None


class StrategyLadderRawWindowManifest(BaseModel, frozen=True):
    """Deterministic raw-window extraction manifest."""

    schema_version: str = Field(default="v1", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    window_start_ms: int = Field(..., ge=0)
    window_end_ms: int = Field(..., ge=0)
    raw_trade_path: str | None = None
    raw_book_path: str | None = None
    # Audit 2026-05-07 (P3a fix) — chemin vers le fichier JSONL des deltas
    # orderbook (silver/bybit/spot/orderbook_delta/...). Necessaire pour
    # reconstruire sequentiellement les etats du book a partir d'un snapshot
    # initial sparse + N deltas. Sans ca, OFI ne peut pas etre calcule sur
    # une fenetre courte (5min) avec snapshots peu frequents.
    # Si None, l'adapter le derive en remplacant "orderbook_snapshot" par
    # "orderbook_delta" dans raw_book_path (convention silver canonique).
    raw_book_delta_path: str | None = None
    raw_ohlcv_path: str | None = None
    raw_metadata_path: str | None = None
    book_depth_levels_available: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    window_extraction_status: str = "RAW_WINDOW_NOT_PROVEN"
    raw_sources_used: tuple[str, ...] = ()
    trade_source_id: str | None = None
    book_snapshot_source_id: str | None = None
    book_delta_source_id: str | None = None
    ohlcv_source_id: str | None = None
    metadata_source_id: str | None = None
    source_coverage_status: str = "RAW_WINDOW_SOURCE_NOT_PROVEN"
    input_data_hash: str | None = None
    artifact_hash: str | None = None


class StrategyLadderBucketReplayResult(BaseModel, frozen=True):
    """One measured detailed-replay result for one candidate and one capital bucket."""

    schema_version: str = Field(default="v1", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    timestamp_ms: int = Field(..., ge=0)
    execution_state: str | None = None
    executed_notional: float | None = Field(default=None, ge=0.0)
    reduced_notional: float | None = Field(default=None, ge=0.0)
    no_fill_flag: bool = False
    partial_fill_flag: bool = False
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    replay_outcome_status: str = "REPLAY_OUTCOME_NOT_PROVEN"
    entry_reference_status: str = "ENTRY_REFERENCE_NOT_AVAILABLE"
    mfe_mae_status: str = "MFE_MAE_NOT_AVAILABLE"
    holding_time_ms: int | None = Field(default=None, ge=0)
    forward_return_h1: float | None = None
    forward_return_h5: float | None = None
    forward_return_h10: float | None = None
    mfe_bps: float | None = None
    mae_bps: float | None = None
    entry_ref: dict[str, object] = Field(default_factory=dict)
    exit_ref: dict[str, object] = Field(default_factory=dict)
    invalidation_ref: dict[str, object] = Field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    planned_notional: float | None = Field(default=None, ge=0.0)
    min_notional: float | None = Field(default=None, ge=0.0)
    min_notional_viable: bool | None = None
    min_notional_reason_codes: tuple[str, ...] = ()
    size_reduction_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    artifact_hash: str | None = None
    dtr_record: dict[str, object] = Field(default_factory=dict)
    parity_payload: dict[str, object] = Field(default_factory=dict)
    shared_payload_ref: str = ""


class StrategyLadderSharedReplayPayload(BaseModel, frozen=True):
    """Per-candidate payload shared across all capital-bucket replay artifacts."""

    schema_version: str = Field(default="v1", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    raw_trade_path: str = ""
    raw_book_path: str = ""
    raw_book_delta_path: str = ""
    raw_ohlcv_path: str = ""
    raw_metadata_path: str = ""
    raw_sources_used: tuple[str, ...] = ()
    book_depth_levels_available: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    source_coverage_status: str = "SOURCE_COVERAGE_NOT_PROVEN"
    shared_parity_payload: dict[str, object] = Field(default_factory=dict)
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    artifact_hash: str | None = None


class StrategyLadderBucketReplaySummary(BaseModel, frozen=True):
    """Compact candidate-wrapper projection of one bucket result."""

    candidate_id: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=0)
    execution_state: str = "evaluated"
    expected_ce_net: float = 0.0
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    planned_notional: float | None = Field(default=None, ge=0.0)
    min_notional_viable: bool | None = None
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    replay_outcome_status: str = "REPLAY_OUTCOME_NOT_PROVEN"
    reason_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None


class StrategyLadderDetailedReplayArtifact(BaseModel, frozen=True):
    """Per-candidate detailed replay carrier with bucket-result refs."""

    schema_version: str = Field(default="v1", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    detailed_replay_status: str = "DETAILED_REPLAY_NOT_PROVEN"
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...] = ()
    bucket_result_summary: tuple[StrategyLadderBucketReplaySummary, ...] = ()
    bucket_result_refs: tuple[str, ...] = ()
    shared_payload_ref: str = ""
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    artifact_hash: str | None = None


class StrategyLadderRunManifest(BaseModel, frozen=True):
    """Run manifest written by the canonical Strategy Ladder runner."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    input_root: str = ""
    feature_store_root: str = ""
    raw_root: str = ""
    raw_roots: tuple[str, ...] = ()
    raw_source_manifest_path: str = ""
    silver_index_path: str = ""
    output_root: str = ""
    workflow_run_id: str = ""
    phase_run_id: str = ""
    parent_workflow_ref: str = ""
    pairs: tuple[str, ...] = ()
    engines: tuple[str, ...] = ()
    capital_buckets: tuple[int, ...] = ()
    timeframes: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    fast_only: bool = False
    detailed_only: bool = False
    resume: bool = False
    dry_run: bool = False
    ml_mode_status: str = "ML_MODE_OFF"
    compatibility_mode_status: str = "COMPAT_FEATURE_DISCOVERY"
    live_engine_parity_status: str = "NOT_PROVEN"
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    raw_source_status: str = "RAW_SOURCE_NOT_PROVEN"
    pair_universe_status: str = "PAIR_UNIVERSE_NOT_PROVEN"
    silver_index_status: str = "SILVER_INDEX_NOT_READY"
    gold_feature_store_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    candidate_discovery_status: str = "CANDIDATE_DISCOVERY_NOT_PROVEN"
    candidate_export_status: str = "CANDIDATE_EXPORT_NOT_PROVEN"
    raw_window_extraction_status: str = "RAW_WINDOW_NOT_PROVEN"
    raw_window_materialization_mode: str = "MATERIALIZE"
    detailed_replay_status: str = "DETAILED_REPLAY_NOT_PROVEN"
    capital_profile_generation_status: str = "CAPITAL_PROFILE_NOT_PROVEN"
    promotion_artifact_status: str = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    final_status: str = "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA"
    blocker_codes: tuple[str, ...] = ()
    feature_row_count: int = Field(default=0, ge=0)
    candidate_sample_cap: int = Field(default=0, ge=0)
    effective_engine_native_sample_size: int = Field(default=10, ge=0)
    engine_count: int = Field(default=4, ge=0)
    candidate_cap_formula: str = ""
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    candidate_discovery_limited: bool = True
    candidate_discovery_limit_reason: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
    temporal_bucket_granularity: str = ""
    temporal_bucket_count_available: int = Field(default=0, ge=0)
    temporal_bucket_count_selected: int = Field(default=0, ge=0)
    temporal_bucket_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    preselection_status: str = "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN"
    replay_input_mode_status: str = "PRESELECTED_ONLY"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    b1_5_policy_mode: str = "conservative_hard_only"
    candidate_count: int = Field(default=0, ge=0)
    unique_candidate_count: int = Field(default=0, ge=0)
    base_event_count: int = Field(default=0, ge=0)
    per_engine_candidate_count: int | None = Field(default=None, ge=0)
    engine_native_candidate_count: int = Field(default=0, ge=0)
    discovery_pre_candidate_count: int = Field(default=0, ge=0)
    engine_native_preselected_count: int = Field(default=0, ge=0)
    preselection_hard_rejected_count: int = Field(default=0, ge=0)
    preselection_soft_flagged_count: int = Field(default=0, ge=0)
    preselection_passed_count: int = Field(default=0, ge=0)
    b2_replay_candidate_count: int = Field(default=0, ge=0)
    trade_eligible_candidate_count: int = Field(default=0, ge=0)
    preselection_rejection_count: int = Field(default=0, ge=0)
    replay_savings_estimate_count: int = Field(default=0, ge=0)
    replay_record_count: int = Field(default=0, ge=0)
    evaluation_record_count: int = Field(default=0, ge=0)
    promotion_record_count: int = Field(default=0, ge=0)
    capital_bucket_record_count: int = Field(default=0, ge=0)
    replay_expansion_factor: float | None = Field(default=None, ge=0.0)
    replay_expansion_axis: str = ""
    candidate_source_status: str = "CANDIDATE_SOURCE_NOT_PROVEN"
    count_semantics_validator_codes: tuple[str, ...] = ()
    matrix_count_inflation_status: str = "COUNT_SEMANTICS_NOT_PROVEN"
    raw_window_count: int = Field(default=0, ge=0)
    raw_windows_total: int = Field(default=0, ge=0)
    trade_windows_found: int = Field(default=0, ge=0)
    trade_windows_missing: int = Field(default=0, ge=0)
    book_windows_found: int = Field(default=0, ge=0)
    book_windows_missing: int = Field(default=0, ge=0)
    ohlcv_windows_found: int = Field(default=0, ge=0)
    ohlcv_windows_missing: int = Field(default=0, ge=0)
    depth20_found: int = Field(default=0, ge=0)
    depth20_missing: int = Field(default=0, ge=0)
    detailed_replay_count: int = Field(default=0, ge=0)
    capital_profile_count: int = Field(default=0, ge=0)
    engine_promotion_count: int = Field(default=0, ge=0)
    pair_promotion_count: int = Field(default=0, ge=0)
    strategy_promotion_count: int = Field(default=0, ge=0)
    sample_size_survival_count: int = Field(default=0, ge=0)
    # Audit 2026-05-06 — provenance + compteurs de véracité.
    # `economic_constants_provenance` documente la SOURCE des champs
    # economiques (expected_edge_bps, spread_bps, slippage_bps,
    # latency_penalty_bps, fee). Tant que ces valeurs sont des constantes
    # codees en dur dans data_factory.py (5.0/4.0/2.0/1.0), ce champ doit
    # rester "HARDCODED_PROXY_CONSTANTS" et le run ne peut pas etre promu.
    economic_constants_provenance: str = "UNKNOWN"
    candidate_truth_status: str = "CANDIDATE_TRUTH_NOT_PROVEN"
    expected_edge_truth_status: str = "EXPECTED_EDGE_TRUTH_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    expected_edge_proxy_count: int = Field(default=0, ge=0)
    expected_edge_governed_count: int = Field(default=0, ge=0)
    expected_edge_model_status: str = "EXPECTED_EDGE_MODEL_NOT_REQUESTED"
    expected_edge_model_artifact_hash: str | None = None
    expected_edge_model_feature_hash: str | None = None
    expected_edge_training_artifact_ref: str = ""
    expected_edge_label_source: str = "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"
    expected_edge_label_fidelity: str = "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    expected_edge_anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
    expected_edge_walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    expected_edge_horizon: int | None = Field(default=None, ge=0)
    expected_edge_purge_window: int | None = Field(default=None, ge=0)
    expected_edge_embargo_window: int | None = Field(default=None, ge=0)
    expected_edge_blocker_codes: tuple[str, ...] = ()
    # `candidate_engine_native_count` compte les candidats issus d'un
    # vrai appel a engine_a/b/c/d.runner. `candidate_proxy_count` compte
    # les candidats fabriques par le proxy COMPAT_FEATURE_DISCOVERY.
    # Tant que candidate_engine_native_count == 0, le run n'a pas de
    # parite moteur live et ne peut pas servir a calibrer A/B/C/D.
    candidate_engine_native_count: int = Field(default=0, ge=0)
    candidate_proxy_count: int = Field(default=0, ge=0)
    executed_trade_count: int = Field(default=0, ge=0)
    statistical_validation_status: str = "STATISTICAL_VALIDATION_NOT_PROVEN"
    statistical_validation_observation_count: int = Field(default=0, ge=0)
    statistical_validation_trial_count: int = Field(default=1, ge=1)
    statistical_validation_benchmark_sharpe: float = 0.0
    statistical_validation_acceptance_floor: float = Field(default=0.95, gt=0.0, lt=1.0)
    statistical_validation_sample_sharpe: float | None = None
    statistical_validation_psr: float | None = Field(default=None, ge=0.0, le=1.0)
    statistical_validation_dsr: float | None = Field(default=None, ge=0.0, le=1.0)
    statistical_validation_stationary_block_length: int = Field(default=1, ge=1)
    statistical_validation_effective_sample_size: float | None = Field(default=None, ge=0.0)
    statistical_validation_min_trl_required: float | None = Field(default=None, ge=0.0)
    statistical_validation_min_trl_satisfied: bool = False
    statistical_validation_psr_passes_floor: bool = False
    statistical_validation_dsr_passes_floor: bool = False
    statistical_validation_blocker_codes: tuple[str, ...] = ()
    # Audit 2026-05-06 (P3a) — Statut du pont microstructure vers les
    # engine runners natifs. Etats possibles :
    # - "ENGINE_NATIVE_NOT_REQUESTED" : engine_native_mode=False (defaut, comportement legacy)
    # - "ENGINE_NATIVE_BRIDGE_READY_STRUCTURE_RESOLVER_PENDING" : pont microstructure
    #   active, 5 records canoniques calcules, mais run_engine_c bloque par les
    #   7 champs structurels manquants (breakout_strength, range_quality, ...)
    # - "ENGINE_NATIVE_FULL_PARITY" : tous les engines invoques avec inputs reels
    #   (cible long terme, hors session 2026-05-06)
    # - "ENGINE_NATIVE_FAILED_<reason>" : echec lors du calcul des records
    engine_native_status: str = "ENGINE_NATIVE_NOT_REQUESTED"
    engine_native_records_built: int = Field(default=0, ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    artifact_hash: str | None = None


class StrategyLadderReportSummary(BaseModel, frozen=True):
    """Final ladder report summary surfaced to disk and cockpit."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    backtest_architecture_status: str = "PARTIALLY_UPDATED_REPLAY_BACKTEST"
    data_factory_status: str = "DATA_FACTORY_NOT_PROVEN"
    raw_source_status: str = "RAW_SOURCE_NOT_PROVEN"
    pair_universe_status: str = "PAIR_UNIVERSE_NOT_PROVEN"
    silver_index_status: str = "SILVER_INDEX_NOT_READY"
    gold_feature_store_status: str = "GOLD_FEATURE_STORE_NOT_READY"
    orderbook_reconstruction_status: str = "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    ml_mode_status: str = "ML_MODE_OFF"
    feature_store_status: str = "FEATURE_STORE_NOT_PROVEN"
    candidate_discovery_status: str = "CANDIDATE_DISCOVERY_NOT_PROVEN"
    candidate_export_status: str = "CANDIDATE_EXPORT_NOT_PROVEN"
    raw_window_extraction_status: str = "RAW_WINDOW_NOT_PROVEN"
    raw_window_materialization_mode: str = "MATERIALIZE"
    detailed_replay_status: str = "DETAILED_REPLAY_NOT_PROVEN"
    capital_profile_generation_status: str = "CAPITAL_PROFILE_NOT_PROVEN"
    promotion_artifact_status: str = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    final_status: str = "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA"
    blocker_codes: tuple[str, ...] = ()
    feature_names: tuple[str, ...] = ()
    silver_index_path: str = ""
    workflow_run_id: str = ""
    phase_run_id: str = ""
    parent_workflow_ref: str = ""
    candidate_sample_cap: int = Field(default=0, ge=0)
    effective_engine_native_sample_size: int = Field(default=10, ge=0)
    engine_count: int = Field(default=4, ge=0)
    candidate_cap_formula: str = ""
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    candidate_discovery_limited: bool = True
    candidate_discovery_limit_reason: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
    temporal_bucket_granularity: str = ""
    temporal_bucket_count_available: int = Field(default=0, ge=0)
    temporal_bucket_count_selected: int = Field(default=0, ge=0)
    temporal_bucket_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    preselection_status: str = "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN"
    replay_input_mode_status: str = "PRESELECTED_ONLY"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    b1_5_policy_mode: str = "conservative_hard_only"
    candidate_count: int = Field(default=0, ge=0)
    unique_candidate_count: int = Field(default=0, ge=0)
    base_event_count: int = Field(default=0, ge=0)
    per_engine_candidate_count: int | None = Field(default=None, ge=0)
    engine_native_candidate_count: int = Field(default=0, ge=0)
    discovery_pre_candidate_count: int = Field(default=0, ge=0)
    engine_native_preselected_count: int = Field(default=0, ge=0)
    preselection_hard_rejected_count: int = Field(default=0, ge=0)
    preselection_soft_flagged_count: int = Field(default=0, ge=0)
    preselection_passed_count: int = Field(default=0, ge=0)
    b2_replay_candidate_count: int = Field(default=0, ge=0)
    trade_eligible_candidate_count: int = Field(default=0, ge=0)
    preselection_rejection_count: int = Field(default=0, ge=0)
    replay_savings_estimate_count: int = Field(default=0, ge=0)
    replay_record_count: int = Field(default=0, ge=0)
    evaluation_record_count: int = Field(default=0, ge=0)
    promotion_record_count: int = Field(default=0, ge=0)
    capital_bucket_record_count: int = Field(default=0, ge=0)
    replay_expansion_factor: float | None = Field(default=None, ge=0.0)
    replay_expansion_axis: str = ""
    candidate_source_status: str = "CANDIDATE_SOURCE_NOT_PROVEN"
    count_semantics_validator_codes: tuple[str, ...] = ()
    matrix_count_inflation_status: str = "COUNT_SEMANTICS_NOT_PROVEN"
    raw_window_count: int = Field(default=0, ge=0)
    raw_windows_total: int = Field(default=0, ge=0)
    trade_windows_found: int = Field(default=0, ge=0)
    trade_windows_missing: int = Field(default=0, ge=0)
    book_windows_found: int = Field(default=0, ge=0)
    book_windows_missing: int = Field(default=0, ge=0)
    ohlcv_windows_found: int = Field(default=0, ge=0)
    ohlcv_windows_missing: int = Field(default=0, ge=0)
    depth20_found: int = Field(default=0, ge=0)
    depth20_missing: int = Field(default=0, ge=0)
    detailed_replay_count: int = Field(default=0, ge=0)
    capital_profile_count: int = Field(default=0, ge=0)
    engine_promotion_count: int = Field(default=0, ge=0)
    pair_promotion_count: int = Field(default=0, ge=0)
    strategy_promotion_count: int = Field(default=0, ge=0)
    sample_size_survival_count: int = Field(default=0, ge=0)
    economic_constants_provenance: str = "UNKNOWN"
    candidate_truth_status: str = "CANDIDATE_TRUTH_NOT_PROVEN"
    expected_edge_truth_status: str = "EXPECTED_EDGE_TRUTH_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    expected_edge_proxy_count: int = Field(default=0, ge=0)
    expected_edge_governed_count: int = Field(default=0, ge=0)
    expected_edge_model_status: str = "EXPECTED_EDGE_MODEL_NOT_REQUESTED"
    expected_edge_model_artifact_hash: str | None = None
    expected_edge_model_feature_hash: str | None = None
    expected_edge_training_artifact_ref: str = ""
    expected_edge_label_source: str = "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN"
    expected_edge_label_fidelity: str = "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    expected_edge_anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
    expected_edge_walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    expected_edge_horizon: int | None = Field(default=None, ge=0)
    expected_edge_purge_window: int | None = Field(default=None, ge=0)
    expected_edge_embargo_window: int | None = Field(default=None, ge=0)
    expected_edge_blocker_codes: tuple[str, ...] = ()
    candidate_engine_native_count: int = Field(default=0, ge=0)
    candidate_proxy_count: int = Field(default=0, ge=0)
    executed_trade_count: int = Field(default=0, ge=0)
    statistical_validation_status: str = "STATISTICAL_VALIDATION_NOT_PROVEN"
    statistical_validation_observation_count: int = Field(default=0, ge=0)
    statistical_validation_trial_count: int = Field(default=1, ge=1)
    statistical_validation_benchmark_sharpe: float = 0.0
    statistical_validation_acceptance_floor: float = Field(default=0.95, gt=0.0, lt=1.0)
    statistical_validation_sample_sharpe: float | None = None
    statistical_validation_psr: float | None = Field(default=None, ge=0.0, le=1.0)
    statistical_validation_dsr: float | None = Field(default=None, ge=0.0, le=1.0)
    statistical_validation_stationary_block_length: int = Field(default=1, ge=1)
    statistical_validation_effective_sample_size: float | None = Field(default=None, ge=0.0)
    statistical_validation_min_trl_required: float | None = Field(default=None, ge=0.0)
    statistical_validation_min_trl_satisfied: bool = False
    statistical_validation_psr_passes_floor: bool = False
    statistical_validation_dsr_passes_floor: bool = False
    statistical_validation_blocker_codes: tuple[str, ...] = ()
    engine_native_status: str = "ENGINE_NATIVE_NOT_REQUESTED"
    engine_native_records_built: int = Field(default=0, ge=0)
    depth_status_distribution: dict[str, int] = Field(default_factory=dict)
    fill_realism_status_distribution: dict[str, int] = Field(default_factory=dict)
    capital_bucket_verdicts: dict[str, str] = Field(default_factory=dict)
    engine_verdicts: dict[str, str] = Field(default_factory=dict)
    pair_verdicts: dict[str, str] = Field(default_factory=dict)
    strategy_verdicts: dict[str, str] = Field(default_factory=dict)
    governed_audit_evidence_index_path: str = ""
    governed_evidence_status: str = "EVIDENCE_CLASS_NOT_PROVEN"
    audited_evidence_count: int = Field(default=0, ge=0)
    scratch_only_evidence_count: int = Field(default=0, ge=0)
    promotion_grade_evidence_count: int = Field(default=0, ge=0)
    run_manifest_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    capital_profiles_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    engine_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    pair_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    strategy_promotion_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    sample_size_survival_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    trade_detail_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    refusal_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    loss_analysis_ledger_evidence_class: str = "EVIDENCE_CLASS_NOT_PROVEN"
    evidence_audit_blocker_codes: tuple[str, ...] = ()
    promotion_blockers: tuple[str, ...] = ()
    recommended_next_action: str = "RUN_SHADOW_OR_FIX_BLOCKERS"
    robustness_score: str | float = "NOT_COMPUTED"
    parameter_stability_score: str | float = "NOT_COMPUTED"
    trade_lifecycle_status: str = "NOT_COMPUTED"
    regret_analysis_status: str = "NOT_COMPUTED"
    engine_interaction_status: str = "NOT_COMPUTED"
    created_at: datetime | None = None
    artifact_hash: str | None = None


__all__ = [
    "FeatureScalar",
    "StrategyLadderRequest",
    "StrategyLadderFeatureRow",
    "StrategyLadderFeatureStoreResult",
    "StrategyLadderCandidateEvent",
    "StrategyLadderCandidateSummary",
    "StrategyLadderRawWindowManifest",
    "StrategyLadderBucketReplayResult",
    "StrategyLadderDetailedReplayArtifact",
    "StrategyLadderRunManifest",
    "StrategyLadderReportSummary",
    "deterministic_payload_hash",
]
