"""Detailed candidate-window replay for the canonical Strategy Ladder runner."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from local_replay_runtime.replay_execution_contracts import (
    ReplayExecutionEvaluationRequest,
)
from local_replay_runtime.replay_execution_runtime import (
    evaluate_replay_execution,
)
from local_replay_runtime.strategy_ladder_replay_evidence import (
    StrategyLadderReplayEvidenceCache,
    build_measured_cost_governance_payload,
    build_measured_spread_payload,
    build_replay_outcome_payload,
    build_strategy_ladder_replay_evidence,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplaySummary,
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    StrategyLadderSharedReplayPayload,
    deterministic_payload_hash,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from portfolio_minimal.allocation_router.capital_viability import (
    PairMinNotionalAssessment,
    assess_pair_min_notional_viability,
)


_EXECUTED_STATES = {DecisionState.EXECUTED, DecisionState.REDUCED}
_SHARED_PARITY_KEYS = (
    "build14_shadow_activation_status",
    "build14_shadow_observation",
    "build14_shadow_report",
    "build14_shadow_applied_fields",
    "build14_shadow_adjustment_factors",
    "build14_shadow_reason_codes",
    "book_staleness_ms",
    "best_bid",
    "best_ask",
    "mid_price",
    "spread_source_status",
    "measured_spread_report",
    "measured_spread_bps",
    "replay_outcome_report",
)


@dataclass(frozen=True)
class StrategyLadderDetailedReplayPerformanceMetrics:
    shared_payload_build_seconds: float = 0.0
    engine_dataset_build_seconds: float = 0.0
    evaluate_replay_execution_seconds: float = 0.0
    replay_evidence_seconds: float = 0.0
    by_bucket_write_seconds: float = 0.0
    candidate_wrapper_write_seconds: float = 0.0
    cache_hits_book_state: int = 0
    cache_misses_book_state: int = 0
    cache_hits_ohlcv: int = 0
    cache_misses_ohlcv: int = 0


@dataclass(frozen=True)
class StrategyLadderDetailedReplayStageResult:
    detailed_replay_status: str
    candidate_artifacts: tuple[StrategyLadderDetailedReplayArtifact, ...]
    bucket_results_by_bucket: dict[int, tuple[StrategyLadderBucketReplayResult, ...]]
    bucket_dtr_records: dict[int, tuple[DTRRecord, ...]]
    performance_metrics: StrategyLadderDetailedReplayPerformanceMetrics = (
        StrategyLadderDetailedReplayPerformanceMetrics()
    )


def _coalesce_numeric(payload: dict[str, object], key: str, default: float) -> float:
    value = payload.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _measured_fee_rate_from_payload(payload: dict[str, object]) -> float | None:
    fee_bps = _coalesce_numeric(payload, "fee_bps", -1.0)
    if fee_bps < 0.0:
        return None
    fee_source = str(payload.get("fee_source_status") or "").strip().upper()
    if not fee_source.startswith("MEASURED_FROM_") and fee_source not in {
        "FEE_SOURCE_PROVEN",
        "FEE_SOURCE_CONFIGURED",
        "FEE_SOURCE_EXCHANGE_METADATA",
    }:
        return None
    return fee_bps / 10_000.0


def _fee_source_status_from_payload(payload: dict[str, object]) -> str:
    raw_status = str(payload.get("fee_source_status") or "FEE_SOURCE_NOT_PROVEN").strip()
    normalized = raw_status.upper()
    if normalized.startswith("MEASURED_FROM_VENUE_METADATA"):
        return "FEE_SOURCE_EXCHANGE_METADATA"
    if normalized == "MEASURED_FROM_VENUE_API_OVERRIDE":
        return "FEE_SOURCE_PROVEN"
    return raw_status or "FEE_SOURCE_NOT_PROVEN"


def _impact_source_from_book_status(book_status: str) -> str:
    if book_status == "BOOK_DEPTH20_AVAILABLE":
        return "IMPACT_SOURCE_DEPTH20_MODEL"
    if book_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        return "IMPACT_SOURCE_LIMITED_DEPTH_MODEL"
    if book_status == "BOOK_TOP_OF_BOOK_ONLY":
        return "IMPACT_SOURCE_TOP_OF_BOOK_PROXY"
    if book_status == "BOOK_DEPTH_MISSING":
        return "IMPACT_SOURCE_MISSING"
    return "IMPACT_SOURCE_NOT_PROVEN"


def _bucket_planned_notional(payload: dict[str, object], capital_bucket: int) -> float | None:
    allocation_fraction = payload.get("allocation_fraction")
    if allocation_fraction is not None:
        try:
            return round(float(allocation_fraction) * float(capital_bucket), 6)
        except (TypeError, ValueError):
            return None
    for key in ("planned_notional", "final_size", "candidate_size"):
        raw_value = payload.get(key)
        if raw_value is None:
            continue
        try:
            return round(min(float(raw_value), float(capital_bucket)), 6)
        except (TypeError, ValueError):
            continue
    return None


def _min_notional_assessment(
    *,
    payload: dict[str, object],
    capital_bucket: int,
    planned_notional: float | None,
) -> PairMinNotionalAssessment:
    raw_min_notional = payload.get("min_notional")
    min_notional = None
    if raw_min_notional is not None:
        try:
            min_notional = float(raw_min_notional)
        except (TypeError, ValueError):
            min_notional = None
    return assess_pair_min_notional_viability(
        pair=str(payload.get("pair") or ""),
        capital_bucket=capital_bucket,
        planned_notional=planned_notional,
        min_notional=min_notional,
        size_reduced=(float(payload.get("fill_ratio") or 1.0) < 1.0),
        fragmented=False,
    )


def _row_from_candidate(
    *,
    candidate: StrategyLadderCandidateEvent,
    capital_bucket: int,
    window_manifest: StrategyLadderRawWindowManifest | None,
) -> tuple[HistoricalReplayOpportunity, PairMinNotionalAssessment, float | None]:
    payload = dict(candidate.compatibility_payload or {})
    planned_notional = _bucket_planned_notional(payload, capital_bucket)
    min_notional_assessment = _min_notional_assessment(
        payload=payload,
        capital_bucket=capital_bucket,
        planned_notional=planned_notional,
    )
    hard_block_reasons = tuple(str(reason) for reason in payload.get("hard_block_reasons") or ())
    if min_notional_assessment.min_notional_viable is False:
        hard_block_reasons = tuple(
            dict.fromkeys(
                (*hard_block_reasons, *min_notional_assessment.min_notional_reason_codes)
            )
        )
    target_decision_state = payload.get("target_decision_state")
    if target_decision_state is None and planned_notional not in (None, 0.0) and not hard_block_reasons:
        target_decision_state = DecisionState.SELECTED.value
    book_status = (
        window_manifest.book_depth_source_status
        if window_manifest is not None
        else str(payload.get("book_depth_source_status") or "BOOK_DEPTH_NOT_PROVEN")
    )
    book_levels = (
        window_manifest.book_depth_levels_available
        if window_manifest is not None
        else payload.get("book_depth_levels")
    )
    measured_fee_rate = _measured_fee_rate_from_payload(payload)
    maker_fee_rate = payload.get("maker_fee_rate")
    taker_fee_rate = payload.get("taker_fee_rate")
    if measured_fee_rate is not None:
        if maker_fee_rate is None:
            maker_fee_rate = measured_fee_rate
        if taker_fee_rate is None:
            taker_fee_rate = measured_fee_rate
    record_payload = {
        "opportunity_id": payload.get("opportunity_id") or candidate.candidate_id,
        "timestamp_ms": candidate.resolved_timestamp_ms,
        "pair": candidate.pair,
        "engine_id": candidate.engine_id,
        "close_price": _coalesce_numeric(payload, "close_price", 0.0),
        "regime": payload.get("regime") or "",
        "raw_score": _coalesce_numeric(payload, "raw_score", 0.0),
        "penalized_score": payload.get("penalized_score"),
        "final_score": payload.get("final_score"),
        "expected_edge_bps": _coalesce_numeric(payload, "expected_edge_bps", 0.0),
        "spread_bps": _coalesce_numeric(payload, "spread_bps", 0.0),
        # Audit 2026-05-14 P3-A : propage le tier-aware spread provenance
        # depuis le compatibility_payload (qui le tient du feature_row data_factory).
        "spread_provenance": str(payload.get("spread_provenance") or ""),
        "slippage_bps": _coalesce_numeric(payload, "slippage_bps", 0.0),
        # Audit 2026-05-14 P3-B : propage le tier-aware slippage provenance.
        "slippage_provenance": str(payload.get("slippage_provenance") or ""),
        "latency_penalty_bps": _coalesce_numeric(payload, "latency_penalty_bps", 0.0),
        "fill_ratio": _coalesce_numeric(payload, "fill_ratio", 1.0),
        "side": str(payload.get("side") or "buy"),
        "tick_size": payload.get("tick_size"),
        "step_size": payload.get("step_size"),
        "maker_fee_rate": maker_fee_rate,
        "taker_fee_rate": taker_fee_rate,
        "min_notional": min_notional_assessment.min_notional,
        "mid_price": (
            _coalesce_numeric(payload, "mid_price", 0.0)
            or _coalesce_numeric(payload, "close_price", 0.0)
            or None
        ),
        "post_fill_mid_price": payload.get("post_fill_mid_price"),
        "adverse_selection_delay_s": payload.get("adverse_selection_delay_s"),
        "target_decision_state": target_decision_state,
        "production_decision_state": payload.get("production_decision_state"),
        "production_final_score": payload.get("production_final_score"),
        "production_expected_cost": payload.get("production_expected_cost"),
        "book_depth_levels": book_levels,
        "book_depth_source_status": book_status,
        "book_depth_snapshot_count": payload.get("book_depth_snapshot_count"),
        "book_depth_event_count": payload.get("book_depth_event_count"),
        "book_depth_missing_count": payload.get("book_depth_missing_count"),
        "book_depth_staleness_status": payload.get("book_depth_staleness_status")
        or book_status,
        "hard_block_reasons": hard_block_reasons,
        "ranking_position": int(payload.get("ranking_position") or 0),
        "candidate_size": planned_notional or 0.0,
        "final_size": planned_notional or 0.0,
        "tier": payload.get("tier") or "",
        "gross_return_bps": _coalesce_numeric(payload, "gross_return_bps", 0.0),
        "primary_reason": payload.get("primary_reason") or "",
        "feature_values": payload.get("feature_values") or {},
        "shared_core_match": bool(payload.get("shared_core_match", True)),
    }
    return (
        HistoricalReplayOpportunity.model_validate(record_payload),
        min_notional_assessment,
        planned_notional,
    )


def _executed_return_for_record(record: DTRRecord) -> tuple[float | None, str]:
    if record.decision_state not in _EXECUTED_STATES:
        return None, "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
    if record.realized_cost <= 0.0:
        return None, "EXECUTED_NET_RETURN_MISSING_REALIZED_COST"
    return round(record.gross_return - record.realized_cost, 6), "EXECUTED_NET_RETURN_NOT_PROVEN"


def _shared_payload_dir(output_dir: Path) -> Path:
    return output_dir / "shared"


def _shared_payload_path(output_dir: Path, candidate_id: str) -> Path:
    return _shared_payload_dir(output_dir) / f"{candidate_id}.json"


def _shared_payload_path_from_ref(ref: str) -> Path | None:
    if not ref:
        return None
    try:
        return Path(ref)
    except OSError:
        return None


def _strip_shared_parity_payload(
    parity_payload: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    shared: dict[str, object] = {}
    bucket_specific: dict[str, object] = {}
    for key, value in parity_payload.items():
        if key in _SHARED_PARITY_KEYS:
            shared[key] = value
        else:
            bucket_specific[key] = value
    return shared, bucket_specific


def _bucket_result_summary(
    result: StrategyLadderBucketReplayResult,
) -> StrategyLadderBucketReplaySummary:
    return StrategyLadderBucketReplaySummary(
        candidate_id=result.candidate_id,
        capital_bucket=result.capital_bucket,
        execution_state=result.execution_state,
        expected_ce_net=result.expected_ce_net,
        executed_only_net_return=result.executed_only_net_return,
        executed_only_net_return_status=result.executed_only_net_return_status,
        planned_notional=result.planned_notional,
        min_notional_viable=result.min_notional_viable,
        book_depth_source_status=result.book_depth_source_status,
        fill_realism_status=result.fill_realism_status,
        cost_parity_status=result.cost_parity_status,
        replay_outcome_status=result.replay_outcome_status,
        reason_codes=result.reason_codes,
        artifact_hash=result.artifact_hash,
    )


def load_strategy_ladder_shared_replay_payload(
    path: Path,
) -> StrategyLadderSharedReplayPayload:
    return StrategyLadderSharedReplayPayload.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )


def load_strategy_ladder_bucket_replay_result(
    path: Path,
    *,
    shared_payload_cache: dict[str, StrategyLadderSharedReplayPayload] | None = None,
) -> StrategyLadderBucketReplayResult:
    result = StrategyLadderBucketReplayResult.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )
    shared_ref = result.shared_payload_ref
    shared_path = _shared_payload_path_from_ref(shared_ref)
    if shared_path is None or not shared_path.is_file():
        return result
    cache = shared_payload_cache if shared_payload_cache is not None else {}
    cache_key = str(shared_path.resolve())
    shared_payload = cache.get(cache_key)
    if shared_payload is None:
        shared_payload = load_strategy_ladder_shared_replay_payload(shared_path)
        cache[cache_key] = shared_payload
    merged_parity = dict(shared_payload.shared_parity_payload)
    merged_parity.update(result.parity_payload)
    return result.model_copy(update={"parity_payload": merged_parity})


def load_strategy_ladder_detailed_replay_artifact(
    path: Path,
    *,
    shared_payload_cache: dict[str, StrategyLadderSharedReplayPayload] | None = None,
) -> StrategyLadderDetailedReplayArtifact:
    artifact = StrategyLadderDetailedReplayArtifact.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )
    hydrated_results: list[StrategyLadderBucketReplayResult] = []
    if artifact.bucket_results:
        for result in artifact.bucket_results:
            shared_ref = result.shared_payload_ref or artifact.shared_payload_ref
            if not shared_ref:
                hydrated_results.append(result)
                continue
            shared_path = _shared_payload_path_from_ref(shared_ref)
            if shared_path is None or not shared_path.is_file():
                hydrated_results.append(result)
                continue
            cache = shared_payload_cache if shared_payload_cache is not None else {}
            cache_key = str(shared_path.resolve())
            shared_payload = cache.get(cache_key)
            if shared_payload is None:
                shared_payload = load_strategy_ladder_shared_replay_payload(shared_path)
                cache[cache_key] = shared_payload
            merged_parity = dict(shared_payload.shared_parity_payload)
            merged_parity.update(result.parity_payload)
            hydrated_results.append(result.model_copy(update={"parity_payload": merged_parity}))
    elif artifact.bucket_result_refs:
        for ref in artifact.bucket_result_refs:
            hydrated_results.append(
                load_strategy_ladder_bucket_replay_result(
                    Path(ref),
                    shared_payload_cache=shared_payload_cache,
                )
            )
    if not hydrated_results:
        return artifact
    return artifact.model_copy(update={"bucket_results": tuple(hydrated_results)})


def run_strategy_ladder_detailed_replay(
    output_dir: Path,
    *,
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
    raw_window_manifests: tuple[StrategyLadderRawWindowManifest, ...],
    capital_buckets: tuple[int, ...],
    execution_runtime_projection_path: Path | None = None,
) -> StrategyLadderDetailedReplayStageResult:
    """Run candidate-window replay and persist deterministic detailed artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    window_by_candidate = {
        manifest.candidate_id: manifest for manifest in raw_window_manifests
    }
    candidate_artifacts: list[StrategyLadderDetailedReplayArtifact] = []
    bucket_results_by_bucket: dict[int, list[StrategyLadderBucketReplayResult]] = {
        bucket: [] for bucket in capital_buckets
    }
    bucket_dtr_records: dict[int, list[DTRRecord]] = {
        bucket: [] for bucket in capital_buckets
    }
    overall_partial = False
    if not candidate_events:
        return StrategyLadderDetailedReplayStageResult(
            detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
            candidate_artifacts=(),
            bucket_results_by_bucket={bucket: () for bucket in capital_buckets},
            bucket_dtr_records={bucket: () for bucket in capital_buckets},
            performance_metrics=StrategyLadderDetailedReplayPerformanceMetrics(),
        )

    shared_payload_root = _shared_payload_dir(output_dir)
    shared_payload_root.mkdir(parents=True, exist_ok=True)
    shared_payload_build_seconds = 0.0
    engine_dataset_build_seconds = 0.0
    evaluate_replay_execution_seconds = 0.0
    replay_evidence_seconds = 0.0
    by_bucket_write_seconds = 0.0
    candidate_wrapper_write_seconds = 0.0
    cache_hits_book_state = 0
    cache_misses_book_state = 0
    cache_hits_ohlcv = 0
    cache_misses_ohlcv = 0

    for candidate in candidate_events:
        window_manifest = window_by_candidate.get(candidate.candidate_id)
        bucket_results: list[StrategyLadderBucketReplayResult] = []
        bucket_refs: list[str] = []
        evidence_cache = StrategyLadderReplayEvidenceCache()
        candidate_payload = dict(candidate.compatibility_payload or {})
        shared_payload_ref = str(
            _shared_payload_path(output_dir, candidate.candidate_id).resolve()
        )
        shared_payload_started = perf_counter()
        shared_measured_spread = build_measured_spread_payload(
            window_manifest=window_manifest,
            decision_timestamp_ms=candidate.resolved_timestamp_ms,
            evidence_cache=evidence_cache,
        )
        shared_replay_outcome = build_replay_outcome_payload(
            candidate=candidate,
            window_manifest=window_manifest,
            decision_timestamp_ms=candidate.resolved_timestamp_ms,
            evidence_cache=evidence_cache,
        )
        shared_parity_payload = {
            key: candidate_payload[key]
            for key in _SHARED_PARITY_KEYS
            if key in candidate_payload
        }
        shared_parity_payload["measured_spread_report"] = shared_measured_spread
        shared_parity_payload["replay_outcome_report"] = shared_replay_outcome
        shared_parity_payload["book_staleness_ms"] = shared_measured_spread.get(
            "staleness_ms"
        )
        shared_parity_payload["best_bid"] = shared_measured_spread.get("best_bid")
        shared_parity_payload["best_ask"] = shared_measured_spread.get("best_ask")
        shared_parity_payload["mid_price"] = shared_measured_spread.get("mid_price")
        shared_parity_payload["spread_source_status"] = shared_measured_spread.get(
            "status"
        )
        if shared_measured_spread.get("spread_bps") is not None:
            shared_parity_payload["measured_spread_bps"] = shared_measured_spread.get(
                "spread_bps"
            )
        shared_payload = StrategyLadderSharedReplayPayload(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            strategy_id=candidate.strategy_id,
            timestamp_ms=candidate.resolved_timestamp_ms,
            window_start_ms=(
                window_manifest.window_start_ms if window_manifest is not None else None
            ),
            window_end_ms=(
                window_manifest.window_end_ms if window_manifest is not None else None
            ),
            raw_trade_path=(
                window_manifest.raw_trade_path if window_manifest is not None else ""
            )
            or "",
            raw_book_path=(
                window_manifest.raw_book_path if window_manifest is not None else ""
            )
            or "",
            raw_book_delta_path=(
                window_manifest.raw_book_delta_path if window_manifest is not None else ""
            )
            or "",
            raw_ohlcv_path=(
                window_manifest.raw_ohlcv_path if window_manifest is not None else ""
            )
            or "",
            raw_metadata_path=(
                window_manifest.raw_metadata_path if window_manifest is not None else ""
            )
            or "",
            raw_sources_used=(
                window_manifest.raw_sources_used if window_manifest is not None else ()
            ),
            book_depth_levels_available=(
                window_manifest.book_depth_levels_available
                if window_manifest is not None
                else None
            ),
            book_depth_source_status=(
                window_manifest.book_depth_source_status
                if window_manifest is not None
                else "BOOK_DEPTH_NOT_PROVEN"
            ),
            source_coverage_status=(
                window_manifest.source_coverage_status
                if window_manifest is not None
                else "SOURCE_COVERAGE_NOT_PROVEN"
            ),
            shared_parity_payload=shared_parity_payload,
            input_data_hash=candidate.input_data_hash,
            method_version_hash=candidate.method_version_hash,
        )
        shared_payload = shared_payload.model_copy(
            update={
                "artifact_hash": deterministic_payload_hash(
                    shared_payload.model_dump(mode="json")
                )
            }
        )
        atomic_write_json(
            Path(shared_payload_ref),
            shared_payload.model_dump(mode="json"),
        )
        shared_payload_build_seconds += perf_counter() - shared_payload_started
        for capital_bucket in capital_buckets:
            dataset_started = perf_counter()
            row, min_notional_assessment, planned_notional = _row_from_candidate(
                candidate=candidate,
                capital_bucket=capital_bucket,
                window_manifest=window_manifest,
            )
            dataset = HistoricalReplayDataset.from_records(
                dataset_id=f"{candidate.candidate_id}-{capital_bucket}",
                source_path=(
                    window_manifest.raw_trade_path
                    if window_manifest is not None and window_manifest.raw_trade_path
                    else str(Path(candidate.feature_refs[0]).resolve()) if candidate.feature_refs else candidate.candidate_id
                ),
                records=(row,),
                source="strategy_ladder_detailed_replay",
            )
            engine_dataset_build_seconds += perf_counter() - dataset_started
            evaluate_started = perf_counter()
            execution_evaluation = evaluate_replay_execution(
                ReplayExecutionEvaluationRequest(
                    dataset=dataset,
                    execution_label="strategy_ladder_detailed_replay",
                    execution_runtime_projection_path=(
                        str(execution_runtime_projection_path)
                        if execution_runtime_projection_path is not None
                        else None
                    ),
                )
            )
            evaluate_replay_execution_seconds += perf_counter() - evaluate_started
            dtr_record = execution_evaluation.dtr_records[0]
            parity_payload = execution_evaluation.parity_diagnostics_payload
            executed_only_net_return, executed_return_status = _executed_return_for_record(
                dtr_record
            )
            if window_manifest is not None and window_manifest.window_extraction_status != "RAW_WINDOW_READY":
                overall_partial = True
            book_status = (
                window_manifest.book_depth_source_status
                if window_manifest is not None
                else str(parity_payload.get("book_depth_source_status") or "BOOK_DEPTH_NOT_PROVEN")
            )
            execution_state = dtr_record.decision_state.value
            replay_evidence_started = perf_counter()
            replay_evidence = build_strategy_ladder_replay_evidence(
                candidate=candidate,
                window_manifest=window_manifest,
                planned_notional=planned_notional,
                execution_state=execution_state,
                evidence_cache=evidence_cache,
            )
            cost_governance = build_measured_cost_governance_payload(
                measured_spread=shared_measured_spread,
                measured_slippage=replay_evidence.measured_slippage,
                fee_bps=_coalesce_numeric(candidate_payload, "fee_bps", 0.0),
                fee_source_status=_fee_source_status_from_payload(candidate_payload),
                latency_penalty_bps=_coalesce_numeric(
                    candidate_payload,
                    "latency_penalty_bps",
                    0.0,
                ),
                latency_source_status=str(
                    candidate_payload.get("latency_source_status")
                    or candidate_payload.get("latency_provenance")
                    or "STATIC_CONSERVATIVE_VENUE_MODEL"
                ),
            )
            parity_payload["measured_slippage_report"] = replay_evidence.measured_slippage
            parity_payload["adverse_selection_report"] = replay_evidence.adverse_selection
            parity_payload["fill_realism_report"] = replay_evidence.fill_realism
            parity_payload["cost_source_used_for_break_even"] = cost_governance.get(
                "cost_source_used_for_break_even"
            )
            parity_payload["cost_source_used_for_expected_ce_net"] = cost_governance.get(
                "cost_source_used_for_expected_ce_net"
            )
            parity_payload["expected_cost_truth_status"] = cost_governance.get(
                "expected_cost_truth_status"
            )
            parity_payload["expected_cost_block_reason"] = cost_governance.get(
                "expected_cost_block_reason"
            )
            parity_payload["book_staleness_ms"] = cost_governance.get("book_staleness_ms")
            parity_payload["spread_source_status"] = cost_governance.get(
                "spread_source_status"
            )
            parity_payload["slippage_source_status"] = cost_governance.get(
                "slippage_source_status"
            )
            parity_payload["best_bid"] = cost_governance.get("best_bid")
            parity_payload["best_ask"] = cost_governance.get("best_ask")
            parity_payload["mid_price"] = cost_governance.get("mid_price")
            parity_payload["depth_fill_ratio"] = cost_governance.get("depth_fill_ratio")
            parity_payload["partial_fill_status"] = cost_governance.get(
                "partial_fill_status"
            )
            parity_payload["impact_source_status"] = cost_governance.get(
                "impact_source_status"
            )
            parity_payload["fill_realism_status"] = cost_governance.get(
                "fill_realism_status"
            )
            if replay_evidence.measured_slippage.get("walk_cost_bps") is not None:
                parity_payload["measured_slippage_bps"] = replay_evidence.measured_slippage.get(
                    "walk_cost_bps"
                )
            if replay_evidence.adverse_selection.get("adverse_selection_bps") is not None:
                parity_payload["adverse_selection_bps"] = replay_evidence.adverse_selection.get(
                    "adverse_selection_bps"
                )
            replay_evidence_seconds += perf_counter() - replay_evidence_started
            full_parity_payload = dict(shared_parity_payload)
            full_parity_payload.update(parity_payload)
            _shared_overlay, bucket_specific_parity_payload = _strip_shared_parity_payload(
                full_parity_payload
            )
            persisted_result = StrategyLadderBucketReplayResult(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                strategy_id=candidate.strategy_id,
                capital_bucket=capital_bucket,
                timestamp_ms=candidate.resolved_timestamp_ms,
                execution_state=execution_state,
                executed_notional=(
                    planned_notional
                    if dtr_record.decision_state == DecisionState.EXECUTED
                    else None
                ),
                reduced_notional=(
                    dtr_record.final_size
                    if dtr_record.decision_state == DecisionState.REDUCED
                    else None
                ),
                no_fill_flag=dtr_record.decision_state == DecisionState.PHANTOM,
                partial_fill_flag=dtr_record.decision_state == DecisionState.REDUCED,
                expected_ce_net=dtr_record.ce_expected,
                executed_only_net_return=executed_only_net_return,
                executed_only_net_return_status=executed_return_status,
                fee_source_status=_fee_source_status_from_payload(
                    candidate.compatibility_payload or {}
                ),
                impact_source_status=str(
                    parity_payload.get("impact_source_status")
                    or (candidate.compatibility_payload or {}).get("impact_source_status")
                    or _impact_source_from_book_status(book_status)
                ),
                fill_realism_status=str(
                    parity_payload.get("fill_realism_status")
                    or (candidate.compatibility_payload or {}).get("fill_realism_status")
                    or replay_evidence.fill_realism.get("status")
                    or "FILL_REALISM_NOT_PROVEN"
                ),
                cost_parity_status=str(
                    (candidate.compatibility_payload or {}).get("cost_parity_status")
                    or parity_payload.get("cost_parity_status")
                    or "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
                ),
                book_depth_source_status=book_status,
                impact_depth_readiness_status=str(
                    parity_payload.get("impact_depth_readiness_status")
                    or book_status
                ),
                replay_outcome_status=str(
                    replay_evidence.replay_outcome.get("status")
                    or "REPLAY_OUTCOME_NOT_PROVEN"
                ),
                entry_reference_status=str(
                    replay_evidence.replay_outcome.get("entry_reference_status")
                    or "ENTRY_REFERENCE_NOT_AVAILABLE"
                ),
                mfe_mae_status=str(
                    replay_evidence.replay_outcome.get("mfe_mae_status")
                    or "MFE_MAE_NOT_AVAILABLE"
                ),
                holding_time_ms=(
                    int(replay_evidence.replay_outcome["holding_time_ms"])
                    if replay_evidence.replay_outcome.get("holding_time_ms") is not None
                    else None
                ),
                forward_return_h1=(
                    float(replay_evidence.replay_outcome["forward_return_h1"])
                    if replay_evidence.replay_outcome.get("forward_return_h1") is not None
                    else None
                ),
                forward_return_h5=(
                    float(replay_evidence.replay_outcome["forward_return_h5"])
                    if replay_evidence.replay_outcome.get("forward_return_h5") is not None
                    else None
                ),
                forward_return_h10=(
                    float(replay_evidence.replay_outcome["forward_return_h10"])
                    if replay_evidence.replay_outcome.get("forward_return_h10") is not None
                    else None
                ),
                mfe_bps=(
                    float(replay_evidence.replay_outcome["mfe_bps"])
                    if replay_evidence.replay_outcome.get("mfe_bps") is not None
                    else None
                ),
                mae_bps=(
                    float(replay_evidence.replay_outcome["mae_bps"])
                    if replay_evidence.replay_outcome.get("mae_bps") is not None
                    else None
                ),
                entry_ref=(
                    dict(replay_evidence.replay_outcome.get("entry_ref") or {})
                ),
                exit_ref=(
                    dict(replay_evidence.replay_outcome.get("exit_ref") or {})
                ),
                invalidation_ref=(
                    dict(replay_evidence.replay_outcome.get("invalidation_ref") or {})
                ),
                reason_codes=tuple(
                    dict.fromkeys(
                        (
                            *min_notional_assessment.min_notional_reason_codes,
                            *(dtr_record.cause_chain or ()),
                            *tuple(
                                str(code)
                                for code in (
                                    candidate_payload.get("build14_shadow_reason_codes") or ()
                                )
                            ),
                        )
                    )
                ),
                planned_notional=planned_notional,
                min_notional=min_notional_assessment.min_notional,
                min_notional_viable=min_notional_assessment.min_notional_viable,
                min_notional_reason_codes=min_notional_assessment.min_notional_reason_codes,
                size_reduction_rate=(
                    None
                    if planned_notional in (None, 0.0)
                    else round(
                        max(planned_notional - dtr_record.final_size, 0.0) / planned_notional,
                        6,
                    )
                ),
                input_data_hash=candidate.input_data_hash,
                method_version_hash=candidate.method_version_hash,
                dtr_record=dtr_record.model_dump(mode="json"),
                parity_payload=bucket_specific_parity_payload,
                shared_payload_ref=shared_payload_ref,
            )
            persisted_result = persisted_result.model_copy(
                update={
                    "artifact_hash": deterministic_payload_hash(
                        persisted_result.model_dump(mode="json")
                    )
                }
            )
            result = persisted_result.model_copy(
                update={"parity_payload": full_parity_payload}
            )
            bucket_dir = output_dir / "by_bucket" / str(capital_bucket)
            bucket_dir.mkdir(parents=True, exist_ok=True)
            bucket_path = bucket_dir / f"{candidate.candidate_id}.json"
            write_started = perf_counter()
            atomic_write_json(bucket_path, persisted_result.model_dump(mode="json"))
            by_bucket_write_seconds += perf_counter() - write_started
            bucket_results.append(result)
            bucket_refs.append(str(bucket_path.resolve()))
            bucket_results_by_bucket[capital_bucket].append(result)
            bucket_dtr_records[capital_bucket].append(dtr_record)

        cache_metrics = evidence_cache.metrics_snapshot()
        cache_hits_book_state += cache_metrics.cache_hits_book_state
        cache_misses_book_state += cache_metrics.cache_misses_book_state
        cache_hits_ohlcv += cache_metrics.cache_hits_ohlcv
        cache_misses_ohlcv += cache_metrics.cache_misses_ohlcv
        candidate_status = (
            "DETAILED_REPLAY_READY"
            if all(
                item.book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
                for item in bucket_results
            )
            else "DETAILED_REPLAY_PARTIAL"
        )
        artifact = StrategyLadderDetailedReplayArtifact(
            candidate_id=candidate.candidate_id,
            pair=candidate.pair,
            engine_id=candidate.engine_id,
            strategy_id=candidate.strategy_id,
            timestamp_ms=candidate.resolved_timestamp_ms,
            detailed_replay_status=candidate_status,
            bucket_results=(),
            bucket_result_summary=tuple(
                _bucket_result_summary(item) for item in bucket_results
            ),
            bucket_result_refs=tuple(bucket_refs),
            shared_payload_ref=shared_payload_ref,
            input_data_hash=candidate.input_data_hash,
            method_version_hash=candidate.method_version_hash,
        )
        artifact = artifact.model_copy(
            update={"artifact_hash": deterministic_payload_hash(artifact.model_dump(mode="json"))}
        )
        candidate_wrapper_started = perf_counter()
        atomic_write_json(
            output_dir / f"{candidate.candidate_id}.json",
            artifact.model_dump(mode="json"),
        )
        candidate_wrapper_write_seconds += perf_counter() - candidate_wrapper_started
        candidate_artifacts.append(artifact)

    overall_status = "DETAILED_REPLAY_READY"
    if not candidate_artifacts:
        overall_status = "DETAILED_REPLAY_NOT_PROVEN"
    elif overall_partial or any(
        artifact.detailed_replay_status != "DETAILED_REPLAY_READY"
        for artifact in candidate_artifacts
    ):
        overall_status = "DETAILED_REPLAY_PARTIAL"
    return StrategyLadderDetailedReplayStageResult(
        detailed_replay_status=overall_status,
        candidate_artifacts=tuple(candidate_artifacts),
        bucket_results_by_bucket={
            bucket: tuple(items)
            for bucket, items in bucket_results_by_bucket.items()
        },
        bucket_dtr_records={
            bucket: tuple(items)
            for bucket, items in bucket_dtr_records.items()
        },
        performance_metrics=StrategyLadderDetailedReplayPerformanceMetrics(
            shared_payload_build_seconds=round(shared_payload_build_seconds, 6),
            engine_dataset_build_seconds=round(engine_dataset_build_seconds, 6),
            evaluate_replay_execution_seconds=round(
                evaluate_replay_execution_seconds,
                6,
            ),
            replay_evidence_seconds=round(replay_evidence_seconds, 6),
            by_bucket_write_seconds=round(by_bucket_write_seconds, 6),
            candidate_wrapper_write_seconds=round(
                candidate_wrapper_write_seconds,
                6,
            ),
            cache_hits_book_state=cache_hits_book_state,
            cache_misses_book_state=cache_misses_book_state,
            cache_hits_ohlcv=cache_hits_ohlcv,
            cache_misses_ohlcv=cache_misses_ohlcv,
        ),
    )


__all__ = [
    "StrategyLadderDetailedReplayPerformanceMetrics",
    "StrategyLadderDetailedReplayStageResult",
    "load_strategy_ladder_bucket_replay_result",
    "load_strategy_ladder_detailed_replay_artifact",
    "load_strategy_ladder_shared_replay_payload",
    "run_strategy_ladder_detailed_replay",
]
