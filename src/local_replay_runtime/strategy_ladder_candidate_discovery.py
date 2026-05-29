"""Fast candidate discovery and canonical export for the Strategy Ladder runner."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_count_semantics import (
    summarize_candidate_count_semantics,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderCandidateSummary,
    StrategyLadderFeatureRow,
    deterministic_payload_hash,
)
from local_replay_runtime.tabular_artifacts import write_tabular_mirror


_TEMPORAL_STRATIFIED_CANDIDATE_MODES = {
    "TEMPORAL_STRATIFIED",
    "TEMPORAL_STRATIFIED_SAMPLE_BUDGET",
}


@dataclass(frozen=True)
class StrategyLadderCandidateBudgetResult:
    candidates: tuple[StrategyLadderCandidateEvent, ...]
    limited: bool
    limit_reason: str
    cap_status: str
    temporal_bucket_granularity: str = ""
    temporal_bucket_count_available: int = 0
    temporal_bucket_count_selected: int = 0
    temporal_bucket_coverage_ratio: float | None = None


def _candidate_id(
    *,
    run_id: str,
    timestamp_ms: int,
    pair: str,
    timeframe: str,
    engine_id: str,
    strategy_id: str,
) -> str:
    payload = f"{run_id}|{timestamp_ms}|{pair}|{timeframe}|{engine_id}|{strategy_id}"
    return deterministic_payload_hash(payload)[:24]


def _compatibility_payload(
    *,
    row: StrategyLadderFeatureRow,
    engine_id: str,
    strategy_id: str,
    opportunity_id: str,
) -> dict[str, object]:
    return {
        "opportunity_id": row.source_record_id or opportunity_id,
        "timestamp_ms": row.resolved_timestamp_ms,
        "pair": row.pair,
        "engine_id": engine_id,
        "close_price": row.close_price,
        "regime": row.regime,
        "raw_score": row.raw_score,
        "penalized_score": row.penalized_score,
        "final_score": row.final_score,
        "expected_edge_bps": row.expected_edge_bps,
        "expected_edge_provenance": row.expected_edge_provenance,
        "economic_provenance": row.economic_provenance,
        "economic_measurement_warnings": row.economic_measurement_warnings,
        "spread_bps": row.spread_bps,
        # Audit 2026-05-14 P3-A : tier-aware spread provenance pour
        # mapping downstream spread_model_source (CANONICAL_BOOK_* vs
        # MEASURED_STALE_AUDIT_ONLY vs REPLAY_PROXY).
        "spread_provenance": row.spread_provenance,
        "slippage_bps": row.slippage_bps,
        # Audit 2026-05-14 P3-B : tier-aware slippage provenance pour
        # mapping downstream slippage_model_source (CANONICAL_KYLE_LAMBDA_METER
        # vs REPLAY_PROXY).
        "slippage_provenance": row.slippage_provenance,
        "latency_penalty_bps": row.latency_penalty_bps,
        "fill_ratio": row.fill_ratio,
        "side": row.side,
        "tick_size": row.tick_size,
        "step_size": row.step_size,
        "maker_fee_rate": row.maker_fee_rate,
        "taker_fee_rate": row.taker_fee_rate,
        "target_decision_state": row.target_decision_state,
        "production_decision_state": row.production_decision_state,
        "production_final_score": row.production_final_score,
        "production_expected_cost": row.production_expected_cost,
        "book_depth_levels": row.book_depth_levels,
        "book_depth_source_status": row.book_depth_source_status,
        "book_depth_snapshot_count": row.book_depth_snapshot_count,
        "book_depth_event_count": row.book_depth_event_count,
        "book_depth_missing_count": row.book_depth_missing_count,
        "book_depth_staleness_status": row.book_depth_staleness_status,
        "hard_block_reasons": row.hard_block_reasons,
        "ranking_position": row.ranking_position,
        "candidate_size": row.candidate_size,
        "final_size": row.final_size,
        "tier": row.tier,
        "gross_return_bps": row.gross_return_bps,
        "primary_reason": row.primary_reason,
        "feature_values": row.feature_values,
        "shared_core_match": row.shared_core_match,
        "strategy_id": strategy_id,
        "strategy_role": row.strategy_role,
        "planned_notional": row.planned_notional,
        "allocation_fraction": row.allocation_fraction,
        "min_notional": row.min_notional,
        "input_data_hash": row.input_data_hash,
        "method_version_hash": row.method_version_hash,
        "source_ref": row.source_ref,
        "available_at_timestamp_ms": row.available_at_timestamp_ms,
        "feature_truth_boundary_status": row.feature_truth_boundary_status,
        "feature_usage_policy": row.feature_usage_policy,
        "cost_feature_truth_status": row.cost_feature_truth_status,
        "feature_sources_used": row.feature_sources_used,
        "trade_feature_status": row.trade_feature_status,
        "kline_feature_status": row.kline_feature_status,
        "orderbook_feature_status": row.orderbook_feature_status,
        "candidate_data_source_label": row.candidate_data_source_label,
        "compatibility_notes": (
            "COMPAT_FEATURE_DISCOVERY",
            "NOT_LIVE_ENGINE_PARITY",
            *row.compatibility_notes,
        ),
    }


def discover_strategy_ladder_candidates(
    *,
    run_id: str,
    rows: tuple[StrategyLadderFeatureRow, ...],
) -> tuple[str, tuple[StrategyLadderCandidateEvent, ...]]:
    """Emit canonical Strategy Ladder candidate events from feature-store rows."""

    if not rows:
        return "CANDIDATE_DISCOVERY_EMPTY", ()
    candidates: list[StrategyLadderCandidateEvent] = []
    for row in rows:
        for engine_id in row.resolved_engine_ids:
            strategy_id = row.resolved_strategy_id(engine_id)
            opportunity_id = _candidate_id(
                run_id=run_id,
                timestamp_ms=row.resolved_timestamp_ms,
                pair=row.pair,
                timeframe=row.timeframe,
                engine_id=engine_id,
                strategy_id=strategy_id,
            )
            preliminary_score = (
                row.final_score
                if row.final_score is not None
                else row.penalized_score
            )
            candidates.append(
                StrategyLadderCandidateEvent(
                    run_id=run_id,
                    candidate_id=opportunity_id,
                    timestamp_ns=row.timestamp_ns,
                    timestamp_ms=row.timestamp_ms,
                    pair=row.pair,
                    timeframe=row.timeframe,
                    engine_id=engine_id,
                    strategy_id=strategy_id,
                    candidate_source="COMPAT_FEATURE_DISCOVERY",
                    feature_refs=(row.source_ref,),
                    preliminary_score=preliminary_score,
                    preliminary_reason_codes=(
                        "COMPAT_FEATURE_DISCOVERY",
                        "NOT_LIVE_ENGINE_PARITY",
                        row.feature_truth_boundary_status,
                        row.cost_feature_truth_status,
                        *(("HARD_BLOCK_REASONS_PRESENT",) if row.hard_block_reasons else ()),
                    ),
                    feature_version=row.feature_version,
                    input_data_hash=row.input_data_hash,
                    method_version_hash=row.method_version_hash,
                    feature_sources_used=row.feature_sources_used,
                    trade_feature_status=row.trade_feature_status,
                    kline_feature_status=row.kline_feature_status,
                    orderbook_feature_status=row.orderbook_feature_status,
                    candidate_data_source_label=row.candidate_data_source_label,
                    compatibility_payload=_compatibility_payload(
                        row=row,
                        engine_id=engine_id,
                        strategy_id=strategy_id,
                        opportunity_id=opportunity_id,
                    ),
                )
            )
    ordered = tuple(
        sorted(
            candidates,
            key=lambda row: (
                row.resolved_timestamp_ms,
                row.pair,
                row.engine_id,
                row.strategy_id,
            ),
        )
    )
    return "CANDIDATE_DISCOVERY_READY", ordered


def cap_strategy_ladder_candidates(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
    *,
    sample_cap_per_engine: int,
) -> tuple[tuple[StrategyLadderCandidateEvent, ...], bool]:
    if sample_cap_per_engine <= 0:
        return candidates, False
    capped: list[StrategyLadderCandidateEvent] = []
    counts_by_engine: dict[str, int] = {}
    limited = False
    for event in candidates:
        key = event.engine_id
        current = counts_by_engine.get(key, 0)
        if current >= sample_cap_per_engine:
            limited = True
            continue
        counts_by_engine[key] = current + 1
        capped.append(event)
    return tuple(capped), limited


def _is_temporal_stratified_candidate_mode(candidate_discovery_mode: str) -> bool:
    return candidate_discovery_mode.strip().upper() in _TEMPORAL_STRATIFIED_CANDIDATE_MODES


def _temporal_bucket_key(event: StrategyLadderCandidateEvent) -> str:
    return datetime.fromtimestamp(event.resolved_timestamp_ms / 1000.0, tz=UTC).date().isoformat()


def _cap_strategy_ladder_candidates_temporal_stratified(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
    *,
    sample_cap_per_engine: int,
) -> StrategyLadderCandidateBudgetResult:
    if sample_cap_per_engine <= 0:
        return StrategyLadderCandidateBudgetResult(
            candidates=candidates,
            limited=False,
            limit_reason="",
            cap_status="CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN",
        )

    candidate_ids_by_pair_engine_bucket: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    available_bucket_keys: set[str] = set()
    for event in candidates:
        bucket_key = _temporal_bucket_key(event)
        available_bucket_keys.add(bucket_key)
        pair_engine_key = f"{event.pair}|{event.engine_id}"
        candidate_ids_by_pair_engine_bucket[pair_engine_key][bucket_key].append(
            event.candidate_id
        )

    selected_ids: set[str] = set()
    for buckets_by_key in candidate_ids_by_pair_engine_bucket.values():
        ordered_bucket_keys = sorted(buckets_by_key)
        if not ordered_bucket_keys:
            continue
        base_quota = sample_cap_per_engine // len(ordered_bucket_keys)
        remainder = sample_cap_per_engine % len(ordered_bucket_keys)
        leftovers: dict[str, list[str]] = {}
        selected_count = 0
        for index, bucket_key in enumerate(ordered_bucket_keys):
            quota = base_quota + (1 if index < remainder else 0)
            bucket_candidate_ids = buckets_by_key[bucket_key]
            take = min(quota, len(bucket_candidate_ids))
            selected_ids.update(bucket_candidate_ids[:take])
            leftovers[bucket_key] = bucket_candidate_ids[take:]
            selected_count += take
        remaining_budget = sample_cap_per_engine - selected_count
        while remaining_budget > 0:
            progress = False
            for bucket_key in ordered_bucket_keys:
                bucket_leftovers = leftovers[bucket_key]
                if not bucket_leftovers:
                    continue
                selected_ids.add(bucket_leftovers.pop(0))
                remaining_budget -= 1
                progress = True
                if remaining_budget <= 0:
                    break
            if not progress:
                break

    selected_candidates = tuple(
        event for event in candidates if event.candidate_id in selected_ids
    )
    selected_bucket_keys = {_temporal_bucket_key(event) for event in selected_candidates}
    available_bucket_count = len(available_bucket_keys)
    selected_bucket_count = len(selected_bucket_keys)
    return StrategyLadderCandidateBudgetResult(
        candidates=selected_candidates,
        limited=len(selected_candidates) < len(candidates),
        limit_reason="TEMPORAL_STRATIFIED_SAMPLE_BUDGET_ACTIVE",
        cap_status="CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
        temporal_bucket_granularity="day",
        temporal_bucket_count_available=available_bucket_count,
        temporal_bucket_count_selected=selected_bucket_count,
        temporal_bucket_coverage_ratio=(
            selected_bucket_count / float(available_bucket_count)
            if available_bucket_count > 0
            else None
        ),
    )


def apply_strategy_ladder_candidate_budget(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
    *,
    sample_cap_per_engine: int,
    candidate_discovery_mode: str,
) -> StrategyLadderCandidateBudgetResult:
    if _is_temporal_stratified_candidate_mode(candidate_discovery_mode):
        return _cap_strategy_ladder_candidates_temporal_stratified(
            candidates,
            sample_cap_per_engine=sample_cap_per_engine,
        )
    capped, limited = cap_strategy_ladder_candidates(
        candidates,
        sample_cap_per_engine=sample_cap_per_engine,
    )
    return StrategyLadderCandidateBudgetResult(
        candidates=capped,
        limited=limited,
        limit_reason="ENGINE_NATIVE_SAMPLE_CAP_ACTIVE" if limited else "",
        cap_status=(
            "CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
            if limited
            else "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN"
        ),
    )


def export_strategy_ladder_candidates(
    output_dir: Path,
    *,
    run_id: str,
    candidates: tuple[StrategyLadderCandidateEvent, ...],
    feature_store_status: str,
    candidate_discovery_status: str,
    requested_pairs: tuple[str, ...] = (),
    pairs_with_feature_rows: tuple[str, ...] = (),
    candidate_sample_cap: int = 0,
    effective_engine_native_sample_size: int = 10,
    engine_count: int = 4,
    candidate_cap_formula: str = "",
    small_scope_enabled: bool = True,
    full_scan_enabled: bool = False,
    no_full_scan_enabled: bool = True,
    candidate_discovery_limited: bool = True,
    candidate_discovery_limit_reason: str = "",
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG",
    candidate_discovery_cap_status: str = "CANDIDATE_DISCOVERY_LIMIT_NOT_PROVEN",
    preselection_status: str = "ENGINE_NATIVE_PRESELECTION_NOT_PROVEN",
    replay_input_mode_status: str = "PRESELECTED_ONLY",
    preselected_only: bool = True,
    diagnostic_full_replay: bool = False,
    b1_5_policy_mode: str = "conservative_hard_only",
    discovery_pre_candidate_count: int = 0,
    engine_native_preselected_count: int = 0,
    preselection_hard_rejected_count: int = 0,
    preselection_soft_flagged_count: int = 0,
    preselection_passed_count: int = 0,
    b2_replay_candidate_count: int = 0,
    trade_eligible_candidate_count: int = 0,
    preselection_rejection_count: int = 0,
    replay_savings_estimate_count: int = 0,
    unique_candidate_count: int | None = None,
    base_event_count: int | None = None,
    per_engine_candidate_count: int | None = None,
    engine_native_candidate_count: int | None = None,
    candidate_source_status: str | None = None,
    temporal_bucket_granularity: str = "",
    temporal_bucket_count_available: int = 0,
    temporal_bucket_count_selected: int = 0,
    temporal_bucket_coverage_ratio: float | None = None,
) -> StrategyLadderCandidateSummary:
    """Write canonical candidate export artifacts for one run."""

    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "candidate_events.jsonl"
    summary_path = output_dir / "candidate_summary.json"
    candidate_export_status = (
        "CANDIDATE_EXPORT_READY" if candidates else "CANDIDATE_EXPORT_EMPTY"
    )
    lines = [
        event.model_dump_json(exclude_none=False)
        for event in candidates
    ]
    atomic_write_text(events_path, "\n".join(lines) + ("\n" if lines else ""))
    try:
        write_tabular_mirror(
            rows=candidates,
            artifact_name="candidate_events",
            output_dir=output_dir,
            source_path=events_path,
        )
    except Exception as exc:  # pragma: no cover - optional performance mirror
        atomic_write_json(
            output_dir / "candidate_events.tabular_manifest.json",
            {
                "schema_version": "v53.tabular_artifact_mirror.v1",
                "artifact_name": "candidate_events",
                "source_path": str(events_path.resolve()),
                "status": "TABULAR_MIRROR_FAILED_NON_BLOCKING",
                "error_type": type(exc).__name__,
                "audit_jsonl_preserved": events_path.is_file(),
            },
            indent=2,
        )
    candidate_semantics = summarize_candidate_count_semantics(candidates)
    pairs_seen = tuple(sorted({event.pair for event in candidates if event.pair}))
    requested_pair_set = {
        str(pair).strip().upper()
        for pair in requested_pairs
        if str(pair).strip()
    }
    feature_pair_set = {
        str(pair).strip().upper()
        for pair in pairs_with_feature_rows
        if str(pair).strip()
    }
    pair_seen_set = {str(pair).strip().upper() for pair in pairs_seen if pair}
    data_backed_requested_pair_set = (
        requested_pair_set & feature_pair_set if feature_pair_set else requested_pair_set
    )
    missing_requested_pairs = tuple(
        sorted(pair for pair in data_backed_requested_pair_set if pair not in pair_seen_set)
    )
    pair_candidate_blocker_codes = (
        ("PAIR_NO_ENGINE_NATIVE_CANDIDATES",) if missing_requested_pairs else ()
    )
    candidate_count_by_pair: dict[str, int] = {}
    candidate_count_by_pair_engine: dict[str, int] = {}
    candidate_count_by_pair_timeframe: dict[str, int] = {}
    for event in candidates:
        if event.pair:
            candidate_count_by_pair[event.pair] = (
                candidate_count_by_pair.get(event.pair, 0) + 1
            )
        pair_engine_key = f"{event.pair}|{event.engine_id}"
        candidate_count_by_pair_engine[pair_engine_key] = (
            candidate_count_by_pair_engine.get(pair_engine_key, 0) + 1
        )
        if event.timeframe:
            pair_timeframe_key = f"{event.pair}|{event.timeframe}"
            candidate_count_by_pair_timeframe[pair_timeframe_key] = (
                candidate_count_by_pair_timeframe.get(pair_timeframe_key, 0) + 1
            )
    summary = StrategyLadderCandidateSummary(
        run_id=run_id,
        candidate_count=(
            unique_candidate_count
            if unique_candidate_count is not None
            else candidate_semantics.unique_candidate_count
        ),
        unique_candidate_count=(
            unique_candidate_count
            if unique_candidate_count is not None
            else candidate_semantics.unique_candidate_count
        ),
        base_event_count=(
            base_event_count
            if base_event_count is not None
            else candidate_semantics.base_event_count
        ),
        per_engine_candidate_count=(
            per_engine_candidate_count
            if per_engine_candidate_count is not None
            else candidate_semantics.per_engine_candidate_count
        ),
        engine_native_candidate_count=(
            engine_native_candidate_count
            if engine_native_candidate_count is not None
            else candidate_semantics.engine_native_candidate_count
        ),
        candidate_source_status=(
            candidate_source_status
            if candidate_source_status is not None
            else candidate_semantics.candidate_source_status
        ),
        requested_pairs=tuple(sorted(requested_pair_set)),
        pairs_with_feature_rows=tuple(sorted(feature_pair_set)),
        pairs_seen=pairs_seen,
        missing_requested_pairs=missing_requested_pairs,
        pair_candidate_coverage_status=(
            "PAIR_CANDIDATE_COVERAGE_BLOCKED"
            if missing_requested_pairs
            else "PAIR_CANDIDATE_COVERAGE_READY"
            if pairs_seen
            else "PAIR_CANDIDATE_COVERAGE_EMPTY"
        ),
        pair_candidate_blocker_codes=pair_candidate_blocker_codes,
        candidate_count_by_pair=dict(sorted(candidate_count_by_pair.items())),
        candidate_count_by_pair_engine=dict(sorted(candidate_count_by_pair_engine.items())),
        candidate_count_by_pair_timeframe=dict(
            sorted(candidate_count_by_pair_timeframe.items())
        ),
        engines_seen=tuple(sorted({event.engine_id for event in candidates})),
        strategies_seen=tuple(sorted({event.strategy_id for event in candidates})),
        timeframes_seen=tuple(
            sorted(
                {
                    event.timeframe
                    for event in candidates
                    if event.timeframe
                }
            )
        ),
        start_timestamp=(
            min(event.resolved_timestamp_ms for event in candidates)
            if candidates
            else None
        ),
        end_timestamp=(
            max(event.resolved_timestamp_ms for event in candidates)
            if candidates
            else None
        ),
        feature_store_status=feature_store_status,
        candidate_discovery_status=candidate_discovery_status,
        candidate_export_status=candidate_export_status,
        candidate_sample_cap=candidate_sample_cap,
        effective_engine_native_sample_size=effective_engine_native_sample_size,
        engine_count=engine_count,
        candidate_cap_formula=candidate_cap_formula,
        small_scope_enabled=small_scope_enabled,
        full_scan_enabled=full_scan_enabled,
        no_full_scan_enabled=no_full_scan_enabled,
        candidate_discovery_limited=candidate_discovery_limited,
        candidate_discovery_limit_reason=candidate_discovery_limit_reason,
        candidate_discovery_mode=candidate_discovery_mode,
        candidate_discovery_cap_status=candidate_discovery_cap_status,
        temporal_bucket_granularity=temporal_bucket_granularity,
        temporal_bucket_count_available=temporal_bucket_count_available,
        temporal_bucket_count_selected=temporal_bucket_count_selected,
        temporal_bucket_coverage_ratio=temporal_bucket_coverage_ratio,
        preselection_status=preselection_status,
        replay_input_mode_status=replay_input_mode_status,
        preselected_only=preselected_only,
        diagnostic_full_replay=diagnostic_full_replay,
        b1_5_policy_mode=b1_5_policy_mode,
        discovery_pre_candidate_count=discovery_pre_candidate_count,
        engine_native_preselected_count=engine_native_preselected_count,
        preselection_hard_rejected_count=preselection_hard_rejected_count,
        preselection_soft_flagged_count=preselection_soft_flagged_count,
        preselection_passed_count=preselection_passed_count,
        b2_replay_candidate_count=b2_replay_candidate_count,
        trade_eligible_candidate_count=trade_eligible_candidate_count,
        preselection_rejection_count=preselection_rejection_count,
        replay_savings_estimate_count=replay_savings_estimate_count,
        input_data_hash=(
            deterministic_payload_hash(
                [event.input_data_hash for event in candidates]
            )
            if candidates
            else None
        ),
        created_at=datetime.now(tz=UTC),
    )
    summary = summary.model_copy(
        update={"artifact_hash": deterministic_payload_hash(summary.model_dump(mode="json"))}
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"))
    return summary


def load_strategy_ladder_candidate_events(path: Path) -> tuple[StrategyLadderCandidateEvent, ...]:
    """Read one canonical Strategy Ladder candidate export."""

    records: list[StrategyLadderCandidateEvent] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(StrategyLadderCandidateEvent.model_validate_json(stripped))
    return tuple(records)


def load_strategy_ladder_candidate_summary(
    path: Path,
) -> StrategyLadderCandidateSummary | None:
    if not path.is_file():
        return None
    try:
        return StrategyLadderCandidateSummary.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, TypeError, ValueError):
        return None


__all__ = [
    "StrategyLadderCandidateBudgetResult",
    "apply_strategy_ladder_candidate_budget",
    "cap_strategy_ladder_candidates",
    "discover_strategy_ladder_candidates",
    "export_strategy_ladder_candidates",
    "load_strategy_ladder_candidate_events",
    "load_strategy_ladder_candidate_summary",
]
