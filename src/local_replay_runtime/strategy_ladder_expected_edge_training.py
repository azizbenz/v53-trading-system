"""Governed Strategy Ladder expected-edge training from legacy klines or B2 replay labels."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from calibration_methods import (
    MlTrainerDataError,
    MlTrainerDependencyError,
    MlTrainerRequest,
    MlTrainerResult,
    MlTrainingRow,
    train_lightgbm_ml_artifact,
)
from interface_contracts import MlModelArtifact, MlModelWindow
from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    LABEL_STORE_DATASET_FILENAME,
    LEGACY_LABEL_STORE_DATASET_FILENAMES,
    LABEL_STORE_QUALITY_REPORT_FILENAME,
    LABEL_STORE_SUMMARY_FILENAME,
    StrategyLadderB2LabelStoreBuilderRequest,
    StrategyLadderB2LabelStoreQualityReport,
    StrategyLadderB2LabelStoreRow,
    StrategyLadderB2LabelStoreSummary,
    build_strategy_ladder_b2_label_store,
)


STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY = "B2_REPLAY_EXECUTION_AWARE_NET_EDGE.v1"
LEGACY_STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY = "ABS_FORWARD_CLOSE_RETURN"
DEFAULT_EXPECTED_EDGE_FEATURE_NAMES = ("close_return", "high_low_range", "volume")
# Patch F16-B (2026-05-21) — ajout de 3 microstructure canoniques V5.3
# (vpin, cumulative_ofi, queue_pressure) capturées depuis bridge engine_native_adapter
# et persistées dans StrategyLadderB2LabelStoreRow v2.
REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "spread_bps",
    "slippage_bps",
    "book_depth_levels",
    "break_even_bps",
    "fragility_score",
    "false_breakout_context",
    "vpin",
    "cumulative_ofi",
    "queue_pressure",
)
EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
    "latency_penalty_bps",
)
BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES = (
    "micro_edge_exit_governor_observed",
    "micro_edge_entry_timing_observed",
)
ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES = (
    "history_score",
    "marginal_value_score",
    "reentry_lateness",
    "concentration_headroom",
)
ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES = (
    "anti_revenge_state__active",
    "anti_revenge_state__cooling",
    "anti_revenge_state__idle",
)
SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES = (
    *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES,
    *ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
    *ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
)
_SUPPORTED_FEATURE_NAME_SET = frozenset(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES)
_LEGACY_FEATURE_NAME_SET = frozenset(DEFAULT_EXPECTED_EDGE_FEATURE_NAMES)
_ANTI_REVENGE_STATE_ONE_HOT_SET = frozenset(ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES)


def normalize_supported_expected_edge_feature_names(
    raw_feature_names: tuple[str, ...] | list[str] | set[str] | frozenset[str],
) -> tuple[str, ...]:
    """Normalize and validate the governed expected-edge feature tuple."""

    normalized = tuple(dict.fromkeys(item.strip() for item in raw_feature_names if item.strip()))
    if not normalized:
        raise ValueError("feature_names must not be empty")
    unsupported = tuple(item for item in normalized if item not in _SUPPORTED_FEATURE_NAME_SET)
    if unsupported:
        raise ValueError(f"unsupported Strategy Ladder expected-edge features: {unsupported}")
    anti_revenge_subset = {
        item for item in normalized if item in _ANTI_REVENGE_STATE_ONE_HOT_SET
    }
    if anti_revenge_subset and anti_revenge_subset != _ANTI_REVENGE_STATE_ONE_HOT_SET:
        raise ValueError(
            "anti_revenge_state one-hot requires the full governed triplet: "
            f"{ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES}"
        )
    return normalized


class StrategyLadderExpectedEdgeTrainingRequest(BaseModel, frozen=True):
    """Request for a bounded Strategy Ladder expected-edge ML artifact.

    DOCTRINE V5.3 — Patch MP3 (2026-05-21) : Training is **MONO-PAIR** par doctrine.
    Le champ ``pair: str`` (singulier) reflète cette contrainte structurelle :
    chaque artifact d'entraînement est ancré sur un seul pair (typiquement
    "BTCUSDT" research-only, multi-pair étant Phase F13 future).

    **Multi-pair generalization** (F13) est explicitement HORS SCOPE de ce
    request model. Pour du data sourcing multi-pair, utiliser le data factory
    avec ``pairs: tuple[str, ...]`` — c'est une étape antérieure indépendante.

    Multi-timeframe par contre est SUPPORTÉ (1m/5m/10m/15m) : un artifact par
    timeframe, mais sur le MÊME pair. Pour Phase B P0-A, on entraîne 4 artifacts
    LightGBM (un par tf) tous ancrés sur BTCUSDT.
    """

    artifact_id: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    kline_root: Path | None = None
    b2_run_root: Path | None = None
    label_store_dataset_path: Path | None = None
    output_dir: Path
    # DOCTRINE MONO-PAIR — Patch MP3 (2026-05-21) — voir docstring classe.
    pair: str = Field(default="BTCUSDT", min_length=1)
    timeframe: str = Field(default="1m", min_length=1)
    train_start: str = Field(..., min_length=1)
    train_end: str = Field(..., min_length=1)
    sample_stride_minutes: int = Field(default=60, ge=1)
    target_horizon_minutes: int = Field(default=1, ge=1)
    training_seed: int = 5307
    max_optuna_trials: int = Field(default=0, ge=0)
    min_training_rows: int = Field(default=210, ge=10)
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    shap_summary_ref: str | None = None

    @field_validator("feature_names")
    @classmethod
    def _validate_feature_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return normalize_supported_expected_edge_feature_names(value)

    @field_validator("pair", mode="before")
    @classmethod
    def _validate_mono_pair_doctrine(cls, value: object) -> str:
        """Patch MP3 (2026-05-21) — doctrine mono-pair training strict.

        Reject explicitly any non-str input (list, tuple, iterable) with a
        clear V5.3 doctrinal message. Pydantic's default str coercion would
        accept `tuple` and silently use repr(). This validator catches the
        common multi-pair anti-pattern (`pair=("BTCUSDT", "ETHUSDT")`) with
        actionable guidance.
        """
        if isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError(
                f"DOCTRINE_MONO_PAIR_TRAINING — pair must be a single str (got {type(value).__name__} "
                f"with {len(value) if hasattr(value, '__len__') else '?'} entries). "
                "V5.3 expected-edge training is MONO-PAIR by doctrine. For multi-pair sourcing "
                "use data_factory.pairs (multi-pair container). For multi-pair training, "
                "instantiate ONE StrategyLadderExpectedEdgeTrainingRequest PER pair (F13 future scope)."
            )
        if not isinstance(value, str):
            raise ValueError(
                f"DOCTRINE_MONO_PAIR_TRAINING — pair must be str (got {type(value).__name__})"
            )
        return value

    @model_validator(mode="after")
    def _validate_sources(self) -> "StrategyLadderExpectedEdgeTrainingRequest":
        if (
            self.kline_root is None
            and self.b2_run_root is None
            and self.label_store_dataset_path is None
        ):
            raise ValueError(
                "StrategyLadderExpectedEdgeTrainingRequest requires kline_root or "
                "a replay-grounded label-store source"
            )
        requested_microstructure_features = tuple(
            name for name in self.feature_names if name not in _LEGACY_FEATURE_NAME_SET
        )
        if (
            requested_microstructure_features
            and self.b2_run_root is None
            and self.label_store_dataset_path is None
        ):
            raise ValueError(
                "Strategy Ladder microstructure expected-edge features require "
                "b2_run_root or label_store_dataset_path"
            )
        return self


class StrategyLadderExpectedEdgeTrainingReport(BaseModel, frozen=True):
    """Audit-ready report for the governed expected-edge training rail."""

    artifact_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    ready: bool = False
    target_policy: str = STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    kline_root: str = Field(..., min_length=1)
    label_store_dataset_path: str | None = None
    label_store_summary_path: str | None = None
    label_store_quality_report_path: str | None = None
    output_dir: str = Field(..., min_length=1)
    artifact_path: str | None = None
    training_report_path: str | None = None
    artifact_hash: str | None = None
    feature_hash: str | None = None
    dataset_hash: str | None = None
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
    train_start: str = Field(..., min_length=1)
    train_end: str = Field(..., min_length=1)
    target_horizon_minutes: int = Field(..., ge=1)
    sample_stride_minutes: int = Field(..., ge=1)
    kline_file_count: int = Field(default=0, ge=0)
    training_row_count: int = Field(default=0, ge=0)
    trainer_train_row_count: int = Field(default=0, ge=0)
    trainer_validation_row_count: int = Field(default=0, ge=0)
    optuna_trials_used: int = Field(default=0, ge=0)
    bagging_folds_used: int = Field(default=0, ge=0)
    first_training_timestamp: datetime | None = None
    last_training_timestamp: datetime | None = None
    artifact_stale_after: datetime | None = None
    calibration_version: str = Field(..., min_length=1)
    training_seed: int
    label_source_type: str = ""
    label_fidelity: str = ""
    feature_source: str = ""
    replay_grounded_label_count: int = Field(default=0, ge=0)
    proxy_execution_label_count: int = Field(default=0, ge=0)
    replay_backed_label_coverage: float | None = None
    net_positive_rate: float | None = None
    break_even_clearance_rate: float | None = None
    mfe_availability_rate: float | None = None
    mae_availability_rate: float | None = None
    best_params: dict[str, float | int | str | bool] = Field(default_factory=dict)
    blocking_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _KlineBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class _KlineLoadResult:
    bars: tuple[_KlineBar, ...]
    file_count: int


@dataclass(frozen=True)
class _TrainingBuildResult:
    rows: tuple[MlTrainingRow, ...]
    target_policy: str
    label_source: str
    label_fidelity: str
    feature_source: str
    kline_file_count: int = 0
    label_store_dataset_path: Path | None = None
    label_store_summary_path: Path | None = None
    label_store_quality_report_path: Path | None = None
    replay_grounded_label_count: int = 0
    proxy_execution_label_count: int = 0
    replay_backed_label_coverage: float | None = None
    net_positive_rate: float | None = None
    break_even_clearance_rate: float | None = None
    mfe_availability_rate: float | None = None
    mae_availability_rate: float | None = None


def _parse_date(raw_value: str) -> date:
    value = raw_value.strip().replace("Z", "+00:00")
    if "T" not in value and " " not in value:
        return date.fromisoformat(value)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def _timeframe_minutes(raw_value: str) -> int:
    value = raw_value.strip().lower()
    if value.endswith("m"):
        value = value[:-1]
    minutes = int(value)
    if minutes <= 0:
        raise ValueError("timeframe minutes must be positive")
    return minutes


def _timeframe_code(raw_value: str) -> str:
    return str(_timeframe_minutes(raw_value))


def _iter_days(start: date, end: date) -> tuple[date, ...]:
    if end < start:
        raise ValueError("train_end must be >= train_start")
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _resolve_kline_paths(root: Path, *, pair: str, timeframe_code: str, day: date) -> tuple[Path, ...]:
    pair_root = root if root.name.upper() == pair.upper() else root / pair
    filename = f"{pair}_{timeframe_code}_{day.isoformat()}.csv"
    return (
        pair_root / timeframe_code / f"{day.year:04d}" / filename,
        pair_root / timeframe_code / filename,
    )


def _coerce_float(raw_value: object) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _coerce_timestamp(raw_value: object) -> datetime | None:
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if value < 10_000_000_000:
        value *= 1000
    return datetime.fromtimestamp(value / 1000.0, tz=UTC)


def _read_kline_csv(path: Path) -> tuple[_KlineBar, ...]:
    rows: list[_KlineBar] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            timestamp = _coerce_timestamp(
                raw.get("timestamp_ms")
                or raw.get("startTime")
                or raw.get("open_time")
                or raw.get("openTime")
            )
            open_price = _coerce_float(raw.get("open"))
            high_price = _coerce_float(raw.get("high"))
            low_price = _coerce_float(raw.get("low"))
            close_price = _coerce_float(raw.get("close"))
            volume = _coerce_float(raw.get("volume"))
            if (
                timestamp is None
                or open_price is None
                or high_price is None
                or low_price is None
                or close_price is None
                or volume is None
            ):
                continue
            if min(open_price, high_price, low_price, close_price) <= 0.0:
                continue
            rows.append(
                _KlineBar(
                    timestamp=timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=max(0.0, volume),
                )
            )
    return tuple(rows)


def _sanitize_filename(raw_value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_value.strip()).strip("._") or "artifact"


def load_strategy_ladder_expected_edge_kline_bars(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> _KlineLoadResult:
    """Load only the requested pair/timeframe/date range from the kline tree."""

    if request.kline_root is None:
        raise ValueError("kline_root is required for legacy Strategy Ladder expected-edge training")
    start_day = _parse_date(request.train_start)
    end_day = _parse_date(request.train_end)
    timeframe_code = _timeframe_code(request.timeframe)
    bars: list[_KlineBar] = []
    file_count = 0
    for day in _iter_days(start_day, end_day):
        resolved_path = next(
            (
                candidate
                for candidate in _resolve_kline_paths(
                    request.kline_root,
                    pair=request.pair,
                    timeframe_code=timeframe_code,
                    day=day,
                )
                if candidate.is_file()
            ),
            None,
        )
        if resolved_path is None:
            continue
        file_count += 1
        bars.extend(_read_kline_csv(resolved_path))
    return _KlineLoadResult(
        bars=tuple(sorted(bars, key=lambda item: item.timestamp)),
        file_count=file_count,
    )


def _feature_payload(
    *,
    bar: _KlineBar,
    feature_names: tuple[str, ...],
) -> dict[str, float]:
    values = {
        "close_return": ((bar.close - bar.open) / bar.open) if bar.open > 0.0 else 0.0,
        "high_low_range": ((bar.high - bar.low) / bar.open) if bar.open > 0.0 else 0.0,
        "volume": bar.volume,
    }
    return {name: float(values[name]) for name in feature_names}


def _uses_replay_label_store(request: StrategyLadderExpectedEdgeTrainingRequest) -> bool:
    return request.b2_run_root is not None or request.label_store_dataset_path is not None


def _require_supported_legacy_features(feature_names: tuple[str, ...]) -> None:
    unsupported = tuple(name for name in feature_names if name not in _LEGACY_FEATURE_NAME_SET)
    if unsupported:
        raise ValueError(
            "Strategy Ladder legacy kline training only supports gold-store kline features: "
            f"{unsupported}"
        )


def _label_store_paths_from_dataset(dataset_path: Path) -> tuple[Path, Path]:
    parent = dataset_path.parent
    return (
        (parent / LABEL_STORE_SUMMARY_FILENAME).resolve(),
        (parent / LABEL_STORE_QUALITY_REPORT_FILENAME).resolve(),
    )


def _load_label_store_rows(path: Path) -> tuple[StrategyLadderB2LabelStoreRow, ...]:
    if not path.is_file():
        raise ValueError("LABEL_STORE_DATASET_NOT_FOUND")
    rows: list[StrategyLadderB2LabelStoreRow] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        rows.append(StrategyLadderB2LabelStoreRow.model_validate_json(line))
    return tuple(rows)


def _load_label_store_summary(path: Path) -> StrategyLadderB2LabelStoreSummary:
    if not path.is_file():
        raise ValueError("LABEL_STORE_SUMMARY_NOT_FOUND")
    return StrategyLadderB2LabelStoreSummary.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )


def _load_label_store_quality_report(path: Path) -> StrategyLadderB2LabelStoreQualityReport:
    if not path.is_file():
        raise ValueError("LABEL_STORE_QUALITY_REPORT_NOT_FOUND")
    return StrategyLadderB2LabelStoreQualityReport.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )


def _dataset_hash(rows: tuple[MlTrainingRow, ...]) -> str:
    payload = [
        {
            "timestamp": row.timestamp.isoformat(),
            "pair": row.pair,
            "features": row.features,
            "target": row.target,
        }
        for row in sorted(rows, key=lambda item: (item.timestamp, item.pair))
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _label_hash(rows: tuple[MlTrainingRow, ...]) -> str:
    payload = [
        {
            "timestamp": row.timestamp.isoformat(),
            "pair": row.pair,
            "target": row.target,
        }
        for row in sorted(rows, key=lambda item: (item.timestamp, item.pair))
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _build_legacy_kline_training_rows(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> _TrainingBuildResult:
    _require_supported_legacy_features(request.feature_names)
    load_result = load_strategy_ladder_expected_edge_kline_bars(request)
    bars = load_result.bars
    timeframe_minutes = _timeframe_minutes(request.timeframe)
    horizon_rows = max(1, request.target_horizon_minutes // timeframe_minutes)
    stride_rows = max(1, request.sample_stride_minutes // timeframe_minutes)
    rows: list[MlTrainingRow] = []
    eligible_index = 0
    for index in range(0, max(0, len(bars) - horizon_rows)):
        bar = bars[index]
        future = bars[index + horizon_rows]
        if eligible_index % stride_rows != 0:
            eligible_index += 1
            continue
        eligible_index += 1
        if bar.close <= 0.0:
            continue
        target = abs((future.close - bar.close) / bar.close)
        if not math.isfinite(target):
            continue
        rows.append(
            MlTrainingRow(
                timestamp=bar.timestamp,
                pair=request.pair,
                features=_feature_payload(bar=bar, feature_names=request.feature_names),
                target=target,
            )
        )
    return _TrainingBuildResult(
        rows=tuple(rows),
        target_policy=LEGACY_STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
        label_source=LEGACY_STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
        label_fidelity="EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
        feature_source="gold_store_kline_features",
        kline_file_count=load_result.file_count,
    )


def _build_replay_grounded_training_rows(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> _TrainingBuildResult:
    artifact_name = _sanitize_filename(request.artifact_id)
    if request.b2_run_root is not None:
        label_store_output_dir = request.output_dir / f"{artifact_name}.label_store"
        build_strategy_ladder_b2_label_store(
            StrategyLadderB2LabelStoreBuilderRequest(
                run_root=request.b2_run_root,
                output_dir=label_store_output_dir,
                walk_forward_train_days=180,
                walk_forward_validation_days=30,
                purge_window_minutes=request.target_horizon_minutes,
                embargo_window_minutes=request.target_horizon_minutes,
            )
        )
        dataset_candidates = (
            (label_store_output_dir / LABEL_STORE_DATASET_FILENAME).resolve(),
            *(
                (label_store_output_dir / legacy_name).resolve()
                for legacy_name in LEGACY_LABEL_STORE_DATASET_FILENAMES
            ),
        )
        dataset_path = next((path for path in dataset_candidates if path.is_file()), dataset_candidates[0])
        summary_path, quality_report_path = _label_store_paths_from_dataset(dataset_path)
    else:
        if request.label_store_dataset_path is None:
            raise ValueError("LABEL_STORE_DATASET_PATH_MISSING")
        dataset_path = request.label_store_dataset_path.resolve()
        summary_path, quality_report_path = _label_store_paths_from_dataset(dataset_path)
    rows = _load_label_store_rows(dataset_path)
    summary = _load_label_store_summary(summary_path)
    _load_label_store_quality_report(quality_report_path)
    if summary.status in {
        "LABEL_STORE_BLOCKED_BY_MISSING_REPLAY",
        "LABEL_STORE_BLOCKED_BY_NO_EXECUTED_TRADES",
    }:
        raise ValueError(summary.status)
    start_day = _parse_date(request.train_start)
    end_day = _parse_date(request.train_end)
    training_rows: list[MlTrainingRow] = []
    for row in rows:
        if row.pair != request.pair:
            continue
        if request.timeframe and row.timeframe != request.timeframe:
            continue
        decision_time = datetime.fromtimestamp(row.decision_timestamp_ms / 1000.0, tz=UTC)
        decision_day = decision_time.date()
        if decision_day < start_day or decision_day > end_day:
            continue
        target = row.executed_only_net_return
        if target is None:
            target = row.expected_ce_net
        if target is None or not math.isfinite(target):
            continue
        selected_features: dict[str, float] = {}
        missing_feature = False
        for name in request.feature_names:
            value = row.feature_values.get(name)
            if value is None or not math.isfinite(value):
                missing_feature = True
                break
            selected_features[name] = float(value)
        if missing_feature:
            continue
        training_rows.append(
            MlTrainingRow(
                timestamp=decision_time,
                pair=row.pair,
                features=selected_features,
                target=float(target),
            )
        )
    if not training_rows:
        raise ValueError("LABEL_STORE_FILTER_PRODUCED_NO_TRAINING_ROWS")
    return _TrainingBuildResult(
        rows=tuple(training_rows),
        target_policy=STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
        label_source=summary.label_source_type,
        label_fidelity=summary.promotion_state,
        feature_source="strategy_ladder_b2_replay_label_store",
        label_store_dataset_path=dataset_path,
        label_store_summary_path=summary_path,
        label_store_quality_report_path=quality_report_path,
        replay_grounded_label_count=summary.replay_grounded_label_count,
        proxy_execution_label_count=summary.proxy_execution_label_count,
        replay_backed_label_coverage=summary.replay_backed_label_coverage,
        net_positive_rate=summary.net_positive_rate,
        break_even_clearance_rate=summary.break_even_clearance_rate,
        mfe_availability_rate=summary.mfe_availability_rate,
        mae_availability_rate=summary.mae_availability_rate,
    )


def _build_training_rows(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> _TrainingBuildResult:
    if _uses_replay_label_store(request):
        return _build_replay_grounded_training_rows(request)
    return _build_legacy_kline_training_rows(request)


def _training_dataset_load_failure_reason(exc: OSError | ValueError) -> str:
    detail = str(exc).strip()
    if detail and re.fullmatch(r"[A-Z0-9_:.+-]+", detail):
        return f"TRAINING_DATASET_LOAD_FAILED:{detail}"
    return f"TRAINING_DATASET_LOAD_FAILED:{type(exc).__name__}"


def _ml_trainer_failure_reason(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail and re.fullmatch(r"[A-Z0-9_:.+-]+", detail):
        return f"ML_TRAINER_FAILED:{detail}"
    if detail:
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", detail).strip("_").upper()
        if normalized:
            return f"ML_TRAINER_FAILED:{normalized}"
    return f"ML_TRAINER_FAILED:{type(exc).__name__}"


def build_strategy_ladder_expected_edge_training_rows(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> tuple[MlTrainingRow, ...]:
    """Project governed inputs into the bounded ML trainer contract."""

    return _build_training_rows(request).rows


def _failure_report(
    request: StrategyLadderExpectedEdgeTrainingRequest,
    *,
    status: str,
    rows: tuple[MlTrainingRow, ...] = (),
    kline_file_count: int = 0,
    target_policy: str = STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
    label_store_dataset_path: Path | None = None,
    label_store_summary_path: Path | None = None,
    label_store_quality_report_path: Path | None = None,
    label_source_type: str = "",
    label_fidelity: str = "",
    feature_source: str = "",
    replay_grounded_label_count: int = 0,
    proxy_execution_label_count: int = 0,
    replay_backed_label_coverage: float | None = None,
    net_positive_rate: float | None = None,
    break_even_clearance_rate: float | None = None,
    mfe_availability_rate: float | None = None,
    mae_availability_rate: float | None = None,
    blocking_reasons: tuple[str, ...],
    training_report_path: Path | None = None,
) -> StrategyLadderExpectedEdgeTrainingReport:
    return StrategyLadderExpectedEdgeTrainingReport(
        artifact_id=request.artifact_id,
        status=status,
        ready=False,
        target_policy=target_policy,
        pair=request.pair,
        timeframe=request.timeframe,
        kline_root=(
            str(request.kline_root)
            if request.kline_root is not None
            else "NOT_USED_REPLAY_LABEL_STORE"
        ),
        label_store_dataset_path=(
            None if label_store_dataset_path is None else str(label_store_dataset_path)
        ),
        label_store_summary_path=(
            None if label_store_summary_path is None else str(label_store_summary_path)
        ),
        label_store_quality_report_path=(
            None
            if label_store_quality_report_path is None
            else str(label_store_quality_report_path)
        ),
        output_dir=str(request.output_dir),
        training_report_path=None if training_report_path is None else str(training_report_path),
        dataset_hash=_dataset_hash(rows) if rows else None,
        feature_names=request.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        target_horizon_minutes=request.target_horizon_minutes,
        sample_stride_minutes=request.sample_stride_minutes,
        kline_file_count=kline_file_count,
        training_row_count=len(rows),
        first_training_timestamp=rows[0].timestamp if rows else None,
        last_training_timestamp=rows[-1].timestamp if rows else None,
        calibration_version=request.calibration_version,
        training_seed=request.training_seed,
        label_source_type=label_source_type,
        label_fidelity=label_fidelity,
        feature_source=feature_source,
        replay_grounded_label_count=replay_grounded_label_count,
        proxy_execution_label_count=proxy_execution_label_count,
        replay_backed_label_coverage=replay_backed_label_coverage,
        net_positive_rate=net_positive_rate,
        break_even_clearance_rate=break_even_clearance_rate,
        mfe_availability_rate=mfe_availability_rate,
        mae_availability_rate=mae_availability_rate,
        blocking_reasons=blocking_reasons,
    )


def _write_training_report(
    report: StrategyLadderExpectedEdgeTrainingReport,
    path: Path,
) -> StrategyLadderExpectedEdgeTrainingReport:
    final_report = report.model_copy(update={"training_report_path": str(path)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(final_report.model_dump_json(indent=2), encoding="utf-8")
    return final_report


def train_strategy_ladder_expected_edge_artifact(
    request: StrategyLadderExpectedEdgeTrainingRequest,
) -> StrategyLadderExpectedEdgeTrainingReport:
    """Train and persist a governed expected-edge artifact for backtest replay."""

    artifact_name = _sanitize_filename(request.artifact_id)
    artifact_path = request.output_dir / f"{artifact_name}.json"
    report_path = request.output_dir / f"{artifact_name}.training_report.json"

    try:
        build_result = _build_training_rows(request)
        rows = build_result.rows
    except (OSError, ValueError) as exc:
        report = _failure_report(
            request,
            status="STRATEGY_LADDER_EXPECTED_EDGE_TRAINING_BLOCKED",
            target_policy=(
                STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY
                if _uses_replay_label_store(request)
                else LEGACY_STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY
            ),
            label_store_dataset_path=request.label_store_dataset_path,
            blocking_reasons=(_training_dataset_load_failure_reason(exc),),
            training_report_path=report_path,
        )
        return _write_training_report(report, report_path)

    if len(rows) < request.min_training_rows:
        report = _failure_report(
            request,
            status="STRATEGY_LADDER_EXPECTED_EDGE_TRAINING_BLOCKED",
            rows=rows,
            kline_file_count=build_result.kline_file_count,
            target_policy=build_result.target_policy,
            label_store_dataset_path=build_result.label_store_dataset_path,
            label_store_summary_path=build_result.label_store_summary_path,
            label_store_quality_report_path=build_result.label_store_quality_report_path,
            label_source_type=build_result.label_source,
            label_fidelity=build_result.label_fidelity,
            feature_source=build_result.feature_source,
            replay_grounded_label_count=build_result.replay_grounded_label_count,
            proxy_execution_label_count=build_result.proxy_execution_label_count,
            replay_backed_label_coverage=build_result.replay_backed_label_coverage,
            net_positive_rate=build_result.net_positive_rate,
            break_even_clearance_rate=build_result.break_even_clearance_rate,
            mfe_availability_rate=build_result.mfe_availability_rate,
            mae_availability_rate=build_result.mae_availability_rate,
            blocking_reasons=("INSUFFICIENT_EXPECTED_EDGE_TRAINING_ROWS",),
            training_report_path=report_path,
        )
        return _write_training_report(report, report_path)

    trainer_request = MlTrainerRequest(
        artifact_id=request.artifact_id,
        calibration_version=request.calibration_version,
        rows=rows,
        training_seed=request.training_seed,
        max_optuna_trials=request.max_optuna_trials,
        shap_summary_ref=request.shap_summary_ref,
    )
    try:
        trainer_result = train_lightgbm_ml_artifact(trainer_request)
    except (MlTrainerDependencyError, MlTrainerDataError, ValueError) as exc:
        report = _failure_report(
            request,
            status="STRATEGY_LADDER_EXPECTED_EDGE_TRAINING_BLOCKED",
            rows=rows,
            kline_file_count=build_result.kline_file_count,
            target_policy=build_result.target_policy,
            label_store_dataset_path=build_result.label_store_dataset_path,
            label_store_summary_path=build_result.label_store_summary_path,
            label_store_quality_report_path=build_result.label_store_quality_report_path,
            label_source_type=build_result.label_source,
            label_fidelity=build_result.label_fidelity,
            feature_source=build_result.feature_source,
            replay_grounded_label_count=build_result.replay_grounded_label_count,
            proxy_execution_label_count=build_result.proxy_execution_label_count,
            replay_backed_label_coverage=build_result.replay_backed_label_coverage,
            net_positive_rate=build_result.net_positive_rate,
            break_even_clearance_rate=build_result.break_even_clearance_rate,
            mfe_availability_rate=build_result.mfe_availability_rate,
            mae_availability_rate=build_result.mae_availability_rate,
            blocking_reasons=(_ml_trainer_failure_reason(exc),),
            training_report_path=report_path,
        )
        return _write_training_report(report, report_path)

    trainer_result = trainer_result.model_copy(
        update={
            "artifact": _attach_strategy_ladder_training_metadata(
                trainer_result.artifact,
                request=request,
                rows=rows,
                build_result=build_result,
            )
        }
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        trainer_result.artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report = _success_report(
        request=request,
        rows=rows,
        build_result=build_result,
        artifact_path=artifact_path,
        result=trainer_result,
    )
    return _write_training_report(report, report_path)


def _attach_strategy_ladder_training_metadata(
    artifact: MlModelArtifact,
    *,
    request: StrategyLadderExpectedEdgeTrainingRequest,
    rows: tuple[MlTrainingRow, ...],
    build_result: _TrainingBuildResult,
) -> MlModelArtifact:
    payload = artifact.model_dump()
    payload.pop("artifact_hash", None)
    metrics = {
        **dict(artifact.training_metrics),
        "strategy_ladder_target_policy": build_result.target_policy,
        "strategy_ladder_label_source": build_result.label_source,
        "strategy_ladder_label_hash": _label_hash(rows),
        "strategy_ladder_target_horizon_minutes": request.target_horizon_minutes,
        "strategy_ladder_sample_stride_minutes": request.sample_stride_minutes,
        "strategy_ladder_purge_window_minutes": request.target_horizon_minutes,
        "strategy_ladder_embargo_window_minutes": request.target_horizon_minutes,
        "strategy_ladder_walkforward_status": "EXPECTED_EDGE_WALKFORWARD_DECLARED",
        "strategy_ladder_split_declared": True,
        "strategy_ladder_label_fidelity": build_result.label_fidelity,
        "strategy_ladder_feature_source": build_result.feature_source,
        "strategy_ladder_replay_grounded_label_count": build_result.replay_grounded_label_count,
        "strategy_ladder_proxy_execution_label_count": build_result.proxy_execution_label_count,
    }
    if build_result.label_store_dataset_path is not None:
        metrics["strategy_ladder_label_store_dataset_ref"] = str(
            build_result.label_store_dataset_path
        )
    if build_result.label_store_summary_path is not None:
        metrics["strategy_ladder_label_store_summary_ref"] = str(
            build_result.label_store_summary_path
        )
    if build_result.label_store_quality_report_path is not None:
        metrics["strategy_ladder_label_store_quality_report_ref"] = str(
            build_result.label_store_quality_report_path
        )
    if build_result.replay_backed_label_coverage is not None:
        metrics["strategy_ladder_replay_backed_label_coverage"] = (
            build_result.replay_backed_label_coverage
        )
    if build_result.net_positive_rate is not None:
        metrics["strategy_ladder_net_positive_rate"] = build_result.net_positive_rate
    if build_result.break_even_clearance_rate is not None:
        metrics["strategy_ladder_break_even_clearance_rate"] = (
            build_result.break_even_clearance_rate
        )
    if build_result.mfe_availability_rate is not None:
        metrics["strategy_ladder_mfe_availability_rate"] = build_result.mfe_availability_rate
    if build_result.mae_availability_rate is not None:
        metrics["strategy_ladder_mae_availability_rate"] = build_result.mae_availability_rate
    payload["training_metrics"] = metrics
    return MlModelArtifact.create(**payload)


def _success_report(
    *,
    request: StrategyLadderExpectedEdgeTrainingRequest,
    rows: tuple[MlTrainingRow, ...],
    build_result: _TrainingBuildResult,
    artifact_path: Path,
    result: MlTrainerResult,
) -> StrategyLadderExpectedEdgeTrainingReport:
    return StrategyLadderExpectedEdgeTrainingReport(
        artifact_id=request.artifact_id,
        status="STRATEGY_LADDER_EXPECTED_EDGE_ARTIFACT_READY",
        ready=True,
        target_policy=build_result.target_policy,
        pair=request.pair,
        timeframe=request.timeframe,
        kline_root=(
            str(request.kline_root)
            if request.kline_root is not None
            else "NOT_USED_REPLAY_LABEL_STORE"
        ),
        label_store_dataset_path=(
            None
            if build_result.label_store_dataset_path is None
            else str(build_result.label_store_dataset_path)
        ),
        label_store_summary_path=(
            None
            if build_result.label_store_summary_path is None
            else str(build_result.label_store_summary_path)
        ),
        label_store_quality_report_path=(
            None
            if build_result.label_store_quality_report_path is None
            else str(build_result.label_store_quality_report_path)
        ),
        output_dir=str(request.output_dir),
        artifact_path=str(artifact_path),
        artifact_hash=result.artifact.artifact_hash,
        feature_hash=result.artifact.feature_hash,
        dataset_hash=result.artifact.dataset_hash,
        feature_names=result.artifact.feature_names,
        train_start=request.train_start,
        train_end=request.train_end,
        target_horizon_minutes=request.target_horizon_minutes,
        sample_stride_minutes=request.sample_stride_minutes,
        kline_file_count=build_result.kline_file_count,
        training_row_count=len(rows),
        trainer_train_row_count=result.train_row_count,
        trainer_validation_row_count=result.validation_row_count,
        optuna_trials_used=result.optuna_trials_used,
        bagging_folds_used=result.bagging_folds_used,
        first_training_timestamp=rows[0].timestamp if rows else None,
        last_training_timestamp=rows[-1].timestamp if rows else None,
        artifact_stale_after=result.artifact.stale_after,
        calibration_version=request.calibration_version,
        training_seed=request.training_seed,
        label_source_type=build_result.label_source,
        label_fidelity=build_result.label_fidelity,
        feature_source=build_result.feature_source,
        replay_grounded_label_count=build_result.replay_grounded_label_count,
        proxy_execution_label_count=build_result.proxy_execution_label_count,
        replay_backed_label_coverage=build_result.replay_backed_label_coverage,
        net_positive_rate=build_result.net_positive_rate,
        break_even_clearance_rate=build_result.break_even_clearance_rate,
        mfe_availability_rate=build_result.mfe_availability_rate,
        mae_availability_rate=build_result.mae_availability_rate,
        best_params=result.best_params,
    )


def build_fixture_expected_edge_artifact(
    *,
    feature_names: tuple[str, ...] = DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    label_source: str = STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
    label_fidelity: str = "LABEL_STORE_RESEARCH_ONLY",
    feature_source: str = "strategy_ladder_b2_replay_label_store",
) -> MlModelArtifact:
    """Build a tiny valid artifact shell for tests that monkeypatch the trainer."""

    feature_hash = hashlib.sha256(
        json.dumps(list(feature_names), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    train_window = MlModelWindow(
        start_at=datetime(2025, 1, 1, tzinfo=UTC),
        end_at=datetime(2025, 3, 31, tzinfo=UTC),
    )
    validation_window = MlModelWindow(
        start_at=datetime(2025, 4, 1, tzinfo=UTC),
        end_at=datetime(2025, 4, 30, tzinfo=UTC),
    )
    return MlModelArtifact.create(
        model_family="lightgbm",
        feature_names=feature_names,
        feature_hash=feature_hash,
        pair_universe=("BTCUSDT",),
        train_window=train_window,
        validation_window=validation_window,
        oos_sharpe=0.0,
        backtest_sharpe=0.0,
        ks_test_features_pvalue=1.0,
        shadow_diff_pct=None,
        training_seed=5307,
        created_at=validation_window.end_at,
        calibration_version="fixture",
        dataset_hash="1" * 64,
        model_bytes_b64=base64.b64encode(b"fixture").decode("ascii"),
        model_path_ref=None,
        training_metrics={
            "strategy_ladder_target_policy": STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
            "strategy_ladder_label_source": label_source,
            "strategy_ladder_label_hash": "2" * 64,
            "strategy_ladder_target_horizon_minutes": 1,
            "strategy_ladder_sample_stride_minutes": 60,
            "strategy_ladder_purge_window_minutes": 1,
            "strategy_ladder_embargo_window_minutes": 1,
            "strategy_ladder_walkforward_status": "EXPECTED_EDGE_WALKFORWARD_DECLARED",
            "strategy_ladder_split_declared": True,
            "strategy_ladder_label_fidelity": label_fidelity,
            "strategy_ladder_feature_source": feature_source,
        },
        stale_after=datetime(2025, 5, 30, tzinfo=UTC),
    )


__all__ = [
    "ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES",
    "BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES",
    "DEFAULT_EXPECTED_EDGE_FEATURE_NAMES",
    "ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES",
    "EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES",
    "REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES",
    "SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES",
    "LEGACY_STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY",
    "STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY",
    "StrategyLadderExpectedEdgeTrainingReport",
    "StrategyLadderExpectedEdgeTrainingRequest",
    "build_fixture_expected_edge_artifact",
    "build_strategy_ladder_expected_edge_training_rows",
    "load_strategy_ladder_expected_edge_kline_bars",
    "normalize_supported_expected_edge_feature_names",
    "train_strategy_ladder_expected_edge_artifact",
]
