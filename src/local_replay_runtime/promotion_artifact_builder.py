"""Governed promotion and sample-size artifact builders for replay exports."""

from __future__ import annotations

from datetime import UTC, datetime
import math
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    EngineCPromotionLocalStatus,
    EngineDPromotionLocalStatus,
    EnginePromotionArtifact,
    PairPromotionArtifact,
    SampleSizeSurvivalArtifact,
    StrategyPromotionArtifact,
    engine_promotion_artifact_hash,
    pair_promotion_artifact_hash,
    sample_size_survival_artifact_hash,
    strategy_promotion_artifact_hash,
)
from local_replay_runtime.strategy_ladder_count_semantics import (
    summarize_replay_count_semantics,
)
from local_replay_runtime.replay_metrics_collector import (
    ReplayMetricsSummary,
    _guard_executed_only_return_status,
    _true_net_equity_drawdown,
    _executed_only_net_return,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


_SELECTED_STATES = {
    DecisionState.SELECTED,
    DecisionState.REDUCED,
    DecisionState.PHANTOM,
    DecisionState.EXECUTED,
}
_PROMOTION_READY_EXECUTED_RETURN_STATUSES = {
    "EXECUTED_NET_RETURN_PROVEN",
    "EXECUTED_RETURN_PROVEN",
}
_PROMOTION_READY_DRAWDOWN_STATUSES = {
    "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
    "MEASURED",
    "PROVEN",
}
_PROMOTION_READY_SAMPLE_STATUSES = {
    "SAMPLE_SIZE_PROVEN",
    "MEASURED",
    "PROVEN",
    "PASS",
}
_PROMOTION_READY_FILL_STATUSES = {
    "FILL_REALISM_PROVEN",
    "FILL_REALISM_SHADOW_MEASURED",
    "MEASURED",
    "PROVEN",
}
_PROMOTION_READY_COST_STATUSES = {"COST_MODEL_COMPLETE", "COMPLETE"}
_PROMOTION_READY_DEPTH_STATUSES = {"BOOK_DEPTH20_AVAILABLE"}


class SampleSizeSurvivalBuildInput(BaseModel, frozen=True):
    """Typed build input for a single sample-size survival artifact."""

    run_id: str | None = None
    scope: str = Field(..., min_length=1)
    scope_id: str = Field(..., min_length=1)
    raw_candidate_count: int | None = Field(default=None, ge=0)
    after_hard_filters_count: int | None = Field(default=None, ge=0)
    after_cost_filters_count: int | None = Field(default=None, ge=0)
    after_risk_filters_count: int | None = Field(default=None, ge=0)
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    min_required_candidates: int | None = Field(default=None, ge=0)
    min_required_executions: int | None = Field(default=None, ge=0)
    min_required_days: int | None = Field(default=None, ge=0)
    sample_period_start: str | None = None
    sample_period_end: str | None = None
    sample_days: int | None = Field(default=None, ge=0)
    input_data_hash: str | None = None
    method_version_hash: str | None = "promotion_artifact_builder.v1"
    created_at: datetime | None = None
    expires_at: datetime | None = None


class ReplayPromotionArtifactBundle(BaseModel, frozen=True):
    """All governed promotion/sample-size artifacts emitted for one replay run."""

    engine_promotion_artifacts: tuple[EnginePromotionArtifact, ...] = ()
    pair_promotion_artifacts: tuple[PairPromotionArtifact, ...] = ()
    strategy_promotion_artifacts: tuple[StrategyPromotionArtifact, ...] = ()
    sample_size_survival_artifacts: tuple[SampleSizeSurvivalArtifact, ...] = ()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _timestamp_ms_to_iso(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).isoformat()


def _sample_days(manifest: ReplayRunManifest) -> int:
    duration_ms = max(0, manifest.end_timestamp_ms - manifest.start_timestamp_ms)
    return max(1, math.ceil(duration_ms / 86_400_000))


def _safe_scope_id(*parts: str) -> str:
    return "__".join(part.replace("/", "_").replace("\\", "_") for part in parts if part)


def _ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return round(numerator / denominator, 6)


def _dedupe(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _build_engine_local_status(engine_id: str) -> tuple[EngineCPromotionLocalStatus | None, EngineDPromotionLocalStatus | None]:
    if engine_id == "engine_c":
        return EngineCPromotionLocalStatus(), None
    if engine_id == "engine_d":
        return None, EngineDPromotionLocalStatus()
    return None, None


def build_sample_size_survival_artifact(
    payload: SampleSizeSurvivalBuildInput,
) -> SampleSizeSurvivalArtifact:
    """Materialize a governed sample-size survival artifact."""

    executed_total = (
        (payload.executed_count or 0) + (payload.reduced_count or 0)
        if payload.executed_count is not None or payload.reduced_count is not None
        else None
    )
    blockers: list[str] = []
    status = "SAMPLE_SIZE_NOT_PROVEN"
    raw_count = payload.raw_candidate_count
    if raw_count in {None, 0}:
        status = "SAMPLE_SIZE_BLOCKED_BY_BACKTEST"
        blockers.append("SAMPLE_SIZE_BLOCKED_BY_BACKTEST")
    else:
        filter_counts = tuple(
            value
            for value in (
                payload.after_hard_filters_count,
                payload.after_cost_filters_count,
                payload.after_risk_filters_count,
                payload.selected_count,
            )
            if value is not None
        )
        if filter_counts and any(value == 0 for value in filter_counts):
            status = "SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS"
            blockers.append("SAMPLE_SIZE_COLLAPSED_AFTER_FILTERS")
        elif (
            payload.min_required_candidates is not None
            and raw_count < payload.min_required_candidates
        ):
            status = "SAMPLE_SIZE_INSUFFICIENT_CANDIDATES"
            blockers.append("SAMPLE_SIZE_INSUFFICIENT_CANDIDATES")
        elif (
            payload.min_required_executions is not None
            and (executed_total is None or executed_total < payload.min_required_executions)
        ):
            status = "SAMPLE_SIZE_INSUFFICIENT_EXECUTIONS"
            blockers.append("SAMPLE_SIZE_INSUFFICIENT_EXECUTIONS")
        elif (
            payload.min_required_days is not None
            and (payload.sample_days is None or payload.sample_days < payload.min_required_days)
        ):
            status = "SAMPLE_SIZE_TOO_SHORT_PERIOD"
            blockers.append("SAMPLE_SIZE_TOO_SHORT_PERIOD")
        elif all(
            threshold is not None
            for threshold in (
                payload.min_required_candidates,
                payload.min_required_executions,
                payload.min_required_days,
            )
        ):
            status = "SAMPLE_SIZE_PROVEN"
        else:
            status = "SAMPLE_SIZE_NOT_PROVEN"
            blockers.append("SAMPLE_SIZE_NOT_PROVEN")
    artifact = SampleSizeSurvivalArtifact(
        run_id=payload.run_id,
        scope=payload.scope,
        id=payload.scope_id,
        raw_candidate_count=payload.raw_candidate_count,
        after_hard_filters_count=payload.after_hard_filters_count,
        after_cost_filters_count=payload.after_cost_filters_count,
        after_risk_filters_count=payload.after_risk_filters_count,
        selected_count=payload.selected_count,
        executed_count=payload.executed_count,
        reduced_count=payload.reduced_count,
        no_fill_count=payload.no_fill_count,
        survival_ratio_raw_to_selected=_ratio(payload.selected_count, payload.raw_candidate_count),
        survival_ratio_selected_to_executed=_ratio(executed_total, payload.selected_count),
        survival_ratio_raw_to_executed=_ratio(executed_total, payload.raw_candidate_count),
        min_required_candidates=payload.min_required_candidates,
        min_required_executions=payload.min_required_executions,
        min_required_days=payload.min_required_days,
        sample_period_start=payload.sample_period_start,
        sample_period_end=payload.sample_period_end,
        sample_days=payload.sample_days,
        sample_size_survival_status=status,
        sample_size_blockers=_dedupe(blockers),
        input_data_hash=payload.input_data_hash,
        method_version_hash=payload.method_version_hash,
        created_at=_normalize_datetime(payload.created_at),
        expires_at=_normalize_datetime(payload.expires_at),
    )
    return artifact.model_copy(
        update={"artifact_hash": sample_size_survival_artifact_hash(artifact)}
    )


def _pair_groups(records: tuple[DTRRecord, ...]) -> dict[str, tuple[DTRRecord, ...]]:
    groups: dict[str, list[DTRRecord]] = {}
    for record in records:
        groups.setdefault(record.pair, []).append(record)
    return {pair: tuple(group) for pair, group in groups.items()}


def _engine_groups(records: tuple[DTRRecord, ...]) -> dict[str, tuple[DTRRecord, ...]]:
    groups: dict[str, list[DTRRecord]] = {}
    for record in records:
        groups.setdefault(record.engine_id, []).append(record)
    return {engine_id: tuple(group) for engine_id, group in groups.items()}


def _pair_result_groups(
    results: tuple[StrategyLadderBucketReplayResult, ...],
) -> dict[str, tuple[StrategyLadderBucketReplayResult, ...]]:
    groups: dict[str, list[StrategyLadderBucketReplayResult]] = {}
    for result in results:
        groups.setdefault(result.pair, []).append(result)
    return {pair: tuple(group) for pair, group in groups.items()}


def _engine_result_groups(
    results: tuple[StrategyLadderBucketReplayResult, ...],
) -> dict[str, tuple[StrategyLadderBucketReplayResult, ...]]:
    groups: dict[str, list[StrategyLadderBucketReplayResult]] = {}
    for result in results:
        groups.setdefault(result.engine_id, []).append(result)
    return {engine_id: tuple(group) for engine_id, group in groups.items()}


def _candidate_event_identity(
    candidate: StrategyLadderCandidateEvent,
) -> tuple[str, int, str, str, str, str]:
    return (
        candidate.candidate_id,
        candidate.resolved_timestamp_ms,
        candidate.pair,
        candidate.timeframe or "",
        candidate.engine_id,
        candidate.strategy_id,
    )


def _pair_candidate_groups(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
) -> dict[str, tuple[StrategyLadderCandidateEvent, ...]]:
    groups: dict[str, list[StrategyLadderCandidateEvent]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.pair, []).append(candidate)
    return {pair: tuple(group) for pair, group in groups.items()}


def _engine_candidate_groups(
    candidates: tuple[StrategyLadderCandidateEvent, ...],
) -> dict[str, tuple[StrategyLadderCandidateEvent, ...]]:
    groups: dict[str, list[StrategyLadderCandidateEvent]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.engine_id, []).append(candidate)
    return {engine_id: tuple(group) for engine_id, group in groups.items()}


def _group_counts(
    records: tuple[DTRRecord, ...],
    *,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...] = (),
    candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
) -> dict[str, int | float | str | None]:
    candidate_count = (
        len({_candidate_event_identity(candidate) for candidate in candidate_events})
        if candidate_events
        else len({result.candidate_id for result in bucket_results})
        if bucket_results
        else len(records)
    )
    candidate_selected_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower()
                in {state.value for state in _SELECTED_STATES}
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state in _SELECTED_STATES)
    )
    candidate_executed_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower() == DecisionState.EXECUTED.value
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state == DecisionState.EXECUTED)
    )
    candidate_reduced_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower() == DecisionState.REDUCED.value
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state == DecisionState.REDUCED)
    )
    candidate_no_fill_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower() == DecisionState.PHANTOM.value
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state == DecisionState.PHANTOM)
    )
    candidate_hard_blocked_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower() == DecisionState.HARD_BLOCKED.value
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED)
    )
    candidate_rejected_count = (
        len(
            {
                result.candidate_id
                for result in bucket_results
                if str(result.execution_state or "").lower()
                == DecisionState.REJECTED_RANKING.value
            }
        )
        if bucket_results
        else sum(1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING)
    )
    replay_semantics = summarize_replay_count_semantics(
        unique_candidate_count=candidate_count,
        bucket_results=bucket_results,
    )
    return {
        "record_count": len(records),
        "candidate_count": candidate_count,
        "candidate_selected_count": candidate_selected_count,
        "candidate_executed_count": candidate_executed_count,
        "candidate_reduced_count": candidate_reduced_count,
        "candidate_no_fill_count": candidate_no_fill_count,
        "candidate_hard_blocked_count": candidate_hard_blocked_count,
        "candidate_rejected_count": candidate_rejected_count,
        "evaluation_record_count": replay_semantics.evaluation_record_count,
        "promotion_record_count": replay_semantics.promotion_record_count,
        "capital_bucket_record_count": replay_semantics.capital_bucket_record_count,
        "replay_expansion_factor": replay_semantics.replay_expansion_factor,
        "replay_expansion_axis": replay_semantics.replay_expansion_axis,
        "selected_count": sum(1 for record in records if record.decision_state in _SELECTED_STATES),
        "executed_count": sum(1 for record in records if record.decision_state == DecisionState.EXECUTED),
        "reduced_count": sum(1 for record in records if record.decision_state == DecisionState.REDUCED),
        "no_fill_count": sum(1 for record in records if record.decision_state == DecisionState.PHANTOM),
        "hard_blocked_count": sum(1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED),
        "rejected_count": sum(1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING),
    }


