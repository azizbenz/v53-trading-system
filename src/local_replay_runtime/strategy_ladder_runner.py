"""Canonical V5.3 Backtest Strategy Ladder runner."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from statistics import NormalDist, median
from time import perf_counter, process_time

from calibration_methods.dsr import (
    DeflatedSharpeRatioError,
    compute_deflated_sharpe_ratio,
)
from calibration_methods.psr import (
    ProbabilisticSharpeRatioError,
    compute_probabilistic_sharpe_ratio,
)
from calibration_methods.bootstrap import infer_stationary_block_length
from local_replay_runtime.capital_profile_builder import (
    CapitalProfileBuildInput,
    build_capital_bucket_profile,
)
from local_replay_runtime.backtest_decision_report_builder import (
    write_backtest_decision_reports,
)
from interface_contracts import (
    ProfileId,
    StrategyClassification,
    build_strategy_ladder_proxy_fidelity_surface,
)
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.capital_profile_contracts import (
    CapitalBucketProfile,
    CapitalProfileBlockedPair,
)
from interface_contracts.promotion_artifact_contracts import (
    EnginePromotionArtifact,
    PairPromotionArtifact,
    SampleSizeSurvivalArtifact,
    StrategyPromotionArtifact,
)
from interface_contracts.strategy_ladder_workflow_support import (
    PHASE_B1,
    PHASE_B2,
    PHASE_STATUS_DISCOVERY_BLOCKED,
    PHASE_STATUS_DISCOVERY_READY,
    PHASE_STATUS_DISCOVERY_SAMPLED,
    PHASE_STATUS_PROOF_BLOCKED,
    PHASE_STATUS_PROMOTION_BLOCKED,
    PHASE_STATUS_REPLAY_READY,
    ensure_workflow_manifest,
    read_workflow_manifest,
    upsert_workflow_phase,
)
from local_replay_runtime.promotion_artifact_builder import (
    ReplayPromotionArtifactBundle,
    SampleSizeSurvivalBuildInput,
    build_replay_promotion_artifact_bundle,
    build_sample_size_survival_artifact,
)
from local_replay_runtime.governed_audit_evidence_index import (
    build_governed_audit_evidence_entry,
    build_governed_audit_evidence_index,
    build_governed_audit_evidence_projection,
)
from local_replay_runtime.replay_metrics_collector import (
    ReplayBookDepthAvailability,
    ReplayCostParityEvidence,
    ReplayFeeProvenance,
    ReplayFillRealismEvidence,
    ReplayImpactProvenance,
    build_replay_metrics_summary,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_execution_contracts import ShadowExecutionSimulatorConfig
from execution_backbone.fee_aware_edge_gate import FeeAwareEdgeGateConfig
from regime_classifier.regime_lite import RegimeLiteThresholds
from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS,
    StrategyLadderB2LabelStoreBuilderRequest,
    build_strategy_ladder_b2_label_store,
)
from local_replay_runtime.strategy_ladder_operator_artifacts import (
    write_strategy_ladder_operator_artifacts,
)
from local_replay_runtime.strategy_ladder_candidate_discovery import (
    apply_strategy_ladder_candidate_budget,
    discover_strategy_ladder_candidates,
    export_strategy_ladder_candidates,
    load_strategy_ladder_candidate_events,
    load_strategy_ladder_candidate_summary,
)
from local_replay_runtime.strategy_ladder_count_semantics import (
    summarize_candidate_count_semantics,
    summarize_replay_count_semantics,
)
from local_replay_runtime.strategy_ladder_complete_enabler_support import (
    StrategyLadderBuild14Application,
    apply_build14_shadow_context,
)
from local_replay_runtime.strategy_ladder_detailed_replay import (
    StrategyLadderDetailedReplayStageResult,
    run_strategy_ladder_detailed_replay,
    run_strategy_ladder_detailed_replay_parallel,
)
from local_replay_runtime.strategy_ladder_parallel import (
    ordered_parallel_map,
    resolve_worker_count,
)
from local_replay_runtime.strategy_ladder_resource_guard import (
    assert_ram_below_hard_limit,
)
from local_replay_runtime.strategy_ladder_economic_provenance import (
    EconomicProvenance,
    ExpectedEdgeModelProtocol,
    compute_economic_provenance,
    expected_edge_backtest_truth_status,
    is_expected_edge_backtest_truth,
)
from local_replay_runtime.strategy_ladder_edge_model_provider import (
    GovernedExpectedEdgeModelLoadResult,
    load_governed_expected_edge_model_artifact,
)
from local_replay_runtime.strategy_ladder_engine_native_preselection import (
    build_strategy_ladder_engine_native_preselection,
)
from local_replay_runtime.strategy_ladder_feature_store import (
    load_strategy_ladder_feature_store,
    parse_time_boundary_to_ms,
)
from local_replay_runtime.strategy_ladder_gate_waterfall_analysis import (
    write_strategy_ladder_gate_waterfall_reports,
)
from local_replay_runtime.strategy_ladder_candidate_trade_semantics_audit import (
    write_strategy_ladder_candidate_trade_semantics_audit,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderReportSummary,
    StrategyLadderRequest,
    StrategyLadderRawWindowManifest,
    StrategyLadderRunManifest,
    deterministic_payload_hash,
)
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    extract_strategy_ladder_raw_windows,
    load_strategy_ladder_raw_window_manifests,
)
from local_replay_runtime.strategy_ladder_replay_performance_profile import (
    StrategyLadderReplayPerformanceProfiler,
)
from local_replay_runtime.strategy_ladder_replay_evidence import (
    build_measured_cost_governance_payload,
    build_measured_slippage_payload,
    build_measured_spread_payload,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from portfolio_minimal.allocation_router.capital_viability import (
    analyze_capital_fragmentation,
)


_BOOK_STATUS_PRIORITY = (
    "BOOK_DEPTH_MISSING",
    "BOOK_DEPTH_STALE",
    "BOOK_TOP_OF_BOOK_ONLY",
    "BOOK_LIMITED_DEPTH_AVAILABLE",
    "BOOK_DEPTH_NOT_PROVEN",
    "BOOK_DEPTH20_AVAILABLE",
)
_ENGINE_NATIVE_PROGRESS_EVERY = 25
_FEE_STATUS_PRIORITY = (
    "FEE_SOURCE_MISSING",
    "FEE_SOURCE_NOT_PROVEN",
    "FEE_SOURCE_ESTIMATED",
    "FEE_SOURCE_EXCHANGE_METADATA",
    "FEE_SOURCE_CONFIGURED",
    "FEE_SOURCE_PROVEN",
)
_IMPACT_STATUS_PRIORITY = (
    "IMPACT_SOURCE_MISSING",
    "IMPACT_SOURCE_NOT_PROVEN",
    "IMPACT_SOURCE_SYNTHETIC",
    "IMPACT_SOURCE_ESTIMATED",
    "IMPACT_SOURCE_TOP_OF_BOOK_PROXY",
    "IMPACT_SOURCE_LIMITED_DEPTH_MODEL",
    "IMPACT_SOURCE_DEPTH20_MODEL",
    "IMPACT_SOURCE_PROVEN",
)
_FILL_STATUS_PRIORITY = (
    "FILL_REALISM_MISSING",
    "FILL_REALISM_NOT_PROVEN",
    "FILL_REALISM_MODEL_ONLY",
    "FILL_REALISM_SYNTHETIC_ONLY",
    "FILL_REALISM_PARTIAL",
    "FILL_REALISM_SHADOW_MEASURED",
    "FILL_REALISM_PROVEN",
)
_PARITY_STATUS_PRIORITY = (
    "REPLAY_LIVE_COST_PARITY_MISSING",
    "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
    "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
    "REPLAY_LIVE_COST_PARITY_PARTIAL",
    "REPLAY_SHADOW_COST_PARITY_PROVEN",
    "REPLAY_LIVE_COST_PARITY_PROVEN",
)
_EXECUTION_LABEL_SOURCE_PRIORITY = (
    "REPLAY_PROXY_EXECUTION",
    "PARTIAL_CANONICAL_EXECUTION",
    "FULL_CANONICAL_EXECUTION",
)
_CAPITAL_PROFILE_TTL = timedelta(days=7)


@dataclass(frozen=True)
class StrategyLadderRunResult:
    run_manifest: StrategyLadderRunManifest
    report_summary: StrategyLadderReportSummary
    capital_profiles: tuple[CapitalBucketProfile, ...]
    engine_promotion_artifacts: tuple[EnginePromotionArtifact, ...]
    pair_promotion_artifacts: tuple[PairPromotionArtifact, ...]
    strategy_promotion_artifacts: tuple[StrategyPromotionArtifact, ...]
    sample_size_survival_artifacts: tuple[SampleSizeSurvivalArtifact, ...]


StrategyLadderProgressCallback = Callable[[StrategyLadderRunManifest], None]


def _load_json_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_jsonl_rows(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and not bool(payload.get("artifact_header")):
                    rows.append(payload)
    except OSError:
        return []
    return rows


def _resolve_data_factory_payloads(
    request: StrategyLadderRequest,
) -> dict[str, object]:
    candidate_roots: list[Path] = []
    if request.silver_index_path is not None:
        candidate_roots.append(request.silver_index_path.resolve().parent)
    candidate_roots.append(request.feature_store_root.resolve().parent)
    candidate_roots.append(request.input_root.resolve())
    if request.parent_workflow_ref:
        workflow_root = Path(request.parent_workflow_ref).resolve().parent
        candidate_roots.append(workflow_root / "phase_a2_data_factory")
    base = next(
        (
            root
            for root in candidate_roots
            if (root / "data_factory_manifest.json").is_file()
            or (root / "silver_index.json").is_file()
            or (root / "gold_feature_manifest.json").is_file()
        ),
        request.input_root.resolve(),
    )
    manifest = _load_json_payload(base / "data_factory_manifest.json")
    raw_source_report = _load_json_payload(base / "raw_source_report.json")
    pair_report = _load_json_payload(base / "pair_universe_report.json")
    quality_report = _load_json_payload(base / "data_quality_report.json")
    silver_index_report = _load_json_payload(base / "silver_index.json")
    gold_manifest = _load_json_payload(base / "gold_feature_manifest.json")
    return {
        "base_root": base.resolve(),
        "manifest": manifest,
        "raw_source_report": raw_source_report,
        "pair_report": pair_report,
        "quality_report": quality_report,
        "silver_index_report": silver_index_report,
        "gold_manifest": gold_manifest,
        "silver_index_path": (
            request.silver_index_path.resolve()
            if request.silver_index_path is not None
            else (base / "silver_index.json").resolve()
        ),
    }


def _resolve_run_raw_source_manifest_path(
    *,
    request: StrategyLadderRequest,
    silver_index_path: Path | None = None,
    data_factory_base_root: Path | None = None,
) -> str:
    if request.raw_source_manifest_path is not None:
        return str(request.raw_source_manifest_path.resolve())

    candidate_roots: list[Path] = []
    if data_factory_base_root is not None:
        candidate_roots.append(data_factory_base_root.resolve())
    if silver_index_path is not None:
        candidate_roots.append(silver_index_path.resolve().parent)
    if request.parent_workflow_ref:
        workflow_root = Path(request.parent_workflow_ref).resolve().parent
        candidate_roots.append(workflow_root / "phase_a2_data_factory")

    for root in candidate_roots:
        manifest_payload = _load_json_payload(root / "data_factory_manifest.json")
        manifest_path = str(manifest_payload.get("raw_source_manifest_path") or "").strip()
        if manifest_path:
            return manifest_path
        candidate_path = root / "raw_source_manifest.json"
        if candidate_path.is_file():
            return str(candidate_path.resolve())
    return ""


def _hash_file_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workflow_phase_id_for_request(request: StrategyLadderRequest) -> str:
    return PHASE_B1 if request.fast_only else PHASE_B2


def _isoformat_or_empty(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return ""


def _workflow_request_hash_for_sync(
    request: StrategyLadderRequest,
    existing_request_hash: str,
) -> str:
    if existing_request_hash:
        return existing_request_hash
    payload = {
        "workflow_run_id": request.workflow_run_id,
        "phase_id": _workflow_phase_id_for_request(request),
        "pairs": request.pairs,
        "engines": request.engines,
        "capital_buckets": request.capital_buckets,
        "timeframes": request.timeframes,
        "start": request.start,
        "end": request.end,
        "ml_mode": request.ml_mode,
        "engine_native_sample_size": request.engine_native_sample_size,
        "candidate_discovery_mode": request.candidate_discovery_mode,
        "candidate_sample_cap": request.candidate_sample_cap,
        "small_scope_enabled": request.small_scope_enabled,
        "full_scan_enabled": request.full_scan_enabled,
        "no_full_scan_enabled": request.no_full_scan_enabled,
    }
    return deterministic_payload_hash(payload)


def _infer_silver_storage_mode_effective(
    silver_index_report_payload: dict[str, object],
    existing_mode: str,
) -> str:
    if existing_mode:
        return existing_mode
    entries = silver_index_report_payload.get("entries")
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            storage_format = str(entry.get("storage_format") or "").strip()
            if storage_format:
                return storage_format
    return "jsonl_debug"


def _infer_silver_exchange_from_index(
    silver_index_report_payload: dict[str, object],
) -> tuple[str | None, str]:
    """Audit 2026-05-13 W1 fix : resoud (exchange, market_type) canonique
    depuis le `silver_index.entries[i].exchange` produit par le data factory.

    C'est la source d'autorite pour le venue routing : le `raw_book_path`
    dans le replay pointe vers les raw_windows extraits (pas le silver
    direct), donc l'auto-detect via path echoue. Resoudre une fois ici au
    demarrage du runner et propager au call site `compute_economic_provenance`.

    Retourne (exchange, market_type). exchange peut etre None si l'index est
    vide ou degrade. market_type defaut "spot".
    """
    entries = silver_index_report_payload.get("entries")
    if not isinstance(entries, list):
        return None, "spot"
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        exchange = str(entry.get("exchange") or "").strip().lower()
        if not exchange:
            continue
        market_type = str(entry.get("market_type") or "spot").strip().lower() or "spot"
        return exchange, market_type
    return None, "spot"


def _workflow_phase_status_from_run_manifest(
    request: StrategyLadderRequest,
    run_manifest: StrategyLadderRunManifest,
) -> str:
    phase_id = _workflow_phase_id_for_request(request)
    if phase_id == PHASE_B1:
        if (
            run_manifest.candidate_export_status == "CANDIDATE_EXPORT_READY"
            and run_manifest.candidate_count > 0
        ):
            if (
                run_manifest.candidate_discovery_cap_status
                == "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
            ):
                return PHASE_STATUS_DISCOVERY_SAMPLED
            return PHASE_STATUS_DISCOVERY_READY
        return PHASE_STATUS_DISCOVERY_BLOCKED

    blocker_codes = set(run_manifest.blocker_codes)
    proof_blockers = {
        "RAW_WINDOW_NOT_PROVEN",
        "RAW_WINDOW_EXTRACTION_FAILED",
        "DETAILED_REPLAY_NOT_PROVEN",
        "NO_EXECUTED_TRADES",
        "SAMPLE_SIZE_SURVIVAL_NOT_PROVEN",
    }
    if (
        run_manifest.raw_window_extraction_status != "RAW_WINDOW_READY"
        or run_manifest.detailed_replay_status != "DETAILED_REPLAY_READY"
        or blocker_codes.intersection(proof_blockers)
    ):
        return PHASE_STATUS_PROOF_BLOCKED
    if run_manifest.promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY":
        return PHASE_STATUS_PROMOTION_BLOCKED
    return PHASE_STATUS_REPLAY_READY


def _workflow_consumed_artifact_refs(
    request: StrategyLadderRequest,
    *,
    data_factory_root: Path,
    candidate_events_source_path: Path | None,
) -> dict[str, str]:
    refs: dict[str, str] = {}
    manifest_path = data_factory_root / "data_factory_manifest.json"
    if manifest_path.is_file():
        refs["phase_a2_data_factory_manifest"] = str(manifest_path.resolve())
    silver_index_path = data_factory_root / "silver_index.json"
    if silver_index_path.is_file():
        refs["phase_a2_silver_index"] = str(silver_index_path.resolve())
    gold_root = data_factory_root / "gold"
    if gold_root.is_dir():
        refs["phase_a2_gold_root"] = str(gold_root.resolve())
    if candidate_events_source_path is not None and candidate_events_source_path.is_file():
        refs["phase_b1_candidate_events"] = str(candidate_events_source_path.resolve())
    return refs


def _workflow_produced_artifact_refs(
    request: StrategyLadderRequest,
    *,
    run_dir: Path,
    fast_candidates_dir: Path,
    reports_dir: Path,
    operator_artifact_refs: dict[str, str],
) -> dict[str, str]:
    refs: dict[str, str] = {}
    for path in (
        run_dir / "run_manifest.json",
        reports_dir / "strategy_ladder_summary.json",
        reports_dir / "strategy_ladder_report.md",
        reports_dir / "profitability_truth_verdict.json",
        reports_dir / "profitability_truth_verdict.md",
        reports_dir / "governed_audit_evidence_index.json",
        reports_dir / "engine_matrix.json",
        reports_dir / "pair_matrix.json",
        reports_dir / "strategy_matrix.json",
        reports_dir / "capital_bucket_matrix.json",
        reports_dir / "backtest_decision_capability_audit.json",
        reports_dir / "backtest_decision_report.json",
        reports_dir / "timeframe_ranking_report.json",
        reports_dir / "feature_ranking_report.json",
        reports_dir / "ml_vs_no_ml_delta_report.json",
        reports_dir / "engine_by_regime_report.json",
        reports_dir / "pair_ranking_report.json",
        reports_dir / "capital_bucket_ranking_report.json",
        reports_dir / "cost_fill_realism_report.json",
        reports_dir / "threshold_near_miss_report.json",
        reports_dir / "backtest_decision_report_final_verdict.json",
        fast_candidates_dir / "candidate_events.jsonl",
        fast_candidates_dir / "candidate_events.parquet",
        fast_candidates_dir / "candidate_events.columns.json",
        fast_candidates_dir / "candidate_events.tabular_manifest.json",
        fast_candidates_dir / "candidate_summary.json",
    ):
        if path.is_file():
            refs[path.name] = str(path.resolve())
    refs.update(operator_artifact_refs)
    return refs


def _workflow_artifact_hashes(artifact_refs: dict[str, str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name, ref in sorted(artifact_refs.items()):
        path = Path(ref)
        if not path.is_file():
            continue
        try:
            hashes[name] = _hash_file_bytes(path)
        except OSError:
            continue
    return hashes


def _build_profitability_truth_verdict(
    *,
    summary: StrategyLadderReportSummary,
    run_manifest: StrategyLadderRunManifest,
) -> dict[str, object]:
    blocker_codes = tuple(
        dict.fromkeys(
            (
                *run_manifest.blocker_codes,
                *summary.blocker_codes,
                *summary.promotion_blockers,
                *summary.execution_fidelity_gap_codes,
                *summary.expected_edge_blocker_codes,
            )
        )
    )
    proxy_blockers: list[str] = []
    proxy_blocker_code_set = {
        "EXPECTED_EDGE_PROXY_BLOCKED",
        "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH",
        "SLIPPAGE_MODEL_PROXY",
        "SPREAD_MODEL_PROXY",
        "FEE_MODEL_PROXY",
        "ADVERSE_SELECTION_PROXY",
        "PARTIAL_FILL_PROXY",
        "REPLAY_PROXY_EXECUTION",
        "LABEL_STORE_RESEARCH_ONLY",
        "LABEL_STORE_PARTIAL_PROXY_EXECUTION",
        "B2_REPLAY_EXPECTED_CE_NET_PROXY",
    }
    proxy_blockers.extend(code for code in blocker_codes if code in proxy_blocker_code_set)
    if summary.expected_edge_proxy_count > 0:
        proxy_blockers.append("EXPECTED_EDGE_PROXY_COUNT_NONZERO")
    if summary.expected_edge_truth_status != "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH":
        proxy_blockers.append(summary.expected_edge_truth_status)
    for field_name, blocker_code in (
        ("execution_label_source", "EXECUTION_LABEL_SOURCE_PROXY"),
        ("fee_model_source", "FEE_MODEL_PROXY"),
        ("spread_model_source", "SPREAD_MODEL_PROXY"),
        ("slippage_model_source", "SLIPPAGE_MODEL_PROXY"),
        ("partial_fill_model_source", "PARTIAL_FILL_PROXY"),
        ("adverse_selection_source", "ADVERSE_SELECTION_PROXY"),
    ):
        value = str(getattr(summary, field_name) or "")
        if value == "REPLAY_PROXY" or value == "REPLAY_PROXY_EXECUTION" or value.endswith("_PROXY"):
            proxy_blockers.append(blocker_code)
    proxy_blockers = list(dict.fromkeys(code for code in proxy_blockers if code))
    executed_trade_count = int(summary.executed_trade_count or run_manifest.executed_trade_count or 0)
    if executed_trade_count <= 0 or "NO_EXECUTED_TRADES" in blocker_codes:
        status = "PROFITABILITY_VERDICT_BLOCKED_NO_EXECUTED_TRADES"
    elif proxy_blockers:
        status = "PROFITABILITY_VERDICT_BLOCKED_PROXY"
    elif executed_trade_count < 50:
        status = "PROFITABILITY_VERDICT_INCONCLUSIVE_LOW_EXECUTIONS"
    elif executed_trade_count < 100:
        status = "PROFITABILITY_VERDICT_DIAGNOSTIC_FRAGILE"
    else:
        status = "PROFITABILITY_VERDICT_PROD_CANDIDATE"
    return {
        "schema_version": "strategy_ladder.profitability_truth_verdict.v1",
        "run_id": summary.run_id,
        "workflow_run_id": summary.workflow_run_id,
        "status": status,
        "profitability_claim_allowed": status == "PROFITABILITY_VERDICT_PROD_CANDIDATE",
        "executed_trade_count": executed_trade_count,
        "minimum_diagnostic_trade_count": 50,
        "minimum_prod_trade_count": 100,
        "proxy_blockers_present": bool(proxy_blockers),
        "proxy_blocker_codes": tuple(proxy_blockers),
        "blocker_codes": blocker_codes,
        "expected_edge_truth_status": summary.expected_edge_truth_status,
        "execution_label_source": summary.execution_label_source,
        "fee_model_source": summary.fee_model_source,
        "spread_model_source": summary.spread_model_source,
        "slippage_model_source": summary.slippage_model_source,
        "label_store_proxy_free_required": True,
        "train_eval_overlap_allowed": False,
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


def _format_profitability_truth_verdict_markdown(payload: dict[str, object]) -> str:
    proxy_blockers = payload.get("proxy_blocker_codes") or ()
    blocker_codes = payload.get("blocker_codes") or ()
    return "\n".join(
        [
            "# Profitability Truth Verdict",
            "",
            f"- run_id: {payload.get('run_id', '')}",
            f"- status: {payload.get('status', '')}",
            f"- profitability_claim_allowed: {payload.get('profitability_claim_allowed', False)}",
            f"- executed_trade_count: {payload.get('executed_trade_count', 0)}",
            f"- proxy_blocker_codes: {', '.join(str(code) for code in proxy_blockers) if proxy_blockers else 'none'}",
            f"- blocker_codes: {', '.join(str(code) for code in blocker_codes) if blocker_codes else 'none'}",
            "",
        ]
    )


def _sync_parent_workflow_phase_record(
    request: StrategyLadderRequest,
    *,
    run_manifest: StrategyLadderRunManifest,
    data_factory_root: Path,
    candidate_events_source_path: Path | None,
    run_dir: Path,
    fast_candidates_dir: Path,
    reports_dir: Path,
    operator_artifact_refs: dict[str, str],
    silver_index_report_payload: dict[str, object],
) -> None:
    if not request.parent_workflow_ref:
        return
    workflow_root = Path(request.parent_workflow_ref).resolve().parent
    phase_id = _workflow_phase_id_for_request(request)
    existing = read_workflow_manifest(workflow_root)
    request_hash = _workflow_request_hash_for_sync(
        request,
        existing.request_hash if existing is not None else "",
    )
    allow_broad_run = (
        existing.allow_broad_run
        if existing is not None
        else (not request.small_scope_enabled and request.full_scan_enabled)
    )
    silver_storage_mode = _infer_silver_storage_mode_effective(
        silver_index_report_payload,
        existing.silver_storage_mode_effective if existing is not None else "",
    )
    ensure_workflow_manifest(
        workflow_root=workflow_root,
        workflow_run_id=request.workflow_run_id or run_manifest.workflow_run_id,
        request_hash=request_hash,
        phase_id=phase_id,
        pairs=request.pairs,
        start=request.start,
        end=request.end,
        ml_mode=request.ml_mode,
        candidate_discovery_mode=run_manifest.candidate_discovery_mode,
        engine_native_sample_size=run_manifest.effective_engine_native_sample_size,
        b1_5_policy_mode=run_manifest.b1_5_policy_mode,
        engine_count=run_manifest.engine_count,
        allow_broad_run=allow_broad_run,
        small_scope_enabled=run_manifest.small_scope_enabled,
        full_scan_enabled=run_manifest.full_scan_enabled,
        no_full_scan_enabled=run_manifest.no_full_scan_enabled,
        silver_storage_mode_requested=(
            existing.silver_storage_mode_requested
            if existing is not None
            else silver_storage_mode
        ),
        silver_storage_mode_effective=silver_storage_mode,
    )
    consumed_artifact_refs = _workflow_consumed_artifact_refs(
        request,
        data_factory_root=data_factory_root,
        candidate_events_source_path=candidate_events_source_path,
    )
    produced_artifact_refs = _workflow_produced_artifact_refs(
        request,
        run_dir=run_dir,
        fast_candidates_dir=fast_candidates_dir,
        reports_dir=reports_dir,
        operator_artifact_refs=operator_artifact_refs,
    )
    artifact_hashes = _workflow_artifact_hashes(produced_artifact_refs)
    upsert_workflow_phase(
        workflow_root=workflow_root,
        workflow_run_id=request.workflow_run_id or run_manifest.workflow_run_id,
        phase_id=phase_id,
        phase_run_id=request.phase_run_id or run_manifest.phase_run_id or request.run_id,
        phase_output_root=request.output_root.resolve(),
        parent_workflow_ref=str(Path(request.parent_workflow_ref).resolve()),
        job_id=request.phase_run_id or request.run_id,
        request_hash=request_hash,
        phase_status=_workflow_phase_status_from_run_manifest(request, run_manifest),
        blocker_codes=run_manifest.blocker_codes,
        error_code="",
        stderr_ref="",
        consumed_artifact_refs=consumed_artifact_refs,
        produced_artifact_refs=produced_artifact_refs,
        artifact_hashes=artifact_hashes,
        phase_started_at=_isoformat_or_empty(run_manifest.created_at),
        phase_completed_at=_isoformat_or_empty(run_manifest.updated_at),
    )


def _strategy_classification_for_engine(engine_id: str) -> StrategyClassification:
    if engine_id == "engine_a":
        return StrategyClassification.A_VARIANT
    if engine_id == "engine_b":
        return StrategyClassification.B_VARIANT
    if engine_id == "engine_c":
        return StrategyClassification.C_CANDIDATE
    if engine_id == "engine_d":
        return StrategyClassification.D_CANDIDATE
    return StrategyClassification.OUT_OF_SCOPE_FOR_V5_3


def _build_replay_manifest(
    *,
    request: StrategyLadderRequest,
    run_id: str,
    strategy_id: str,
    engines: tuple[str, ...],
    pairs: tuple[str, ...],
    record_count: int,
    start_timestamp_ms: int | None,
    end_timestamp_ms: int | None,
) -> ReplayRunManifest:
    classification = (
        _strategy_classification_for_engine(engines[0])
        if len(engines) == 1
        else StrategyClassification.OUT_OF_SCOPE_FOR_V5_3
    )
    timeframe_scope = (
        ",".join(request.timeframes)
        if request.timeframes
        else f"{request.start or 'open'}/{request.end or 'open'}"
    )
    artifact_hash = deterministic_payload_hash(
        {
            "run_id": run_id,
            "strategy_id": strategy_id,
            "engines": engines,
            "pairs": pairs,
            "record_count": record_count,
            "start_timestamp_ms": start_timestamp_ms,
            "end_timestamp_ms": end_timestamp_ms,
        }
    )
    return ReplayRunManifest(
        run_id=run_id,
        strategy_id=strategy_id,
        strategy_version="strategy_ladder.v1",
        strategy_classification=classification,
        lineage_version="strategy_ladder.v1",
        profile_scope=ProfileId.COMPLETE,
        engine_scope=engines,
        tested_pairs=pairs,
        dataset_manifest_id=f"{request.run_id}-strategy-ladder",
        timeframe_scope=timeframe_scope,
        feature_set_version="strategy_ladder.feature_store.v1",
        transform_set_version="strategy_ladder.transform.v1",
        formula_set_version="strategy_ladder.formula.v1",
        scoring_version="strategy_ladder.scoring.v1",
        regime_version="strategy_ladder.regime.v1",
        risk_policy_version="strategy_ladder.risk.v1",
        cost_model_version="strategy_ladder.cost.v1",
        performance_mode="research_fast_mode",
        artifact_schema_version="v1",
        artifact_hash=artifact_hash,
        clock_id=f"strategy-ladder-{request.run_id}",
        start_timestamp_ms=start_timestamp_ms or 0,
        end_timestamp_ms=end_timestamp_ms or (start_timestamp_ms or 0),
        tick_count=max(record_count, 1),
        record_count=max(record_count, 1),
    )


def _select_status(values: tuple[str, ...], priority: tuple[str, ...], default: str) -> str:
    unique = {value for value in values if value}
    if not unique:
        return default
    for status in priority:
        if status in unique:
            return status
    return sorted(unique)[0]


def _build_fee_provenance(results: tuple[StrategyLadderBucketReplayResult, ...]) -> ReplayFeeProvenance:
    status = _select_status(
        tuple(result.fee_source_status for result in results),
        _FEE_STATUS_PRIORITY,
        "FEE_SOURCE_NOT_PROVEN",
    )
    return ReplayFeeProvenance(fee_source_status=status)


def _build_impact_provenance(results: tuple[StrategyLadderBucketReplayResult, ...]) -> ReplayImpactProvenance:
    status = _select_status(
        tuple(result.impact_source_status for result in results),
        _IMPACT_STATUS_PRIORITY,
        "IMPACT_SOURCE_NOT_PROVEN",
    )
    levels = [
        result.parity_payload.get("impact_depth_level_used")
        for result in results
        if result.parity_payload.get("impact_depth_level_used") is not None
    ]
    depth_level = max(int(level) for level in levels) if levels else None
    return ReplayImpactProvenance(
        impact_source_status=status,
        impact_depth_level=depth_level,
    )


def _build_book_depth_availability(results: tuple[StrategyLadderBucketReplayResult, ...]) -> ReplayBookDepthAvailability:
    status = _select_status(
        tuple(result.book_depth_source_status for result in results),
        _BOOK_STATUS_PRIORITY,
        "BOOK_DEPTH_NOT_PROVEN",
    )
    levels = [
        result.parity_payload.get("book_depth_levels")
        for result in results
        if result.parity_payload.get("book_depth_levels") is not None
    ]
    level = min(int(item) for item in levels) if levels else None
    return ReplayBookDepthAvailability(
        book_depth_available=None if status == "BOOK_DEPTH_NOT_PROVEN" else status != "BOOK_DEPTH_MISSING",
        book_depth_levels=level,
        book_depth_source_status=status,
        impact_depth_level_used=level,
        impact_depth_readiness_status=_select_status(
            tuple(result.impact_depth_readiness_status for result in results),
            (
                "BOOK_DEPTH_STALE",
                "MICRO_LIVE_BLOCKED_BY_DEPTH",
                "TOP_OF_BOOK_PROXY_ONLY",
                "LIMITED_DEPTH_PARTIAL",
                "BOOK_DEPTH_NOT_PROVEN",
                "DEPTH20_AVAILABLE",
            ),
            "BOOK_DEPTH_NOT_PROVEN",
        ),
        shadow_extension_required=any(
            bool(result.parity_payload.get("shadow_extension_required", True))
            for result in results
        ),
        shadow_extension_reason=_select_status(
            tuple(
                str(result.parity_payload.get("shadow_extension_reason") or "")
                for result in results
            ),
            (
                "MICRO_LIVE_BLOCKED_BY_DEPTH",
                "BOOK_DEPTH_STALE",
                "SHADOW_EXTENDED_REQUIRED",
                "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF",
                "SHADOW_STANDARD_30D",
            ),
            "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF",
        ),
        minimum_shadow_days_required=max(
            (
                int(value)
                for value in (
                    result.parity_payload.get("minimum_shadow_days_required")
                    for result in results
                )
                if value is not None
            ),
            default=None,
        ),
        shadow_extension_status=_select_status(
            tuple(
                str(result.parity_payload.get("shadow_extension_status") or "")
                for result in results
            ),
            (
                "MICRO_LIVE_BLOCKED_BY_DEPTH",
                "SHADOW_DIAGNOSTIC_ONLY",
                "SHADOW_EXTENDED_60D",
                "SHADOW_EXTENDED_45D",
                "SHADOW_STANDARD_30D",
            ),
            "MICRO_LIVE_BLOCKED_BY_DEPTH",
        ),
    )


def _rate(values: tuple[bool, ...]) -> float | None:
    if not values:
        return None
    return round(sum(1 for value in values if value) / len(values), 6)


def _build_fill_realism(results: tuple[StrategyLadderBucketReplayResult, ...]) -> ReplayFillRealismEvidence:
    fill_status = _select_status(
        tuple(result.fill_realism_status for result in results),
        _FILL_STATUS_PRIORITY,
        "FILL_REALISM_NOT_PROVEN",
    )
    no_fill_rate = _rate(tuple(result.no_fill_flag for result in results))
    partial_fill_rate = _rate(tuple(result.partial_fill_flag for result in results))
    observed_ratios = tuple(
        0.0 if result.no_fill_flag else (1.0 - (result.size_reduction_rate or 0.0))
        for result in results
    )
    fill_ratio_observed = (
        round(sum(observed_ratios) / len(observed_ratios), 6)
        if observed_ratios
        else None
    )
    return ReplayFillRealismEvidence(
        fill_realism_status=fill_status,
        fill_source_status=(
            "FILL_SOURCE_SHADOW_TELEMETRY"
            if fill_status == "FILL_REALISM_SHADOW_MEASURED"
            else "FILL_SOURCE_MODEL_ONLY"
        ),
        fill_model_name="strategy_ladder_candidate_window_replay",
        fill_model_version="v1",
        fill_ratio_observed=fill_ratio_observed,
        partial_fill_rate_observed=partial_fill_rate,
        no_fill_rate_observed=no_fill_rate,
        synthetic_fill_flag=fill_status in {"FILL_REALISM_MODEL_ONLY", "FILL_REALISM_SYNTHETIC_ONLY"},
        measured_fill_flag=fill_status in {"FILL_REALISM_PROVEN", "FILL_REALISM_SHADOW_MEASURED"},
        fill_ratio_source="candidate_window_replay",
    )


def _derive_live_engine_parity_status(
    *,
    fee_model_source: str,
    spread_model_source: str,
    slippage_model_source: str,
    partial_fill_model_source: str,
    adverse_selection_source: str,
    order_type_selection_source: str,
    venue_constraints_source: str,
    execution_fidelity_gap_codes: tuple[str, ...],
) -> str:
    """W3 (2026-05-30) — derive `live_engine_parity_status` from shadow simulator
    aggregated outputs.

    Per V5.3 doctrine, the manifest field `live_engine_parity_status` has been
    stuck at "NOT_PROVEN" because no code computed it from the shadow
    simulator results. This helper closes that gap by inspecting the 7
    canonical model_source fields + execution_fidelity_gap_codes.

    Returns:
      - "PROVEN_NO_FIDELITY_GAP" : all 7 sources canonical AND zero gap codes
      - "PROVEN_PARTIAL_FIDELITY" : at least 1 source canonical but gap codes
        remain (shadow proved part of the chain but not all)
      - "NOT_PROVEN" : zero canonical sources OR all REPLAY_PROXY (shadow
        did not run or produced no parity evidence)
    """

    sources = (
        fee_model_source,
        spread_model_source,
        slippage_model_source,
        partial_fill_model_source,
        adverse_selection_source,
        order_type_selection_source,
        venue_constraints_source,
    )
    canonical_count = sum(
        1 for s in sources if str(s or "").upper().startswith("CANONICAL_")
    )
    if canonical_count == 0:
        return "NOT_PROVEN"
    if canonical_count == len(sources) and not execution_fidelity_gap_codes:
        return "PROVEN_NO_FIDELITY_GAP"
    return "PROVEN_PARTIAL_FIDELITY"


def _build_cost_parity(results: tuple[StrategyLadderBucketReplayResult, ...]) -> ReplayCostParityEvidence:
    status = _select_status(
        tuple(result.cost_parity_status for result in results),
        _PARITY_STATUS_PRIORITY,
        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
    )
    parity_payloads = tuple(result.parity_payload for result in results)
    execution_label_source = _select_status(
        tuple(
            str(payload.get("execution_label_source") or "")
            for payload in parity_payloads
        ),
        _EXECUTION_LABEL_SOURCE_PRIORITY,
        "REPLAY_PROXY_EXECUTION",
    )
    def _source(field_name: str) -> str:
        values = tuple(str(payload.get(field_name) or "") for payload in parity_payloads)
        has_proxy = any(value == "REPLAY_PROXY" for value in values)
        has_non_proxy = any(value and value != "REPLAY_PROXY" for value in values)
        if has_proxy and has_non_proxy:
            return "CANONICAL_OR_PROXY"
        return _select_status(
            values,
            ("CANONICAL_OR_PROXY", "REPLAY_PROXY"),
            "REPLAY_PROXY",
        )

    gap_codes: list[str] = []
    for payload in parity_payloads:
        gap_codes.extend(str(code) for code in (payload.get("execution_fidelity_gap_codes") or ()))
    return ReplayCostParityEvidence(
        cost_parity_status=status,
        execution_label_source=execution_label_source,
        fee_model_source=_source("fee_model_source"),
        spread_model_source=_source("spread_model_source"),
        slippage_model_source=_source("slippage_model_source"),
        partial_fill_model_source=_source("partial_fill_model_source"),
        adverse_selection_source=_source("adverse_selection_source"),
        order_type_selection_source=_source("order_type_selection_source"),
        venue_constraints_source=_source("venue_constraints_source"),
        execution_fidelity_gap_codes=tuple(dict.fromkeys(gap_codes)),
        replay_cost_components=("expected_cost", "realized_cost", "fill_ratio", "depth_status"),
        shadow_cost_components=("expected_cost", "realized_cost", "fill_ratio"),
        live_cost_components=(),
        parity_sample_count=len(results),
    )


def _promotion_fidelity_blockers(
    *,
    candidate_truth_status: str,
    expected_edge_truth_status: str,
    economic_constants_provenance: str,
    execution_fidelity_gap_codes: tuple[str, ...],
    statistical_validation_status: str = "STATISTICAL_VALIDATION_NOT_PROVEN",
    statistical_validation_blocker_codes: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers: list[str] = []
    if candidate_truth_status != "CANDIDATE_ENGINE_NATIVE_READY":
        blockers.append(candidate_truth_status)
    if expected_edge_truth_status != "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH":
        blockers.append(expected_edge_truth_status)
    if economic_constants_provenance != "FULLY_MEASURED":
        blockers.append(economic_constants_provenance)
    if statistical_validation_status != "STATISTICAL_VALIDATION_READY":
        blockers.append(statistical_validation_status)
    blockers.extend(
        str(code) for code in statistical_validation_blocker_codes if str(code)
    )
    blockers.extend(str(code) for code in execution_fidelity_gap_codes if str(code))
    return tuple(dict.fromkeys(code for code in blockers if code))


def _derive_promotion_artifact_status(
    *,
    engine_artifact_count: int,
    pair_artifact_count: int,
    strategy_artifact_count: int,
    promotion_fidelity_blockers: tuple[str, ...],
) -> str:
    if engine_artifact_count and pair_artifact_count and strategy_artifact_count:
        if promotion_fidelity_blockers:
            return "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
        return "PROMOTION_ARTIFACTS_READY"
    if engine_artifact_count or pair_artifact_count or strategy_artifact_count:
        return "PROMOTION_ARTIFACTS_PARTIAL"
    return "PROMOTION_ARTIFACTS_NOT_PROVEN"


def _strategy_ids_from_results(results: tuple[StrategyLadderBucketReplayResult, ...]) -> tuple[str, ...]:
    return tuple(sorted({result.strategy_id for result in results if result.strategy_id}))


def _strategy_records_for_scope(
    results: tuple[StrategyLadderBucketReplayResult, ...],
    dtrs: tuple[DTRRecord, ...],
    strategy_id: str,
) -> tuple[DTRRecord, ...]:
    selected_ids = {
        str(result.dtr_record.get("dtr_id") or "")
        for result in results
        if result.strategy_id == strategy_id
    }
    return tuple(
        record
        for record in dtrs
        if record.dtr_id in selected_ids
    )


def _build_strategy_bundle(
    *,
    request: StrategyLadderRequest,
    strategy_id: str,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
    bucket_dtrs: tuple[DTRRecord, ...],
    candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
) -> ReplayPromotionArtifactBundle:
    start_ts = min((result.timestamp_ms for result in bucket_results), default=0)
    end_ts = max((result.timestamp_ms for result in bucket_results), default=start_ts)
    engines = tuple(sorted({result.engine_id for result in bucket_results}))
    pairs = tuple(sorted({result.pair for result in bucket_results}))
    manifest = _build_replay_manifest(
        request=request,
        run_id=request.run_id,
        strategy_id=strategy_id,
        engines=engines or request.engines,
        pairs=pairs or request.pairs,
        record_count=max(len(bucket_dtrs), 1),
        start_timestamp_ms=start_ts,
        end_timestamp_ms=end_ts,
    )
    metrics_summary = build_replay_metrics_summary(
        bucket_dtrs,
        total_opportunities=max(len(bucket_results), len(bucket_dtrs), 1),
        initial_capital=max(request.capital_buckets) if request.capital_buckets else None,
        fee_provenance=_build_fee_provenance(bucket_results),
        impact_provenance=_build_impact_provenance(bucket_results),
        book_depth_availability=_build_book_depth_availability(bucket_results),
        fill_realism=_build_fill_realism(bucket_results),
        cost_parity=_build_cost_parity(bucket_results),
    )
    return build_replay_promotion_artifact_bundle(
        run_manifest=manifest,
        metrics_summary=metrics_summary,
        dtr_records=bucket_dtrs,
        bucket_results=bucket_results,
        candidate_events=candidate_events,
        input_data_hash=manifest.artifact_hash,
    )


def _capital_profile_for_bucket(
    *,
    request: StrategyLadderRequest,
    capital_bucket: int,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
    bucket_dtrs: tuple[DTRRecord, ...],
) -> CapitalBucketProfile:
    if not bucket_results or not bucket_dtrs:
        created_at = datetime.now(tz=UTC)
        return build_capital_bucket_profile(
            CapitalProfileBuildInput(
                capital_bucket=capital_bucket,
                initial_capital=float(capital_bucket),
                usable_sizing_capital=float(capital_bucket),
                capital_source_status="CAPITAL_SOURCE_NOT_PROVEN",
                pair_universe=request.pairs,
                max_active_pairs=None,
                record_count=0,
                candidate_count=0,
                promotion_status="CAPITAL_BUCKET_BLOCKED_BY_BACKTEST",
                promotion_blockers=("BLOCKED_BY_BACKTEST",),
                input_data_hash=deterministic_payload_hash(
                    {"bucket": capital_bucket, "run_id": request.run_id}
                ),
                method_version_hash="strategy_ladder_runner.v1",
                run_id=request.run_id,
                strategy_ladder_manifest_ref=str((request.run_dir / "run_manifest.json").resolve()),
                execution_fidelity_status="REPLAY_PROXY_EXECUTION",
                execution_fidelity_gap_codes=(),
                created_at=created_at,
                expires_at=created_at + _CAPITAL_PROFILE_TTL,
            )
        )

    fee_provenance = _build_fee_provenance(bucket_results)
    impact_provenance = _build_impact_provenance(bucket_results)
    book_depth = _build_book_depth_availability(bucket_results)
    fill_realism = _build_fill_realism(bucket_results)
    cost_parity = _build_cost_parity(bucket_results)
    metrics_summary = build_replay_metrics_summary(
        bucket_dtrs,
        total_opportunities=len(bucket_results),
        initial_capital=float(capital_bucket),
        fee_provenance=fee_provenance,
        impact_provenance=impact_provenance,
        book_depth_availability=book_depth,
        fill_realism=fill_realism,
        cost_parity=cost_parity,
    )
    bucket_manifest = _build_replay_manifest(
        request=request,
        run_id=f"{request.run_id}-bucket-{capital_bucket}",
        strategy_id=f"capital_bucket_{capital_bucket}",
        engines=tuple(sorted({result.engine_id for result in bucket_results})),
        pairs=tuple(sorted({result.pair for result in bucket_results})),
        record_count=max(len(bucket_dtrs), 1),
        start_timestamp_ms=min(result.timestamp_ms for result in bucket_results),
        end_timestamp_ms=max(result.timestamp_ms for result in bucket_results),
    )
    bucket_bundle = build_replay_promotion_artifact_bundle(
        run_manifest=bucket_manifest,
        metrics_summary=metrics_summary,
        dtr_records=bucket_dtrs,
        bucket_results=bucket_results,
        input_data_hash=bucket_manifest.artifact_hash,
    )
    all_pairs = tuple(sorted({result.pair for result in bucket_results}))
    viable_pairs = tuple(
        sorted(
            {
                result.pair
                for result in bucket_results
                if result.min_notional_viable is not False
            }
        )
    )
    pair_universe = viable_pairs or all_pairs
    pair_result_map: dict[str, list[StrategyLadderBucketReplayResult]] = {}
    for result in bucket_results:
        pair_result_map.setdefault(result.pair, []).append(result)

    planned_notionals = tuple(
        result.planned_notional
        for result in bucket_results
        if result.planned_notional is not None and result.planned_notional > 0.0
    )
    median_notional = float(median(planned_notionals)) if planned_notionals else 0.0
    if median_notional > 0.0:
        provisional_max_active_pairs = max(
            1,
            min(
                len(all_pairs),
                int(float(capital_bucket) // max(median_notional, 1.0)),
            ),
        )
    else:
        provisional_max_active_pairs = max(1, min(len(all_pairs), 1))
    fragmentation = analyze_capital_fragmentation(
        capital_bucket=capital_bucket,
        candidate_pair_count=len(all_pairs),
        allocated_notionals=planned_notionals,
        max_active_pairs=provisional_max_active_pairs,
    )
    allowed_pairs: list[str] = []
    blocked_pairs: list[CapitalProfileBlockedPair] = []
    for pair_artifact in bucket_bundle.pair_promotion_artifacts:
        pair_results = pair_result_map.get(pair_artifact.pair, [])
        planned_notional = next(
            (item.planned_notional for item in pair_results if item.planned_notional is not None),
            None,
        )
        min_notional = next(
            (item.min_notional for item in pair_results if item.min_notional is not None),
            None,
        )
        if pair_artifact.promotion_status == "PAIR_ALLOWED":
            allowed_pairs.append(pair_artifact.pair)
            continue
        blocked_pairs.append(
            CapitalProfileBlockedPair(
                pair=pair_artifact.pair,
                status=pair_artifact.promotion_status,
                reason_codes=pair_artifact.promotion_blockers or (pair_artifact.promotion_status,),
                planned_notional=planned_notional,
                min_notional=min_notional,
                metadata={
                    "capital_bucket": capital_bucket,
                    "executed_only_net_return_status": pair_artifact.executed_only_net_return_status,
                    "true_drawdown_status": pair_artifact.true_net_equity_drawdown_status,
                },
            )
        )
    min_notional_block_rate = round(
        sum(
            1
            for result in bucket_results
            if result.min_notional_viable is False
        )
        / len(bucket_results),
        6,
    )
    bucket_sample = next(
        (
            artifact
            for artifact in bucket_bundle.sample_size_survival_artifacts
            if artifact.scope == "capital_bucket" and artifact.id == str(capital_bucket)
        ),
        None,
    )
    size_reduction_values = tuple(
        value
        for value in (result.size_reduction_rate for result in bucket_results)
        if value is not None
    )
    size_reduction_rate = (
        round(sum(size_reduction_values) / len(size_reduction_values), 6)
        if size_reduction_values
        else None
    )
    total_records = max(metrics_summary.total_records, 1)
    created_at = datetime.now(tz=UTC)
    return build_capital_bucket_profile(
        CapitalProfileBuildInput(
            capital_bucket=capital_bucket,
            initial_capital=float(capital_bucket),
            usable_sizing_capital=float(capital_bucket),
            reserve_buffer=0.0,
            capital_source_status="BACKTEST_SCENARIO_FIXED_BUCKET",
            pair_universe=pair_universe,
            allowed_pairs=tuple(sorted(dict.fromkeys(allowed_pairs))),
            blocked_pairs=tuple(blocked_pairs),
            max_active_pairs=fragmentation.recommended_max_active_pairs or provisional_max_active_pairs,
            record_count=metrics_summary.total_records,
            candidate_count=metrics_summary.total_records,
            selected_count=metrics_summary.selected_count,
            executed_count=metrics_summary.executed_count,
            reduced_count=metrics_summary.reduced_count,
            no_fill_count=metrics_summary.no_fill_count,
            hard_blocked_count=metrics_summary.hard_blocked_count,
            rejected_count=metrics_summary.rejected_count,
            min_notional_block_rate=min_notional_block_rate,
            capital_fragmentation_rate=fragmentation.fragmentation_rate,
            size_reduction_rate=size_reduction_rate,
            pair_universe_too_wide_status=fragmentation.pair_universe_too_wide_status,
            expected_ce_net=metrics_summary.ce_net,
            executed_only_net_return=metrics_summary.executed_only_net_return,
            executed_only_net_return_status=metrics_summary.executed_only_net_return_status,
            true_net_equity_max_drawdown=metrics_summary.true_net_equity_max_drawdown,
            true_net_equity_drawdown_status=metrics_summary.true_net_equity_drawdown_status,
            fee_source_status=metrics_summary.fee_source_status,
            impact_source_status=metrics_summary.impact_source_status,
            fill_realism_status=metrics_summary.fill_realism_status,
            cost_parity_status=metrics_summary.cost_parity_status,
            cost_model_completeness_status=metrics_summary.cost_model_completeness_status,
            book_depth_source_status=metrics_summary.book_depth_source_status,
            impact_depth_readiness_status=metrics_summary.impact_depth_readiness_status,
            execution_rate=round(metrics_summary.executed_count / total_records, 6),
            partial_fill_rate=round(metrics_summary.reduced_count / total_records, 6),
            no_fill_rate=round((metrics_summary.no_fill_count or 0) / total_records, 6),
            sample_size_survival_status=(
                bucket_sample.sample_size_survival_status
                if bucket_sample is not None
                else "SAMPLE_SIZE_NOT_PROVEN"
            ),
            input_data_hash=deterministic_payload_hash(
                [result.candidate_id for result in bucket_results]
            ),
            method_version_hash="strategy_ladder_runner.v1",
            run_id=request.run_id,
            strategy_ladder_manifest_ref=str((request.run_dir / "run_manifest.json").resolve()),
            execution_fidelity_status=metrics_summary.execution_label_source,
            execution_fidelity_gap_codes=metrics_summary.execution_fidelity_gap_codes,
            created_at=created_at,
            expires_at=created_at + _CAPITAL_PROFILE_TTL,
        )
    )


def _write_promotion_payloads(
    root: Path,
    *,
    run_id: str,
    engine_artifacts: tuple[EnginePromotionArtifact, ...],
    pair_artifacts: tuple[PairPromotionArtifact, ...],
    strategy_artifacts: tuple[StrategyPromotionArtifact, ...],
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...],
) -> None:
    for artifact in engine_artifacts:
        path = root / "engine_promotion" / artifact.engine_id / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, artifact.model_dump(mode="json"))
    for artifact in pair_artifacts:
        path = root / "pair_promotion" / artifact.pair / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, artifact.model_dump(mode="json"))
    for artifact in strategy_artifacts:
        path = root / "strategy_promotion" / str(artifact.strategy_id) / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, artifact.model_dump(mode="json"))
    for artifact in sample_artifacts:
        path = root / "sample_size_survival" / artifact.scope / artifact.id / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, artifact.model_dump(mode="json"))


def _stage_final_status(
    *,
    request: StrategyLadderRequest,
    feature_store_status: str,
    candidate_export_status: str,
    raw_window_status: str,
    detailed_replay_status: str,
    capital_profile_count: int,
    promotion_artifact_count: int,
    executed_trade_count: int = -1,
    detailed_replay_record_count: int = -1,
    statistical_validation_status: str = "STATISTICAL_VALIDATION_NOT_PROVEN",
) -> str:
    # Audit 2026-05-06: gate ajoutée pour bloquer la promotion d'un run
    # qui n'a produit AUCUN trade exécuté (cas typique du proxy
    # COMPAT_FEATURE_DISCOVERY qui aboutit à 100% de PHANTOM
    # "economically_absurd"). Sentinelle -1 = caller legacy, comportement
    # historique préservé pour la rétro-compatibilité des tests.
    if feature_store_status == "FEATURE_STORE_MISSING":
        return "STRATEGY_LADDER_BLOCKED_BY_FEATURE_STORE"
    if request.dry_run or request.fast_only:
        return "STRATEGY_LADDER_READY_TO_RUN"
    if raw_window_status == "RAW_WINDOW_NOT_PROVEN":
        return "STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS"
    if detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN":
        return "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA"
    if capital_profile_count == 0 or promotion_artifact_count == 0:
        return "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA"
    if (
        executed_trade_count == 0
        and detailed_replay_record_count > 0
    ):
        return "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES"
    if (
        executed_trade_count > 0
        and detailed_replay_record_count > 0
        and statistical_validation_status != "STATISTICAL_VALIDATION_READY"
    ):
        return "STRATEGY_LADDER_BLOCKED_BY_STATISTICAL_VALIDATION"
    if raw_window_status == "RAW_WINDOW_PARTIAL" or detailed_replay_status == "DETAILED_REPLAY_PARTIAL":
        return "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE"
    if candidate_export_status != "CANDIDATE_EXPORT_READY":
        return "STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA"
    return "STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED"


def _is_temporal_candidate_budget_mode(candidate_discovery_mode: str) -> bool:
    return str(candidate_discovery_mode or "").strip().upper() in {
        "TEMPORAL_STRATIFIED",
        "TEMPORAL_STRATIFIED_SAMPLE_BUDGET",
    }


def _is_full_discovery_uncapped(request: StrategyLadderRequest) -> bool:
    return (
        str(request.candidate_discovery_mode or "").strip().upper() == "FULL_DISCOVERY"
        and bool(request.full_scan_enabled)
        and int(request.candidate_sample_cap or 0) == 0
    )


def _effective_candidate_sample_cap(request: StrategyLadderRequest) -> int:
    if _is_full_discovery_uncapped(request):
        return 0
    requested_cap = max(int(request.candidate_sample_cap or 0), 0)
    if requested_cap > 0:
        return requested_cap
    return max(int(request.engine_native_sample_size or 0), 0)


def _candidate_pair_count_for_cap(
    *,
    request: StrategyLadderRequest,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
) -> int:
    pairs = {
        str(pair).strip().upper()
        for pair in request.pairs
        if str(pair).strip()
    }
    pairs.update(
        str(event.pair).strip().upper()
        for event in candidate_events
        if str(event.pair).strip()
    )
    return max(len(pairs), 1)


def _candidate_sample_cap_total(
    *,
    effective_sample_cap: int,
    engine_count: int,
    pair_count: int,
    candidate_discovery_mode: str,
) -> int:
    if effective_sample_cap <= 0:
        return 0
    if _is_temporal_candidate_budget_mode(candidate_discovery_mode):
        return effective_sample_cap * engine_count * pair_count
    return effective_sample_cap * engine_count


def _candidate_cap_formula(
    *,
    effective_sample_cap: int,
    engine_count: int,
    pair_count: int,
    candidate_discovery_mode: str,
) -> str:
    if effective_sample_cap <= 0:
        return "uncapped"
    if _is_temporal_candidate_budget_mode(candidate_discovery_mode):
        return (
            f"{pair_count} pairs x {engine_count} engines x "
            f"{effective_sample_cap} (temporal_stratified/day)"
        )
    return f"{engine_count} engines x {effective_sample_cap}"


def _feature_pairs_from_rows(rows: tuple[object, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(getattr(row, "pair", "") or "").strip().upper()
                for row in rows
                if str(getattr(row, "pair", "") or "").strip()
            }
        )
    )


def _count_executed_trades(
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> int:
    """Compte les records dont l'execution_state vaut EXECUTED ou REDUCED
    avec une notional non-nul. Utilisé par la gate de promotion."""
    return sum(
        1
        for result in bucket_results
        if _enum_value(result.execution_state).lower() in {"executed", "reduced"}
        and (
            (result.executed_notional is not None and result.executed_notional > 0.0)
            or (result.reduced_notional is not None and result.reduced_notional > 0.0)
        )
    )


@dataclass(frozen=True)
class _StatisticalValidationResult:
    status: str
    observation_count: int
    trial_count: int
    benchmark_sharpe: float
    acceptance_floor: float
    sample_sharpe: float | None = None
    psr: float | None = None
    dsr: float | None = None
    stationary_block_length: int = 1
    effective_sample_size: float | None = None
    min_trl_required: float | None = None
    min_trl_satisfied: bool = False
    psr_passes_floor: bool = False
    dsr_passes_floor: bool = False
    blocker_codes: tuple[str, ...] = ()


def _compute_min_trl_required(
    *,
    sample_sharpe: float,
    benchmark_sharpe: float,
    skewness: float,
    kurtosis: float,
    acceptance_floor: float,
) -> float | None:
    if (
        not math.isfinite(sample_sharpe)
        or not math.isfinite(benchmark_sharpe)
        or not math.isfinite(skewness)
        or not math.isfinite(kurtosis)
        or not (0.0 < acceptance_floor < 1.0)
        or sample_sharpe <= benchmark_sharpe
    ):
        return None
    sharpe_gap = sample_sharpe - benchmark_sharpe
    if sharpe_gap <= 0.0:
        return None
    inner = 1.0 - (skewness * sample_sharpe) + (((kurtosis - 1.0) / 4.0) * sample_sharpe**2)
    if not math.isfinite(inner) or inner <= 0.0:
        return None
    z_score = NormalDist().inv_cdf(acceptance_floor)
    required = 1.0 + ((inner * (z_score**2)) / (sharpe_gap**2))
    if not math.isfinite(required) or required <= 0.0:
        return None
    return required


def _compute_statistical_validation_result(
    *,
    request: StrategyLadderRequest,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
    benchmark_sharpe: float = 0.0,
    acceptance_floor: float = 0.95,
) -> _StatisticalValidationResult:
    proven_returns = tuple(
        float(result.executed_only_net_return)
        for result in bucket_results
        if result.executed_only_net_return is not None
        and result.executed_only_net_return_status == "EXECUTED_NET_RETURN_PROVEN"
        and math.isfinite(float(result.executed_only_net_return))
    )
    trial_seams = {
        (result.pair, result.engine_id, result.strategy_id)
        for result in bucket_results
        if result.pair and result.engine_id and result.strategy_id
    }
    timeframe_multiplier = max(len(request.timeframes), 1)
    trial_count = max(len(trial_seams) * timeframe_multiplier, 1)
    observation_count = len(proven_returns)
    if observation_count < 3:
        return _StatisticalValidationResult(
            status="STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS",
            observation_count=observation_count,
            trial_count=trial_count,
            benchmark_sharpe=benchmark_sharpe,
            acceptance_floor=acceptance_floor,
            effective_sample_size=float(observation_count),
            blocker_codes=("STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS",),
        )
    try:
        psr_result = compute_probabilistic_sharpe_ratio(
            proven_returns,
            benchmark_sharpe=benchmark_sharpe,
            acceptance_floor=acceptance_floor,
        )
        dsr_result = compute_deflated_sharpe_ratio(
            proven_returns,
            trial_count=trial_count,
            acceptance_floor=acceptance_floor,
        )
    except (ProbabilisticSharpeRatioError, DeflatedSharpeRatioError, ValueError):
        return _StatisticalValidationResult(
            status="STATISTICAL_VALIDATION_INVALID_RETURNS",
            observation_count=observation_count,
            trial_count=trial_count,
            benchmark_sharpe=benchmark_sharpe,
            acceptance_floor=acceptance_floor,
            blocker_codes=("STATISTICAL_VALIDATION_INVALID_RETURNS",),
        )
    stationary_block_length = max(infer_stationary_block_length(proven_returns), 1)
    effective_sample_size = observation_count / float(stationary_block_length)
    min_trl_required = _compute_min_trl_required(
        sample_sharpe=psr_result.sample_sharpe,
        benchmark_sharpe=benchmark_sharpe,
        skewness=psr_result.skewness,
        kurtosis=psr_result.kurtosis,
        acceptance_floor=acceptance_floor,
    )
    min_trl_satisfied = (
        min_trl_required is not None and effective_sample_size >= min_trl_required
    )
    blocker_codes: list[str] = []
    if not psr_result.passes_floor:
        blocker_codes.append("STATISTICAL_VALIDATION_PSR_BELOW_FLOOR")
    if not dsr_result.passes_floor:
        blocker_codes.append("STATISTICAL_VALIDATION_DSR_BELOW_FLOOR")
    if min_trl_required is None:
        blocker_codes.append("STATISTICAL_VALIDATION_MINTRL_NOT_COMPUTABLE")
    elif not min_trl_satisfied:
        blocker_codes.append("STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED")
    return _StatisticalValidationResult(
        status=(
            "STATISTICAL_VALIDATION_READY"
            if not blocker_codes
            else (
                "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED"
                if (
                    "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED" in blocker_codes
                    and "STATISTICAL_VALIDATION_PSR_BELOW_FLOOR" not in blocker_codes
                    and "STATISTICAL_VALIDATION_DSR_BELOW_FLOOR" not in blocker_codes
                )
                else "STATISTICAL_VALIDATION_BELOW_FLOOR"
            )
        ),
        observation_count=observation_count,
        trial_count=trial_count,
        benchmark_sharpe=benchmark_sharpe,
        acceptance_floor=acceptance_floor,
        sample_sharpe=psr_result.sample_sharpe,
        psr=psr_result.psr,
        dsr=dsr_result.dsr,
        stationary_block_length=stationary_block_length,
        effective_sample_size=effective_sample_size,
        min_trl_required=min_trl_required,
        min_trl_satisfied=min_trl_satisfied,
        psr_passes_floor=psr_result.passes_floor,
        dsr_passes_floor=dsr_result.passes_floor,
        blocker_codes=tuple(blocker_codes),
    )


@dataclass(frozen=True)
class _EngineNativeCandidateMaterialization:
    candidate_events: tuple[StrategyLadderCandidateEvent, ...]
    candidate_discovery_status: str
    engine_native_status: str
    engine_native_records_built: int
    engine_native_runner_invocation_count: int
    expected_edge_proxy_count: int
    expected_edge_governed_count: int
    blocker_codes: tuple[str, ...] = ()


def _enum_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "")


def _coerce_float(value: object, default: float = 0.0) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return coerced


def _payload_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    raw = payload.get(key)
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(part for part in raw.split("|") if part)
    if isinstance(raw, (list, tuple, set)):
        return tuple(str(part) for part in raw if str(part))
    return (str(raw),)


def _merge_codes(*parts: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            code
            for part in parts
            for code in part
            if str(code).strip()
        )
    )


def _planned_notional_from_payload(payload: dict[str, object]) -> float:
    for key in ("planned_notional", "final_size", "candidate_size"):
        value = _coerce_float(payload.get(key), 0.0)
        if value > 0.0:
            return value
    return 0.0


def _expected_cost_from_provenance(provenance: EconomicProvenance) -> float:
    return (
        provenance.spread_bps
        + provenance.slippage_bps * 1.15
        + provenance.latency_penalty_bps
    ) / 10_000.0


def _is_causal_engine_edge_proxy(provenance: str | None) -> bool:
    value = str(provenance or "").strip().upper()
    return value.startswith("PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE")


def _engine_input_expected_gain_source_status(
    provenance: EconomicProvenance,
    *,
    ml_mode: str,
) -> str:
    if is_expected_edge_backtest_truth(provenance.expected_edge_provenance):
        return "ENGINE_INPUT_EDGE_GOVERNED_BACKTEST_TRUTH"
    if (
        str(ml_mode or "").strip().upper() == "ML_MODE_OFF"
        and _is_causal_engine_edge_proxy(provenance.expected_edge_provenance)
    ):
        return "ENGINE_INPUT_EDGE_CAUSAL_PROXY_DIAGNOSTIC_ML_OFF"
    if str(ml_mode or "").strip().upper() == "ML_MODE_OFF":
        return "ENGINE_INPUT_EDGE_ZEROED_NOT_CAUSAL"
    return "ENGINE_INPUT_EDGE_ZEROED_EXPECTED_EDGE_NOT_GOVERNED"


def _engine_input_expected_gain_from_provenance(
    provenance: EconomicProvenance,
    *,
    ml_mode: str,
) -> float:
    status = _engine_input_expected_gain_source_status(provenance, ml_mode=ml_mode)
    if status in {
        "ENGINE_INPUT_EDGE_GOVERNED_BACKTEST_TRUTH",
        "ENGINE_INPUT_EDGE_CAUSAL_PROXY_DIAGNOSTIC_ML_OFF",
    }:
        return max(0.0, float(provenance.expected_edge_bps or 0.0) / 10_000.0)
    return 0.0


def _apply_b2_measured_cost_governance(
    *,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
    provenance: EconomicProvenance,
    planned_notional: float,
) -> EconomicProvenance:
    measured_spread = build_measured_spread_payload(
        window_manifest=window,
        decision_timestamp_ms=candidate.resolved_timestamp_ms,
    )
    measured_slippage = build_measured_slippage_payload(
        candidate=candidate,
        window_manifest=window,
        planned_notional=planned_notional,
        decision_timestamp_ms=candidate.resolved_timestamp_ms,
    )
    cost_governance = build_measured_cost_governance_payload(
        measured_spread=measured_spread,
        measured_slippage=measured_slippage,
        fee_bps=provenance.fee_bps,
        fee_source_status=provenance.fee_provenance,
        latency_penalty_bps=provenance.latency_penalty_bps,
        latency_source_status=provenance.latency_provenance,
    )
    spread_bps = provenance.spread_bps
    spread_provenance = provenance.spread_provenance
    measured_spread_bps = cost_governance.get("spread_bps_measured")
    if isinstance(measured_spread_bps, (int, float)):
        spread_bps = float(measured_spread_bps)
        spread_provenance = str(
            cost_governance.get("spread_provenance_for_payload") or provenance.spread_provenance
        )
    elif str(cost_governance.get("expected_cost_block_reason") or "").strip():
        spread_bps = 0.0
        spread_provenance = "DEFAULT_BY_BOOK_STATUS"

    slippage_bps = provenance.slippage_bps
    slippage_provenance = provenance.slippage_provenance
    measured_slippage_bps = cost_governance.get("slippage_bps_measured")
    if isinstance(measured_slippage_bps, (int, float)):
        slippage_bps = float(measured_slippage_bps)
        slippage_provenance = str(
            cost_governance.get("slippage_provenance_for_payload")
            or provenance.slippage_provenance
        )
    elif str(cost_governance.get("expected_cost_block_reason") or "").strip():
        slippage_bps = 0.0
        slippage_provenance = "DEFAULT_TO_CALIBRATE"

    measurement_warnings = tuple(provenance.measurement_warnings)
    block_reason = str(cost_governance.get("expected_cost_block_reason") or "").strip()
    if block_reason and block_reason not in measurement_warnings:
        measurement_warnings = (*measurement_warnings, block_reason)
    return EconomicProvenance(
        expected_edge_bps=provenance.expected_edge_bps,
        expected_edge_provenance=provenance.expected_edge_provenance,
        spread_bps=spread_bps,
        spread_provenance=spread_provenance,
        slippage_bps=slippage_bps,
        slippage_provenance=slippage_provenance,
        latency_penalty_bps=provenance.latency_penalty_bps,
        latency_provenance=provenance.latency_provenance,
        fee_bps=provenance.fee_bps,
        fee_provenance=provenance.fee_provenance,
        measurement_warnings=measurement_warnings,
        expected_edge_model_status=provenance.expected_edge_model_status,
        expected_edge_model_artifact_hash=provenance.expected_edge_model_artifact_hash,
        expected_edge_model_feature_hash=provenance.expected_edge_model_feature_hash,
        measured_cost_governance=cost_governance,
    )


def _expected_edge_model_feature_maps(
    candidate: StrategyLadderCandidateEvent,
) -> tuple[dict[str, object], dict[str, object]]:
    payload = dict(candidate.compatibility_payload or {})
    raw_feature_values = payload.get("feature_values")
    feature_values = (
        dict(raw_feature_values)
        if isinstance(raw_feature_values, dict)
        else {}
    )
    # Keep runtime inference on the same governed feature contract as the
    # B2 label-store builder. Without this hoist, F16-C fields can be present
    # in the compatibility payload yet remain invisible to frozen-artifact
    # inference, causing false missing-feature blocks in backtest.
    for key in _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS:
        if key in feature_values:
            continue
        raw_value = payload.get(key)
        if raw_value in (None, ""):
            continue
        feature_values[key] = raw_value
    route_features: dict[str, object] = {
        "route_raw_score": _coerce_float(payload.get("raw_score"), 0.0),
        "route_penalized_score": _coerce_float(payload.get("penalized_score"), 0.0),
        "route_final_score": _coerce_float(payload.get("final_score"), 0.0),
        "route_expected_edge_bps": _coerce_float(payload.get("expected_edge_bps"), 0.0),
        "route_spread_bps": _coerce_float(payload.get("spread_bps"), 0.0),
        "route_slippage_bps": _coerce_float(payload.get("slippage_bps"), 0.0),
        "route_latency_penalty_bps": _coerce_float(
            payload.get("latency_penalty_bps"),
            0.0,
        ),
        "route_fill_ratio": _coerce_float(payload.get("fill_ratio"), 1.0),
        "route_ranking_position": _coerce_float(payload.get("ranking_position"), 0.0),
        "route_candidate_size": _coerce_float(payload.get("candidate_size"), 0.0),
        "route_final_size": _coerce_float(payload.get("final_size"), 0.0),
    }
    return feature_values, route_features


def _expected_edge_model_reference_at(
    *,
    created_at: datetime,
    end_ms: int | None,
) -> datetime:
    """Evaluate frozen ML artifact freshness at the replay boundary, not wall clock."""

    if end_ms is None:
        return created_at
    return datetime.fromtimestamp(end_ms / 1000.0, tz=UTC)


def _economic_provenance_for_candidate(
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
    *,
    expected_edge_model: ExpectedEdgeModelProtocol | None = None,
    expected_edge_model_required: bool = False,
    expected_edge_model_load_status: str = "",
    silver_exchange: str | None = None,
    silver_market_type: str = "spot",
) -> EconomicProvenance:
    payload = dict(candidate.compatibility_payload or {})
    feature_values, route_features = _expected_edge_model_feature_maps(candidate)
    base_provenance = compute_economic_provenance(
        timestamp_ms=candidate.resolved_timestamp_ms,
        book_status=(
            window.book_depth_source_status
            if window is not None
            else str(payload.get("book_depth_source_status") or "BOOK_DEPTH_NOT_PROVEN")
        ),
        pair=candidate.pair,
        timeframe=candidate.timeframe,
        raw_book_path=window.raw_book_path if window is not None else None,
        raw_trade_path=window.raw_trade_path if window is not None else None,
        raw_ohlcv_path=window.raw_ohlcv_path if window is not None else None,
        expected_edge_model=expected_edge_model,
        expected_edge_model_required=expected_edge_model_required,
        expected_edge_model_load_status=expected_edge_model_load_status,
        expected_edge_feature_values=feature_values,
        expected_edge_route_features=route_features,
        silver_exchange=silver_exchange,
        silver_market_type=silver_market_type,
    )
    return _apply_b2_measured_cost_governance(
        candidate=candidate,
        window=window,
        provenance=base_provenance,
        planned_notional=_planned_notional_from_payload(payload),
    )


def _engine_output_reason_codes(output: object | None) -> tuple[str, ...]:
    if output is None:
        return ()
    return tuple(
        _enum_value(code)
        for code in (getattr(output, "reason_codes", ()) or ())
        if _enum_value(code)
    )


def _engine_output_no_trade_reasons(output: object | None) -> tuple[str, ...]:
    if output is None:
        return ()
    return tuple(
        _enum_value(code)
        for code in (getattr(output, "no_trade_reasons", ()) or ())
        if _enum_value(code)
    )


def _engine_output_payload(output: object | None) -> dict[str, object]:
    if output is None:
        return {}
    if hasattr(output, "model_dump"):
        dumped = output.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {"value": dumped}
    return {"value": str(output)}


def _extract_engine_d_first_episode_context(
    payload: dict[str, object],
) -> dict[str, object] | None:
    first_episode_fields = (
        "origin_context_id",
        "origin_trade_id",
        "link_type",
        "first_episode_id",
        "first_episode_engine_id",
        "first_episode_close_reason",
        "consecutive_stop_count",
        "last_stop_at_ns",
        "last_fresh_a_detection_at_ns",
        "anti_revenge_state",
        "prior_trade_quality",
        "duplication_overlap_with_engine_a",
        "marginal_portfolio_gain",
        "covered_share_by_engine_a",
        "concentration_headroom",
        "reentry_lateness",
        "structure_reformed_detected",
        "reentry_anchor_price",
    )
    context = {
        field: payload[field]
        for field in first_episode_fields
        if field in payload and payload[field] not in (None, "", (), [], {})
    }
    return context or None


def _build14_reader_observed_value(
    build14_application: StrategyLadderBuild14Application | None,
    *,
    reader_name: str,
) -> float | None:
    if build14_application is None:
        return None
    snapshots = build14_application.shadow_report.model_dump(mode="json").get("snapshots") or ()
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        if str(snapshot.get("reader_name") or "") != reader_name:
            continue
        try:
            return float(snapshot.get("observed_value"))
        except (TypeError, ValueError):
            continue
    return None


def _selected_engine_payload_fields(
    *,
    candidate_payload: dict[str, object],
    engine_input_payload: dict[str, object],
    native_output: dict[str, object],
    build14_application: StrategyLadderBuild14Application | None,
) -> dict[str, object]:
    feature_values = (
        dict(candidate_payload.get("feature_values"))
        if isinstance(candidate_payload.get("feature_values"), dict)
        else {}
    )
    selected: dict[str, object] = {}
    for key in (
        "cumulative_ofi",
        "queue_pressure",
        "vpin",
        "kyle_lambda",
        "realized_vol_current",
        "realized_vol_at_break",
        "entry_price",
        "breakout_level",
        "range_low",
        "range_high",
        "first_episode_id",
        "first_episode_engine_id",
        "first_episode_close_reason",
        "anti_revenge_state",
        "history_score",
        "marginal_value_score",
        "reentry_lateness",
        "concentration_headroom",
        "origin_context_id",
        "origin_trade_id",
        "link_type",
    ):
        for source in (native_output, engine_input_payload):
            if key in source and source[key] not in (None, "", (), [], {}):
                selected[key] = source[key]
                break
    if "fragility_score" in feature_values and "fragility_score" not in selected:
        selected["fragility_score"] = feature_values["fragility_score"]
    if "false_breakout_context" in feature_values and "false_breakout_context" not in selected:
        selected["false_breakout_context"] = feature_values["false_breakout_context"]
    micro_edge_exit_governor = _build14_reader_observed_value(
        build14_application,
        reader_name="micro_edge_exit_governor",
    )
    if micro_edge_exit_governor is not None:
        selected["micro_edge_exit_governor"] = micro_edge_exit_governor
    micro_edge_entry_timing = _build14_reader_observed_value(
        build14_application,
        reader_name="micro_edge_entry_timing_layer",
    )
    if micro_edge_entry_timing is not None:
        selected["micro_edge_entry_timing"] = micro_edge_entry_timing
    execution_fragility_score = _build14_reader_observed_value(
        build14_application,
        reader_name="execution_fragility_score",
    )
    if execution_fragility_score is not None and "fragility_score" not in selected:
        selected["fragility_score"] = execution_fragility_score
    return selected


def _native_production_decision_state(decision: str, target_state: str) -> str:
    canonical_states = {
        "not_evaluated",
        "evaluated",
        "hard_blocked",
        "rejected_ranking",
        "selected",
        "reduced",
        "phantom",
        "executed",
    }
    normalized = (decision or "").strip().lower()
    if normalized in canonical_states:
        return normalized
    if normalized in {"emit", "trade", "selected"}:
        return "selected"
    if normalized in {"no_trade", "reject", "rejected", "skip", "blocked"}:
        return "hard_blocked"
    return target_state if target_state in canonical_states else "evaluated"


# Patch F16-B (2026-05-21) — extraction des scalaires microstructure canoniques
# V5.3 (VPIN, OFI, queue_pressure) depuis un bridge result. Backward-compat :
# accepte n'importe quel objet ayant les attributs `vpin_record`, `ofi_record`,
# `queue_pressure_record` ; retourne None si absent. Source des records :
# `engine_native_adapter.py:586-630` (compute_vpin/_ofi/_queue_pressure).
def _extract_bridge_microstructure_scalars(
    bridge_or_result: object | None,
) -> dict[str, float | None]:
    scalars: dict[str, float | None] = {
        "vpin": None,
        "cumulative_ofi": None,
        "queue_pressure": None,
        "kyle_lambda": None,
        "realized_vol_current": None,
        "realized_vol_at_break": None,
    }
    if bridge_or_result is None:
        return scalars
    def _record_value(record: object | None) -> float | None:
        if record is None:
            return None
        try:
            return float(getattr(record, "value"))
        except (TypeError, ValueError, AttributeError):
            return None

    def _payload_value(key: str) -> float | None:
        for attr_name in (
            "engine_c_partial_input_payload",
            "engine_b_partial_input_payload",
            "engine_d_partial_input_payload",
        ):
            raw_payload = getattr(bridge_or_result, attr_name, None)
            if not isinstance(raw_payload, dict):
                continue
            value = _coerce_float(raw_payload.get(key), default=float("nan"))
            if value == value:
                return value
        return None

    vpin_record = getattr(bridge_or_result, "vpin_record", None)
    scalars["vpin"] = _record_value(vpin_record)
    ofi_record = getattr(bridge_or_result, "ofi_record", None)
    scalars["cumulative_ofi"] = _record_value(ofi_record)
    queue_record = getattr(bridge_or_result, "queue_pressure_record", None)
    scalars["queue_pressure"] = _record_value(queue_record)
    kyle_record = getattr(bridge_or_result, "kyle_lambda_record", None)
    scalars["kyle_lambda"] = _record_value(kyle_record)
    realized_current_record = getattr(bridge_or_result, "realized_vol_current_record", None)
    if realized_current_record is None:
        realized_current_record = getattr(bridge_or_result, "realized_kernel_vol_record", None)
    scalars["realized_vol_current"] = _record_value(realized_current_record)
    realized_break_record = getattr(bridge_or_result, "realized_vol_at_break_record", None)
    scalars["realized_vol_at_break"] = _record_value(realized_break_record)
    for key in tuple(scalars):
        if scalars[key] is None:
            scalars[key] = _payload_value(key)
    if scalars["realized_vol_at_break"] is None:
        # For non-breakout engines the canonical bridge only owns a current
        # realized-vol record. It is measured at the decision window and is the
        # closest governed replay equivalent to the F16 at-break volatility.
        scalars["realized_vol_at_break"] = scalars["realized_vol_current"]
    return scalars


def _extract_engine_d_governance_scalars(
    *sources: dict[str, object],
) -> dict[str, float | None]:
    scalars: dict[str, float | None] = {
        "history_score": None,
        "marginal_value_score": None,
        "reentry_lateness": None,
        "concentration_headroom": None,
    }
    for key in tuple(scalars):
        for source in sources:
            if key not in source:
                continue
            value = _coerce_float(source.get(key))
            if value is not None:
                scalars[key] = value
                break
    return scalars


def _extract_build14_observed_values(
    build14_application: StrategyLadderBuild14Application | None,
) -> dict[str, float | None]:
    return {
        "micro_edge_exit_governor_observed": _build14_reader_observed_value(
            build14_application,
            reader_name="micro_edge_exit_governor",
        ),
        "micro_edge_entry_timing_observed": _build14_reader_observed_value(
            build14_application,
            reader_name="micro_edge_entry_timing_layer",
        ),
    }


def _extract_anti_revenge_one_hot(
    *sources: dict[str, object],
) -> dict[str, bool | None]:
    state = ""
    for source in sources:
        raw_value = str(source.get("anti_revenge_state") or "").strip().lower()
        if raw_value:
            state = raw_value
            break
    mapping = {
        "active": {
            "anti_revenge_state__active": True,
            "anti_revenge_state__cooling": False,
            "anti_revenge_state__idle": False,
        },
        "cooling": {
            "anti_revenge_state__active": False,
            "anti_revenge_state__cooling": True,
            "anti_revenge_state__idle": False,
        },
        "idle": {
            "anti_revenge_state__active": False,
            "anti_revenge_state__cooling": False,
            "anti_revenge_state__idle": True,
        },
    }
    return mapping.get(
        state,
        {
            "anti_revenge_state__active": None,
            "anti_revenge_state__cooling": None,
            "anti_revenge_state__idle": None,
        },
    )


def _extract_latency_penalty_bps(
    native_output: dict[str, object],
    compatibility_payload: dict[str, object],
) -> float | None:
    return _coerce_float(
        native_output.get("latency_penalty_bps")
        if native_output.get("latency_penalty_bps") is not None
        else compatibility_payload.get("latency_penalty_bps")
    )


def _materialize_native_candidate_event(
    *,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
    economic_provenance: EconomicProvenance,
    builder_status: str,
    builder_warnings: tuple[str, ...],
    builder_provenance: str,
    engine_output: object | None,
    engine_input_payload: dict[str, object],
    build14_application: StrategyLadderBuild14Application | None,
    records_built: int,
    runner_invoked: bool,
    bridge_microstructure_scalars: dict[str, float | None] | None = None,
    ml_mode: str = "ML_MODE_OFF",
) -> StrategyLadderCandidateEvent:
    payload = dict(candidate.compatibility_payload or {})
    decision = _enum_value(getattr(engine_output, "decision", "not_invoked"))
    is_emit = decision == "emit"
    edge_truth_status = expected_edge_backtest_truth_status(
        economic_provenance.expected_edge_provenance
    )
    edge_is_truth = is_expected_edge_backtest_truth(
        economic_provenance.expected_edge_provenance
    )
    cost_governance = dict(economic_provenance.measured_cost_governance or {})
    cost_block_reason = str(cost_governance.get("expected_cost_block_reason") or "").strip()
    cost_usage_break_even = str(
        cost_governance.get("cost_source_used_for_break_even") or ""
    ).strip()
    reason_codes = _engine_output_reason_codes(engine_output)
    no_trade_reasons = _engine_output_no_trade_reasons(engine_output)
    hard_block_reasons = _payload_tuple(payload, "hard_block_reasons")
    lower_engine_id = str(candidate.engine_id).strip().lower()
    engine_history_reason_set = {
        str(code).strip().lower()
        for code in (*reason_codes, *no_trade_reasons, *hard_block_reasons)
        if str(code).strip()
    }
    # Patch P0 #1 + #2 + P1 #1 (2026-05-30) — 3-bucket split per audit run
    # 31bdfa55481f6d8f. Previously `native_blockers` mixed 3 categories
    # (hard execution / promotion / diagnostic) into hard_block_reasons,
    # misleading the operator dashboard. Now split cleanly :
    #
    #   - `native_blockers`     = REAL execution hard-block reasons only
    #                             (ENGINE_NATIVE_NO_TRADE, engine-specific
    #                             history_weak, etc.)
    #   - `promotion_blockers_local` = blocks PROMOTION but allows execution
    #                                  (cost_block_reason, edge proxy in
    #                                  ML_MODE_OFF, etc.)
    #   - `diagnostic_status_local`  = INFORMATIONAL, not blocking
    #                                  (B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1)
    native_blockers: tuple[str, ...] = ()
    promotion_blockers_local: list[str] = []
    diagnostic_status_local: list[str] = []

    if not runner_invoked:
        # P0 #1 fix : B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1 is DIAGNOSTIC info
        # ("decision reused from B1, no re-evaluation requested"), NOT a hard block.
        # Previously it was injected into hard_block_reasons → polluted 100% of
        # records and misled operator into thinking pipeline broken.
        diagnostic_status_local.append("B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1")
    elif not is_emit:
        # ENGINE_NATIVE_NO_TRADE = real execution hard block (engine refused trade)
        native_blockers = ("ENGINE_NATIVE_NO_TRADE",)

    edge_truth_is_selection_gate = str(ml_mode or "").strip().upper() != "ML_MODE_OFF"
    profitability_blockers: tuple[str, ...] = ()
    if not edge_is_truth:
        # Always promotion blocker (audit-grade truth requires governed edge)
        profitability_blockers = _merge_codes(
            list(profitability_blockers),
            [
                "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
                "EXPECTED_EDGE_PROXY_BLOCKED",
                "FEE_AWARE_EDGE_PROXY_BLOCKED",
                "BREAK_EVEN_PROXY_BLOCKED",
            ],
        )
    if not edge_is_truth and edge_truth_is_selection_gate:
        # Only HARD block when ML mode active (gate active) AND edge not truth
        native_blockers = _merge_codes(
            list(native_blockers),
            [
                "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
                "EXPECTED_EDGE_PROXY_BLOCKED",
                "FEE_AWARE_EDGE_PROXY_BLOCKED",
                "BREAK_EVEN_PROXY_BLOCKED",
            ],
        )
    if cost_block_reason:
        # P1 #1 fix : cost_block_reason = PROMOTION blocker (can execute with
        # cost proxy estimate, but cannot promote as backtest truth). Was
        # incorrectly injected as hard_block.
        promotion_blockers_local.append(cost_block_reason)
    if lower_engine_id == "engine_d" and (
        "history_weak" in engine_history_reason_set
        or "engine_d.no_trade.history_weak" in engine_history_reason_set
    ):
        # Real engine-D hard block (no closed_episode_source = cannot trade)
        native_blockers = _merge_codes(
            list(native_blockers),
            ["ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE"],
        )

    # Merge per-row promotion_blockers into the manifest-level profitability_blockers
    if promotion_blockers_local:
        profitability_blockers = _merge_codes(
            list(profitability_blockers),
            promotion_blockers_local,
        )

    target_state = (
        "selected"
        if is_emit
        and (edge_is_truth or not edge_truth_is_selection_gate)
        and cost_usage_break_even == "measured"
        else "hard_blocked"
    )
    native_output = _engine_output_payload(engine_output)
    native_output_hash = deterministic_payload_hash(native_output)
    engine_input_hash = deterministic_payload_hash(engine_input_payload)
    raw_score = _coerce_float(getattr(engine_output, "raw_score", payload.get("raw_score")), 0.0)
    penalized_score = _coerce_float(
        getattr(engine_output, "penalized_score", raw_score),
        raw_score,
    )
    final_score = penalized_score

    compatibility_notes = tuple(
        note
        for note in _payload_tuple(payload, "compatibility_notes")
        if note not in {"COMPAT_FEATURE_DISCOVERY", "NOT_LIVE_ENGINE_PARITY"}
    )
    native_notes = _merge_codes(
        list(compatibility_notes),
        [
            "ENGINE_NATIVE_RUNNER_INVOKED" if runner_invoked else "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
            edge_truth_status,
            builder_provenance,
            (
                build14_application.activation_status
                if build14_application is not None
                else "BUILD14_NOT_APPLIED"
            ),
        ],
    )
    build14_payload = (
        {
            "build14_shadow_activation_status": build14_application.activation_status,
            "build14_shadow_observation": build14_application.observation_input.model_dump(
                mode="json"
            ),
            "build14_shadow_report": build14_application.shadow_report.model_dump(
                mode="json"
            ),
            "build14_shadow_applied_fields": build14_application.applied_fields,
            "build14_shadow_adjustment_factors": build14_application.adjustment_factors,
            "build14_shadow_reason_codes": build14_application.reason_codes,
        }
        if build14_application is not None
        else {}
    )
    selected_engine_fields = _selected_engine_payload_fields(
        candidate_payload=payload,
        engine_input_payload=engine_input_payload,
        native_output=native_output,
        build14_application=build14_application,
    )
    # Patch F16-B (2026-05-21) — merge VPIN/OFI/queue scalaires bridge dans
    # le payload de compatibilité. Permet à `strategy_ladder_b2_label_store_builder`
    # de lire ces 3 features microstructure canoniques V5.3 via
    # `compatibility.get("vpin"/"cumulative_ofi"/"queue_pressure")` au même
    # titre que spread_bps. Backward-compat : dict vide si aucun bridge fourni.
    microstructure_bridge_payload: dict[str, object] = {}
    if bridge_microstructure_scalars:
        for key, value in bridge_microstructure_scalars.items():
            if value is not None:
                microstructure_bridge_payload[key] = value
    engine_d_governance_payload: dict[str, object] = {}
    for key, value in _extract_engine_d_governance_scalars(
        selected_engine_fields,
        native_output,
        engine_input_payload,
    ).items():
        if value is not None:
            engine_d_governance_payload[key] = value
    build14_observed_payload: dict[str, object] = {}
    for key, value in _extract_build14_observed_values(build14_application).items():
        if value is not None:
            build14_observed_payload[key] = value
    anti_revenge_one_hot_payload: dict[str, object] = {}
    for key, value in _extract_anti_revenge_one_hot(
        selected_engine_fields,
        native_output,
        engine_input_payload,
    ).items():
        if value is not None:
            anti_revenge_one_hot_payload[key] = value
    latency_penalty_bps = economic_provenance.latency_penalty_bps
    if latency_penalty_bps is None:
        latency_penalty_bps = _extract_latency_penalty_bps(native_output, payload)
    measured_slippage_report = cost_governance.get("measured_slippage_report")
    measured_slippage_status = (
        str(measured_slippage_report.get("status") or "").strip()
        if isinstance(measured_slippage_report, dict)
        else ""
    )
    measured_depth20_level = None
    if (
        measured_slippage_status == "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
        and window is not None
        and window.book_depth_levels_available is not None
        and int(window.book_depth_levels_available or 0) > 0
    ):
        measured_depth20_level = int(window.book_depth_levels_available)
    feature_values_payload = dict(payload.get("feature_values") or {})
    if measured_depth20_level is not None:
        feature_values_payload["book_depth_levels"] = measured_depth20_level
    updated_payload = {
        **payload,
        **build14_payload,
        **selected_engine_fields,
        **microstructure_bridge_payload,
        **engine_d_governance_payload,
        **build14_observed_payload,
        **anti_revenge_one_hot_payload,
        "candidate_source": "ENGINE_NATIVE" if runner_invoked else "ENGINE_NATIVE_UNAVAILABLE",
        "candidate_data_source_label": "ENGINE_NATIVE_A_B_C_D_RUNNER",
        "raw_score": raw_score,
        "penalized_score": penalized_score,
        "final_score": final_score,
        "expected_edge_bps": economic_provenance.expected_edge_bps,
        "expected_edge_provenance": economic_provenance.expected_edge_provenance,
        "expected_edge_truth_status": edge_truth_status,
        "expected_edge_selection_gate_status": (
            "EXPECTED_EDGE_SELECTION_GATE_DISABLED_IN_ML_OFF"
            if not edge_truth_is_selection_gate
            else "EXPECTED_EDGE_SELECTION_GATE_ENABLED"
        ),
        "engine_input_expected_gain": (
            _coerce_float(engine_input_payload.get("expected_gain"), 0.0)
            if engine_input_payload
            else 0.0
        ),
        "engine_input_expected_gain_source_status": (
            _engine_input_expected_gain_source_status(
                economic_provenance,
                ml_mode=ml_mode,
            )
        ),
        "profitability_blocker_reasons": profitability_blockers,
        "expected_edge_model_status": economic_provenance.expected_edge_model_status,
        "expected_edge_model_artifact_hash": (
            economic_provenance.expected_edge_model_artifact_hash
        ),
        "expected_edge_model_feature_hash": (
            economic_provenance.expected_edge_model_feature_hash
        ),
        "economic_provenance": economic_provenance.aggregated_provenance,
        "economic_measurement_warnings": economic_provenance.measurement_warnings,
        "spread_bps": economic_provenance.spread_bps,
        "spread_provenance": economic_provenance.spread_provenance,
        "slippage_bps": economic_provenance.slippage_bps,
        "slippage_provenance": economic_provenance.slippage_provenance,
        "book_depth_levels": (
            measured_depth20_level
            if measured_depth20_level is not None
            else payload.get("book_depth_levels")
        ),
        "feature_values": feature_values_payload,
        "latency_penalty_bps": latency_penalty_bps,
        "latency_source_status": economic_provenance.latency_provenance,
        "fee_bps": economic_provenance.fee_bps,
        "fee_source_status": economic_provenance.fee_provenance,
        "impact_source_status": (
            str(cost_governance.get("impact_source_status") or "").strip()
            or economic_provenance.slippage_provenance
        ),
        "measured_spread_report": cost_governance.get("measured_spread_report"),
        "measured_slippage_report": cost_governance.get("measured_slippage_report"),
        "book_staleness_ms": cost_governance.get("book_staleness_ms"),
        "best_bid": cost_governance.get("best_bid"),
        "best_ask": cost_governance.get("best_ask"),
        "mid_price": cost_governance.get("mid_price"),
        "spread_bps_measured": cost_governance.get("spread_bps_measured"),
        "slippage_bps_measured": cost_governance.get("slippage_bps_measured"),
        "depth_fill_ratio": cost_governance.get("depth_fill_ratio"),
        "partial_fill_status": cost_governance.get("partial_fill_status"),
        "spread_source_status": cost_governance.get("spread_source_status"),
        "slippage_source_status": cost_governance.get("slippage_source_status"),
        "cost_source_used_for_break_even": cost_governance.get(
            "cost_source_used_for_break_even"
        ),
        "cost_source_used_for_expected_ce_net": cost_governance.get(
            "cost_source_used_for_expected_ce_net"
        ),
        "expected_cost_truth_status": cost_governance.get("expected_cost_truth_status"),
        "expected_cost_block_reason": cost_governance.get("expected_cost_block_reason"),
        "fill_realism_status": (
            str(cost_governance.get("fill_realism_status") or "").strip()
            or payload.get("fill_realism_status")
        ),
        "target_decision_state": target_state,
        "production_decision_state": _native_production_decision_state(
            decision,
            target_state,
        ),
        "production_final_score": final_score,
        "production_expected_cost": _expected_cost_from_provenance(economic_provenance),
        "hard_block_reasons": _merge_codes(
            list(hard_block_reasons),
            list(native_blockers),
            list(reason_codes),
            list(no_trade_reasons),
        ),
        # Patch P0 #2 + P1 #1 (2026-05-30) — separate buckets so the dashboard
        # can render hard-block / promotion / diagnostic in distinct sections.
        # `promotion_blockers` allows execution but blocks promotion (audit-grade).
        # `diagnostic_status` is informational (e.g. DECISION_REUSED_FROM_B1).
        "promotion_blockers": tuple(profitability_blockers),
        "diagnostic_status": tuple(diagnostic_status_local),
        "compatibility_notes": native_notes,
        "engine_native_status": (
            "ENGINE_NATIVE_RUNNER_INVOKED" if runner_invoked else "ENGINE_NATIVE_RUNNER_NOT_INVOKED"
        ),
        "engine_native_builder_status": builder_status,
        "engine_native_input_provenance": builder_provenance,
        "engine_native_input_hash": engine_input_hash,
        "engine_native_output_hash": native_output_hash,
        "engine_native_decision": decision,
        "engine_native_reason_codes": reason_codes,
        "engine_native_no_trade_reasons": no_trade_reasons,
        "engine_native_records_built": records_built,
    }
    preliminary_reasons = _merge_codes(
        [
            "ENGINE_NATIVE_RUNNER_INVOKED" if runner_invoked else "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
            f"ENGINE_NATIVE_DECISION:{decision.upper() or 'NOT_INVOKED'}",
            builder_status,
            edge_truth_status,
        ],
        list(build14_application.reason_codes) if build14_application is not None else [],
        list(reason_codes),
        list(no_trade_reasons),
        list(builder_warnings),
    )
    source = "ENGINE_NATIVE" if runner_invoked else "ENGINE_NATIVE_UNAVAILABLE"
    native_input_hash = deterministic_payload_hash(
        {
            "candidate_input": candidate.input_data_hash,
            "window_input": window.input_data_hash if window is not None else None,
            "engine_input": engine_input_hash,
            "engine_output": native_output_hash,
            "economic": economic_provenance.__dict__,
            "build14_shadow": (
                build14_application.shadow_report.model_dump(mode="json")
                if build14_application is not None
                else None
            ),
        }
    )
    return candidate.model_copy(
        update={
            "candidate_source": source,
            "candidate_data_source_label": "ENGINE_NATIVE_A_B_C_D_RUNNER",
            "preliminary_score": final_score,
            "preliminary_reason_codes": preliminary_reasons,
            "input_data_hash": native_input_hash,
            "method_version_hash": deterministic_payload_hash(
                {
                    "method": "strategy_ladder.engine_native_materialization.v1",
                    "engine_id": candidate.engine_id,
                    "builder_provenance": builder_provenance,
                    "build14_shadow_status": (
                        build14_application.activation_status
                        if build14_application is not None
                        else "BUILD14_NOT_APPLIED"
                    ),
                }
            ),
            "compatibility_payload": updated_payload,
        }
    )


def _run_native_engine_candidate(
    *,
    candidate: StrategyLadderCandidateEvent,
    window: StrategyLadderRawWindowManifest | None,
    economic_provenance: EconomicProvenance,
    ml_mode: str = "ML_MODE_OFF",
) -> tuple[StrategyLadderCandidateEvent, int, bool]:
    payload = dict(candidate.compatibility_payload or {})
    expected_gain = _engine_input_expected_gain_from_provenance(
        economic_provenance,
        ml_mode=ml_mode,
    )
    expected_cost = _expected_cost_from_provenance(economic_provenance)
    candidate_size = _planned_notional_from_payload(payload)
    builder_status = "ENGINE_NATIVE_INPUT_BUILDER_NOT_RUN"
    builder_warnings: tuple[str, ...] = ()
    builder_provenance = "ENGINE_NATIVE_INPUT_PROVENANCE_NOT_PROVEN"
    engine_input_payload: dict[str, object] = {}
    engine_output: object | None = None
    records_built = 0
    runner_invoked = False
    build14_application: StrategyLadderBuild14Application | None = None
    # Patch F16-B (2026-05-21) — VPIN/OFI/queue_pressure capturés depuis bridge
    # par engine et propagés au payload pour persistence en label store.
    bridge_microstructure_scalars: dict[str, float | None] | None = None

    if window is None:
        return (
            _materialize_native_candidate_event(
                candidate=candidate,
                window=window,
                economic_provenance=economic_provenance,
                builder_status="ENGINE_NATIVE_INPUT_BUILDER_FAILED_NO_RAW_WINDOW",
                builder_warnings=("RAW_WINDOW_NOT_AVAILABLE",),
                builder_provenance=builder_provenance,
                engine_output=None,
                engine_input_payload={},
                build14_application=None,
                records_built=0,
                runner_invoked=False,
                ml_mode=ml_mode,
            ),
            0,
            False,
        )

    try:
        engine_id = (candidate.engine_id or "").lower()
        if engine_id == "engine_a":
            from engines.engine_a.engine_a_runner import EngineAInput, run_engine_a
            from local_replay_runtime.strategy_ladder_engine_a_input_builder import (
                build_engine_a_input_from_window,
            )
            from local_replay_runtime.strategy_ladder_engine_native_adapter import (
                build_engine_a_microstructure_inputs_from_window,
            )

            bridge = build_engine_a_microstructure_inputs_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_trade_path=window.raw_trade_path,
                raw_book_path=window.raw_book_path,
                raw_book_delta_path=window.raw_book_delta_path,
            )
            records_built = bridge.n_records_built
            bridge_microstructure_scalars = _extract_bridge_microstructure_scalars(bridge)
            builder = build_engine_a_input_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_ohlcv_path=window.raw_ohlcv_path,
                microstructure_updates=bridge.engine_a_microstructure_updates,
                expected_gain=expected_gain,
                expected_cost=expected_cost,
                candidate_size=candidate_size,
            )
            builder_status = builder.builder_status
            builder_warnings = _merge_codes(
                list(bridge.bridge_warnings),
                list(builder.builder_warnings),
            )
            builder_provenance = builder.engine_a_input_provenance
            engine_input_payload = builder.engine_a_input_payload
            if engine_input_payload:
                engine_output = run_engine_a(EngineAInput.model_validate(engine_input_payload))
                runner_invoked = True
        elif engine_id == "engine_b":
            from engines.engine_b.engine_b_runner import EngineBInput, run_engine_b
            from local_replay_runtime.strategy_ladder_engine_b_input_builder import (
                build_engine_b_input_from_window,
            )

            builder = build_engine_b_input_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_trade_path=window.raw_trade_path,
                raw_book_path=window.raw_book_path,
                raw_book_delta_path=window.raw_book_delta_path,
                expected_gain=expected_gain,
                expected_cost=expected_cost,
                candidate_size=candidate_size,
            )
            records_built = (
                builder.bridge_result.n_records_built
                if builder.bridge_result is not None
                else 0
            )
            bridge_microstructure_scalars = _extract_bridge_microstructure_scalars(
                builder.bridge_result
            )
            builder_status = builder.builder_status
            builder_warnings = builder.builder_warnings
            builder_provenance = builder.engine_b_input_provenance
            engine_input_payload = builder.engine_b_input_payload
            if engine_input_payload:
                engine_output = run_engine_b(EngineBInput.model_validate(engine_input_payload))
                runner_invoked = True
        elif engine_id == "engine_c":
            from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
            from local_replay_runtime.strategy_ladder_engine_c_input_builder import (
                build_engine_c_input_from_window,
            )
            from local_replay_runtime.strategy_ladder_engine_native_adapter import (
                build_engine_c_microstructure_inputs_from_window,
            )

            bridge = build_engine_c_microstructure_inputs_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_trade_path=window.raw_trade_path,
                raw_book_path=window.raw_book_path,
                raw_book_delta_path=window.raw_book_delta_path,
            )
            records_built = bridge.n_records_built
            bridge_microstructure_scalars = _extract_bridge_microstructure_scalars(bridge)
            builder = build_engine_c_input_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_trade_path=window.raw_trade_path,
                raw_ohlcv_path=window.raw_ohlcv_path,
                microstructure_partial_payload=bridge.engine_c_partial_input_payload,
                expected_gain=expected_gain,
                expected_cost=expected_cost,
                candidate_size=candidate_size,
            )
            builder_status = builder.builder_status
            builder_warnings = _merge_codes(
                list(bridge.bridge_warnings),
                list(builder.builder_warnings),
            )
            builder_provenance = builder.engine_c_input_provenance
            engine_input_payload = builder.engine_c_input_payload
            if engine_input_payload:
                build14_application = apply_build14_shadow_context(
                    engine_id=engine_id,
                    candidate_id=candidate.candidate_id,
                    pair=candidate.pair,
                    candidate_payload=payload,
                    engine_input_payload=engine_input_payload,
                )
                engine_input_payload = build14_application.adjusted_engine_input_payload
                builder_warnings = _merge_codes(
                    list(builder_warnings),
                    list(build14_application.reason_codes),
                )
                engine_output = run_engine_c(EngineCInput.model_validate(engine_input_payload))
                runner_invoked = True
        elif engine_id == "engine_d":
            from engines.engine_d.engine_d_models import EngineDInput
            from engines.engine_d.engine_d_runner import run_engine_d
            from local_replay_runtime.strategy_ladder_engine_d_input_builder import (
                build_engine_d_input_from_window,
            )

            builder = build_engine_d_input_from_window(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                window_start_ms=window.window_start_ms,
                window_end_ms=window.window_end_ms,
                raw_trade_path=window.raw_trade_path,
                raw_ohlcv_path=window.raw_ohlcv_path,
                raw_book_path=window.raw_book_path,
                raw_book_delta_path=window.raw_book_delta_path,
                first_episode_context=_extract_engine_d_first_episode_context(payload),
                expected_gain=expected_gain,
                expected_cost=expected_cost,
                candidate_size=candidate_size,
            )
            records_built = (
                builder.bridge_result.n_records_built
                if builder.bridge_result is not None
                else 0
            )
            bridge_microstructure_scalars = _extract_bridge_microstructure_scalars(
                builder.bridge_result
            )
            builder_status = builder.builder_status
            builder_warnings = builder.builder_warnings
            builder_provenance = builder.engine_d_input_provenance
            engine_input_payload = builder.engine_d_input_payload
            if engine_input_payload:
                build14_application = apply_build14_shadow_context(
                    engine_id=engine_id,
                    candidate_id=candidate.candidate_id,
                    pair=candidate.pair,
                    candidate_payload=payload,
                    engine_input_payload=engine_input_payload,
                )
                engine_input_payload = build14_application.adjusted_engine_input_payload
                builder_warnings = _merge_codes(
                    list(builder_warnings),
                    list(build14_application.reason_codes),
                )
                engine_output = run_engine_d(EngineDInput.model_validate(engine_input_payload))
                runner_invoked = True
        else:
            builder_status = "ENGINE_NATIVE_INPUT_BUILDER_UNSUPPORTED_ENGINE"
            builder_warnings = (f"UNSUPPORTED_ENGINE:{candidate.engine_id}",)
    except Exception as exc:  # noqa: BLE001
        builder_warnings = _merge_codes(
            list(builder_warnings),
            [f"ENGINE_NATIVE_RUN_FAILED:{type(exc).__name__}:{exc}"],
        )
        runner_invoked = False
        engine_output = None

    return (
        _materialize_native_candidate_event(
            candidate=candidate,
            window=window,
            economic_provenance=economic_provenance,
            builder_status=builder_status,
            builder_warnings=builder_warnings,
            builder_provenance=builder_provenance,
            engine_output=engine_output,
            engine_input_payload=engine_input_payload,
            build14_application=build14_application,
            records_built=records_built,
            runner_invoked=runner_invoked,
            bridge_microstructure_scalars=bridge_microstructure_scalars,
            ml_mode=ml_mode,
        ),
        records_built,
        runner_invoked,
    )


def _native_candidate_worker(
    packed: tuple[
        StrategyLadderCandidateEvent, StrategyLadderRawWindowManifest | None, dict
    ],
) -> tuple[StrategyLadderCandidateEvent, int, bool, bool, str]:
    """Picklable per-candidate unit for the Phase 3 parallel path: compute the
    economic provenance (book reconstruction + Kyle slippage) then run the native
    engine. Module-level so it survives the Windows ``spawn`` pickle. Used only
    when no expected-edge model is loaded (models are not passed across the
    process boundary). Returns exactly what the serial loop needs to accumulate."""
    candidate, window, cfg = packed
    economic_provenance = _economic_provenance_for_candidate(
        candidate,
        window,
        expected_edge_model=None,
        expected_edge_model_required=cfg["expected_edge_model_required"],
        expected_edge_model_load_status=cfg["expected_edge_model_load_status"],
        silver_exchange=cfg["silver_exchange"],
        silver_market_type=cfg["silver_market_type"],
    )
    native_event, built_count, invoked = _run_native_engine_candidate(
        candidate=candidate,
        window=window,
        economic_provenance=economic_provenance,
        ml_mode=cfg["ml_mode"],
    )
    is_truth = is_expected_edge_backtest_truth(
        economic_provenance.expected_edge_provenance
    )
    edge_status = expected_edge_backtest_truth_status(
        economic_provenance.expected_edge_provenance
    )
    return native_event, built_count, invoked, is_truth, edge_status


def _candidate_affinity_key(
    packed: tuple[
        StrategyLadderCandidateEvent, StrategyLadderRawWindowManifest | None, dict
    ],
) -> str:
    """Group candidates reading the same silver book source into one worker chunk
    so the per-process Arrow ``load_silver_table`` cache is reused, not re-parsed."""
    window = packed[1]
    if window is None:
        return ""
    return str(
        getattr(window, "raw_book_path", "")
        or getattr(window, "raw_trade_path", "")
        or ""
    )


def _prewrite_silver_ipc_sidecars(
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    window_by_candidate: dict,
) -> None:
    """Parent parses each unique silver source ONCE (writing its Arrow IPC
    sidecar) so the spawned workers all memory-map it (zero re-parse). Best-effort
    — a missing/unreadable source just means that worker falls back to a parse."""
    from local_replay_runtime.strategy_ladder_arrow_window import load_silver_table

    seen: set[str] = set()
    for candidate in candidate_events:
        window = window_by_candidate.get(candidate.candidate_id)
        if window is None:
            continue
        for attr in (
            "raw_book_path",
            "raw_book_delta_path",
            "raw_trade_path",
            "raw_ohlcv_path",
        ):
            path = str(getattr(window, attr, "") or "")
            if path and path not in seen:
                seen.add(path)
                try:
                    load_silver_table(path)
                except Exception:  # noqa: BLE001 — best-effort sidecar pre-warm
                    pass


def _parallel_native_materialization(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    window_by_candidate: dict,
    expected_edge_model: ExpectedEdgeModelProtocol | None,
    expected_edge_model_required: bool,
    expected_edge_model_load_status: str,
    silver_exchange: str | None,
    silver_market_type: str,
    ml_mode: str,
    progress_callback: Callable[[int, int, int, int, int, int], None] | None,
) -> tuple[list, int, int, int, int, list[str]] | None:
    """Phase 3 — engine-native materialization across CPU cores.

    Returns the accumulated tuple ``(native_events, records_built,
    runner_invocations, expected_edge_proxy_count, expected_edge_governed_count,
    expected_edge_blocker_codes)`` when parallelism is engaged, or ``None`` to
    tell the caller to run the legacy serial loop unchanged.

    Engaged only when: workers > 1 (``V53_MAX_WORKERS`` opt-in / auto), no
    expected-edge model is loaded, and there is more than one candidate. Output
    is identical to the serial loop — order is preserved, counters are sums."""
    workers = resolve_worker_count()
    if workers <= 1 or expected_edge_model is not None or len(candidate_events) <= 1:
        return None
    cfg = {
        "expected_edge_model_required": expected_edge_model_required,
        "expected_edge_model_load_status": expected_edge_model_load_status,
        "silver_exchange": silver_exchange,
        "silver_market_type": silver_market_type,
        "ml_mode": ml_mode,
    }
    tasks = [
        (candidate, window_by_candidate.get(candidate.candidate_id), cfg)
        for candidate in candidate_events
    ]
    # Phase 3 IPC orchestration: parse each silver source ONCE in the parent and
    # share it with the workers as a memory-mapped Arrow IPC sidecar (no per-worker
    # re-parse). Scoped to this call + cleaned up so it never leaks elsewhere.
    ipc_cache_dir = tempfile.mkdtemp(prefix="v53_ipc_")
    previous_ipc_env = os.environ.get("V53_IPC_CACHE_DIR")
    os.environ["V53_IPC_CACHE_DIR"] = ipc_cache_dir
    try:
        _prewrite_silver_ipc_sidecars(candidate_events, window_by_candidate)
        results = ordered_parallel_map(
            _native_candidate_worker,
            tasks,
            max_workers=workers,
            affinity_key=_candidate_affinity_key,
        )
    finally:
        if previous_ipc_env is None:
            os.environ.pop("V53_IPC_CACHE_DIR", None)
        else:
            os.environ["V53_IPC_CACHE_DIR"] = previous_ipc_env
        shutil.rmtree(ipc_cache_dir, ignore_errors=True)
    native_events: list[StrategyLadderCandidateEvent] = []
    records_built = 0
    runner_invocations = 0
    expected_edge_proxy_count = 0
    expected_edge_governed_count = 0
    expected_edge_blocker_codes: list[str] = []
    for native_event, built_count, invoked, is_truth, edge_status in results:
        if is_truth:
            expected_edge_governed_count += 1
        else:
            expected_edge_proxy_count += 1
            expected_edge_blocker_codes.append(
                "EXPECTED_EDGE_MODEL_NOT_BACKTEST_TRUTH"
                if edge_status == "EXPECTED_EDGE_MODEL_BLOCKED"
                else "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH"
            )
        native_events.append(native_event)
        records_built += built_count
        if invoked:
            runner_invocations += 1
    if progress_callback is not None:
        total_candidates = len(candidate_events)
        progress_callback(
            total_candidates,
            total_candidates,
            records_built,
            runner_invocations,
            expected_edge_proxy_count,
            expected_edge_governed_count,
        )
    return (
        native_events,
        records_built,
        runner_invocations,
        expected_edge_proxy_count,
        expected_edge_governed_count,
        expected_edge_blocker_codes,
    )


def _materialize_engine_native_candidates(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
    expected_edge_model: ExpectedEdgeModelProtocol | None = None,
    expected_edge_model_required: bool = False,
    expected_edge_model_load_status: str = "",
    progress_callback: Callable[[int, int, int, int, int, int], None] | None = None,
    silver_exchange: str | None = None,
    silver_market_type: str = "spot",
    ml_mode: str = "ML_MODE_OFF",
) -> _EngineNativeCandidateMaterialization:
    if not candidate_events:
        return _EngineNativeCandidateMaterialization(
            candidate_events=(),
            candidate_discovery_status="CANDIDATE_DISCOVERY_EMPTY",
            engine_native_status="ENGINE_NATIVE_NO_CANDIDATES",
            engine_native_records_built=0,
            engine_native_runner_invocation_count=0,
            expected_edge_proxy_count=0,
            expected_edge_governed_count=0,
        )

    window_by_candidate = {
        manifest.candidate_id: manifest for manifest in raw_window_manifests
    }
    native_events: list[StrategyLadderCandidateEvent] = []
    records_built = 0
    runner_invocations = 0
    expected_edge_proxy_count = 0
    expected_edge_governed_count = 0
    expected_edge_blocker_codes: list[str] = []
    total_candidates = len(candidate_events)
    _serial_events: tuple[StrategyLadderCandidateEvent, ...] = candidate_events
    _parallel = _parallel_native_materialization(
        candidate_events=candidate_events,
        window_by_candidate=window_by_candidate,
        expected_edge_model=expected_edge_model,
        expected_edge_model_required=expected_edge_model_required,
        expected_edge_model_load_status=expected_edge_model_load_status,
        silver_exchange=silver_exchange,
        silver_market_type=silver_market_type,
        ml_mode=ml_mode,
        progress_callback=progress_callback,
    )
    if _parallel is not None:
        (
            native_events,
            records_built,
            runner_invocations,
            expected_edge_proxy_count,
            expected_edge_governed_count,
            expected_edge_blocker_codes,
        ) = _parallel
        _serial_events = ()
    for processed_count, candidate in enumerate(_serial_events, start=1):
        if processed_count == 1 or processed_count % _ENGINE_NATIVE_PROGRESS_EVERY == 0:
            assert_ram_below_hard_limit(phase_name="engine_native_materialization")
        window = window_by_candidate.get(candidate.candidate_id)
        economic_provenance = _economic_provenance_for_candidate(
            candidate,
            window,
            expected_edge_model=expected_edge_model,
            expected_edge_model_required=expected_edge_model_required,
            expected_edge_model_load_status=expected_edge_model_load_status,
            silver_exchange=silver_exchange,
            silver_market_type=silver_market_type,
        )
        if is_expected_edge_backtest_truth(economic_provenance.expected_edge_provenance):
            expected_edge_governed_count += 1
        else:
            expected_edge_proxy_count += 1
            edge_status = expected_edge_backtest_truth_status(
                economic_provenance.expected_edge_provenance
            )
            expected_edge_blocker_codes.append(
                "EXPECTED_EDGE_MODEL_NOT_BACKTEST_TRUTH"
                if edge_status == "EXPECTED_EDGE_MODEL_BLOCKED"
                else "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH"
            )
        native_event, built_count, invoked = _run_native_engine_candidate(
            candidate=candidate,
            window=window,
            economic_provenance=economic_provenance,
            ml_mode=ml_mode,
        )
        native_events.append(native_event)
        records_built += built_count
        if invoked:
            runner_invocations += 1
        if progress_callback is not None and (
            processed_count == total_candidates
            or processed_count == 1
            or processed_count % _ENGINE_NATIVE_PROGRESS_EVERY == 0
        ):
            progress_callback(
                processed_count,
                total_candidates,
                records_built,
                runner_invocations,
                expected_edge_proxy_count,
                expected_edge_governed_count,
            )

    if runner_invocations == len(candidate_events):
        discovery_status = "CANDIDATE_DISCOVERY_ENGINE_NATIVE_READY"
        native_status = "ENGINE_NATIVE_FULL_PATH_READY"
        blockers: tuple[str, ...] = ()
    elif runner_invocations > 0:
        discovery_status = "CANDIDATE_DISCOVERY_ENGINE_NATIVE_PARTIAL"
        native_status = "ENGINE_NATIVE_PARTIAL_WITH_BLOCKERS"
        blockers = ("ENGINE_NATIVE_CANDIDATE_TRUTH_PARTIAL",)
    else:
        discovery_status = "CANDIDATE_DISCOVERY_ENGINE_NATIVE_NOT_PROVEN"
        native_status = "ENGINE_NATIVE_CANDIDATES_PRESENT_NOT_INVOKED"
        blockers = ("ENGINE_NATIVE_CANDIDATE_TRUTH_NOT_PROVEN",)
    if expected_edge_proxy_count:
        blockers = _merge_codes(list(blockers), expected_edge_blocker_codes)

    return _EngineNativeCandidateMaterialization(
        candidate_events=tuple(native_events),
        candidate_discovery_status=discovery_status,
        engine_native_status=native_status,
        engine_native_records_built=records_built,
        engine_native_runner_invocation_count=runner_invocations,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        blocker_codes=blockers,
    )


def _invoke_engine_native_bridges_sample(
    *,
    request: StrategyLadderRequest,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
) -> int:
    """Audit 2026-05-07 (P3a wire) — invoque les engine bridges sur un sample.

    Quand `request.engine_native_mode` est True, parcourt jusqu'a
    `request.engine_native_sample_size` candidats et invoque le bridge approprie
    selon `candidate.engine_id` (engine_a/b/c/d). Compte les records canoniques
    construits avec succes (Kyle/VPIN/OFI/QueuePressure/RealizedKernelVol pour
    a/c, realized_vol_current/post_close pour d, current_price/local_mean/std/vpin
    pour b).

    Retourne 0 si engine_native_mode est False ou sample_size==0.

    Note : cette fonction NE met PAS a jour candidate_count_engine_native parce
    que le bridge produit des inputs partiels — pas encore d'invocation
    `run_engine_X(EngineXInput)` finale (bloquee par les champs structurels
    sans structure-resolver canonique).
    """
    if not request.engine_native_mode:
        return 0
    sample_size = request.engine_native_sample_size
    if sample_size == 0:
        # 0 = traiter tous les candidats (DANGER : peut prendre des heures)
        sample_candidates = candidate_events
    else:
        sample_candidates = candidate_events[:sample_size]

    # Import local pour eviter dependance hard sur l'adapter au top-level
    # (l'adapter import data_backbone.microstructure qui peut avoir ses
    # propres dependances).
    try:
        from local_replay_runtime.strategy_ladder_engine_native_adapter import (
            build_engine_a_microstructure_inputs_from_window,
            build_engine_b_microstructure_inputs_from_window,
            build_engine_c_microstructure_inputs_from_window,
            build_engine_d_microstructure_inputs_from_window,
        )
    except ImportError:
        return 0

    window_by_candidate = {
        manifest.candidate_id: manifest for manifest in raw_window_manifests
    }
    total_records_built = 0

    for candidate in sample_candidates:
        window = window_by_candidate.get(candidate.candidate_id)
        if window is None:
            continue
        common_kwargs = {
            "candidate_id": candidate.candidate_id,
            "pair": candidate.pair,
            "window_start_ms": window.window_start_ms,
            "window_end_ms": window.window_end_ms,
            "raw_trade_path": window.raw_trade_path,
        }
        try:
            engine_id = (candidate.engine_id or "").lower()
            if engine_id == "engine_a":
                result = build_engine_a_microstructure_inputs_from_window(
                    **common_kwargs,
                    raw_book_path=window.raw_book_path,
                    raw_book_delta_path=window.raw_book_delta_path,
                )
                total_records_built += result.n_records_built
            elif engine_id == "engine_b":
                result_b = build_engine_b_microstructure_inputs_from_window(
                    **common_kwargs,
                )
                total_records_built += result_b.n_records_built
            elif engine_id == "engine_c":
                result_c = build_engine_c_microstructure_inputs_from_window(
                    **common_kwargs,
                    raw_book_path=window.raw_book_path,
                    raw_book_delta_path=window.raw_book_delta_path,
                )
                total_records_built += result_c.n_records_built
            elif engine_id == "engine_d":
                result_d = build_engine_d_microstructure_inputs_from_window(
                    **common_kwargs,
                    post_close_window_end_ms=window.window_end_ms + 60_000,
                )
                total_records_built += result_d.n_records_built
            # engines inconnus : ignore silencieusement (pas de bridge dispo)
        except Exception:  # noqa: BLE001
            # On ne propage pas — le bridge est best-effort. Les warnings sont
            # remontes dans chaque BridgeResult (perdus ici par design : ce
            # wire est minimal, full reporting sera la session suivante).
            continue

    return total_records_built


def _build_report_summary(
    *,
    request: StrategyLadderRequest,
    run_manifest: StrategyLadderRunManifest,
    capital_profiles: tuple[CapitalBucketProfile, ...],
    engine_artifacts: tuple[EnginePromotionArtifact, ...],
    pair_artifacts: tuple[PairPromotionArtifact, ...],
    strategy_artifacts: tuple[StrategyPromotionArtifact, ...],
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
    evidence_projection: dict[str, object],
) -> StrategyLadderReportSummary:
    promotion_blockers = tuple(
        dict.fromkeys(
            (
                *run_manifest.blocker_codes,
                *(
                    blocker
                    for profile in capital_profiles
                    for blocker in profile.promotion_blockers
                ),
                *(
                    blocker
                    for artifact in (*engine_artifacts, *pair_artifacts, *strategy_artifacts)
                    for blocker in artifact.promotion_blockers
                ),
                *(
                    str(item)
                    for item in evidence_projection.get(
                        "evidence_audit_blocker_codes", ()
                    )
                ),
            )
        )
    )
    recommended_next_action = (
        "RUN_SHADOW_CONFIRMATION"
        if (
            run_manifest.final_status == "STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED"
            and run_manifest.promotion_artifact_status == "PROMOTION_ARTIFACTS_READY"
            and not promotion_blockers
        )
        else "FIX_BLOCKERS_OR_PROVIDE_HIGHER_FIDELITY_DATA"
    )
    summary = StrategyLadderReportSummary(
        run_id=request.run_id,
        # STRATEGY_LADDER_READY remains an external audit verdict, not a runtime-emitted
        # backtest status. The runner only emits measured / partial / blocked evidence.
        backtest_architecture_status="PARTIALLY_UPDATED_REPLAY_BACKTEST",
        data_factory_status=run_manifest.data_factory_status,
        raw_source_status=run_manifest.raw_source_status,
        pair_universe_status=run_manifest.pair_universe_status,
        silver_index_status=run_manifest.silver_index_status,
        gold_feature_store_status=run_manifest.gold_feature_store_status,
        orderbook_reconstruction_status=run_manifest.orderbook_reconstruction_status,
        ml_mode_status=run_manifest.ml_mode_status,
        feature_store_status=run_manifest.feature_store_status,
        candidate_discovery_status=run_manifest.candidate_discovery_status,
        candidate_export_status=run_manifest.candidate_export_status,
        raw_window_extraction_status=run_manifest.raw_window_extraction_status,
        raw_window_materialization_mode=run_manifest.raw_window_materialization_mode,
        detailed_replay_status=run_manifest.detailed_replay_status,
        capital_profile_generation_status=run_manifest.capital_profile_generation_status,
        promotion_artifact_status=run_manifest.promotion_artifact_status,
        sample_size_survival_status=run_manifest.sample_size_survival_status,
        final_status=run_manifest.final_status,
        blocker_codes=run_manifest.blocker_codes,
        silver_index_path=run_manifest.silver_index_path,
        workflow_run_id=run_manifest.workflow_run_id,
        phase_run_id=run_manifest.phase_run_id,
        parent_workflow_ref=run_manifest.parent_workflow_ref,
        candidate_sample_cap=run_manifest.candidate_sample_cap,
        effective_engine_native_sample_size=run_manifest.effective_engine_native_sample_size,
        engine_count=run_manifest.engine_count,
        candidate_cap_formula=run_manifest.candidate_cap_formula,
        small_scope_enabled=run_manifest.small_scope_enabled,
        full_scan_enabled=run_manifest.full_scan_enabled,
        no_full_scan_enabled=run_manifest.no_full_scan_enabled,
        candidate_discovery_limited=run_manifest.candidate_discovery_limited,
        candidate_discovery_limit_reason=run_manifest.candidate_discovery_limit_reason,
        candidate_discovery_mode=run_manifest.candidate_discovery_mode,
        candidate_discovery_cap_status=run_manifest.candidate_discovery_cap_status,
        temporal_bucket_granularity=run_manifest.temporal_bucket_granularity,
        temporal_bucket_count_available=run_manifest.temporal_bucket_count_available,
        temporal_bucket_count_selected=run_manifest.temporal_bucket_count_selected,
        temporal_bucket_coverage_ratio=run_manifest.temporal_bucket_coverage_ratio,
        feature_names=run_manifest.feature_names,
        preselection_status=run_manifest.preselection_status,
        replay_input_mode_status=run_manifest.replay_input_mode_status,
        preselected_only=run_manifest.preselected_only,
        diagnostic_full_replay=run_manifest.diagnostic_full_replay,
        b1_5_policy_mode=run_manifest.b1_5_policy_mode,
        candidate_count=run_manifest.candidate_count,
        unique_candidate_count=run_manifest.unique_candidate_count,
        base_event_count=run_manifest.base_event_count,
        per_engine_candidate_count=run_manifest.per_engine_candidate_count,
        engine_native_candidate_count=run_manifest.engine_native_candidate_count,
        discovery_pre_candidate_count=run_manifest.discovery_pre_candidate_count,
        engine_native_preselected_count=run_manifest.engine_native_preselected_count,
        preselection_hard_rejected_count=run_manifest.preselection_hard_rejected_count,
        preselection_soft_flagged_count=run_manifest.preselection_soft_flagged_count,
        preselection_passed_count=run_manifest.preselection_passed_count,
        b2_replay_candidate_count=run_manifest.b2_replay_candidate_count,
        trade_eligible_candidate_count=run_manifest.trade_eligible_candidate_count,
        preselection_rejection_count=run_manifest.preselection_rejection_count,
        replay_savings_estimate_count=run_manifest.replay_savings_estimate_count,
        replay_record_count=run_manifest.replay_record_count,
        evaluation_record_count=run_manifest.evaluation_record_count,
        promotion_record_count=run_manifest.promotion_record_count,
        capital_bucket_record_count=run_manifest.capital_bucket_record_count,
        replay_expansion_factor=run_manifest.replay_expansion_factor,
        replay_expansion_axis=run_manifest.replay_expansion_axis,
        candidate_source_status=run_manifest.candidate_source_status,
        count_semantics_validator_codes=run_manifest.count_semantics_validator_codes,
        matrix_count_inflation_status=run_manifest.matrix_count_inflation_status,
        raw_window_count=run_manifest.raw_window_count,
        raw_windows_total=run_manifest.raw_windows_total,
        trade_windows_found=run_manifest.trade_windows_found,
        trade_windows_missing=run_manifest.trade_windows_missing,
        book_windows_found=run_manifest.book_windows_found,
        book_windows_missing=run_manifest.book_windows_missing,
        ohlcv_windows_found=run_manifest.ohlcv_windows_found,
        ohlcv_windows_missing=run_manifest.ohlcv_windows_missing,
        depth20_found=run_manifest.depth20_found,
        depth20_missing=run_manifest.depth20_missing,
        detailed_replay_count=run_manifest.detailed_replay_count,
        capital_profile_count=len(capital_profiles),
        engine_promotion_count=len(engine_artifacts),
        pair_promotion_count=len(pair_artifacts),
        strategy_promotion_count=len(strategy_artifacts),
        sample_size_survival_count=len(sample_artifacts),
        economic_constants_provenance=run_manifest.economic_constants_provenance,
        candidate_truth_status=run_manifest.candidate_truth_status,
        expected_edge_truth_status=run_manifest.expected_edge_truth_status,
        execution_label_source=run_manifest.execution_label_source,
        fee_model_source=run_manifest.fee_model_source,
        spread_model_source=run_manifest.spread_model_source,
        slippage_model_source=run_manifest.slippage_model_source,
        partial_fill_model_source=run_manifest.partial_fill_model_source,
        adverse_selection_source=run_manifest.adverse_selection_source,
        order_type_selection_source=run_manifest.order_type_selection_source,
        venue_constraints_source=run_manifest.venue_constraints_source,
        execution_fidelity_gap_codes=run_manifest.execution_fidelity_gap_codes,
        expected_edge_proxy_count=run_manifest.expected_edge_proxy_count,
        expected_edge_governed_count=run_manifest.expected_edge_governed_count,
        expected_edge_model_status=run_manifest.expected_edge_model_status,
        expected_edge_model_artifact_hash=run_manifest.expected_edge_model_artifact_hash,
        expected_edge_model_feature_hash=run_manifest.expected_edge_model_feature_hash,
        expected_edge_training_artifact_ref=run_manifest.expected_edge_training_artifact_ref,
        expected_edge_label_source=run_manifest.expected_edge_label_source,
        expected_edge_label_fidelity=run_manifest.expected_edge_label_fidelity,
        expected_edge_anti_leakage_status=run_manifest.expected_edge_anti_leakage_status,
        expected_edge_walkforward_status=run_manifest.expected_edge_walkforward_status,
        expected_edge_horizon=run_manifest.expected_edge_horizon,
        expected_edge_purge_window=run_manifest.expected_edge_purge_window,
        expected_edge_embargo_window=run_manifest.expected_edge_embargo_window,
        expected_edge_blocker_codes=run_manifest.expected_edge_blocker_codes,
        candidate_engine_native_count=run_manifest.candidate_engine_native_count,
        candidate_proxy_count=run_manifest.candidate_proxy_count,
        executed_trade_count=run_manifest.executed_trade_count,
        statistical_validation_status=run_manifest.statistical_validation_status,
        statistical_validation_observation_count=run_manifest.statistical_validation_observation_count,
        statistical_validation_trial_count=run_manifest.statistical_validation_trial_count,
        statistical_validation_benchmark_sharpe=run_manifest.statistical_validation_benchmark_sharpe,
        statistical_validation_acceptance_floor=run_manifest.statistical_validation_acceptance_floor,
        statistical_validation_sample_sharpe=run_manifest.statistical_validation_sample_sharpe,
        statistical_validation_psr=run_manifest.statistical_validation_psr,
        statistical_validation_dsr=run_manifest.statistical_validation_dsr,
        statistical_validation_stationary_block_length=run_manifest.statistical_validation_stationary_block_length,
        statistical_validation_effective_sample_size=run_manifest.statistical_validation_effective_sample_size,
        statistical_validation_min_trl_required=run_manifest.statistical_validation_min_trl_required,
        statistical_validation_min_trl_satisfied=run_manifest.statistical_validation_min_trl_satisfied,
        statistical_validation_psr_passes_floor=run_manifest.statistical_validation_psr_passes_floor,
        statistical_validation_dsr_passes_floor=run_manifest.statistical_validation_dsr_passes_floor,
        statistical_validation_blocker_codes=run_manifest.statistical_validation_blocker_codes,
        engine_native_status=run_manifest.engine_native_status,
        engine_native_records_built=run_manifest.engine_native_records_built,
        depth_status_distribution={
            status: sum(
                1 for result in bucket_results if result.book_depth_source_status == status
            )
            for status in sorted({result.book_depth_source_status for result in bucket_results})
        },
        fill_realism_status_distribution={
            status: sum(
                1 for result in bucket_results if result.fill_realism_status == status
            )
            for status in sorted({result.fill_realism_status for result in bucket_results})
        },
        capital_bucket_verdicts={
            str(profile.capital_bucket): profile.promotion_status
            for profile in capital_profiles
        },
        engine_verdicts={
            artifact.engine_id: artifact.promotion_status
            for artifact in engine_artifacts
        },
        pair_verdicts={
            artifact.pair: artifact.promotion_status
            for artifact in pair_artifacts
        },
        strategy_verdicts={
            str(artifact.strategy_id): artifact.promotion_status
            for artifact in strategy_artifacts
        },
        governed_audit_evidence_index_path=str(
            evidence_projection.get("governed_audit_evidence_index_path") or ""
        ),
        governed_evidence_status=str(
            evidence_projection.get("governed_evidence_status")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        audited_evidence_count=int(
            evidence_projection.get("audited_evidence_count") or 0
        ),
        scratch_only_evidence_count=int(
            evidence_projection.get("scratch_only_evidence_count") or 0
        ),
        promotion_grade_evidence_count=int(
            evidence_projection.get("promotion_grade_evidence_count") or 0
        ),
        run_manifest_evidence_class=str(
            evidence_projection.get("run_manifest_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        capital_profiles_evidence_class=str(
            evidence_projection.get("capital_profiles_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        engine_promotion_evidence_class=str(
            evidence_projection.get("engine_promotion_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        pair_promotion_evidence_class=str(
            evidence_projection.get("pair_promotion_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        strategy_promotion_evidence_class=str(
            evidence_projection.get("strategy_promotion_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        sample_size_survival_evidence_class=str(
            evidence_projection.get("sample_size_survival_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        trade_detail_ledger_evidence_class=str(
            evidence_projection.get("trade_detail_ledger_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        refusal_ledger_evidence_class=str(
            evidence_projection.get("refusal_ledger_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        loss_analysis_ledger_evidence_class=str(
            evidence_projection.get("loss_analysis_ledger_evidence_class")
            or "EVIDENCE_CLASS_NOT_PROVEN"
        ),
        evidence_audit_blocker_codes=tuple(
            str(item)
            for item in evidence_projection.get("evidence_audit_blocker_codes", ())
        ),
        promotion_blockers=promotion_blockers,
        recommended_next_action=recommended_next_action,
        created_at=datetime.now(tz=UTC),
    )
    return summary.model_copy(
        update={"artifact_hash": deterministic_payload_hash(summary.model_dump(mode="json"))}
    )


def _write_reports(
    reports_dir: Path,
    *,
    summary: StrategyLadderReportSummary,
    run_manifest: StrategyLadderRunManifest,
    gold_manifest_payload: dict[str, object],
    capital_profiles: tuple[CapitalBucketProfile, ...],
    engine_artifacts: tuple[EnginePromotionArtifact, ...],
    pair_artifacts: tuple[PairPromotionArtifact, ...],
    strategy_artifacts: tuple[StrategyPromotionArtifact, ...],
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...],
    operator_artifact_refs: dict[str, str],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        reports_dir / "strategy_ladder_summary.json",
        summary.model_dump(mode="json"),
    )
    profitability_truth_verdict = _build_profitability_truth_verdict(
        summary=summary,
        run_manifest=run_manifest,
    )
    atomic_write_json(
        reports_dir / "profitability_truth_verdict.json",
        profitability_truth_verdict,
    )
    atomic_write_text(
        reports_dir / "profitability_truth_verdict.md",
        _format_profitability_truth_verdict_markdown(profitability_truth_verdict),
    )
    atomic_write_json(
        reports_dir / "capital_bucket_matrix.json",
        [profile.model_dump(mode="json") for profile in capital_profiles],
    )
    atomic_write_json(
        reports_dir / "engine_matrix.json",
        [artifact.model_dump(mode="json") for artifact in engine_artifacts],
    )
    atomic_write_json(
        reports_dir / "pair_matrix.json",
        [artifact.model_dump(mode="json") for artifact in pair_artifacts],
    )
    atomic_write_json(
        reports_dir / "strategy_matrix.json",
        [artifact.model_dump(mode="json") for artifact in strategy_artifacts],
    )
    output_root = reports_dir.parent.parent
    proof_payload = _load_json_payload(output_root / "backtest_proof_matrix.json")
    threshold_payload = _load_json_payload(output_root / "feature_threshold_manifest.json")
    threshold_rows = threshold_payload.get("thresholds_used")
    if not isinstance(threshold_rows, list):
        threshold_rows = []
    historical_replay_venue = str(
        proof_payload.get("historical_replay_venue") or "BYBIT"
    )
    execution_target_venue = str(
        proof_payload.get("execution_target_venue") or "BINANCE"
    )
    backtest_class = str(proof_payload.get("backtest_class") or "BYBIT_PROXY_BACKTEST")
    silver_storage_status = str(
        proof_payload.get("silver_storage_status") or "SILVER_STORAGE_NOT_PROVEN"
    )
    silver_bloat_ratio = proof_payload.get("silver_bloat_ratio")
    if not isinstance(silver_bloat_ratio, (int, float)):
        silver_bloat_ratio = None
    overall_backtest_proof_status = str(
        proof_payload.get("overall_backtest_proof_status")
        or (
            "BACKTEST_PROOF_BLOCKED"
            if summary.promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
            else "BACKTEST_PROOF_NOT_PROVEN"
        )
    )
    proxy_surface = build_strategy_ladder_proxy_fidelity_surface(
        feature_store_status=summary.feature_store_status,
        feature_row_count=run_manifest.feature_row_count,
        expected_edge_truth_status=summary.expected_edge_truth_status,
        expected_edge_governed_count=summary.expected_edge_governed_count,
        execution_fidelity_gap_codes=summary.execution_fidelity_gap_codes,
        threshold_rows=(
            tuple(dict(item) for item in threshold_rows if isinstance(item, dict))
        ),
        historical_replay_venue=historical_replay_venue,
        execution_target_venue=execution_target_venue,
        backtest_class=backtest_class,
        venue_transfer_status=str(
            proof_payload.get("venue_transfer_status") or "BINANCE_SHADOW_REQUIRED"
        ),
        promotion_artifact_status=summary.promotion_artifact_status,
        overall_backtest_proof_status=overall_backtest_proof_status,
    )
    lines = [
        "# Strategy Ladder Report",
        "",
        f"- run_id: {summary.run_id}",
        f"- final_status: {summary.final_status}",
        f"- feature_store_status: {summary.feature_store_status}",
        f"- feature_row_count: {run_manifest.feature_row_count}",
        f"- candidate_export_status: {summary.candidate_export_status}",
        f"- raw_window_extraction_status: {summary.raw_window_extraction_status}",
        f"- detailed_replay_status: {summary.detailed_replay_status}",
        f"- capital_profile_generation_status: {summary.capital_profile_generation_status}",
        f"- promotion_artifact_status: {proxy_surface.promotion_artifact_status}",
        f"- sample_size_survival_status: {summary.sample_size_survival_status}",
        f"- statistical_validation_status: {summary.statistical_validation_status}",
        f"- statistical_validation_observation_count: {summary.statistical_validation_observation_count}",
        f"- statistical_validation_trial_count: {summary.statistical_validation_trial_count}",
        f"- statistical_validation_acceptance_floor: {summary.statistical_validation_acceptance_floor}",
        f"- statistical_validation_stationary_block_length: {summary.statistical_validation_stationary_block_length}",
        (
            f"- statistical_validation_effective_sample_size: {summary.statistical_validation_effective_sample_size}"
            if summary.statistical_validation_effective_sample_size is not None
            else "- statistical_validation_effective_sample_size: NOT_PROVEN"
        ),
        (
            f"- statistical_validation_min_trl_required: {summary.statistical_validation_min_trl_required}"
            if summary.statistical_validation_min_trl_required is not None
            else "- statistical_validation_min_trl_required: NOT_PROVEN"
        ),
        f"- statistical_validation_min_trl_satisfied: {summary.statistical_validation_min_trl_satisfied}",
        (
            f"- statistical_validation_sample_sharpe: {summary.statistical_validation_sample_sharpe}"
            if summary.statistical_validation_sample_sharpe is not None
            else "- statistical_validation_sample_sharpe: NOT_PROVEN"
        ),
        (
            f"- statistical_validation_psr: {summary.statistical_validation_psr}"
            if summary.statistical_validation_psr is not None
            else "- statistical_validation_psr: NOT_PROVEN"
        ),
        (
            f"- statistical_validation_dsr: {summary.statistical_validation_dsr}"
            if summary.statistical_validation_dsr is not None
            else "- statistical_validation_dsr: NOT_PROVEN"
        ),
        f"- candidate_truth_status: {summary.candidate_truth_status}",
        f"- expected_edge_truth_status: {summary.expected_edge_truth_status}",
        f"- engine_native_status: {summary.engine_native_status}",
        f"- economic_constants_provenance: {summary.economic_constants_provenance}",
        f"- execution_label_source: {summary.execution_label_source}",
        f"- fee_model_source: {summary.fee_model_source}",
        f"- spread_model_source: {summary.spread_model_source}",
        f"- slippage_model_source: {summary.slippage_model_source}",
        f"- partial_fill_model_source: {summary.partial_fill_model_source}",
        f"- adverse_selection_source: {summary.adverse_selection_source}",
        f"- order_type_selection_source: {summary.order_type_selection_source}",
        f"- venue_constraints_source: {summary.venue_constraints_source}",
        (
            f"- execution_fidelity_gap_codes: {', '.join(summary.execution_fidelity_gap_codes)}"
            if summary.execution_fidelity_gap_codes
            else "- execution_fidelity_gap_codes: none"
        ),
        f"- candidate_count: {summary.candidate_count}",
        f"- unique_candidate_count: {summary.unique_candidate_count}",
        f"- base_event_count: {summary.base_event_count}",
        (
            f"- per_engine_candidate_count: {summary.per_engine_candidate_count}"
            if summary.per_engine_candidate_count is not None
            else "- per_engine_candidate_count: NOT_UNIFORM"
        ),
        f"- engine_native_candidate_count: {summary.engine_native_candidate_count}",
        f"- candidate_engine_native_count: {summary.candidate_engine_native_count}",
        f"- candidate_proxy_count: {summary.candidate_proxy_count}",
        f"- candidate_source_status: {summary.candidate_source_status}",
        f"- raw_window_count: {summary.raw_window_count}",
        f"- raw_windows_total: {summary.raw_windows_total}",
        f"- trade_windows_found: {summary.trade_windows_found}",
        f"- trade_windows_missing: {summary.trade_windows_missing}",
        f"- book_windows_found: {summary.book_windows_found}",
        f"- book_windows_missing: {summary.book_windows_missing}",
        f"- ohlcv_windows_found: {summary.ohlcv_windows_found}",
        f"- ohlcv_windows_missing: {summary.ohlcv_windows_missing}",
        f"- depth20_found: {summary.depth20_found}",
        f"- depth20_missing: {summary.depth20_missing}",
        f"- expected_edge_proxy_count: {summary.expected_edge_proxy_count}",
        f"- expected_edge_governed_count: {summary.expected_edge_governed_count}",
        f"- expected_edge_model_status: {summary.expected_edge_model_status}",
        f"- expected_edge_model_artifact_hash: {summary.expected_edge_model_artifact_hash}",
        f"- expected_edge_model_feature_hash: {summary.expected_edge_model_feature_hash}",
        f"- expected_edge_training_artifact_ref: {summary.expected_edge_training_artifact_ref or 'NOT_PROVEN'}",
        f"- expected_edge_label_source: {summary.expected_edge_label_source}",
        f"- expected_edge_label_fidelity: {summary.expected_edge_label_fidelity}",
        f"- expected_edge_anti_leakage_status: {summary.expected_edge_anti_leakage_status}",
        f"- expected_edge_walkforward_status: {summary.expected_edge_walkforward_status}",
        (
            f"- expected_edge_horizon: {summary.expected_edge_horizon}"
            if summary.expected_edge_horizon is not None
            else "- expected_edge_horizon: NOT_DECLARED"
        ),
        (
            f"- expected_edge_purge_window: {summary.expected_edge_purge_window}"
            if summary.expected_edge_purge_window is not None
            else "- expected_edge_purge_window: NOT_DECLARED"
        ),
        (
            f"- expected_edge_embargo_window: {summary.expected_edge_embargo_window}"
            if summary.expected_edge_embargo_window is not None
            else "- expected_edge_embargo_window: NOT_DECLARED"
        ),
        (
            f"- expected_edge_blocker_codes: {', '.join(summary.expected_edge_blocker_codes)}"
            if summary.expected_edge_blocker_codes
            else "- expected_edge_blocker_codes: none"
        ),
        f"- detailed_replay_count: {summary.detailed_replay_count}",
        f"- replay_record_count: {summary.replay_record_count}",
        f"- evaluation_record_count: {summary.evaluation_record_count}",
        f"- promotion_record_count: {summary.promotion_record_count}",
        f"- capital_bucket_record_count: {summary.capital_bucket_record_count}",
        (
            f"- replay_expansion_factor: {summary.replay_expansion_factor}"
            if summary.replay_expansion_factor is not None
            else "- replay_expansion_factor: NOT_PROVEN"
        ),
        f"- replay_expansion_axis: {summary.replay_expansion_axis or 'NOT_DECLARED'}",
        f"- matrix_count_inflation_status: {summary.matrix_count_inflation_status}",
        (
            f"- count_semantics_validator_codes: {', '.join(summary.count_semantics_validator_codes)}"
            if summary.count_semantics_validator_codes
            else "- count_semantics_validator_codes: none"
        ),
        f"- capital_profile_count: {summary.capital_profile_count}",
        "",
        "## Proxy & Fidelity Surface",
        f"- feature_store_pipeline_status: {proxy_surface.feature_store_pipeline_status}",
        f"- feature_row_sample_status: {proxy_surface.feature_row_sample_status}",
        f"- expected_edge_governance_status: {proxy_surface.expected_edge_governance_status}",
        f"- expected_edge_proxy_count: {summary.expected_edge_proxy_count}",
        f"- expected_edge_governed_count: {summary.expected_edge_governed_count}",
        f"- expected_edge_label_source: {summary.expected_edge_label_source}",
        f"- expected_edge_label_fidelity: {summary.expected_edge_label_fidelity}",
        f"- expected_edge_anti_leakage_status: {summary.expected_edge_anti_leakage_status}",
        f"- expected_edge_walkforward_status: {summary.expected_edge_walkforward_status}",
        (
            f"- expected_edge_horizon: {summary.expected_edge_horizon}"
            if summary.expected_edge_horizon is not None
            else "- expected_edge_horizon: NOT_DECLARED"
        ),
        (
            f"- expected_edge_purge_window: {summary.expected_edge_purge_window}"
            if summary.expected_edge_purge_window is not None
            else "- expected_edge_purge_window: NOT_DECLARED"
        ),
        (
            f"- expected_edge_embargo_window: {summary.expected_edge_embargo_window}"
            if summary.expected_edge_embargo_window is not None
            else "- expected_edge_embargo_window: NOT_DECLARED"
        ),
        f"- execution_label_source: {summary.execution_label_source}",
        f"- fee_model_source: {summary.fee_model_source}",
        f"- spread_model_source: {summary.spread_model_source}",
        f"- slippage_model_source: {summary.slippage_model_source}",
        f"- partial_fill_model_source: {summary.partial_fill_model_source}",
        f"- adverse_selection_source: {summary.adverse_selection_source}",
        f"- order_type_selection_source: {summary.order_type_selection_source}",
        f"- venue_constraints_source: {summary.venue_constraints_source}",
        f"- execution_fidelity_status: {proxy_surface.execution_fidelity_status}",
        (
            f"- execution_fidelity_gap_codes: {', '.join(summary.execution_fidelity_gap_codes)}"
            if summary.execution_fidelity_gap_codes
            else "- execution_fidelity_gap_codes: none"
        ),
        f"- threshold_calibration_status: {proxy_surface.threshold_calibration_status}",
        (
            f"- threshold_counts: default={proxy_surface.threshold_counts.default_count}, "
            f"calibrated={proxy_surface.threshold_counts.calibrated_count}, "
            f"calibration_not_proven={proxy_surface.threshold_counts.calibration_not_proven_count}"
        ),
        f"- silver_storage_status: {silver_storage_status}",
        (
            f"- silver_bloat_ratio: {silver_bloat_ratio}"
            if silver_bloat_ratio is not None
            else "- silver_bloat_ratio: NOT_PROVEN"
        ),
        f"- historical_replay_venue: {historical_replay_venue}",
        f"- execution_target_venue: {execution_target_venue}",
        f"- venue_transfer_status: {proxy_surface.venue_transfer_status}",
        f"- promotion_artifact_status: {proxy_surface.promotion_artifact_status}",
        f"- overall_backtest_proof_status: {proxy_surface.overall_backtest_proof_status}",
        (
            f"- expected_edge_blocker_codes: {', '.join(summary.expected_edge_blocker_codes)}"
            if summary.expected_edge_blocker_codes
            else "- expected_edge_blocker_codes: none"
        ),
        "",
        "## Governed Audit Evidence",
        f"- governed_evidence_status: {summary.governed_evidence_status}",
        f"- governed_audit_evidence_index_path: {summary.governed_audit_evidence_index_path or 'NOT_PROVEN'}",
        f"- audited_evidence_count: {summary.audited_evidence_count}",
        f"- scratch_only_evidence_count: {summary.scratch_only_evidence_count}",
        f"- promotion_grade_evidence_count: {summary.promotion_grade_evidence_count}",
        f"- run_manifest_evidence_class: {summary.run_manifest_evidence_class}",
        f"- capital_profiles_evidence_class: {summary.capital_profiles_evidence_class}",
        f"- engine_promotion_evidence_class: {summary.engine_promotion_evidence_class}",
        f"- pair_promotion_evidence_class: {summary.pair_promotion_evidence_class}",
        f"- strategy_promotion_evidence_class: {summary.strategy_promotion_evidence_class}",
        f"- sample_size_survival_evidence_class: {summary.sample_size_survival_evidence_class}",
        f"- trade_detail_ledger_evidence_class: {summary.trade_detail_ledger_evidence_class}",
        f"- refusal_ledger_evidence_class: {summary.refusal_ledger_evidence_class}",
        f"- loss_analysis_ledger_evidence_class: {summary.loss_analysis_ledger_evidence_class}",
        (
            f"- evidence_audit_blocker_codes: {', '.join(summary.evidence_audit_blocker_codes)}"
            if summary.evidence_audit_blocker_codes
            else "- evidence_audit_blocker_codes: none"
        ),
        "",
        "## Blockers",
        *(
            [f"- {blocker}" for blocker in summary.promotion_blockers]
            if summary.promotion_blockers
            else ["- none"]
        ),
        "",
        f"recommended_next_action: {summary.recommended_next_action}",
    ]
    atomic_write_text(reports_dir / "strategy_ladder_report.md", "\n".join(lines) + "\n")
    post_b2_refusal_audit = _build_post_b2_refusal_audit_payload(
        summary=summary,
        run_manifest=run_manifest,
        pair_artifacts=pair_artifacts,
        engine_artifacts=engine_artifacts,
        sample_artifacts=sample_artifacts,
        operator_artifact_refs=operator_artifact_refs,
    )
    atomic_write_json(
        reports_dir / "post_b2_refusal_audit.json",
        post_b2_refusal_audit,
    )
    atomic_write_text(
        reports_dir / "post_b2_refusal_audit.md",
        _format_post_b2_refusal_audit_markdown(post_b2_refusal_audit),
    )
    engine_no_trade_diagnosis = _build_engine_no_trade_diagnosis_payload(
        summary=summary,
        run_manifest=run_manifest,
        run_dir=reports_dir.parent,
        operator_artifact_refs=operator_artifact_refs,
        gold_manifest_payload=gold_manifest_payload,
    )
    atomic_write_json(
        reports_dir / "engine_no_trade_diagnosis.json",
        engine_no_trade_diagnosis,
    )
    atomic_write_text(
        reports_dir / "engine_no_trade_diagnosis.md",
        _format_engine_no_trade_diagnosis_markdown(engine_no_trade_diagnosis),
    )


def _build_governed_audit_evidence_entries(
    *,
    run_id: str,
    run_dir: Path,
    capital_profiles: tuple[CapitalBucketProfile, ...],
    engine_artifacts: tuple[EnginePromotionArtifact, ...],
    pair_artifacts: tuple[PairPromotionArtifact, ...],
    strategy_artifacts: tuple[StrategyPromotionArtifact, ...],
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...],
    operator_artifact_refs: dict[str, str],
) -> tuple[object, ...]:
    entries = [
        build_governed_audit_evidence_entry(
            rail_id=f"{run_id}:run_manifest",
            artifact_kind="run_manifest",
            artifact_ref=str((run_dir / "run_manifest.json").resolve()),
        ),
    ]
    for profile in capital_profiles:
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:capital_bucket:{profile.capital_bucket}",
                artifact_kind="capital_profile",
                artifact_ref=str((run_dir / "capital_profiles" / f"{profile.capital_bucket}.json").resolve()),
            )
        )
    for artifact in engine_artifacts:
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:engine:{artifact.engine_id}",
                artifact_kind="engine_promotion",
                artifact_ref=str((run_dir / "engine_promotion" / artifact.engine_id / f"{run_id}.json").resolve()),
            )
        )
    for artifact in pair_artifacts:
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:pair:{artifact.pair}",
                artifact_kind="pair_promotion",
                artifact_ref=str((run_dir / "pair_promotion" / artifact.pair / f"{run_id}.json").resolve()),
            )
        )
    for artifact in strategy_artifacts:
        strategy_id = str(artifact.strategy_id)
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:strategy:{strategy_id}",
                artifact_kind="strategy_promotion",
                artifact_ref=str((run_dir / "strategy_promotion" / strategy_id / f"{run_id}.json").resolve()),
            )
        )
    for artifact in sample_artifacts:
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:sample:{artifact.scope}:{artifact.id}",
                artifact_kind="sample_size_survival",
                artifact_ref=str((run_dir / "sample_size_survival" / artifact.scope / artifact.id / f"{run_id}.json").resolve()),
            )
        )
    for name, ref in sorted(operator_artifact_refs.items()):
        entries.append(
            build_governed_audit_evidence_entry(
                rail_id=f"{run_id}:operator:{name}",
                artifact_kind=name,
                artifact_ref=ref,
            )
        )
    return tuple(entries)


def _reason_domain(reason_code: str) -> str:
    upper = reason_code.upper()
    lower = reason_code.lower()
    if (
        upper.startswith("EXPECTED_EDGE_")
        or upper in {"FEE_AWARE_EDGE_PROXY_BLOCKED", "BREAK_EVEN_PROXY_BLOCKED"}
    ):
        return "governance"
    if "non_long" in lower or ".direction." in lower:
        return "direction"
    if "cost" in lower or "break_even" in lower or "no_excess" in lower:
        return "cost"
    if "microstructure" in lower or "structured_breakout" in lower or "breakout" in lower:
        return "microstructure"
    if "history" in lower or "closed_episode" in lower or "cold_start" in lower:
        return "history"
    if "not_applied" in lower or "missing" in lower or "wiring" in lower:
        return "wiring"
    return "unknown"


def _first_blocking_layer(reason_codes: tuple[str, ...]) -> str:
    if any(code.startswith("EXPECTED_EDGE_") for code in reason_codes):
        return "expected_edge_governance_gate"
    if "FEE_AWARE_EDGE_PROXY_BLOCKED" in reason_codes:
        return "fee_aware_edge_gate"
    if "BREAK_EVEN_PROXY_BLOCKED" in reason_codes:
        return "break_even_filter"
    if any(
        "history" in code.lower()
        or "closed_episode" in code.lower()
        or "cold_start" in code.lower()
        for code in reason_codes
    ):
        return "history_gate"
    if any("microstructure" in code.lower() for code in reason_codes):
        return "microstructure_gate"
    if any("non_long" in code.lower() for code in reason_codes):
        return "direction_gate"
    return "execution_rejected"


def _blocker_assessment(reason_codes: tuple[str, ...]) -> dict[str, object]:
    joined = " ".join(reason_codes)
    if "ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE" in reason_codes:
        return {
            "assessment": "HEALTHY_ENGINE_D_COLD_START_BLOCKER",
            "classification": "history",
            "note": "Engine D is correctly blocked because no real closed-episode source exists for re-entry context.",
        }
    if "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL" in reason_codes:
        return {
            "assessment": "SUSPECTED_WIRING_ISSUE",
            "classification": "history",
            "note": "Engine D is blocked by a missing required closed-episode history artifact.",
        }
    if "engine_c.microstructure.not_applied" in reason_codes:
        return {
            "assessment": "SUSPECTED_WIRING_ISSUE",
            "classification": "microstructure",
            "note": "Engine C reports microstructure.not_applied and should be audited for consumption/wiring.",
        }
    if any(code.startswith("EXPECTED_EDGE_") for code in reason_codes) or (
        "FEE_AWARE_EDGE_PROXY_BLOCKED" in reason_codes
        or "BREAK_EVEN_PROXY_BLOCKED" in reason_codes
    ):
        return {
            "assessment": "HEALTHY_GOVERNANCE_BLOCKER",
            "classification": "governance",
            "note": "Expected-edge governance is fail-closed and blocks selection before backtest truth is proven.",
        }
    if any(token in joined.lower() for token in ("non_long_direction", ".direction.non_long")):
        return {
            "assessment": "HEALTHY_STRATEGY_MARKET_BLOCKER",
            "classification": "direction",
            "note": "Direction filters reject setup quality; audit only if it overtriggers abnormally.",
        }
    if any(token in joined.lower() for token in ("cost_infeasible", "break_even_not_cleared", "no_excess")):
        return {
            "assessment": "HEALTHY_COST_BLOCKER",
            "classification": "cost",
            "note": "Cost and break-even constraints block economically weak setups.",
        }
    return {
        "assessment": "REVIEW_REQUIRED",
        "classification": _reason_domain(reason_codes[0]) if reason_codes else "unknown",
        "note": "Blocker needs manual review.",
    }


def _select_engine_specific_reason_counts(
    *,
    reason_counter: Counter[str],
    common_reason_codes: set[str],
) -> list[tuple[str, int]]:
    specific_reason_counts = [
        (code, count)
        for code, count in reason_counter.items()
        if code not in common_reason_codes
    ]
    non_build14_specific_reason_counts = [
        (code, count)
        for code, count in specific_reason_counts
        if not code.startswith("BUILD14_APPLIED:")
        and not code.startswith("BUILD14_READER:")
        and code != "BUILD14_SHADOW_ENABLED_ACTIVE"
    ]
    preferred_reason_counts = (
        non_build14_specific_reason_counts
        or specific_reason_counts
        or list(reason_counter.items())
    )
    preferred_reason_counts.sort(key=lambda item: (-item[1], item[0]))
    return preferred_reason_counts


def _build_post_b2_refusal_audit_payload(
    *,
    summary: StrategyLadderReportSummary,
    run_manifest: StrategyLadderRunManifest,
    pair_artifacts: tuple[PairPromotionArtifact, ...],
    engine_artifacts: tuple[EnginePromotionArtifact, ...],
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...],
    operator_artifact_refs: dict[str, str],
) -> dict[str, object]:
    refusal_rows = _load_jsonl_rows(Path(operator_artifact_refs.get("refusal_ledger", "")))
    trade_rows = _load_jsonl_rows(Path(operator_artifact_refs.get("trade_detail_ledger", "")))
    total_refusals = len(refusal_rows)
    reason_counter: Counter[str] = Counter()
    engine_reason_counter: dict[str, Counter[str]] = defaultdict(Counter)
    engine_counts: Counter[str] = Counter()
    bucket_counts: Counter[int] = Counter()
    common_reason_codes: set[str] | None = None
    for row in refusal_rows:
        engine_id = str(row.get("engine_id") or "unknown")
        engine_counts[engine_id] += 1
        reason_codes = tuple(
            str(code)
            for code in (row.get("reason_codes") or ())
            if isinstance(code, str) and code
        )
        current_set = set(reason_codes)
        if common_reason_codes is None:
            common_reason_codes = set(current_set)
        else:
            common_reason_codes &= current_set
        for code in current_set:
            reason_counter[code] += 1
            engine_reason_counter[engine_id][code] += 1
        capital_bucket = row.get("capital_bucket")
        if isinstance(capital_bucket, int):
            bucket_counts[capital_bucket] += 1
    common_reason_counts = sorted(
        (
            {
                "reason_code": code,
                "count": reason_counter[code],
                "pct_of_replay_records": round(
                    reason_counter[code] / summary.replay_record_count,
                    6,
                )
                if summary.replay_record_count > 0
                else 0.0,
            }
            for code in sorted(common_reason_codes or set())
        ),
        key=lambda item: (-int(item["count"]), str(item["reason_code"])),
    )
    engine_rows: list[dict[str, object]] = []
    for artifact in engine_artifacts:
        reason_counts = _select_engine_specific_reason_counts(
            reason_counter=engine_reason_counter.get(artifact.engine_id, Counter()),
            common_reason_codes=common_reason_codes or set(),
        )
        top_reason_codes = tuple(code for code, _ in reason_counts[:6])
        assessment = _blocker_assessment(top_reason_codes)
        engine_rows.append(
            {
                "engine_id": artifact.engine_id,
                "candidate_count": artifact.candidate_count,
                "record_count": artifact.record_count,
                "selected_count": artifact.selected_count,
                "executed_count": artifact.executed_count,
                "hard_blocked_count": artifact.hard_blocked_count,
                "top_blockers": [
                    {"reason_code": code, "count": count}
                    for code, count in reason_counts[:8]
                ],
                "first_blocking_layer": _first_blocking_layer(top_reason_codes),
                "blocker_classification": assessment["classification"],
                "blocker_assessment": assessment["assessment"],
                "assessment_note": assessment["note"],
            }
        )
    next_actions = [
        {
            "rank": "A",
            "action": "Run Backtest Circuit Coverage Scan",
            "rationale": "Establish full expected-vs-consumed coverage before deeper engine surgery.",
        },
        {
            "rank": "B",
            "action": "Fix/implement closed_episode_journal for Engine D history",
            "rationale": "Engine D shows a missing required history artifact, not just a healthy blocker.",
        },
        {
            "rank": "C",
            "action": "Audit Engine C microstructure consumption",
            "rationale": "microstructure.not_applied suggests a possible consumption or wiring gap.",
        },
        {
            "rank": "D",
            "action": "Build expected-edge governed dataset",
            "rationale": "Expected-edge governance blocks all 4000 records before selection.",
        },
        {
            "rank": "E",
            "action": "Upgrade execution realism for spread/slippage/adverse selection",
            "rationale": "Execution realism remains a healthy promotion blocker after selection is restored.",
        },
    ]
    pair_artifact = pair_artifacts[0] if pair_artifacts else None
    first_gate_reason_codes = tuple(
        code["reason_code"] for code in common_reason_counts[:5]
    )
    sample_size_status = next(
        (
            artifact.sample_size_survival_status
            for artifact in sample_artifacts
            if artifact.scope == "global"
        ),
        summary.sample_size_survival_status,
    )
    return {
        "schema_version": "v1",
        "run_id": summary.run_id,
        "workflow_run_id": summary.workflow_run_id,
        "phase_run_id": summary.phase_run_id,
        "source_status": "ok" if total_refusals > 0 else "missing",
        "final_status": summary.final_status,
        "evidence": {
            "governed_evidence_status": summary.governed_evidence_status,
            "refusal_ledger_evidence_class": summary.refusal_ledger_evidence_class,
            "sample_size_survival_evidence_class": summary.sample_size_survival_evidence_class,
            "trade_detail_ledger_evidence_class": summary.trade_detail_ledger_evidence_class,
        },
        "candidate_funnel": {
            "discovery_pre_candidates": summary.discovery_pre_candidate_count or summary.candidate_count,
            "engine_native_candidates": summary.engine_native_candidate_count,
            "engine_native_preselected": summary.engine_native_preselected_count,
            "b2_replay_candidates": summary.b2_replay_candidate_count,
            "trade_eligible_candidates": summary.trade_eligible_candidate_count,
            "replay_records": summary.replay_record_count,
            "selected_count": pair_artifact.selected_count if pair_artifact is not None else 0,
            "executed_count": pair_artifact.executed_count if pair_artifact is not None else 0,
            "hard_blocked_count": pair_artifact.hard_blocked_count if pair_artifact is not None else total_refusals,
            "trade_rows": len(trade_rows),
            "refusal_rows": total_refusals,
        },
        "common_blockers": common_reason_counts,
        "first_gate_analysis": {
            "gate_status": "FIRST_GATE_BLOCKS_BEFORE_SELECTION"
            if pair_artifact is not None and pair_artifact.selected_count == 0
            else "FIRST_GATE_NOT_PROVEN",
            "first_gate_reason_codes": first_gate_reason_codes,
            "explanation": (
                "Selection collapses before execution because governance and proxy cost gates block all replay records."
            ),
        },
        "engine_specific_blockers": engine_rows,
        "capital_bucket_distribution": [
            {
                "capital_bucket": bucket,
                "replay_record_count": bucket_counts[bucket],
                "selected_count": 0,
                "hard_blocked_count": bucket_counts[bucket],
            }
            for bucket in sorted(bucket_counts)
        ],
        "healthy_vs_suspected": [
            {
                "issue": "EXPECTED_EDGE_PROXY_BLOCKED",
                "status": "HEALTHY_GOVERNANCE_BLOCKER",
                "note": "Expected-edge proxy is discovery-only and must not clear backtest truth.",
            },
            {
                "issue": "SPREAD/SLIPPAGE/ADVERSE_SELECTION_PROXY",
                "status": "HEALTHY_PROMOTION_BLOCKER",
                "note": "Execution realism remains promotion-blocked until measured fidelity exists.",
            },
            {
                "issue": "ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE",
                "status": "HEALTHY_ENGINE_D_COLD_START_BLOCKER",
                "note": "Engine D is not executable until a real closed-episode source exists.",
            },
            {
                "issue": "engine_c.microstructure.not_applied",
                "status": "SUSPECTED_WIRING_ISSUE",
                "note": "Engine C microstructure consumption should be audited explicitly.",
            },
            {
                "issue": "non_long_direction",
                "status": "HEALTHY_STRATEGY_MARKET_BLOCKER",
                "note": "Direction filters are acceptable unless they overtrigger abnormally.",
            },
        ],
        "next_action_ranking": next_actions,
        "profitability_claim_allowed": False,
        "profitability_claim_blocker": (
            "SELECTED_COUNT_ZERO_NO_PROFITABILITY_CLAIM"
            if pair_artifact is not None and pair_artifact.selected_count == 0
            else "NOT_APPLICABLE"
        ),
        "sample_size_status": sample_size_status,
        "request_window": {
            "start": run_manifest.start,
            "end": run_manifest.end,
            "pair": (
                run_manifest.pairs[0]
                if run_manifest.pairs
                else ""
            ),
        },
    }


def _format_post_b2_refusal_audit_markdown(payload: dict[str, object]) -> str:
    funnel = dict(payload.get("candidate_funnel") or {})
    common_blockers = tuple(payload.get("common_blockers") or ())
    engine_rows = tuple(payload.get("engine_specific_blockers") or ())
    bucket_rows = tuple(payload.get("capital_bucket_distribution") or ())
    next_actions = tuple(payload.get("next_action_ranking") or ())
    lines = [
        "# Post-B2 Refusal Audit",
        "",
        f"- run_id: {payload.get('run_id')}",
        f"- workflow_run_id: {payload.get('workflow_run_id')}",
        f"- phase_run_id: {payload.get('phase_run_id')}",
        f"- final_status: {payload.get('final_status')}",
        f"- source_status: {payload.get('source_status')}",
        f"- profitability_claim_allowed: {payload.get('profitability_claim_allowed')}",
        f"- profitability_claim_blocker: {payload.get('profitability_claim_blocker')}",
        "",
        "## Candidate Funnel",
        f"- discovery_pre_candidates: {funnel.get('discovery_pre_candidates', 0)}",
        f"- engine_native_candidates: {funnel.get('engine_native_candidates', 0)}",
        f"- engine_native_preselected: {funnel.get('engine_native_preselected', 0)}",
        f"- b2_replay_candidates: {funnel.get('b2_replay_candidates', 0)}",
        f"- trade_eligible_candidates: {funnel.get('trade_eligible_candidates', 0)}",
        f"- replay_records: {funnel.get('replay_records', 0)}",
        f"- selected_count: {funnel.get('selected_count', 0)}",
        f"- executed_count: {funnel.get('executed_count', 0)}",
        f"- hard_blocked_count: {funnel.get('hard_blocked_count', 0)}",
        "",
        "## Common Blockers",
    ]
    lines.extend(
        f"- {row.get('reason_code')}: count={row.get('count')}, pct={row.get('pct_of_replay_records')}"
        for row in common_blockers
    )
    lines.extend(
        [
            "",
            "## Engine-Specific Blocker Analysis",
        ]
    )
    for row in engine_rows:
        lines.extend(
            [
                f"- {row.get('engine_id')}:",
                f"  - first_blocking_layer: {row.get('first_blocking_layer')}",
                f"  - blocker_classification: {row.get('blocker_classification')}",
                f"  - blocker_assessment: {row.get('blocker_assessment')}",
                f"  - assessment_note: {row.get('assessment_note')}",
                "  - top_blockers: "
                + ", ".join(
                    f"{item.get('reason_code')}({item.get('count')})"
                    for item in (row.get('top_blockers') or ())
                ),
            ]
        )
    lines.extend(["", "## Capital Bucket Distribution"])
    lines.extend(
        f"- bucket={row.get('capital_bucket')}: replay_records={row.get('replay_record_count')}, selected={row.get('selected_count')}, hard_blocked={row.get('hard_blocked_count')}"
        for row in bucket_rows
    )
    first_gate = dict(payload.get("first_gate_analysis") or {})
    lines.extend(
        [
            "",
            "## First-Gate Analysis",
            f"- gate_status: {first_gate.get('gate_status')}",
            "- first_gate_reason_codes: "
            + ", ".join(first_gate.get("first_gate_reason_codes") or ()),
            f"- explanation: {first_gate.get('explanation')}",
            "",
            "## Healthy Blockers vs Suspected Wiring Issues",
        ]
    )
    lines.extend(
        f"- {item.get('issue')}: {item.get('status')} - {item.get('note')}"
        for item in (payload.get("healthy_vs_suspected") or ())
    )
    lines.extend(["", "## Next Action Ranking"])
    lines.extend(
        f"- {item.get('rank')}. {item.get('action')}: {item.get('rationale')}"
        for item in next_actions
    )
    evidence = dict(payload.get("evidence") or {})
    lines.extend(
        [
            "",
            "## Evidence",
            f"- governed_evidence_status: {evidence.get('governed_evidence_status')}",
            f"- refusal_ledger_evidence_class: {evidence.get('refusal_ledger_evidence_class')}",
            f"- sample_size_survival_evidence_class: {evidence.get('sample_size_survival_evidence_class')}",
            f"- trade_detail_ledger_evidence_class: {evidence.get('trade_detail_ledger_evidence_class')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_compatibility_payload(candidate_row: dict[str, object]) -> dict[str, object]:
    compatibility_payload = candidate_row.get("compatibility_payload")
    return compatibility_payload if isinstance(compatibility_payload, dict) else {}


def _row_reason_codes(row: dict[str, object], *, field_name: str = "reason_codes") -> tuple[str, ...]:
    return tuple(
        str(code)
        for code in (row.get(field_name) or ())
        if isinstance(code, str) and code
    )


def _reason_count_matches(reason_counter: Counter[str], *, tokens: tuple[str, ...]) -> int:
    total = 0
    lowered_tokens = tuple(token.lower() for token in tokens)
    for code, count in reason_counter.items():
        lowered_code = code.lower()
        if any(token in lowered_code for token in lowered_tokens):
            total += count
    return total


def _reason_row_count_matches(
    refusal_rows: list[dict[str, object]],
    *,
    tokens: tuple[str, ...],
) -> int:
    lowered_tokens = tuple(token.lower() for token in tokens)
    count = 0
    for row in refusal_rows:
        reason_codes = {
            code.lower()
            for code in _row_reason_codes(row)
        }
        if any(any(token in code for token in lowered_tokens) for code in reason_codes):
            count += 1
    return count


def _top_reason_rows(
    reason_counter: Counter[str],
    *,
    common_reason_codes: set[str],
    limit: int = 10,
) -> list[dict[str, object]]:
    specific_reason_counts = [
        (code, count)
        for code, count in reason_counter.items()
        if code not in common_reason_codes
    ]
    non_build14_reason_counts = [
        (code, count)
        for code, count in specific_reason_counts
        if not code.startswith("BUILD14_APPLIED:")
        and not code.startswith("BUILD14_READER:")
        and code != "BUILD14_SHADOW_ENABLED_ACTIVE"
    ]
    preferred_reason_counts = (
        non_build14_reason_counts
        or specific_reason_counts
        or list(reason_counter.items())
    )
    preferred_reason_counts.sort(key=lambda item: (-item[1], item[0]))
    return [
        {"reason_code": code, "count": count}
        for code, count in preferred_reason_counts[:limit]
    ]


def _status_from_count(
    *,
    present_count: int,
    ready_in_gold: bool,
    present_status: str,
    missing_from_payload_status: str,
    group_not_ready_status: str,
) -> str:
    if present_count > 0:
        return present_status
    if ready_in_gold:
        return missing_from_payload_status
    return group_not_ready_status


def _find_closed_episode_journal(workflow_root: Path) -> dict[str, object]:
    manifest_candidates = sorted(workflow_root.rglob("closed_episode_manifest.json"))
    jsonl_candidates = sorted(workflow_root.rglob("closed_episodes.jsonl"))
    manifest_path = manifest_candidates[0] if manifest_candidates else None
    jsonl_path = jsonl_candidates[0] if jsonl_candidates else None
    if manifest_path is None and jsonl_path is None:
        return {
            "status": "CLOSED_EPISODE_JOURNAL_NOT_GENERATED",
            "path": "",
            "record_count": 0,
            "source_status": "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE",
        }
    manifest_payload = _load_json_payload(manifest_path) if manifest_path is not None else {}
    record_count = int(manifest_payload.get("record_count") or 0)
    if record_count <= 0 and jsonl_path is not None:
        record_count = len(_load_jsonl_rows(jsonl_path))
    status = str(manifest_payload.get("status") or "")
    source_status = str(manifest_payload.get("source_status") or "")
    if not status:
        if manifest_path is not None and jsonl_path is not None:
            status = (
                "CLOSED_EPISODE_JOURNAL_READY"
                if record_count > 0
                else "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
            )
        elif manifest_path is not None:
            status = "CLOSED_EPISODE_JOURNAL_MANIFEST_ONLY"
        else:
            status = (
                "CLOSED_EPISODE_JOURNAL_JSONL_ONLY"
                if record_count > 0
                else "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
            )
    if not source_status:
        source_status = (
            "CLOSED_EPISODE_SOURCE_EXECUTED_TRADES"
            if record_count > 0
            else "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE"
        )
    return {
        "status": status,
        "path": str((manifest_path or jsonl_path).resolve()),
        "record_count": record_count,
        "source_status": source_status,
    }


def _build_engine_d_diagnosis(
    *,
    candidate_rows: list[dict[str, object]],
    reason_counter: Counter[str],
    common_reason_codes: set[str],
    workflow_root: Path,
) -> dict[str, object]:
    journal_state = _find_closed_episode_journal(workflow_root)
    journal_status = str(journal_state["status"])
    journal_record_count = int(journal_state["record_count"])
    compat_rows = tuple(_candidate_compatibility_payload(row) for row in candidate_rows)
    first_episode_present = any(
        any(str(compat.get(field) or "").strip() for field in ("first_episode_id", "first_episode_engine_id", "first_episode_close_reason"))
        for compat in compat_rows
    )
    history_score_present = any(isinstance(compat.get("history_score"), (int, float)) for compat in compat_rows)
    marginal_value_present = any(
        isinstance(compat.get("marginal_value_score"), (int, float)) for compat in compat_rows
    )
    anti_revenge_present = any(str(compat.get("anti_revenge_state") or "").strip() for compat in compat_rows)
    reentry_age_present = any(isinstance(compat.get("reentry_lateness"), (int, float)) for compat in compat_rows)
    if first_episode_present:
        first_episode_ref_status = "FIRST_EPISODE_REF_PRESENT"
    elif journal_record_count > 0:
        first_episode_ref_status = "FIRST_EPISODE_REF_NOT_LINKED"
    else:
        first_episode_ref_status = "FIRST_EPISODE_REF_MISSING"
    if journal_status == "CLOSED_EPISODE_JOURNAL_NOT_GENERATED":
        history_input_status = "REQUIRED_FOR_ENGINE_D_BUT_NOT_AVAILABLE_IN_B2"
    elif journal_record_count <= 0:
        history_input_status = "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE"
    elif not first_episode_present:
        history_input_status = "ENGINE_D_HISTORY_INPUT_NOT_CONSUMED"
    else:
        history_input_status = "ENGINE_D_HISTORY_INPUT_READY"
    suspected_wiring_gaps: list[str] = []
    if history_input_status == "REQUIRED_FOR_ENGINE_D_BUT_NOT_AVAILABLE_IN_B2":
        suspected_wiring_gaps.extend(
            [
                "ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE",
                journal_status,
                history_input_status,
            ]
        )
        recommended_next_action = "PROVIDE_REAL_CLOSED_EPISODE_SOURCE_FOR_ENGINE_D"
    elif history_input_status == "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE":
        suspected_wiring_gaps.extend(
            [
                journal_status,
                history_input_status,
            ]
        )
        recommended_next_action = (
            "PRODUCE_VALID_CLOSED_EPISODES_BEFORE_EVALUATING_ENGINE_D"
        )
    elif history_input_status == "ENGINE_D_HISTORY_INPUT_NOT_CONSUMED":
        suspected_wiring_gaps.extend(
            [
                journal_status,
                history_input_status,
                first_episode_ref_status,
            ]
        )
        recommended_next_action = "LINK_FIRST_EPISODE_REFS_FOR_ENGINE_D"
    else:
        recommended_next_action = "NO_ACTION_REQUIRED"
    top_reason_rows = _top_reason_rows(
        reason_counter,
        common_reason_codes=common_reason_codes,
        limit=10,
    )
    top_reason_codes = tuple(str(item["reason_code"]) for item in top_reason_rows)
    return {
        "closed_episode_journal_status": str(journal_state["status"]),
        "closed_episode_journal_path": str(journal_state["path"]),
        "closed_episode_count": int(journal_state["record_count"]),
        "closed_episode_source_status": str(journal_state.get("source_status") or ""),
        "engine_d_history_input_status": history_input_status,
        "first_episode_ref_status": first_episode_ref_status,
        "history_score_status": (
            "HISTORY_SCORE_PRESENT"
            if history_score_present
            else "HISTORY_SCORE_BLOCKED_BY_MISSING_FIRST_EPISODE"
        ),
        "marginal_value_score_status": (
            "MARGINAL_VALUE_SCORE_PRESENT"
            if marginal_value_present
            else "MARGINAL_VALUE_SCORE_BLOCKED_BY_MISSING_FIRST_EPISODE"
        ),
        "anti_revenge_state_status": (
            "ANTI_REVENGE_STATE_PRESENT"
            if anti_revenge_present
            else "ANTI_REVENGE_STATE_BLOCKED_BY_MISSING_FIRST_EPISODE"
        ),
        "reentry_age_status": (
            "REENTRY_AGE_PRESENT"
            if reentry_age_present
            else "REENTRY_AGE_BLOCKED_BY_MISSING_FIRST_EPISODE"
        ),
        "first_blocking_layer": _first_blocking_layer(top_reason_codes),
        "healthy_blockers": [
            code
            for code in sorted(common_reason_codes)
            if code in reason_counter
        ],
        "suspected_wiring_gaps": tuple(dict.fromkeys(suspected_wiring_gaps)),
        "recommended_next_action": recommended_next_action,
    }


def _build_engine_c_diagnosis(
    *,
    candidate_rows: list[dict[str, object]],
    reason_counter: Counter[str],
    common_reason_codes: set[str],
    gold_manifest_payload: dict[str, object],
) -> dict[str, object]:
    if not candidate_rows:
        return {
            "engine_c_microstructure_input_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "engine_c_microstructure_consumption_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "vpin_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "ofi_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "queue_pressure_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "spread_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "depth_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "fragility_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "false_breakout_context_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "micro_edge_entry_timing_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "micro_edge_exit_governor_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "fragility_block_status": "ENGINE_C_NOT_PRESENT_IN_B2",
            "first_blocking_layer": "upstream_preselection",
            "healthy_blockers": [],
            "suspected_wiring_gaps": (),
            "recommended_next_action": "AUDIT_ENGINE_C_B1_BREAKOUT_ELIGIBILITY",
        }
    ready_groups = {
        str(group)
        for group in (gold_manifest_payload.get("feature_groups_ready") or ())
        if isinstance(group, str) and group
    }
    micro_groups_ready = bool(
        ready_groups
        & {
            "flow_microstructure_features",
            "ofi_features",
            "vpin_features",
            "queue_pressure",
        }
    )
    spread_group_ready = bool(
        ready_groups & {"book_liquidity_features", "spread_features"}
    )
    depth_group_ready = bool(
        ready_groups & {"book_liquidity_features", "depth_features"}
    )
    fragility_group_ready = bool(
        ready_groups & {"fragility_false_breakout_features"}
    )
    compat_rows = tuple(_candidate_compatibility_payload(row) for row in candidate_rows)
    vpin_present = sum(1 for compat in compat_rows if isinstance(compat.get("vpin"), (int, float)))
    ofi_present = sum(
        1
        for compat in compat_rows
        if isinstance(compat.get("cumulative_ofi"), (int, float))
        or isinstance(compat.get("ofi"), (int, float))
    )
    queue_present = sum(
        1 for compat in compat_rows if isinstance(compat.get("queue_pressure"), (int, float))
    )
    spread_present = sum(
        1 for compat in compat_rows if isinstance(compat.get("spread_bps"), (int, float))
    )
    depth_present = sum(
        1
        for compat in compat_rows
        if isinstance(compat.get("book_depth_levels"), int) and int(compat.get("book_depth_levels") or 0) > 0
    )
    fragility_present = sum(
        1
        for compat in compat_rows
        if str(compat.get("build14_shadow_activation_status") or "") == "BUILD14_SHADOW_ENABLED_ACTIVE"
        or any(
            code.startswith("BUILD14_READER:execution_fragility_score:")
            for code in _row_reason_codes(compat, field_name="build14_shadow_reason_codes")
        )
    )
    false_breakout_present = sum(
        1
        for compat in compat_rows
        if isinstance(compat.get("false_breakout_context"), (int, float))
        or any(
            "false_breakout_model" in code
            for code in _row_reason_codes(compat, field_name="build14_shadow_reason_codes")
        )
    )
    micro_edge_entry_timing_present = sum(
        1
        for compat in compat_rows
        if isinstance(compat.get("micro_edge_entry_timing"), (int, float))
    )
    micro_edge_exit_governor_present = sum(
        1
        for compat in compat_rows
        if isinstance(compat.get("micro_edge_exit_governor"), (int, float))
    )
    micro_not_applied = any("engine_c.microstructure.not_applied" in code for code in reason_counter)
    fragility_blocked = any(
        code.startswith("BUILD14_READER:execution_fragility_score:")
        or code.startswith("BUILD14_READER:false_breakout_model:")
        for compat in compat_rows
        for code in _row_reason_codes(compat, field_name="build14_shadow_reason_codes")
    )
    core_present = any(count > 0 for count in (vpin_present, ofi_present, queue_present))
    if core_present:
        input_status = "ENGINE_C_MICROSTRUCTURE_INPUT_PRESENT_IN_REPLAY_PAYLOAD"
    elif micro_groups_ready:
        input_status = "ENGINE_C_MICROSTRUCTURE_MISSING_FROM_REPLAY_PAYLOAD"
    else:
        input_status = "ENGINE_C_MICROSTRUCTURE_GROUP_NOT_READY"
    if micro_not_applied and core_present:
        consumption_status = "ENGINE_C_MICROSTRUCTURE_PRESENT_BUT_NOT_CONSUMED"
    elif micro_not_applied or not core_present:
        consumption_status = "ENGINE_C_MICROSTRUCTURE_MISSING_FROM_REPLAY_PAYLOAD"
    elif fragility_blocked:
        consumption_status = "ENGINE_C_MICROSTRUCTURE_CONSUMED_BUT_BLOCKED_BY_FRAGILITY"
    else:
        consumption_status = "ENGINE_C_MICROSTRUCTURE_CONSUMED"
    suspected_wiring_gaps: list[str] = []
    if consumption_status in {
        "ENGINE_C_MICROSTRUCTURE_PRESENT_BUT_NOT_CONSUMED",
        "ENGINE_C_MICROSTRUCTURE_MISSING_FROM_REPLAY_PAYLOAD",
    }:
        suspected_wiring_gaps.append(consumption_status)
    top_reason_rows = _top_reason_rows(
        reason_counter,
        common_reason_codes=common_reason_codes,
        limit=10,
    )
    top_reason_codes = tuple(str(item["reason_code"]) for item in top_reason_rows)
    return {
        "engine_c_microstructure_input_status": input_status,
        "engine_c_microstructure_consumption_status": consumption_status,
        "vpin_context_status": _status_from_count(
            present_count=vpin_present,
            ready_in_gold=micro_groups_ready,
            present_status="VPIN_PRESENT_IN_REPLAY_PAYLOAD",
            missing_from_payload_status="VPIN_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD",
            group_not_ready_status="VPIN_GROUP_NOT_READY",
        ),
        "ofi_context_status": _status_from_count(
            present_count=ofi_present,
            ready_in_gold=micro_groups_ready,
            present_status="OFI_PRESENT_IN_REPLAY_PAYLOAD",
            missing_from_payload_status="OFI_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD",
            group_not_ready_status="OFI_GROUP_NOT_READY",
        ),
        "queue_pressure_context_status": _status_from_count(
            present_count=queue_present,
            ready_in_gold=micro_groups_ready,
            present_status="QUEUE_PRESSURE_PRESENT_IN_REPLAY_PAYLOAD",
            missing_from_payload_status="QUEUE_PRESSURE_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD",
            group_not_ready_status="QUEUE_PRESSURE_GROUP_NOT_READY",
        ),
        "spread_context_status": _status_from_count(
            present_count=spread_present,
            ready_in_gold=spread_group_ready,
            present_status="SPREAD_PRESENT_IN_REPLAY_PAYLOAD",
            missing_from_payload_status="SPREAD_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD",
            group_not_ready_status="SPREAD_GROUP_NOT_READY",
        ),
        "depth_context_status": _status_from_count(
            present_count=depth_present,
            ready_in_gold=depth_group_ready,
            present_status="DEPTH_PRESENT_IN_REPLAY_PAYLOAD",
            missing_from_payload_status="DEPTH_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD",
            group_not_ready_status="DEPTH_GROUP_NOT_READY",
        ),
        "fragility_context_status": (
            "FRAGILITY_PRESENT_IN_REPLAY_PAYLOAD"
            if fragility_present > 0
            else "FRAGILITY_GROUP_NOT_READY"
            if not fragility_group_ready
            else "FRAGILITY_NOT_PROVEN"
        ),
        "false_breakout_context_status": (
            "FALSE_BREAKOUT_PRESENT_IN_REPLAY_PAYLOAD"
            if false_breakout_present > 0
            else "FALSE_BREAKOUT_GROUP_NOT_READY"
            if not fragility_group_ready
            else "FALSE_BREAKOUT_NOT_PROVEN"
        ),
        "micro_edge_entry_timing_status": (
            "MICRO_EDGE_ENTRY_TIMING_PRESENT"
            if micro_edge_entry_timing_present > 0
            else "MICRO_EDGE_ENTRY_TIMING_NOT_PROVEN"
        ),
        "micro_edge_exit_governor_status": (
            "MICRO_EDGE_EXIT_GOVERNOR_PRESENT"
            if micro_edge_exit_governor_present > 0
            else "MICRO_EDGE_EXIT_GOVERNOR_NOT_PROVEN"
        ),
        "fragility_block_status": (
            "ENGINE_C_MICROSTRUCTURE_CONSUMED_BUT_BLOCKED_BY_FRAGILITY"
            if consumption_status == "ENGINE_C_MICROSTRUCTURE_CONSUMED_BUT_BLOCKED_BY_FRAGILITY"
            else "FRAGILITY_NOT_PROVEN"
        ),
        "first_blocking_layer": _first_blocking_layer(top_reason_codes),
        "healthy_blockers": [
            code
            for code in sorted(common_reason_codes)
            if code in reason_counter
        ],
        "suspected_wiring_gaps": tuple(dict.fromkeys(suspected_wiring_gaps)),
        "recommended_next_action": (
            "FIX_ENGINE_C_MICROSTRUCTURE_CONSUMPTION"
            if suspected_wiring_gaps
            else "BUILD_EXPECTED_EDGE_GOVERNED_DATASET"
        ),
    }


_NEXT_ACTION_RATIONALES: dict[str, str] = {
    "RUN_BACKTEST_CIRCUIT_COVERAGE_SCAN": "Measure feature-generation, payload transport, and engine-consumption coverage end to end.",
    "BUILD_CLOSED_EPISODE_JOURNAL_FOR_ENGINE_D": "Engine D requires closed-episode history and the journal is not generated yet.",
    "PRODUCE_VALID_CLOSED_EPISODES_BEFORE_EVALUATING_ENGINE_D": "Engine D has no valid closed-episode source yet; generating an empty journal is not sufficient.",
    "LINK_FIRST_EPISODE_REFS_FOR_ENGINE_D": "Engine D has closed episodes on disk but they are not linked into replay payloads.",
    "AUDIT_ENGINE_C_B1_BREAKOUT_ELIGIBILITY": "Engine C is filtered out before B2 and should be audited at B1 breakout eligibility first.",
    "FIX_ENGINE_C_MICROSTRUCTURE_CONSUMPTION": "Gold feature groups exist, but core Engine C microstructure inputs are missing or not consumed in replay payloads.",
    "BUILD_EXPECTED_EDGE_GOVERNED_DATASET": "Expected-edge governance stays fail-closed and blocks selection for every replay record.",
    "UPGRADE_EXECUTION_REALISM_FOR_SPREAD_SLIPPAGE_ADVERSE_SELECTION": "Execution realism remains a healthy blocker even after selection issues are understood.",
}


def _next_action_row(rank: str, action: str) -> dict[str, str]:
    return {
        "rank": rank,
        "action": action,
        "rationale": _NEXT_ACTION_RATIONALES.get(
            action,
            "Investigate the engine-specific blocker before widening the backtest claim.",
        ),
    }


def _build_engine_ab_direction_cost_diagnosis(
    *,
    engine_id: str,
    candidate_rows: list[dict[str, object]],
    refusal_rows: list[dict[str, object]],
    reason_counter: Counter[str],
    common_reason_codes: set[str],
) -> dict[str, object]:
    compat_rows = tuple(_candidate_compatibility_payload(row) for row in candidate_rows)
    native_reason_codes = {
        code
        for compat in compat_rows
        for code in _row_reason_codes(compat, field_name="engine_native_reason_codes")
    }
    non_long_direction_count = _reason_row_count_matches(
        refusal_rows,
        tokens=("non_long_direction", ".direction.non_long"),
    )
    cost_infeasible_count = _reason_row_count_matches(
        refusal_rows,
        tokens=("cost_infeasible", ".cost.infeasible"),
    )
    break_even_not_cleared_count = _reason_row_count_matches(
        refusal_rows,
        tokens=("break_even_not_cleared",),
    )
    structure_unfavorable_count = _reason_row_count_matches(
        refusal_rows,
        tokens=("structure.unfavorable",),
    )
    no_excess_count = _reason_row_count_matches(
        refusal_rows,
        tokens=("no_excess",),
    )
    if native_reason_codes and any("direction.non_long" in code for code in native_reason_codes):
        direction_mapping_status = "ENGINE_A_B_DIRECTION_MAPPING_PROVEN_FROM_ENGINE_NATIVE_REASON_CODES"
    else:
        direction_mapping_status = "ENGINE_A_B_DIRECTION_MAPPING_NOT_PROVEN"
    long_only_filter_status = (
        "LONG_ONLY_GOVERNANCE_BLOCKED_NON_LONG_CONTEXT"
        if non_long_direction_count > 0
        and direction_mapping_status != "ENGINE_A_B_DIRECTION_MAPPING_NOT_PROVEN"
        else "LONG_ONLY_FILTER_NOT_PROVEN"
    )
    top_reason_rows = _top_reason_rows(
        reason_counter,
        common_reason_codes=common_reason_codes,
        limit=10,
    )
    top_reason_codes = tuple(str(item["reason_code"]) for item in top_reason_rows)
    suspected_wiring_gaps = (
        ("ENGINE_A_B_DIRECTION_MAPPING_NOT_PROVEN",)
        if direction_mapping_status == "ENGINE_A_B_DIRECTION_MAPPING_NOT_PROVEN"
        else ()
    )
    return {
        "direction_input_status": (
            "ENGINE_NATIVE_DIRECTION_INPUT_PRESENT"
            if compat_rows
            else "DIRECTION_INPUT_NOT_PROVEN"
        ),
        "long_only_filter_status": long_only_filter_status,
        "direction_mapping_status": direction_mapping_status,
        "break_even_gate_status": (
            "BREAK_EVEN_GATE_BLOCKER_ONLY_PROXY"
            if "BREAK_EVEN_PROXY_BLOCKED" in common_reason_codes
            else "BREAK_EVEN_GATE_NOT_PROVEN"
        ),
        "fee_aware_edge_gate_status": (
            "FEE_AWARE_EDGE_GATE_BLOCKER_ONLY_PROXY"
            if "FEE_AWARE_EDGE_PROXY_BLOCKED" in common_reason_codes
            else "FEE_AWARE_EDGE_GATE_NOT_PROVEN"
        ),
        "aggregated_blocker_counts": {
            "non_long_direction": non_long_direction_count,
            "cost_infeasible": cost_infeasible_count,
            "break_even_not_cleared": break_even_not_cleared_count,
            "structure_unfavorable": structure_unfavorable_count,
            "no_excess": no_excess_count,
        },
        "first_blocking_layer": _first_blocking_layer(top_reason_codes),
        "healthy_blockers": tuple(
            dict.fromkeys(
                [
                    *sorted(code for code in common_reason_codes if code in reason_counter),
                    *(
                        ["LONG_ONLY_GOVERNANCE_BLOCKED_NON_LONG_CONTEXT"]
                        if long_only_filter_status == "LONG_ONLY_GOVERNANCE_BLOCKED_NON_LONG_CONTEXT"
                        else []
                    ),
                ]
            )
        ),
        "suspected_wiring_gaps": suspected_wiring_gaps,
        "recommended_next_action": (
            "AUDIT_ENGINE_A_B_DIRECTION_MAPPING"
            if suspected_wiring_gaps
            else "BUILD_EXPECTED_EDGE_GOVERNED_DATASET"
        ),
        "engine_id": engine_id,
    }


def _build_engine_no_trade_diagnosis_payload(
    *,
    summary: StrategyLadderReportSummary,
    run_manifest: StrategyLadderRunManifest,
    run_dir: Path,
    operator_artifact_refs: dict[str, str],
    gold_manifest_payload: dict[str, object],
) -> dict[str, object]:
    candidate_rows = _load_jsonl_rows(run_dir / "fast_candidates" / "candidate_events.jsonl")
    refusal_rows = _load_jsonl_rows(Path(operator_artifact_refs.get("refusal_ledger", "")))
    try:
        engine_matrix_payload = json.loads(
            (run_dir / "reports" / "engine_matrix.json").read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError):
        engine_matrix_payload = []
    engine_matrix_rows = tuple(
        row
        for row in (engine_matrix_payload if isinstance(engine_matrix_payload, list) else ())
        if isinstance(row, dict)
    )
    engine_matrix_index = {
        str(row.get("engine_id") or ""): row
        for row in engine_matrix_rows
        if isinstance(row, dict) and str(row.get("engine_id") or "")
    }
    candidate_rows_by_engine: dict[str, list[dict[str, object]]] = defaultdict(list)
    refusal_rows_by_engine: dict[str, list[dict[str, object]]] = defaultdict(list)
    reason_counter: Counter[str] = Counter()
    common_reason_codes: set[str] | None = None
    for row in candidate_rows:
        candidate_rows_by_engine[str(row.get("engine_id") or "unknown")].append(row)
    for row in refusal_rows:
        engine_id = str(row.get("engine_id") or "unknown")
        refusal_rows_by_engine[engine_id].append(row)
        reason_codes = _row_reason_codes(row)
        current_set = set(reason_codes)
        if common_reason_codes is None:
            common_reason_codes = set(current_set)
        else:
            common_reason_codes &= current_set
        for code in current_set:
            reason_counter[code] += 1
    resolved_common_codes = common_reason_codes or set()
    common_blockers = [
        {
            "reason_code": code,
            "count": reason_counter[code],
            "pct_of_replay_records": round(
                reason_counter[code] / summary.replay_record_count,
                6,
            )
            if summary.replay_record_count > 0
            else 0.0,
        }
        for code in sorted(
            resolved_common_codes,
            key=lambda item: (-reason_counter[item], item),
        )
    ]
    engine_rows: list[dict[str, object]] = []
    workflow_root = run_dir
    for engine_id in ("engine_a", "engine_b", "engine_c", "engine_d"):
        engine_candidate_rows = candidate_rows_by_engine.get(engine_id, [])
        engine_refusal_rows = refusal_rows_by_engine.get(engine_id, [])
        engine_reason_counter: Counter[str] = Counter()
        for refusal_row in engine_refusal_rows:
            for code in set(_row_reason_codes(refusal_row)):
                engine_reason_counter[code] += 1
        matrix_row = engine_matrix_index.get(engine_id, {})
        candidate_count = len(
            {
                (
                    str(row.get("candidate_id") or ""),
                    int(row.get("timestamp_ms") or 0),
                    str(row.get("pair") or ""),
                    str(row.get("timeframe") or ""),
                )
                for row in engine_candidate_rows
            }
        )
        top_reason_rows = _top_reason_rows(
            engine_reason_counter,
            common_reason_codes=resolved_common_codes,
            limit=10,
        )
        top_reason_codes = tuple(str(item["reason_code"]) for item in top_reason_rows)
        if engine_id == "engine_d":
            engine_specific = _build_engine_d_diagnosis(
                candidate_rows=engine_candidate_rows,
                reason_counter=engine_reason_counter,
                common_reason_codes=resolved_common_codes,
                workflow_root=workflow_root,
            )
        elif engine_id == "engine_c":
            engine_specific = _build_engine_c_diagnosis(
                candidate_rows=engine_candidate_rows,
                reason_counter=engine_reason_counter,
                common_reason_codes=resolved_common_codes,
                gold_manifest_payload=gold_manifest_payload,
            )
        else:
            engine_specific = _build_engine_ab_direction_cost_diagnosis(
                engine_id=engine_id,
                candidate_rows=engine_candidate_rows,
                refusal_rows=engine_refusal_rows,
                reason_counter=engine_reason_counter,
                common_reason_codes=resolved_common_codes,
            )
        engine_rows.append(
            {
                "engine_id": engine_id,
                "candidate_count": candidate_count,
                "replay_record_count": int(
                    matrix_row.get("record_count") or len(engine_refusal_rows)
                ),
                "selected_count": int(matrix_row.get("selected_count") or 0),
                "hard_blocked_count": int(
                    matrix_row.get("hard_blocked_count") or len(engine_refusal_rows)
                ),
                "first_blocking_layer": str(
                    engine_specific.get("first_blocking_layer")
                    or _first_blocking_layer(top_reason_codes)
                ),
                "top_reason_codes": top_reason_rows,
                "healthy_blockers": tuple(engine_specific.get("healthy_blockers") or ()),
                "suspected_wiring_gaps": tuple(
                    engine_specific.get("suspected_wiring_gaps") or ()
                ),
                "recommended_next_action": str(
                    engine_specific.get("recommended_next_action")
                    or "KEEP_BLOCKED_UNTIL_EDGE_GOVERNED"
                ),
                "diagnostics": {
                    key: value
                    for key, value in engine_specific.items()
                    if key
                    not in {
                        "first_blocking_layer",
                        "healthy_blockers",
                        "suspected_wiring_gaps",
                        "recommended_next_action",
                        "engine_id",
                    }
                },
            }
        )
    selected_count_total = sum(int(row.get("selected_count") or 0) for row in engine_rows)
    hard_blocked_count_total = sum(
        int(row.get("hard_blocked_count") or 0) for row in engine_rows
    )
    engine_index = {
        str(row.get("engine_id") or ""): row
        for row in engine_rows
        if isinstance(row, dict) and str(row.get("engine_id") or "")
    }
    engine_d_action = str(
        (engine_index.get("engine_d") or {}).get("recommended_next_action")
        or "BUILD_CLOSED_EPISODE_JOURNAL_FOR_ENGINE_D"
    )
    engine_c_action = str(
        (engine_index.get("engine_c") or {}).get("recommended_next_action")
        or "FIX_ENGINE_C_MICROSTRUCTURE_CONSUMPTION"
    )
    next_action_ranking = [
        _next_action_row("A", "RUN_BACKTEST_CIRCUIT_COVERAGE_SCAN"),
        _next_action_row("B", engine_d_action),
        _next_action_row("C", engine_c_action),
        _next_action_row("D", "BUILD_EXPECTED_EDGE_GOVERNED_DATASET"),
        _next_action_row("E", "UPGRADE_EXECUTION_REALISM_FOR_SPREAD_SLIPPAGE_ADVERSE_SELECTION"),
    ]
    return {
        "schema_version": "v1",
        "run_id": summary.run_id,
        "workflow_run_id": summary.workflow_run_id,
        "phase_run_id": summary.phase_run_id,
        "source_status": "ok" if candidate_rows and refusal_rows else "missing",
        "final_status": summary.final_status,
        "candidate_funnel": {
            "discovery_candidates": summary.candidate_count,
            "engine_native_candidates": summary.engine_native_candidate_count,
            "replay_records": summary.replay_record_count,
            "selected_count": selected_count_total,
            "executed_count": run_manifest.executed_trade_count,
            "hard_blocked_count": hard_blocked_count_total,
        },
        "common_blockers": common_blockers,
        "first_gate_analysis": {
            "gate_status": (
                "FIRST_GATE_BLOCKS_BEFORE_SELECTION"
                if run_manifest.executed_trade_count == 0 and hard_blocked_count_total >= summary.replay_record_count
                else "FIRST_GATE_NOT_PROVEN"
            ),
            "first_gate_reason_codes": tuple(item["reason_code"] for item in common_blockers),
            "explanation": "Selection collapses before execution because common governance and proxy cost gates block every replay record.",
        },
        "engines": engine_rows,
        "next_action_ranking": next_action_ranking,
        "evidence": {
            "governed_evidence_status": summary.governed_evidence_status,
            "run_manifest_evidence_class": summary.run_manifest_evidence_class,
            "refusal_ledger_evidence_class": summary.refusal_ledger_evidence_class,
            "sample_size_survival_evidence_class": summary.sample_size_survival_evidence_class,
            "audited_evidence_count": summary.audited_evidence_count,
            "scratch_only_evidence_count": summary.scratch_only_evidence_count,
            "promotion_grade_evidence_count": summary.promotion_grade_evidence_count,
        },
        "profitability_claim_allowed": False,
        "profitability_claim_blocker": "SELECTED_COUNT_ZERO_NO_PROFITABILITY_CLAIM",
        "request_window": {
            "start": run_manifest.start,
            "end": run_manifest.end,
            "pair": run_manifest.pairs[0] if run_manifest.pairs else "",
        },
    }


def _format_engine_no_trade_diagnosis_markdown(payload: dict[str, object]) -> str:
    candidate_funnel = dict(payload.get("candidate_funnel") or {})
    common_blockers = tuple(payload.get("common_blockers") or ())
    engine_rows = tuple(payload.get("engines") or ())
    next_actions = tuple(payload.get("next_action_ranking") or ())
    first_gate = dict(payload.get("first_gate_analysis") or {})
    evidence = dict(payload.get("evidence") or {})
    lines = [
        "# Engine No-Trade Diagnosis",
        "",
        f"- run_id: {payload.get('run_id')}",
        f"- workflow_run_id: {payload.get('workflow_run_id')}",
        f"- phase_run_id: {payload.get('phase_run_id')}",
        f"- final_status: {payload.get('final_status')}",
        f"- source_status: {payload.get('source_status')}",
        f"- profitability_claim_allowed: {payload.get('profitability_claim_allowed')}",
        f"- profitability_claim_blocker: {payload.get('profitability_claim_blocker')}",
        "",
        "## Candidate Funnel",
        f"- discovery_candidates: {candidate_funnel.get('discovery_candidates', 0)}",
        f"- engine_native_candidates: {candidate_funnel.get('engine_native_candidates', 0)}",
        f"- replay_records: {candidate_funnel.get('replay_records', 0)}",
        f"- selected_count: {candidate_funnel.get('selected_count', 0)}",
        f"- executed_count: {candidate_funnel.get('executed_count', 0)}",
        f"- hard_blocked_count: {candidate_funnel.get('hard_blocked_count', 0)}",
        "",
        "## Common Blockers",
    ]
    lines.extend(
        f"- {row.get('reason_code')}: count={row.get('count')}, pct={row.get('pct_of_replay_records')}"
        for row in common_blockers
    )
    lines.extend(
        [
            "",
            "## First-Gate Analysis",
            f"- gate_status: {first_gate.get('gate_status')}",
            "- first_gate_reason_codes: "
            + ", ".join(str(code) for code in (first_gate.get("first_gate_reason_codes") or ())),
            f"- explanation: {first_gate.get('explanation')}",
            "",
            "## Unified Per-Engine Verdict",
        ]
    )
    for row in engine_rows:
        diagnostics = dict(row.get("diagnostics") or {})
        lines.extend(
            [
                f"- {row.get('engine_id')}:",
                f"  - candidate_count: {row.get('candidate_count')}",
                f"  - replay_record_count: {row.get('replay_record_count')}",
                f"  - selected_count: {row.get('selected_count')}",
                f"  - hard_blocked_count: {row.get('hard_blocked_count')}",
                f"  - first_blocking_layer: {row.get('first_blocking_layer')}",
                "  - top_reason_codes: "
                + ", ".join(
                    f"{item.get('reason_code')}({item.get('count')})"
                    for item in (row.get("top_reason_codes") or ())
                ),
                "  - healthy_blockers: "
                + ", ".join(str(item) for item in (row.get("healthy_blockers") or ())),
                "  - suspected_wiring_gaps: "
                + ", ".join(str(item) for item in (row.get("suspected_wiring_gaps") or ())),
                f"  - recommended_next_action: {row.get('recommended_next_action')}",
            ]
        )
        for key, value in diagnostics.items():
            lines.append(f"  - {key}: {value}")
    lines.extend(["", "## Next Action Ranking"])
    lines.extend(
        f"- {item.get('rank')}. {item.get('action')}: {item.get('rationale')}"
        for item in next_actions
    )
    lines.extend(
        [
            "",
            "## Evidence",
            f"- governed_evidence_status: {evidence.get('governed_evidence_status')}",
            f"- run_manifest_evidence_class: {evidence.get('run_manifest_evidence_class')}",
            f"- refusal_ledger_evidence_class: {evidence.get('refusal_ledger_evidence_class')}",
            f"- sample_size_survival_evidence_class: {evidence.get('sample_size_survival_evidence_class')}",
            f"- audited_evidence_count: {evidence.get('audited_evidence_count')}",
            f"- scratch_only_evidence_count: {evidence.get('scratch_only_evidence_count')}",
            f"- promotion_grade_evidence_count: {evidence.get('promotion_grade_evidence_count')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _persist_progress_run_manifest(
    run_dir: Path,
    manifest: StrategyLadderRunManifest,
    *,
    progress_callback: StrategyLadderProgressCallback | None = None,
) -> StrategyLadderRunManifest:
    manifest = manifest.model_copy(
        update={
            "updated_at": datetime.now(tz=UTC),
            "artifact_hash": deterministic_payload_hash(
                manifest.model_dump(mode="json")
            ),
        }
    )
    atomic_write_json(
        run_dir / "run_manifest.progress.json",
        manifest.model_dump(mode="json"),
    )
    if progress_callback is not None:
        progress_callback(manifest)
    return manifest


def _clear_progress_run_manifest(run_dir: Path) -> None:
    progress_path = run_dir / "run_manifest.progress.json"
    try:
        progress_path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _persist_canonical_run_manifest(
    run_dir: Path,
    manifest: StrategyLadderRunManifest,
    *,
    progress_callback: StrategyLadderProgressCallback | None = None,
) -> StrategyLadderRunManifest:
    manifest = manifest.model_copy(
        update={
            "updated_at": datetime.now(tz=UTC),
            "artifact_hash": deterministic_payload_hash(
                manifest.model_dump(mode="json")
            ),
        }
    )
    atomic_write_json(run_dir / "run_manifest.json", manifest.model_dump(mode="json"))
    _clear_progress_run_manifest(run_dir)
    if progress_callback is not None:
        progress_callback(manifest)
    return manifest


def _merge_blocker_codes(
    *parts: tuple[str, ...] | list[str] | tuple[str, str] | tuple[str, ...],
) -> tuple[str, ...]:
    merged: list[str] = []
    for part in parts:
        for item in part:
            code = str(item).strip()
            if code and code not in merged:
                merged.append(code)
    return tuple(merged)


def _write_raw_window_failure_report(
    run_dir: Path,
    *,
    request: StrategyLadderRequest,
    candidate_count: int,
    manifest_count: int,
    raw_window_status: str,
    error: Exception,
    blocker_codes: tuple[str, ...],
    linkage_counts: dict[str, int] | None = None,
) -> Path:
    payload = dict(linkage_counts or {})
    path = run_dir / "raw_window_failure_report.json"
    atomic_write_json(
        path,
        {
            "run_id": request.run_id,
            "stage": "raw_window_extraction",
            "raw_window_status": raw_window_status,
            "candidate_count": candidate_count,
            "raw_window_count": manifest_count,
            "raw_windows_total": int(payload.get("raw_windows_total", candidate_count)),
            "trade_windows_found": int(payload.get("trade_windows_found", 0)),
            "trade_windows_missing": int(payload.get("trade_windows_missing", candidate_count)),
            "book_windows_found": int(payload.get("book_windows_found", 0)),
            "book_windows_missing": int(payload.get("book_windows_missing", candidate_count)),
            "ohlcv_windows_found": int(payload.get("ohlcv_windows_found", 0)),
            "ohlcv_windows_missing": int(payload.get("ohlcv_windows_missing", candidate_count)),
            "depth20_found": int(payload.get("depth20_found", 0)),
            "depth20_missing": int(payload.get("depth20_missing", candidate_count)),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "blocker_codes": list(blocker_codes),
            "stage_statuses": {
                "raw_window_status": raw_window_status,
                "raw_window_extraction_status": raw_window_status,
            },
            "raw_windows_root": str((run_dir / "raw_windows").resolve()),
            "created_at": datetime.now(tz=UTC).isoformat(),
        },
        indent=2,
    )
    return path


def _summarize_raw_window_linkage(
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
) -> dict[str, int]:
    manifest_by_candidate = {
        manifest.candidate_id: manifest for manifest in raw_window_manifests
    }
    summary = {
        "raw_windows_total": len(candidate_events),
        "trade_windows_found": 0,
        "trade_windows_missing": 0,
        "book_windows_found": 0,
        "book_windows_missing": 0,
        "ohlcv_windows_found": 0,
        "ohlcv_windows_missing": 0,
        "depth20_found": 0,
        "depth20_missing": 0,
    }
    for candidate in candidate_events:
        manifest = manifest_by_candidate.get(candidate.candidate_id)
        trade_present = bool(
            manifest is not None
            and manifest.raw_trade_path
            and Path(manifest.raw_trade_path).is_file()
        )
        book_present = bool(
            manifest is not None
            and (
                (manifest.raw_book_path and Path(manifest.raw_book_path).is_file())
                or (
                    manifest.raw_book_delta_path
                    and Path(manifest.raw_book_delta_path).is_file()
                )
            )
        )
        ohlcv_present = bool(
            manifest is not None
            and manifest.raw_ohlcv_path
            and Path(manifest.raw_ohlcv_path).is_file()
        )
        depth20_present = bool(
            manifest is not None
            and manifest.book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
        )
        summary["trade_windows_found" if trade_present else "trade_windows_missing"] += 1
        summary["book_windows_found" if book_present else "book_windows_missing"] += 1
        summary["ohlcv_windows_found" if ohlcv_present else "ohlcv_windows_missing"] += 1
        summary["depth20_found" if depth20_present else "depth20_missing"] += 1
    return summary


def _normalize_raw_window_materialization_mode(request: StrategyLadderRequest) -> str:
    raw = str(request.raw_window_materialization_mode or "MATERIALIZE").strip().upper()
    normalized = raw.replace("-", "_")
    if normalized in {"REFS_ONLY", "REFERENCE_ONLY"}:
        return "REFS_ONLY"
    return "MATERIALIZE"


def _should_materialize_raw_windows(
    *,
    request: StrategyLadderRequest,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
) -> bool:
    if not candidate_events or request.dry_run:
        return False
    if _normalize_raw_window_materialization_mode(request) == "REFS_ONLY":
        return False
    native_preselection_enabled = request.engine_native_mode and not request.dry_run
    return bool(not request.fast_only or native_preselection_enabled)


def _raw_window_refs_only_linkage_counts(
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
) -> dict[str, int]:
    return {
        "raw_windows_total": len(candidate_events),
        "trade_windows_found": 0,
        "trade_windows_missing": 0,
        "book_windows_found": 0,
        "book_windows_missing": 0,
        "ohlcv_windows_found": 0,
        "ohlcv_windows_missing": 0,
        "depth20_found": 0,
        "depth20_missing": 0,
    }


def _build_progress_manifest(
    *,
    request: StrategyLadderRequest,
    run_dir: Path,
    silver_index_path: Path,
    silver_index_ready: bool,
    data_factory_status: str,
    raw_source_status: str,
    pair_universe_status: str,
    silver_index_status: str,
    gold_feature_store_status: str,
    orderbook_reconstruction_status: str,
    feature_store_status: str,
    candidate_discovery_status: str,
    candidate_export_status: str,
    raw_window_status: str,
    detailed_replay_status: str,
    capital_profile_generation_status: str,
    promotion_artifact_status: str,
    sample_size_status: str,
    feature_row_count: int,
    candidate_count: int,
    raw_window_count: int,
    detailed_replay_count: int,
    capital_profile_count: int,
    engine_promotion_count: int,
    pair_promotion_count: int,
    strategy_promotion_count: int,
    sample_size_survival_count: int,
    blocker_codes: tuple[str, ...],
    created_at: datetime,
    economic_constants_provenance: str = "UNKNOWN",
    candidate_truth_status: str | None = None,
    expected_edge_truth_status: str | None = None,
    expected_edge_proxy_count: int = 0,
    expected_edge_governed_count: int = 0,
    expected_edge_model_status: str = "EXPECTED_EDGE_MODEL_NOT_REQUESTED",
    expected_edge_model_artifact_hash: str | None = None,
    expected_edge_model_feature_hash: str | None = None,
    expected_edge_training_artifact_ref: str = "",
    expected_edge_label_source: str = "EXPECTED_EDGE_LABEL_SOURCE_NOT_PROVEN",
    expected_edge_label_fidelity: str = "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY",
    expected_edge_anti_leakage_status: str = "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN",
    expected_edge_walkforward_status: str = "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED",
    expected_edge_horizon: int | None = None,
    expected_edge_purge_window: int | None = None,
    expected_edge_embargo_window: int | None = None,
    expected_edge_blocker_codes: tuple[str, ...] = (),
    candidate_engine_native_count: int = 0,
    candidate_proxy_count: int | None = None,
    engine_native_status: str | None = None,
    engine_native_records_built: int = 0,
) -> StrategyLadderRunManifest:
    resolved_raw_source_manifest_path = _resolve_run_raw_source_manifest_path(
        request=request,
        silver_index_path=silver_index_path,
    )
    if engine_native_status is None:
        engine_native_status = (
            "ENGINE_NATIVE_PENDING"
            if request.engine_native_mode and candidate_count > 0 and not request.dry_run
            else "ENGINE_NATIVE_NOT_REQUESTED"
        )
    if candidate_proxy_count is None:
        candidate_proxy_count = (
            candidate_count
            if candidate_count > 0
            and candidate_engine_native_count == 0
            and candidate_discovery_status
            in {
                "CANDIDATE_DISCOVERY_READY",
                "CANDIDATE_DISCOVERY_RESUMED",
                "CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
                "CANDIDATE_DISCOVERY_EXHAUSTED",
                "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED",
            }
            else 0
        )
    if candidate_truth_status is None:
        if candidate_count == 0:
            candidate_truth_status = "CANDIDATE_TRUTH_NOT_PROVEN"
        elif engine_native_status == "ENGINE_NATIVE_MATERIALIZING":
            candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_IN_PROGRESS"
        elif candidate_proxy_count > 0:
            candidate_truth_status = "CANDIDATE_TRUTH_PROXY_PRESENT"
        elif candidate_engine_native_count >= candidate_count:
            candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_READY"
        elif candidate_engine_native_count > 0:
            candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_PARTIAL"
        else:
            candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_NOT_PROVEN"
    if expected_edge_truth_status is None:
        if candidate_count == 0:
            expected_edge_truth_status = "EXPECTED_EDGE_NOT_PROVEN"
        elif expected_edge_proxy_count > 0 and expected_edge_governed_count > 0:
            expected_edge_truth_status = "EXPECTED_EDGE_MIXED_PROXY_BLOCKED"
        elif expected_edge_proxy_count > 0:
            expected_edge_truth_status = "EXPECTED_EDGE_PROXY_BLOCKED"
        elif expected_edge_governed_count > 0:
            expected_edge_truth_status = "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        else:
            expected_edge_truth_status = "EXPECTED_EDGE_NOT_PROVEN"
    effective_sample_cap = _effective_candidate_sample_cap(request)
    engine_count = max(len(request.engines) or 4, 4)
    pair_count_for_cap = _candidate_pair_count_for_cap(request=request)
    candidate_sample_cap = _candidate_sample_cap_total(
        effective_sample_cap=effective_sample_cap,
        engine_count=engine_count,
        pair_count=pair_count_for_cap,
        candidate_discovery_mode=request.candidate_discovery_mode,
    )
    temporal_stratified_mode = _is_temporal_candidate_budget_mode(
        request.candidate_discovery_mode
    )
    temporal_bucket_granularity = ""
    temporal_bucket_count_available = 0
    temporal_bucket_count_selected = 0
    temporal_bucket_coverage_ratio = None
    if candidate_count > 0 and effective_sample_cap > 0 and candidate_count >= candidate_sample_cap:
        candidate_discovery_cap_status = "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
        candidate_discovery_limit_reason = (
            "TEMPORAL_STRATIFIED_SAMPLE_BUDGET_ACTIVE"
            if temporal_stratified_mode
            else "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
        )
        candidate_discovery_limited = True
    elif candidate_count > 0 and request.full_scan_enabled:
        candidate_discovery_cap_status = "CANDIDATE_DISCOVERY_EXHAUSTED"
        candidate_discovery_limit_reason = "DISCOVERY_EXHAUSTED_BEFORE_CAP"
        candidate_discovery_limited = False
    elif request.full_scan_enabled:
        candidate_discovery_cap_status = "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED"
        candidate_discovery_limit_reason = ""
        candidate_discovery_limited = False
    else:
        candidate_discovery_cap_status = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
        candidate_discovery_limit_reason = "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
        candidate_discovery_limited = True
    final_status = _stage_final_status(
        request=request,
        feature_store_status=feature_store_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status=detailed_replay_status,
        capital_profile_count=capital_profile_count,
        promotion_artifact_count=(
            engine_promotion_count + pair_promotion_count + strategy_promotion_count
        ),
    )
    manifest = StrategyLadderRunManifest(
        run_id=request.run_id,
        input_root=str(request.input_root.resolve()),
        feature_store_root=str(request.feature_store_root.resolve()),
        raw_root=str(request.raw_root.resolve()),
        raw_roots=tuple(str(path.resolve()) for path in request.raw_roots),
        raw_source_manifest_path=resolved_raw_source_manifest_path,
        silver_index_path=str(silver_index_path.resolve()) if silver_index_ready else "",
        output_root=str(run_dir.resolve()),
        workflow_run_id=request.workflow_run_id,
        phase_run_id=request.phase_run_id,
        parent_workflow_ref=request.parent_workflow_ref,
        pairs=request.pairs,
        engines=request.engines,
        capital_buckets=request.capital_buckets,
        timeframes=request.timeframes,
        feature_names=request.feature_names,
        start=request.start,
        end=request.end,
        fast_only=request.fast_only,
        detailed_only=request.detailed_only,
        resume=request.resume,
        dry_run=request.dry_run,
        ml_mode_status=request.ml_mode,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_extraction_status=raw_window_status,
        raw_window_materialization_mode=_normalize_raw_window_materialization_mode(request),
        detailed_replay_status=detailed_replay_status,
        capital_profile_generation_status=capital_profile_generation_status,
        promotion_artifact_status=promotion_artifact_status,
        sample_size_survival_status=sample_size_status,
        final_status=final_status,
        blocker_codes=blocker_codes,
        feature_row_count=feature_row_count,
        candidate_sample_cap=candidate_sample_cap,
        effective_engine_native_sample_size=effective_sample_cap,
        engine_count=engine_count,
        candidate_cap_formula=_candidate_cap_formula(
            effective_sample_cap=effective_sample_cap,
            engine_count=engine_count,
            pair_count=pair_count_for_cap,
            candidate_discovery_mode=request.candidate_discovery_mode,
        ),
        small_scope_enabled=request.small_scope_enabled,
        full_scan_enabled=request.full_scan_enabled,
        no_full_scan_enabled=request.no_full_scan_enabled,
        candidate_discovery_limited=candidate_discovery_limited,
        candidate_discovery_limit_reason=candidate_discovery_limit_reason,
        candidate_discovery_mode=request.candidate_discovery_mode,
        candidate_discovery_cap_status=candidate_discovery_cap_status,
        temporal_bucket_granularity=temporal_bucket_granularity,
        temporal_bucket_count_available=temporal_bucket_count_available,
        temporal_bucket_count_selected=temporal_bucket_count_selected,
        temporal_bucket_coverage_ratio=temporal_bucket_coverage_ratio,
        candidate_count=candidate_count,
        raw_window_count=raw_window_count,
        detailed_replay_count=detailed_replay_count,
        capital_profile_count=capital_profile_count,
        engine_promotion_count=engine_promotion_count,
        pair_promotion_count=pair_promotion_count,
        strategy_promotion_count=strategy_promotion_count,
        sample_size_survival_count=sample_size_survival_count,
        economic_constants_provenance=economic_constants_provenance,
        candidate_truth_status=candidate_truth_status,
        expected_edge_truth_status=expected_edge_truth_status,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        expected_edge_model_status=expected_edge_model_status,
        expected_edge_model_artifact_hash=expected_edge_model_artifact_hash,
        expected_edge_model_feature_hash=expected_edge_model_feature_hash,
        expected_edge_training_artifact_ref=expected_edge_training_artifact_ref,
        expected_edge_label_source=expected_edge_label_source,
        expected_edge_label_fidelity=expected_edge_label_fidelity,
        expected_edge_anti_leakage_status=expected_edge_anti_leakage_status,
        expected_edge_walkforward_status=expected_edge_walkforward_status,
        expected_edge_horizon=expected_edge_horizon,
        expected_edge_purge_window=expected_edge_purge_window,
        expected_edge_embargo_window=expected_edge_embargo_window,
        expected_edge_blocker_codes=expected_edge_blocker_codes,
        candidate_engine_native_count=candidate_engine_native_count,
        candidate_proxy_count=candidate_proxy_count,
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
        created_at=created_at,
        updated_at=datetime.now(tz=UTC),
    )
    return manifest.model_copy(
        update={"artifact_hash": deterministic_payload_hash(manifest.model_dump(mode="json"))}
    )


def run_backtest_strategy_ladder(
    request: StrategyLadderRequest,
    *,
    progress_callback: StrategyLadderProgressCallback | None = None,
) -> StrategyLadderRunResult:
    """Execute the canonical Strategy Ladder pipeline end to end."""

    run_dir = request.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    fast_candidates_dir = run_dir / "fast_candidates"
    raw_windows_dir = run_dir / "raw_windows"
    detailed_replay_dir = run_dir / "detailed_replay"
    capital_profiles_dir = run_dir / "capital_profiles"
    reports_dir = run_dir / "reports"
    performance_profiler = StrategyLadderReplayPerformanceProfiler(run_id=request.run_id)

    created_at = datetime.now(tz=UTC)
    start_ms = parse_time_boundary_to_ms(request.start)
    end_ms = parse_time_boundary_to_ms(request.end, end_of_day=True)
    with performance_profiler.phase("feature_loading", status="OK"):
        data_factory_payloads = _resolve_data_factory_payloads(request)
    data_factory_root = Path(str(data_factory_payloads["base_root"]))
    data_factory_manifest_payload = data_factory_payloads["manifest"]
    raw_source_report_payload = data_factory_payloads["raw_source_report"]
    pair_report_payload = data_factory_payloads["pair_report"]
    quality_report_payload = data_factory_payloads["quality_report"]
    gold_manifest_payload = data_factory_payloads["gold_manifest"]
    silver_index_report_payload = data_factory_payloads["silver_index_report"]
    silver_index_path = Path(str(data_factory_payloads["silver_index_path"]))
    resolved_raw_source_manifest_path = _resolve_run_raw_source_manifest_path(
        request=request,
        silver_index_path=silver_index_path,
        data_factory_base_root=data_factory_root,
    )
    silver_index_ready = silver_index_path.is_file() and bool(
        silver_index_report_payload.get("entries")
    )
    # Audit 2026-05-13 W1 fix : on resoud le venue (exchange + market_type)
    # depuis le silver_index canonique ici, UNE seule fois. Le auto-detect via
    # raw_book_path echoue car les raw_windows sont extraites dans le run dir
    # (pas le silver path direct), donc on doit cabler explicitement le venue
    # au call site `compute_economic_provenance`.
    silver_exchange_resolved, silver_market_type_resolved = (
        _infer_silver_exchange_from_index(silver_index_report_payload)
    )
    data_factory_status = str(
        data_factory_manifest_payload.get("data_factory_status")
        or "DATA_FACTORY_NOT_PROVEN"
    )
    raw_source_status = str(
        raw_source_report_payload.get("raw_source_status")
        or data_factory_manifest_payload.get("raw_source_status")
        or "RAW_SOURCE_NOT_PROVEN"
    )
    pair_universe_status = str(
        pair_report_payload.get("pair_universe_status")
        or data_factory_manifest_payload.get("pair_universe_status")
        or "PAIR_UNIVERSE_NOT_PROVEN"
    )
    silver_index_status = (
        str(silver_index_report_payload.get("status") or "")
        or str(data_factory_manifest_payload.get("silver_index_status") or "")
        or ("SILVER_INDEX_READY" if silver_index_ready else "SILVER_INDEX_NOT_READY")
    )
    gold_feature_store_status = str(
        gold_manifest_payload.get("gold_feature_store_status")
        or data_factory_manifest_payload.get("gold_feature_store_status")
        or "GOLD_FEATURE_STORE_NOT_READY"
    )
    orderbook_reconstruction_status = str(
        quality_report_payload.get("orderbook_schema_status")
        or "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"
    )
    ml_mode_status = request.ml_mode
    expected_edge_model_required = request.ml_mode == "ML_MODE_OVERLAY_FROZEN"
    expected_edge_model_reference_at = _expected_edge_model_reference_at(
        created_at=created_at,
        end_ms=end_ms,
    )
    expected_edge_model_load_result = GovernedExpectedEdgeModelLoadResult(
        model=None,
        status="GOVERNED_EDGE_MODEL_NOT_REQUESTED",
    )
    if expected_edge_model_required:
        expected_edge_model_load_result = load_governed_expected_edge_model_artifact(
            request.frozen_ml_artifact_path,
            expected_artifact_hash=request.frozen_ml_artifact_hash,
            now=expected_edge_model_reference_at,
            expected_edge_artifact_mode=request.expected_edge_artifact_mode,
        )
    expected_edge_model = expected_edge_model_load_result.model
    expected_edge_model_load_status = expected_edge_model_load_result.status
    expected_edge_model_blockers = expected_edge_model_load_result.blocker_codes

    with performance_profiler.phase("feature_loading", status="OK"):
        feature_result = load_strategy_ladder_feature_store(
            request.feature_store_root,
            pairs=request.pairs,
            engines=request.engines,
            timeframes=request.timeframes,
            start_ms=start_ms,
            end_ms=end_ms,
        )

    candidate_discovery_status = "CANDIDATE_DISCOVERY_NOT_PROVEN"
    candidate_export_status = "CANDIDATE_EXPORT_NOT_PROVEN"
    candidate_events = ()
    candidate_summary = None
    candidate_source_truth_events = ()
    materialized_candidate_events = ()
    preselection_result = None
    candidate_path = fast_candidates_dir / "candidate_events.jsonl"
    candidate_events_source_path: Path | None = None
    external_candidate_path = request.candidate_events_path
    effective_sample_cap = _effective_candidate_sample_cap(request)
    engine_count = max(len(request.engines) or 4, 4)
    feature_pairs = _feature_pairs_from_rows(feature_result.rows)
    full_discovery_uncapped = _is_full_discovery_uncapped(request)
    if request.detailed_only:
        source_candidate_path = (
            external_candidate_path
            if external_candidate_path is not None and external_candidate_path.is_file()
            else candidate_path
        )
        if not source_candidate_path.is_file():
            raise ValueError(
                "Strategy Ladder detailed-only mode requires existing fast_candidates/candidate_events.jsonl"
            )
        candidate_events_source_path = source_candidate_path.resolve()
        with performance_profiler.phase("candidate_loading", status="OK"):
            candidate_events = load_strategy_ladder_candidate_events(source_candidate_path)
        candidate_source_truth_events = candidate_events
        candidate_summary = load_strategy_ladder_candidate_summary(
            source_candidate_path.with_name("candidate_summary.json")
        )
        candidate_discovery_status = (
            candidate_summary.candidate_discovery_status
            if candidate_summary is not None
            else "CANDIDATE_DISCOVERY_RESUMED"
        )
        candidate_export_status = (
            candidate_summary.candidate_export_status
            if candidate_summary is not None
            else "CANDIDATE_EXPORT_READY"
        )
    elif request.resume and candidate_path.is_file():
        with performance_profiler.phase("candidate_loading", status="OK"):
            candidate_events = load_strategy_ladder_candidate_events(candidate_path)
        candidate_source_truth_events = candidate_events
        candidate_summary = load_strategy_ladder_candidate_summary(
            candidate_path.with_name("candidate_summary.json")
        )
        candidate_discovery_status = (
            candidate_summary.candidate_discovery_status
            if candidate_summary is not None
            else "CANDIDATE_DISCOVERY_RESUMED"
        )
        candidate_export_status = (
            candidate_summary.candidate_export_status
            if candidate_summary is not None
            else "CANDIDATE_EXPORT_READY"
        )
    elif feature_result.feature_store_status != "FEATURE_STORE_MISSING":
        with performance_profiler.phase(
            "candidate_discovery",
            status="OK",
            rows_processed=len(feature_result.rows),
        ):
            candidate_discovery_status, discovered_candidate_events = (
                discover_strategy_ladder_candidates(
                    run_id=request.run_id,
                    rows=feature_result.rows,
                )
            )
            budget_result = apply_strategy_ladder_candidate_budget(
                discovered_candidate_events,
                sample_cap_per_engine=effective_sample_cap,
                candidate_discovery_mode=request.candidate_discovery_mode,
            )
            candidate_events = budget_result.candidates
            discovery_capped = budget_result.limited
            temporal_bucket_granularity = budget_result.temporal_bucket_granularity
            temporal_bucket_count_available = (
                budget_result.temporal_bucket_count_available
            )
            temporal_bucket_count_selected = (
                budget_result.temporal_bucket_count_selected
            )
            temporal_bucket_coverage_ratio = (
                budget_result.temporal_bucket_coverage_ratio
            )
        if discovery_capped and candidate_events:
            candidate_discovery_status = "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
        elif candidate_events and request.full_scan_enabled:
            candidate_discovery_status = "CANDIDATE_DISCOVERY_EXHAUSTED"
        if not request.dry_run:
            with performance_profiler.phase(
                "candidate_export",
                status="OK",
                candidate_count=len(candidate_events),
            ):
                candidate_summary = export_strategy_ladder_candidates(
                    fast_candidates_dir,
                    run_id=request.run_id,
                    candidates=candidate_events,
                    feature_store_status=feature_result.feature_store_status,
                    candidate_discovery_status=candidate_discovery_status,
                    requested_pairs=request.pairs,
                    pairs_with_feature_rows=feature_pairs,
                    candidate_sample_cap=_candidate_sample_cap_total(
                        effective_sample_cap=effective_sample_cap,
                        engine_count=engine_count,
                        pair_count=_candidate_pair_count_for_cap(
                            request=request,
                            candidate_events=discovered_candidate_events,
                        ),
                        candidate_discovery_mode=request.candidate_discovery_mode,
                    ),
                    effective_engine_native_sample_size=effective_sample_cap,
                    engine_count=engine_count,
                    candidate_cap_formula=_candidate_cap_formula(
                        effective_sample_cap=effective_sample_cap,
                        engine_count=engine_count,
                        pair_count=_candidate_pair_count_for_cap(
                            request=request,
                            candidate_events=discovered_candidate_events,
                        ),
                        candidate_discovery_mode=request.candidate_discovery_mode,
                    ),
                    small_scope_enabled=request.small_scope_enabled,
                    full_scan_enabled=request.full_scan_enabled,
                    no_full_scan_enabled=request.no_full_scan_enabled,
                    candidate_discovery_limited=discovery_capped
                    or (
                        not full_discovery_uncapped
                        and (
                            request.candidate_discovery_mode == "SAMPLE_CAPPED_DEBUG"
                            or request.small_scope_enabled
                        )
                    ),
                    candidate_discovery_limit_reason=(
                        budget_result.limit_reason
                        if discovery_capped
                        or (
                            not full_discovery_uncapped
                            and (
                                request.candidate_discovery_mode == "SAMPLE_CAPPED_DEBUG"
                                or request.small_scope_enabled
                            )
                        )
                        else "DISCOVERY_EXHAUSTED_BEFORE_CAP"
                    ),
                    candidate_discovery_mode=request.candidate_discovery_mode,
                    candidate_discovery_cap_status=(
                        budget_result.cap_status
                        if discovery_capped or (
                            candidate_events and effective_sample_cap > 0
                            and len(candidate_events)
                            == _candidate_sample_cap_total(
                                effective_sample_cap=effective_sample_cap,
                                engine_count=engine_count,
                                pair_count=_candidate_pair_count_for_cap(
                                    request=request,
                                    candidate_events=discovered_candidate_events,
                                ),
                                candidate_discovery_mode=request.candidate_discovery_mode,
                            )
                        )
                        else (
                            "CANDIDATE_DISCOVERY_EXHAUSTED"
                            if candidate_events and request.full_scan_enabled
                            else "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED"
                        )
                    ),
                    temporal_bucket_granularity=temporal_bucket_granularity,
                    temporal_bucket_count_available=temporal_bucket_count_available,
                    temporal_bucket_count_selected=temporal_bucket_count_selected,
                    temporal_bucket_coverage_ratio=temporal_bucket_coverage_ratio,
                )
            candidate_export_status = candidate_summary.candidate_export_status
            candidate_source_truth_events = candidate_events
        else:
            candidate_export_status = (
                "CANDIDATE_EXPORT_READY" if candidate_events else "CANDIDATE_EXPORT_EMPTY"
            )
    progress_manifest = _build_progress_manifest(
        request=request,
        run_dir=run_dir,
        silver_index_path=silver_index_path,
        silver_index_ready=silver_index_ready,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_status="RAW_WINDOW_NOT_PROVEN",
        detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
        capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
        promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
        sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
        feature_row_count=feature_result.row_count,
        candidate_count=len(candidate_events),
        raw_window_count=0,
        detailed_replay_count=0,
        capital_profile_count=0,
        engine_promotion_count=0,
        pair_promotion_count=0,
        strategy_promotion_count=0,
        sample_size_survival_count=0,
        blocker_codes=_merge_blocker_codes(
            feature_result.blocker_codes,
            expected_edge_model_blockers,
        ),
        created_at=created_at,
        expected_edge_model_status=expected_edge_model_load_status,
        expected_edge_model_artifact_hash=expected_edge_model_load_result.artifact_hash,
        expected_edge_model_feature_hash=expected_edge_model_load_result.feature_hash,
    )
    _persist_progress_run_manifest(
        run_dir,
        progress_manifest,
        progress_callback=progress_callback,
    )

    raw_window_status = "RAW_WINDOW_NOT_PROVEN"
    raw_window_manifests = ()
    raw_window_linkage_counts = _summarize_raw_window_linkage(
        candidate_events=(),
        raw_window_manifests=(),
    )
    raw_window_failure_blockers: tuple[str, ...] = ()
    engine_native_blockers: tuple[str, ...] = ()
    engine_native_status = (
        "ENGINE_NATIVE_PENDING" if request.engine_native_mode else "ENGINE_NATIVE_NOT_REQUESTED"
    )
    engine_native_records_built = 0
    expected_edge_proxy_count = 0
    expected_edge_governed_count = 0
    candidate_engine_native_progress_count = 0
    candidate_proxy_progress_count: int | None = None
    raw_window_extraction_failed = False

    def _raw_window_stage_blockers(*extra: str) -> tuple[str, ...]:
        return _merge_blocker_codes(
            feature_result.blocker_codes,
            expected_edge_model_blockers,
            raw_window_failure_blockers,
            engine_native_blockers,
            tuple(extra),
        )

    def _raw_window_progress_callback(
        progress_status: str,
        raw_window_count_progress: int,
    ) -> None:
        progress_manifest = _build_progress_manifest(
            request=request,
            run_dir=run_dir,
            silver_index_path=silver_index_path,
            silver_index_ready=silver_index_ready,
            data_factory_status=data_factory_status,
            raw_source_status=raw_source_status,
            pair_universe_status=pair_universe_status,
            silver_index_status=silver_index_status,
            gold_feature_store_status=gold_feature_store_status,
            orderbook_reconstruction_status=orderbook_reconstruction_status,
            feature_store_status=feature_result.feature_store_status,
            candidate_discovery_status=candidate_discovery_status,
            candidate_export_status=candidate_export_status,
            raw_window_status=progress_status,
            detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
            capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
            promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
            sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
            feature_row_count=feature_result.row_count,
            candidate_count=len(candidate_events),
            raw_window_count=raw_window_count_progress,
            detailed_replay_count=0,
            capital_profile_count=0,
            engine_promotion_count=0,
            pair_promotion_count=0,
            strategy_promotion_count=0,
            sample_size_survival_count=0,
            blocker_codes=_raw_window_stage_blockers(
                *(
                    ("RAW_WINDOW_NOT_PROVEN",)
                    if progress_status == "RAW_WINDOW_NOT_PROVEN"
                    else ()
                )
            ),
            created_at=created_at,
            expected_edge_model_status=expected_edge_model_load_status,
            expected_edge_model_artifact_hash=expected_edge_model_load_result.artifact_hash,
            expected_edge_model_feature_hash=expected_edge_model_load_result.feature_hash,
        )
        _persist_progress_run_manifest(
            run_dir,
            progress_manifest,
            progress_callback=progress_callback,
        )

    def _engine_native_progress_callback(
        processed_count: int,
        total_count: int,
        records_built_progress: int,
        runner_invocations: int,
        edge_proxy_count: int,
        edge_governed_count: int,
    ) -> None:
        progress_manifest = _build_progress_manifest(
            request=request,
            run_dir=run_dir,
            silver_index_path=silver_index_path,
            silver_index_ready=silver_index_ready,
            data_factory_status=data_factory_status,
            raw_source_status=raw_source_status,
            pair_universe_status=pair_universe_status,
            silver_index_status=silver_index_status,
            gold_feature_store_status=gold_feature_store_status,
            orderbook_reconstruction_status=orderbook_reconstruction_status,
            feature_store_status=feature_result.feature_store_status,
            candidate_discovery_status="CANDIDATE_DISCOVERY_ENGINE_NATIVE_IN_PROGRESS",
            candidate_export_status=candidate_export_status,
            raw_window_status=raw_window_status,
            detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
            capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
            promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
            sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
            feature_row_count=feature_result.row_count,
            candidate_count=total_count,
            raw_window_count=len(raw_window_manifests),
            detailed_replay_count=0,
            capital_profile_count=0,
            engine_promotion_count=0,
            pair_promotion_count=0,
            strategy_promotion_count=0,
            sample_size_survival_count=0,
            blocker_codes=_raw_window_stage_blockers(),
            created_at=created_at,
            expected_edge_model_status=expected_edge_model_load_status,
            expected_edge_model_artifact_hash=expected_edge_model_load_result.artifact_hash,
            expected_edge_model_feature_hash=expected_edge_model_load_result.feature_hash,
            candidate_truth_status="CANDIDATE_ENGINE_NATIVE_IN_PROGRESS",
            expected_edge_truth_status=(
                "EXPECTED_EDGE_MIXED_PROXY_BLOCKED"
                if edge_proxy_count and edge_governed_count
                else (
                    "EXPECTED_EDGE_PROXY_BLOCKED"
                    if edge_proxy_count
                    else (
                        "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
                        if edge_governed_count
                        else "EXPECTED_EDGE_NOT_PROVEN"
                    )
                )
            ),
            expected_edge_proxy_count=edge_proxy_count,
            expected_edge_governed_count=edge_governed_count,
            candidate_engine_native_count=runner_invocations,
            candidate_proxy_count=max(total_count - processed_count, 0),
            engine_native_status="ENGINE_NATIVE_MATERIALIZING",
            engine_native_records_built=records_built_progress,
        )
        _persist_progress_run_manifest(
            run_dir,
            progress_manifest,
            progress_callback=progress_callback,
        )

    raw_window_materialization_mode = _normalize_raw_window_materialization_mode(request)
    if (
        raw_window_materialization_mode == "REFS_ONLY"
        and not request.fast_only
        and not request.dry_run
    ):
        raise ValueError(
            "RAW_WINDOW_REFS_ONLY is allowed only for fast-only B1 discovery; "
            "B2/detailed replay must materialize raw windows."
        )

    if _should_materialize_raw_windows(request=request, candidate_events=candidate_events):
        try:
            with performance_profiler.phase(
                "raw_window_extraction",
                status="OK",
                candidate_count=len(candidate_events),
            ):
                raw_window_result = extract_strategy_ladder_raw_windows(
                    raw_windows_dir,
                    candidate_events=candidate_events,
                    raw_root=request.raw_root,
                    silver_index_path=silver_index_path if silver_index_ready else None,
                    progress_callback=_raw_window_progress_callback,
                )
            raw_window_status, raw_window_manifests = raw_window_result
            performance_profiler.observe_window_index_metrics(
                raw_window_result.indexed_lookup_metrics
            )
            performance_profiler.observe_window_cache_metrics(
                raw_window_result.window_cache_metrics
            )
            performance_profiler.record_phase(
                "jsonl_parsing",
                status=(
                    "OK"
                    if raw_window_result.jsonl_files_scanned > 0
                    else "NOT_RUN"
                ),
                wall_time_s=raw_window_result.jsonl_parsing_wall_time_s,
                cpu_time_s=raw_window_result.jsonl_parsing_cpu_time_s,
                rows_processed=raw_window_result.jsonl_rows_processed,
                files_scanned=raw_window_result.jsonl_files_scanned,
                candidate_count=len(candidate_events),
            )
            raw_window_linkage_counts = _summarize_raw_window_linkage(
                candidate_events=candidate_events,
                raw_window_manifests=raw_window_manifests,
            )
        except Exception as exc:  # noqa: BLE001
            raw_window_manifests = (
                load_strategy_ladder_raw_window_manifests(raw_windows_dir)
                if raw_windows_dir.exists()
                else ()
            )
            raw_window_linkage_counts = _summarize_raw_window_linkage(
                candidate_events=candidate_events,
                raw_window_manifests=raw_window_manifests,
            )
            raw_window_status = (
                "RAW_WINDOW_PARTIAL" if raw_window_manifests else "RAW_WINDOW_NOT_PROVEN"
            )
            raw_window_extraction_failed = True
            raw_window_failure_blockers = ("RAW_WINDOW_EXTRACTION_FAILED",)
            _write_raw_window_failure_report(
                run_dir,
                request=request,
                candidate_count=len(candidate_events),
                manifest_count=len(raw_window_manifests),
                raw_window_status=raw_window_status,
                error=exc,
                blocker_codes=_raw_window_stage_blockers(),
                linkage_counts=raw_window_linkage_counts,
            )
    elif raw_window_materialization_mode == "REFS_ONLY" and candidate_events:
        raw_window_status = "RAW_WINDOW_REFS_ONLY"
        raw_window_manifests = ()
        raw_window_linkage_counts = _raw_window_refs_only_linkage_counts(candidate_events)
        performance_profiler.record_phase(
            "raw_window_extraction",
            status="REFS_ONLY_NOT_RUN",
            wall_time_s=0.0,
            cpu_time_s=0.0,
            candidate_count=len(candidate_events),
            counters={"raw_window_materialization_mode": "REFS_ONLY"},
        )
    elif request.resume and raw_windows_dir.exists():
        raw_window_manifests = load_strategy_ladder_raw_window_manifests(raw_windows_dir)
        raw_window_linkage_counts = _summarize_raw_window_linkage(
            candidate_events=candidate_events,
            raw_window_manifests=raw_window_manifests,
        )
        raw_window_status = (
            "RAW_WINDOW_READY"
            if raw_window_manifests
            and all(item.window_extraction_status == "RAW_WINDOW_READY" for item in raw_window_manifests)
            else ("RAW_WINDOW_PARTIAL" if raw_window_manifests else "RAW_WINDOW_NOT_PROVEN")
        )
    else:
        raw_window_linkage_counts = _summarize_raw_window_linkage(
            candidate_events=candidate_events,
            raw_window_manifests=raw_window_manifests,
        )
    progress_manifest = _build_progress_manifest(
        request=request,
        run_dir=run_dir,
        silver_index_path=silver_index_path,
        silver_index_ready=silver_index_ready,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
        capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
        promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
        sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
        feature_row_count=feature_result.row_count,
        candidate_count=len(candidate_events),
        raw_window_count=len(raw_window_manifests),
        detailed_replay_count=0,
        capital_profile_count=0,
        engine_promotion_count=0,
        pair_promotion_count=0,
        strategy_promotion_count=0,
        sample_size_survival_count=0,
        blocker_codes=_raw_window_stage_blockers(
            *(("RAW_WINDOW_NOT_PROVEN",) if raw_window_status == "RAW_WINDOW_NOT_PROVEN" else ())
        ),
        created_at=created_at,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        candidate_engine_native_count=candidate_engine_native_progress_count,
        candidate_proxy_count=candidate_proxy_progress_count,
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
    )
    _persist_progress_run_manifest(
        run_dir,
        progress_manifest,
        progress_callback=progress_callback,
    )

    if request.engine_native_mode and not request.dry_run and candidate_events:
        engine_native_started_wall = perf_counter()
        engine_native_started_cpu = process_time()
        # Patch B2-RECON-SHARE (2026-06-04) — enable the (pair, base) shared book
        # timeline for B2 materialization only; A2 keeps the legacy progressive
        # cache. Reset + evict timelines in finally so neither leaks past B2.
        from local_replay_runtime.strategy_ladder_engine_native_adapter import (
            evict_partition_book_timelines,
            set_partition_book_timeline_enabled,
        )

        _prior_timeline_enabled = set_partition_book_timeline_enabled(True)
        try:
            native_materialization = _materialize_engine_native_candidates(
                candidate_events=candidate_events,
                raw_window_manifests=raw_window_manifests,
                expected_edge_model=expected_edge_model,
                expected_edge_model_required=expected_edge_model_required,
                expected_edge_model_load_status=expected_edge_model_load_status,
                progress_callback=_engine_native_progress_callback,
                silver_exchange=silver_exchange_resolved,
                silver_market_type=silver_market_type_resolved,
                ml_mode=request.ml_mode,
            )
        finally:
            set_partition_book_timeline_enabled(_prior_timeline_enabled)
            evict_partition_book_timelines()
        performance_profiler.record_phase(
            "engine_native_materialization",
            status=native_materialization.engine_native_status,
            wall_time_s=perf_counter() - engine_native_started_wall,
            cpu_time_s=process_time() - engine_native_started_cpu,
            candidate_count=len(candidate_events),
            replay_record_count=(
                native_materialization.engine_native_records_built
            ),
            counters={
                "workers_requested": resolve_worker_count(),
                "engine_native_runner_invocation_count": (
                    native_materialization.engine_native_runner_invocation_count
                ),
                "expected_edge_proxy_count": (
                    native_materialization.expected_edge_proxy_count
                ),
                "expected_edge_governed_count": (
                    native_materialization.expected_edge_governed_count
                ),
            },
        )
        materialized_candidate_events = native_materialization.candidate_events
        candidate_discovery_status = native_materialization.candidate_discovery_status
        engine_native_status = native_materialization.engine_native_status
        engine_native_records_built = native_materialization.engine_native_records_built
        expected_edge_proxy_count = native_materialization.expected_edge_proxy_count
        expected_edge_governed_count = native_materialization.expected_edge_governed_count
        engine_native_blockers = native_materialization.blocker_codes
        candidate_engine_native_progress_count = sum(
            1
            for event in materialized_candidate_events
            if getattr(event, "candidate_source", "") == "ENGINE_NATIVE"
        )
        candidate_proxy_progress_count = sum(
            1
            for event in materialized_candidate_events
            if getattr(event, "candidate_source", "") == "COMPAT_FEATURE_DISCOVERY"
        )
        source_truth_semantics = summarize_candidate_count_semantics(
            candidate_source_truth_events or materialized_candidate_events
        )
        materialized_candidate_semantics = summarize_candidate_count_semantics(
            materialized_candidate_events
        )
        preselection_result = build_strategy_ladder_engine_native_preselection(
            run_dir=run_dir,
            source_candidate_events=candidate_source_truth_events or candidate_events,
            materialized_candidate_events=materialized_candidate_events,
            diagnostic_full_replay=request.diagnostic_full_replay,
            preselected_only=request.preselected_only,
            b1_5_policy_mode=request.b1_5_policy_mode,
        )
        if request.diagnostic_full_replay:
            candidate_events = materialized_candidate_events
            replay_input_mode_status = "DIAGNOSTIC_FULL_REPLAY"
        else:
            preselected_candidate_path = Path(
                preselection_result.preselection_candidates_path
            )
            candidate_events = (
                load_strategy_ladder_candidate_events(preselected_candidate_path)
                if preselected_candidate_path.is_file()
                else ()
            )
            replay_input_mode_status = "PRESELECTED_ONLY"
        candidate_summary = export_strategy_ladder_candidates(
            fast_candidates_dir,
            run_id=request.run_id,
            candidates=materialized_candidate_events,
            feature_store_status=feature_result.feature_store_status,
            candidate_discovery_status=(
                candidate_summary.candidate_discovery_status
                if candidate_summary is not None
                else candidate_discovery_status
            ),
            requested_pairs=request.pairs,
            pairs_with_feature_rows=feature_pairs,
            candidate_sample_cap=(
                candidate_summary.candidate_sample_cap
                if candidate_summary is not None
                else _candidate_sample_cap_total(
                    effective_sample_cap=effective_sample_cap,
                    engine_count=engine_count,
                    pair_count=_candidate_pair_count_for_cap(
                        request=request,
                        candidate_events=materialized_candidate_events,
                    ),
                    candidate_discovery_mode=request.candidate_discovery_mode,
                )
            ),
            effective_engine_native_sample_size=(
                candidate_summary.effective_engine_native_sample_size
                if candidate_summary is not None
                and candidate_summary.effective_engine_native_sample_size > 0
                else effective_sample_cap
            ),
            engine_count=(
                candidate_summary.engine_count
                if candidate_summary is not None and candidate_summary.engine_count > 0
                else engine_count
            ),
            candidate_cap_formula=(
                candidate_summary.candidate_cap_formula
                if candidate_summary is not None and candidate_summary.candidate_cap_formula
                else _candidate_cap_formula(
                    effective_sample_cap=effective_sample_cap,
                    engine_count=engine_count,
                    pair_count=_candidate_pair_count_for_cap(
                        request=request,
                        candidate_events=materialized_candidate_events,
                    ),
                    candidate_discovery_mode=request.candidate_discovery_mode,
                )
            ),
            small_scope_enabled=(
                candidate_summary.small_scope_enabled
                if candidate_summary is not None
                else request.small_scope_enabled
            ),
            full_scan_enabled=(
                candidate_summary.full_scan_enabled
                if candidate_summary is not None
                else request.full_scan_enabled
            ),
            no_full_scan_enabled=(
                candidate_summary.no_full_scan_enabled
                if candidate_summary is not None
                else request.no_full_scan_enabled
            ),
            candidate_discovery_limited=(
                candidate_summary.candidate_discovery_limited
                if candidate_summary is not None
                else candidate_discovery_status == "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
            ),
            candidate_discovery_limit_reason=(
                candidate_summary.candidate_discovery_limit_reason
                if candidate_summary is not None
                else (
                    (
                        "TEMPORAL_STRATIFIED_SAMPLE_BUDGET_ACTIVE"
                        if request.candidate_discovery_mode.strip().upper() in {
                            "TEMPORAL_STRATIFIED",
                            "TEMPORAL_STRATIFIED_SAMPLE_BUDGET",
                        }
                        else "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
                    )
                    if candidate_discovery_status == "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
                    else "DISCOVERY_EXHAUSTED_BEFORE_CAP"
                )
            ),
            candidate_discovery_mode=(
                candidate_summary.candidate_discovery_mode
                if candidate_summary is not None and candidate_summary.candidate_discovery_mode
                else request.candidate_discovery_mode
            ),
            candidate_discovery_cap_status=(
                candidate_summary.candidate_discovery_cap_status
                if candidate_summary is not None
                and candidate_summary.candidate_discovery_cap_status
                else candidate_discovery_status
            ),
            temporal_bucket_granularity=(
                candidate_summary.temporal_bucket_granularity
                if candidate_summary is not None
                else ""
            ),
            temporal_bucket_count_available=(
                candidate_summary.temporal_bucket_count_available
                if candidate_summary is not None
                else 0
            ),
            temporal_bucket_count_selected=(
                candidate_summary.temporal_bucket_count_selected
                if candidate_summary is not None
                else 0
            ),
            temporal_bucket_coverage_ratio=(
                candidate_summary.temporal_bucket_coverage_ratio
                if candidate_summary is not None
                else None
            ),
            preselection_status=preselection_result.status,
            replay_input_mode_status=replay_input_mode_status,
            preselected_only=(request.preselected_only and not request.diagnostic_full_replay),
            diagnostic_full_replay=request.diagnostic_full_replay,
            b1_5_policy_mode=request.b1_5_policy_mode,
            discovery_pre_candidate_count=source_truth_semantics.unique_candidate_count,
            engine_native_preselected_count=preselection_result.engine_native_preselected_count,
            preselection_hard_rejected_count=preselection_result.preselection_hard_rejected_count,
            preselection_soft_flagged_count=preselection_result.preselection_soft_flagged_count,
            preselection_passed_count=preselection_result.preselection_passed_count,
            b2_replay_candidate_count=preselection_result.b2_replay_candidate_count,
            trade_eligible_candidate_count=0,
            preselection_rejection_count=preselection_result.preselection_rejection_count,
            replay_savings_estimate_count=preselection_result.replay_savings_estimate_count,
            unique_candidate_count=source_truth_semantics.unique_candidate_count,
            base_event_count=source_truth_semantics.base_event_count,
            per_engine_candidate_count=source_truth_semantics.per_engine_candidate_count,
            engine_native_candidate_count=materialized_candidate_semantics.engine_native_candidate_count,
            candidate_source_status=materialized_candidate_semantics.candidate_source_status,
        )
        candidate_export_status = candidate_summary.candidate_export_status
        progress_manifest = _build_progress_manifest(
            request=request,
            run_dir=run_dir,
            silver_index_path=silver_index_path,
            silver_index_ready=silver_index_ready,
            data_factory_status=data_factory_status,
            raw_source_status=raw_source_status,
            pair_universe_status=pair_universe_status,
            silver_index_status=silver_index_status,
            gold_feature_store_status=gold_feature_store_status,
            orderbook_reconstruction_status=orderbook_reconstruction_status,
            feature_store_status=feature_result.feature_store_status,
            candidate_discovery_status=candidate_discovery_status,
            candidate_export_status=candidate_export_status,
            raw_window_status=raw_window_status,
            detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
            capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
            promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
            sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
            feature_row_count=feature_result.row_count,
            candidate_count=len(candidate_source_truth_events or materialized_candidate_events),
            raw_window_count=len(raw_window_manifests),
            detailed_replay_count=0,
            capital_profile_count=0,
            engine_promotion_count=0,
            pair_promotion_count=0,
            strategy_promotion_count=0,
            sample_size_survival_count=0,
            blocker_codes=_raw_window_stage_blockers(
                *(("RAW_WINDOW_NOT_PROVEN",) if raw_window_status == "RAW_WINDOW_NOT_PROVEN" else ())
            ),
            created_at=created_at,
            expected_edge_proxy_count=expected_edge_proxy_count,
            expected_edge_governed_count=expected_edge_governed_count,
            candidate_engine_native_count=candidate_engine_native_progress_count,
            candidate_proxy_count=candidate_proxy_progress_count,
            engine_native_status=engine_native_status,
            engine_native_records_built=engine_native_records_built,
        )
        _persist_progress_run_manifest(
            run_dir,
            progress_manifest,
            progress_callback=progress_callback,
        )
    elif candidate_events:
        materialized_candidate_events = candidate_events
    candidate_baseline_count = len(
        candidate_source_truth_events or materialized_candidate_events or candidate_events
    )

    detailed_result = StrategyLadderDetailedReplayStageResult(
        detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
        candidate_artifacts=(),
        bucket_results_by_bucket={bucket: () for bucket in request.capital_buckets},
        bucket_dtr_records={bucket: () for bucket in request.capital_buckets},
    )
    if (
        not request.fast_only
        and not request.dry_run
        and candidate_events
        and not raw_window_extraction_failed
    ):
        build14_activation_statuses = tuple(
            str((event.compatibility_payload or {}).get("build14_shadow_activation_status") or "")
            for event in candidate_events
        )
        build14_applied_fields = tuple(
            sorted(
                {
                    str(field)
                    for event in candidate_events
                    for field in (
                        (event.compatibility_payload or {}).get("build14_shadow_applied_fields")
                        or ()
                    )
                    if str(field)
                }
            )
        )
        build14_feature_groups = tuple(
            sorted(
                {
                    str(group)
                    for group in (gold_manifest_payload.get("feature_groups_ready") or ())
                    if str(group)
                    and str(group)
                    in {
                        "flow_microstructure_features",
                        "ofi_features",
                        "vpin_features",
                        "queue_pressure",
                        "book_liquidity_features",
                        "spread_features",
                        "depth_features",
                        "fragility_false_breakout_features",
                    }
                }
            )
        )
        if any(status == "BUILD14_SHADOW_ENABLED_ACTIVE" for status in build14_activation_statuses):
            build14_context_status = "BUILD14_CONTEXT_READY"
        elif build14_activation_statuses and any(build14_activation_statuses):
            build14_context_status = "BUILD14_CONTEXT_NOT_READY"
        else:
            build14_context_status = "BUILD14_CONTEXT_NOT_DECLARED"
        if build14_applied_fields:
            build14_upstream_filter_status = "BUILD14_CONTEXT_APPLIED_TO_CANDIDATES"
        elif build14_feature_groups:
            build14_upstream_filter_status = "BUILD14_FEATURES_READY_NOT_APPLIED_OR_FILTERED"
        else:
            build14_upstream_filter_status = "BUILD14_UPSTREAM_FILTER_NOT_DECLARED"
        detailed_simulator_config = ShadowExecutionSimulatorConfig(
            ml_mode=request.ml_mode,
            # Fee-aware edge gate ENABLED for production B2 backtests (2026-06-02):
            # documented-floor artifact config/calibration/v1/edge_gate.yml
            # (THR-E01=2.0/THR-E02=15.0). Real runs enforce fee-aware edge discipline
            # (block trades whose edge cannot cover fees) → `fee_aware_edge_gate`
            # surface becomes CANONICAL. Simulator falls back gracefully if the
            # artifact is missing. Unit tests keep the gate-free default (None).
            fee_aware_edge_gate_config=FeeAwareEdgeGateConfig(),
            expected_edge_model_status=expected_edge_model_load_status,
            expected_edge_model_artifact_hash=expected_edge_model_load_result.artifact_hash,
            expected_edge_model_feature_hash=expected_edge_model_load_result.feature_hash,
            expected_edge_training_artifact_ref=(
                expected_edge_model_load_result.training_artifact_ref
                or (
                    str(request.frozen_ml_artifact_path.resolve())
                    if request.frozen_ml_artifact_path is not None
                    else None
                )
            ),
            protocol_contract_refs=("strategy_ladder_refusal_ledger.v1",),
            refusal_contract_status="REFUSAL_LEDGER_CONTRACT_DECLARED",
            live_transport_enabled=False,
            build14_context_status=build14_context_status,
            build14_feature_groups=build14_feature_groups,
            build14_upstream_filter_status=build14_upstream_filter_status,
            # Patch P1 #2 (2026-05-31, Option B) — enable the canonical
            # regime_classifier.regime_lite surface with governed documented
            # default thresholds (calibration seam, not hardcoded magic numbers).
            # DTRRecord.regime is populated from the canonical assessment when
            # the four regime metrics are present in feature_values, else falls
            # back to row.regime (no regression). Feeds dashboard section 5.
            regime_lite_thresholds=RegimeLiteThresholds.from_documented_defaults(),
        )
        with performance_profiler.phase(
            "replay_orchestration",
            status="OK",
            candidate_count=len(candidate_events),
        ):
            if resolve_worker_count() > 1:
                detailed_result = run_strategy_ladder_detailed_replay_parallel(
                    detailed_replay_dir,
                    candidate_events=candidate_events,
                    raw_window_manifests=raw_window_manifests,
                    capital_buckets=request.capital_buckets,
                    execution_runtime_projection_path=request.execution_runtime_projection_path,
                    simulator_config=detailed_simulator_config,
                )
            else:
                detailed_result = run_strategy_ladder_detailed_replay(
                    detailed_replay_dir,
                    candidate_events=candidate_events,
                    raw_window_manifests=raw_window_manifests,
                    capital_buckets=request.capital_buckets,
                    execution_runtime_projection_path=request.execution_runtime_projection_path,
                    simulator_config=detailed_simulator_config,
                )
        performance_profiler.observe_replay_subtimers(
            shared_payload_build_seconds=(
                detailed_result.performance_metrics.shared_payload_build_seconds
            ),
            engine_dataset_build_seconds=(
                detailed_result.performance_metrics.engine_dataset_build_seconds
            ),
            evaluate_replay_execution_seconds=(
                detailed_result.performance_metrics.evaluate_replay_execution_seconds
            ),
            replay_evidence_seconds=(
                detailed_result.performance_metrics.replay_evidence_seconds
            ),
            by_bucket_write_seconds=(
                detailed_result.performance_metrics.by_bucket_write_seconds
            ),
            candidate_wrapper_write_seconds=(
                detailed_result.performance_metrics.candidate_wrapper_write_seconds
            ),
            cache_hits_book_state=(
                detailed_result.performance_metrics.cache_hits_book_state
            ),
            cache_misses_book_state=(
                detailed_result.performance_metrics.cache_misses_book_state
            ),
            cache_hits_ohlcv=(
                detailed_result.performance_metrics.cache_hits_ohlcv
            ),
            cache_misses_ohlcv=(
                detailed_result.performance_metrics.cache_misses_ohlcv
            ),
            replay_workers_used=(
                detailed_result.performance_metrics.replay_workers_used
            ),
        )
    progress_manifest = _build_progress_manifest(
        request=request,
        run_dir=run_dir,
        silver_index_path=silver_index_path,
        silver_index_ready=silver_index_ready,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status=detailed_result.detailed_replay_status,
        capital_profile_generation_status="CAPITAL_PROFILE_NOT_PROVEN",
        promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
        sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
        feature_row_count=feature_result.row_count,
        candidate_count=candidate_baseline_count,
        raw_window_count=len(raw_window_manifests),
        detailed_replay_count=sum(
            len(items) for items in detailed_result.bucket_results_by_bucket.values()
        ),
        capital_profile_count=0,
        engine_promotion_count=0,
        pair_promotion_count=0,
        strategy_promotion_count=0,
        sample_size_survival_count=0,
        blocker_codes=_raw_window_stage_blockers(
            *(("RAW_WINDOW_NOT_PROVEN",) if raw_window_status == "RAW_WINDOW_NOT_PROVEN" else ()),
            *(
                ("DETAILED_REPLAY_NOT_PROVEN",)
                if detailed_result.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN"
                else ()
            ),
        ),
        created_at=created_at,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        candidate_engine_native_count=candidate_engine_native_progress_count,
        candidate_proxy_count=candidate_proxy_progress_count,
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
    )
    _persist_progress_run_manifest(
        run_dir,
        progress_manifest,
        progress_callback=progress_callback,
    )

    capital_profiles: tuple[CapitalBucketProfile, ...] = ()
    capital_profile_generation_status = "CAPITAL_PROFILE_NOT_PROVEN"
    if not request.fast_only and not request.dry_run:
        profiles: list[CapitalBucketProfile] = []
        for bucket in request.capital_buckets:
            profile = _capital_profile_for_bucket(
                request=request,
                capital_bucket=bucket,
                bucket_results=detailed_result.bucket_results_by_bucket.get(bucket, ()),
                bucket_dtrs=detailed_result.bucket_dtr_records.get(bucket, ()),
            )
            profiles.append(profile)
            capital_profiles_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(
                capital_profiles_dir / f"{bucket}.json",
                profile.model_dump(mode="json"),
            )
        capital_profiles = tuple(profiles)
        if all(profile.record_count not in {None, 0} for profile in capital_profiles):
            capital_profile_generation_status = "CAPITAL_PROFILE_GENERATION_READY"
        elif capital_profiles:
            capital_profile_generation_status = "CAPITAL_PROFILE_GENERATION_PARTIAL"
    progress_manifest = _build_progress_manifest(
        request=request,
        run_dir=run_dir,
        silver_index_path=silver_index_path,
        silver_index_ready=silver_index_ready,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status=detailed_result.detailed_replay_status,
        capital_profile_generation_status=capital_profile_generation_status,
        promotion_artifact_status="PROMOTION_ARTIFACTS_NOT_PROVEN",
        sample_size_status="SAMPLE_SIZE_NOT_PROVEN",
        feature_row_count=feature_result.row_count,
        candidate_count=candidate_baseline_count,
        raw_window_count=len(raw_window_manifests),
        detailed_replay_count=sum(
            len(items) for items in detailed_result.bucket_results_by_bucket.values()
        ),
        capital_profile_count=len(capital_profiles),
        engine_promotion_count=0,
        pair_promotion_count=0,
        strategy_promotion_count=0,
        sample_size_survival_count=0,
        blocker_codes=_raw_window_stage_blockers(
            *(("RAW_WINDOW_NOT_PROVEN",) if raw_window_status == "RAW_WINDOW_NOT_PROVEN" else ()),
            *(
                ("DETAILED_REPLAY_NOT_PROVEN",)
                if detailed_result.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN"
                else ()
            ),
        ),
        created_at=created_at,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        candidate_engine_native_count=candidate_engine_native_progress_count,
        candidate_proxy_count=candidate_proxy_progress_count,
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
    )
    _persist_progress_run_manifest(
        run_dir,
        progress_manifest,
        progress_callback=progress_callback,
    )

    all_bucket_results = tuple(
        result
        for bucket in request.capital_buckets
        for result in detailed_result.bucket_results_by_bucket.get(bucket, ())
    )
    all_bucket_dtrs = tuple(
        record
        for bucket in request.capital_buckets
        for record in detailed_result.bucket_dtr_records.get(bucket, ())
    )
    engine_artifacts: tuple[EnginePromotionArtifact, ...] = ()
    pair_artifacts: tuple[PairPromotionArtifact, ...] = ()
    strategy_artifacts: tuple[StrategyPromotionArtifact, ...] = ()
    sample_artifacts: tuple[SampleSizeSurvivalArtifact, ...] = ()
    promotion_artifact_status = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    sample_size_status = "SAMPLE_SIZE_NOT_PROVEN"
    execution_label_source = "REPLAY_PROXY_EXECUTION"
    fee_model_source = "REPLAY_PROXY"
    spread_model_source = "REPLAY_PROXY"
    slippage_model_source = "REPLAY_PROXY"
    partial_fill_model_source = "REPLAY_PROXY"
    adverse_selection_source = "REPLAY_PROXY"
    order_type_selection_source = "REPLAY_PROXY"
    venue_constraints_source = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    # Patch W3 (2026-05-30) — live_engine_parity_status default NOT_PROVEN when
    # shadow simulator did not run (fast_only/dry_run/no bucket results).
    # Overwritten below via _derive_live_engine_parity_status when shadow ran.
    live_engine_parity_status: str = "NOT_PROVEN"
    if not request.fast_only and not request.dry_run and all_bucket_results and all_bucket_dtrs:
        global_manifest = _build_replay_manifest(
            request=request,
            run_id=request.run_id,
            strategy_id="strategy_ladder",
            engines=tuple(sorted({item.engine_id for item in all_bucket_results})),
            pairs=tuple(sorted({item.pair for item in all_bucket_results})),
            record_count=max(len(all_bucket_dtrs), 1),
            start_timestamp_ms=min(item.timestamp_ms for item in all_bucket_results),
            end_timestamp_ms=max(item.timestamp_ms for item in all_bucket_results),
        )
        global_metrics_summary = build_replay_metrics_summary(
            all_bucket_dtrs,
            total_opportunities=len(all_bucket_results),
            initial_capital=max(request.capital_buckets) if request.capital_buckets else None,
            fee_provenance=_build_fee_provenance(all_bucket_results),
            impact_provenance=_build_impact_provenance(all_bucket_results),
            book_depth_availability=_build_book_depth_availability(all_bucket_results),
            fill_realism=_build_fill_realism(all_bucket_results),
            cost_parity=_build_cost_parity(all_bucket_results),
            capital_bucket_profiles=capital_profiles,
        )
        global_bundle = build_replay_promotion_artifact_bundle(
            run_manifest=global_manifest,
            metrics_summary=global_metrics_summary,
            dtr_records=all_bucket_dtrs,
            bucket_results=all_bucket_results,
            candidate_events=candidate_source_truth_events or candidate_events,
            input_data_hash=global_manifest.artifact_hash,
        )
        execution_label_source = global_metrics_summary.execution_label_source
        fee_model_source = global_metrics_summary.fee_model_source
        spread_model_source = global_metrics_summary.spread_model_source
        slippage_model_source = global_metrics_summary.slippage_model_source
        partial_fill_model_source = global_metrics_summary.partial_fill_model_source
        adverse_selection_source = global_metrics_summary.adverse_selection_source
        order_type_selection_source = global_metrics_summary.order_type_selection_source
        venue_constraints_source = global_metrics_summary.venue_constraints_source
        execution_fidelity_gap_codes = global_metrics_summary.execution_fidelity_gap_codes
        # Patch W3 (2026-05-30) — derive live parity status from shadow outputs
        live_engine_parity_status = _derive_live_engine_parity_status(
            fee_model_source=fee_model_source,
            spread_model_source=spread_model_source,
            slippage_model_source=slippage_model_source,
            partial_fill_model_source=partial_fill_model_source,
            adverse_selection_source=adverse_selection_source,
            order_type_selection_source=order_type_selection_source,
            venue_constraints_source=venue_constraints_source,
            execution_fidelity_gap_codes=execution_fidelity_gap_codes,
        )
        strategy_bundles = tuple(
            _build_strategy_bundle(
                request=request,
                strategy_id=strategy_id,
                bucket_results=tuple(
                    result for result in all_bucket_results if result.strategy_id == strategy_id
                ),
                bucket_dtrs=_strategy_records_for_scope(
                    all_bucket_results,
                    all_bucket_dtrs,
                    strategy_id,
                ),
                candidate_events=tuple(
                    candidate
                    for candidate in (candidate_source_truth_events or candidate_events)
                    if candidate.strategy_id == strategy_id
                ),
            )
            for strategy_id in _strategy_ids_from_results(all_bucket_results)
        )
        engine_artifacts = global_bundle.engine_promotion_artifacts
        pair_artifacts = global_bundle.pair_promotion_artifacts
        strategy_artifacts = tuple(
            artifact
            for bundle in strategy_bundles
            for artifact in bundle.strategy_promotion_artifacts
        )
        non_strategy_sample_artifacts = tuple(
            artifact
            for artifact in global_bundle.sample_size_survival_artifacts
            if artifact.scope not in {"strategy", "strategy_pair"}
        )
        strategy_sample_artifacts = tuple(
            artifact
            for bundle in strategy_bundles
            for artifact in bundle.sample_size_survival_artifacts
            if artifact.scope in {"strategy", "strategy_pair"}
        )
        sample_artifacts = tuple(
            {
                (artifact.scope, artifact.id): artifact
                for artifact in (*non_strategy_sample_artifacts, *strategy_sample_artifacts)
            }.values()
        )
        _write_promotion_payloads(
            run_dir,
            run_id=request.run_id,
            engine_artifacts=engine_artifacts,
            pair_artifacts=pair_artifacts,
            strategy_artifacts=strategy_artifacts,
            sample_artifacts=sample_artifacts,
        )
        promotion_artifact_status = _derive_promotion_artifact_status(
            engine_artifact_count=len(engine_artifacts),
            pair_artifact_count=len(pair_artifacts),
            strategy_artifact_count=len(strategy_artifacts),
            promotion_fidelity_blockers=(),
        )
        if sample_artifacts:
            sample_size_status = (
                "SAMPLE_SIZE_PROVEN"
                if any(
                    artifact.sample_size_survival_status == "SAMPLE_SIZE_PROVEN"
                    for artifact in sample_artifacts
                )
                else "SAMPLE_SIZE_NOT_PROVEN"
            )
    progress_manifest = _build_progress_manifest(
        request=request,
        run_dir=run_dir,
        silver_index_path=silver_index_path,
        silver_index_ready=silver_index_ready,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status=detailed_result.detailed_replay_status,
        capital_profile_generation_status=capital_profile_generation_status,
        promotion_artifact_status=promotion_artifact_status,
        sample_size_status=sample_size_status,
        feature_row_count=feature_result.row_count,
        candidate_count=candidate_baseline_count,
        raw_window_count=len(raw_window_manifests),
        detailed_replay_count=len(all_bucket_results),
        capital_profile_count=len(capital_profiles),
        engine_promotion_count=len(engine_artifacts),
        pair_promotion_count=len(pair_artifacts),
        strategy_promotion_count=len(strategy_artifacts),
        sample_size_survival_count=len(sample_artifacts),
        blocker_codes=_raw_window_stage_blockers(
            *(
                ("RAW_WINDOW_NOT_PROVEN",)
                if raw_window_status == "RAW_WINDOW_NOT_PROVEN" and not request.fast_only and not request.dry_run
                else ()
            ),
            *(("PAIR_UNIVERSE_EMPTY",) if pair_universe_status == "PAIR_UNIVERSE_EMPTY" else ()),
            *(
                ("SILVER_INDEX_NOT_READY",)
                if silver_index_status == "SILVER_INDEX_NOT_READY" and not request.fast_only and not request.dry_run
                else ()
            ),
            *(
                ("DETAILED_REPLAY_NOT_PROVEN",)
                if detailed_result.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN" and not request.fast_only and not request.dry_run
                else ()
            ),
        ),
        created_at=created_at,
        expected_edge_proxy_count=expected_edge_proxy_count,
        expected_edge_governed_count=expected_edge_governed_count,
        candidate_engine_native_count=candidate_engine_native_progress_count,
        candidate_proxy_count=candidate_proxy_progress_count,
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
    )
    _persist_progress_run_manifest(
        run_dir,
        progress_manifest,
        progress_callback=progress_callback,
    )

    executed_trade_count = _count_executed_trades(all_bucket_results)
    statistical_validation_result = _compute_statistical_validation_result(
        request=request,
        bucket_results=all_bucket_results,
    )
    trade_eligible_candidate_count = len(
        {
            result.candidate_id
            for result in all_bucket_results
            if str(result.execution_state or "") in {"selected", "reduced", "executed"}
        }
    )
    # Audit 2026-05-07 (P3a wire) — invocation opt-in du pont microstructure
    final_status = _stage_final_status(
        request=request,
        feature_store_status=feature_result.feature_store_status,
        candidate_export_status=candidate_export_status,
        raw_window_status=raw_window_status,
        detailed_replay_status=detailed_result.detailed_replay_status,
        capital_profile_count=len(capital_profiles),
        promotion_artifact_count=(
            len(engine_artifacts) + len(pair_artifacts) + len(strategy_artifacts)
        ),
        executed_trade_count=executed_trade_count,
        detailed_replay_record_count=len(all_bucket_results),
        statistical_validation_status=statistical_validation_result.status,
    )
    candidate_count_semantics = summarize_candidate_count_semantics(
        candidate_source_truth_events or materialized_candidate_events or candidate_events
    )
    materialized_candidate_semantics = summarize_candidate_count_semantics(
        materialized_candidate_events or candidate_events
    )
    replay_candidate_semantics = summarize_candidate_count_semantics(candidate_events)
    materialized_candidate_count = len(materialized_candidate_events or candidate_events)
    truth_candidate_events = materialized_candidate_events or candidate_events
    candidate_engine_native_count = (
        materialized_candidate_semantics.engine_native_candidate_count
    )
    candidate_proxy_count = materialized_candidate_semantics.proxy_candidate_count
    final_expected_edge_governed_count = sum(
        1
        for event in truth_candidate_events
        if is_expected_edge_backtest_truth(
            (event.compatibility_payload or {}).get("expected_edge_provenance")
        )
    )
    final_expected_edge_proxy_count = max(
        expected_edge_proxy_count,
        len(truth_candidate_events) - final_expected_edge_governed_count,
    )
    final_expected_edge_statuses = tuple(
        expected_edge_backtest_truth_status(
            (event.compatibility_payload or {}).get("expected_edge_provenance")
        )
        for event in truth_candidate_events
    )
    if not truth_candidate_events:
        candidate_truth_status = "CANDIDATE_TRUTH_NOT_PROVEN"
    elif candidate_proxy_count > 0:
        candidate_truth_status = "CANDIDATE_TRUTH_PROXY_PRESENT"
    elif candidate_engine_native_count == materialized_candidate_count:
        candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_READY"
    elif candidate_engine_native_count > 0:
        candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_PARTIAL"
    else:
        candidate_truth_status = "CANDIDATE_ENGINE_NATIVE_NOT_PROVEN"
    if not truth_candidate_events:
        expected_edge_truth_status = "EXPECTED_EDGE_NOT_PROVEN"
    elif final_expected_edge_proxy_count == 0 and final_expected_edge_governed_count > 0:
        expected_edge_truth_status = "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
    elif final_expected_edge_governed_count > 0:
        expected_edge_truth_status = "EXPECTED_EDGE_MIXED_PROXY_BLOCKED"
    elif "EXPECTED_EDGE_MODEL_BLOCKED" in final_expected_edge_statuses:
        expected_edge_truth_status = "EXPECTED_EDGE_MODEL_BLOCKED"
    else:
        expected_edge_truth_status = "EXPECTED_EDGE_PROXY_BLOCKED"
    economic_statuses = tuple(
        str((event.compatibility_payload or {}).get("economic_provenance") or "")
        for event in truth_candidate_events
    )
    final_expected_edge_model_statuses = tuple(
        str((event.compatibility_payload or {}).get("expected_edge_model_status") or "")
        for event in truth_candidate_events
    )
    if "GOVERNED_EDGE_MODEL_READY" in final_expected_edge_model_statuses:
        expected_edge_model_status = "GOVERNED_EDGE_MODEL_READY"
    elif expected_edge_model_required:
        expected_edge_model_status = expected_edge_model_load_status
    else:
        expected_edge_model_status = "EXPECTED_EDGE_MODEL_NOT_REQUESTED"
    final_expected_edge_model_artifact_hash = (
        expected_edge_model_load_result.artifact_hash
        or next(
            (
                str((event.compatibility_payload or {}).get("expected_edge_model_artifact_hash"))
                for event in candidate_events
                if (event.compatibility_payload or {}).get("expected_edge_model_artifact_hash")
            ),
            None,
        )
    )
    final_expected_edge_model_feature_hash = (
        expected_edge_model_load_result.feature_hash
        or next(
            (
                str((event.compatibility_payload or {}).get("expected_edge_model_feature_hash"))
                for event in candidate_events
                if (event.compatibility_payload or {}).get("expected_edge_model_feature_hash")
            ),
            None,
        )
    )
    expected_edge_training_artifact_ref = (
        expected_edge_model_load_result.training_artifact_ref
        or (
            str(request.frozen_ml_artifact_path.resolve())
            if request.frozen_ml_artifact_path is not None
            else ""
        )
    )
    expected_edge_label_source = (
        expected_edge_model_load_result.label_source
        if expected_edge_training_artifact_ref
        else "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
    )
    expected_edge_label_fidelity = (
        expected_edge_model_load_result.label_fidelity
        if expected_edge_training_artifact_ref
        else "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    )
    expected_edge_anti_leakage_status = (
        expected_edge_model_load_result.anti_leakage_status
        if expected_edge_training_artifact_ref
        else "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
    )
    expected_edge_walkforward_status = (
        expected_edge_model_load_result.walkforward_status
        if expected_edge_training_artifact_ref
        else "EXPECTED_EDGE_WALKFORWARD_NOT_DECLARED"
    )
    expected_edge_horizon = (
        expected_edge_model_load_result.horizon_minutes
        if expected_edge_training_artifact_ref
        else None
    )
    expected_edge_purge_window = (
        expected_edge_model_load_result.purge_window_minutes
        if expected_edge_training_artifact_ref
        else None
    )
    expected_edge_embargo_window = (
        expected_edge_model_load_result.embargo_window_minutes
        if expected_edge_training_artifact_ref
        else None
    )
    expected_edge_blocker_codes = _merge_blocker_codes(
        expected_edge_model_load_result.blocker_codes,
        (
            expected_edge_truth_status,
            "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH",
        )
        if final_expected_edge_proxy_count > 0
        else (),
        (
            "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
        )
        if final_expected_edge_governed_count > 0
        and expected_edge_label_fidelity == "EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY"
        else (),
    )
    if economic_statuses and all(status == "FULLY_MEASURED" for status in economic_statuses):
        economic_constants_provenance = "FULLY_MEASURED"
    elif any(status in {"FULLY_MEASURED", "PARTIALLY_MEASURED"} for status in economic_statuses):
        economic_constants_provenance = "PARTIALLY_MEASURED"
    elif request.engine_native_mode:
        economic_constants_provenance = "ECONOMIC_PROVENANCE_BLOCKED"
    else:
        economic_constants_provenance = "HARDCODED_PROXY_CONSTANTS"
    promotion_fidelity_blockers = _promotion_fidelity_blockers(
        candidate_truth_status=candidate_truth_status,
        expected_edge_truth_status=expected_edge_truth_status,
        economic_constants_provenance=economic_constants_provenance,
        execution_fidelity_gap_codes=execution_fidelity_gap_codes,
        statistical_validation_status=statistical_validation_result.status,
        statistical_validation_blocker_codes=statistical_validation_result.blocker_codes,
    )
    promotion_artifact_status = _derive_promotion_artifact_status(
        engine_artifact_count=len(engine_artifacts),
        pair_artifact_count=len(pair_artifacts),
        strategy_artifact_count=len(strategy_artifacts),
        promotion_fidelity_blockers=promotion_fidelity_blockers,
    )
    replay_count_semantics = summarize_replay_count_semantics(
        unique_candidate_count=candidate_count_semantics.unique_candidate_count,
        bucket_results=all_bucket_results,
    )
    resolved_pairs = request.pairs or tuple(
        sorted(
            {
                *(event.pair for event in candidate_events if event.pair),
                *(item.pair for item in all_bucket_results if item.pair),
            }
        )
    )
    resolved_engines = request.engines or tuple(
        sorted(
            {
                *(event.engine_id for event in candidate_events if event.engine_id),
                *(item.engine_id for item in all_bucket_results if item.engine_id),
            }
        )
    )
    resolved_timeframes = request.timeframes or tuple(
        sorted({event.timeframe for event in candidate_events if event.timeframe})
    )
    resolved_engine_count = max(
        (
            candidate_summary.engine_count
            if candidate_summary is not None and candidate_summary.engine_count > 0
            else 0
        ),
        len(resolved_engines),
        candidate_count_semantics.engine_count,
        len(request.engines),
        4,
    )
    resolved_effective_sample_size = (
        candidate_summary.effective_engine_native_sample_size
        if candidate_summary is not None
        else _effective_candidate_sample_cap(request)
    )
    resolved_pair_count_for_cap = max(len(resolved_pairs), 1)
    resolved_candidate_sample_cap = (
        candidate_summary.candidate_sample_cap
        if candidate_summary is not None
        else _candidate_sample_cap_total(
            effective_sample_cap=resolved_effective_sample_size,
            engine_count=resolved_engine_count,
            pair_count=resolved_pair_count_for_cap,
            candidate_discovery_mode=request.candidate_discovery_mode,
        )
    )
    resolved_candidate_discovery_mode = (
        candidate_summary.candidate_discovery_mode
        if candidate_summary is not None and candidate_summary.candidate_discovery_mode
        else request.candidate_discovery_mode
    )
    resolved_candidate_cap_formula = (
        candidate_summary.candidate_cap_formula
        if candidate_summary is not None and candidate_summary.candidate_cap_formula
        else _candidate_cap_formula(
            effective_sample_cap=resolved_effective_sample_size,
            engine_count=resolved_engine_count,
            pair_count=resolved_pair_count_for_cap,
            candidate_discovery_mode=resolved_candidate_discovery_mode,
        )
    )
    resolved_small_scope_enabled = (
        candidate_summary.small_scope_enabled
        if candidate_summary is not None
        else request.small_scope_enabled
    )
    resolved_full_scan_enabled = (
        candidate_summary.full_scan_enabled
        if candidate_summary is not None
        else request.full_scan_enabled
    )
    resolved_no_full_scan_enabled = (
        candidate_summary.no_full_scan_enabled
        if candidate_summary is not None
        else request.no_full_scan_enabled
    )
    resolved_candidate_discovery_limited = (
        candidate_summary.candidate_discovery_limited
        if candidate_summary is not None
        else (
            bool(resolved_candidate_sample_cap)
            and candidate_count_semantics.unique_candidate_count >= resolved_candidate_sample_cap
        )
    )
    resolved_candidate_discovery_limit_reason = (
        candidate_summary.candidate_discovery_limit_reason
        if candidate_summary is not None
        else (
            "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE"
            if resolved_candidate_discovery_limited
            else "DISCOVERY_EXHAUSTED_BEFORE_CAP"
        )
    )
    resolved_candidate_discovery_cap_status = (
        candidate_summary.candidate_discovery_cap_status
        if candidate_summary is not None and candidate_summary.candidate_discovery_cap_status
        else (
            "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
            if resolved_candidate_sample_cap > 0
            and candidate_count_semantics.unique_candidate_count >= resolved_candidate_sample_cap
            else (
                "CANDIDATE_DISCOVERY_EXHAUSTED"
                if candidate_count_semantics.unique_candidate_count > 0
                and resolved_full_scan_enabled
                else (
                    "CANDIDATE_DISCOVERY_FULL_SCAN_ENABLED"
                    if resolved_full_scan_enabled
                    else "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
                )
            )
        )
    )
    resolved_temporal_bucket_granularity = (
        candidate_summary.temporal_bucket_granularity
        if candidate_summary is not None and candidate_summary.temporal_bucket_granularity
        else ""
    )
    resolved_temporal_bucket_count_available = (
        candidate_summary.temporal_bucket_count_available
        if candidate_summary is not None
        else 0
    )
    resolved_temporal_bucket_count_selected = (
        candidate_summary.temporal_bucket_count_selected
        if candidate_summary is not None
        else 0
    )
    resolved_temporal_bucket_coverage_ratio = (
        candidate_summary.temporal_bucket_coverage_ratio
        if candidate_summary is not None
        else None
    )
    summary_inconsistency_codes: list[str] = []
    if data_factory_manifest_payload:
        if data_factory_status == "DATA_FACTORY_NOT_PROVEN":
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
        if silver_index_status == "SILVER_INDEX_NOT_READY":
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
        if gold_feature_store_status == "GOLD_FEATURE_STORE_NOT_READY":
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
    if candidate_summary is not None:
        if (
            candidate_summary.candidate_sample_cap > 0
            and resolved_candidate_sample_cap != candidate_summary.candidate_sample_cap
        ):
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
        if (
            candidate_summary.effective_engine_native_sample_size > 0
            and resolved_effective_sample_size
            != candidate_summary.effective_engine_native_sample_size
        ):
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
        if resolved_full_scan_enabled != candidate_summary.full_scan_enabled:
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
        if resolved_small_scope_enabled != candidate_summary.small_scope_enabled:
            summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
    if candidate_events and engine_native_status == "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS":
        summary_inconsistency_codes.append("SUMMARY_INCONSISTENT")
    count_semantics_validator_codes: list[str] = []
    if summary_inconsistency_codes:
        count_semantics_validator_codes.extend(summary_inconsistency_codes)
    if (
        candidate_count_semantics.unique_candidate_count > 0
        and replay_count_semantics.replay_record_count
        > candidate_count_semantics.unique_candidate_count
        and not replay_count_semantics.replay_expansion_axis
    ):
        count_semantics_validator_codes.append("REPLAY_EXPANSION_UNDECLARED")
    if (
        candidate_count_semantics.unique_candidate_count > 0
        and engine_native_status == "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS"
        and materialized_candidate_semantics.candidate_source_status
        not in {
            "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
            "CANDIDATE_SOURCE_FALLBACK_SYNTHETIC",
            "CANDIDATE_SOURCE_MIXED_ENGINE_AND_PROXY",
        }
    ):
        count_semantics_validator_codes.append("SUMMARY_INCONSISTENT")
    matrix_count_inflation_status = (
        "COUNT_SEMANTICS_CONSISTENT"
        if not count_semantics_validator_codes
        else "COUNT_SEMANTICS_BLOCKED"
    )
    run_manifest = StrategyLadderRunManifest(
        run_id=request.run_id,
        input_root=str(request.input_root.resolve()),
        feature_store_root=str(request.feature_store_root.resolve()),
        raw_root=str(request.raw_root.resolve()),
        raw_roots=tuple(str(path.resolve()) for path in request.raw_roots),
        raw_source_manifest_path=resolved_raw_source_manifest_path,
        silver_index_path=str(silver_index_path.resolve()) if silver_index_ready else "",
        output_root=str(run_dir.resolve()),
        workflow_run_id=request.workflow_run_id,
        phase_run_id=request.phase_run_id,
        parent_workflow_ref=request.parent_workflow_ref,
        pairs=resolved_pairs,
        engines=resolved_engines,
        capital_buckets=request.capital_buckets,
        timeframes=resolved_timeframes,
        feature_names=request.feature_names,
        start=request.start,
        end=request.end,
        fast_only=request.fast_only,
        detailed_only=request.detailed_only,
        resume=request.resume,
        dry_run=request.dry_run,
        ml_mode_status=ml_mode_status,
        # Patch W3 (2026-05-30) — propagate shadow simulator parity verdict
        live_engine_parity_status=live_engine_parity_status,
        data_factory_status=data_factory_status,
        raw_source_status=raw_source_status,
        pair_universe_status=pair_universe_status,
        silver_index_status=silver_index_status,
        gold_feature_store_status=gold_feature_store_status,
        orderbook_reconstruction_status=orderbook_reconstruction_status,
        feature_store_status=feature_result.feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        raw_window_extraction_status=raw_window_status,
        raw_window_materialization_mode=_normalize_raw_window_materialization_mode(request),
        detailed_replay_status=detailed_result.detailed_replay_status,
        capital_profile_generation_status=capital_profile_generation_status,
        promotion_artifact_status=promotion_artifact_status,
        sample_size_survival_status=sample_size_status,
        final_status=final_status,
        blocker_codes=_raw_window_stage_blockers(
            *(
                ("RAW_WINDOW_NOT_PROVEN",)
                if raw_window_status == "RAW_WINDOW_NOT_PROVEN" and not request.fast_only and not request.dry_run
                else ()
            ),
            *(("PAIR_UNIVERSE_EMPTY",) if pair_universe_status == "PAIR_UNIVERSE_EMPTY" else ()),
            *(
                ("SILVER_INDEX_NOT_READY",)
                if silver_index_status == "SILVER_INDEX_NOT_READY" and not request.fast_only and not request.dry_run
                else ()
            ),
            *(
                ("DETAILED_REPLAY_NOT_PROVEN",)
                if detailed_result.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN" and not request.fast_only and not request.dry_run
                else ()
            ),
            *(
                ("NO_EXECUTED_TRADES",)
                if (
                    executed_trade_count == 0
                    and len(all_bucket_results) > 0
                    and not request.fast_only
                    and not request.dry_run
                )
                else ()
            ),
            *promotion_fidelity_blockers,
            *statistical_validation_result.blocker_codes,
            *summary_inconsistency_codes,
        ),
        feature_row_count=feature_result.row_count,
        candidate_sample_cap=resolved_candidate_sample_cap,
        effective_engine_native_sample_size=resolved_effective_sample_size,
        engine_count=resolved_engine_count,
        candidate_cap_formula=resolved_candidate_cap_formula,
        small_scope_enabled=resolved_small_scope_enabled,
        full_scan_enabled=resolved_full_scan_enabled,
        no_full_scan_enabled=resolved_no_full_scan_enabled,
        candidate_discovery_limited=resolved_candidate_discovery_limited,
        candidate_discovery_limit_reason=resolved_candidate_discovery_limit_reason,
        candidate_discovery_mode=resolved_candidate_discovery_mode,
        candidate_discovery_cap_status=resolved_candidate_discovery_cap_status,
        temporal_bucket_granularity=resolved_temporal_bucket_granularity,
        temporal_bucket_count_available=resolved_temporal_bucket_count_available,
        temporal_bucket_count_selected=resolved_temporal_bucket_count_selected,
        temporal_bucket_coverage_ratio=resolved_temporal_bucket_coverage_ratio,
        preselection_status=(
            preselection_result.status
            if preselection_result is not None
            else "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN"
        ),
        replay_input_mode_status=(
            "DIAGNOSTIC_FULL_REPLAY"
            if request.diagnostic_full_replay
            else "PRESELECTED_ONLY"
        ),
        preselected_only=(request.preselected_only and not request.diagnostic_full_replay),
        diagnostic_full_replay=request.diagnostic_full_replay,
        b1_5_policy_mode=request.b1_5_policy_mode,
        candidate_count=candidate_count_semantics.unique_candidate_count,
        unique_candidate_count=candidate_count_semantics.unique_candidate_count,
        base_event_count=candidate_count_semantics.base_event_count,
        per_engine_candidate_count=candidate_count_semantics.per_engine_candidate_count,
        engine_native_candidate_count=materialized_candidate_semantics.engine_native_candidate_count,
        discovery_pre_candidate_count=candidate_count_semantics.unique_candidate_count,
        engine_native_preselected_count=(
            preselection_result.engine_native_preselected_count
            if preselection_result is not None
            else 0
        ),
        preselection_hard_rejected_count=(
            preselection_result.preselection_hard_rejected_count
            if preselection_result is not None
            else 0
        ),
        preselection_soft_flagged_count=(
            preselection_result.preselection_soft_flagged_count
            if preselection_result is not None
            else 0
        ),
        preselection_passed_count=(
            preselection_result.preselection_passed_count
            if preselection_result is not None
            else 0
        ),
        b2_replay_candidate_count=replay_candidate_semantics.unique_candidate_count,
        trade_eligible_candidate_count=trade_eligible_candidate_count,
        preselection_rejection_count=(
            preselection_result.preselection_rejection_count
            if preselection_result is not None
            else 0
        ),
        replay_savings_estimate_count=(
            preselection_result.replay_savings_estimate_count
            if preselection_result is not None
            else 0
        ),
        replay_record_count=replay_count_semantics.replay_record_count,
        evaluation_record_count=replay_count_semantics.evaluation_record_count,
        promotion_record_count=replay_count_semantics.promotion_record_count,
        capital_bucket_record_count=replay_count_semantics.capital_bucket_record_count,
        replay_expansion_factor=replay_count_semantics.replay_expansion_factor,
        replay_expansion_axis=replay_count_semantics.replay_expansion_axis,
        candidate_source_status=materialized_candidate_semantics.candidate_source_status,
        count_semantics_validator_codes=tuple(dict.fromkeys(count_semantics_validator_codes)),
        matrix_count_inflation_status=matrix_count_inflation_status,
        raw_window_count=len(raw_window_manifests),
        raw_windows_total=raw_window_linkage_counts["raw_windows_total"],
        trade_windows_found=raw_window_linkage_counts["trade_windows_found"],
        trade_windows_missing=raw_window_linkage_counts["trade_windows_missing"],
        book_windows_found=raw_window_linkage_counts["book_windows_found"],
        book_windows_missing=raw_window_linkage_counts["book_windows_missing"],
        ohlcv_windows_found=raw_window_linkage_counts["ohlcv_windows_found"],
        ohlcv_windows_missing=raw_window_linkage_counts["ohlcv_windows_missing"],
        depth20_found=raw_window_linkage_counts["depth20_found"],
        depth20_missing=raw_window_linkage_counts["depth20_missing"],
        detailed_replay_count=len(all_bucket_results),
        capital_profile_count=len(capital_profiles),
        engine_promotion_count=len(engine_artifacts),
        pair_promotion_count=len(pair_artifacts),
        strategy_promotion_count=len(strategy_artifacts),
        sample_size_survival_count=len(sample_artifacts),
        # Audit 2026-05-06 — flags de veracite (cf. _stage_final_status).
        # Audit 2026-05-07 (P0 CE/cost provenance) — quand engine_native_mode
        # Final provenance is derived from the materialized candidate payloads.
        economic_constants_provenance=economic_constants_provenance,
        candidate_truth_status=candidate_truth_status,
        expected_edge_truth_status=expected_edge_truth_status,
        execution_label_source=execution_label_source,
        fee_model_source=fee_model_source,
        spread_model_source=spread_model_source,
        slippage_model_source=slippage_model_source,
        partial_fill_model_source=partial_fill_model_source,
        adverse_selection_source=adverse_selection_source,
        order_type_selection_source=order_type_selection_source,
        venue_constraints_source=venue_constraints_source,
        execution_fidelity_gap_codes=execution_fidelity_gap_codes,
        expected_edge_proxy_count=final_expected_edge_proxy_count,
        expected_edge_governed_count=final_expected_edge_governed_count,
        expected_edge_model_status=expected_edge_model_status,
        expected_edge_model_artifact_hash=final_expected_edge_model_artifact_hash,
        expected_edge_model_feature_hash=final_expected_edge_model_feature_hash,
        expected_edge_training_artifact_ref=expected_edge_training_artifact_ref,
        expected_edge_label_source=expected_edge_label_source,
        expected_edge_label_fidelity=expected_edge_label_fidelity,
        expected_edge_anti_leakage_status=expected_edge_anti_leakage_status,
        expected_edge_walkforward_status=expected_edge_walkforward_status,
        expected_edge_horizon=expected_edge_horizon,
        expected_edge_purge_window=expected_edge_purge_window,
        expected_edge_embargo_window=expected_edge_embargo_window,
        expected_edge_blocker_codes=expected_edge_blocker_codes,
        candidate_engine_native_count=candidate_engine_native_count,
        candidate_proxy_count=candidate_proxy_count,
        executed_trade_count=executed_trade_count,
        statistical_validation_status=statistical_validation_result.status,
        statistical_validation_observation_count=statistical_validation_result.observation_count,
        statistical_validation_trial_count=statistical_validation_result.trial_count,
        statistical_validation_benchmark_sharpe=statistical_validation_result.benchmark_sharpe,
        statistical_validation_acceptance_floor=statistical_validation_result.acceptance_floor,
        statistical_validation_sample_sharpe=statistical_validation_result.sample_sharpe,
        statistical_validation_psr=statistical_validation_result.psr,
        statistical_validation_dsr=statistical_validation_result.dsr,
        statistical_validation_stationary_block_length=statistical_validation_result.stationary_block_length,
        statistical_validation_effective_sample_size=statistical_validation_result.effective_sample_size,
        statistical_validation_min_trl_required=statistical_validation_result.min_trl_required,
        statistical_validation_min_trl_satisfied=statistical_validation_result.min_trl_satisfied,
        statistical_validation_psr_passes_floor=statistical_validation_result.psr_passes_floor,
        statistical_validation_dsr_passes_floor=statistical_validation_result.dsr_passes_floor,
        statistical_validation_blocker_codes=statistical_validation_result.blocker_codes,
        # Audit 2026-05-06 (P3a) — Statut du pont microstructure vers les
        # Native status now reflects full-path runner invocation before replay.
        engine_native_status=engine_native_status,
        engine_native_records_built=engine_native_records_built,
        created_at=created_at,
        updated_at=datetime.now(tz=UTC),
    )
    run_manifest = run_manifest.model_copy(
        update={"artifact_hash": deterministic_payload_hash(run_manifest.model_dump(mode="json"))}
    )
    atomic_write_json(run_dir / "run_manifest.json", run_manifest.model_dump(mode="json"))
    _clear_progress_run_manifest(run_dir)
    replay_artifact_refs = {
        artifact.candidate_id: str((detailed_replay_dir / f"{artifact.candidate_id}.json").resolve())
        for artifact in detailed_result.candidate_artifacts
    }
    replay_bucket_refs = {
        artifact.candidate_id: artifact.bucket_result_refs
        for artifact in detailed_result.candidate_artifacts
    }
    with performance_profiler.phase(
        "refusal_ledger_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        operator_artifact_refs = write_strategy_ladder_operator_artifacts(
            run_dir=run_dir,
            candidate_events=candidate_events,
            raw_window_manifests=raw_window_manifests,
            bucket_results=all_bucket_results,
            replay_artifact_refs=replay_artifact_refs,
            replay_bucket_refs=replay_bucket_refs,
        )
    with performance_profiler.phase(
        "dashboard_report_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        evidence_index = build_governed_audit_evidence_index(
            run_id=request.run_id,
            source_root=run_dir,
            entries=_build_governed_audit_evidence_entries(
                run_id=request.run_id,
                run_dir=run_dir,
                capital_profiles=capital_profiles,
                engine_artifacts=engine_artifacts,
                pair_artifacts=pair_artifacts,
                strategy_artifacts=strategy_artifacts,
                sample_artifacts=sample_artifacts,
                operator_artifact_refs=operator_artifact_refs,
            ),
        )
        reports_dir.mkdir(parents=True, exist_ok=True)
        evidence_index_path = reports_dir / "governed_audit_evidence_index.json"
        atomic_write_json(
            evidence_index_path,
            evidence_index.model_dump(mode="json"),
        )
        evidence_projection = build_governed_audit_evidence_projection(
            index=evidence_index,
            index_path=evidence_index_path,
        )

        report_summary = _build_report_summary(
            request=request,
            run_manifest=run_manifest,
            capital_profiles=capital_profiles,
            engine_artifacts=engine_artifacts,
            pair_artifacts=pair_artifacts,
            strategy_artifacts=strategy_artifacts,
            sample_artifacts=sample_artifacts,
            bucket_results=all_bucket_results,
            evidence_projection=evidence_projection,
        )
    with performance_profiler.phase(
        "matrix_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        _write_reports(
            reports_dir,
            summary=report_summary,
            run_manifest=run_manifest,
            gold_manifest_payload=gold_manifest_payload,
            capital_profiles=capital_profiles,
            engine_artifacts=engine_artifacts,
            pair_artifacts=pair_artifacts,
            strategy_artifacts=strategy_artifacts,
            sample_artifacts=sample_artifacts,
            operator_artifact_refs=operator_artifact_refs,
        )
    with performance_profiler.phase(
        "label_store_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        label_store_result = build_strategy_ladder_b2_label_store(
            StrategyLadderB2LabelStoreBuilderRequest(
                run_root=run_dir,
                output_dir=run_dir / "ml_label_store",
            )
        )
    with performance_profiler.phase(
        "b2_label_store_ml_training_audit_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        b2_label_store_ml_training_audit_filename = "b2_label_store_ml_training_audit.json"
        try:
            from local_replay_runtime.b2_label_store_ml_training_audit import (
                B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME,
                write_b2_label_store_ml_training_audit_reports,
            )

            b2_label_store_ml_training_audit_filename = (
                B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME
            )
            write_b2_label_store_ml_training_audit_reports(
                run_dir,
                label_store_path=Path(label_store_result.dataset_path),
            )
        except Exception as exc:  # pragma: no cover - defensive audit fallback
            atomic_write_json(
                reports_dir / b2_label_store_ml_training_audit_filename,
                {
                    "schema_version": "v53.b2_label_store_ml_training_audit.v1",
                    "generated_at": datetime.now(tz=UTC).isoformat(),
                    "run_id": request.run_id,
                    "workflow_root": str(run_dir.resolve()),
                    "label_store_path": getattr(label_store_result, "dataset_path", ""),
                    "row_count": 0,
                    "scientifically_valid_for_training": False,
                    "scientifically_valid_for_promotion": False,
                    "final_verdict": "B2_LABEL_STORE_INSUFFICIENT_ROWS",
                    "status": "INSUFFICIENT_DATA",
                    "error_type": type(exc).__name__,
                },
                indent=2,
            )
    with performance_profiler.phase(
        "gate_counterfactual_analysis_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        write_strategy_ladder_gate_waterfall_reports(
            run_dir=run_dir,
            summary=report_summary,
            run_manifest=run_manifest,
            label_store_summary_path=Path(label_store_result.summary_path),
            label_store_quality_report_path=Path(label_store_result.quality_report_path),
        )
    with performance_profiler.phase(
        "candidate_trade_semantics_audit_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        write_strategy_ladder_candidate_trade_semantics_audit(
            run_dir=run_dir,
            summary=report_summary,
            run_manifest=run_manifest,
            source_candidate_events=candidate_source_truth_events or candidate_events,
            materialized_candidate_events=materialized_candidate_events or candidate_events,
        )
    with performance_profiler.phase(
        "backtest_decision_report_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        write_backtest_decision_reports(run_dir)
    # Patch BACKBONE-PARITY-WIRING-1 (2026-05-27) — Wire the read-only
    # backbone parity audit module to the runner so the 12 aggregate reports
    # documented in `docs/audit/2026-05-27_BACKTEST_BACKBONE_PARITY_DIAGNOSTIC_PATCH_PLAN.md`
    # are produced at runtime. Without this, the module
    # `backtest_backbone_parity_audit.py` is self-contained and the
    # backbone_parity_final_report / backbone_module_usage_matrix /
    # backtest_decision_source_matrix / count_semantics_deep_audit /
    # reason_code_taxonomy_audit / engine_a_executed_candidate_autopsy / etc.
    # never reach the run directory. Per-bucket `backbone_surface_report`
    # remains the row-level evidence; this module aggregates the surface
    # status across all bucket records into operator-readable artifacts.
    with performance_profiler.phase(
        "backtest_backbone_parity_audit_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        try:
            from local_replay_runtime.backtest_backbone_parity_audit import (
                BACKTEST_BACKBONE_PARITY_AUDIT_FILENAME,
                write_backtest_backbone_parity_audit_reports,
            )

            write_backtest_backbone_parity_audit_reports(run_dir)
        except Exception as exc:  # pragma: no cover - defensive audit fallback
            atomic_write_json(
                reports_dir / "backtest_backbone_parity_audit.json",
                {
                    "schema_version": "v53.backtest_backbone_parity_audit.v1",
                    "generated_at": datetime.now(tz=UTC).isoformat(),
                    "run_id": request.run_id,
                    "audit_mode": "READ_ONLY",
                    "status": "INSUFFICIENT_DATA",
                    "error_type": type(exc).__name__,
                    "trading_logic_modified": False,
                    "thresholds_modified": False,
                },
                indent=2,
            )
    with performance_profiler.phase(
        "no_shadow_threshold_challenge_generation",
        status="OK",
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    ):
        no_shadow_threshold_challenge_filename = "no_shadow_threshold_challenge_report.json"
        try:
            from local_replay_runtime.no_shadow_threshold_challenge import (
                NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME,
                write_no_shadow_threshold_challenge_reports,
            )

            no_shadow_threshold_challenge_filename = NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME
            write_no_shadow_threshold_challenge_reports(run_dir)
        except Exception as exc:  # pragma: no cover - defensive audit fallback
            atomic_write_json(
                reports_dir / no_shadow_threshold_challenge_filename,
                {
                    "schema_version": "v53.no_shadow_threshold_challenge.v1",
                    "generated_at": datetime.now(tz=UTC).isoformat(),
                    "run_id": request.run_id,
                    "mode": "OFFLINE_COUNTERFACTUAL_ONLY",
                    "shadow_used": False,
                    "trading_decisions_modified": False,
                    "status": "INSUFFICIENT_DATA",
                    "error_type": type(exc).__name__,
                    "profitability_claim_allowed": False,
                },
                indent=2,
            )
    performance_profiler.finalize_counts(
        candidate_count=len(candidate_events),
        replay_record_count=len(all_bucket_results),
    )
    performance_profiler.write(run_dir)
    if operator_artifact_refs.get("timeframe_matrix"):
        run_manifest = _persist_canonical_run_manifest(
            run_dir,
            run_manifest,
            progress_callback=progress_callback,
        )
    _sync_parent_workflow_phase_record(
        request,
        run_manifest=run_manifest,
        data_factory_root=data_factory_root,
        candidate_events_source_path=candidate_events_source_path,
        run_dir=run_dir,
        fast_candidates_dir=fast_candidates_dir,
        reports_dir=reports_dir,
        operator_artifact_refs=operator_artifact_refs,
        silver_index_report_payload=silver_index_report_payload,
    )
    return StrategyLadderRunResult(
        run_manifest=run_manifest,
        report_summary=report_summary,
        capital_profiles=capital_profiles,
        engine_promotion_artifacts=engine_artifacts,
        pair_promotion_artifacts=pair_artifacts,
        strategy_promotion_artifacts=strategy_artifacts,
        sample_size_survival_artifacts=sample_artifacts,
    )


__all__ = [
    "StrategyLadderRunResult",
    "run_backtest_strategy_ladder",
]
