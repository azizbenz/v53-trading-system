"""FastAPI app factory for the V5.3 cockpit operator shell."""

from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cockpit.action_support import (
    CockpitBacktestJobKind,
    OUTPUT_ROOT_EXISTS_NON_EMPTY,
    OUTPUT_ROOT_INSIDE_RAW_ROOT,
    OUTPUT_ROOT_INVALID_PATH,
    OUTPUT_ROOT_NOT_WRITABLE,
    PAIR_ARG_INVALID_PATH,
    PAIR_UNIVERSE_AMBIGUOUS,
    RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE,
    StrategyLadderControlAction,
    enqueue_artifact_command,
    enqueue_pair_command,
    load_backtest_job_records,
    is_path_like_pair_token,
    is_valid_raw_source_manifest_path,
    launch_backtest_job,
    request_job_cancel,
    resolve_output_root,
    stage_artifact_upload,
)
from cockpit.backtest_preflight import (
    build_patch6_preflight_preview,
    infer_pair_symbol_from_path,
    infer_pair_universe_from_paths,
    resolve_phase_b1_replay_input_candidates_path,
)
from cockpit.backtest_state_support import (
    BacktestMlChainState,
    BacktestPreviewManifest,
    action_name_for_phase,
    build_patch6_state,
    canonical_patch6_raw_roots,
    normalize_backtest_timeframes,
    phase_id_for_action,
    read_launch_request_state,
    read_backtest_ml_chain_state,
    read_preview_manifest,
    write_backtest_ml_chain_state,
    write_current_form_state,
    write_launch_request_state,
    write_preview_manifest,
    write_source_preview_state,
)
from cockpit.form_state_support import (
    BacktestFormState,
    LabMlHandoffFormState,
    read_lab_ml_handoff_form_state,
    read_backtest_form_state,
    write_lab_ml_handoff_form_state,
    write_backtest_form_state,
)
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A1,
    PHASE_A2,
    PHASE_B1,
    PHASE_B_ML,
    PHASE_B2,
    ensure_workflow_manifest,
    upsert_workflow_phase,
    workflow_manifest_path,
    workflow_phase_dirname,
)
from cockpit.runtime_support import read_runtime_surfaces
from cockpit.strategy_ladder_ml_handoff_support import (
    DEFAULT_ROLLING_CHUNK_DAYS,
    DEFAULT_ROLLING_FRESHNESS_DAYS,
    DEFAULT_ROLLING_TRAIN_DAYS,
    DEFAULT_ROLLING_VALIDATION_DAYS,
    discover_backtest_feature_governance,
    discover_lab_feature_governance,
    read_strategy_ladder_ml_handoff_dashboard_summary,
    resolve_backtest_feature_picker_defaults,
    resolve_backtest_selected_feature_names,
    selected_demoted_lab_features,
)
from cockpit.state import (
    CockpitPaths,
    build_dashboard_view_model,
    read_pair_selector,
    read_service_status,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
    normalize_supported_expected_edge_feature_names,
)
from interface_contracts import (
    DashboardArtifactKind,
    DashboardGovernedCommandKind,
)
from interface_contracts.atomic_io import atomic_write_json
from monitoring.contracts import ShadowVpsServiceLogQuery


_logger = logging.getLogger(__name__)
_LEGACY_EXPECTED_EDGE_FEATURE_NAME_SET = frozenset(
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
)
_DEFAULT_EXPECTED_EDGE_FEATURE_NAMES_CSV = ",".join(
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
)

PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates"
STATIC_DIR = PACKAGE_ROOT / "static"

DEFAULT_WELCOME = "Welcome Benz Family · AI Bot Trading"
DEFAULT_GRAFANA_URL = "http://127.0.0.1:3000"
DEFAULT_PROMETHEUS_URL = "http://127.0.0.1:9090"


def _pick_native_directory(initial_path_text: str) -> dict[str, str]:
    initial_text = (initial_path_text or "").strip()
    initial_path = Path(initial_text).expanduser() if initial_text else None
    if initial_path is not None and initial_path.is_file():
        initial_path = initial_path.parent
    if initial_path is not None and not initial_path.exists():
        initial_path = initial_path.parent if initial_path.parent != initial_path else None
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        return {
            "status": "FOLDER_PICKER_UNAVAILABLE",
            "reason": f"tkinter_unavailable:{exc.__class__.__name__}",
            "selected_path": "",
        }

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        root.update()
        selected = filedialog.askdirectory(
            initialdir=str(initial_path) if initial_path is not None else "",
            mustexist=True,
        )
        if not selected:
            return {
                "status": "FOLDER_PICKER_CANCELLED",
                "reason": "",
                "selected_path": "",
            }
        resolved = Path(selected).expanduser().resolve()
        return {
            "status": "FOLDER_PICKER_SELECTED",
            "reason": "",
            "selected_path": str(resolved),
        }
    except Exception as exc:
        return {
            "status": "FOLDER_PICKER_UNAVAILABLE",
            "reason": f"folder_picker_failed:{exc.__class__.__name__}",
            "selected_path": "",
        }
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def _checkbox_text(enabled: bool) -> str:
    return "true" if enabled else ""


def _adopt_launch_state_into_form(
    *,
    current_form: BacktestFormState,
    launch_state,
) -> BacktestFormState:
    return current_form.model_copy(
        update={
            "action_name": launch_state.action_name,
            "phase_id": launch_state.phase_id,
            "workflow_phase": launch_state.phase_id or launch_state.action_name,
            "workflow_run_id": launch_state.workflow_run_id,
            "pairs": launch_state.pair_subset,
            "start": launch_state.start,
            "end": launch_state.end,
            "ml_mode": launch_state.ml_mode,
            "backtest_timeframes": launch_state.backtest_timeframes,
            "ml_handoff_run_root": "",
            "allow_broad_run": _checkbox_text(bool(launch_state.allow_broad_run)),
            "candidate_discovery_mode": launch_state.candidate_discovery_mode,
            "bml_candidate_sampler_mode": launch_state.bml_candidate_sampler_mode,
            "engine_native_sample_size": max(
                int(launch_state.engine_native_sample_size or 0),
                0,
            ),
            "preselected_only": _checkbox_text(bool(launch_state.preselected_only)),
            "diagnostic_full_replay": _checkbox_text(
                bool(launch_state.diagnostic_full_replay)
            ),
            "small_scope_enabled": _checkbox_text(
                bool(launch_state.small_scope_enabled)
            ),
            "full_scan_enabled": _checkbox_text(bool(launch_state.full_scan_enabled)),
            "silver_storage_mode": (
                launch_state.silver_storage_mode or current_form.silver_storage_mode
            ),
            "orderbook_path": launch_state.orderbook_root,
            "trades_path": launch_state.trades_root,
            "klines_path": launch_state.klines_root,
            "metadata_path": launch_state.historical_metadata_root,
            "output_root": launch_state.output_root_selected,
        }
    )


