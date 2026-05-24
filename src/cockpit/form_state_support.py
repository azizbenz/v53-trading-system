"""Persistence helpers for the cockpit backtest form state across page renders."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.expected_edge_feature_promotion_registry import (
    FeaturePromotionEntry,
)


_FORM_STATE_FILENAME = "_last_form_state.json"
_LAB_ML_HANDOFF_FORM_STATE_FILENAME = "_last_lab_ml_handoff_form_state.json"


class BacktestFormState(BaseModel, frozen=True):
    """Last-submitted backtest form values for repopulation across redirects."""

    job_kind: str = ""
    action_name: str = ""
    phase_id: str = ""
    workflow_phase: str = "PHASE_A1"
    workflow_run_id: str = ""
    export_dir: str = ""
    baseline_export_dir: str = ""
    raw_source_manifest_path: str = ""
    raw_roots: tuple[str, ...] = ()
    pairs: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    ml_mode: str = "ML_MODE_OFF"
    training_timeframe: str = "1m"
    backtest_timeframes: tuple[str, ...] = ("1m",)
    feature_names: str = "close_return,high_low_range,volume"
    selected_features: tuple[str, ...] = ()
    feature_picker_enabled: str = ""
    # Patch P3 (2026-05-22) — explicit mono|multi mode selector for the C1-aware
    # provider. Default keeps backward-compat with the frozen mono bundle path.
    expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"
    ml_handoff_run_root: str = ""
    frozen_ml_artifact_path: str = ""
    frozen_ml_artifact_hash: str = ""
    rolling_ml_window_plan_path: str = ""
    ml_artifact_freshness_days: int = 30
    allow_broad_run: str = ""
    confirm_broad_run: str = ""
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    engine_native_sample_size: int = 10
    b1_5_policy_mode: str = "conservative_hard_only"
    preselected_only: str = "true"
    diagnostic_full_replay: str = ""
    small_scope_enabled: str = ""
    full_scan_enabled: str = ""
    silver_storage_mode: str = "jsonl_debug"
    debug_storage_override: str = ""
    signed_by: str = "cockpit_operator"
    last_blocker: str = ""
    # Patch 6 dashboard redesign — explicit per-data-type input fields.
    orderbook_path: str = ""
    klines_path: str = ""
    trades_path: str = ""
    metadata_path: str = ""
    # Patch 6 output-root selector. Empty string preserves the default
    # ``<jobs_root>/<job_id>/output`` path. Operators can override per run.
    output_root: str = ""

    @property
    def raw_roots_csv(self) -> str:
        return ",".join(self.raw_roots)

    @property
    def pairs_csv(self) -> str:
        return ",".join(self.pairs)

    @property
    def backtest_timeframes_csv(self) -> str:
        return ",".join(self.backtest_timeframes or ("1m",))


class LabMlHandoffFormState(BaseModel, frozen=True):
    """Last-submitted IA Lab ML handoff form values for repopulation."""

    kline_root: str = ""
    b2_run_root: str = ""
    orderbook_root: str = ""
    trades_root: str = ""
    metadata_root: str = ""
    handoff_export_dir: str = ""
    pair: str = "BTCUSDT"
    # Patch P2 (2026-05-22) — multi-select tuple. Empty → fallback to mono `pair`.
    # Order preserved (admin selection order), dedup applied at construction.
    selected_pairs: tuple[str, ...] = ()
    timeframe: str = "1m"
    train_start: str = ""
    train_end: str = ""
    requested_backtest_start: str = ""
    requested_backtest_days: int = 130
    train_days: int = 180
    validation_days: int = 30
    freshness_days: int = 30
    chunk_days: int = 30
    calibration_version: str = "strategy_ladder_expected_edge.v1"
    feature_names: str = "close_return,high_low_range,volume"
    selected_features: tuple[str, ...] = ()
    discovered_feature_governance: tuple[FeaturePromotionEntry, ...] = ()
    sample_stride_minutes: int = 60
    target_horizon_minutes: int = 1
    training_seed: int = 5307
    max_optuna_trials: int = 0
    min_training_rows: int = 210
    shap_summary_ref: str = ""
    signed_by: str = "cockpit_operator"
    last_intent: str = "launch"


def form_state_path(jobs_root: Path | None) -> Path | None:
    """Return the path to the cockpit form-state sidecar file, or None."""

    if jobs_root is None:
        return None
    return jobs_root / _FORM_STATE_FILENAME


def lab_ml_handoff_form_state_path(jobs_root: Path | None) -> Path | None:
    """Return the path to the IA Lab ML handoff form-state sidecar, or None."""

    if jobs_root is None:
        return None
    return jobs_root / _LAB_ML_HANDOFF_FORM_STATE_FILENAME


def write_backtest_form_state(
    jobs_root: Path | None, state: BacktestFormState
) -> None:
    """Persist the most recent backtest form submission for next render."""

    target = form_state_path(jobs_root)
    if target is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(target, state.model_dump(mode="json"), indent=2)


def read_backtest_form_state(jobs_root: Path | None) -> BacktestFormState:
    """Load the persisted backtest form state, or return defaults."""

    target = form_state_path(jobs_root)
    if target is None or not target.is_file():
        return BacktestFormState()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return BacktestFormState()
    if not isinstance(payload, dict):
        return BacktestFormState()
    try:
        return BacktestFormState.model_validate(payload)
    except ValueError:
        return BacktestFormState()


def write_lab_ml_handoff_form_state(
    jobs_root: Path | None,
    state: LabMlHandoffFormState,
) -> None:
    """Persist the most recent IA Lab ML handoff form submission."""

    target = lab_ml_handoff_form_state_path(jobs_root)
    if target is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(target, state.model_dump(mode="json"), indent=2)


def read_lab_ml_handoff_form_state(jobs_root: Path | None) -> LabMlHandoffFormState:
    """Load the persisted IA Lab ML handoff form state, or return defaults."""

    target = lab_ml_handoff_form_state_path(jobs_root)
    if target is None or not target.is_file():
        return LabMlHandoffFormState()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return LabMlHandoffFormState()
    if not isinstance(payload, dict):
        return LabMlHandoffFormState()
    try:
        return LabMlHandoffFormState.model_validate(payload)
    except ValueError:
        return LabMlHandoffFormState()


__all__ = [
    "BacktestFormState",
    "LabMlHandoffFormState",
    "form_state_path",
    "lab_ml_handoff_form_state_path",
    "read_backtest_form_state",
    "read_lab_ml_handoff_form_state",
    "write_backtest_form_state",
    "write_lab_ml_handoff_form_state",
]