def _pair_economics(
    records: tuple[DTRRecord, ...],
    *,
    initial_capital: float | None,
    cost_model_completeness_status: str,
) -> tuple[float | None, str, float | None, str]:
    executed_only_net_return, raw_status, _missing_realized_cost_count = _executed_only_net_return(records)
    executed_only_net_return, executed_only_net_return_status = _guard_executed_only_return_status(
        executed_only_net_return,
        raw_status,
        cost_model_completeness_status=cost_model_completeness_status,
    )
    _curve, true_drawdown, true_drawdown_status = _true_net_equity_drawdown(
        records,
        initial_capital=initial_capital,
        executed_only_net_return_status=executed_only_net_return_status,
    )
    return (
        executed_only_net_return,
        executed_only_net_return_status,
        true_drawdown,
        true_drawdown_status,
    )


def _strategy_role(manifest: ReplayRunManifest) -> str:
    if manifest.strategy_identity is not None:
        return manifest.strategy_identity.bet_structure.value
    return manifest.strategy_classification.value


def _derive_engine_promotion_status(
    *,
    engine_id: str,
    record_count: int | None,
    executed_only_net_return: float | None,
    executed_only_net_return_status: str,
    true_drawdown_status: str,
    sample_size_status: str,
    cost_model_completeness_status: str,
    fill_realism_status: str,
    book_depth_source_status: str,
    execution_fidelity_gap_codes: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    blockers: list[str] = []
    if record_count in {None, 0}:
        blockers.append("ENGINE_PROMOTION_BLOCKED_BY_BACKTEST")
        return "ENGINE_PROMOTION_BLOCKED_BY_BACKTEST", _dedupe(blockers)
    if execution_fidelity_gap_codes:
        blockers.append("ENGINE_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY")
        blockers.extend(str(code) for code in execution_fidelity_gap_codes if str(code))
    if sample_size_status not in _PROMOTION_READY_SAMPLE_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_SAMPLE_SIZE")
    if cost_model_completeness_status not in _PROMOTION_READY_COST_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_COST_COMPLETENESS")
    if fill_realism_status not in _PROMOTION_READY_FILL_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_FILL_REALISM")
    if book_depth_source_status not in _PROMOTION_READY_DEPTH_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_DEPTH")
    if true_drawdown_status not in _PROMOTION_READY_DRAWDOWN_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_DRAWDOWN")
    if executed_only_net_return_status not in _PROMOTION_READY_EXECUTED_RETURN_STATUSES:
        blockers.append("EXECUTED_RETURN_NOT_PROVEN")
    elif executed_only_net_return is not None and executed_only_net_return <= 0.0:
        blockers.append("ENGINE_EXECUTED_RETURN_NON_POSITIVE")
    if engine_id in {"engine_c", "engine_d"}:
        blockers.append("ENGINE_C_D_ARTIFACTS_NOT_MEASURED")
    blockers = list(_dedupe(blockers))
    if not blockers:
        return "ENGINE_PROMOTION_READY", ()
    if "ENGINE_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_SAMPLE_SIZE" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_SAMPLE_SIZE", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_COST_COMPLETENESS" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_COST_COMPLETENESS", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_FILL_REALISM" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_FILL_REALISM", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_DEPTH" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_DEPTH", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_DRAWDOWN" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_DRAWDOWN", tuple(blockers)
    if "ENGINE_C_D_ARTIFACTS_NOT_MEASURED" in blockers:
        return "ENGINE_PROMOTION_BLOCKED_BY_C_D_ARTIFACTS", tuple(blockers)
    return "ENGINE_PROMOTION_NOT_PROVEN", tuple(blockers)


def _derive_pair_promotion_status(
    *,
    record_count: int | None,
    min_notional_block_rate: float | None,
    capital_fragmentation_rate: float | None,
    executed_only_net_return: float | None,
    executed_only_net_return_status: str,
    true_drawdown_status: str,
    sample_size_status: str,
    cost_model_completeness_status: str,
    fill_realism_status: str,
    book_depth_source_status: str,
    execution_fidelity_gap_codes: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    blockers: list[str] = []
    if record_count in {None, 0}:
        return "PAIR_NOT_PROVEN", ("PAIR_NOT_PROVEN",)
    if execution_fidelity_gap_codes:
        blockers.append("PAIR_BLOCKED_EXECUTION_FIDELITY")
        blockers.extend(str(code) for code in execution_fidelity_gap_codes if str(code))
    if min_notional_block_rate is not None and min_notional_block_rate > 0.0:
        blockers.append("PAIR_BLOCKED_MIN_NOTIONAL")
    if capital_fragmentation_rate is not None and capital_fragmentation_rate > 0.0:
        blockers.append("PAIR_BLOCKED_CAPITAL_FRAGMENTATION")
    if cost_model_completeness_status not in _PROMOTION_READY_COST_STATUSES:
        blockers.append("PAIR_BLOCKED_COST_COMPLETENESS")
    if fill_realism_status not in _PROMOTION_READY_FILL_STATUSES:
        blockers.append("PAIR_BLOCKED_FILL_REALISM")
    if book_depth_source_status not in _PROMOTION_READY_DEPTH_STATUSES:
        blockers.append("PAIR_BLOCKED_DEPTH_LIMITATION")
    if sample_size_status not in _PROMOTION_READY_SAMPLE_STATUSES:
        blockers.append("PAIR_BLOCKED_SAMPLE_SIZE")
    if true_drawdown_status not in _PROMOTION_READY_DRAWDOWN_STATUSES:
        blockers.append("PAIR_BLOCKED_DRAWDOWN")
    if executed_only_net_return_status not in _PROMOTION_READY_EXECUTED_RETURN_STATUSES:
        blockers.append("PAIR_NOT_PROVEN")
    elif executed_only_net_return is not None and executed_only_net_return < 0.0:
        blockers.append("PAIR_BLOCKED_NEGATIVE_EXECUTED_RETURN")
    blockers = list(_dedupe(blockers))
    if not blockers:
        return "PAIR_ALLOWED", ()
    for status in (
        "PAIR_BLOCKED_EXECUTION_FIDELITY",
        "PAIR_BLOCKED_MIN_NOTIONAL",
        "PAIR_BLOCKED_CAPITAL_FRAGMENTATION",
        "PAIR_BLOCKED_COST_COMPLETENESS",
        "PAIR_BLOCKED_FILL_REALISM",
        "PAIR_BLOCKED_DEPTH_LIMITATION",
        "PAIR_BLOCKED_SAMPLE_SIZE",
        "PAIR_BLOCKED_DRAWDOWN",
        "PAIR_BLOCKED_NEGATIVE_EXECUTED_RETURN",
        "PAIR_NOT_PROVEN",
    ):
        if status in blockers:
            return status, tuple(blockers)
    return "PAIR_NOT_PROVEN", tuple(blockers)


def _derive_strategy_promotion_status(
    *,
    record_count: int | None,
    executed_only_net_return_status: str,
    true_drawdown_status: str,
    sample_size_status: str,
    cost_model_completeness_status: str,
    fill_realism_status: str,
    book_depth_source_status: str,
    execution_fidelity_gap_codes: tuple[str, ...] = (),
) -> tuple[str, tuple[str, ...]]:
    blockers: list[str] = []
    if record_count in {None, 0}:
        blockers.append("STRATEGY_PROMOTION_BLOCKED_BY_BACKTEST")
        return "STRATEGY_PROMOTION_BLOCKED_BY_BACKTEST", tuple(blockers)
    if execution_fidelity_gap_codes:
        blockers.append("STRATEGY_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY")
        blockers.extend(str(code) for code in execution_fidelity_gap_codes if str(code))
    if sample_size_status not in _PROMOTION_READY_SAMPLE_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_SAMPLE_SIZE")
    if cost_model_completeness_status not in _PROMOTION_READY_COST_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_COST_COMPLETENESS")
    if fill_realism_status not in _PROMOTION_READY_FILL_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_FILL_REALISM")
    if book_depth_source_status not in _PROMOTION_READY_DEPTH_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_DEPTH")
    if true_drawdown_status not in _PROMOTION_READY_DRAWDOWN_STATUSES:
        blockers.append("PROMOTION_BLOCKED_BY_DRAWDOWN")
    if executed_only_net_return_status not in _PROMOTION_READY_EXECUTED_RETURN_STATUSES:
        blockers.append("EXECUTED_RETURN_NOT_PROVEN")
    blockers = list(_dedupe(blockers))
    if not blockers:
        return "STRATEGY_PROMOTION_READY", ()
    if "STRATEGY_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY" in blockers:
        return "STRATEGY_PROMOTION_BLOCKED_BY_EXECUTION_FIDELITY", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_SAMPLE_SIZE" in blockers:
        return "STRATEGY_PROMOTION_BLOCKED_BY_SAMPLE_SIZE", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_COST_COMPLETENESS" in blockers:
        return "STRATEGY_PROMOTION_BLOCKED_BY_COST_COMPLETENESS", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_FILL_REALISM" in blockers:
        return "STRATEGY_PROMOTION_BLOCKED_BY_FILL_REALISM", tuple(blockers)
    if "PROMOTION_BLOCKED_BY_DRAWDOWN" in blockers:
        return "STRATEGY_PROMOTION_BLOCKED_BY_DRAWDOWN", tuple(blockers)
    return "STRATEGY_PROMOTION_NOT_PROVEN", tuple(blockers)


def _engine_survival_artifact(
    *,
    run_manifest: ReplayRunManifest,
    engine_id: str,
    counts: dict[str, int],
    min_required_candidates: int | None,
    min_required_executions: int | None,
    min_required_days: int | None,
    created_at: datetime | None,
    expires_at: datetime | None,
    input_data_hash: str | None,
    method_version_hash: str,
) -> SampleSizeSurvivalArtifact:
    return build_sample_size_survival_artifact(
        SampleSizeSurvivalBuildInput(
            run_id=run_manifest.run_id,
            scope="engine",
            scope_id=engine_id,
            raw_candidate_count=counts["candidate_count"],
            after_hard_filters_count=counts["candidate_count"] - counts["candidate_hard_blocked_count"],
            selected_count=counts["candidate_selected_count"],
            executed_count=counts["candidate_executed_count"],
            reduced_count=counts["candidate_reduced_count"],
            no_fill_count=counts["candidate_no_fill_count"],
            min_required_candidates=min_required_candidates,
            min_required_executions=min_required_executions,
            min_required_days=min_required_days,
            sample_period_start=_timestamp_ms_to_iso(run_manifest.start_timestamp_ms),
            sample_period_end=_timestamp_ms_to_iso(run_manifest.end_timestamp_ms),
            sample_days=_sample_days(run_manifest),
            input_data_hash=input_data_hash,
            method_version_hash=method_version_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
    )


def build_replay_promotion_artifact_bundle(
    *,
    run_manifest: ReplayRunManifest,
    metrics_summary: ReplayMetricsSummary,
    dtr_records: tuple[DTRRecord, ...],
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...] = (),
    candidate_events: tuple[StrategyLadderCandidateEvent, ...] = (),
    min_required_candidates: int | None = None,
    min_required_executions: int | None = None,
    min_required_days: int | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    input_data_hash: str | None = None,
    method_version_hash: str = "promotion_artifact_builder.v1",
) -> ReplayPromotionArtifactBundle:
    """Build governed promotion/sample-size artifacts from a replay export session."""

    created_at = _normalize_datetime(created_at)
    expires_at = _normalize_datetime(expires_at)
    pair_groups = _pair_groups(dtr_records)
    engine_groups = _engine_groups(dtr_records)
    pair_result_groups = _pair_result_groups(bucket_results)
    engine_result_groups = _engine_result_groups(bucket_results)
    pair_candidate_groups = _pair_candidate_groups(candidate_events)
    engine_candidate_groups = _engine_candidate_groups(candidate_events)
    sample_days = _sample_days(run_manifest)
    sample_start = _timestamp_ms_to_iso(run_manifest.start_timestamp_ms)
    sample_end = _timestamp_ms_to_iso(run_manifest.end_timestamp_ms)
    global_candidate_count = (
        len({_candidate_event_identity(candidate) for candidate in candidate_events})
        if candidate_events
        else len({result.candidate_id for result in bucket_results})
        if bucket_results
        else metrics_summary.total_records
    )
    global_counts = _group_counts(
        dtr_records,
        bucket_results=bucket_results,
        candidate_events=candidate_events,
    )
    global_replay_semantics = summarize_replay_count_semantics(
        unique_candidate_count=global_candidate_count,
        bucket_results=bucket_results,
    )

    sample_artifacts: list[SampleSizeSurvivalArtifact] = [
        build_sample_size_survival_artifact(
            SampleSizeSurvivalBuildInput(
                run_id=run_manifest.run_id,
                scope="global",
                scope_id="global",
                raw_candidate_count=global_candidate_count,
                after_hard_filters_count=global_candidate_count - global_counts["candidate_hard_blocked_count"],
                selected_count=global_counts["candidate_selected_count"],
                executed_count=global_counts["candidate_executed_count"],
                reduced_count=global_counts["candidate_reduced_count"],
                no_fill_count=global_counts["candidate_no_fill_count"],
                min_required_candidates=min_required_candidates,
                min_required_executions=min_required_executions,
                min_required_days=min_required_days,
                sample_period_start=sample_start,
                sample_period_end=sample_end,
                sample_days=sample_days,
                input_data_hash=input_data_hash,
                method_version_hash=method_version_hash,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
    ]

    engine_artifacts: list[EnginePromotionArtifact] = []
    for aggregate in metrics_summary.engine_aggregates:
        counts = _group_counts(
            engine_groups.get(aggregate.engine_id, ()),
            bucket_results=engine_result_groups.get(aggregate.engine_id, ()),
            candidate_events=engine_candidate_groups.get(aggregate.engine_id, ()),
        )
        sample_artifact = _engine_survival_artifact(
            run_manifest=run_manifest,
            engine_id=aggregate.engine_id,
            counts=counts,
            min_required_candidates=min_required_candidates,
            min_required_executions=min_required_executions,
            min_required_days=min_required_days,
            created_at=created_at,
            expires_at=expires_at,
            input_data_hash=input_data_hash,
            method_version_hash=method_version_hash,
        )
        sample_artifacts.append(sample_artifact)
        engine_c_local, engine_d_local = _build_engine_local_status(aggregate.engine_id)
        promotion_status, promotion_blockers = _derive_engine_promotion_status(
            engine_id=aggregate.engine_id,
            record_count=aggregate.record_count,
            executed_only_net_return=aggregate.engine_executed_only_net_return,
            executed_only_net_return_status=aggregate.executed_only_net_return_status,
            true_drawdown_status=aggregate.true_net_equity_drawdown_status,
            sample_size_status=sample_artifact.sample_size_survival_status,
            cost_model_completeness_status=aggregate.cost_model_completeness_status,
            fill_realism_status=aggregate.fill_realism_status,
            book_depth_source_status=aggregate.book_depth_source_status,
            execution_fidelity_gap_codes=aggregate.execution_fidelity_gap_codes,
        )
        engine_artifact = EnginePromotionArtifact(
            run_id=run_manifest.run_id,
            engine_id=aggregate.engine_id,
            engine_role=aggregate.engine_role or None,
            strategy_id=run_manifest.strategy_id,
            capital_bucket=None,
            pair_universe=tuple(sorted({record.pair for record in engine_groups.get(aggregate.engine_id, ())})),
            shared_physics_mapping_status=aggregate.shared_physics_mapping_status,
            record_count=aggregate.record_count,
            candidate_count=int(counts["candidate_count"]),
            unique_candidate_count=int(counts["candidate_count"]),
            engine_evaluation_count=int(counts["record_count"]),
            evaluation_record_count=int(counts["evaluation_record_count"]),
            promotion_record_count=int(counts["promotion_record_count"]),
            capital_bucket_record_count=int(counts["capital_bucket_record_count"]),
            replay_expansion_factor=(
                float(counts["replay_expansion_factor"])
                if counts["replay_expansion_factor"] is not None
                else None
            ),
            replay_expansion_axis=str(counts["replay_expansion_axis"] or ""),
            selected_count=aggregate.selected_count,
            executed_count=aggregate.executed_count,
            reduced_count=aggregate.reduced_count,
            no_fill_count=aggregate.no_fill_count,
            hard_blocked_count=aggregate.hard_blocked_count,
            rejected_count=aggregate.rejected_count,
            execution_rate=aggregate.execution_rate,
            partial_fill_rate=aggregate.partial_fill_rate,
            no_fill_rate=aggregate.no_fill_rate,
            expected_ce_net=aggregate.ce_net,
            executed_only_net_return=aggregate.engine_executed_only_net_return,
            executed_only_net_return_status=aggregate.executed_only_net_return_status,
            true_net_equity_max_drawdown=aggregate.engine_true_net_equity_max_drawdown,
            true_net_equity_drawdown_status=aggregate.true_net_equity_drawdown_status,
            drawdown_proxy=None,
            fee_source_status=aggregate.fee_source_status,
            impact_source_status=aggregate.impact_source_status,
            fill_realism_status=aggregate.fill_realism_status,
            cost_parity_status=aggregate.cost_parity_status,
            execution_label_source=aggregate.execution_label_source,
            fee_model_source=aggregate.fee_model_source,
            spread_model_source=aggregate.spread_model_source,
            slippage_model_source=aggregate.slippage_model_source,
            partial_fill_model_source=aggregate.partial_fill_model_source,
            adverse_selection_source=aggregate.adverse_selection_source,
            order_type_selection_source=aggregate.order_type_selection_source,
            venue_constraints_source=aggregate.venue_constraints_source,
            execution_fidelity_gap_codes=aggregate.execution_fidelity_gap_codes,
            cost_model_completeness_status=aggregate.cost_model_completeness_status,
            book_depth_source_status=aggregate.book_depth_source_status,
            impact_depth_readiness_status=aggregate.impact_depth_readiness_status,
            sample_size_survival_status=sample_artifact.sample_size_survival_status,
            sample_size_survival_ratio=sample_artifact.survival_ratio_raw_to_executed,
            sample_size_min_required=sample_artifact.min_required_executions,
            sample_size_actual=(
                None
                if sample_artifact.executed_count is None and sample_artifact.reduced_count is None
                else (sample_artifact.executed_count or 0) + (sample_artifact.reduced_count or 0)
            ),
            promotion_status=promotion_status,
            promotion_blockers=promotion_blockers,
            engine_c=engine_c_local,
            engine_d=engine_d_local,
            input_data_hash=input_data_hash,
            method_version_hash=method_version_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
        engine_artifacts.append(
            engine_artifact.model_copy(
                update={"artifact_hash": engine_promotion_artifact_hash(engine_artifact)}
            )
        )

    pair_artifacts: list[PairPromotionArtifact] = []
    for pair, pair_records in sorted(pair_groups.items()):
        counts = _group_counts(
            pair_records,
            bucket_results=pair_result_groups.get(pair, ()),
            candidate_events=pair_candidate_groups.get(pair, ()),
        )
        executed_only_net_return, executed_status, true_drawdown, true_drawdown_status = _pair_economics(
            pair_records,
            initial_capital=metrics_summary.initial_capital,
            cost_model_completeness_status=metrics_summary.cost_model_completeness_status,
        )
        pair_sample = build_sample_size_survival_artifact(
            SampleSizeSurvivalBuildInput(
                run_id=run_manifest.run_id,
                scope="pair",
                scope_id=pair,
                raw_candidate_count=counts["candidate_count"],
                after_hard_filters_count=counts["candidate_count"] - counts["candidate_hard_blocked_count"],
                selected_count=counts["candidate_selected_count"],
                executed_count=counts["candidate_executed_count"],
                reduced_count=counts["candidate_reduced_count"],
                no_fill_count=counts["candidate_no_fill_count"],
                min_required_candidates=min_required_candidates,
                min_required_executions=min_required_executions,
                min_required_days=min_required_days,
                sample_period_start=sample_start,
                sample_period_end=sample_end,
                sample_days=sample_days,
                input_data_hash=input_data_hash,
                method_version_hash=method_version_hash,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
        sample_artifacts.append(pair_sample)
        sample_artifacts.append(
            build_sample_size_survival_artifact(
                SampleSizeSurvivalBuildInput(
                    run_id=run_manifest.run_id,
                    scope="strategy_pair",
                    scope_id=_safe_scope_id(run_manifest.strategy_id, pair),
                    raw_candidate_count=counts["candidate_count"],
                    after_hard_filters_count=counts["candidate_count"] - counts["candidate_hard_blocked_count"],
                    selected_count=counts["candidate_selected_count"],
                    executed_count=counts["candidate_executed_count"],
                    reduced_count=counts["candidate_reduced_count"],
                    no_fill_count=counts["candidate_no_fill_count"],
                    min_required_candidates=min_required_candidates,
                    min_required_executions=min_required_executions,
                    min_required_days=min_required_days,
                    sample_period_start=sample_start,
                    sample_period_end=sample_end,
                    sample_days=sample_days,
                    input_data_hash=input_data_hash,
                    method_version_hash=method_version_hash,
                    created_at=created_at,
                    expires_at=expires_at,
                )
            )
        )
        for engine_id in sorted({record.engine_id for record in pair_records}):
            engine_pair_records = tuple(record for record in pair_records if record.engine_id == engine_id)
            engine_pair_counts = _group_counts(
                engine_pair_records,
                bucket_results=tuple(
                    result
                    for result in pair_result_groups.get(pair, ())
                    if result.engine_id == engine_id
                ),
                candidate_events=tuple(
                    candidate
                    for candidate in pair_candidate_groups.get(pair, ())
                    if candidate.engine_id == engine_id
                ),
            )
            sample_artifacts.append(
                build_sample_size_survival_artifact(
                    SampleSizeSurvivalBuildInput(
                        run_id=run_manifest.run_id,
                        scope="engine_pair",
                        scope_id=_safe_scope_id(engine_id, pair),
                        raw_candidate_count=engine_pair_counts["candidate_count"],
                        after_hard_filters_count=engine_pair_counts["candidate_count"] - engine_pair_counts["candidate_hard_blocked_count"],
                        selected_count=engine_pair_counts["candidate_selected_count"],
                        executed_count=engine_pair_counts["candidate_executed_count"],
                        reduced_count=engine_pair_counts["candidate_reduced_count"],
                        no_fill_count=engine_pair_counts["candidate_no_fill_count"],
                        min_required_candidates=min_required_candidates,
                        min_required_executions=min_required_executions,
                        min_required_days=min_required_days,
                        sample_period_start=sample_start,
                        sample_period_end=sample_end,
                        sample_days=sample_days,
                        input_data_hash=input_data_hash,
                        method_version_hash=method_version_hash,
                        created_at=created_at,
                        expires_at=expires_at,
                    )
                )
            )
        promotion_status, promotion_blockers = _derive_pair_promotion_status(
            record_count=counts["record_count"],
            min_notional_block_rate=None,
            capital_fragmentation_rate=None,
            executed_only_net_return=executed_only_net_return,
            executed_only_net_return_status=executed_status,
            true_drawdown_status=true_drawdown_status,
            sample_size_status=pair_sample.sample_size_survival_status,
            cost_model_completeness_status=metrics_summary.cost_model_completeness_status,
            fill_realism_status=metrics_summary.fill_realism_status,
            book_depth_source_status=metrics_summary.book_depth_source_status,
            execution_fidelity_gap_codes=metrics_summary.execution_fidelity_gap_codes,
        )
        pair_artifact = PairPromotionArtifact(
            run_id=run_manifest.run_id,
            pair=pair,
            capital_bucket=None,
            engines_seen=tuple(sorted({record.engine_id for record in pair_records})),
            strategies_seen=(run_manifest.strategy_id,),
            record_count=counts["record_count"],
            candidate_count=counts["candidate_count"],
            unique_candidate_count=counts["candidate_count"],
            evaluation_record_count=counts["evaluation_record_count"],
            promotion_record_count=counts["promotion_record_count"],
            capital_bucket_record_count=counts["capital_bucket_record_count"],
            replay_expansion_factor=counts["replay_expansion_factor"],
            replay_expansion_axis=str(counts["replay_expansion_axis"] or ""),
            selected_count=counts["selected_count"],
            executed_count=counts["executed_count"],
            reduced_count=counts["reduced_count"],
            no_fill_count=counts["no_fill_count"],
            hard_blocked_count=counts["hard_blocked_count"],
            rejected_count=counts["rejected_count"],
            execution_rate=_ratio(counts["executed_count"], counts["record_count"]),
            partial_fill_rate=_ratio(counts["reduced_count"], counts["record_count"]),
            no_fill_rate=_ratio(counts["no_fill_count"], counts["record_count"]),
            expected_ce_net=round(sum(record.ce_expected for record in pair_records), 6),
            executed_only_net_return=executed_only_net_return,
            executed_only_net_return_status=executed_status,
            true_net_equity_max_drawdown=true_drawdown,
            true_net_equity_drawdown_status=true_drawdown_status,
            min_notional_block_rate=None,
            capital_fragmentation_rate=None,
            fee_source_status=metrics_summary.fee_source_status,
            impact_source_status=metrics_summary.impact_source_status,
            fill_realism_status=metrics_summary.fill_realism_status,
            cost_parity_status=metrics_summary.cost_parity_status,
            execution_label_source=metrics_summary.execution_label_source,
            fee_model_source=metrics_summary.fee_model_source,
            spread_model_source=metrics_summary.spread_model_source,
            slippage_model_source=metrics_summary.slippage_model_source,
            partial_fill_model_source=metrics_summary.partial_fill_model_source,
            adverse_selection_source=metrics_summary.adverse_selection_source,
            order_type_selection_source=metrics_summary.order_type_selection_source,
            venue_constraints_source=metrics_summary.venue_constraints_source,
            execution_fidelity_gap_codes=metrics_summary.execution_fidelity_gap_codes,
            book_depth_source_status=metrics_summary.book_depth_source_status,
            sample_size_survival_status=pair_sample.sample_size_survival_status,
            promotion_status=promotion_status,
            promotion_blockers=promotion_blockers,
            input_data_hash=input_data_hash,
            method_version_hash=method_version_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
        pair_artifacts.append(
            pair_artifact.model_copy(
                update={"artifact_hash": pair_promotion_artifact_hash(pair_artifact)}
            )
        )

    strategy_sample = build_sample_size_survival_artifact(
        SampleSizeSurvivalBuildInput(
            run_id=run_manifest.run_id,
            scope="strategy",
            scope_id=run_manifest.strategy_id,
            raw_candidate_count=global_candidate_count,
            after_hard_filters_count=global_candidate_count - global_counts["candidate_hard_blocked_count"],
            selected_count=global_counts["candidate_selected_count"],
            executed_count=global_counts["candidate_executed_count"],
            reduced_count=global_counts["candidate_reduced_count"],
            no_fill_count=global_counts["candidate_no_fill_count"],
            min_required_candidates=min_required_candidates,
            min_required_executions=min_required_executions,
            min_required_days=min_required_days,
            sample_period_start=sample_start,
            sample_period_end=sample_end,
            sample_days=sample_days,
            input_data_hash=input_data_hash,
            method_version_hash=method_version_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
    )
    sample_artifacts.append(strategy_sample)
    strategy_status, strategy_blockers = _derive_strategy_promotion_status(
        record_count=metrics_summary.total_records,
        executed_only_net_return_status=metrics_summary.executed_only_net_return_status,
        true_drawdown_status=metrics_summary.true_net_equity_drawdown_status,
        sample_size_status=strategy_sample.sample_size_survival_status,
        cost_model_completeness_status=metrics_summary.cost_model_completeness_status,
        fill_realism_status=metrics_summary.fill_realism_status,
        book_depth_source_status=metrics_summary.book_depth_source_status,
        execution_fidelity_gap_codes=metrics_summary.execution_fidelity_gap_codes,
    )
    strategy_artifact = StrategyPromotionArtifact(
        run_id=run_manifest.run_id,
        strategy_id=run_manifest.strategy_id,
        strategy_role=_strategy_role(run_manifest),
        engine_ids=run_manifest.engine_scope,
        capital_bucket=None,
        pair_universe=run_manifest.tested_pairs,
        record_count=metrics_summary.total_records,
        candidate_count=global_candidate_count,
        unique_candidate_count=global_candidate_count,
        evaluation_record_count=global_replay_semantics.evaluation_record_count,
        promotion_record_count=global_replay_semantics.promotion_record_count,
        capital_bucket_record_count=global_replay_semantics.capital_bucket_record_count,
        replay_expansion_factor=global_replay_semantics.replay_expansion_factor,
        replay_expansion_axis=global_replay_semantics.replay_expansion_axis,
        selected_count=metrics_summary.selected_count,
        executed_count=metrics_summary.executed_count,
        reduced_count=metrics_summary.reduced_count,
        no_fill_count=metrics_summary.no_fill_count,
        hard_blocked_count=metrics_summary.hard_blocked_count,
        rejected_count=metrics_summary.rejected_count,
        execution_rate=_ratio(metrics_summary.executed_count, metrics_summary.total_records),
        partial_fill_rate=_ratio(metrics_summary.reduced_count, metrics_summary.total_records),
        no_fill_rate=_ratio(metrics_summary.no_fill_count, metrics_summary.total_records),
        expected_ce_net=metrics_summary.ce_net,
        executed_only_net_return=metrics_summary.executed_only_net_return,
        executed_only_net_return_status=metrics_summary.executed_only_net_return_status,
        true_net_equity_max_drawdown=metrics_summary.true_net_equity_max_drawdown,
        true_net_equity_drawdown_status=metrics_summary.true_net_equity_drawdown_status,
        cost_model_completeness_status=metrics_summary.cost_model_completeness_status,
        fill_realism_status=metrics_summary.fill_realism_status,
        cost_parity_status=metrics_summary.cost_parity_status,
        execution_label_source=metrics_summary.execution_label_source,
        fee_model_source=metrics_summary.fee_model_source,
        spread_model_source=metrics_summary.spread_model_source,
        slippage_model_source=metrics_summary.slippage_model_source,
        partial_fill_model_source=metrics_summary.partial_fill_model_source,
        adverse_selection_source=metrics_summary.adverse_selection_source,
        order_type_selection_source=metrics_summary.order_type_selection_source,
        venue_constraints_source=metrics_summary.venue_constraints_source,
        execution_fidelity_gap_codes=metrics_summary.execution_fidelity_gap_codes,
        book_depth_source_status=metrics_summary.book_depth_source_status,
        sample_size_survival_status=strategy_sample.sample_size_survival_status,
        promotion_status=strategy_status,
        promotion_blockers=strategy_blockers,
        input_data_hash=input_data_hash,
        method_version_hash=method_version_hash,
        created_at=created_at,
        expires_at=expires_at,
    )
    strategy_artifact = strategy_artifact.model_copy(
        update={"artifact_hash": strategy_promotion_artifact_hash(strategy_artifact)}
    )

    for profile in metrics_summary.capital_bucket_profiles:
        sample_artifacts.append(
            build_sample_size_survival_artifact(
                SampleSizeSurvivalBuildInput(
                    run_id=run_manifest.run_id,
                    scope="capital_bucket",
                    scope_id=str(profile.capital_bucket),
                    raw_candidate_count=profile.candidate_count,
                    after_hard_filters_count=(
                        None
                        if profile.candidate_count is None or profile.hard_blocked_count is None
                        else profile.candidate_count - profile.hard_blocked_count
                    ),
                    selected_count=profile.selected_count,
                    executed_count=profile.executed_count,
                    reduced_count=profile.reduced_count,
                    no_fill_count=profile.no_fill_count,
                    min_required_candidates=min_required_candidates,
                    min_required_executions=min_required_executions,
                    min_required_days=min_required_days,
                    sample_period_start=sample_start,
                    sample_period_end=sample_end,
                    sample_days=sample_days,
                    input_data_hash=input_data_hash,
                    method_version_hash=method_version_hash,
                    created_at=created_at,
                    expires_at=expires_at,
                )
            )
        )

    return ReplayPromotionArtifactBundle(
        engine_promotion_artifacts=tuple(engine_artifacts),
        pair_promotion_artifacts=tuple(pair_artifacts),
        strategy_promotion_artifacts=(strategy_artifact,),
        sample_size_survival_artifacts=tuple(sample_artifacts),
    )


def discover_promotion_artifact_refs(export_dir: Path) -> tuple[str, ...]:
    """Return sorted standalone promotion/sample-size artifact refs from an export dir."""

    roots = (
        export_dir / "engine_promotion",
        export_dir / "pair_promotion",
        export_dir / "strategy_promotion",
        export_dir / "sample_size_survival",
    )
    refs: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        refs.extend(str(path.resolve()) for path in sorted(root.rglob("*.json")))
    return tuple(dict.fromkeys(refs))


__all__ = [
    "ReplayPromotionArtifactBundle",
    "SampleSizeSurvivalBuildInput",
    "build_replay_promotion_artifact_bundle",
    "build_sample_size_survival_artifact",
    "discover_promotion_artifact_refs",
]