def _normalize_feature_picker_selection(
    *,
    selected_features: list[str] | tuple[str, ...] | None = None,
    selected_features_csv: str = "",
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return authoritative, checkbox, and mirror feature tuples for cockpit pickers."""

    normalized_checkbox_features: tuple[str, ...] = ()
    if selected_features:
        ordered_features: list[str] = []
        seen_features: set[str] = set()
        for raw_name in selected_features:
            cleaned = (raw_name or "").strip()
            if not cleaned or cleaned in seen_features:
                continue
            seen_features.add(cleaned)
            ordered_features.append(cleaned)
        if ordered_features:
            normalized_checkbox_features = normalize_supported_expected_edge_feature_names(
                ordered_features
            )

    csv_candidates = tuple(
        part.strip() for part in (selected_features_csv or "").split(",") if part.strip()
    )
    normalized_csv_features = (
        normalize_supported_expected_edge_feature_names(csv_candidates)
        if csv_candidates
        else ()
    )
    authoritative_features = normalized_csv_features or normalized_checkbox_features
    return (
        authoritative_features,
        normalized_checkbox_features,
        normalized_csv_features,
    )


def _normalize_feature_names_csv_selection(raw_feature_names: str) -> tuple[str, ...]:
    feature_tokens = tuple(
        part.strip() for part in (raw_feature_names or "").split(",") if part.strip()
    )
    if not feature_tokens:
        return ()
    try:
        return normalize_supported_expected_edge_feature_names(feature_tokens)
    except ValueError:
        return ()


def _non_legacy_expected_edge_features(
    feature_names: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        name for name in feature_names if name not in _LEGACY_EXPECTED_EDGE_FEATURE_NAME_SET
    )


def _lab_feature_selection_source(
    form_state: LabMlHandoffFormState,
) -> str:
    if form_state.selected_features:
        return "FORM_SELECTED"
    if (form_state.feature_names or "").strip():
        return "FORM_CSV"
    return "NONE"


def _build_lab_ml_handoff_form_state(
    *,
    kline_root: str,
    b2_run_root: str,
    label_store_dataset_path: str = "",
    orderbook_root: str,
    trades_root: str,
    metadata_root: str,
    handoff_export_dir: str,
    pair: str,
    timeframe: str,
    train_start: str,
    train_end: str,
    requested_backtest_start: str,
    requested_backtest_days: int,
    train_days: int,
    validation_days: int,
    freshness_days: int,
    chunk_days: int,
    calibration_version: str,
    feature_names: str,
    sample_stride_minutes: int,
    target_horizon_minutes: int,
    training_seed: int,
    max_optuna_trials: int,
    min_training_rows: int,
    shap_summary_ref: str,
    signed_by: str,
    intent: str,
    selected_pairs: list[str] | tuple[str, ...] | None = None,
    selected_features: list[str] | tuple[str, ...] | None = None,
    feature_picker_enabled: bool | str = False,
    selected_features_csv: str = "",
) -> LabMlHandoffFormState:
    # Patch P2 — normalize multi-select : strip, upper, dedup (preserve order).
    normalized_selected: tuple[str, ...] = ()
    if selected_pairs:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw_name in selected_pairs:
            cleaned = (raw_name or "").strip().upper()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            ordered.append(cleaned)
        normalized_selected = tuple(ordered)
    (
        normalized_selected_features,
        normalized_checkbox_features,
        normalized_csv_features,
    ) = _normalize_feature_picker_selection(
        selected_features=selected_features,
        selected_features_csv=selected_features_csv,
    )
    feature_picker_active = str(feature_picker_enabled).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if feature_picker_active and not normalized_selected_features:
        raise ValueError(">=1 feature requise ; default reset au minimal 3")
    if (
        normalized_checkbox_features
        and normalized_csv_features
        and normalized_checkbox_features != normalized_csv_features
    ):
        _logger.warning(
            "LAB_FEATURE_PICKER_MIRROR_MISMATCH checkbox=%s csv=%s",
            ",".join(normalized_checkbox_features),
            ",".join(normalized_csv_features),
        )
    resolved_feature_names = (
        ",".join(normalized_selected_features)
        if normalized_selected_features
        else ((feature_names or "").strip() or "close_return,high_low_range,volume")
    )
    return LabMlHandoffFormState(
        kline_root=(kline_root or "").strip(),
        b2_run_root=(b2_run_root or "").strip(),
        label_store_dataset_path=(label_store_dataset_path or "").strip(),
        orderbook_root=(orderbook_root or "").strip(),
        trades_root=(trades_root or "").strip(),
        metadata_root=(metadata_root or "").strip(),
        handoff_export_dir=(handoff_export_dir or "").strip(),
        pair=(pair or "BTCUSDT").strip().upper() or "BTCUSDT",
        selected_pairs=normalized_selected,
        timeframe=(timeframe or "1m").strip() or "1m",
        train_start=(train_start or "").strip(),
        train_end=(train_end or "").strip(),
        requested_backtest_start=(requested_backtest_start or "").strip(),
        requested_backtest_days=max(int(requested_backtest_days or 0), 1),
        train_days=max(int(train_days or 0), 1),
        validation_days=max(int(validation_days or 0), 1),
        freshness_days=max(int(freshness_days or 0), 1),
        chunk_days=max(int(chunk_days or 0), 1),
        calibration_version=(
            (calibration_version or "").strip() or "strategy_ladder_expected_edge.v1"
        ),
        feature_names=resolved_feature_names,
        selected_features=normalized_selected_features,
        sample_stride_minutes=max(int(sample_stride_minutes or 0), 1),
        target_horizon_minutes=max(int(target_horizon_minutes or 0), 1),
        training_seed=int(training_seed),
        max_optuna_trials=max(int(max_optuna_trials or 0), 0),
        min_training_rows=max(int(min_training_rows or 0), 10),
        shap_summary_ref=(shap_summary_ref or "").strip(),
        signed_by=(signed_by or "cockpit_operator").strip() or "cockpit_operator",
        last_intent=(intent or "launch").strip() or "launch",
    )


def _sync_lab_handoff_into_backtest_form(
    current_form: BacktestFormState,
    lab_form: LabMlHandoffFormState,
) -> BacktestFormState:
    preview_export_dir = (
        lab_form.handoff_export_dir
        or current_form.export_dir
        or lab_form.kline_root
    )
    preserved_output_root = (current_form.output_root or "").strip()
    lab_export_root = (lab_form.handoff_export_dir or "").strip()
    if preserved_output_root and lab_export_root:
        try:
            preserved_path = Path(preserved_output_root).expanduser().resolve(strict=False)
            lab_export_path = Path(lab_export_root).expanduser().resolve(strict=False)
        except OSError:
            preserved_path = None
            lab_export_path = None
        if preserved_path is not None and lab_export_path is not None and preserved_path == lab_export_path:
            preserved_output_root = ""
    # Patch P2 — propagate multi-select if admin selected ≥1 paires explicitly,
    # otherwise fall back to mono `pair` for backward-compat.
    propagated_pairs: tuple[str, ...]
    if lab_form.selected_pairs:
        propagated_pairs = lab_form.selected_pairs
    elif lab_form.pair:
        propagated_pairs = (lab_form.pair,)
    else:
        propagated_pairs = ()
    return current_form.model_copy(
        update={
            "action_name": StrategyLadderControlAction.PHASE_A1_PREVIEW.value,
            "phase_id": PHASE_A1,
            "workflow_phase": PHASE_A1,
            "export_dir": preview_export_dir,
            "pairs": propagated_pairs,
            "start": lab_form.train_start,
            "end": lab_form.train_end,
            "ml_mode": "ML_MODE_OFF",
            "ml_handoff_run_root": "",
            "orderbook_path": lab_form.orderbook_root,
            "klines_path": lab_form.kline_root,
            "trades_path": lab_form.trades_root,
            "metadata_path": lab_form.metadata_root,
            # Keep IA Lab export roots isolated from backtest workflow roots.
            "output_root": preserved_output_root,
        }
    )


def _build_backtest_form_state(
    *,
    current_form: BacktestFormState | None = None,
    job_kind: str,
    selected_action_name: str,
    resolved_phase_id: str,
    workflow_phase: str,
    workflow_run_id: str,
    export_dir: str,
    baseline_export_dir: str,
    raw_source_manifest_path: str,
    raw_roots: tuple[str, ...],
    pairs: tuple[str, ...],
    start: str,
    end: str,
    ml_mode: str,
    training_timeframe: str,
    backtest_timeframes: str,
    feature_names: str,
    selected_features: list[str] | tuple[str, ...] | None,
    feature_picker_enabled: str,
    expected_edge_artifact_mode: str,
    ml_handoff_run_root: str,
    frozen_ml_artifact_path: str,
    frozen_ml_artifact_hash: str,
    rolling_ml_window_plan_path: str,
    ml_artifact_freshness_days: int,
    allow_broad_run: str,
    confirm_broad_run: str,
    candidate_discovery_mode: str,
    bml_candidate_sampler_mode: str = "TEMPORAL_STRATIFIED_BACKGROUND_GRID",
    engine_native_sample_size: int,
    b1_5_policy_mode: str,
    preselected_only: str,
    diagnostic_full_replay: str,
    small_scope_enabled: str,
    full_scan_enabled: str,
    silver_storage_mode: str,
    debug_storage_override: str,
    signed_by: str,
    orderbook_path: str,
    klines_path: str,
    trades_path: str,
    metadata_path: str,
    output_root: str,
    selected_features_csv: str = "",
) -> BacktestFormState:
    (
        normalized_selected_features,
        normalized_checkbox_features,
        normalized_csv_features,
    ) = _normalize_feature_picker_selection(
        selected_features=selected_features,
        selected_features_csv=selected_features_csv,
    )
    feature_picker_active = str(feature_picker_enabled).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if (
        normalized_checkbox_features
        and normalized_csv_features
        and normalized_checkbox_features != normalized_csv_features
    ):
        _logger.warning(
            "BACKTEST_FEATURE_PICKER_MIRROR_MISMATCH checkbox=%s csv=%s",
            ",".join(normalized_checkbox_features),
            ",".join(normalized_csv_features),
        )
    if normalized_selected_features:
        resolved_feature_names = ",".join(normalized_selected_features)
    elif feature_picker_active:
        fallback_features = _normalize_feature_names_csv_selection(feature_names)
        if (
            fallback_features
            and ",".join(fallback_features) != _DEFAULT_EXPECTED_EDGE_FEATURE_NAMES_CSV
        ):
            normalized_selected_features = fallback_features
            resolved_feature_names = ",".join(fallback_features)
        elif current_form is not None and current_form.selected_features:
            normalized_selected_features = current_form.selected_features
            resolved_feature_names = ",".join(current_form.selected_features)
        else:
            resolved_feature_names = ""
    else:
        resolved_feature_names = (
            (feature_names or "").strip() or "close_return,high_low_range,volume"
        )
    return (current_form or BacktestFormState()).model_copy(
        update={
            "job_kind": job_kind,
            "action_name": selected_action_name,
            "phase_id": resolved_phase_id,
            "workflow_phase": (workflow_phase or resolved_phase_id or PHASE_A1),
            "workflow_run_id": (workflow_run_id or "").strip(),
            "export_dir": export_dir,
            "baseline_export_dir": baseline_export_dir,
            "raw_source_manifest_path": raw_source_manifest_path,
            "raw_roots": raw_roots,
            "pairs": pairs,
            "start": start,
            "end": end,
            "ml_mode": ml_mode,
            "training_timeframe": (training_timeframe or "1m").strip() or "1m",
            "backtest_timeframes": normalize_backtest_timeframes(backtest_timeframes),
            "feature_names": resolved_feature_names,
            "selected_features": normalized_selected_features,
            "feature_picker_enabled": feature_picker_enabled,
            "expected_edge_artifact_mode": (
                expected_edge_artifact_mode or "MONO_PAIR_LEGACY"
            ),
            "ml_handoff_run_root": ml_handoff_run_root,
            "frozen_ml_artifact_path": frozen_ml_artifact_path,
            "frozen_ml_artifact_hash": frozen_ml_artifact_hash,
            "rolling_ml_window_plan_path": rolling_ml_window_plan_path,
            "ml_artifact_freshness_days": max(int(ml_artifact_freshness_days), 1),
            "allow_broad_run": allow_broad_run,
            "confirm_broad_run": confirm_broad_run,
            "candidate_discovery_mode": candidate_discovery_mode,
            "bml_candidate_sampler_mode": (
                bml_candidate_sampler_mode or "TEMPORAL_STRATIFIED_BACKGROUND_GRID"
            ),
            "engine_native_sample_size": max(int(engine_native_sample_size), 0),
            "b1_5_policy_mode": b1_5_policy_mode,
            "preselected_only": preselected_only,
            "diagnostic_full_replay": diagnostic_full_replay,
            "small_scope_enabled": small_scope_enabled,
            "full_scan_enabled": full_scan_enabled,
            "silver_storage_mode": silver_storage_mode,
            "debug_storage_override": debug_storage_override,
            "signed_by": signed_by,
            "orderbook_path": orderbook_path,
            "klines_path": klines_path,
            "trades_path": trades_path,
            "metadata_path": metadata_path,
            "output_root": output_root,
        }
    )


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    cfg: CockpitPaths = app.state.paths
    _logger.info("Cockpit starting · service_dir=%s", cfg.service_dir)
    _logger.info("Cockpit PID file watched at %s", cfg.pid_file)
    _logger.info("Cockpit log tail target %s", cfg.log_file)
    yield
    _logger.info("Cockpit shutting down")


def _format_price(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:,.4f}"
    return f"${value:.6f}"


def _format_change(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _change_class(value: float | None) -> str:
    if value is None:
        return "neutral"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "neutral"


def create_app(
    *,
    paths: CockpitPaths,
    welcome_message: str = DEFAULT_WELCOME,
    grafana_url: str = DEFAULT_GRAFANA_URL,
    prometheus_url: str = DEFAULT_PROMETHEUS_URL,
) -> FastAPI:
    """Build and return the cockpit FastAPI application."""

    app = FastAPI(
        title="V5.3 Cockpit",
        version="0.2.0",
        description="Local operator shell for V5.3 Shadow, VPS, IA Lab, and observability.",
        lifespan=_lifespan,
    )
    app.state.paths = paths
    app.state.welcome_message = welcome_message
    app.state.grafana_url = grafana_url
    app.state.prometheus_url = prometheus_url

    if not TEMPLATE_DIR.is_dir():
        raise RuntimeError(f"Cockpit templates directory missing: {TEMPLATE_DIR}")
    if not STATIC_DIR.is_dir():
        raise RuntimeError(f"Cockpit static directory missing: {STATIC_DIR}")

    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
    templates.env.filters["price"] = _format_price
    templates.env.filters["change"] = _format_change
    templates.env.filters["change_class"] = _change_class
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _build_vm(
        request: Request,
        *,
        current_page: str,
        selected_pair: str | None = None,
        log_query: ShadowVpsServiceLogQuery | None = None,
        pinned_run_id: str = "",
    ):
        if current_page == "backtest":
            _reconcile_backtest_ml_chain()
        notice_message = request.query_params.get("notice", "")
        notice_status = request.query_params.get("notice_status", "info")
        selected_candidate_id = request.query_params.get("candidate_id", "")
        return build_dashboard_view_model(
            paths=app.state.paths,
            welcome_message=app.state.welcome_message,
            grafana_url=app.state.grafana_url,
            prometheus_url=app.state.prometheus_url,
            selected_pair=selected_pair,
            selected_candidate_id=selected_candidate_id,
            current_page=current_page,
            notice_message=notice_message,
            notice_status=notice_status,
            log_query=log_query,
            pinned_run_id=pinned_run_id,
        )

    def _resolve_backtest_runtime_feature_context() -> tuple[tuple[str, ...], tuple[str, ...]]:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return (), ()
        current_form = read_backtest_form_state(jobs_root)
        lab_form = read_lab_ml_handoff_form_state(jobs_root)
        preflight = build_patch6_preflight_preview(
            selected_form=current_form,
            jobs_root=jobs_root,
        )
        artifact_feature_names = tuple(preflight.ml_overlay_intake.feature_names)
        governance_entries = discover_backtest_feature_governance(
            current_form,
            registry_path=jobs_root / "feature_promotion_registry.json",
        )
        authoritative_frozen_artifact = bool(
            current_form.ml_mode == "ML_MODE_OVERLAY_FROZEN"
            and preflight.ml_overlay_intake.ready
            and artifact_feature_names
        )
        active_feature_names = (
            resolve_backtest_selected_feature_names(
                current_form,
                lab_form_state=lab_form,
                artifact_feature_names=artifact_feature_names,
            )
            if authoritative_frozen_artifact
            else resolve_backtest_feature_picker_defaults(
                form_state=current_form,
                lab_form_state=lab_form,
                governance_entries=governance_entries,
                supported_feature_names=SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
                artifact_feature_names=(),
            )
        )
        return active_feature_names, artifact_feature_names

    def _redirect(
        path: str,
        *,
        notice: str,
        notice_status: str = "info",
    ) -> RedirectResponse:
        query = urlencode({"notice": notice, "notice_status": notice_status})
        return RedirectResponse(url=f"{path}?{query}", status_code=303)

    def _list_local_drives() -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:\\")
            if drive.exists():
                rows.append({"path": str(drive), "label": str(drive)})
        return rows

    def _list_directories(path_text: str) -> dict[str, object]:
        target_text = (path_text or "").strip()
        target = Path(target_text).expanduser() if target_text else None
        if target is None or not target.exists() or not target.is_dir():
            return {
                "current_path": "",
                "parent_path": "",
                "directories": [],
                "status": "FOLDER_NOT_FOUND",
            }
        directories: list[dict[str, str]] = []
        try:
            children = sorted(
                (child for child in target.iterdir() if child.is_dir()),
                key=lambda child: child.name.lower(),
            )
        except OSError:
            return {
                "current_path": str(target),
                "parent_path": str(target.parent) if target.parent != target else "",
                "directories": [],
                "status": "FOLDER_READ_FAILED",
            }
        for child in children:
            directories.append({"name": child.name, "path": str(child)})
        parent_path = str(target.parent) if target.parent != target else ""
        return {
            "current_path": str(target),
            "parent_path": parent_path,
            "directories": directories,
            "status": "FOLDER_LIST_READY",
        }

    def _build_preview_manifest(
        *,
        preflight,
    ) -> BacktestPreviewManifest:
        return BacktestPreviewManifest(
            preview_id=preflight.preview_id,
            request_hash=preflight.request_hash,
            workflow_request_hash=preflight.workflow_request_hash,
            workflow_run_id=preflight.workflow_run_id,
            created_at=datetime.now(tz=UTC).isoformat(),
            phase_id=preflight.phase_id,
            phase_label=preflight.phase_label,
            action_name=preflight.action_name,
            normalized_request=preflight.normalized_request,
            detected_pairs=preflight.detected_pairs,
            requested_pairs=preflight.requested_pairs,
            active_pairs_after_pruning=preflight.active_pairs_after_pruning,
            matched_files_total=preflight.files_matched_total,
            matched_files_by_type={
                "orderbook": preflight.orderbook.files_matched,
                "trades": preflight.trades.files_matched,
                "klines": preflight.klines.files_matched,
                "metadata": preflight.metadata.files_matched,
            },
            common_intersection_status=preflight.common_data_intersection_status,
            common_date_range={
                "start": preflight.common_date_start,
                "end": preflight.common_date_end,
                "days_count": preflight.common_days_count,
            },
            historical_metadata_root=preflight.normalized_request.historical_metadata_root,
            metadata_status=preflight.metadata_status,
            output_root_selected=preflight.output_root_selected,
            output_root_effective=preflight.output_root_effective_preview,
            inspection_status=preflight.inspection_status,
            preview_launchable=preflight.preview_launchable,
            blockers=preflight.blockers,
            warnings=preflight.warnings,
            command_preview=preflight.command_preview,
            preview_payload=preflight.model_dump(mode="json"),
        )

    def _sha256_path(path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""

    def _workflow_root_for_request(
        *,
        jobs_root: Path,
        workflow_run_id: str,
        operator_output_root: str,
    ) -> Path:
        if (operator_output_root or "").strip():
            return (
                Path(operator_output_root).expanduser()
                / "runs"
                / workflow_run_id
            )
        return jobs_root / "workflows" / workflow_run_id

    def _workflow_consumed_artifact_refs(
        *,
        workflow_root: Path,
        phase_id: str,
        normalized_request,
    ) -> dict[str, str]:
        phase_a1_root = workflow_root / workflow_phase_dirname(PHASE_A1)
        phase_a2_root = workflow_root / workflow_phase_dirname(PHASE_A2)
        phase_b1_root = workflow_root / workflow_phase_dirname(PHASE_B1)
        if phase_id == PHASE_A1:
            refs: dict[str, str] = {}
            raw_source_manifest_path = (
                normalized_request.raw_source_manifest_path or ""
            ).strip()
            if raw_source_manifest_path:
                refs["raw_source_manifest"] = str(
                    Path(raw_source_manifest_path).expanduser().resolve()
                )
            for key, raw_value in (
                ("orderbook_root", normalized_request.orderbook_root),
                ("trades_root", normalized_request.trades_root),
                ("klines_root", normalized_request.klines_root),
                (
                    "historical_metadata_root",
                    normalized_request.historical_metadata_root,
                ),
            ):
                value = (raw_value or "").strip()
                if value:
                    refs[key] = str(Path(value).expanduser().resolve())
            return refs
        if phase_id == PHASE_A2:
            return {
                "phase_a1_preview_manifest": str(
                    (phase_a1_root / "source_date_preview_manifest.json").resolve()
                ),
                "phase_a1_source_scope_report": str(
                    (phase_a1_root / "source_scope_report.json").resolve()
                ),
            }
        if phase_id == PHASE_B1:
            return {
                "phase_a2_data_factory_manifest": str(
                    (phase_a2_root / "data_factory_manifest.json").resolve()
                ),
                "phase_a2_silver_index": str(
                    (phase_a2_root / "silver_index.json").resolve()
                ),
                "phase_a2_gold_root": str((phase_a2_root / "gold").resolve()),
            }
        if phase_id == PHASE_B2:
            workflow_run_id = workflow_root.name
            return {
                "phase_a2_data_factory_manifest": str(
                    (phase_a2_root / "data_factory_manifest.json").resolve()
                ),
                "phase_a2_silver_index": str(
                    (phase_a2_root / "silver_index.json").resolve()
                ),
                "phase_a2_gold_root": str((phase_a2_root / "gold").resolve()),
                "phase_b1_candidate_events": str(
                    (
                        phase_b1_root
                        / "backtest_strategy_ladder"
                        / workflow_run_id
                        / "fast_candidates"
                        / "candidate_events.jsonl"
                    ).resolve()
                ),
            }
        if phase_id == PHASE_B_ML:
            workflow_run_id = workflow_root.name
            return {
                "phase_a2_data_factory_manifest": str(
                    (phase_a2_root / "data_factory_manifest.json").resolve()
                ),
                "phase_a2_silver_index": str(
                    (phase_a2_root / "silver_index.json").resolve()
                ),
                "phase_a2_gold_root": str((phase_a2_root / "gold").resolve()),
                "phase_b1_candidate_events": str(
                    (
                        phase_b1_root
                        / "backtest_strategy_ladder"
                        / workflow_run_id
                        / "fast_candidates"
                        / "candidate_events.jsonl"
                    ).resolve()
                ),
            }
        return {}

    def _write_phase_a1_preview_artifacts(
        *,
        jobs_root: Path,
        preview_manifest: BacktestPreviewManifest,
        preflight,
    ) -> None:
        workflow_root = _workflow_root_for_request(
            jobs_root=jobs_root,
            workflow_run_id=preflight.workflow_run_id,
            operator_output_root=preflight.output_root_selected,
        )
        phase_output_root = Path(preflight.output_root_effective_preview).resolve()
        phase_output_root.mkdir(parents=True, exist_ok=True)
        preview_manifest_output = phase_output_root / "source_date_preview_manifest.json"
        source_scope_output = phase_output_root / "source_scope_report.json"
        atomic_write_json(
            preview_manifest_output,
            preview_manifest.model_dump(mode="json"),
            indent=2,
        )
        atomic_write_json(
            source_scope_output,
            preflight.model_dump(mode="json"),
            indent=2,
        )
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id=preflight.workflow_run_id,
            request_hash=preflight.request_hash,
            phase_id=PHASE_A1,
            pairs=preflight.requested_pairs or preflight.detected_pairs,
            start=preflight.normalized_request.start,
            end=preflight.normalized_request.end,
            ml_mode=preflight.normalized_request.ml_mode,
            candidate_discovery_mode=preflight.candidate_discovery_mode,
            engine_native_sample_size=preflight.effective_engine_native_sample_size,
            b1_5_policy_mode=preflight.normalized_request.b1_5_policy_mode,
            engine_count=preflight.engine_count,
            allow_broad_run=preflight.normalized_request.allow_broad_run,
            small_scope_enabled=preflight.small_scope_enabled,
            full_scan_enabled=preflight.full_scan_enabled,
            no_full_scan_enabled=preflight.no_full_scan_enabled,
            silver_storage_mode_requested=preflight.silver_storage_mode_requested,
            silver_storage_mode_effective=preflight.silver_storage_mode_effective,
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id=preflight.workflow_run_id,
            phase_id=PHASE_A1,
            phase_run_id=preview_manifest.preview_id,
            phase_output_root=phase_output_root,
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            job_id=preview_manifest.preview_id,
            request_hash=preflight.request_hash,
            phase_status=preflight.inspection_status,
            blocker_codes=preflight.blockers,
            error_code="",
            stderr_ref="",
            consumed_artifact_refs=_workflow_consumed_artifact_refs(
                workflow_root=workflow_root,
                phase_id=PHASE_A1,
                normalized_request=preflight.normalized_request,
            ),
            produced_artifact_refs={
                "phase_a1_preview_manifest": str(preview_manifest_output.resolve()),
                "phase_a1_source_scope_report": str(source_scope_output.resolve()),
            },
            artifact_hashes={
                "phase_a1_preview_manifest": _sha256_path(preview_manifest_output),
                "phase_a1_source_scope_report": _sha256_path(source_scope_output),
            },
            phase_started_at=preview_manifest.created_at,
            phase_completed_at=preview_manifest.created_at,
        )

    def _refresh_requested_phase_a1_workflow_manifest(
        *,
        jobs_root: Path,
        requested_workflow_run_id: str,
        preflight,
        preview_manifest: BacktestPreviewManifest,
    ) -> None:
        requested_id = (requested_workflow_run_id or "").strip()
        if not requested_id or requested_id == preflight.workflow_run_id:
            return
        workflow_root = _workflow_root_for_request(
            jobs_root=jobs_root,
            workflow_run_id=requested_id,
            operator_output_root=preflight.output_root_selected,
        )
        if not workflow_root.exists():
            return
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id=requested_id,
            request_hash=preflight.request_hash,
            phase_id=PHASE_A1,
            pairs=preflight.requested_pairs or preflight.detected_pairs,
            start=preflight.normalized_request.start,
            end=preflight.normalized_request.end,
            ml_mode=preflight.normalized_request.ml_mode,
            candidate_discovery_mode=preflight.candidate_discovery_mode,
            engine_native_sample_size=preflight.effective_engine_native_sample_size,
            b1_5_policy_mode=preflight.normalized_request.b1_5_policy_mode,
            engine_count=preflight.engine_count,
            allow_broad_run=preflight.normalized_request.allow_broad_run,
            small_scope_enabled=preflight.small_scope_enabled,
            full_scan_enabled=preflight.full_scan_enabled,
            no_full_scan_enabled=preflight.no_full_scan_enabled,
            silver_storage_mode_requested=preflight.silver_storage_mode_requested,
            silver_storage_mode_effective=preflight.silver_storage_mode_effective,
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id=requested_id,
            phase_id=PHASE_A1,
            phase_run_id=preview_manifest.preview_id,
            phase_output_root=workflow_root / workflow_phase_dirname(PHASE_A1),
            parent_workflow_ref=str(workflow_manifest_path(workflow_root).resolve()),
            job_id=preview_manifest.preview_id,
            request_hash=preflight.request_hash,
            phase_status=preflight.inspection_status,
            blocker_codes=preflight.blockers,
            error_code="",
            stderr_ref="",
        )

    def _preview_mismatch_fields(
        *,
        manifest: BacktestPreviewManifest | None,
        preflight,
        submitted_preview_id: str,
        submitted_request_hash: str,
    ) -> tuple[str, ...]:
        mismatches: list[str] = []
        if not submitted_preview_id and not submitted_request_hash:
            if preflight.phase_id != PHASE_A1:
                return ("preview_id", "request_hash", "phase_id")
            return ()
        if not submitted_preview_id:
            mismatches.append("preview_id")
        if not submitted_request_hash:
            mismatches.append("request_hash")
        if manifest is None:
            mismatches.append("preview_manifest")
            return tuple(dict.fromkeys(mismatches))
        if manifest.preview_id != submitted_preview_id:
            mismatches.append("preview_id")
        if manifest.request_hash != submitted_request_hash:
            mismatches.append("request_hash")
        allow_a1_preview_for_a2_launch = (
            manifest.workflow_request_hash
            and manifest.workflow_request_hash == preflight.workflow_request_hash
            and manifest.phase_id == PHASE_A1
            and preflight.phase_id == PHASE_A2
        )
        if manifest.request_hash != preflight.request_hash:
            old = manifest.normalized_request
            new = preflight.normalized_request
            field_map = {
                "workflow_run_id": (
                    manifest.workflow_run_id,
                    preflight.workflow_run_id,
                ),
                "pair_subset": (tuple(old.pair_subset), tuple(new.pair_subset)),
                "start": (old.start, new.start),
                "end": (old.end, new.end),
                "orderbook_root": (old.orderbook_root, new.orderbook_root),
                "trades_root": (old.trades_root, new.trades_root),
                "klines_root": (old.klines_root, new.klines_root),
                "historical_metadata_root": (
                    old.historical_metadata_root,
                    new.historical_metadata_root,
                ),
                "output_root": (
                    old.output_root_selected,
                    new.output_root_selected,
                ),
                "candidate_discovery_mode": (
                    old.candidate_discovery_mode,
                    new.candidate_discovery_mode,
                ),
                "bml_candidate_sampler_mode": (
                    old.bml_candidate_sampler_mode,
                    new.bml_candidate_sampler_mode,
                ),
                "engine_native_sample_size": (
                    old.engine_native_sample_size,
                    new.engine_native_sample_size,
                ),
                "allow_broad_run": (old.allow_broad_run, new.allow_broad_run),
                "small_scope_enabled": (
                    old.small_scope_enabled,
                    new.small_scope_enabled,
                ),
                "full_scan_enabled": (old.full_scan_enabled, new.full_scan_enabled),
                "no_full_scan_enabled": (
                    old.no_full_scan_enabled,
                    new.no_full_scan_enabled,
                ),
                "silver_storage_mode": (
                    old.silver_storage_mode,
                    new.silver_storage_mode,
                ),
                "debug_storage_override": (
                    old.debug_storage_override,
                    new.debug_storage_override,
                ),
            }
            if not allow_a1_preview_for_a2_launch:
                field_map = {
                    "phase_id": (manifest.phase_id, preflight.phase_id),
                    "action_name": (manifest.action_name, preflight.action_name),
                    **field_map,
                }
            for field_name, (old_value, new_value) in field_map.items():
                if old_value != new_value:
                    mismatches.append(field_name)
        return tuple(dict.fromkeys(mismatches))

    def _truthy(raw_value: object) -> bool:
        return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _has_authoritative_frozen_artifact(preflight) -> bool:
        return bool(
            preflight.normalized_request.ml_mode == "ML_MODE_OVERLAY_FROZEN"
            and preflight.ml_overlay_intake.ready
            and preflight.ml_overlay_intake.frozen_ml_artifact_path
            and preflight.ml_overlay_intake.frozen_ml_artifact_hash
        )

    def _parse_date_only(raw_value: str) -> datetime:
        value = (raw_value or "").strip().replace("Z", "+00:00")
        if "T" in value:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        return datetime.fromisoformat(f"{value}T00:00:00+00:00")

    def _derive_backtest_ml_training_window(
        *,
        selected_form: BacktestFormState,
    ) -> tuple[dict[str, object] | None, tuple[str, ...]]:
        start_text = (selected_form.start or "").strip()
        end_text = (selected_form.end or "").strip()
        blockers: list[str] = []
        if not start_text or not end_text:
            blockers.append("BACKTEST_FEATURE_TRAINING_REQUIRES_EXPLICIT_START_END")
            return None, tuple(blockers)
        try:
            requested_backtest_start = _parse_date_only(start_text)
            requested_backtest_end = _parse_date_only(end_text)
        except ValueError:
            blockers.append("BACKTEST_FEATURE_TRAINING_INVALID_DATE_RANGE")
            return None, tuple(blockers)
        if requested_backtest_end < requested_backtest_start:
            blockers.append("BACKTEST_FEATURE_TRAINING_INVALID_DATE_RANGE")
            return None, tuple(blockers)
        train_days = DEFAULT_ROLLING_TRAIN_DAYS
        validation_days = DEFAULT_ROLLING_VALIDATION_DAYS
        freshness_days = DEFAULT_ROLLING_FRESHNESS_DAYS
        chunk_days = DEFAULT_ROLLING_CHUNK_DAYS
        train_end = requested_backtest_start - timedelta(days=1)
        train_start = train_end - timedelta(days=train_days - 1)
        requested_backtest_days = (
            requested_backtest_end.date() - requested_backtest_start.date()
        ).days + 1
        return (
            {
                "train_start": train_start.date().isoformat(),
                "train_end": train_end.date().isoformat(),
                "requested_backtest_start": requested_backtest_start.date().isoformat(),
                "requested_backtest_days": max(int(requested_backtest_days), 1),
                "train_days": train_days,
                "validation_days": validation_days,
                "freshness_days": freshness_days,
                "chunk_days": chunk_days,
            },
            (),
        )

    def _existing_phase_b2_run_root(
        *,
        workflow_root: Path,
        workflow_run_id: str,
    ) -> Path | None:
        candidate = (
            workflow_root
            / workflow_phase_dirname(PHASE_B2)
            / "backtest_strategy_ladder"
            / workflow_run_id
        )
        return candidate if candidate.is_dir() else None

    def _launch_strategy_ladder_phase_job(
        *,
        jobs_root: Path,
        preflight,
        export_path: Path,
        baseline_path: Path | None,
        raw_manifest_path: Path | None,
        manifest_blocker: str,
        ambiguity_blocker: str,
        allow_broad: bool,
        operator_output_root: str,
        signed_by: str,
    ):
        selected_action_name = str(preflight.action_name or "").strip()
        parsed_action = StrategyLadderControlAction(selected_action_name)
        parsed_job_kind = (
            CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
            if parsed_action
            in {
                StrategyLadderControlAction.PHASE_A1_PREVIEW,
                StrategyLadderControlAction.PHASE_A2_DATA_FACTORY,
                StrategyLadderControlAction.DATA_FACTORY_DRY_RUN,
                StrategyLadderControlAction.DATA_FACTORY_SMALL_SCOPE_RUN,
            }
            else (
                CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY
                if parsed_action
                == StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY
                else
                CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
                if parsed_action
                in {
                    StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY,
                    StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY,
                }
                else CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN
            )
        )
        blocked_reason = ""
        if (
            parsed_job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
            and "ML_OVERLAY_UNSUPPORTED_FOR_DATA_FACTORY" in preflight.blockers
        ):
            blocked_reason = "ML_OVERLAY_UNSUPPORTED_FOR_DATA_FACTORY"
        elif manifest_blocker:
            blocked_reason = manifest_blocker
        elif ambiguity_blocker:
            blocked_reason = ambiguity_blocker
        elif not preflight.preview_launchable and preflight.blockers:
            blocked_reason = preflight.blockers[0]
        elif not preflight.preview_launchable:
            blocked_reason = preflight.inspection_status
        canonical_raw_roots = tuple(
            Path(path).expanduser()
            for path in canonical_patch6_raw_roots(
                BacktestFormState(
                    orderbook_path=preflight.normalized_request.orderbook_root,
                    trades_path=preflight.normalized_request.trades_root,
                    klines_path=preflight.normalized_request.klines_root,
                    raw_roots=preflight.normalized_request.raw_roots,
                )
            )
            if path
        )
        workflow_root = _workflow_root_for_request(
            jobs_root=jobs_root,
            workflow_run_id=preflight.workflow_run_id,
            operator_output_root=operator_output_root,
        )
        phase_a2_root = workflow_root / workflow_phase_dirname(PHASE_A2)
        feature_store_root = (
            phase_a2_root / "gold"
            if parsed_job_kind
            in {
                CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY,
            }
            else None
        )
        silver_index_path = (
            phase_a2_root / "silver_index.json"
            if parsed_job_kind
            in {
                CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
                CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY,
            }
            else None
        )
        candidate_events_path = (
            resolve_phase_b1_replay_input_candidates_path(
                workflow_root=workflow_root,
                workflow_run_id=preflight.workflow_run_id,
                allow_discovery_fallback=(
                    parsed_action
                    == StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY
                ),
            )
            if parsed_action
            in {
                StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY,
                StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY,
            }
            else None
        )
        metadata_root_path = (
            Path(preflight.normalized_request.historical_metadata_root).expanduser()
            if preflight.normalized_request.historical_metadata_root
            else None
        )
        frozen_ml_artifact_path_obj = (
            Path(preflight.normalized_request.frozen_ml_artifact_path).expanduser()
            if preflight.normalized_request.frozen_ml_artifact_path
            else None
        )
        rolling_ml_window_plan_path_obj = (
            Path(preflight.normalized_request.rolling_ml_window_plan_path).expanduser()
            if preflight.normalized_request.rolling_ml_window_plan_path
            else None
        )
        if (
            metadata_root_path is not None
            and not preflight.command_preview
            and not blocked_reason
        ):
            blocked_reason = "METADATA_ROOT_NOT_PROPAGATED_TO_LAUNCH"
        return launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=parsed_job_kind,
            export_dir=export_path,
            baseline_export_dir=baseline_path,
            signed_by=signed_by,
            action_name=parsed_action.value,
            phase_id=preflight.phase_id,
            preview_id=preflight.preview_id,
            request_hash=preflight.request_hash,
            raw_source_manifest_path=raw_manifest_path,
            historical_metadata_root=metadata_root_path,
            raw_roots=canonical_raw_roots,
            pairs=preflight.normalized_request.pair_subset,
            start=preflight.normalized_request.start,
            end=preflight.normalized_request.end,
            allow_broad_run=allow_broad,
            blocked_reason=blocked_reason,
            ml_mode_status=preflight.normalized_request.ml_mode,
            frozen_ml_artifact_path=frozen_ml_artifact_path_obj,
            frozen_ml_artifact_hash=preflight.normalized_request.frozen_ml_artifact_hash,
            expected_edge_artifact_mode=preflight.normalized_request.expected_edge_artifact_mode,
            rolling_ml_window_plan_path=rolling_ml_window_plan_path_obj,
            ml_artifact_freshness_days=preflight.normalized_request.ml_artifact_freshness_days,
            operator_output_root=operator_output_root,
            engine_native_mode=parsed_job_kind
            in {
                CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN,
                CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
            },
            engine_native_sample_size=preflight.effective_engine_native_sample_size,
            candidate_discovery_mode=preflight.candidate_discovery_mode,
            preselected_only=preflight.normalized_request.preselected_only,
            diagnostic_full_replay=preflight.normalized_request.diagnostic_full_replay,
            backtest_timeframes=preflight.normalized_request.backtest_timeframes,
            b1_5_policy_mode=preflight.normalized_request.b1_5_policy_mode,
            small_scope_enabled=preflight.small_scope_enabled,
            full_scan_enabled=preflight.full_scan_enabled,
            no_full_scan_enabled=preflight.no_full_scan_enabled,
            silver_storage_mode=preflight.silver_storage_mode_effective,
            debug_storage_override=preflight.normalized_request.debug_storage_override,
            workflow_run_id=preflight.workflow_run_id,
            feature_store_root=feature_store_root,
            silver_index_path=silver_index_path,
            candidate_events_path=candidate_events_path,
            consumed_artifact_refs=_workflow_consumed_artifact_refs(
                workflow_root=workflow_root,
                phase_id=preflight.phase_id,
                normalized_request=preflight.normalized_request,
            ),
            feature_names_csv=preflight.normalized_request.feature_names,
            bml_candidate_sampler_mode=(
                preflight.normalized_request.bml_candidate_sampler_mode
            ),
        )

    def _reconcile_backtest_ml_chain() -> None:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return
        chain_state = read_backtest_ml_chain_state(jobs_root)
        if chain_state is None or chain_state.status in {
            "CHAIN_NOT_REQUESTED",
            "CHAIN_BLOCKED",
            "CHAIN_REPLAY_COMPLETED",
        }:
            return
        jobs = load_backtest_job_records(jobs_root, limit=64)
        jobs_by_id = {job.job_id: job for job in jobs}
        handoff_job = jobs_by_id.get(chain_state.handoff_job_id)
        replay_job = jobs_by_id.get(chain_state.replay_job_id)
        running_statuses = {"JOB_CREATED", "JOB_RUNNING", "JOB_CANCELLING", "REQUESTED"}
        success_statuses = {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}
        terminal_failure_statuses = {"JOB_FAILED", "JOB_BLOCKED", "JOB_CANCELLED", "JOB_KILLED"}
        if chain_state.status == "CHAIN_HANDOFF_PENDING":
            if handoff_job is None:
                return
            handoff_status = handoff_job.status.value
            if handoff_status in running_statuses:
                return
            if handoff_status in terminal_failure_statuses:
                write_backtest_ml_chain_state(
                    jobs_root,
                    chain_state.model_copy(
                        update={
                            "status": "CHAIN_BLOCKED",
                            "updated_at": datetime.now(UTC).isoformat(),
                            "handoff_output_root": handoff_job.output_root,
                            "blockers": tuple(handoff_job.blockers or (handoff_status,)),
                        }
                    ),
                )
                return
            if handoff_status in success_statuses:
                updated_form = chain_state.frozen_form.model_copy(
                    update={
                        "ml_mode": "ML_MODE_OVERLAY_FROZEN",
                        "ml_handoff_run_root": handoff_job.output_root,
                    }
                )
                preflight = build_patch6_preflight_preview(
                    selected_form=updated_form,
                    jobs_root=jobs_root,
                )
                updated_form = updated_form.model_copy(
                    update={
                        "workflow_run_id": preflight.workflow_run_id,
                        "pairs": (
                            preflight.normalized_request.pair_subset or updated_form.pairs
                        ),
                        "start": preflight.normalized_request.start or updated_form.start,
                        "end": preflight.normalized_request.end or updated_form.end,
                        "expected_edge_artifact_mode": (
                            preflight.normalized_request.expected_edge_artifact_mode
                            or updated_form.expected_edge_artifact_mode
                        ),
                        "frozen_ml_artifact_path": (
                            preflight.normalized_request.frozen_ml_artifact_path
                            or updated_form.frozen_ml_artifact_path
                        ),
                        "frozen_ml_artifact_hash": (
                            preflight.normalized_request.frozen_ml_artifact_hash
                            or updated_form.frozen_ml_artifact_hash
                        ),
                        "rolling_ml_window_plan_path": (
                            preflight.normalized_request.rolling_ml_window_plan_path
                            or updated_form.rolling_ml_window_plan_path
                        ),
                        "ml_artifact_freshness_days": (
                            preflight.normalized_request.ml_artifact_freshness_days
                            or updated_form.ml_artifact_freshness_days
                        ),
                    }
                )
                write_backtest_form_state(jobs_root, updated_form)
                if not _has_authoritative_frozen_artifact(preflight):
                    write_backtest_ml_chain_state(
                        jobs_root,
                        chain_state.model_copy(
                            update={
                                "status": "CHAIN_BLOCKED",
                                "updated_at": datetime.now(UTC).isoformat(),
                                "handoff_output_root": handoff_job.output_root,
                                "blockers": tuple(preflight.ml_overlay_intake.blocker_codes),
                            }
                        ),
                    )
                    return
                replay_record = _launch_strategy_ladder_phase_job(
                    jobs_root=jobs_root,
                    preflight=preflight,
                    export_path=Path(updated_form.export_dir).expanduser(),
                    baseline_path=(
                        Path(updated_form.baseline_export_dir).expanduser()
                        if updated_form.baseline_export_dir
                        else None
                    ),
                    raw_manifest_path=(
                        Path(updated_form.raw_source_manifest_path).expanduser()
                        if updated_form.raw_source_manifest_path
                        and is_valid_raw_source_manifest_path(
                            updated_form.raw_source_manifest_path
                        )
                        else None
                    ),
                    manifest_blocker="",
                    ambiguity_blocker="",
                    allow_broad=_truthy(updated_form.allow_broad_run),
                    operator_output_root=(updated_form.output_root or "").strip(),
                    signed_by=updated_form.signed_by,
                )
                write_launch_request_state(
                    jobs_root,
                    build_patch6_state(
                        state_name="launch_request_state",
                        normalized_request=preflight.normalized_request,
                        request_hash=preflight.request_hash,
                        detected_pairs=preflight.detected_pairs,
                        active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                        status=replay_record.status.value,
                        preview_id=preflight.preview_id,
                        job_id=replay_record.job_id,
                        output_root_effective=replay_record.output_root,
                        blockers=replay_record.blockers,
                    ),
                )
                write_backtest_ml_chain_state(
                    jobs_root,
                    chain_state.model_copy(
                        update={
                            "status": (
                                "CHAIN_BLOCKED"
                                if replay_record.status.value in terminal_failure_statuses
                                else "CHAIN_REPLAY_LAUNCHED"
                            ),
                            "updated_at": datetime.now(UTC).isoformat(),
                            "handoff_output_root": handoff_job.output_root,
                            "replay_job_id": replay_record.job_id,
                            "replay_output_root": replay_record.output_root,
                            "blockers": tuple(replay_record.blockers),
                            "frozen_form": updated_form,
                        }
                    ),
                )
                return
        if chain_state.status == "CHAIN_REPLAY_LAUNCHED":
            if replay_job is None:
                return
            replay_status = replay_job.status.value
            if replay_status in running_statuses:
                return
            write_backtest_ml_chain_state(
                jobs_root,
                chain_state.model_copy(
                    update={
                        "status": (
                            "CHAIN_REPLAY_COMPLETED"
                            if replay_status in success_statuses
                            else "CHAIN_BLOCKED"
                        ),
                        "updated_at": datetime.now(UTC).isoformat(),
                        "replay_output_root": replay_job.output_root,
                        "blockers": tuple(replay_job.blockers),
                    }
                ),
            )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(request, current_page="overview", selected_pair=pair)
        return templates.TemplateResponse(request, "index.html", {"vm": view_model})

    @app.get("/lab", response_class=HTMLResponse)
    def lab(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(request, current_page="lab", selected_pair=pair)
        return templates.TemplateResponse(
            request,
            "pages/lab.html",
            {"vm": view_model},
        )

    @app.get("/trading", response_class=HTMLResponse)
    def trading(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(request, current_page="trading", selected_pair=pair)
        return templates.TemplateResponse(
            request,
            "pages/trading.html",
            {"vm": view_model},
        )

    @app.get("/shadow", response_class=HTMLResponse)
    def shadow(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(request, current_page="shadow", selected_pair=pair)
        return templates.TemplateResponse(
            request,
            "pages/shadow.html",
            {"vm": view_model},
        )

    @app.get("/vps", response_class=HTMLResponse)
    def vps(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(request, current_page="vps", selected_pair=pair)
        return templates.TemplateResponse(request, "pages/vps.html", {"vm": view_model})

    @app.get("/backtest", response_class=HTMLResponse)
    def backtest(
        request: Request,
        pair: str | None = None,
        pinned_run_id: str | None = None,
    ) -> HTMLResponse:
        # Patch BACKTEST-RUN-PIN (2026-05-27) — allow operator to pin a
        # historical run for inspection from the Recent Backtest Jobs table.
        # When `pinned_run_id` matches a job in the cockpit registry, the
        # whole strategy_ladder_summary is recomputed for THAT run instead
        # of the latest job. The cockpit then displays its decision report,
        # backbone parity card, backbone metrics card, etc. for diagnostic.
        view_model = _build_vm(
            request,
            current_page="backtest",
            selected_pair=pair,
            pinned_run_id=(pinned_run_id or "").strip(),
        )
        return templates.TemplateResponse(
            request,
            "pages/backtest.html",
            {"vm": view_model},
        )

    @app.get("/backtest/picker/drives")
    def backtest_picker_drives() -> JSONResponse:
        return JSONResponse({"drives": _list_local_drives()})

    @app.get("/backtest/picker/browse")
    def backtest_picker_browse(path: str = "") -> JSONResponse:
        return JSONResponse(_list_directories(path))

    @app.get("/backtest/picker/native")
    def backtest_picker_native(path: str = "") -> JSONResponse:
        return JSONResponse(_pick_native_directory(path))

    @app.get("/backtest/status.json")
    def backtest_status_snapshot() -> JSONResponse:
        _reconcile_backtest_ml_chain()
        jobs_root = app.state.paths.backtest_jobs_root
        backtest_jobs = (
            load_backtest_job_records(jobs_root, limit=8)
            if jobs_root is not None
            else ()
        )
        latest_job = backtest_jobs[0] if backtest_jobs else None
        chain_state = (
            read_backtest_ml_chain_state(jobs_root)
            if jobs_root is not None
            else None
        )
        service = read_service_status(app.state.paths)
        payload = {
            "generated_at": datetime.now(UTC),
            "service": {
                "label": "Shadow Service",
                "running": service.running,
                "pid": service.pid,
                "runtime_mode": service.runtime_mode,
                "status_text": (
                    f"Shadow Service | PID {service.pid}"
                    if service.running and service.pid is not None
                    else "Shadow Service offline"
                ),
            },
            "summary": _build_backtest_status_summary(backtest_jobs),
            "latest_job": _serialize_backtest_job(latest_job),
            "backtest_jobs": [
                _serialize_backtest_job(record) for record in backtest_jobs
            ],
            "ml_chain": None if chain_state is None else chain_state.model_dump(mode="json"),
        }
        return JSONResponse(content=_jsonable(payload))

    @app.get("/lab/status.json")
    def lab_status_snapshot() -> JSONResponse:
        jobs_root = app.state.paths.backtest_jobs_root
        backtest_jobs = (
            load_backtest_job_records(jobs_root, limit=24)
            if jobs_root is not None
            else ()
        )
        ml_jobs = tuple(
            job
            for job in backtest_jobs
            if job.job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF
        )
        latest_job = ml_jobs[0] if ml_jobs else None
        handoff = read_strategy_ladder_ml_handoff_dashboard_summary(
            backtest_jobs,
            form_state=read_lab_ml_handoff_form_state(jobs_root),
        )
        payload = {
            "generated_at": datetime.now(UTC),
            "summary": _build_backtest_status_summary(ml_jobs),
            "latest_job": _serialize_backtest_job(latest_job),
            "ml_jobs": [_serialize_backtest_job(record) for record in ml_jobs[:8]],
            "handoff": handoff,
        }
        return JSONResponse(content=_jsonable(payload))

    @app.get("/backtest/candidate-detail.json")
    def backtest_candidate_detail(candidate_id: str = "") -> JSONResponse:
        selected_candidate_id = candidate_id.strip()
        if not selected_candidate_id:
            return JSONResponse(
                status_code=400,
                content={"error": "candidate_id is required"},
            )
        active_feature_names, artifact_feature_names = (
            _resolve_backtest_runtime_feature_context()
        )
        runtime = read_runtime_surfaces(
            service_dir=app.state.paths.service_dir,
            queue_root=app.state.paths.dashboard_command_queue_root,
            observability_output_dir=app.state.paths.observability_output_dir,
            backtest_jobs_root=app.state.paths.backtest_jobs_root,
            selected_candidate_id=selected_candidate_id,
            active_feature_names=active_feature_names,
            artifact_feature_names=artifact_feature_names,
        )
        summary = runtime.strategy_ladder_summary
        found = (
            summary.selected_candidate_id == selected_candidate_id
            and bool(summary.selected_candidate_detail)
        )
        payload = {
            "candidate_id": selected_candidate_id,
            "found": found,
            "selected_candidate_id": summary.selected_candidate_id,
            "detail": summary.selected_candidate_detail,
            "replay": summary.selected_candidate_replay,
            "window": summary.selected_candidate_window,
        }
        return JSONResponse(
            status_code=200 if found else 404,
            content=_jsonable(payload),
        )

    @app.get("/backtest/candidate-feature-table.json")
    def backtest_candidate_feature_table() -> JSONResponse:
        active_feature_names, artifact_feature_names = (
            _resolve_backtest_runtime_feature_context()
        )
        runtime = read_runtime_surfaces(
            service_dir=app.state.paths.service_dir,
            queue_root=app.state.paths.dashboard_command_queue_root,
            observability_output_dir=app.state.paths.observability_output_dir,
            backtest_jobs_root=app.state.paths.backtest_jobs_root,
            active_feature_names=active_feature_names,
            artifact_feature_names=artifact_feature_names,
        )
        summary = runtime.strategy_ladder_summary
        payload = {
            "generated_at": datetime.now(UTC),
            "run_id": summary.run_id,
            "workflow_run_id": summary.workflow_run_id,
            "status": summary.candidate_feature_table_status,
            "active_feature_names": summary.active_feature_names,
            "columns": (
                "candidate_id",
                "pair",
                "engine_id",
                "timeframe",
                "outcome_status",
                "accepted_or_refused",
                "reason_codes",
                *summary.candidate_feature_columns,
            ),
            "rows": summary.candidate_feature_rows,
            "wiring_status": summary.feature_engine_ml_wiring_status,
            "wiring_report_path": summary.feature_engine_ml_wiring_report_path,
            "wiring_rows": summary.feature_engine_ml_wiring_rows,
        }
        return JSONResponse(content=_jsonable(payload))

    @app.get("/observability", response_class=HTMLResponse)
    def observability(request: Request, pair: str | None = None) -> HTMLResponse:
        view_model = _build_vm(
            request,
            current_page="observability",
            selected_pair=pair,
        )
        return templates.TemplateResponse(
            request,
            "pages/observability.html",
            {"vm": view_model},
        )

    @app.get("/logs", response_class=HTMLResponse)
    def logs(
        request: Request,
        pair: str | None = None,
        event_type: list[str] | None = None,
        contains_text: str = "",
        error_only: bool = False,
        max_events: int = 50,
    ) -> HTMLResponse:
        log_query = ShadowVpsServiceLogQuery(
            max_events=max(1, min(max_events, 200)),
            event_types=tuple(item for item in (event_type or []) if item),
            contains_text=contains_text,
            error_only=error_only,
        )
        view_model = _build_vm(
            request,
            current_page="logs",
            selected_pair=pair,
            log_query=log_query,
        )
        return templates.TemplateResponse(
            request,
            "pages/logs.html",
            {"vm": view_model},
        )

    @app.post("/lab/import/{action_name}")
    async def lab_import(
        action_name: str,
        artifact_file: UploadFile = File(...),
    ) -> RedirectResponse:
        ingress_root = app.state.paths.artifact_ingress_root
        queue_root = app.state.paths.dashboard_command_queue_root
        if ingress_root is None or queue_root is None:
            return _redirect(
                "/lab",
                notice="Artifact ingress root or queue root is not configured.",
                notice_status="error",
            )
        action = _ARTIFACT_IMPORT_ACTIONS.get(action_name)
        if action is None:
            return _redirect(
                "/lab",
                notice=f"Unsupported artifact import action: {action_name}",
                notice_status="error",
            )
        payload = await artifact_file.read()
        if not payload:
            return _redirect(
                "/lab",
                notice="Uploaded artifact file is empty.",
                notice_status="error",
            )
        manifest = stage_artifact_upload(
            ingress_root=ingress_root,
            filename=artifact_file.filename or "artifact.bundle",
            payload=payload,
            artifact_kind=action["artifact_kind"],
        )
        summary = enqueue_artifact_command(
            queue_root=queue_root,
            command_kind=action["command_kind"],
            requested_by="cockpit_operator",
            operator_reason=action["operator_reason"],
            artifact_manifest=manifest,
        )
        return _redirect(
            "/lab",
            notice=(
                f"Queued {summary.command_kind} request {summary.request_id} "
                f"for {artifact_file.filename or 'artifact.bundle'}."
            ),
            notice_status="success",
        )

    @app.post("/lab/export/{action_name}")
    def lab_export(action_name: str) -> RedirectResponse:
        queue_root = app.state.paths.dashboard_command_queue_root
        if queue_root is None:
            return _redirect(
                "/lab",
                notice="Dashboard command queue root is not configured.",
                notice_status="error",
            )
        action = _ARTIFACT_EXPORT_ACTIONS.get(action_name)
        if action is None:
            return _redirect(
                "/lab",
                notice=f"Unsupported artifact export action: {action_name}",
                notice_status="error",
            )
        summary = enqueue_artifact_command(
            queue_root=queue_root,
            command_kind=action["command_kind"],
            requested_by="cockpit_operator",
            operator_reason=action["operator_reason"],
        )
        return _redirect(
            "/lab",
            notice=f"Queued {summary.command_kind} request {summary.request_id}.",
            notice_status="success",
        )

    @app.post("/lab/strategy-ladder-ml-handoff")
    def lab_strategy_ladder_ml_handoff(
        intent: str = Form("launch"),
        kline_root: str = Form(...),
        b2_run_root: str = Form(""),
        label_store_dataset_path: str = Form(""),
        orderbook_root: str = Form(""),
        trades_root: str = Form(""),
        metadata_root: str = Form(""),
        handoff_export_dir: str = Form(""),
        pair: str = Form("BTCUSDT"),
        # Patch P2 (2026-05-22) — multi-select. Empty list → mono `pair` fallback.
        selected_pairs: list[str] = Form(default=[]),
        timeframe: str = Form("1m"),
        train_start: str = Form(...),
        train_end: str = Form(...),
        requested_backtest_start: str = Form(""),
        requested_backtest_days: int = Form(130),
        train_days: int = Form(180),
        validation_days: int = Form(30),
        freshness_days: int = Form(30),
        chunk_days: int = Form(30),
        calibration_version: str = Form("strategy_ladder_expected_edge.v1"),
        feature_names: str = Form("close_return,high_low_range,volume"),
        selected_features_csv: str = Form(""),
        selected_features: list[str] = Form(default=[]),
        feature_picker_enabled: str = Form(""),
        sample_stride_minutes: int = Form(60),
        target_horizon_minutes: int = Form(1),
        training_seed: int = Form(5307),
        max_optuna_trials: int = Form(0),
        min_training_rows: int = Form(210),
        shap_summary_ref: str = Form(""),
        signed_by: str = Form("cockpit_operator"),
    ) -> RedirectResponse:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return _redirect(
                "/lab",
                notice="Backtest jobs root is not configured.",
                notice_status="error",
            )
        try:
            lab_form_state = _build_lab_ml_handoff_form_state(
                kline_root=kline_root,
                b2_run_root=b2_run_root,
                label_store_dataset_path=label_store_dataset_path,
                orderbook_root=orderbook_root,
                trades_root=trades_root,
                metadata_root=metadata_root,
                handoff_export_dir=handoff_export_dir,
                pair=pair,
                selected_pairs=selected_pairs,
                timeframe=timeframe,
                train_start=train_start,
                train_end=train_end,
                requested_backtest_start=requested_backtest_start,
                requested_backtest_days=requested_backtest_days,
                train_days=train_days,
                validation_days=validation_days,
                freshness_days=freshness_days,
                chunk_days=chunk_days,
                calibration_version=calibration_version,
                feature_names=feature_names,
                selected_features_csv=selected_features_csv,
                selected_features=selected_features,
                feature_picker_enabled=feature_picker_enabled,
                sample_stride_minutes=sample_stride_minutes,
                target_horizon_minutes=target_horizon_minutes,
                training_seed=training_seed,
                max_optuna_trials=max_optuna_trials,
                min_training_rows=min_training_rows,
                shap_summary_ref=shap_summary_ref,
                signed_by=signed_by,
                intent=intent,
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        lab_governance_entries = discover_lab_feature_governance(
            lab_form_state,
            registry_path=jobs_root / "feature_promotion_registry.json",
        )
        demoted_override_features = selected_demoted_lab_features(
            selected_feature_names=tuple(lab_form_state.selected_features),
            governance_entries=lab_governance_entries,
        )
        if demoted_override_features:
            _logger.warning(
                "EXPECTED_EDGE_FEATURE_USER_OVERRIDE_DEMOTED pair=%s timeframe=%s features=%s",
                lab_form_state.pair,
                lab_form_state.timeframe,
                ",".join(demoted_override_features),
            )
        write_lab_ml_handoff_form_state(jobs_root, lab_form_state)
        synced_backtest_form = _sync_lab_handoff_into_backtest_form(
            read_backtest_form_state(jobs_root),
            lab_form_state,
        )
        requested_non_legacy_features = _non_legacy_expected_edge_features(
            tuple(lab_form_state.selected_features)
        )
        if (
            intent == "launch"
            and requested_non_legacy_features
            and not (
                (lab_form_state.b2_run_root or "").strip()
                or (lab_form_state.label_store_dataset_path or "").strip()
            )
        ):
            write_backtest_form_state(jobs_root, synced_backtest_form)
            return _redirect(
                "/lab",
                notice=(
                    "Non-legacy ML features require B2 run root or label-store dataset path before launch: "
                    + ", ".join(requested_non_legacy_features)
                ),
                notice_status="error",
            )
        if intent == "preview":
            preflight = build_patch6_preflight_preview(
                selected_form=synced_backtest_form,
                jobs_root=jobs_root,
            )
            synced_backtest_form = synced_backtest_form.model_copy(
                update={"workflow_run_id": preflight.workflow_run_id}
            )
            write_backtest_form_state(jobs_root, synced_backtest_form)
            current_form_state = build_patch6_state(
                state_name="current_form_state",
                normalized_request=preflight.normalized_request,
                request_hash=preflight.request_hash,
                detected_pairs=preflight.detected_pairs,
                active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                status=preflight.inspection_status,
                preview_id=preflight.preview_id,
                output_root_effective=preflight.output_root_effective_preview,
                blockers=preflight.blockers,
            )
            write_current_form_state(jobs_root, current_form_state)
            preview_manifest = _build_preview_manifest(preflight=preflight)
            write_preview_manifest(jobs_root, preview_manifest)
            _write_phase_a1_preview_artifacts(
                jobs_root=jobs_root,
                preview_manifest=preview_manifest,
                preflight=preflight,
            )
            write_source_preview_state(
                jobs_root,
                build_patch6_state(
                    state_name="source_preview_state",
                    normalized_request=preflight.normalized_request,
                    request_hash=preflight.request_hash,
                    detected_pairs=preflight.detected_pairs,
                    active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                    status=preflight.inspection_status,
                    preview_id=preflight.preview_id,
                    output_root_effective=preflight.output_root_effective_preview,
                    blockers=preflight.blockers,
                ),
            )
            return _redirect(
                "/lab",
                notice=(
                    f"IA Lab source preview updated: {preflight.inspection_status}."
                ),
                notice_status=("success" if preflight.preview_launchable else "info"),
            )

        write_backtest_form_state(jobs_root, synced_backtest_form)
        kline_path = Path(kline_root).expanduser()
        output_root = (handoff_export_dir or "").strip()
        if not train_start.strip() or not train_end.strip():
            return _redirect(
                "/lab",
                notice="Strategy Ladder ML handoff requires train_start and train_end.",
                notice_status="error",
            )
        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
            export_dir=kline_path,
            b2_run_root=Path(b2_run_root).expanduser() if (b2_run_root or "").strip() else None,
            label_store_dataset_path=(
                Path(label_store_dataset_path).expanduser()
                if (label_store_dataset_path or "").strip()
                else None
            ),
            signed_by=signed_by,
            operator_output_root=output_root,
            raw_roots=(kline_path,),
            pairs=(
                lab_form_state.selected_pairs
                if lab_form_state.selected_pairs
                else ((pair.strip().upper() or "BTCUSDT"),)
            ),
            start=train_start.strip(),
            end=train_end.strip(),
            calibration_version=calibration_version.strip()
            or "strategy_ladder_expected_edge.v1",
            timeframe=timeframe.strip() or "1m",
            requested_backtest_start=requested_backtest_start.strip(),
            requested_backtest_days=max(int(requested_backtest_days), 1),
            train_days=max(int(train_days), 1),
            validation_days=max(int(validation_days), 1),
            freshness_days=max(int(freshness_days), 1),
            chunk_days=max(int(chunk_days), 1),
            feature_names_csv=(
                lab_form_state.feature_names or "close_return,high_low_range,volume"
            ),
            sample_stride_minutes=max(int(sample_stride_minutes), 1),
            target_horizon_minutes=max(int(target_horizon_minutes), 1),
            training_seed=int(training_seed),
            max_optuna_trials=max(int(max_optuna_trials), 0),
            min_training_rows=max(int(min_training_rows), 10),
            shap_summary_ref=(shap_summary_ref or "").strip(),
        )
        return _redirect(
            "/lab",
            notice=(
                f"Blocked Strategy Ladder ML handoff job {record.job_id}: "
                f"{', '.join(record.blockers)}."
                if record.blockers
                else f"Launched Strategy Ladder ML handoff job {record.job_id}."
            ),
            notice_status=("error" if record.blockers else "success"),
        )

    @app.post("/backtest/run")
    def backtest_run(
        job_kind: str = Form(""),
        phase_id: str = Form(""),
        workflow_phase: str = Form(""),
        action_name: str = Form(""),
        intent: str = Form("launch"),
        preview_id: str = Form(""),
        request_hash: str = Form(""),
        workflow_run_id: str = Form(""),
        export_dir: str = Form(...),
        baseline_export_dir: str = Form(""),
        raw_source_manifest_path: str = Form(""),
        raw_roots: str = Form(""),
        orderbook_path: str = Form(""),
        klines_path: str = Form(""),
        trades_path: str = Form(""),
        metadata_path: str = Form(""),
        output_root: str = Form(""),
        pairs: str = Form(""),
        start: str = Form(""),
        end: str = Form(""),
        allow_broad_run: str = Form(""),
        confirm_broad_run: str = Form(""),
        candidate_discovery_mode: str = Form("SAMPLE_CAPPED_DEBUG"),
        bml_candidate_sampler_mode: str = Form("TEMPORAL_STRATIFIED_BACKGROUND_GRID"),
        engine_native_sample_size: int = Form(10),
        b1_5_policy_mode: str = Form("conservative_hard_only"),
        preselected_only: str = Form("true"),
        diagnostic_full_replay: str = Form(""),
        small_scope_enabled: str = Form(""),
        full_scan_enabled: str = Form(""),
        silver_storage_mode: str = Form("jsonl_debug"),
        debug_storage_override: str = Form(""),
        ml_mode: str = Form("ML_MODE_OFF"),
        training_timeframe: str = Form("1m"),
        backtest_timeframes: str = Form("1m"),
        feature_names: str = Form("close_return,high_low_range,volume"),
        selected_features_csv: str = Form(""),
        selected_features: list[str] = Form(default=[]),
        feature_picker_enabled: str = Form(""),
        # Patch P3 (2026-05-22) — explicit mono|multi mode selector.
        expected_edge_artifact_mode: str = Form("MONO_PAIR_LEGACY"),
        ml_handoff_run_root: str = Form(""),
        frozen_ml_artifact_path: str = Form(""),
        frozen_ml_artifact_hash: str = Form(""),
        rolling_ml_window_plan_path: str = Form(""),
        ml_artifact_freshness_days: int = Form(30),
        signed_by: str = Form("cockpit_operator"),
        # Patch P3 (2026-05-22) — multi-select pair checkbox (overrides CSV `pairs`).
        selected_pairs: list[str] = Form(default=[]),
    ) -> RedirectResponse:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return _redirect(
                "/backtest",
                notice="Backtest jobs root is not configured.",
                notice_status="error",
            )
        export_path = Path(export_dir).expanduser()
        baseline_path = Path(baseline_export_dir).expanduser() if baseline_export_dir else None
        selected_action_name = action_name_for_phase(
            workflow_phase or phase_id,
            fallback=action_name,
        )
        resolved_phase_id = phase_id_for_action(selected_action_name) if selected_action_name else ""
        # Dedicated fields are canonical for Patch 6. Legacy raw_roots remain an
        # advanced fallback only when the dedicated roots are empty.
        explicit_raw_root_strings: list[str] = []
        for explicit in (orderbook_path, klines_path, trades_path):
            cleaned = (explicit or "").strip()
            if cleaned and cleaned not in explicit_raw_root_strings:
                explicit_raw_root_strings.append(cleaned)
        legacy_raw_root_strings = [
            part.strip() for part in raw_roots.split(",") if part.strip()
        ]
        raw_root_strings = (
            list(explicit_raw_root_strings)
            if explicit_raw_root_strings
            else list(dict.fromkeys(legacy_raw_root_strings))
        )
        # Manifest validation: must be a .json path. Anything else (.data,
        # folders, .csv) is rejected with a typed blocker.
        manifest_blocker = ""
        raw_manifest_path: Path | None = None
        manifest_raw = (raw_source_manifest_path or "").strip()
        if manifest_raw:
            if is_valid_raw_source_manifest_path(manifest_raw):
                raw_manifest_path = Path(manifest_raw).expanduser()
            else:
                manifest_blocker = RAW_SOURCE_MANIFEST_INVALID_PATH_TYPE
        # Patch P3 (2026-05-22) — multi-select checkbox takes priority over CSV
        # `pairs`. Strip / dedup / preserve order.
        if selected_pairs:
            seen_selected: set[str] = set()
            raw_pair_tokens: list[str] = []
            for raw_name in selected_pairs:
                cleaned = (raw_name or "").strip()
                if not cleaned or cleaned in seen_selected:
                    continue
                seen_selected.add(cleaned)
                raw_pair_tokens.append(cleaned)
        else:
            raw_pair_tokens = [part.strip() for part in pairs.split(",") if part.strip()]
        rerouted_pair_tokens: list[str] = []
        for token in raw_pair_tokens:
            if is_path_like_pair_token(token):
                if token not in raw_root_strings and not explicit_raw_root_strings:
                    raw_root_strings.append(token)
                inferred = infer_pair_symbol_from_path(token)
                if inferred and inferred not in rerouted_pair_tokens:
                    rerouted_pair_tokens.append(inferred)
            elif token not in rerouted_pair_tokens:
                rerouted_pair_tokens.append(token)
        # If operator left "Pair subset" empty but provided dedicated paths,
        # infer the symbol from the paths. Reject ambiguous universes.
        ambiguity_blocker = ""
        if not rerouted_pair_tokens and explicit_raw_root_strings:
            inferred_symbols, ambiguous = infer_pair_universe_from_paths(
                tuple(explicit_raw_root_strings)
            )
            if ambiguous:
                ambiguity_blocker = PAIR_UNIVERSE_AMBIGUOUS
            elif inferred_symbols:
                rerouted_pair_tokens = list(inferred_symbols)
        raw_root_paths = tuple(
            Path(part).expanduser() for part in raw_root_strings
        )
        pair_values = tuple(rerouted_pair_tokens)
        allow_broad = str(allow_broad_run).strip().lower() in {"1", "true", "yes", "on"}
        operator_output_root = (output_root or "").strip()
        form_state = _build_backtest_form_state(
            current_form=read_backtest_form_state(jobs_root),
            job_kind=job_kind,
            selected_action_name=selected_action_name,
            resolved_phase_id=resolved_phase_id,
            workflow_phase=workflow_phase,
            workflow_run_id=workflow_run_id,
            export_dir=export_dir,
            baseline_export_dir=baseline_export_dir,
            raw_source_manifest_path=raw_source_manifest_path,
            raw_roots=(() if explicit_raw_root_strings else tuple(raw_root_strings)),
            pairs=pair_values,
            start=start,
            end=end,
            ml_mode=ml_mode,
            training_timeframe=training_timeframe,
            backtest_timeframes=backtest_timeframes,
            feature_names=feature_names,
            selected_features_csv=selected_features_csv,
            selected_features=selected_features,
            feature_picker_enabled=feature_picker_enabled,
            expected_edge_artifact_mode=expected_edge_artifact_mode,
            ml_handoff_run_root=ml_handoff_run_root,
            frozen_ml_artifact_path=frozen_ml_artifact_path,
            frozen_ml_artifact_hash=frozen_ml_artifact_hash,
            rolling_ml_window_plan_path=rolling_ml_window_plan_path,
            ml_artifact_freshness_days=ml_artifact_freshness_days,
            allow_broad_run=allow_broad_run,
            confirm_broad_run=confirm_broad_run,
            candidate_discovery_mode=candidate_discovery_mode,
            bml_candidate_sampler_mode=bml_candidate_sampler_mode,
            engine_native_sample_size=engine_native_sample_size,
            b1_5_policy_mode=b1_5_policy_mode,
            preselected_only=preselected_only,
            diagnostic_full_replay=diagnostic_full_replay,
            small_scope_enabled=small_scope_enabled,
            full_scan_enabled=full_scan_enabled,
            silver_storage_mode=silver_storage_mode,
            debug_storage_override=debug_storage_override,
            signed_by=signed_by,
            orderbook_path=orderbook_path,
            klines_path=klines_path,
            trades_path=trades_path,
            metadata_path=metadata_path,
            output_root=operator_output_root,
        )
        preflight = build_patch6_preflight_preview(
            selected_form=form_state,
            jobs_root=jobs_root,
        )
        form_state = form_state.model_copy(
            update={
                "workflow_run_id": preflight.workflow_run_id,
                "pairs": (
                    preflight.normalized_request.pair_subset or form_state.pairs
                ),
                "start": preflight.normalized_request.start or form_state.start,
                "end": preflight.normalized_request.end or form_state.end,
                "expected_edge_artifact_mode": (
                    preflight.normalized_request.expected_edge_artifact_mode
                    or form_state.expected_edge_artifact_mode
                ),
                "frozen_ml_artifact_path": (
                    preflight.normalized_request.frozen_ml_artifact_path
                    or form_state.frozen_ml_artifact_path
                ),
                "frozen_ml_artifact_hash": (
                    preflight.normalized_request.frozen_ml_artifact_hash
                    or form_state.frozen_ml_artifact_hash
                ),
                "rolling_ml_window_plan_path": (
                    preflight.normalized_request.rolling_ml_window_plan_path
                    or form_state.rolling_ml_window_plan_path
                ),
                "ml_artifact_freshness_days": (
                    preflight.normalized_request.ml_artifact_freshness_days
                    or form_state.ml_artifact_freshness_days
                ),
                "bml_candidate_sampler_mode": (
                    preflight.normalized_request.bml_candidate_sampler_mode
                    or form_state.bml_candidate_sampler_mode
                ),
            }
        )
        write_backtest_form_state(jobs_root, form_state)
        current_form_state = build_patch6_state(
            state_name="current_form_state",
            normalized_request=preflight.normalized_request,
            request_hash=preflight.request_hash,
            detected_pairs=preflight.detected_pairs,
            active_pairs_after_pruning=preflight.active_pairs_after_pruning,
            status=preflight.inspection_status,
            preview_id=preflight.preview_id,
            output_root_effective=preflight.output_root_effective_preview,
            blockers=preflight.blockers,
        )
        write_current_form_state(jobs_root, current_form_state)
        preview_manifest = _build_preview_manifest(preflight=preflight)
        write_preview_manifest(jobs_root, preview_manifest)
        if preflight.phase_id == PHASE_A1:
            _write_phase_a1_preview_artifacts(
                jobs_root=jobs_root,
                preview_manifest=preview_manifest,
                preflight=preflight,
            )
            _refresh_requested_phase_a1_workflow_manifest(
                jobs_root=jobs_root,
                requested_workflow_run_id=workflow_run_id,
                preflight=preflight,
                preview_manifest=preview_manifest,
            )
        write_source_preview_state(
            jobs_root,
            build_patch6_state(
                state_name="source_preview_state",
                normalized_request=preflight.normalized_request,
                request_hash=preflight.request_hash,
                detected_pairs=preflight.detected_pairs,
                active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                status=preflight.inspection_status,
                preview_id=preflight.preview_id,
                output_root_effective=preflight.output_root_effective_preview,
                blockers=preflight.blockers,
            ),
        )
        if selected_action_name:
            try:
                parsed_action = StrategyLadderControlAction(selected_action_name)
            except ValueError:
                return _redirect(
                    "/backtest",
                    notice=f"Unsupported strategy ladder control action: {selected_action_name}",
                    notice_status="error",
                )
            if intent == "preview":
                return _redirect(
                    "/backtest",
                    notice=(
                        f"Preview updated for {preflight.phase_label}: "
                        f"{preflight.inspection_status}."
                    ),
                    notice_status=("success" if preflight.preview_launchable else "info"),
                )
            if preflight.phase_id == PHASE_A1:
                return _redirect(
                    "/backtest",
                    notice="Phase A1 is preview-only. Use Generate Preview, not Launch.",
                    notice_status="error",
                )
            parsed_job_kind = (
                CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
                if parsed_action in {
                    StrategyLadderControlAction.PHASE_A1_PREVIEW,
                    StrategyLadderControlAction.PHASE_A2_DATA_FACTORY,
                    StrategyLadderControlAction.DATA_FACTORY_DRY_RUN,
                    StrategyLadderControlAction.DATA_FACTORY_SMALL_SCOPE_RUN,
                }
                else (
                    CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY
                    if parsed_action
                    == StrategyLadderControlAction.PHASE_B_ML_LABEL_FACTORY
                    else
                    CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
                    if parsed_action
                    in {
                        StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY,
                        StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY,
                    }
                    else CockpitBacktestJobKind.STRATEGY_LADDER_FIRST_CONTROLLED_RUN
                )
            )
            submitted_preview_id = (preview_id or "").strip()
            submitted_request_hash = (request_hash or "").strip()
            manifest_for_launch = (
                read_preview_manifest(jobs_root, submitted_preview_id)
                if submitted_preview_id and submitted_request_hash
                else preview_manifest
            )
            mismatch_fields = _preview_mismatch_fields(
                manifest=manifest_for_launch,
                preflight=preflight,
                submitted_preview_id=submitted_preview_id,
                submitted_request_hash=submitted_request_hash,
            )
            if mismatch_fields:
                write_launch_request_state(
                    jobs_root,
                    build_patch6_state(
                        state_name="launch_request_state",
                        normalized_request=preflight.normalized_request,
                        request_hash=preflight.request_hash,
                        detected_pairs=preflight.detected_pairs,
                        active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                        status="PREVIEW_LAUNCH_MISMATCH",
                        preview_id=preflight.preview_id,
                        mismatch_fields=mismatch_fields,
                        blockers=("PREVIEW_LAUNCH_MISMATCH",),
                    ),
                )
                return _redirect(
                    "/backtest",
                    notice=(
                        "Preview/launch mismatch blocked: "
                        + ", ".join(mismatch_fields)
                    ),
                    notice_status="error",
                )
            blocked_reason = ""
            if (
                parsed_job_kind == CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY
                and "ML_OVERLAY_UNSUPPORTED_FOR_DATA_FACTORY" in preflight.blockers
            ):
                blocked_reason = "ML_OVERLAY_UNSUPPORTED_FOR_DATA_FACTORY"
            elif manifest_blocker:
                blocked_reason = manifest_blocker
            elif ambiguity_blocker:
                blocked_reason = ambiguity_blocker
            elif not preflight.preview_launchable and preflight.blockers:
                blocked_reason = preflight.blockers[0]
            elif not preflight.preview_launchable:
                blocked_reason = preflight.inspection_status
            workflow_root = _workflow_root_for_request(
                jobs_root=jobs_root,
                workflow_run_id=preflight.workflow_run_id,
                operator_output_root=operator_output_root,
            )
            chain_requested = (
                parsed_action
                in {
                    StrategyLadderControlAction.PHASE_B1_CANDIDATE_DISCOVERY,
                    StrategyLadderControlAction.PHASE_B2_DETAILED_REPLAY,
                }
                and form_state.ml_mode == "ML_MODE_OVERLAY_FROZEN"
                and bool(form_state.selected_features)
                and not _has_authoritative_frozen_artifact(preflight)
            )
            if chain_requested:
                if blocked_reason:
                    write_launch_request_state(
                        jobs_root,
                        build_patch6_state(
                            state_name="launch_request_state",
                            normalized_request=preflight.normalized_request,
                            request_hash=preflight.request_hash,
                            detected_pairs=preflight.detected_pairs,
                            active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                            status="CHAIN_BLOCKED",
                            preview_id=preflight.preview_id,
                            blockers=(blocked_reason,),
                        ),
                    )
                    return _redirect(
                        "/backtest",
                        notice=(
                            "ML feature chain blocked before handoff: "
                            f"{blocked_reason}."
                        ),
                        notice_status="error",
                    )
                blocker_codes = ("BACKTEST_REQUIRES_IA_LAB_FROZEN_ARTIFACT",)
                write_launch_request_state(
                    jobs_root,
                    build_patch6_state(
                        state_name="launch_request_state",
                        normalized_request=preflight.normalized_request,
                        request_hash=preflight.request_hash,
                        detected_pairs=preflight.detected_pairs,
                        active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                        status="CHAIN_BLOCKED",
                        preview_id=preflight.preview_id,
                        blockers=blocker_codes,
                    ),
                )
                write_backtest_ml_chain_state(
                    jobs_root,
                    BacktestMlChainState(
                        status="CHAIN_BLOCKED",
                        created_at=datetime.now(UTC).isoformat(),
                        updated_at=datetime.now(UTC).isoformat(),
                        action_name=preflight.action_name,
                        phase_id=preflight.phase_id,
                        workflow_run_id=preflight.workflow_run_id,
                        preview_id=preflight.preview_id,
                        request_hash=preflight.request_hash,
                        selected_features=tuple(form_state.selected_features),
                        training_timeframe=form_state.training_timeframe,
                        backtest_timeframes=form_state.backtest_timeframes,
                        feature_selection_source="FORM_SELECTED",
                        blockers=blocker_codes,
                        notes=(
                            "IA_LAB_OWNS_ML_DATES_TIMEFRAMES_AND_TRAINING",
                            "BACKTEST_CONSUMES_FROZEN_IA_LAB_ARTIFACT_ONLY",
                        ),
                        frozen_form=form_state,
                    ),
                )
                return _redirect(
                    "/backtest",
                    notice=(
                        "Backtest feature selection requires a frozen IA Lab artifact; "
                        "Backtest will not train ML silently."
                    ),
                    notice_status="error",
                )
                training_window, training_blockers = _derive_backtest_ml_training_window(
                    selected_form=form_state
                )
                resolved_training_blockers = list(training_blockers)
                if not (form_state.klines_path or "").strip():
                    resolved_training_blockers.append(
                        "BACKTEST_FEATURE_TRAINING_REQUIRES_KLINES_ROOT"
                    )
                if training_window is None or resolved_training_blockers:
                    blocker_codes = tuple(dict.fromkeys(resolved_training_blockers))
                    write_launch_request_state(
                        jobs_root,
                        build_patch6_state(
                            state_name="launch_request_state",
                            normalized_request=preflight.normalized_request,
                            request_hash=preflight.request_hash,
                            detected_pairs=preflight.detected_pairs,
                            active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                            status="CHAIN_BLOCKED",
                            preview_id=preflight.preview_id,
                            blockers=blocker_codes,
                        ),
                    )
                    return _redirect(
                        "/backtest",
                        notice=(
                            "ML feature chain blocked: "
                            + ", ".join(blocker_codes)
                        ),
                        notice_status="error",
                    )
                handoff_output_root = (form_state.export_dir or operator_output_root).strip()
                selected_pair = (
                    preflight.normalized_request.pair_subset[0]
                    if preflight.normalized_request.pair_subset
                    else (form_state.pairs[0] if form_state.pairs else "BTCUSDT")
                )
                backtest_lab_form = _build_lab_ml_handoff_form_state(
                    kline_root=form_state.klines_path,
                    b2_run_root=str(
                        _existing_phase_b2_run_root(
                            workflow_root=workflow_root,
                            workflow_run_id=preflight.workflow_run_id,
                        )
                        or ""
                    ),
                    orderbook_root=form_state.orderbook_path,
                    trades_root=form_state.trades_path,
                    metadata_root=form_state.metadata_path,
                    handoff_export_dir=handoff_output_root,
                    pair=selected_pair,
                    selected_pairs=list(preflight.normalized_request.pair_subset),
                    timeframe=form_state.training_timeframe,
                    train_start=str(training_window["train_start"]),
                    train_end=str(training_window["train_end"]),
                    requested_backtest_start=str(
                        training_window["requested_backtest_start"]
                    ),
                    requested_backtest_days=int(
                        training_window["requested_backtest_days"]
                    ),
                    train_days=int(training_window["train_days"]),
                    validation_days=int(training_window["validation_days"]),
                    freshness_days=int(training_window["freshness_days"]),
                    chunk_days=int(training_window["chunk_days"]),
                    calibration_version="strategy_ladder_expected_edge.v1",
                    feature_names=form_state.feature_names,
                    selected_features_csv=form_state.feature_names,
                    selected_features=list(form_state.selected_features),
                    feature_picker_enabled="1",
                    sample_stride_minutes=60,
                    target_horizon_minutes=1,
                    training_seed=5307,
                    max_optuna_trials=0,
                    min_training_rows=210,
                    shap_summary_ref="",
                    signed_by=signed_by,
                    intent="launch",
                )
                governance_entries = discover_lab_feature_governance(
                    backtest_lab_form,
                    registry_path=jobs_root / "feature_promotion_registry.json",
                )
                demoted_override_features = selected_demoted_lab_features(
                    selected_feature_names=tuple(backtest_lab_form.selected_features),
                    governance_entries=governance_entries,
                )
                if demoted_override_features:
                    _logger.warning(
                        "EXPECTED_EDGE_FEATURE_USER_OVERRIDE_DEMOTED pair=%s timeframe=%s features=%s",
                        backtest_lab_form.pair,
                        backtest_lab_form.timeframe,
                        ",".join(demoted_override_features),
                    )
                requested_non_legacy_features = _non_legacy_expected_edge_features(
                    tuple(backtest_lab_form.selected_features)
                )
                if (
                    requested_non_legacy_features
                    and not (backtest_lab_form.b2_run_root or "").strip()
                ):
                    blocker_codes = (
                        "BACKTEST_FEATURE_TRAINING_REQUIRES_B2_REPLAY_ROOT_FOR_NON_LEGACY_FEATURES",
                    )
                    write_lab_ml_handoff_form_state(jobs_root, backtest_lab_form)
                    write_launch_request_state(
                        jobs_root,
                        build_patch6_state(
                            state_name="launch_request_state",
                            normalized_request=preflight.normalized_request,
                            request_hash=preflight.request_hash,
                            detected_pairs=preflight.detected_pairs,
                            active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                            status="CHAIN_BLOCKED",
                            preview_id=preflight.preview_id,
                            blockers=blocker_codes,
                        ),
                    )
                    write_backtest_ml_chain_state(
                        jobs_root,
                        BacktestMlChainState(
                            status="CHAIN_BLOCKED",
                            created_at=datetime.now(UTC).isoformat(),
                            updated_at=datetime.now(UTC).isoformat(),
                            action_name=preflight.action_name,
                            phase_id=preflight.phase_id,
                            workflow_run_id=preflight.workflow_run_id,
                            preview_id=preflight.preview_id,
                            request_hash=preflight.request_hash,
                            selected_features=tuple(form_state.selected_features),
                            training_timeframe=form_state.training_timeframe,
                            feature_selection_source="FORM_SELECTED",
                            blockers=blocker_codes,
                            notes=(
                                "NON_LEGACY_FEATURES_REQUIRE_REPLAY_GROUNDED_B2_ROOT",
                            ),
                            frozen_form=form_state,
                        ),
                    )
                    return _redirect(
                        "/backtest",
                        notice=(
                            "ML feature chain blocked: non-legacy features require a Phase B2 replay root."
                        ),
                        notice_status="error",
                    )
                write_lab_ml_handoff_form_state(jobs_root, backtest_lab_form)
                chain_form_state = form_state.model_copy(
                    update={
                        "ml_mode": "ML_MODE_OFF",
                        "ml_handoff_run_root": "",
                        "frozen_ml_artifact_path": "",
                        "frozen_ml_artifact_hash": "",
                        "rolling_ml_window_plan_path": "",
                    }
                )
                write_backtest_form_state(jobs_root, chain_form_state)
                handoff_record = launch_backtest_job(
                    jobs_root=jobs_root,
                    job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
                    export_dir=Path(backtest_lab_form.kline_root).expanduser(),
                    b2_run_root=(
                        Path(backtest_lab_form.b2_run_root).expanduser()
                        if (backtest_lab_form.b2_run_root or "").strip()
                        else None
                    ),
                    signed_by=signed_by,
                    operator_output_root=handoff_output_root,
                    raw_roots=(Path(backtest_lab_form.kline_root).expanduser(),),
                    pairs=(
                        backtest_lab_form.selected_pairs
                        if backtest_lab_form.selected_pairs
                        else (backtest_lab_form.pair,)
                    ),
                    start=backtest_lab_form.train_start,
                    end=backtest_lab_form.train_end,
                    calibration_version=backtest_lab_form.calibration_version,
                    timeframe=backtest_lab_form.timeframe,
                    requested_backtest_start=backtest_lab_form.requested_backtest_start,
                    requested_backtest_days=backtest_lab_form.requested_backtest_days,
                    train_days=backtest_lab_form.train_days,
                    validation_days=backtest_lab_form.validation_days,
                    freshness_days=backtest_lab_form.freshness_days,
                    chunk_days=backtest_lab_form.chunk_days,
                    feature_names_csv=backtest_lab_form.feature_names,
                    sample_stride_minutes=backtest_lab_form.sample_stride_minutes,
                    target_horizon_minutes=backtest_lab_form.target_horizon_minutes,
                    training_seed=backtest_lab_form.training_seed,
                    max_optuna_trials=backtest_lab_form.max_optuna_trials,
                    min_training_rows=backtest_lab_form.min_training_rows,
                    shap_summary_ref=backtest_lab_form.shap_summary_ref,
                )
                chain_status = (
                    "CHAIN_BLOCKED"
                    if handoff_record.status.value
                    in {"JOB_FAILED", "JOB_BLOCKED", "JOB_CANCELLED", "JOB_KILLED"}
                    else "CHAIN_HANDOFF_PENDING"
                )
                chain_state = BacktestMlChainState(
                    status=chain_status,
                    created_at=datetime.now(UTC).isoformat(),
                    updated_at=datetime.now(UTC).isoformat(),
                    action_name=preflight.action_name,
                    phase_id=preflight.phase_id,
                    workflow_run_id=preflight.workflow_run_id,
                    preview_id=preflight.preview_id,
                    request_hash=preflight.request_hash,
                    selected_features=tuple(chain_form_state.selected_features),
                    training_timeframe=chain_form_state.training_timeframe,
                    feature_selection_source="FORM_SELECTED",
                    handoff_job_id=handoff_record.job_id,
                    handoff_output_root=handoff_record.output_root,
                    blockers=tuple(handoff_record.blockers),
                    notes=(
                        "BACKTEST_FEATURE_SELECTION_TRIGGERED_ML_HANDOFF",
                        "REPLAY_LAUNCH_DEFERRED_UNTIL_FROZEN_ARTIFACT_READY",
                    ),
                    frozen_form=chain_form_state,
                )
                write_backtest_ml_chain_state(jobs_root, chain_state)
                write_launch_request_state(
                    jobs_root,
                    build_patch6_state(
                        state_name="launch_request_state",
                        normalized_request=preflight.normalized_request,
                        request_hash=preflight.request_hash,
                        detected_pairs=preflight.detected_pairs,
                        active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                        status=chain_state.status,
                        preview_id=preflight.preview_id,
                        job_id=handoff_record.job_id,
                        output_root_effective=handoff_record.output_root,
                        blockers=chain_state.blockers,
                    ),
                )
                return _redirect(
                    "/backtest",
                    notice=(
                        f"Blocked ML handoff job {handoff_record.job_id}: "
                        f"{', '.join(handoff_record.blockers)}."
                        if chain_status == "CHAIN_BLOCKED"
                        else (
                            "Launched ML handoff first for selected features; "
                            f"replay will auto-start when handoff job {handoff_record.job_id} is ready."
                        )
                    ),
                    notice_status=("error" if chain_status == "CHAIN_BLOCKED" else "success"),
                )
            record = _launch_strategy_ladder_phase_job(
                jobs_root=jobs_root,
                preflight=preflight,
                export_path=export_path,
                baseline_path=baseline_path,
                raw_manifest_path=raw_manifest_path,
                manifest_blocker=manifest_blocker,
                ambiguity_blocker=ambiguity_blocker,
                allow_broad=allow_broad,
                operator_output_root=operator_output_root,
                signed_by=signed_by,
            )
            write_backtest_ml_chain_state(
                jobs_root,
                BacktestMlChainState(
                    status="CHAIN_NOT_REQUESTED",
                    created_at=datetime.now(UTC).isoformat(),
                    updated_at=datetime.now(UTC).isoformat(),
                    action_name=preflight.action_name,
                    phase_id=preflight.phase_id,
                    workflow_run_id=preflight.workflow_run_id,
                    preview_id=preflight.preview_id,
                    request_hash=preflight.request_hash,
                    frozen_form=form_state,
                ),
            )
            write_launch_request_state(
                jobs_root,
                build_patch6_state(
                    state_name="launch_request_state",
                    normalized_request=preflight.normalized_request,
                    request_hash=preflight.request_hash,
                    detected_pairs=preflight.detected_pairs,
                    active_pairs_after_pruning=preflight.active_pairs_after_pruning,
                    status=record.status.value,
                    preview_id=preflight.preview_id,
                    job_id=record.job_id,
                    output_root_effective=record.output_root,
                    blockers=record.blockers,
                ),
            )
            return _redirect(
                "/backtest",
                notice=(
                    f"Blocked {preflight.phase_label} job {record.job_id}: {', '.join(record.blockers)}."
                    if record.blockers
                    else f"Launched {preflight.phase_label} job {record.job_id}."
                ),
                notice_status=("error" if record.blockers else "success"),
            )
        try:
            parsed_job_kind = CockpitBacktestJobKind(job_kind)
        except ValueError:
            return _redirect(
                "/backtest",
                notice=f"Unsupported backtest job kind: {job_kind}",
                notice_status="error",
            )
        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=parsed_job_kind,
            export_dir=export_path,
            baseline_export_dir=baseline_path,
            signed_by=signed_by,
            operator_output_root=operator_output_root,
            raw_roots=raw_root_paths,
        )
        return _redirect(
            "/backtest",
            notice=f"Launched {record.job_kind.value} job {record.job_id}.",
            notice_status="success",
        )

    @app.post("/backtest/adopt-launch-workflow")
    def backtest_adopt_launch_workflow() -> RedirectResponse:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return _redirect(
                "/backtest",
                notice="Backtest jobs root is not configured.",
                notice_status="error",
            )
        launch_request_state = read_launch_request_state(jobs_root)
        if launch_request_state is None or not launch_request_state.workflow_run_id:
            return _redirect(
                "/backtest",
                notice="No current launch workflow is available to adopt.",
                notice_status="error",
            )
        if launch_request_state.status == "PREVIEW_LAUNCH_MISMATCH":
            return _redirect(
                "/backtest",
                notice="Cannot adopt a workflow from a preview/launch mismatch state.",
                notice_status="error",
            )
        current_form = read_backtest_form_state(jobs_root)
        updated_form = _adopt_launch_state_into_form(
            current_form=current_form,
            launch_state=launch_request_state,
        )
        write_backtest_form_state(jobs_root, updated_form)
        write_current_form_state(
            jobs_root,
            launch_request_state.model_copy(
                update={"state_name": "current_form_state"},
            ),
        )
        return _redirect(
            "/backtest",
            notice=(
                "Current form adopted launch workflow "
                f"{launch_request_state.workflow_run_id}."
            ),
            notice_status="success",
        )

    @app.post("/backtest/cancel")
    def backtest_cancel(
        job_id: str = Form(...),
        operator_reason: str = Form("operator_requested_cancel"),
    ) -> RedirectResponse:
        jobs_root = app.state.paths.backtest_jobs_root
        if jobs_root is None:
            return _redirect(
                "/backtest",
                notice="Backtest jobs root is not configured.",
                notice_status="error",
            )
        status_code, blocker = request_job_cancel(
            jobs_root=jobs_root,
            job_id=job_id.strip(),
            operator_reason=(operator_reason or "operator_requested_cancel").strip(),
        )
        if status_code == "JOB_CANCELLING":
            notice = f"Cancel requested for job {job_id}. Worker will pick it up."
            return _redirect("/backtest", notice=notice, notice_status="success")
        if status_code == "JOB_NOT_RUNNING":
            return _redirect(
                "/backtest",
                notice=f"Job {job_id} is not running.",
                notice_status="error",
            )
        return _redirect(
            "/backtest",
            notice=f"Cancel failed for job {job_id}: {blocker or status_code}.",
            notice_status="error",
        )

    @app.post("/shadow/pairs/apply")
    def shadow_pairs_apply(
        active_pairs: list[str] = Form([]),
        operator_reason: str = Form("study shadow pair universe from cockpit"),
    ) -> RedirectResponse:
        queue_root = app.state.paths.dashboard_command_queue_root
        if queue_root is None:
            return _redirect(
                "/shadow",
                notice="Dashboard command queue root is not configured.",
                notice_status="error",
            )
        pair_selector = read_pair_selector(app.state.paths)
        configured_pairs = pair_selector.configured_pairs
        if not configured_pairs:
            return _redirect(
                "/shadow",
                notice="No governed pair universe is configured yet.",
                notice_status="error",
            )
        requested_active_pairs = tuple(
            pair
            for pair in configured_pairs
            if pair in {
                str(raw_pair).strip().upper()
                for raw_pair in active_pairs
                if str(raw_pair).strip()
            }
        )
        if not requested_active_pairs:
            return _redirect(
                "/shadow",
                notice="Select at least one active pair.",
                notice_status="error",
            )
        runtime = read_runtime_surfaces(
            service_dir=app.state.paths.service_dir,
            queue_root=app.state.paths.dashboard_command_queue_root,
            observability_output_dir=app.state.paths.observability_output_dir,
            backtest_jobs_root=app.state.paths.backtest_jobs_root,
        )
        suspended_pairs = set(
            ()
            if runtime.service_state is None
            else runtime.service_state.dashboard_control_suspended_pairs
        )
        queued_count = 0
        for pair in configured_pairs:
            if pair in requested_active_pairs and pair in suspended_pairs:
                enqueue_pair_command(
                    queue_root=queue_root,
                    command_kind=DashboardGovernedCommandKind.REQUEST_PAIR_RESUME,
                    target_pair=pair,
                    requested_by="cockpit_operator",
                    operator_reason=operator_reason,
                )
                queued_count += 1
            elif pair not in requested_active_pairs and pair not in suspended_pairs:
                enqueue_pair_command(
                    queue_root=queue_root,
                    command_kind=DashboardGovernedCommandKind.SUSPEND_PAIR,
                    target_pair=pair,
                    requested_by="cockpit_operator",
                    operator_reason=operator_reason,
                )
                queued_count += 1
        if queued_count == 0:
            return _redirect(
                "/shadow",
                notice="Active pair set is already aligned with the governed control state.",
                notice_status="info",
            )
        return _redirect(
            "/shadow",
            notice=(
                f"Queued {queued_count} governed pair command(s). "
                f"Target active set: {', '.join(requested_active_pairs)}."
            ),
            notice_status="success",
        )

    @app.get("/api/snapshot")
    def api_snapshot(
        request: Request,
        pair: str | None = None,
    ) -> JSONResponse:
        view_model = _build_vm(request, current_page="overview", selected_pair=pair)
        payload = {key: value for key, value in asdict(view_model).items()}
        return JSONResponse(content=_jsonable(payload))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _jsonable(value: object) -> object:
    from pydantic import BaseModel as _BaseModel

    if isinstance(value, _BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _build_backtest_status_summary(
    records: tuple[object, ...],
) -> dict[str, object]:
    running_statuses = {
        "JOB_CREATED",
        "JOB_RUNNING",
        "JOB_CANCELLING",
    }
    completed_statuses = {
        "JOB_COMPLETED",
        "JOB_COMPLETED_WITH_BLOCKERS",
        "JOB_CANCELLED",
        "JOB_KILLED",
    }
    failed_statuses = {
        "JOB_FAILED",
        "JOB_BLOCKED",
    }
    requested_count = len(records)
    running_count = 0
    completed_count = 0
    failed_count = 0
    latest_status = "not_present"
    for index, record in enumerate(records):
        status_value = getattr(getattr(record, "status", None), "value", "")
        if index == 0 and status_value:
            latest_status = status_value
        if status_value in running_statuses:
            running_count += 1
        elif status_value in completed_statuses:
            completed_count += 1
        elif status_value in failed_statuses:
            failed_count += 1
    return {
        "requested_count": requested_count,
        "running_count": running_count,
        "completed_count": completed_count,
        "failed_count": failed_count,
        "latest_status": latest_status,
    }


def _serialize_backtest_job(record: object | None) -> dict[str, object] | None:
    if record is None:
        return None
    status = getattr(getattr(record, "status", None), "value", "")
    can_cancel = status in {"JOB_CREATED", "JOB_RUNNING", "JOB_CANCELLING"}
    return {
        "job_id": getattr(record, "job_id", ""),
        "job_kind": getattr(getattr(record, "job_kind", None), "value", ""),
        "status": status,
        "can_cancel": can_cancel,
        "pid": getattr(record, "pid", 0),
        "pid_alive": getattr(record, "pid_alive", False),
        "requested_at_iso": getattr(record, "requested_at_iso", ""),
        "started_at_iso": getattr(record, "started_at_iso", ""),
        "finished_at_iso": getattr(record, "finished_at_iso", ""),
        "latest_activity_iso": getattr(record, "latest_activity_iso", ""),
        "duration_seconds": getattr(record, "duration_seconds", None),
        "progress_pct": getattr(record, "progress_pct", 0),
        "eta_minutes": getattr(record, "eta_minutes", 0.0),
        "progress_health_status": getattr(record, "progress_health_status", ""),
        "progress_health_message": getattr(record, "progress_health_message", ""),
        "produced_file_count": getattr(record, "produced_file_count", 0),
        "output_ref_count": getattr(record, "output_ref_count", 0),
        "stdout_log_size_kb": getattr(record, "stdout_log_size_kb", 0.0),
        "stdout_log_path": getattr(record, "stdout_log_path", ""),
        "output_root": getattr(record, "output_root", ""),
        "error_summary": getattr(record, "error_summary", ""),
        "blockers": list(getattr(record, "blockers", ()) or ()),
        "stage_statuses": getattr(record, "stage_statuses", {}) or {},
    }


_ARTIFACT_IMPORT_ACTIONS = {
    "ml": {
        "artifact_kind": DashboardArtifactKind.ML_MODEL_ARTIFACT,
        "command_kind": DashboardGovernedCommandKind.REQUEST_UPLOAD_ML_ARTIFACT,
        "operator_reason": "cockpit_lab_import_ml_artifact",
    },
    "regime": {
        "artifact_kind": DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT
        ),
        "operator_reason": "cockpit_lab_import_regime_artifact",
    },
    "shadow-ml": {
        "artifact_kind": DashboardArtifactKind.ML_MODEL_ARTIFACT,
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT
        ),
        "operator_reason": "cockpit_lab_import_shadow_ml_challenger",
    },
    "shadow-regime": {
        "artifact_kind": DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT,
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT
        ),
        "operator_reason": "cockpit_lab_import_shadow_regime_challenger",
    },
}


_ARTIFACT_EXPORT_ACTIONS = {
    "active-ml": {
        "command_kind": DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
        "operator_reason": "cockpit_lab_export_active_ml_artifact",
    },
    "active-regime": {
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT
        ),
        "operator_reason": "cockpit_lab_export_active_regime_artifact",
    },
    "shadow-ml-comparison": {
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_ML_ARTIFACT_COMPARISON_EVIDENCE
        ),
        "operator_reason": "cockpit_lab_export_shadow_ml_comparison",
    },
    "shadow-regime-comparison": {
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_REGIME_DETECTOR_ARTIFACT_COMPARISON_EVIDENCE
        ),
        "operator_reason": "cockpit_lab_export_shadow_regime_comparison",
    },
    "shadow-verdict": {
        "command_kind": (
            DashboardGovernedCommandKind.REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE
        ),
        "operator_reason": "cockpit_lab_export_shadow_verdict_bundle",
    },
}


__all__ = [
    "create_app",
    "DEFAULT_GRAFANA_URL",
    "DEFAULT_PROMETHEUS_URL",
    "DEFAULT_WELCOME",
]
