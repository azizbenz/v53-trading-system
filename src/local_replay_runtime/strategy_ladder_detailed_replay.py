"""Detailed candidate-window replay for the canonical Strategy Ladder runner."""

from __future__ import annotations

from dataclasses import dataclass
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
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    deterministic_payload_hash,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from portfolio_minimal.allocation_router.capital_viability import (
    PairMinNotionalAssessment,
    assess_pair_min_notional_viability,
)


_EXECUTED_STATES = {DecisionState.EXECUTED, DecisionState.REDUCED}


@dataclass(frozen=True)
class StrategyLadderDetailedReplayStageResult:
    detailed_replay_status: str
    candidate_artifacts: tuple[StrategyLadderDetailedReplayArtifact, ...]
    bucket_results_by_bucket: dict[int, tuple[StrategyLadderBucketReplayResult, ...]]
    bucket_dtr_records: dict[int, tuple[DTRRecord, ...]]


def _coalesce_numeric(payload: dict[str, object], key: str, default: float) -> float:
    value = payload.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        "maker_fee_rate": payload.get("maker_fee_rate"),
        "taker_fee_rate": payload.get("taker_fee_rate"),
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
        )

    for candidate in candidate_events:
        window_manifest = window_by_candidate.get(candidate.candidate_id)
        bucket_results: list[StrategyLadderBucketReplayResult] = []
        bucket_refs: list[str] = []
        for capital_bucket in capital_buckets:
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
            dtr_record = execution_evaluation.dtr_records[0]
            parity_payload = execution_evaluation.parity_diagnostics_payload
            build14_payload = candidate.compatibility_payload or {}
            for key in (
                "build14_shadow_activation_status",
                "build14_shadow_observation",
                "build14_shadow_report",
                "build14_shadow_applied_fields",
                "build14_shadow_adjustment_factors",
                "build14_shadow_reason_codes",
            ):
                if key in build14_payload:
                    parity_payload[key] = build14_payload[key]
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
            result = StrategyLadderBucketReplayResult(
                candidate_id=candidate.candidate_id,
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                strategy_id=candidate.strategy_id,
                capital_bucket=capital_bucket,
                timestamp_ms=candidate.resolved_timestamp_ms,
                execution_state=dtr_record.decision_state.value,
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
                fee_source_status=str(
                    (candidate.compatibility_payload or {}).get("fee_source_status")
                    or "FEE_SOURCE_NOT_PROVEN"
                ),
                impact_source_status=str(
                    (candidate.compatibility_payload or {}).get("impact_source_status")
                    or parity_payload.get("impact_source_status")
                    or _impact_source_from_book_status(book_status)
                ),
                fill_realism_status=str(
                    (candidate.compatibility_payload or {}).get("fill_realism_status")
                    or parity_payload.get("fill_realism_status")
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
                reason_codes=tuple(
                    dict.fromkeys(
                        (
                            *min_notional_assessment.min_notional_reason_codes,
                            *(dtr_record.cause_chain or ()),
                            *tuple(
                                str(code)
                                for code in (
                                    build14_payload.get("build14_shadow_reason_codes") or ()
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
                parity_payload=parity_payload,
            )
            result = result.model_copy(
                update={"artifact_hash": deterministic_payload_hash(result.model_dump(mode="json"))}
            )
            bucket_dir = output_dir / "by_bucket" / str(capital_bucket)
            bucket_dir.mkdir(parents=True, exist_ok=True)
            bucket_path = bucket_dir / f"{candidate.candidate_id}.json"
            atomic_write_json(bucket_path, result.model_dump(mode="json"))
            bucket_results.append(result)
            bucket_refs.append(str(bucket_path.resolve()))
            bucket_results_by_bucket[capital_bucket].append(result)
            bucket_dtr_records[capital_bucket].append(dtr_record)

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
            bucket_results=tuple(bucket_results),
            bucket_result_refs=tuple(bucket_refs),
            input_data_hash=candidate.input_data_hash,
            method_version_hash=candidate.method_version_hash,
        )
        artifact = artifact.model_copy(
            update={"artifact_hash": deterministic_payload_hash(artifact.model_dump(mode="json"))}
        )
        atomic_write_json(
            output_dir / f"{candidate.candidate_id}.json",
            artifact.model_dump(mode="json"),
        )
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
    )


__all__ = [
    "StrategyLadderDetailedReplayStageResult",
    "run_strategy_ladder_detailed_replay",
]
