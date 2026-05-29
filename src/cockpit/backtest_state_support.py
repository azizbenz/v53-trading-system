"""Patch 6 cockpit state, phase, and preview-manifest helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from typing import Any

from pydantic import BaseModel, Field

from cockpit.action_support import StrategyLadderControlAction
from cockpit.form_state_support import BacktestFormState
from cockpit.strategy_ladder_workflow_support import PHASE_A1, PHASE_A2, PHASE_B1, PHASE_B2, PHASE_B_ML
from interface_contracts.atomic_io import atomic_write_json


_CURRENT_FORM_STATE_FILENAME = "_current_form_state.json"
_SOURCE_PREVIEW_STATE_FILENAME = "_source_preview_state.json"
_LAUNCH_REQUEST_STATE_FILENAME = "_launch_request_state.json"
_LATEST_JOB_STATE_FILENAME = "_latest_job_state.json"
_LATEST_CANONICAL_SUMMARY_STATE_FILENAME = "_latest_canonical_summary_state.json"
_PREVIEW_MANIFEST_FILENAME = "source_date_preview_manifest.json"
_BACKTEST_ML_CHAIN_STATE_FILENAME = "_backtest_ml_chain_state.json"


CANONICAL_ACTION_BY_PHASE_ID: dict[str, str] = {
    StrategyLadderControlAction.PHASE_A1_PREVIEW.value: PHASE_A1,
    StrategyLadderControlAction.PHASE_A2_DATA_FACTORY.value: PHASE_A2,
    StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value: PHASE_B1,
    StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY.value: PHASE_B_ML,
    StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value: PHASE_B2,
}
LEGACY_ACTION_PHASE_ALIASES: dict[str, str] = {
    StrategyLadderControlAction.DATA_FACTORY_DRY_RUN.value: "PHASE_1A",
    StrategyLadderControlAction.DATA_FACTORY_SMALL_SCOPE_RUN.value: "PHASE_1B",
    StrategyLadderControlAction.FIRST_CONTROLLED_RUN_DRY_RUN.value: "PHASE_2A",
    StrategyLadderControlAction.FIRST_CONTROLLED_RUN_SMALL_SCOPE.value: "PHASE_2B",
}
PHASE_ID_BY_ACTION: dict[str, str] = {
    **CANONICAL_ACTION_BY_PHASE_ID,
    **LEGACY_ACTION_PHASE_ALIASES,
}
ACTION_BY_PHASE_ID: dict[str, str] = {
    PHASE_A1: StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
    PHASE_A2: StrategyLadderControlAction.PHASE_A2_DATA_FACTORY.value,
    PHASE_B1: StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY.value,
    PHASE_B_ML: StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY.value,
    PHASE_B2: StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY.value,
    **{
        phase_id: action_name
        for action_name, phase_id in LEGACY_ACTION_PHASE_ALIASES.items()
        if phase_id not in {PHASE_A1, PHASE_A2, PHASE_B1, PHASE_B2}
    },
}
PHASE_LABEL_BY_ID: dict[str, str] = {
    PHASE_A1: "Phase A1 Preview",
    PHASE_A2: "Phase A2 Data Factory",
    PHASE_B1: "Phase B1 Candidate Discovery",
    PHASE_B_ML: "Phase B_ML Training Label Factory",
    PHASE_B2: "Phase B2 Detailed Replay",
    "PHASE_1A": "Phase A1 Preview",
    "PHASE_1B": "Phase A2 Data Factory",
    "PHASE_2A": "Legacy Combined Preview",
    "PHASE_2B": "Legacy Combined Diagnostic",
}
SUPPORTED_BACKTEST_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "10m", "15m")


def normalize_backtest_timeframes(raw_value: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if isinstance(raw_value, str):
        tokens = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    else:
        tokens = tuple(str(part).strip() for part in raw_value if str(part).strip())
    normalized = tuple(
        dict.fromkeys(token for token in tokens if token in SUPPORTED_BACKTEST_TIMEFRAMES)
    )
    return normalized or ("1m",)


class Patch6NormalizedRequest(BaseModel, frozen=True):
    phase_id: str = PHASE_A1
    phase_label: str = "Phase A1 Preview"
    action_name: str = StrategyLadderControlAction.PHASE_A1_PREVIEW.value
    workflow_run_id: str = ""
    dry_run: bool = True
    ml_mode: str = "ML_MODE_OFF"
    training_timeframe: str = "1m"
    backtest_timeframes: tuple[str, ...] = ("1m",)
    feature_names: str = "close_return,high_low_range,volume"
    selected_features: tuple[str, ...] = ()
    feature_picker_enabled: bool = False
    expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"
    frozen_ml_artifact_path: str = ""
    frozen_ml_artifact_hash: str = ""
    rolling_ml_window_plan_path: str = ""
    ml_artifact_freshness_days: int = 30
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    engine_native_sample_size: int = 10
    b1_5_policy_mode: str = "conservative_hard_only"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    allow_broad_run: bool = False
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    silver_storage_mode: str = "jsonl_debug"
    debug_storage_override: bool = False
    orderbook_root: str = ""
    trades_root: str = ""
    klines_root: str = ""
    raw_roots: tuple[str, ...] = ()
    historical_metadata_root: str = ""
    raw_source_manifest_path: str = ""
    pair_subset: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    output_root_selected: str = ""


class CockpitPatch6State(BaseModel, frozen=True):
    state_name: str = ""
    state_id: str = ""
    request_hash: str = ""
    preview_id: str = ""
    job_id: str = ""
    run_id: str = ""
    created_at: str = ""
    phase_id: str = PHASE_A1
    phase_label: str = "Phase A1 Preview"
    action_name: str = StrategyLadderControlAction.PHASE_A1_PREVIEW.value
    workflow_run_id: str = ""
    pair_subset: tuple[str, ...] = ()
    detected_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    orderbook_root: str = ""
    trades_root: str = ""
    klines_root: str = ""
    historical_metadata_root: str = ""
    output_root_selected: str = ""
    output_root_effective: str = ""
    dry_run: bool = True
    ml_mode: str = "ML_MODE_OFF"
    training_timeframe: str = "1m"
    backtest_timeframes: tuple[str, ...] = ("1m",)
    feature_names: str = "close_return,high_low_range,volume"
    selected_features: tuple[str, ...] = ()
    feature_picker_enabled: bool = False
    expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"
    frozen_ml_artifact_path: str = ""
    frozen_ml_artifact_hash: str = ""
    rolling_ml_window_plan_path: str = ""
    ml_artifact_freshness_days: int = 30
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    engine_native_sample_size: int = 10
    b1_5_policy_mode: str = "conservative_hard_only"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    allow_broad_run: bool = False
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    silver_storage_mode: str = "jsonl_debug"
    status: str = ""
    mismatch_fields: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


class BacktestPreviewManifest(BaseModel, frozen=True):
    preview_id: str
    request_hash: str
    workflow_request_hash: str = ""
    workflow_run_id: str = ""
    created_at: str
    phase_id: str
    phase_label: str
    action_name: str
    normalized_request: Patch6NormalizedRequest
    detected_pairs: tuple[str, ...] = ()
    requested_pairs: tuple[str, ...] = ()
    active_pairs_after_pruning: tuple[str, ...] = ()
    matched_files_total: int = 0
    matched_files_by_type: dict[str, int] = Field(default_factory=dict)
    common_intersection_status: str = "NO_COMMON_DATA_INTERSECTION"
    common_date_range: dict[str, Any] = Field(default_factory=dict)
    historical_metadata_root: str = ""
    metadata_status: str = "METADATA_SCHEMA_NOT_PROVEN"
    output_root_selected: str = ""
    output_root_effective: str = ""
    inspection_status: str = "PREVIEW_NOT_PROVEN"
    preview_launchable: bool = False
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    command_preview: str = ""
    preview_payload: dict[str, Any] = Field(default_factory=dict)


class BacktestMlChainState(BaseModel, frozen=True):
    """Persisted auto handoff->replay chain state for /backtest ML feature launches."""

    status: str = "CHAIN_NOT_REQUESTED"
    created_at: str = ""
    updated_at: str = ""
    action_name: str = ""
    phase_id: str = PHASE_B1
    workflow_run_id: str = ""
    preview_id: str = ""
    request_hash: str = ""
    selected_features: tuple[str, ...] = ()
    training_timeframe: str = "1m"
    backtest_timeframes: tuple[str, ...] = ("1m",)
    feature_selection_source: str = "NONE"
    handoff_job_id: str = ""
    handoff_output_root: str = ""
    replay_job_id: str = ""
    replay_output_root: str = ""
    blockers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    frozen_form: BacktestFormState = Field(default_factory=BacktestFormState)


class CockpitStateConsistency(BaseModel, frozen=True):
    current_form_request_hash: str = ""
    current_form_workflow_run_id: str = ""
    preview_request_hash: str = ""
    preview_workflow_run_id: str = ""
    launch_request_hash: str = ""
    launch_workflow_run_id: str = ""
    latest_summary_request_hash: str = ""
    latest_summary_workflow_run_id: str = ""
    consistency_status: str = "DASHBOARD_STATE_CONSISTENT"
    current_launch_job_id: str = ""
    displayed_summary_run_id: str = ""
    displayed_summary_workflow_run_id: str = ""
    summary_freshness_status: str = "SUMMARY_FRESHNESS_NOT_PROVEN"
    summary_matches_current_request: bool = False
    current_form_changed_since_launch: bool = False
    current_form_changed_since_summary: bool = False
    launch_matches_displayed_summary_workflow: bool = False
    operator_context_status: str = "CONTEXT_ALIGNMENT_NOT_PROVEN"
    operator_context_message: str = ""
    mismatch_fields: tuple[str, ...] = ()


def phase_id_for_action(action_name: str) -> str:
    return PHASE_ID_BY_ACTION.get(
        action_name or "",
        PHASE_A1,
    )


def phase_label_for_action(action_name: str) -> str:
    return PHASE_LABEL_BY_ID[phase_id_for_action(action_name)]


def action_name_for_phase(phase_id: str, fallback: str = "") -> str:
    if phase_id in ACTION_BY_PHASE_ID:
        return ACTION_BY_PHASE_ID[phase_id]
    if fallback:
        return fallback
    return StrategyLadderControlAction.PHASE_A1_PREVIEW.value


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


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


def canonical_patch6_raw_roots(state: BacktestFormState) -> tuple[str, ...]:
    explicit = tuple(
        value.strip()
        for value in (
            state.orderbook_path,
            state.trades_path,
            state.klines_path,
        )
        if value and value.strip()
    )
    if explicit:
        return tuple(dict.fromkeys(explicit))
    return tuple(dict.fromkeys(item.strip() for item in state.raw_roots if item.strip()))


def build_patch6_normalized_request(
    state: BacktestFormState,
    *,
    detected_pairs: tuple[str, ...] = (),
    active_pairs_after_pruning: tuple[str, ...] = (),
) -> Patch6NormalizedRequest:
    action_name = action_name_for_phase(
        state.workflow_phase or state.phase_id,
        fallback=(state.action_name or StrategyLadderControlAction.PHASE_A1_PREVIEW.value),
    )
    phase_id = phase_id_for_action(action_name)
    pair_subset = tuple(item.strip().upper() for item in state.pairs if item.strip())
    if not pair_subset and len(active_pairs_after_pruning) == 1:
        pair_subset = active_pairs_after_pruning
    elif not pair_subset and len(detected_pairs) == 1:
        pair_subset = detected_pairs
    roots = canonical_patch6_raw_roots(state)
    orderbook_root = state.orderbook_path.strip()
    trades_root = state.trades_path.strip()
    klines_root = state.klines_path.strip()
    allow_broad_run = str(state.allow_broad_run or "").strip().lower() in {"1", "true", "yes", "on"}
    explicit_small_scope = str(state.small_scope_enabled or "").strip().lower() in {"1", "true", "yes", "on"}
    explicit_full_scan = str(state.full_scan_enabled or "").strip().lower() in {"1", "true", "yes", "on"}
    debug_storage_override = str(state.debug_storage_override or "").strip().lower() in {"1", "true", "yes", "on"}
    feature_picker_enabled = str(state.feature_picker_enabled or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    requested_policy_mode = str(state.b1_5_policy_mode or "").strip().lower()
    diagnostic_full_replay = str(state.diagnostic_full_replay or "").strip().lower() in {"1", "true", "yes", "on"}
    preselected_only = (
        str(state.preselected_only or "").strip().lower() not in {"0", "false", "no", "off"}
    )
    if requested_policy_mode not in {
        "conservative_hard_only",
        "strict_fail_closed",
        "diagnostic_full_replay",
    }:
        requested_policy_mode = (
            "diagnostic_full_replay"
            if diagnostic_full_replay
            else "conservative_hard_only"
        )
    if requested_policy_mode == "diagnostic_full_replay":
        diagnostic_full_replay = True
        preselected_only = False
    else:
        diagnostic_full_replay = False
        preselected_only = True
    candidate_discovery_mode = (state.candidate_discovery_mode or "").strip() or (
        "BROAD_DIAGNOSTIC" if allow_broad_run else "SAMPLE_CAPPED_DEBUG"
    )
    bml_candidate_sampler_mode = (
        state.bml_candidate_sampler_mode or "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    ).strip() or "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
    derived_small_scope = (
        explicit_small_scope
        or candidate_discovery_mode == "SAMPLE_CAPPED_DEBUG"
    )
    if allow_broad_run and not explicit_small_scope:
        derived_small_scope = False
    derived_full_scan = explicit_full_scan or candidate_discovery_mode in {
        "BROAD_DIAGNOSTIC",
        "FULL_DISCOVERY",
        "TEMPORAL_STRATIFIED",
        "TEMPORAL_STRATIFIED_SAMPLE_BUDGET",
    }
    if allow_broad_run and not str(state.full_scan_enabled or "").strip():
        derived_full_scan = True
    return Patch6NormalizedRequest(
        phase_id=phase_id,
        phase_label=PHASE_LABEL_BY_ID[phase_id],
        action_name=action_name,
        workflow_run_id=(state.workflow_run_id or "").strip(),
        dry_run=phase_id == PHASE_A1,
        ml_mode=(state.ml_mode or "ML_MODE_OFF").strip() or "ML_MODE_OFF",
        training_timeframe=(state.training_timeframe or "1m").strip() or "1m",
        backtest_timeframes=normalize_backtest_timeframes(state.backtest_timeframes),
        feature_names=(state.feature_names or "close_return,high_low_range,volume").strip()
        or "close_return,high_low_range,volume",
        selected_features=tuple(
            item.strip() for item in state.selected_features if item and item.strip()
        ),
        feature_picker_enabled=feature_picker_enabled,
        expected_edge_artifact_mode=(
            (state.expected_edge_artifact_mode or "MONO_PAIR_LEGACY").strip()
            or "MONO_PAIR_LEGACY"
        ),
        frozen_ml_artifact_path=(state.frozen_ml_artifact_path or "").strip(),
        frozen_ml_artifact_hash=(state.frozen_ml_artifact_hash or "").strip(),
        rolling_ml_window_plan_path=(state.rolling_ml_window_plan_path or "").strip(),
        ml_artifact_freshness_days=max(int(state.ml_artifact_freshness_days or 30), 1),
        candidate_discovery_mode=candidate_discovery_mode,
        bml_candidate_sampler_mode=bml_candidate_sampler_mode,
        engine_native_sample_size=max(int(state.engine_native_sample_size or 10), 0),
        b1_5_policy_mode=requested_policy_mode,
        preselected_only=preselected_only,
        diagnostic_full_replay=diagnostic_full_replay,
        allow_broad_run=allow_broad_run,
        small_scope_enabled=derived_small_scope,
        full_scan_enabled=derived_full_scan,
        no_full_scan_enabled=not derived_full_scan,
        silver_storage_mode=(state.silver_storage_mode or "jsonl_debug").strip() or "jsonl_debug",
        debug_storage_override=debug_storage_override,
        orderbook_root=orderbook_root,
        trades_root=trades_root,
        klines_root=klines_root,
        raw_roots=roots,
        historical_metadata_root=(state.metadata_path or "").strip(),
        raw_source_manifest_path=(state.raw_source_manifest_path or "").strip(),
        pair_subset=pair_subset,
        start=_normalize_boundary_text(state.start),
        end=_normalize_boundary_text(state.end),
        output_root_selected=(state.output_root or "").strip(),
    )


def request_hash_for_normalized_request(request: Patch6NormalizedRequest) -> str:
    payload = request.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_hash_path(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    normalized = os.path.normpath(value)
    return os.path.normcase(normalized)


def workflow_request_hash_for_normalized_request(request: Patch6NormalizedRequest) -> str:
    payload = {
        "pairs": request.pair_subset,
        "start": request.start,
        "end": request.end,
        "orderbook_root": _canonical_hash_path(request.orderbook_root),
        "trades_root": _canonical_hash_path(request.trades_root),
        "klines_root": _canonical_hash_path(request.klines_root),
        "historical_metadata_root": _canonical_hash_path(request.historical_metadata_root),
        "raw_source_manifest_path": _canonical_hash_path(request.raw_source_manifest_path),
        "output_root_selected": _canonical_hash_path(request.output_root_selected),
        "ml_mode": request.ml_mode,
        "backtest_timeframes": request.backtest_timeframes,
        "expected_edge_artifact_mode": request.expected_edge_artifact_mode,
        "frozen_ml_artifact_path": _canonical_hash_path(request.frozen_ml_artifact_path),
        "frozen_ml_artifact_hash": request.frozen_ml_artifact_hash,
        "rolling_ml_window_plan_path": _canonical_hash_path(
            request.rolling_ml_window_plan_path
        ),
        "ml_artifact_freshness_days": request.ml_artifact_freshness_days,
        "candidate_discovery_mode": request.candidate_discovery_mode,
        "engine_native_sample_size": request.engine_native_sample_size,
        "b1_5_policy_mode": request.b1_5_policy_mode,
        "preselected_only": request.preselected_only,
        "diagnostic_full_replay": request.diagnostic_full_replay,
        "allow_broad_run": request.allow_broad_run,
        "small_scope_enabled": request.small_scope_enabled,
        "full_scan_enabled": request.full_scan_enabled,
        "no_full_scan_enabled": request.no_full_scan_enabled,
        "silver_storage_mode": request.silver_storage_mode,
        "debug_storage_override": request.debug_storage_override,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def workflow_parent_hash_for_normalized_request(request: Patch6NormalizedRequest) -> str:
    payload = {
        "pairs": request.pair_subset,
        "start": request.start,
        "end": request.end,
        "orderbook_root": _canonical_hash_path(request.orderbook_root),
        "trades_root": _canonical_hash_path(request.trades_root),
        "klines_root": _canonical_hash_path(request.klines_root),
        "historical_metadata_root": _canonical_hash_path(request.historical_metadata_root),
        "raw_source_manifest_path": _canonical_hash_path(request.raw_source_manifest_path),
        "output_root_selected": _canonical_hash_path(request.output_root_selected),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonicalize_workflow_identity(
    request: Patch6NormalizedRequest,
    *,
    force_new_workflow: bool = False,
) -> tuple[Patch6NormalizedRequest, str]:
    workflow_request_hash = workflow_request_hash_for_normalized_request(request)
    if force_new_workflow:
        workflow_run_id = (
            f"strategy_ladder_workflow-{workflow_request_hash[:8]}{uuid4().hex[:8]}"
        )
    else:
        workflow_run_id = f"strategy_ladder_workflow-{workflow_request_hash[:16]}"
    if request.workflow_run_id == workflow_run_id:
        return request, workflow_request_hash
    return request.model_copy(update={"workflow_run_id": workflow_run_id}), workflow_request_hash


def build_patch6_state(
    *,
    state_name: str,
    normalized_request: Patch6NormalizedRequest,
    request_hash: str,
    detected_pairs: tuple[str, ...] = (),
    active_pairs_after_pruning: tuple[str, ...] = (),
    status: str,
    preview_id: str = "",
    job_id: str = "",
    run_id: str = "",
    output_root_effective: str = "",
    mismatch_fields: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
) -> CockpitPatch6State:
    return CockpitPatch6State(
        state_name=state_name,
        state_id=f"{state_name}:{request_hash[:12]}",
        request_hash=request_hash,
        preview_id=preview_id,
        job_id=job_id,
        run_id=run_id,
        created_at=_utc_now_iso(),
        phase_id=normalized_request.phase_id,
        phase_label=normalized_request.phase_label,
        action_name=normalized_request.action_name,
        workflow_run_id=normalized_request.workflow_run_id,
        pair_subset=normalized_request.pair_subset,
        detected_pairs=detected_pairs,
        active_pairs_after_pruning=active_pairs_after_pruning,
        start=normalized_request.start,
        end=normalized_request.end,
        orderbook_root=normalized_request.orderbook_root,
        trades_root=normalized_request.trades_root,
        klines_root=normalized_request.klines_root,
        historical_metadata_root=normalized_request.historical_metadata_root,
        output_root_selected=normalized_request.output_root_selected,
        output_root_effective=output_root_effective,
        dry_run=normalized_request.dry_run,
        ml_mode=normalized_request.ml_mode,
        training_timeframe=normalized_request.training_timeframe,
        backtest_timeframes=normalized_request.backtest_timeframes,
        feature_names=normalized_request.feature_names,
        selected_features=normalized_request.selected_features,
        feature_picker_enabled=normalized_request.feature_picker_enabled,
        expected_edge_artifact_mode=normalized_request.expected_edge_artifact_mode,
        frozen_ml_artifact_path=normalized_request.frozen_ml_artifact_path,
        frozen_ml_artifact_hash=normalized_request.frozen_ml_artifact_hash,
        rolling_ml_window_plan_path=normalized_request.rolling_ml_window_plan_path,
        ml_artifact_freshness_days=normalized_request.ml_artifact_freshness_days,
        candidate_discovery_mode=normalized_request.candidate_discovery_mode,
        bml_candidate_sampler_mode=normalized_request.bml_candidate_sampler_mode,
        engine_native_sample_size=normalized_request.engine_native_sample_size,
        b1_5_policy_mode=normalized_request.b1_5_policy_mode,
        preselected_only=normalized_request.preselected_only,
        diagnostic_full_replay=normalized_request.diagnostic_full_replay,
        allow_broad_run=normalized_request.allow_broad_run,
        small_scope_enabled=normalized_request.small_scope_enabled,
        full_scan_enabled=normalized_request.full_scan_enabled,
        no_full_scan_enabled=normalized_request.no_full_scan_enabled,
        silver_storage_mode=normalized_request.silver_storage_mode,
        status=status,
        mismatch_fields=mismatch_fields,
        blockers=blockers,
    )


def previews_root(jobs_root: Path | None) -> Path | None:
    if jobs_root is None:
        return None
    return jobs_root / "previews"


def preview_manifest_path(jobs_root: Path | None, preview_id: str) -> Path | None:
    root = previews_root(jobs_root)
    if root is None or not preview_id:
        return None
    return root / preview_id / _PREVIEW_MANIFEST_FILENAME


def write_preview_manifest(
    jobs_root: Path | None,
    manifest: BacktestPreviewManifest,
) -> Path | None:
    path = preview_manifest_path(jobs_root, manifest.preview_id)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, manifest.model_dump(mode="json"), indent=2)
    return path


def read_preview_manifest(
    jobs_root: Path | None,
    preview_id: str,
) -> BacktestPreviewManifest | None:
    path = preview_manifest_path(jobs_root, preview_id)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    try:
        return BacktestPreviewManifest.model_validate(payload)
    except ValueError:
        return None


def _state_path(jobs_root: Path | None, filename: str) -> Path | None:
    if jobs_root is None:
        return None
    return jobs_root / filename


def write_patch6_state(
    jobs_root: Path | None,
    *,
    filename: str,
    state: CockpitPatch6State,
) -> None:
    path = _state_path(jobs_root, filename)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, state.model_dump(mode="json"), indent=2)


def read_patch6_state(
    jobs_root: Path | None,
    *,
    filename: str,
) -> CockpitPatch6State | None:
    path = _state_path(jobs_root, filename)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    try:
        return CockpitPatch6State.model_validate(payload)
    except ValueError:
        return None


def write_current_form_state(jobs_root: Path | None, state: CockpitPatch6State) -> None:
    write_patch6_state(jobs_root, filename=_CURRENT_FORM_STATE_FILENAME, state=state)


def read_current_form_state(jobs_root: Path | None) -> CockpitPatch6State | None:
    return read_patch6_state(jobs_root, filename=_CURRENT_FORM_STATE_FILENAME)


def write_source_preview_state(jobs_root: Path | None, state: CockpitPatch6State) -> None:
    write_patch6_state(jobs_root, filename=_SOURCE_PREVIEW_STATE_FILENAME, state=state)


def read_source_preview_state(jobs_root: Path | None) -> CockpitPatch6State | None:
    return read_patch6_state(jobs_root, filename=_SOURCE_PREVIEW_STATE_FILENAME)


def write_launch_request_state(jobs_root: Path | None, state: CockpitPatch6State) -> None:
    write_patch6_state(jobs_root, filename=_LAUNCH_REQUEST_STATE_FILENAME, state=state)


def read_launch_request_state(jobs_root: Path | None) -> CockpitPatch6State | None:
    return read_patch6_state(jobs_root, filename=_LAUNCH_REQUEST_STATE_FILENAME)


def write_latest_job_state(jobs_root: Path | None, state: CockpitPatch6State) -> None:
    write_patch6_state(jobs_root, filename=_LATEST_JOB_STATE_FILENAME, state=state)


def read_latest_job_state(jobs_root: Path | None) -> CockpitPatch6State | None:
    return read_patch6_state(jobs_root, filename=_LATEST_JOB_STATE_FILENAME)


def write_latest_canonical_summary_state(
    jobs_root: Path | None,
    state: CockpitPatch6State,
) -> None:
    write_patch6_state(
        jobs_root,
        filename=_LATEST_CANONICAL_SUMMARY_STATE_FILENAME,
        state=state,
    )


def read_latest_canonical_summary_state(
    jobs_root: Path | None,
) -> CockpitPatch6State | None:
    return read_patch6_state(
        jobs_root,
        filename=_LATEST_CANONICAL_SUMMARY_STATE_FILENAME,
    )


def write_backtest_ml_chain_state(
    jobs_root: Path | None,
    state: BacktestMlChainState,
) -> None:
    path = _state_path(jobs_root, _BACKTEST_ML_CHAIN_STATE_FILENAME)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, state.model_dump(mode="json"), indent=2)


def read_backtest_ml_chain_state(
    jobs_root: Path | None,
) -> BacktestMlChainState | None:
    path = _state_path(jobs_root, _BACKTEST_ML_CHAIN_STATE_FILENAME)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    try:
        return BacktestMlChainState.model_validate(payload)
    except ValueError:
        return None


def build_state_consistency(
    *,
    current_form_state: CockpitPatch6State | None,
    source_preview_state: CockpitPatch6State | None,
    launch_request_state: CockpitPatch6State | None,
    latest_canonical_summary_state: CockpitPatch6State | None,
) -> CockpitStateConsistency:
    mismatch_fields: list[str] = []
    current_hash = current_form_state.request_hash if current_form_state is not None else ""
    current_workflow = current_form_state.workflow_run_id if current_form_state is not None else ""
    preview_hash = source_preview_state.request_hash if source_preview_state is not None else ""
    preview_workflow = source_preview_state.workflow_run_id if source_preview_state is not None else ""
    launch_hash = launch_request_state.request_hash if launch_request_state is not None else ""
    launch_workflow = launch_request_state.workflow_run_id if launch_request_state is not None else ""
    latest_summary_hash = (
        latest_canonical_summary_state.request_hash
        if latest_canonical_summary_state is not None
        else ""
    )
    latest_summary_workflow = (
        latest_canonical_summary_state.workflow_run_id
        if latest_canonical_summary_state is not None
        else ""
    )
    status = "DASHBOARD_STATE_CONSISTENT"
    if current_hash and preview_hash and current_hash != preview_hash:
        status = "DASHBOARD_STATE_MISMATCH"
        mismatch_fields.append("current_form_vs_preview")
    if (
        launch_request_state is not None
        and launch_request_state.status == "PREVIEW_LAUNCH_MISMATCH"
    ):
        status = "PREVIEW_LAUNCH_MISMATCH"
        mismatch_fields.extend(launch_request_state.mismatch_fields)
    elif launch_hash and preview_hash and launch_hash != preview_hash:
        status = "PREVIEW_LAUNCH_MISMATCH"
        mismatch_fields.append("launch_vs_preview")
    elif latest_summary_hash and (
        (preview_hash and latest_summary_hash != preview_hash)
        or (not preview_hash and current_hash and latest_summary_hash != current_hash)
    ):
        status = "LATEST_SUMMARY_NOT_CURRENT_REQUEST"
        mismatch_fields.append(
            "latest_summary_vs_preview" if preview_hash else "latest_summary_vs_current_form"
        )
    summary_freshness_status = "SUMMARY_RESOLVER_CURRENT"
    summary_matches_current_request = False
    if latest_summary_hash and (latest_summary_hash == preview_hash or latest_summary_hash == current_hash):
        summary_matches_current_request = True
    if launch_workflow and latest_summary_workflow and launch_workflow != latest_summary_workflow:
        summary_freshness_status = "SUMMARY_RESOLVER_STALE"
        if "latest_summary_workflow_vs_launch" not in mismatch_fields:
            mismatch_fields.append("latest_summary_workflow_vs_launch")
        if status == "DASHBOARD_STATE_CONSISTENT":
            status = "LATEST_SUMMARY_NOT_CURRENT_REQUEST"
    elif latest_summary_workflow:
        summary_freshness_status = "SUMMARY_RESOLVER_CURRENT"
    current_form_changed_since_launch = bool(
        current_workflow and launch_workflow and current_workflow != launch_workflow
    )
    current_form_changed_since_summary = bool(
        current_workflow
        and latest_summary_workflow
        and current_workflow != latest_summary_workflow
    )
    launch_matches_displayed_summary_workflow = bool(
        launch_workflow
        and latest_summary_workflow
        and launch_workflow == latest_summary_workflow
    )
    if current_form_changed_since_launch:
        mismatch_fields.append("current_form_workflow_vs_launch")
    if current_form_changed_since_summary:
        mismatch_fields.append("current_form_workflow_vs_summary")

    operator_context_status = "CONTEXT_ALIGNMENT_CONSISTENT"
    operator_context_message = ""
    if (
        current_form_changed_since_launch
        and current_form_changed_since_summary
        and launch_matches_displayed_summary_workflow
    ):
        operator_context_status = "CURRENT_FORM_MOVED_AFTER_LAUNCH"
        operator_context_message = (
            "Current form now targets a different workflow than the latest launch job. "
            "The displayed summary still belongs to the latest launch workflow."
        )
    elif current_form_changed_since_launch:
        operator_context_status = "CURRENT_FORM_MOVED_AFTER_LAUNCH"
        operator_context_message = (
            "Current form now targets a different workflow than the latest launch job."
        )
    elif current_form_changed_since_summary:
        operator_context_status = "CURRENT_FORM_MOVED_AFTER_SUMMARY"
        operator_context_message = (
            "Current form no longer matches the workflow that owns the displayed summary."
        )
    elif summary_freshness_status == "SUMMARY_RESOLVER_STALE":
        operator_context_status = "DISPLAYED_SUMMARY_STALE_VS_LAUNCH"
        operator_context_message = (
            "Displayed summary belongs to an older workflow than the latest launch job."
        )
    elif current_hash and preview_hash and current_hash != preview_hash:
        operator_context_status = "CURRENT_FORM_MOVED_AFTER_PREVIEW"
        operator_context_message = (
            "Current form no longer matches the last preview state."
        )
    return CockpitStateConsistency(
        current_form_request_hash=current_hash,
        current_form_workflow_run_id=current_workflow,
        preview_request_hash=preview_hash,
        preview_workflow_run_id=preview_workflow,
        launch_request_hash=launch_hash,
        launch_workflow_run_id=launch_workflow,
        latest_summary_request_hash=latest_summary_hash,
        latest_summary_workflow_run_id=latest_summary_workflow,
        consistency_status=status,
        current_launch_job_id=(launch_request_state.job_id if launch_request_state is not None else ""),
        displayed_summary_run_id=(latest_canonical_summary_state.run_id if latest_canonical_summary_state is not None else ""),
        displayed_summary_workflow_run_id=latest_summary_workflow,
        summary_freshness_status=summary_freshness_status,
        summary_matches_current_request=summary_matches_current_request,
        current_form_changed_since_launch=current_form_changed_since_launch,
        current_form_changed_since_summary=current_form_changed_since_summary,
        launch_matches_displayed_summary_workflow=launch_matches_displayed_summary_workflow,
        operator_context_status=operator_context_status,
        operator_context_message=operator_context_message,
        mismatch_fields=tuple(dict.fromkeys(mismatch_fields)),
    )


__all__ = [
    "ACTION_BY_PHASE_ID",
    "BacktestMlChainState",
    "BacktestPreviewManifest",
    "CockpitPatch6State",
    "CockpitStateConsistency",
    "PHASE_ID_BY_ACTION",
    "PHASE_LABEL_BY_ID",
    "Patch6NormalizedRequest",
    "SUPPORTED_BACKTEST_TIMEFRAMES",
    "action_name_for_phase",
    "build_patch6_normalized_request",
    "build_patch6_state",
    "build_state_consistency",
    "canonicalize_workflow_identity",
    "canonical_patch6_raw_roots",
    "phase_id_for_action",
    "phase_label_for_action",
    "normalize_backtest_timeframes",
    "preview_manifest_path",
    "read_current_form_state",
    "read_backtest_ml_chain_state",
    "read_launch_request_state",
    "read_latest_canonical_summary_state",
    "read_latest_job_state",
    "read_preview_manifest",
    "read_source_preview_state",
    "request_hash_for_normalized_request",
    "workflow_parent_hash_for_normalized_request",
    "workflow_request_hash_for_normalized_request",
    "write_current_form_state",
    "write_backtest_ml_chain_state",
    "write_launch_request_state",
    "write_latest_canonical_summary_state",
    "write_latest_job_state",
    "write_preview_manifest",
    "write_source_preview_state",
]
