"""Folder-first preflight preview for Patch 6 cockpit actions.

This module is intentionally read-only and cheap:
- it never opens raw payload files
- it relies on filename/path inference for pair/date coverage preview
- it computes operator-facing blockers before any heavy subprocess launch
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re

from pydantic import BaseModel, Field

from cockpit.action_support import (
    CockpitBacktestJobKind,
    OUTPUT_ROOT_DEFAULTED,
    OUTPUT_ROOT_EXISTS_NON_EMPTY,
    OUTPUT_ROOT_READY,
    StrategyLadderControlAction,
    is_valid_raw_source_manifest_path,
    resolve_output_root,
)
from cockpit.backtest_state_support import (
    BacktestPreviewManifest,
    Patch6NormalizedRequest,
    build_patch6_normalized_request,
    canonicalize_workflow_identity,
    phase_id_for_action,
    phase_label_for_action,
    request_hash_for_normalized_request,
    workflow_request_hash_for_normalized_request,
)
from cockpit.form_state_support import BacktestFormState
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A1,
    PHASE_A2,
    PHASE_B1,
    PHASE_B2,
    read_workflow_manifest,
    workflow_phase_dirname,
)
from interface_contracts.pair_catalog import V53_PAIR_CATALOG
from interface_contracts.storage_budget_support import estimate_silver_size_for_paths


_KNOWN_PAIR_SYMBOLS = {
    entry.symbol.upper() for entry in V53_PAIR_CATALOG.entries if entry.symbol
}
_GENERIC_SEGMENTS = {
    "trades",
    "trade",
    "aggtrades",
    "klines",
    "kline",
    "ohlcv",
    "candles",
    "orderbook",
    "book",
    "depth",
    "snapshot",
    "delta",
    "metadata",
    "symbolfilters",
    "symbol_filters",
    "filters",
    "raw",
    "spot",
    "bybit",
    "ordre",
    "part",
    "ob200",
}
_TIMEFRAME_SEGMENTS = {
    "1",
    "3",
    "5",
    "10",
    "15",
    "30",
    "60",
    "120",
    "240",
    "360",
    "720",
    "1m",
    "3m",
    "5m",
    "10m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "12h",
    "1d",
    "1w",
}


def _workflow_root_for_run_id(
    *,
    workflow_run_id: str,
    output_root_text: str,
    jobs_root: Path | None,
) -> Path:
    if output_root_text:
        return Path(output_root_text).expanduser() / "runs" / workflow_run_id
    if jobs_root is not None:
        return jobs_root / "workflows" / workflow_run_id
    return Path.cwd() / "workflows" / workflow_run_id


def _load_phase_a1_workflow_preview(workflow_root: Path) -> BacktestPreviewManifest | None:
    preview_path = workflow_root / workflow_phase_dirname(PHASE_A1) / "source_date_preview_manifest.json"
    if not preview_path.is_file():
        return None
    try:
        payload = json.loads(preview_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return BacktestPreviewManifest.model_validate(payload)
    except ValueError:
        return None


def _reuse_matching_workflow_parent(
    *,
    normalized_request: Patch6NormalizedRequest,
    requested_workflow_run_id: str,
    workflow_request_hash: str,
    output_root_text: str,
    jobs_root: Path | None,
) -> Patch6NormalizedRequest:
    requested_workflow_run_id = (requested_workflow_run_id or "").strip()
    if not requested_workflow_run_id:
        return normalized_request
    if requested_workflow_run_id == normalized_request.workflow_run_id:
        return normalized_request
    candidate_workflow_roots = [
        _workflow_root_for_run_id(
            workflow_run_id=requested_workflow_run_id,
            output_root_text=output_root_text,
            jobs_root=jobs_root,
        )
    ]
    if jobs_root is not None:
        jobs_root_candidate = jobs_root / "workflows" / requested_workflow_run_id
        if jobs_root_candidate not in candidate_workflow_roots:
            candidate_workflow_roots.append(jobs_root_candidate)
    phase_a1_preview = None
    for requested_workflow_root in candidate_workflow_roots:
        phase_a1_preview = _load_phase_a1_workflow_preview(requested_workflow_root)
        if phase_a1_preview is not None:
            break
    if phase_a1_preview is not None:
        existing_workflow_hash = workflow_request_hash_for_normalized_request(
            phase_a1_preview.normalized_request
        )
        if existing_workflow_hash == workflow_request_hash:
            return normalized_request.model_copy(
                update={"workflow_run_id": requested_workflow_run_id}
            )
    for requested_workflow_root in candidate_workflow_roots:
        workflow_manifest = read_workflow_manifest(requested_workflow_root)
        if workflow_manifest is None:
            continue
        if workflow_manifest.pairs != normalized_request.pair_subset:
            continue
        if workflow_manifest.start != normalized_request.start:
            continue
        if workflow_manifest.end != normalized_request.end:
            continue
        if workflow_manifest.ml_mode != normalized_request.ml_mode:
            continue
        if workflow_manifest.candidate_discovery_mode != normalized_request.candidate_discovery_mode:
            continue
        if int(workflow_manifest.engine_native_sample_size) != int(
            normalized_request.engine_native_sample_size
        ):
            continue
        if bool(workflow_manifest.allow_broad_run) != bool(normalized_request.allow_broad_run):
            continue
        if bool(workflow_manifest.small_scope_enabled) != bool(
            normalized_request.small_scope_enabled
        ):
            continue
        if bool(workflow_manifest.full_scan_enabled) != bool(normalized_request.full_scan_enabled):
            continue
        if bool(workflow_manifest.no_full_scan_enabled) != bool(
            normalized_request.no_full_scan_enabled
        ):
            continue
        if (
            workflow_manifest.silver_storage_mode_requested
            and workflow_manifest.silver_storage_mode_requested != normalized_request.silver_storage_mode
        ):
            continue
        return normalized_request.model_copy(
            update={"workflow_run_id": requested_workflow_run_id}
        )
    return normalized_request
_PAIR_DATE_PATTERN = re.compile(r"^(?P<pair>[A-Z0-9/_-]+)_(?P<date>\d{4}-\d{2}-\d{2})$")
_PAIR_TF_DATE_PATTERN = re.compile(
    r"^(?P<pair>[A-Z0-9/_-]+)_(?P<timeframe>[A-Za-z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})$"
)
_DATE_PAIR_SUFFIX_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<pair>[A-Z0-9/_-]+)(?:_.+)?$"
)
_DATE_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
_SUPPORTED_SUFFIXES_BY_SOURCE = {
    "orderbook": (".data", ".jsonl", ".json", ".data.zip", ".jsonl.zip", ".json.zip", ".data.gz", ".jsonl.gz", ".json.gz"),
    "trades": (".csv", ".csv.gz"),
    "klines": (".csv", ".csv.gz"),
    "metadata": (".csv", ".json", ".jsonl"),
}
_MAX_PREVIEW_PATHS = 5
_ONE_DAY_MS = 86_400_000
_DEFAULT_ENGINE_NATIVE_SAMPLE_SIZE = 10


class BacktestSourcePreview(BaseModel, frozen=True):
    source_kind: str
    selected_path: str = ""
    exists: bool = False
    selected_mode: str = "not_selected"
    preview_status: str = "SOURCE_NOT_SELECTED"
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    pair_inference_source: str = ""
    detected_pairs: tuple[str, ...] = ()
    matched_pairs: tuple[str, ...] = ()
    detected_min_date: str = ""
    detected_max_date: str = ""
    matched_min_date: str = ""
    matched_max_date: str = ""
    matched_days_count: int = 0
    files_seen: int = 0
    files_matched: int = 0
    files_skipped_by_date_filter: int = 0
    matched_paths_preview: tuple[str, ...] = ()


class BacktestPreflightPreview(BaseModel, frozen=True):
    inspection_status: str = "PREVIEW_NOT_PROVEN"
    preview_id: str = ""
    request_hash: str = ""
    workflow_request_hash: str = ""
    workflow_run_id: str = ""
    phase_id: str = PHASE_A1
    phase_label: str = "Phase A1 Preview"
    action_name: str = ""
    normalized_request: Patch6NormalizedRequest = Patch6NormalizedRequest()
    dry_run: bool = False
    requested_pairs: tuple[str, ...] = ()
    detected_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    ignored_source_pairs: tuple[str, ...] = ()
    source_pair_map: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    pair_inference_sources: dict[str, str] = Field(default_factory=dict)
    pair_inference_status: str = "PAIR_NOT_DETECTED"
    pair_mismatch_reason_codes: tuple[str, ...] = ()
    pair_date_intersection_status: str = "PAIR_DATE_INTERSECTION_EMPTY"
    common_data_intersection_status: str = "NO_COMMON_DATA_INTERSECTION"
    common_date_start: str = ""
    common_date_end: str = ""
    common_days_count: int = 0
    metadata_status: str = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    files_matched_total: int = 0
    files_skipped_by_date_filter_total: int = 0
    raw_size_estimate_bytes: int = 0
    silver_size_estimate_bytes: int = 0
    gold_size_estimate_bytes: int = 0
    orderbook: BacktestSourcePreview = BacktestSourcePreview(source_kind="orderbook")
    trades: BacktestSourcePreview = BacktestSourcePreview(source_kind="trades")
    klines: BacktestSourcePreview = BacktestSourcePreview(source_kind="klines")
    metadata: BacktestSourcePreview = BacktestSourcePreview(source_kind="metadata")
    output_root_selected: str = ""
    output_root_effective_preview: str = ""
    output_root_status: str = OUTPUT_ROOT_DEFAULTED
    output_root_blocker: str = ""
    output_root_timestamped_suggestion: str = ""
    candidate_sample_cap: int = 0
    effective_engine_native_sample_size: int = _DEFAULT_ENGINE_NATIVE_SAMPLE_SIZE
    engine_count: int = 4
    candidate_cap_formula: str = ""
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    candidate_discovery_limited: bool = True
    candidate_discovery_limit_reason: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
    silver_storage_mode_requested: str = "jsonl_debug"
    silver_storage_mode_effective: str = "jsonl_debug"
    silver_storage_status: str = "SILVER_STORAGE_NOT_PROVEN"
    storage_budget_status: str = "STORAGE_BUDGET_NOT_PROVEN"
    storage_budget_reason_codes: tuple[str, ...] = ()
    blocker_severity: str = "info"
    recommendation: str = ""
    launch_ready: bool = False
    preview_launchable: bool = False
    execution_realism_claim_status: str = "REALISM_CLAIM_NOT_ASSESSED"
    execution_realism_claim_blockers: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    command_preview: str = ""


def _normalize_boundary_text(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parts = value.split("-")
            if len(parts) != 3:
                return value
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        except (TypeError, ValueError):
            return value
    if "T" not in value:
        return parsed.date().isoformat()
    return parsed.astimezone(UTC).isoformat()


def _parse_time_boundary_to_ms(value: str, *, end_of_day: bool = False) -> int | None:
    normalized = _normalize_boundary_text(value)
    if not normalized:
        return None
    try:
        if "T" in normalized:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return int(parsed.timestamp() * 1000)
        parsed = datetime.fromisoformat(f"{normalized}T00:00:00+00:00")
        millis = int(parsed.timestamp() * 1000)
        return millis + (_ONE_DAY_MS - 1 if end_of_day else 0)
    except ValueError:
        return None


def normalize_pair_symbol(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]", "", str(raw or "").upper())
    return value


def _looks_like_pair_symbol(value: str) -> bool:
    if not value or value in _GENERIC_SEGMENTS:
        return False
    if value.lower() in _GENERIC_SEGMENTS:
        return False
    if value.lower() in _TIMEFRAME_SEGMENTS:
        return False
    if value.isdigit():
        return False
    if re.fullmatch(r"\d{8,}", value):
        return False
    if re.fullmatch(r"\d{4}\d{2}\d{2}", value):
        return False
    if value in _KNOWN_PAIR_SYMBOLS:
        return True
    if not (4 <= len(value) <= 20 and any(char.isalpha() for char in value)):
        return False
    return value.endswith(("USDT", "USDC", "BUSD", "USD", "BTC", "ETH"))


def infer_pair_symbol_from_path_with_source(raw: str) -> tuple[str, str]:
    candidate = (raw or "").strip().strip('"').strip("'")
    if not candidate:
        return "", ""
    normalized_path = candidate.replace("\\", "/").rstrip("/")
    if not normalized_path:
        return "", ""
    path = Path(normalized_path)
    logical_name = path.name
    lowered_name = logical_name.lower()
    for suffix in (
        ".data.zip",
        ".jsonl.zip",
        ".json.zip",
        ".csv.gz",
        ".jsonl.gz",
        ".data.gz",
        ".json.gz",
    ):
        if lowered_name.endswith(suffix):
            logical_name = logical_name[: -len(suffix)] + suffix.rsplit(".", 1)[0]
            break
    stem = Path(logical_name).stem.upper()
    for pattern, source_name in (
        (_PAIR_TF_DATE_PATTERN, "filename"),
        (_PAIR_DATE_PATTERN, "filename"),
        (_DATE_PAIR_SUFFIX_PATTERN, "filename"),
    ):
        match = pattern.match(stem)
        if match:
            inferred = normalize_pair_symbol(str(match.group("pair")))
            if _looks_like_pair_symbol(inferred):
                return inferred, source_name
    parts = [part for part in normalized_path.split("/") if part]
    for index in range(len(parts) - 1, -1, -1):
        segment = parts[index]
        if re.fullmatch(r"\d+", segment.strip()):
            continue
        tokens = re.split(r"[._\-]", segment)
        normalized_tokens = [normalize_pair_symbol(token) for token in tokens if token.strip()]
        for token in normalized_tokens:
            if _looks_like_pair_symbol(token):
                if index == len(parts) - 1 and "." not in segment and not Path(segment).suffix:
                    return token, "parent_dir"
                return token, "filename_or_parent_dir"
        compact = normalize_pair_symbol(segment)
        if _looks_like_pair_symbol(compact):
            return compact, "parent_dir" if "." not in segment and not Path(segment).suffix else "filename_or_parent_dir"
    return "", ""


def infer_pair_symbol_from_path(raw: str) -> str:
    symbol, _ = infer_pair_symbol_from_path_with_source(raw)
    return symbol


def infer_pair_universe_from_paths(paths: tuple[str, ...]) -> tuple[tuple[str, ...], bool]:
    inferred: list[str] = []
    for raw in paths:
        symbol = infer_pair_symbol_from_path(raw)
        if symbol and symbol not in inferred:
            inferred.append(symbol)
    return tuple(inferred), len(inferred) > 1


def _infer_date_from_path(path: Path) -> str:
    match = _DATE_PATTERN.search(path.name)
    return match.group("date") if match else ""


def _path_supported_for_source(path: Path, source_kind: str) -> bool:
    name_lower = path.name.lower()
    suffixes = _SUPPORTED_SUFFIXES_BY_SOURCE.get(source_kind, ())
    return any(name_lower.endswith(suffix) for suffix in suffixes)


def _logical_file_name(path: Path) -> str:
    name = path.name
    lowered = name.lower()
    for suffix in (
        ".data.zip",
        ".jsonl.zip",
        ".json.zip",
        ".csv.gz",
        ".jsonl.gz",
        ".data.gz",
        ".json.gz",
    ):
        if lowered.endswith(suffix):
            return name[: -len(suffix)] + suffix.rsplit(".", 1)[0]
    return name


def _candidate_preference_score(path: Path) -> int:
    lowered = path.name.lower()
    if lowered.endswith((".csv.gz", ".data.gz", ".jsonl.gz", ".json.gz")):
        return 1
    if lowered.endswith((".data.zip", ".jsonl.zip", ".json.zip", ".csv.zip", ".zip")):
        return 2
    return 0


def _candidate_identity(path: Path, source_kind: str) -> str:
    logical_name = _logical_file_name(path).lower()
    if source_kind == "orderbook":
        lowered = str(path).lower()
        orderbook_variant = "generic"
        if "snapshot" in lowered:
            orderbook_variant = "snapshot"
        elif "delta" in lowered:
            orderbook_variant = "delta"
        return f"{source_kind}::{orderbook_variant}::{logical_name}"
    return f"{source_kind}::{logical_name}"


def _iter_supported_source_paths(root: Path, source_kind: str) -> tuple[Path, ...]:
    if root.is_file():
        return (root.resolve(),) if _path_supported_for_source(root, source_kind) else ()
    if not root.is_dir():
        return ()
    rows: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and _path_supported_for_source(path, source_kind):
            rows.append(path.resolve())
    deduped: dict[str, Path] = {}
    for candidate in sorted(rows):
        identity = _candidate_identity(candidate, source_kind)
        existing = deduped.get(identity)
        if existing is None or _candidate_preference_score(candidate) < _candidate_preference_score(existing):
            deduped[identity] = candidate
    return tuple(sorted(deduped.values()))


def _date_matches_range(iso_date: str, *, start_ms: int | None, end_ms: int | None) -> bool:
    if not iso_date or (start_ms is None and end_ms is None):
        return True
    try:
        file_start = int(datetime.fromisoformat(f"{iso_date}T00:00:00+00:00").timestamp() * 1000)
        file_end = int(datetime.fromisoformat(f"{iso_date}T23:59:59+00:00").timestamp() * 1000)
    except ValueError:
        return False
    if start_ms is not None and file_end < start_ms:
        return False
    if end_ms is not None and file_start > end_ms:
        return False
    return True


def _days_count(values: set[str]) -> int:
    return len({value for value in values if value})


def _scan_source_preview(
    *,
    source_kind: str,
    selected_path: str,
    start_ms: int | None,
    end_ms: int | None,
    apply_date_filter: bool = True,
) -> tuple[BacktestSourcePreview, tuple[Path, ...], set[str], set[str]]:
    selected = (selected_path or "").strip()
    if not selected:
        return BacktestSourcePreview(source_kind=source_kind), (), set(), set()
    root = Path(selected).expanduser()
    if not root.exists():
        preview = BacktestSourcePreview(
            source_kind=source_kind,
            selected_path=selected,
            exists=False,
            selected_mode="missing",
            preview_status="SOURCE_PATH_NOT_PROVEN",
        )
        return preview, (), set(), set()
    candidate_paths = _iter_supported_source_paths(root, source_kind)
    detected_pairs: set[str] = set()
    matched_pairs: set[str] = set()
    detected_dates: set[str] = set()
    matched_dates: set[str] = set()
    matched_preview_paths: list[str] = []
    pair_source = ""
    files_matched = 0
    files_skipped_by_date = 0
    matched_raw_paths: list[Path] = []
    for path in candidate_paths:
        inferred_pair, inferred_source = infer_pair_symbol_from_path_with_source(str(path))
        if inferred_pair:
            detected_pairs.add(inferred_pair)
            matched_pairs.add(inferred_pair)
            if not pair_source:
                pair_source = inferred_source
        iso_date = _infer_date_from_path(path)
        if iso_date:
            detected_dates.add(iso_date)
        if apply_date_filter and (start_ms is not None or end_ms is not None):
            if not iso_date:
                files_skipped_by_date += 1
                continue
            if not _date_matches_range(iso_date, start_ms=start_ms, end_ms=end_ms):
                files_skipped_by_date += 1
                continue
        if iso_date:
            matched_dates.add(iso_date)
        files_matched += 1
        matched_raw_paths.append(path)
        if len(matched_preview_paths) < _MAX_PREVIEW_PATHS:
            matched_preview_paths.append(str(path))
    preview_status = "SOURCE_PREVIEW_READY"
    if not apply_date_filter and source_kind == "metadata":
        preview_status = "METADATA_CACHE_READY" if files_matched > 0 else "METADATA_CACHE_NOT_PROVEN"
    elif (start_ms is not None or end_ms is not None) and files_matched == 0:
        preview_status = {
            "orderbook": "ORDERBOOK_NO_FILES_IN_DATE_RANGE",
            "trades": "TRADES_NO_FILES_IN_DATE_RANGE",
            "klines": "KLINES_NO_FILES_IN_DATE_RANGE",
            "metadata": "NO_FILES_MATCH_DATE_RANGE",
        }.get(source_kind, "NO_FILES_MATCH_DATE_RANGE")
    elif not candidate_paths:
        preview_status = (
            "METADATA_CACHE_NOT_PROVEN"
            if source_kind == "metadata"
            else "SOURCE_FILES_NOT_PROVEN"
        )
    pair_inference_status = "PAIR_NOT_DETECTED"
    if len(detected_pairs) == 1:
        pair_inference_status = (
            "PAIR_INFERRED_FROM_PARENT_DIR"
            if pair_source == "parent_dir"
            else "PAIR_INFERRED_FROM_FILENAME"
        )
    elif len(detected_pairs) > 1:
        pair_inference_status = "MULTIPLE_PAIRS_DISCOVERED"
    preview = BacktestSourcePreview(
        source_kind=source_kind,
        selected_path=str(root),
        exists=True,
        selected_mode=("file" if root.is_file() else "directory"),
        preview_status=preview_status,
        pair_inference_status=pair_inference_status,
        pair_inference_source=pair_source,
        detected_pairs=tuple(sorted(detected_pairs)),
        matched_pairs=tuple(sorted(matched_pairs)),
        detected_min_date=min(detected_dates, default=""),
        detected_max_date=max(detected_dates, default=""),
        matched_min_date=min(matched_dates, default=""),
        matched_max_date=max(matched_dates, default=""),
        matched_days_count=_days_count(matched_dates),
        files_seen=len(candidate_paths),
        files_matched=files_matched,
        files_skipped_by_date_filter=files_skipped_by_date,
        matched_paths_preview=tuple(matched_preview_paths),
    )
    return preview, tuple(matched_raw_paths), matched_pairs, matched_dates


def _selected_action_is_dry_run(action_name: str) -> bool:
    return action_name in {
        StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
        StrategyLadderControlAction.DATA_FACTORY_DRY_RUN.value,
        StrategyLadderControlAction.FIRST_CONTROLLED_RUN_DRY_RUN.value,
    }


def _selected_action_job_kind(action_name: str) -> CockpitBacktestJobKind:
    if action_name in {
        StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
        StrategyLadderControlAction.PHASE_A2_DATA_FACTORY.value,
        StrategyLadderControlAction.DATA_FACTORY_DRY_RUN.value,
        StrategyLadderControlAction.DATA_FACTORY_SMALL_SCOPE_RUN.value,
    }:
        return CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
    if action_name in {
        StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value,
        StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value,
    }:
        return CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
    return CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN


def _build_preview_command(
    *,
    action_name: str,
    export_dir: str,
    baseline_export_dir: str,
    raw_source_manifest_path: str,
    orderbook_path: str,
    trades_path: str,
    klines_path: str,
    metadata_path: str,
    pairs: tuple[str, ...],
    start: str,
    end: str,
    output_root: str,
    workflow_run_id: str,
    engine_native_sample_size: int,
    candidate_discovery_mode: str,
    small_scope_enabled: bool,
    full_scan_enabled: bool,
    no_full_scan_enabled: bool,
    allow_broad_run: bool,
    silver_storage_mode: str,
) -> str:
    job_kind = _selected_action_job_kind(action_name)
    script = (
        "run_strategy_ladder_data_factory.py"
        if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
        else "run_backtest_strategy_ladder.py"
        if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
        else "run_strategy_ladder_first_controlled_run.py"
    )
    parts = ["python", f"scripts/{script}", "--run-id", workflow_run_id or "preview-job"]
    if output_root:
        parts.extend(["--output-root", output_root])
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY:
        parts.extend(["--silver-root", str(Path(output_root) / "silver")])
        parts.extend(["--gold-root", str(Path(output_root) / "gold")])
        parts.extend(
            [
                "--storage-format",
                (
                    "jsonl-gz"
                    if silver_storage_mode == "jsonl_gz"
                    else "parquet"
                    if silver_storage_mode == "parquet"
                    else "jsonl"
                ),
            ]
        )
    else:
        parts.extend(["--input-root", output_root])
    if baseline_export_dir:
        parts.extend(["--baseline-export-dir", baseline_export_dir])
    for selected in (orderbook_path, trades_path, klines_path):
        cleaned = (selected or "").strip()
        if cleaned:
            parts.extend(["--raw-root", cleaned])
    if metadata_path:
        parts.extend(["--historical-metadata-root", metadata_path])
    if raw_source_manifest_path:
        parts.extend(["--raw-source-manifest", raw_source_manifest_path])
    if pairs:
        parts.extend(["--pairs", ",".join(pairs)])
    if start:
        parts.extend(["--start", start])
    if end:
        parts.extend(["--end", end])
    if allow_broad_run:
        parts.append("--allow-broad-run")
    if small_scope_enabled:
        parts.append("--small-scope")
    if no_full_scan_enabled and script == "run_strategy_ladder_first_controlled_run.py":
        parts.append("--no-full-scan")
    if job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER:
        parts.extend(
            [
                "--engine-native-mode",
                "--engine-native-sample-size",
                str(engine_native_sample_size),
                "--candidate-discovery-mode",
                candidate_discovery_mode,
                "--candidate-sample-cap",
                str(engine_native_sample_size),
            ]
        )
        if action_name == StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value:
            parts.append("--fast-only")
        elif action_name == StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value:
            parts.extend(["--detailed-only", "--resume"])
    elif job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN:
        parts.extend(
            [
                "--engine-native-mode",
                "--engine-native-sample-size",
                str(engine_native_sample_size),
            ]
        )
    if _selected_action_is_dry_run(action_name):
        parts.append("--dry-run")
    return " ".join(parts)


def build_patch6_preflight_preview(
    *,
    selected_form: BacktestFormState,
    jobs_root: Path | None,
) -> BacktestPreflightPreview:
    normalized_request = build_patch6_normalized_request(selected_form)
    action_name = normalized_request.action_name
    dry_run = normalized_request.dry_run
    normalized_start = _normalize_boundary_text(selected_form.start)
    normalized_end = _normalize_boundary_text(selected_form.end)
    start_ms = _parse_time_boundary_to_ms(normalized_start, end_of_day=False)
    end_ms = _parse_time_boundary_to_ms(normalized_end, end_of_day=True)

    orderbook, orderbook_paths, orderbook_pairs, orderbook_dates = _scan_source_preview(
        source_kind="orderbook",
        selected_path=selected_form.orderbook_path,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    trades, trades_paths, trades_pairs, trades_dates = _scan_source_preview(
        source_kind="trades",
        selected_path=selected_form.trades_path,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    klines, klines_paths, klines_pairs, klines_dates = _scan_source_preview(
        source_kind="klines",
        selected_path=selected_form.klines_path,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    metadata, metadata_paths, metadata_pairs, _ = _scan_source_preview(
        source_kind="metadata",
        selected_path=selected_form.metadata_path,
        start_ms=start_ms,
        end_ms=end_ms,
        apply_date_filter=False,
    )
    selected_sources = {
        "orderbook": orderbook,
        "trades": trades,
        "klines": klines,
        "metadata": metadata,
    }
    requested_pairs = tuple(
        pair for pair in (normalize_pair_symbol(item) for item in selected_form.pairs) if pair
    )
    detected_pairs = tuple(
        sorted(
            {
                *orderbook.detected_pairs,
                *trades.detected_pairs,
                *klines.detected_pairs,
                *metadata.detected_pairs,
            }
        )
    )
    source_pair_map = {
        "orderbook": orderbook.detected_pairs,
        "trades": trades.detected_pairs,
        "klines": klines.detected_pairs,
        "metadata": metadata.detected_pairs,
    }
    pair_inference_sources = {
        "orderbook": orderbook.pair_inference_source,
        "trades": trades.pair_inference_source,
        "klines": klines.pair_inference_source,
        "metadata": metadata.pair_inference_source,
    }
    pair_blockers: list[str] = []
    pair_mismatch_reason_codes: list[str] = []
    active_pairs_after_pruning: tuple[str, ...] = requested_pairs or detected_pairs
    ignored_source_pairs = tuple(
        sorted(
            {
                pair
                for pair in detected_pairs
                if requested_pairs and pair not in requested_pairs
            }
        )
    )
    if ignored_source_pairs:
        pair_mismatch_reason_codes.append("IGNORED_SOURCE_PAIR_DETECTED")
    if not requested_pairs and len(detected_pairs) == 1:
        pair_inference_status = "PAIR_AUTO_DETECTED_READY"
        active_pairs_after_pruning = detected_pairs
    elif not requested_pairs and len(detected_pairs) > 1:
        pair_inference_status = "MULTIPLE_PAIRS_DISCOVERED"
        pair_blockers.append("MULTIPLE_PAIRS_DISCOVERED")
        active_pairs_after_pruning = ()
    elif requested_pairs and detected_pairs:
        if not any(pair in detected_pairs for pair in requested_pairs):
            pair_inference_status = "REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES"
            pair_blockers.append("REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES")
            active_pairs_after_pruning = ()
        else:
            source_conflicts = [
                source_name
                for source_name, pairs in source_pair_map.items()
                if pairs and not set(pairs).intersection(requested_pairs)
            ]
            if source_conflicts:
                pair_inference_status = "REQUESTED_PAIR_MISMATCH_WITH_SOURCE"
                pair_mismatch_reason_codes.extend(
                    "RAW_ROOT_PAIR_MISMATCH_WITH_REQUESTED_PAIR"
                    for _ in source_conflicts
                )
            else:
                pair_inference_status = "PAIR_AUTO_DETECTED_READY"
            active_pairs_after_pruning = tuple(
                pair for pair in requested_pairs if pair in detected_pairs
            )
    else:
        pair_inference_status = "PAIR_NOT_DETECTED"

    required_source_pairs = [
        pairs
        for name, pairs in (
            ("orderbook", orderbook_pairs),
            ("trades", trades_pairs),
            ("klines", klines_pairs),
        )
        if selected_sources[name].exists and selected_sources[name].selected_path
    ]
    required_source_dates = [
        dates
        for name, dates in (
            ("orderbook", orderbook_dates),
            ("trades", trades_dates),
            ("klines", klines_dates),
        )
        if selected_sources[name].exists and selected_sources[name].selected_path
    ]
    if requested_pairs:
        active_requested = set(active_pairs_after_pruning)
        required_source_pairs = [
            {pair for pair in pairs if pair in active_requested}
            for pairs in required_source_pairs
        ]
    common_pairs = (
        set.intersection(*required_source_pairs)
        if required_source_pairs
        else set(active_pairs_after_pruning)
    )
    common_dates = set.intersection(*required_source_dates) if required_source_dates else set()
    common_data_intersection_status = "PAIR_DATE_INTERSECTION_EMPTY"
    if common_pairs and (common_dates or len(required_source_dates) <= 1):
        common_data_intersection_status = "PAIR_DATE_INTERSECTION_READY"
    if len(required_source_dates) >= 2 and not common_dates:
        pair_blockers.append("NO_COMMON_DATA_INTERSECTION")
        common_data_intersection_status = "NO_COMMON_DATA_INTERSECTION"
    elif len(required_source_pairs) >= 2 and not common_pairs:
        pair_blockers.append("PAIR_MISMATCH_BETWEEN_SOURCES")
        common_data_intersection_status = "PAIR_DATE_INTERSECTION_EMPTY"
    elif requested_pairs and not active_pairs_after_pruning:
        pair_blockers.append("PAIR_NOT_AVAILABLE_AFTER_DATE_PRUNING")
    if len(required_source_pairs) >= 2 and len({tuple(sorted(pairs)) for pairs in required_source_pairs if pairs}) > 1:
        pair_mismatch_reason_codes.append("PAIR_MISMATCH_BETWEEN_SOURCES")

    for source_name, source_preview in selected_sources.items():
        if source_name == "metadata":
            continue
        if not source_preview.selected_path or not source_preview.exists:
            continue
        if source_preview.preview_status.endswith("_NO_FILES_IN_DATE_RANGE") or source_preview.preview_status == "NO_FILES_MATCH_DATE_RANGE":
            pair_blockers.append(source_preview.preview_status)

    raw_paths = tuple((*orderbook_paths, *trades_paths, *klines_paths))
    raw_size_estimate, silver_size_estimate = estimate_silver_size_for_paths(raw_paths)
    gold_size_estimate = int(silver_size_estimate * 0.08) if not dry_run and klines.files_matched > 0 else 0

    output_root_text = (selected_form.output_root or "").strip()
    default_preview_root = (
        (jobs_root / "__preview__" / "output")
        if jobs_root is not None
        else Path.cwd() / "__preview__" / "output"
    )
    raw_root_paths = tuple(
        Path(path).expanduser()
        for path in (
            selected_form.orderbook_path,
            selected_form.trades_path,
            selected_form.klines_path,
            selected_form.metadata_path,
        )
        if (path or "").strip()
    )
    output_candidate = output_root_text
    if output_candidate:
        output_candidate = str(Path(output_candidate).expanduser() / "runs" / "__preview__")
    resolved_output_root, output_root_status, output_root_blocker = resolve_output_root(
        operator_output_root=output_candidate,
        default_output_root=default_preview_root,
        raw_roots=raw_root_paths,
        allow_resume=False,
    )
    effective_output_root = str(resolved_output_root.resolve())
    if output_root_blocker:
        effective_output_root = str(default_preview_root.resolve())
    output_root_timestamped_suggestion = ""
    if output_root_text:
        output_root_timestamped_suggestion = str(
            Path(output_root_text).expanduser()
            / "runs"
            / datetime.now(tz=UTC).strftime("preview_%Y%m%d_%H%M%S")
        )
    if output_root_status == OUTPUT_ROOT_EXISTS_NON_EMPTY:
        pair_blockers.append(OUTPUT_ROOT_EXISTS_NON_EMPTY)
    if selected_form.raw_source_manifest_path and not is_valid_raw_source_manifest_path(
        selected_form.raw_source_manifest_path
    ):
        pair_blockers.append("RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE")

    inspection_ready = any(
        preview.exists and preview.selected_path
        for preview in (orderbook, trades, klines, metadata)
    )
    files_matched_total = sum(
        preview.files_matched for preview in (orderbook, trades, klines, metadata)
    )
    files_skipped_total = sum(
        preview.files_skipped_by_date_filter
        for preview in (orderbook, trades, klines, metadata)
    )
    launch_ready = (
        inspection_ready
        and not pair_blockers
        and common_data_intersection_status == "PAIR_DATE_INTERSECTION_READY"
        and files_matched_total > 0
    )
    preview_launchable = launch_ready
    warnings: list[str] = []
    execution_realism_claim_blockers: list[str] = []
    if ignored_source_pairs:
        warnings.append("IGNORED_SOURCE_PAIR_DETECTED")
    if metadata.selected_path and not metadata.files_matched:
        warnings.append("METADATA_PAIR_NOT_FOUND")
    if dry_run:
        execution_realism_claim_blockers.append(
            "DRY_RUN_CANNOT_PRODUCE_PROMOTION_GRADE_EXECUTION_REALISM"
        )
    if not orderbook.selected_path or not trades.selected_path:
        execution_realism_claim_blockers.append(
            "ORDERBOOK_AND_TRADES_REQUIRED_FOR_EXECUTION_REALISM"
        )
    normalized_request = build_patch6_normalized_request(
        selected_form,
        detected_pairs=detected_pairs,
        active_pairs_after_pruning=active_pairs_after_pruning,
    )
    requested_workflow_run_id = normalized_request.workflow_run_id
    normalized_request, workflow_request_hash = canonicalize_workflow_identity(
        normalized_request
    )
    normalized_request = _reuse_matching_workflow_parent(
        normalized_request=normalized_request,
        requested_workflow_run_id=requested_workflow_run_id,
        workflow_request_hash=workflow_request_hash,
        output_root_text=output_root_text,
        jobs_root=jobs_root,
    )
    request_hash = request_hash_for_normalized_request(normalized_request)
    workflow_run_id = normalized_request.workflow_run_id
    preview_id = f"preview-{request_hash[:16]}"
    workflow_root = _workflow_root_for_run_id(
        workflow_run_id=workflow_run_id,
        output_root_text=output_root_text,
        jobs_root=jobs_root,
    )
    effective_output_root = str(
        (workflow_root / workflow_phase_dirname(normalized_request.phase_id)).resolve()
    )
    candidate_sample_cap = max(int(normalized_request.engine_native_sample_size), 0) * 4
    candidate_cap_formula = (
        f"4 engines x {max(int(normalized_request.engine_native_sample_size), 0)}"
    )
    candidate_discovery_limited = (
        normalized_request.candidate_discovery_mode == "SAMPLE_CAPPED_DEBUG"
        or normalized_request.small_scope_enabled
        or max(int(normalized_request.engine_native_sample_size), 0) > 0
    )
    candidate_discovery_limit_reason = (
        "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
        if candidate_discovery_limited
        else ""
    )
    candidate_discovery_cap_status = (
        "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
        if normalized_request.candidate_discovery_mode == "SAMPLE_CAPPED_DEBUG"
        else (
            "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED"
            if normalized_request.full_scan_enabled
            else "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
        )
    )
    silver_storage_mode_requested = normalized_request.silver_storage_mode
    silver_storage_mode_effective = silver_storage_mode_requested
    storage_budget_status = "STORAGE_BUDGET_NOT_PROVEN"
    silver_storage_status = "SILVER_STORAGE_NOT_PROVEN"
    recommendation = ""
    blocker_severity = "info"
    storage_budget_reason_codes: list[str] = []
    broad_scope = normalized_request.allow_broad_run and not normalized_request.small_scope_enabled
    if silver_storage_mode_requested == "parquet":
        silver_storage_status = "SILVER_STORAGE_READER_NOT_PROVEN"
        storage_budget_status = "SILVER_STORAGE_READER_NOT_PROVEN"
        storage_budget_reason_codes.append("SILVER_STORAGE_READER_NOT_PROVEN")
        pair_blockers.append("SILVER_STORAGE_READER_NOT_PROVEN")
        blocker_severity = "error"
        recommendation = "Parquet remains experimental for Silver in this rail. Use jsonl_gz."
    elif broad_scope and silver_storage_mode_requested == "jsonl_debug" and not normalized_request.debug_storage_override:
        silver_storage_status = "SILVER_STORAGE_BLOAT_BLOCKER"
        storage_budget_status = "SILVER_STORAGE_BLOAT_BLOCKER"
        storage_budget_reason_codes.append("SILVER_STORAGE_BLOAT_BLOCKER")
        pair_blockers.append("SILVER_STORAGE_BLOAT_BLOCKER")
        blocker_severity = "error"
        recommendation = "Broad runs must use jsonl_gz unless explicit debug-storage override is set."
    elif silver_storage_mode_requested == "jsonl_gz":
        silver_storage_status = "SILVER_STORAGE_READY_COMPRESSED"
        storage_budget_status = "STORAGE_BUDGET_READY"
        blocker_severity = "info"
        recommendation = "Compressed Silver is selected for broad diagnostic runs."
    else:
        silver_storage_status = "SILVER_STORAGE_JSONL_DEBUG_ALLOWED"
        storage_budget_status = "STORAGE_BUDGET_WARNING"
        blocker_severity = "warning"
        recommendation = (
            "jsonl_debug is allowed only for small/debug runs and should not be used for broad diagnostics."
        )
    phase_a2_root = workflow_root / workflow_phase_dirname(PHASE_A2)
    phase_b1_root = workflow_root / workflow_phase_dirname(PHASE_B1)
    phase_a2_manifest_path = phase_a2_root / "data_factory_manifest.json"
    phase_a2_gold_root = phase_a2_root / "gold"
    phase_a2_silver_index_path = phase_a2_root / "silver_index.json"
    phase_b1_candidate_events_path = (
        phase_b1_root
        / "backtest_strategy_ladder"
        / workflow_run_id
        / "fast_candidates"
        / "candidate_events.jsonl"
    )
    if normalized_request.phase_id == PHASE_B1:
        if not phase_a2_manifest_path.is_file():
            pair_blockers.append("PHASE_B1_REQUIRES_A2_DATA_FACTORY_ARTIFACTS")
        if not phase_a2_gold_root.is_dir():
            pair_blockers.append("FEATURE_STORE_NOT_MATERIALIZED_FOR_B1")
        if not phase_a2_silver_index_path.is_file():
            pair_blockers.append("SILVER_INDEX_NOT_MATERIALIZED_FOR_B1")
    elif normalized_request.phase_id == PHASE_B2:
        if not phase_a2_manifest_path.is_file():
            pair_blockers.append("PHASE_B2_REQUIRES_A2_DATA_FACTORY_ARTIFACTS")
        if not phase_a2_silver_index_path.is_file():
            pair_blockers.append("SILVER_INDEX_NOT_MATERIALIZED_FOR_B2")
        if not phase_b1_candidate_events_path.is_file():
            pair_blockers.append("PHASE_B2_REQUIRES_B1_CANDIDATE_EVENTS")
    command_preview = ""
    if launch_ready:
        command_preview = _build_preview_command(
            action_name=action_name,
            export_dir=selected_form.export_dir,
            baseline_export_dir=selected_form.baseline_export_dir,
            raw_source_manifest_path=selected_form.raw_source_manifest_path,
            orderbook_path=selected_form.orderbook_path,
            trades_path=selected_form.trades_path,
            klines_path=selected_form.klines_path,
            metadata_path=selected_form.metadata_path,
            pairs=normalized_request.pair_subset,
            start=normalized_request.start,
            end=normalized_request.end,
            output_root=effective_output_root,
            workflow_run_id=workflow_run_id,
            engine_native_sample_size=normalized_request.engine_native_sample_size,
            candidate_discovery_mode=normalized_request.candidate_discovery_mode,
            small_scope_enabled=normalized_request.small_scope_enabled,
            full_scan_enabled=normalized_request.full_scan_enabled,
            no_full_scan_enabled=normalized_request.no_full_scan_enabled,
            allow_broad_run=normalized_request.allow_broad_run,
            silver_storage_mode=normalized_request.silver_storage_mode,
        )

    common_dates_sorted = sorted(common_dates)
    metadata_status = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
    if metadata.files_matched > 0:
        if normalized_request.pair_subset and metadata.detected_pairs:
            missing_pairs = {
                pair
                for pair in normalized_request.pair_subset
                if pair not in metadata.detected_pairs
            }
            metadata_status = (
                "METADATA_PAIR_NOT_FOUND" if missing_pairs else "BYBIT_HISTORICAL_METADATA_READY"
            )
            if missing_pairs:
                warnings.append("METADATA_PAIR_NOT_FOUND")
        else:
            metadata_status = "BYBIT_HISTORICAL_METADATA_READY"
    if metadata_status != "BYBIT_HISTORICAL_METADATA_READY":
        execution_realism_claim_blockers.append(
            "HISTORICAL_METADATA_REQUIRED_FOR_REALISTIC_EXECUTION_COSTS"
        )
    pair_mismatch_blocked = any(
        blocker == "REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES"
        for blocker in pair_blockers
    ) or "PAIR_MISMATCH_BETWEEN_SOURCES" in pair_mismatch_reason_codes
    if normalized_request.phase_id == PHASE_A1:
        if pair_mismatch_blocked:
            inspection_status = "PREVIEW_BLOCKED_BY_PAIR_MISMATCH"
        else:
            inspection_status = (
                "PHASE_A1_PREVIEW_READY" if inspection_ready else "PHASE_A1_PREVIEW_BLOCKED"
            )
        preview_launchable = False
        launch_ready = False
    elif normalized_request.phase_id == PHASE_A2:
        if "SILVER_STORAGE_BLOAT_BLOCKER" in pair_blockers or "SILVER_STORAGE_READER_NOT_PROVEN" in pair_blockers:
            inspection_status = "PHASE_A2_STORAGE_BLOCKED"
        elif launch_ready:
            inspection_status = "PHASE_A2_DATA_FACTORY_READY"
        else:
            inspection_status = "PHASE_A2_DATA_FACTORY_BLOCKED"
    elif normalized_request.phase_id == PHASE_B1:
        inspection_status = (
            "PHASE_B1_CANDIDATE_DISCOVERY_READY"
            if launch_ready and not pair_blockers
            else "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
        )
    else:
        inspection_status = (
            "PHASE_B2_DETAILED_REPLAY_READY"
            if launch_ready and not pair_blockers
            else "PHASE_B2_BACKTEST_PROOF_BLOCKED"
        )
    if normalized_request.phase_id != PHASE_A1:
        preview_launchable = launch_ready and not pair_blockers
    execution_realism_claim_status = (
        "REALISM_CLAIM_BLOCKED"
        if execution_realism_claim_blockers
        else "REALISM_CLAIM_POSSIBLE"
    )
    return BacktestPreflightPreview(
        inspection_status=inspection_status,
        preview_id=preview_id,
        request_hash=request_hash,
        workflow_request_hash=workflow_request_hash,
        workflow_run_id=workflow_run_id,
        phase_id=phase_id_for_action(action_name),
        phase_label=phase_label_for_action(action_name),
        action_name=action_name,
        normalized_request=normalized_request,
        dry_run=dry_run,
        requested_pairs=requested_pairs,
        detected_pairs=detected_pairs,
        active_pairs_after_pruning=active_pairs_after_pruning,
        ignored_source_pairs=ignored_source_pairs,
        source_pair_map=source_pair_map,
        pair_inference_sources=pair_inference_sources,
        pair_inference_status=pair_inference_status,
        pair_mismatch_reason_codes=tuple(dict.fromkeys(pair_mismatch_reason_codes)),
        pair_date_intersection_status=(
            "PAIR_DATE_INTERSECTION_READY" if common_data_intersection_status == "PAIR_DATE_INTERSECTION_READY" else "PAIR_DATE_INTERSECTION_EMPTY"
        ),
        common_data_intersection_status=common_data_intersection_status,
        common_date_start=(common_dates_sorted[0] if common_dates_sorted else ""),
        common_date_end=(common_dates_sorted[-1] if common_dates_sorted else ""),
        common_days_count=len(common_dates_sorted),
        metadata_status=metadata_status,
        files_matched_total=files_matched_total,
        files_skipped_by_date_filter_total=files_skipped_total,
        raw_size_estimate_bytes=raw_size_estimate,
        silver_size_estimate_bytes=silver_size_estimate,
        gold_size_estimate_bytes=gold_size_estimate,
        orderbook=orderbook,
        trades=trades,
        klines=klines,
        metadata=metadata,
        output_root_selected=output_root_text,
        output_root_effective_preview=effective_output_root,
        output_root_status=output_root_status,
        output_root_blocker=output_root_blocker,
        output_root_timestamped_suggestion=output_root_timestamped_suggestion,
        candidate_sample_cap=candidate_sample_cap,
        effective_engine_native_sample_size=normalized_request.engine_native_sample_size,
        engine_count=4,
        candidate_cap_formula=candidate_cap_formula,
        small_scope_enabled=normalized_request.small_scope_enabled,
        full_scan_enabled=normalized_request.full_scan_enabled,
        no_full_scan_enabled=normalized_request.no_full_scan_enabled,
        candidate_discovery_limited=candidate_discovery_limited,
        candidate_discovery_limit_reason=candidate_discovery_limit_reason,
        candidate_discovery_mode=normalized_request.candidate_discovery_mode,
        candidate_discovery_cap_status=candidate_discovery_cap_status,
        silver_storage_mode_requested=silver_storage_mode_requested,
        silver_storage_mode_effective=silver_storage_mode_effective,
        silver_storage_status=silver_storage_status,
        storage_budget_status=storage_budget_status,
        storage_budget_reason_codes=tuple(dict.fromkeys(storage_budget_reason_codes)),
        blocker_severity=blocker_severity,
        recommendation=recommendation,
        launch_ready=launch_ready,
        preview_launchable=preview_launchable,
        execution_realism_claim_status=execution_realism_claim_status,
        execution_realism_claim_blockers=tuple(
            dict.fromkeys(execution_realism_claim_blockers)
        ),
        blockers=tuple(dict.fromkeys(pair_blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
        command_preview=command_preview,
    )


def load_patch6_preflight_preview(
    *,
    selected_form: BacktestFormState,
    preview_manifest: BacktestPreviewManifest | None,
) -> BacktestPreflightPreview:
    normalized_request = build_patch6_normalized_request(selected_form)
    requested_workflow_run_id = normalized_request.workflow_run_id
    normalized_request, workflow_request_hash = canonicalize_workflow_identity(
        normalized_request
    )
    normalized_request = _reuse_matching_workflow_parent(
        normalized_request=normalized_request,
        requested_workflow_run_id=requested_workflow_run_id,
        workflow_request_hash=workflow_request_hash,
        output_root_text=selected_form.export_dir,
        jobs_root=None,
    )
    request_hash = request_hash_for_normalized_request(normalized_request)
    if preview_manifest is not None:
        payload = preview_manifest.preview_payload
        if isinstance(payload, dict) and payload:
            try:
                loaded = BacktestPreflightPreview.model_validate(payload)
            except ValueError:
                loaded = None
            if loaded is not None and loaded.request_hash == request_hash:
                return loaded
        if preview_manifest.request_hash == request_hash:
            matched_files_by_type = preview_manifest.matched_files_by_type or {}
            common_range = preview_manifest.common_date_range or {}
            return BacktestPreflightPreview(
                inspection_status=preview_manifest.inspection_status,
                preview_id=preview_manifest.preview_id,
                request_hash=preview_manifest.request_hash,
                workflow_request_hash=preview_manifest.workflow_request_hash,
                workflow_run_id=preview_manifest.workflow_run_id,
                phase_id=preview_manifest.phase_id or normalized_request.phase_id,
                phase_label=preview_manifest.phase_label or normalized_request.phase_label,
                action_name=preview_manifest.action_name or normalized_request.action_name,
                normalized_request=preview_manifest.normalized_request,
                dry_run=preview_manifest.normalized_request.dry_run,
                requested_pairs=preview_manifest.requested_pairs,
                detected_pairs=preview_manifest.detected_pairs,
                active_pairs_after_pruning=preview_manifest.active_pairs_after_pruning,
                metadata_status=preview_manifest.metadata_status,
                files_matched_total=preview_manifest.matched_files_total,
                orderbook=BacktestSourcePreview(
                    source_kind="orderbook",
                    preview_status=(
                        "SOURCE_PREVIEW_READY"
                        if int(matched_files_by_type.get("orderbook") or 0) > 0
                        else "SOURCE_NOT_SELECTED"
                    ),
                    files_matched=int(matched_files_by_type.get("orderbook") or 0),
                ),
                trades=BacktestSourcePreview(
                    source_kind="trades",
                    preview_status=(
                        "SOURCE_PREVIEW_READY"
                        if int(matched_files_by_type.get("trades") or 0) > 0
                        else "SOURCE_NOT_SELECTED"
                    ),
                    files_matched=int(matched_files_by_type.get("trades") or 0),
                ),
                klines=BacktestSourcePreview(
                    source_kind="klines",
                    preview_status=(
                        "SOURCE_PREVIEW_READY"
                        if int(matched_files_by_type.get("klines") or 0) > 0
                        else "SOURCE_NOT_SELECTED"
                    ),
                    files_matched=int(matched_files_by_type.get("klines") or 0),
                ),
                metadata=BacktestSourcePreview(
                    source_kind="metadata",
                    preview_status=(
                        "METADATA_CACHE_READY"
                        if int(matched_files_by_type.get("metadata") or 0) > 0
                        else "SOURCE_NOT_SELECTED"
                    ),
                    files_matched=int(matched_files_by_type.get("metadata") or 0),
                ),
                output_root_selected=preview_manifest.output_root_selected,
                output_root_effective_preview=preview_manifest.output_root_effective,
                common_data_intersection_status=preview_manifest.common_intersection_status,
                common_date_start=str(common_range.get("start") or ""),
                common_date_end=str(common_range.get("end") or ""),
                common_days_count=int(common_range.get("days_count") or 0),
                preview_launchable=preview_manifest.preview_launchable,
                launch_ready=preview_manifest.preview_launchable,
                blockers=preview_manifest.blockers,
                warnings=preview_manifest.warnings,
                command_preview=preview_manifest.command_preview,
            )
    return BacktestPreflightPreview(
        inspection_status="PREVIEW_NOT_GENERATED",
        preview_id="",
        request_hash=request_hash,
        workflow_request_hash=workflow_request_hash,
        workflow_run_id=normalized_request.workflow_run_id,
        phase_id=normalized_request.phase_id,
        phase_label=normalized_request.phase_label,
        action_name=normalized_request.action_name,
        normalized_request=normalized_request,
        dry_run=normalized_request.dry_run,
        requested_pairs=normalized_request.pair_subset,
        output_root_selected=normalized_request.output_root_selected,
        warnings=(
            "MANUAL_REFRESH_REQUIRED_FOR_BACKTEST_PREVIEW",
            "Use Generate Preview to scan selected source folders.",
        ),
    )


__all__ = [
    "BacktestPreflightPreview",
    "BacktestSourcePreview",
    "build_patch6_preflight_preview",
    "load_patch6_preflight_preview",
    "infer_pair_symbol_from_path",
    "infer_pair_symbol_from_path_with_source",
    "infer_pair_universe_from_paths",
    "normalize_pair_symbol",
]
