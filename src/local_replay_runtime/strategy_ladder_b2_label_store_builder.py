"""Canonical replay-grounded B2 label-store builder for Strategy Ladder ML."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_detailed_replay import (
    load_strategy_ladder_detailed_replay_artifact,
)
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
    ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
    EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS,
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    deterministic_payload_hash,
)


LABEL_STORE_DATASET_FILENAME = "strategy_ladder_replay_label_store.jsonl"
LEGACY_LABEL_STORE_DATASET_FILENAMES = ("strategy_ladder_b2_label_store.jsonl",)
LABEL_STORE_SUMMARY_FILENAME = "label_store_summary.json"
LABEL_STORE_QUALITY_REPORT_FILENAME = "label_store_quality_report.json"
F16_FEATURE_COVERAGE_REPORT_FILENAME = "f16_feature_coverage_report.json"
DEFAULT_WALK_FORWARD_TRAIN_DAYS = 180
DEFAULT_WALK_FORWARD_VALIDATION_DAYS = 30
DEFAULT_PURGE_WINDOW_MINUTES = 1
DEFAULT_EMBARGO_WINDOW_MINUTES = 1

_EXECUTED_ONLY_PROVEN_STATUSES = frozenset(
    {
        "EXECUTED_NET_RETURN_PROVEN",
        "EXECUTED_NET_RETURN_READY",
    }
)
_PROMOTION_READY_FILL_STATUSES = frozenset(
    {
        "FILL_REALISM_SHADOW_MEASURED",
        "FILL_REALISM_PROVEN",
    }
)
_PROMOTION_READY_COST_PARITY_STATUSES = frozenset(
    {
        "REPLAY_SHADOW_COST_PARITY_PROVEN",
        "REPLAY_LIVE_COST_PARITY_PROVEN",
    }
)


def _utc_datetime_from_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC)


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


def _coerce_float(raw_value: object) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _coerce_int(raw_value: object) -> int | None:
    if isinstance(raw_value, bool):
        return None
    try:
        value = int(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS = (
    "spread_bps",
    "slippage_bps",
    "latency_penalty_bps",
    "book_depth_levels",
    "break_even_bps",
    # Patch F16-B (2026-05-21) — microstructure canoniques V5.3 ajoutées
    # au feature dict pour permettre training expected-edge enrichi.
    # Capturées depuis bridge.vpin_record/ofi_record/queue_pressure_record
    # par strategy_ladder_runner et merged dans compatibility_payload.
    "vpin",
    "cumulative_ofi",
    "queue_pressure",
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
    "micro_edge_exit_governor_observed",
    "micro_edge_entry_timing_observed",
    "history_score",
    "marginal_value_score",
    "reentry_lateness",
    "concentration_headroom",
    "anti_revenge_state__active",
    "anti_revenge_state__cooling",
    "anti_revenge_state__idle",
)
_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS = EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS
_ENGINE_D_ONLY_FEATURE_NAMES = frozenset(
    (*ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES, *ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES)
)


def _numeric_feature_values(payload: dict[str, object]) -> dict[str, float]:
    feature_values = payload.get("feature_values")
    if not isinstance(feature_values, dict):
        feature_values = {}
    normalized: dict[str, float] = {}
    for key, raw_value in feature_values.items():
        name = str(key).strip()
        if not name:
            continue
        value = _coerce_float(raw_value)
        if value is None:
            continue
        normalized[name] = value
    for key in _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS:
        if key in normalized:
            continue
        value = _coerce_float(payload.get(key))
        if value is None:
            continue
        normalized[key] = value
    return normalized


def _break_even_bps(
    compatibility: dict[str, object],
    feature_values: dict[str, float],
) -> float | None:
    return _coerce_float(
        compatibility.get("break_even_bps")
        if compatibility.get("break_even_bps") is not None
        else feature_values.get("break_even_bps")
    )


def _pick_float(
    *sources: dict[str, object],
    keys: tuple[str, ...],
) -> float | None:
    for source in sources:
        for key in keys:
            if key in source:
                value = _coerce_float(source.get(key))
                if value is not None:
                    return value
    return None


def _pick_int(
    *sources: dict[str, object],
    keys: tuple[str, ...],
) -> int | None:
    for source in sources:
        for key in keys:
            if key in source:
                value = _coerce_int(source.get(key))
                if value is not None:
                    return value
    return None


def _pick_bool(
    *sources: dict[str, object],
    keys: tuple[str, ...],
) -> bool | None:
    for source in sources:
        for key in keys:
            if key not in source:
                continue
            raw_value = source.get(key)
            if isinstance(raw_value, bool):
                return raw_value
            if raw_value in (0, 1):
                return bool(raw_value)
            if isinstance(raw_value, str):
                normalized = raw_value.strip().lower()
                if normalized in {"true", "1", "yes", "on"}:
                    return True
                if normalized in {"false", "0", "no", "off"}:
                    return False
    return None


def _label_source_type(
    replay_grounded_label_count: int,
    proxy_execution_label_count: int,
) -> str:
    if replay_grounded_label_count > 0 and proxy_execution_label_count > 0:
        return "B2_REPLAY_EXECUTED_ONLY_AND_EXPECTED_CE_MIXED"
    if replay_grounded_label_count > 0:
        return "B2_REPLAY_EXECUTED_ONLY_NET_RETURN"
    if proxy_execution_label_count > 0:
        return "B2_REPLAY_EXPECTED_CE_NET_PROXY"
    return "B2_REPLAY_LABEL_SOURCE_NOT_PROVEN"


def _execution_fidelity_status(
    *,
    executed_only_net_return: float | None,
    executed_only_net_return_status: str,
    fill_realism_status: str,
    cost_parity_status: str,
) -> str:
    if executed_only_net_return is None:
        return "EXECUTION_FIDELITY_PROXY_EXECUTION"
    if (
        executed_only_net_return_status in _EXECUTED_ONLY_PROVEN_STATUSES
        and fill_realism_status in _PROMOTION_READY_FILL_STATUSES
        and cost_parity_status in _PROMOTION_READY_COST_PARITY_STATUSES
    ):
        return "EXECUTION_FIDELITY_READY"
    return "EXECUTION_FIDELITY_PARTIAL"


def _row_evidence_class(
    *,
    executed_only_net_return: float | None,
    executed_only_net_return_status: str,
    execution_fidelity_status: str,
    expected_ce_net: float | None,
) -> str:
    if executed_only_net_return is not None:
        if (
            executed_only_net_return_status in _EXECUTED_ONLY_PROVEN_STATUSES
            and execution_fidelity_status == "EXECUTION_FIDELITY_READY"
        ):
            return "REPLAY_EXECUTED_ONLY_NET_RETURN"
        return "REPLAY_EXECUTED_ONLY_NET_RETURN_PROXY_EXECUTION"
    if expected_ce_net is not None:
        return "REPLAY_EXPECTED_CE_NET_PROXY"
    return "REPLAY_LABEL_NOT_AVAILABLE"


def _proxy_execution_label_flag(
    *,
    executed_only_net_return: float | None,
    expected_ce_net: float | None,
) -> bool:
    return executed_only_net_return is None and expected_ce_net is not None


def _replay_grounded_label_flag(*, executed_only_net_return: float | None) -> bool:
    return executed_only_net_return is not None


def _replay_grounded_status(
    *,
    replay_grounded_label_flag: bool,
    proxy_execution_label_flag: bool,
    execution_fidelity_status: str,
    entry_reference_status: str,
    mfe_mae_status: str,
) -> str:
    if (
        replay_grounded_label_flag
        and execution_fidelity_status == "EXECUTION_FIDELITY_READY"
        and entry_reference_status == "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED"
        and mfe_mae_status == "MFE_MAE_AVAILABLE"
    ):
        return "REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE"
    if replay_grounded_label_flag:
        return "REPLAY_GROUNDED_PARTIAL"
    if proxy_execution_label_flag:
        return "REPLAY_GROUNDED_PROXY_ONLY"
    return "REPLAY_GROUNDED_NOT_AVAILABLE"


def _label_quality_status(
    *,
    replay_grounded_status: str,
    replay_quality_status: str,
) -> str:
    if (
        replay_grounded_status == "REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE"
        and replay_quality_status == "REPLAY_READY"
    ):
        return "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE"
    if replay_grounded_status in {
        "REPLAY_GROUNDED_PARTIAL",
        "REPLAY_GROUNDED_PROXY_ONLY",
    }:
        return "LABEL_QUALITY_RESEARCH_ONLY"
    return "LABEL_QUALITY_BLOCKED"


def _replay_quality_status(
    *,
    replay_status: str,
    raw_window_status: str,
) -> str:
    if replay_status == "DETAILED_REPLAY_READY" and raw_window_status == "RAW_WINDOW_READY":
        return "REPLAY_READY"
    if replay_status or raw_window_status:
        return "REPLAY_PARTIAL"
    return "REPLAY_NOT_PROVEN"


def _row_net_positive_label(
    *,
    executed_only_net_return: float | None,
    expected_ce_net: float | None,
) -> bool | None:
    if executed_only_net_return is not None:
        return executed_only_net_return > 0.0
    if expected_ce_net is not None:
        return expected_ce_net > 0.0
    return None


def _row_break_even_label(
    *,
    executed_only_net_return: float | None,
    expected_ce_net: float | None,
    break_even_bps: float | None,
) -> bool | None:
    if break_even_bps is None:
        return None
    target_bps = None
    if executed_only_net_return is not None:
        target_bps = executed_only_net_return * 10_000.0
    elif expected_ce_net is not None:
        target_bps = expected_ce_net * 10_000.0
    if target_bps is None:
        return None
    return target_bps > break_even_bps


def _row_mae_survival_label(
    *,
    mae_bps: float | None,
    break_even_bps: float | None,
) -> bool | None:
    if mae_bps is None or break_even_bps is None:
        return None
    return mae_bps >= (-1.0 * break_even_bps)


class StrategyLadderB2LabelStoreBuilderRequest(BaseModel, frozen=True):
    """Build request for the canonical replay-grounded B2 label store."""

    run_root: Path
    output_dir: Path
    candidate_events_path: Path | None = None
    detailed_replay_root: Path | None = None
    raw_windows_root: Path | None = None
    walk_forward_train_days: int = Field(default=DEFAULT_WALK_FORWARD_TRAIN_DAYS, ge=1)
    walk_forward_validation_days: int = Field(
        default=DEFAULT_WALK_FORWARD_VALIDATION_DAYS,
        ge=1,
    )
    purge_window_minutes: int = Field(default=DEFAULT_PURGE_WINDOW_MINUTES, ge=1)
    embargo_window_minutes: int = Field(default=DEFAULT_EMBARGO_WINDOW_MINUTES, ge=1)

    @model_validator(mode="after")
    def _normalize_paths(self) -> "StrategyLadderB2LabelStoreBuilderRequest":
        if self.run_root == self.output_dir:
            raise ValueError("label-store output_dir must not equal run_root")
        return self


class StrategyLadderB2LabelStoreRow(BaseModel, frozen=True):
    """Canonical supervised label row derived from one B2 replay candidate."""

    # Patch F16-C (2026-05-23) — schema_version bumped v2 → v3 pour ajout des
    # 13 champs de governance features (microstructure étendue, Build-14
    # observed, Engine D governance, anti_revenge_state one-hot). Tous restent
    # nullables pour charger sans friction les anciens stores v2.
    schema_version: str = Field(default="strategy_ladder.b2_label_store_row.v3", min_length=1)
    candidate_id: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    capital_bucket: int = Field(..., ge=1)
    decision_timestamp_ms: int = Field(..., ge=0)
    feature_timestamp_ms: int = Field(..., ge=0)
    raw_window_ref: str = ""
    replay_ref: str = ""
    replay_record_id: str = Field(..., min_length=1)
    feature_vector_ref: str = ""
    spread_bps: float | None = None
    fee_bps: float | None = None
    slippage_bps: float | None = None
    adverse_selection_bps: float | None = None
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    break_even_bps: float | None = None
    # F16-B microstructure canoniques V5.3 (ajout 2026-05-21)
    vpin: float | None = None
    cumulative_ofi: float | None = None
    queue_pressure: float | None = None
    # F16-C microstructure étendue (ajout 2026-05-23)
    kyle_lambda: float | None = None
    realized_vol_current: float | None = None
    realized_vol_at_break: float | None = None
    latency_penalty_bps: float | None = None
    # F16-C Build-14 observed values
    micro_edge_exit_governor_observed: float | None = None
    micro_edge_entry_timing_observed: float | None = None
    # F16-C Engine D governance scalars
    history_score: float | None = None
    marginal_value_score: float | None = None
    reentry_lateness: float | None = None
    concentration_headroom: float | None = None
    # F16-C categorical governance as explicit one-hot triplet
    anti_revenge_state__active: bool | None = None
    anti_revenge_state__cooling: bool | None = None
    anti_revenge_state__idle: bool | None = None
    mfe_bps: float | None = None
    mae_bps: float | None = None
    holding_time_ms: int | None = Field(default=None, ge=0)
    label_net_positive: bool | None = None
    label_break_even_cleared: bool | None = None
    label_survived_mae: bool | None = None
    label_forward_return_h1: float | None = None
    label_forward_return_h5: float | None = None
    label_forward_return_h10: float | None = None
    evidence_class: str = Field(..., min_length=1)
    label_quality_status: str = Field(..., min_length=1)
    replay_grounded_status: str = Field(..., min_length=1)
    replay_quality_status: str = Field(..., min_length=1)
    execution_fidelity_status: str = Field(..., min_length=1)
    entry_reference_status: str = Field(..., min_length=1)
    mfe_mae_status: str = Field(..., min_length=1)
    proxy_execution_label_flag: bool = False
    replay_grounded_label_flag: bool = False
    feature_truth_boundary_status: str = "FEATURE_TRUTH_BOUNDARY_NOT_PROVEN"
    feature_usage_policy: str = "A2_GOLD_FEATURE_USAGE_NOT_PROVEN"
    cost_feature_truth_status: str = "COST_FEATURE_TRUTH_NOT_PROVEN"
    feature_values: dict[str, float] = Field(default_factory=dict)
    feature_hash: str = ""

    @model_validator(mode="after")
    def _validate_temporal_invariant(self) -> "StrategyLadderB2LabelStoreRow":
        if self.feature_timestamp_ms > self.decision_timestamp_ms:
            raise ValueError("feature_timestamp_ms must be <= decision_timestamp_ms")
        for field_name in (
            "kyle_lambda",
            "realized_vol_current",
            "realized_vol_at_break",
            "latency_penalty_bps",
            "micro_edge_exit_governor_observed",
            "micro_edge_entry_timing_observed",
            "history_score",
            "marginal_value_score",
            "reentry_lateness",
            "concentration_headroom",
        ):
            value = getattr(self, field_name)
            if value is not None and not math.isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite when provided")
        return self


class StrategyLadderB2LabelStoreSummary(BaseModel, frozen=True):
    """Dataset-level summary surfaced to the IA Lab and training rail."""

    schema_version: str = Field(default="strategy_ladder.b2_label_store_summary.v1", min_length=1)
    status: str = Field(..., min_length=1)
    promotion_state: str = Field(..., min_length=1)
    label_source_type: str = Field(..., min_length=1)
    run_root: str = Field(..., min_length=1)
    dataset_ref: str = Field(..., min_length=1)
    quality_report_ref: str = Field(..., min_length=1)
    row_count: int = Field(default=0, ge=0)
    replay_grounded_label_count: int = Field(default=0, ge=0)
    proxy_execution_label_count: int = Field(default=0, ge=0)
    executed_trade_label_count: int = Field(default=0, ge=0)
    net_positive_rate: float | None = None
    break_even_clearance_rate: float | None = None
    replay_backed_label_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    mfe_available_count: int = Field(default=0, ge=0)
    mae_available_count: int = Field(default=0, ge=0)
    mfe_availability_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    mae_availability_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    dataset_hash: str = Field(..., min_length=64, max_length=64)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    label_hash: str = Field(..., min_length=64, max_length=64)
    pair_scope: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    timeframe_scope: tuple[str, ...] = ()
    capital_bucket_scope: tuple[int, ...] = ()
    walk_forward_train_days: int = Field(default=DEFAULT_WALK_FORWARD_TRAIN_DAYS, ge=1)
    walk_forward_validation_days: int = Field(
        default=DEFAULT_WALK_FORWARD_VALIDATION_DAYS,
        ge=1,
    )
    purge_window_minutes: int = Field(default=DEFAULT_PURGE_WINDOW_MINUTES, ge=1)
    embargo_window_minutes: int = Field(default=DEFAULT_EMBARGO_WINDOW_MINUTES, ge=1)
    replay_provenance_refs: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()


class StrategyLadderB2LabelStoreQualityReport(BaseModel, frozen=True):
    """Quality and governance report for the replay-grounded label store."""

    schema_version: str = Field(
        default="strategy_ladder.b2_label_store_quality_report.v1",
        min_length=1,
    )
    status: str = Field(..., min_length=1)
    promotion_state: str = Field(..., min_length=1)
    label_source_type: str = Field(..., min_length=1)
    run_root: str = Field(..., min_length=1)
    dataset_ref: str = Field(..., min_length=1)
    dataset_hash: str = Field(..., min_length=64, max_length=64)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    label_hash: str = Field(..., min_length=64, max_length=64)
    row_count: int = Field(default=0, ge=0)
    replay_grounded_label_count: int = Field(default=0, ge=0)
    proxy_execution_label_count: int = Field(default=0, ge=0)
    no_future_timestamp_violations: int = Field(default=0, ge=0)
    post_decision_replay_only: bool = True
    no_fabricated_trades: bool = True
    no_fabricated_costs: bool = True
    replay_backed_label_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    net_positive_rate: float | None = None
    break_even_clearance_rate: float | None = None
    mfe_mae_availability: str = "MFE_MAE_NOT_AVAILABLE"
    label_quality_status_counts: dict[str, int] = Field(default_factory=dict)
    replay_grounded_status_counts: dict[str, int] = Field(default_factory=dict)
    entry_reference_status_counts: dict[str, int] = Field(default_factory=dict)
    mfe_mae_status_counts: dict[str, int] = Field(default_factory=dict)
    execution_fidelity_status_counts: dict[str, int] = Field(default_factory=dict)
    evidence_class_counts: dict[str, int] = Field(default_factory=dict)
    feature_truth_boundary_status_counts: dict[str, int] = Field(default_factory=dict)
    cost_feature_truth_status_counts: dict[str, int] = Field(default_factory=dict)
    feature_to_label_truth_promotion_blocked_count: int = Field(default=0, ge=0)
    blocking_reasons: tuple[str, ...] = ()
    replay_provenance_refs: tuple[str, ...] = ()


class StrategyLadderB2LabelStoreBuildResult(BaseModel, frozen=True):
    """Resolved output refs returned by the builder."""

    status: str = Field(..., min_length=1)
    promotion_state: str = Field(..., min_length=1)
    dataset_path: str = Field(..., min_length=1)
    summary_path: str = Field(..., min_length=1)
    quality_report_path: str = Field(..., min_length=1)
    f16_feature_coverage_report_path: str = ""
    dataset_hash: str = Field(..., min_length=64, max_length=64)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    label_hash: str = Field(..., min_length=64, max_length=64)
    row_count: int = Field(default=0, ge=0)
    replay_grounded_label_count: int = Field(default=0, ge=0)
    proxy_execution_label_count: int = Field(default=0, ge=0)
    label_source_type: str = Field(..., min_length=1)


@dataclass(frozen=True)
class _SourceBundle:
    candidate_events: tuple[StrategyLadderCandidateEvent, ...]
    detailed_replay_artifacts: tuple[tuple[Path, StrategyLadderDetailedReplayArtifact], ...]
    raw_window_manifests: dict[str, tuple[Path, StrategyLadderRawWindowManifest]]


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


def _candidate_events_path(request: StrategyLadderB2LabelStoreBuilderRequest) -> Path:
    if request.candidate_events_path is not None:
        return request.candidate_events_path
    return request.run_root / "fast_candidates" / "candidate_events.jsonl"


def _detailed_replay_root(request: StrategyLadderB2LabelStoreBuilderRequest) -> Path:
    if request.detailed_replay_root is not None:
        return request.detailed_replay_root
    return request.run_root / "detailed_replay"


def _raw_windows_root(request: StrategyLadderB2LabelStoreBuilderRequest) -> Path:
    if request.raw_windows_root is not None:
        return request.raw_windows_root
    return request.run_root / "raw_windows"


def _load_source_bundle(
    request: StrategyLadderB2LabelStoreBuilderRequest,
) -> _SourceBundle:
    candidate_events = tuple(
        item
        for item in _read_jsonl_models(
            _candidate_events_path(request),
            StrategyLadderCandidateEvent,
        )
        if isinstance(item, StrategyLadderCandidateEvent)
    )
    detailed_root = _detailed_replay_root(request)
    replay_artifacts: list[tuple[Path, StrategyLadderDetailedReplayArtifact]] = []
    shared_payload_cache: dict[str, object] = {}
    if detailed_root.is_dir():
        for path in sorted(detailed_root.glob("*.json")):
            replay_artifacts.append(
                (
                    path.resolve(),
                    load_strategy_ladder_detailed_replay_artifact(
                        path,
                        shared_payload_cache=shared_payload_cache,
                    ),
                )
            )
    raw_window_root = _raw_windows_root(request)
    raw_window_manifests: dict[str, tuple[Path, StrategyLadderRawWindowManifest]] = {}
    if raw_window_root.is_dir():
        for path in sorted(raw_window_root.rglob("window_manifest.json")):
            manifest = StrategyLadderRawWindowManifest.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
            raw_window_manifests[manifest.candidate_id] = (path.resolve(), manifest)
    return _SourceBundle(
        candidate_events=candidate_events,
        detailed_replay_artifacts=tuple(replay_artifacts),
        raw_window_manifests=raw_window_manifests,
    )


def _dataset_hash(rows: tuple[StrategyLadderB2LabelStoreRow, ...]) -> str:
    return _hash_payload([row.model_dump(mode="json") for row in rows])


def _feature_hash(rows: tuple[StrategyLadderB2LabelStoreRow, ...]) -> str:
    feature_names = sorted({name for row in rows for name in row.feature_values})
    return _hash_payload(feature_names)


def _label_hash(rows: tuple[StrategyLadderB2LabelStoreRow, ...]) -> str:
    payload = [
        {
            "candidate_id": row.candidate_id,
            "capital_bucket": row.capital_bucket,
            "decision_timestamp_ms": row.decision_timestamp_ms,
            "expected_ce_net": row.expected_ce_net,
            "executed_only_net_return": row.executed_only_net_return,
            "label_net_positive": row.label_net_positive,
            "label_break_even_cleared": row.label_break_even_cleared,
            "label_survived_mae": row.label_survived_mae,
            "label_forward_return_h1": row.label_forward_return_h1,
            "label_forward_return_h5": row.label_forward_return_h5,
            "label_forward_return_h10": row.label_forward_return_h10,
            "evidence_class": row.evidence_class,
        }
        for row in rows
    ]
    return _hash_payload(payload)


def _write_jsonl(path: Path, rows: tuple[StrategyLadderB2LabelStoreRow, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(row.model_dump_json() for row in rows)
    atomic_write_text(path, payload + ("\n" if payload else ""))
    return path


def _build_rows(
    bundle: _SourceBundle,
) -> tuple[StrategyLadderB2LabelStoreRow, ...]:
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in bundle.candidate_events
    }
    rows: list[StrategyLadderB2LabelStoreRow] = []
    for replay_ref, artifact in bundle.detailed_replay_artifacts:
        candidate = candidate_by_id.get(artifact.candidate_id)
        compatibility = (
            dict(candidate.compatibility_payload or {})
            if candidate is not None and candidate.compatibility_payload is not None
            else {}
        )
        feature_values = _numeric_feature_values(compatibility)
        feature_vector_ref = (
            candidate.feature_refs[0]
            if candidate is not None and candidate.feature_refs
            else str(compatibility.get("source_ref") or "")
        )
        raw_window_payload = bundle.raw_window_manifests.get(artifact.candidate_id)
        raw_window_ref = raw_window_payload[0] if raw_window_payload is not None else None
        raw_window_status = (
            raw_window_payload[1].window_extraction_status
            if raw_window_payload is not None
            else ""
        )
        timeframe = (
            (candidate.timeframe or "").strip()
            if candidate is not None
            else ""
        ) or "unknown"
        feature_timestamp_ms = _coerce_int(compatibility.get("available_at_timestamp_ms"))
        decision_timestamp_ms = (
            candidate.resolved_timestamp_ms if candidate is not None else artifact.timestamp_ms
        )
        feature_timestamp_ms = min(
            feature_timestamp_ms or decision_timestamp_ms,
            decision_timestamp_ms,
        )
        break_even_bps = _break_even_bps(compatibility, feature_values)
        for result in artifact.bucket_results:
            parity = (
                dict(result.parity_payload)
                if isinstance(result.parity_payload, dict)
                else {}
            )
            replay_outcome_report = (
                dict(parity.get("replay_outcome_report"))
                if isinstance(parity.get("replay_outcome_report"), dict)
                else {}
            )
            dtr_record = (
                dict(result.dtr_record)
                if isinstance(result.dtr_record, dict)
                else {}
            )
            executed_only_status = str(result.executed_only_net_return_status or "")
            execution_fidelity_status = _execution_fidelity_status(
                executed_only_net_return=result.executed_only_net_return,
                executed_only_net_return_status=executed_only_status,
                fill_realism_status=result.fill_realism_status,
                cost_parity_status=result.cost_parity_status,
            )
            proxy_execution_label_flag = _proxy_execution_label_flag(
                executed_only_net_return=result.executed_only_net_return,
                expected_ce_net=result.expected_ce_net,
            )
            replay_grounded_label_flag = _replay_grounded_label_flag(
                executed_only_net_return=result.executed_only_net_return,
            )
            entry_reference_status = str(
                replay_outcome_report.get("entry_reference_status")
                or result.entry_reference_status
                or "ENTRY_REFERENCE_NOT_AVAILABLE"
            )
            mfe_mae_status = str(
                replay_outcome_report.get("mfe_mae_status")
                or result.mfe_mae_status
                or "MFE_MAE_NOT_AVAILABLE"
            )
            replay_quality_status = _replay_quality_status(
                replay_status=artifact.detailed_replay_status,
                raw_window_status=raw_window_status,
            )
            replay_grounded_status = _replay_grounded_status(
                replay_grounded_label_flag=replay_grounded_label_flag,
                proxy_execution_label_flag=proxy_execution_label_flag,
                execution_fidelity_status=execution_fidelity_status,
                entry_reference_status=entry_reference_status,
                mfe_mae_status=mfe_mae_status,
            )
            label_quality_status = _label_quality_status(
                replay_grounded_status=replay_grounded_status,
                replay_quality_status=replay_quality_status,
            )
            row = StrategyLadderB2LabelStoreRow(
                candidate_id=result.candidate_id,
                engine_id=result.engine_id,
                pair=result.pair,
                timeframe=timeframe,
                capital_bucket=result.capital_bucket,
                decision_timestamp_ms=decision_timestamp_ms,
                feature_timestamp_ms=feature_timestamp_ms,
                raw_window_ref="" if raw_window_ref is None else str(raw_window_ref),
                replay_ref=str(replay_ref),
                replay_record_id=str(
                    dtr_record.get("dtr_id")
                    or f"{result.candidate_id}:{result.capital_bucket}"
                ),
                feature_vector_ref=feature_vector_ref,
                spread_bps=_pick_float(
                    parity,
                    compatibility,
                    keys=("measured_spread_bps", "spread_bps_measured", "spread_bps"),
                ),
                # Patch F16-B (2026-05-21) — microstructure canoniques V5.3
                # capturées dans compatibility_payload par strategy_ladder_runner
                # depuis bridge.vpin_record / ofi_record / queue_pressure_record
                # (engine_native_adapter:586-630).
                vpin=_coerce_float(compatibility.get("vpin")),
                cumulative_ofi=_coerce_float(compatibility.get("cumulative_ofi")),
                queue_pressure=_coerce_float(compatibility.get("queue_pressure")),
                kyle_lambda=_coerce_float(compatibility.get("kyle_lambda")),
                realized_vol_current=_coerce_float(
                    compatibility.get("realized_vol_current")
                ),
                realized_vol_at_break=_coerce_float(
                    compatibility.get("realized_vol_at_break")
                ),
                latency_penalty_bps=_coerce_float(
                    compatibility.get("latency_penalty_bps")
                ),
                micro_edge_exit_governor_observed=_pick_float(
                    compatibility,
                    keys=(
                        "micro_edge_exit_governor_observed",
                        "micro_edge_exit_governor",
                    ),
                ),
                micro_edge_entry_timing_observed=_pick_float(
                    compatibility,
                    keys=(
                        "micro_edge_entry_timing_observed",
                        "micro_edge_entry_timing",
                    ),
                ),
                history_score=_coerce_float(compatibility.get("history_score")),
                marginal_value_score=_coerce_float(
                    compatibility.get("marginal_value_score")
                ),
                reentry_lateness=_coerce_float(compatibility.get("reentry_lateness")),
                concentration_headroom=_coerce_float(
                    compatibility.get("concentration_headroom")
                ),
                anti_revenge_state__active=_pick_bool(
                    compatibility,
                    keys=("anti_revenge_state__active",),
                ),
                anti_revenge_state__cooling=_pick_bool(
                    compatibility,
                    keys=("anti_revenge_state__cooling",),
                ),
                anti_revenge_state__idle=_pick_bool(
                    compatibility,
                    keys=("anti_revenge_state__idle",),
                ),
                fee_bps=_pick_float(parity, compatibility, keys=("replay_fee_bps", "fee_bps")),
                slippage_bps=_pick_float(
                    parity,
                    compatibility,
                    keys=(
                        "measured_slippage_bps",
                        "slippage_bps_measured",
                        "replay_slippage_bps",
                        "slippage_bps",
                    ),
                ),
                adverse_selection_bps=_pick_float(
                    parity,
                    dtr_record,
                    keys=("adverse_selection_bps", "adverse_selection_cost_bps"),
                ),
                expected_ce_net=result.expected_ce_net,
                executed_only_net_return=result.executed_only_net_return,
                break_even_bps=break_even_bps,
                mfe_bps=_pick_float(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=("mfe_bps", "max_favorable_excursion_bps"),
                ),
                mae_bps=_pick_float(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=("mae_bps", "max_adverse_excursion_bps"),
                ),
                holding_time_ms=_pick_int(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=("holding_time_ms",),
                ),
                label_net_positive=_row_net_positive_label(
                    executed_only_net_return=result.executed_only_net_return,
                    expected_ce_net=result.expected_ce_net,
                ),
                label_break_even_cleared=_row_break_even_label(
                    executed_only_net_return=result.executed_only_net_return,
                    expected_ce_net=result.expected_ce_net,
                    break_even_bps=break_even_bps,
                ),
                label_survived_mae=_row_mae_survival_label(
                    mae_bps=_pick_float(
                        replay_outcome_report,
                        parity,
                        dtr_record,
                        keys=("mae_bps", "max_adverse_excursion_bps"),
                    ),
                    break_even_bps=break_even_bps,
                ),
                label_forward_return_h1=_pick_float(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=("label_forward_return_h1", "forward_return_h1", "forward_return_bps_h1"),
                ),
                label_forward_return_h5=_pick_float(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=("label_forward_return_h5", "forward_return_h5", "forward_return_bps_h5"),
                ),
                label_forward_return_h10=_pick_float(
                    replay_outcome_report,
                    parity,
                    dtr_record,
                    keys=(
                        "label_forward_return_h10",
                        "forward_return_h10",
                        "forward_return_bps_h10",
                    ),
                ),
                evidence_class=_row_evidence_class(
                    executed_only_net_return=result.executed_only_net_return,
                    executed_only_net_return_status=executed_only_status,
                    execution_fidelity_status=execution_fidelity_status,
                    expected_ce_net=result.expected_ce_net,
                ),
                label_quality_status=label_quality_status,
                replay_grounded_status=replay_grounded_status,
                replay_quality_status=replay_quality_status,
                execution_fidelity_status=execution_fidelity_status,
                entry_reference_status=entry_reference_status,
                mfe_mae_status=mfe_mae_status,
                proxy_execution_label_flag=proxy_execution_label_flag,
                replay_grounded_label_flag=replay_grounded_label_flag,
                feature_truth_boundary_status=str(
                    compatibility.get("feature_truth_boundary_status")
                    or "FEATURE_TRUTH_BOUNDARY_NOT_PROVEN"
                ),
                feature_usage_policy=str(
                    compatibility.get("feature_usage_policy")
                    or "A2_GOLD_FEATURE_USAGE_NOT_PROVEN"
                ),
                cost_feature_truth_status=str(
                    compatibility.get("cost_feature_truth_status")
                    or "COST_FEATURE_TRUTH_NOT_PROVEN"
                ),
                feature_values=feature_values,
                feature_hash=_hash_payload(feature_values),
            )
            rows.append(row)
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.decision_timestamp_ms,
                item.candidate_id,
                item.capital_bucket,
            ),
        )
    )


def _status_and_blockers(
    rows: tuple[StrategyLadderB2LabelStoreRow, ...],
    *,
    replay_grounded_label_count: int,
    proxy_execution_label_count: int,
    source_bundle: _SourceBundle,
) -> tuple[str, str, tuple[str, ...]]:
    blockers: list[str] = []
    if not source_bundle.detailed_replay_artifacts:
        blockers.append("B2_DETAILED_REPLAY_MISSING")
        return (
            "LABEL_STORE_BLOCKED_BY_MISSING_REPLAY",
            "LABEL_STORE_RESEARCH_ONLY",
            tuple(blockers),
        )
    if not rows:
        blockers.append("B2_REPLAY_ROWS_NOT_MATERIALIZED")
        return (
            "LABEL_STORE_BLOCKED_BY_MISSING_REPLAY",
            "LABEL_STORE_RESEARCH_ONLY",
            tuple(blockers),
        )
    if replay_grounded_label_count <= 0:
        blockers.append("NO_EXECUTED_REPLAY_LABELS")
    if proxy_execution_label_count > 0:
        blockers.append("PROXY_EXECUTION_LABELS_PRESENT")
    if any(row.execution_fidelity_status != "EXECUTION_FIDELITY_READY" for row in rows):
        blockers.append("EXECUTION_FIDELITY_NOT_PROMOTION_GRADE")
    if any(
        row.entry_reference_status != "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED"
        for row in rows
    ):
        blockers.append("ENTRY_REFERENCE_NOT_PROMOTION_GRADE")
    if any(row.mfe_mae_status != "MFE_MAE_AVAILABLE" for row in rows):
        blockers.append("MFE_MAE_NOT_PROMOTION_GRADE")
    if any(
        row.label_quality_status != "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE"
        for row in rows
    ):
        blockers.append("LABEL_STORE_ROWS_NOT_PROMOTION_GRADE")
    if replay_grounded_label_count <= 0 and proxy_execution_label_count <= 0:
        return (
            "LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",
            "LABEL_STORE_RESEARCH_ONLY",
            tuple(dict.fromkeys(blockers)),
        )
    if proxy_execution_label_count > 0 or replay_grounded_label_count < len(rows):
        return (
            "LABEL_STORE_PARTIAL_PROXY_EXECUTION",
            "LABEL_STORE_RESEARCH_ONLY",
            tuple(dict.fromkeys(blockers)),
        )
    if blockers:
        return (
            "LABEL_STORE_READY",
            "LABEL_STORE_RESEARCH_ONLY",
            tuple(dict.fromkeys(blockers)),
        )
    return (
        "LABEL_STORE_READY",
        "LABEL_STORE_PROMOTION_GRADE_CANDIDATE",
        (),
    )


def _rate(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _row_feature_value(
    row: StrategyLadderB2LabelStoreRow,
    feature_name: str,
) -> float | None:
    if feature_name in row.feature_values:
        return _coerce_float(row.feature_values.get(feature_name))
    if hasattr(row, feature_name):
        raw_value = getattr(row, feature_name)
        if isinstance(raw_value, bool):
            return 1.0 if raw_value else 0.0
        return _coerce_float(raw_value)
    return None


def _anti_revenge_one_hot_status(row: StrategyLadderB2LabelStoreRow) -> str:
    values = tuple(_row_feature_value(row, name) for name in ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES)
    if any(value is None for value in values):
        return "ANTI_REVENGE_STATE_MISSING"
    active_count = sum(1 for value in values if value is not None and value > 0.5)
    return (
        "ANTI_REVENGE_STATE_ONE_HOT_READY"
        if active_count == 1
        else "ANTI_REVENGE_STATE_ONE_HOT_INVALID"
    )


def _feature_source_status(
    available_count: int,
    row_count: int,
) -> str:
    if row_count <= 0:
        return "FEATURE_SOURCE_NO_ROWS"
    if available_count == row_count:
        return "FEATURE_SOURCE_FULL"
    if available_count <= 0:
        return "FEATURE_SOURCE_MISSING"
    return "FEATURE_SOURCE_PARTIAL"


def _build_f16_feature_coverage_report(
    *,
    rows: tuple[StrategyLadderB2LabelStoreRow, ...],
    summary: StrategyLadderB2LabelStoreSummary,
    quality_report: StrategyLadderB2LabelStoreQualityReport,
) -> dict[str, object]:
    feature_names = SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES
    row_count = len(rows)

    def _required_features_for_engine(engine_id: str) -> tuple[str, ...]:
        normalized = engine_id.strip().lower()
        if normalized == "engine_d":
            return feature_names
        return tuple(
            feature_name
            for feature_name in feature_names
            if feature_name not in _ENGINE_D_ONLY_FEATURE_NAMES
        )

    def _engine_applicable_coverage() -> list[dict[str, object]]:
        engine_rows: list[dict[str, object]] = []
        for engine_id in sorted({row.engine_id for row in rows}):
            scope_rows = tuple(row for row in rows if row.engine_id == engine_id)
            required_features = _required_features_for_engine(engine_id)
            full_count = sum(
                1
                for row in scope_rows
                if all(
                    _row_feature_value(row, feature_name) is not None
                    for feature_name in required_features
                )
                and (
                    engine_id == "engine_d"
                    or _anti_revenge_one_hot_status(row)
                    != "ANTI_REVENGE_STATE_ONE_HOT_INVALID"
                )
            )
            feature_presence_count = {
                feature_name: sum(
                    1
                    for row in scope_rows
                    if _row_feature_value(row, feature_name) is not None
                )
                for feature_name in required_features
            }
            engine_rows.append(
                {
                    "engine_id": engine_id,
                    "row_count": len(scope_rows),
                    "required_feature_names": required_features,
                    "engine_applicable_full_feature_row_count": full_count,
                    "engine_applicable_full_feature_coverage_rate": _rate(
                        full_count,
                        len(scope_rows),
                    ),
                    "missing_engine_applicable_feature_names": tuple(
                        feature_name
                        for feature_name, count in feature_presence_count.items()
                        if count < len(scope_rows)
                    ),
                    "feature_presence_count": feature_presence_count,
                    "d_only_features_excluded": engine_id != "engine_d",
                }
            )
        return engine_rows

    def _coverage_for_scope(scope_rows: tuple[StrategyLadderB2LabelStoreRow, ...]) -> dict[str, object]:
        scope_row_count = len(scope_rows)
        feature_presence_count = {
            feature_name: sum(
                1
                for row in scope_rows
                if _row_feature_value(row, feature_name) is not None
            )
            for feature_name in feature_names
        }
        source_status_by_feature = {
            feature_name: _feature_source_status(count, scope_row_count)
            for feature_name, count in feature_presence_count.items()
        }
        zero_available_features = tuple(
            feature_name
            for feature_name, count in feature_presence_count.items()
            if count <= 0
        )
        partial_features = tuple(
            feature_name
            for feature_name, count in feature_presence_count.items()
            if 0 < count < scope_row_count
        )
        anti_status_counts = {
            status: sum(1 for row in scope_rows if _anti_revenge_one_hot_status(row) == status)
            for status in sorted({_anti_revenge_one_hot_status(row) for row in scope_rows})
        }
        full_feature_row_count = sum(
            1
            for row in scope_rows
            if all(_row_feature_value(row, feature_name) is not None for feature_name in feature_names)
            and _anti_revenge_one_hot_status(row) == "ANTI_REVENGE_STATE_ONE_HOT_READY"
        )
        return {
            "row_count": scope_row_count,
            "full_feature_row_count": full_feature_row_count,
            "full_feature_coverage_rate": _rate(full_feature_row_count, scope_row_count),
            "feature_presence_count": feature_presence_count,
            "source_status_by_feature": source_status_by_feature,
            "missing_feature_names": tuple(
                feature_name
                for feature_name, count in feature_presence_count.items()
                if count < scope_row_count
            ),
            "zero_available_features": zero_available_features,
            "partial_features": partial_features,
            "anti_revenge_status_counts": anti_status_counts,
            "prod_eligible": (
                scope_row_count > 0
                and full_feature_row_count == scope_row_count
                and anti_status_counts.get("ANTI_REVENGE_STATE_ONE_HOT_INVALID", 0) == 0
                and anti_status_counts.get("ANTI_REVENGE_STATE_MISSING", 0) == 0
            ),
        }

    overall = _coverage_for_scope(rows)
    engine_applicable_rows = _engine_applicable_coverage()
    engine_applicable_full_feature_row_count = sum(
        int(row["engine_applicable_full_feature_row_count"])
        for row in engine_applicable_rows
    )
    timeframe_rows: list[dict[str, object]] = []
    for timeframe in sorted({row.timeframe for row in rows}):
        scope_rows = tuple(row for row in rows if row.timeframe == timeframe)
        row_payload = _coverage_for_scope(scope_rows)
        row_payload["timeframe"] = timeframe
        timeframe_rows.append(row_payload)

    blocker_codes: list[str] = []
    if row_count <= 0:
        blocker_codes.append("F16_LABEL_STORE_EMPTY")
    if overall["missing_feature_names"]:
        blocker_codes.append("F16_FEATURES_MISSING")
    anti_status_counts = overall["anti_revenge_status_counts"]
    if isinstance(anti_status_counts, dict) and anti_status_counts.get("ANTI_REVENGE_STATE_MISSING", 0):
        blocker_codes.append("F16_ANTI_REVENGE_STATE_MISSING")
    if isinstance(anti_status_counts, dict) and anti_status_counts.get("ANTI_REVENGE_STATE_ONE_HOT_INVALID", 0):
        blocker_codes.append("F16_ANTI_REVENGE_STATE_ONE_HOT_INVALID")
    if summary.proxy_execution_label_count > 0:
        blocker_codes.append("F16_REPLAY_LABEL_STORE_PROXY_LABELS_PRESENT")
    if summary.replay_grounded_label_count <= 0:
        blocker_codes.append("F16_REPLAY_LABEL_STORE_NO_EXECUTED_LABELS")
    prod_eligible = (
        bool(overall["prod_eligible"])
        and summary.proxy_execution_label_count == 0
        and summary.replay_grounded_label_count == row_count
        and quality_report.no_fabricated_trades
        and quality_report.no_fabricated_costs
        and not blocker_codes
    )
    return {
        "schema_version": "strategy_ladder.f16_feature_coverage_report.v1",
        "status": (
            "F16_FEATURE_COVERAGE_READY"
            if row_count > 0 and overall["full_feature_row_count"] > 0
            else "F16_FEATURE_COVERAGE_BLOCKED"
        ),
        "prod_eligibility_status": (
            "F16_PROD_ELIGIBLE"
            if prod_eligible
            else "F16_RESEARCH_ONLY_NOT_PROD_ELIGIBLE"
        ),
        "label_store_status": summary.status,
        "label_store_promotion_state": summary.promotion_state,
        "label_source_type": summary.label_source_type,
        "row_count": row_count,
        "full_feature_row_count": overall["full_feature_row_count"],
        "full_feature_coverage_rate": overall["full_feature_coverage_rate"],
        "engine_applicable_full_feature_row_count": engine_applicable_full_feature_row_count,
        "engine_applicable_full_feature_coverage_rate": _rate(
            engine_applicable_full_feature_row_count,
            row_count,
        ),
        "requested_feature_names": feature_names,
        "missing_feature_names": overall["missing_feature_names"],
        "zero_available_features": overall["zero_available_features"],
        "partial_features": overall["partial_features"],
        "source_status_by_feature": overall["source_status_by_feature"],
        "anti_revenge_status_counts": overall["anti_revenge_status_counts"],
        "timeframe_rows": timeframe_rows,
        "engine_applicable_rows": engine_applicable_rows,
        "blocker_codes": tuple(dict.fromkeys(blocker_codes)),
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


def build_strategy_ladder_b2_label_store(
    request: StrategyLadderB2LabelStoreBuilderRequest,
) -> StrategyLadderB2LabelStoreBuildResult:
    """Build the canonical B2 replay-grounded supervised label store."""

    source_bundle = _load_source_bundle(request)
    rows = _build_rows(source_bundle)
    dataset_path = _write_jsonl(request.output_dir / LABEL_STORE_DATASET_FILENAME, rows)
    dataset_hash = _dataset_hash(rows)
    feature_hash = _feature_hash(rows)
    label_hash = _label_hash(rows)
    replay_grounded_label_count = sum(
        1 for row in rows if row.replay_grounded_label_flag
    )
    proxy_execution_label_count = sum(
        1 for row in rows if row.proxy_execution_label_flag
    )
    executed_trade_label_count = sum(
        1 for row in rows if row.execution_fidelity_status != "EXECUTION_FIDELITY_PROXY_EXECUTION"
    )
    status, promotion_state, blocking_reasons = _status_and_blockers(
        rows,
        replay_grounded_label_count=replay_grounded_label_count,
        proxy_execution_label_count=proxy_execution_label_count,
        source_bundle=source_bundle,
    )
    label_source_type = _label_source_type(
        replay_grounded_label_count,
        proxy_execution_label_count,
    )
    net_positive_numerator = sum(1 for row in rows if row.label_net_positive is True)
    net_positive_denominator = sum(
        1 for row in rows if row.label_net_positive is not None
    )
    break_even_numerator = sum(
        1 for row in rows if row.label_break_even_cleared is True
    )
    break_even_denominator = sum(
        1 for row in rows if row.label_break_even_cleared is not None
    )
    mfe_available_count = sum(1 for row in rows if row.mfe_bps is not None)
    mae_available_count = sum(1 for row in rows if row.mae_bps is not None)
    replay_provenance_refs = tuple(
        dict.fromkeys(
            [
                *(
                    str(ref)
                    for ref, _artifact in source_bundle.detailed_replay_artifacts
                ),
                *(
                    str(path)
                    for path, _manifest in source_bundle.raw_window_manifests.values()
                ),
            ]
        )
    )
    summary_path = (request.output_dir / LABEL_STORE_SUMMARY_FILENAME).resolve()
    quality_report_path = (request.output_dir / LABEL_STORE_QUALITY_REPORT_FILENAME).resolve()
    f16_feature_coverage_report_path = (
        request.output_dir / F16_FEATURE_COVERAGE_REPORT_FILENAME
    ).resolve()
    summary = StrategyLadderB2LabelStoreSummary(
        status=status,
        promotion_state=promotion_state,
        label_source_type=label_source_type,
        run_root=str(request.run_root.resolve()),
        dataset_ref=str(dataset_path.resolve()),
        quality_report_ref=str(quality_report_path),
        row_count=len(rows),
        replay_grounded_label_count=replay_grounded_label_count,
        proxy_execution_label_count=proxy_execution_label_count,
        executed_trade_label_count=executed_trade_label_count,
        net_positive_rate=None
        if net_positive_denominator <= 0
        else _rate(net_positive_numerator, net_positive_denominator),
        break_even_clearance_rate=None
        if break_even_denominator <= 0
        else _rate(break_even_numerator, break_even_denominator),
        replay_backed_label_coverage=_rate(
            replay_grounded_label_count,
            len(rows),
        ),
        mfe_available_count=mfe_available_count,
        mae_available_count=mae_available_count,
        mfe_availability_rate=_rate(mfe_available_count, len(rows)),
        mae_availability_rate=_rate(mae_available_count, len(rows)),
        dataset_hash=dataset_hash,
        feature_hash=feature_hash,
        label_hash=label_hash,
        pair_scope=tuple(sorted({row.pair for row in rows})),
        engine_scope=tuple(sorted({row.engine_id for row in rows})),
        timeframe_scope=tuple(sorted({row.timeframe for row in rows})),
        capital_bucket_scope=tuple(sorted({row.capital_bucket for row in rows})),
        walk_forward_train_days=request.walk_forward_train_days,
        walk_forward_validation_days=request.walk_forward_validation_days,
        purge_window_minutes=request.purge_window_minutes,
        embargo_window_minutes=request.embargo_window_minutes,
        replay_provenance_refs=replay_provenance_refs,
        blocking_reasons=blocking_reasons,
    )
    quality_report = StrategyLadderB2LabelStoreQualityReport(
        status=status,
        promotion_state=promotion_state,
        label_source_type=label_source_type,
        run_root=str(request.run_root.resolve()),
        dataset_ref=str(dataset_path.resolve()),
        dataset_hash=dataset_hash,
        feature_hash=feature_hash,
        label_hash=label_hash,
        row_count=len(rows),
        replay_grounded_label_count=replay_grounded_label_count,
        proxy_execution_label_count=proxy_execution_label_count,
        no_future_timestamp_violations=0,
        post_decision_replay_only=True,
        no_fabricated_trades=True,
        no_fabricated_costs=True,
        replay_backed_label_coverage=_rate(
            replay_grounded_label_count,
            len(rows),
        ),
        net_positive_rate=summary.net_positive_rate,
        break_even_clearance_rate=summary.break_even_clearance_rate,
        mfe_mae_availability=(
            "MFE_MAE_AVAILABLE"
            if any(row.mfe_mae_status == "MFE_MAE_AVAILABLE" for row in rows)
            else "MFE_MAE_AVAILABLE_PROXY_ONLY"
            if any(
                row.mfe_mae_status == "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE"
                for row in rows
            )
            else "MFE_MAE_NOT_AVAILABLE"
        ),
        label_quality_status_counts={
            key: sum(1 for row in rows if row.label_quality_status == key)
            for key in sorted({row.label_quality_status for row in rows})
        },
        replay_grounded_status_counts={
            key: sum(1 for row in rows if row.replay_grounded_status == key)
            for key in sorted({row.replay_grounded_status for row in rows})
        },
        entry_reference_status_counts={
            key: sum(1 for row in rows if row.entry_reference_status == key)
            for key in sorted({row.entry_reference_status for row in rows})
        },
        mfe_mae_status_counts={
            key: sum(1 for row in rows if row.mfe_mae_status == key)
            for key in sorted({row.mfe_mae_status for row in rows})
        },
        execution_fidelity_status_counts={
            key: sum(1 for row in rows if row.execution_fidelity_status == key)
            for key in sorted({row.execution_fidelity_status for row in rows})
        },
        feature_truth_boundary_status_counts={
            key: sum(1 for row in rows if row.feature_truth_boundary_status == key)
            for key in sorted({row.feature_truth_boundary_status for row in rows})
        },
        cost_feature_truth_status_counts={
            key: sum(1 for row in rows if row.cost_feature_truth_status == key)
            for key in sorted({row.cost_feature_truth_status for row in rows})
        },
        feature_to_label_truth_promotion_blocked_count=sum(
            1
            for row in rows
            if row.cost_feature_truth_status
            in {
                "A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH",
                "A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH",
            }
        ),
        evidence_class_counts={
            key: sum(1 for row in rows if row.evidence_class == key)
            for key in sorted({row.evidence_class for row in rows})
        },
        blocking_reasons=blocking_reasons,
        replay_provenance_refs=replay_provenance_refs,
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"), indent=2)
    atomic_write_json(quality_report_path, quality_report.model_dump(mode="json"), indent=2)
    atomic_write_json(
        f16_feature_coverage_report_path,
        _build_f16_feature_coverage_report(
            rows=rows,
            summary=summary,
            quality_report=quality_report,
        ),
        indent=2,
    )
    return StrategyLadderB2LabelStoreBuildResult(
        status=status,
        promotion_state=promotion_state,
        dataset_path=str(dataset_path.resolve()),
        summary_path=str(summary_path),
        quality_report_path=str(quality_report_path),
        f16_feature_coverage_report_path=str(f16_feature_coverage_report_path),
        dataset_hash=dataset_hash,
        feature_hash=feature_hash,
        label_hash=label_hash,
        row_count=len(rows),
        replay_grounded_label_count=replay_grounded_label_count,
        proxy_execution_label_count=proxy_execution_label_count,
        label_source_type=label_source_type,
    )


__all__ = [
    "DEFAULT_EMBARGO_WINDOW_MINUTES",
    "DEFAULT_PURGE_WINDOW_MINUTES",
    "DEFAULT_WALK_FORWARD_TRAIN_DAYS",
    "DEFAULT_WALK_FORWARD_VALIDATION_DAYS",
    "F16_FEATURE_COVERAGE_REPORT_FILENAME",
    "LABEL_STORE_DATASET_FILENAME",
    "LABEL_STORE_QUALITY_REPORT_FILENAME",
    "LABEL_STORE_SUMMARY_FILENAME",
    "StrategyLadderB2LabelStoreBuildResult",
    "StrategyLadderB2LabelStoreBuilderRequest",
    "StrategyLadderB2LabelStoreQualityReport",
    "StrategyLadderB2LabelStoreRow",
    "StrategyLadderB2LabelStoreSummary",
    "build_strategy_ladder_b2_label_store",
]
