from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
)


@dataclass(frozen=True)
class CandidateCountSemantics:
    total_candidate_count: int
    unique_candidate_count: int
    base_event_count: int
    per_engine_candidate_count: int | None
    engine_native_candidate_count: int
    proxy_candidate_count: int
    engine_count: int
    candidate_source_status: str


@dataclass(frozen=True)
class ReplayCountSemantics:
    replay_record_count: int
    evaluation_record_count: int
    promotion_record_count: int
    capital_bucket_record_count: int
    replay_expansion_factor: float | None
    replay_expansion_axis: str


def _candidate_identity(
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


def _base_event_identity(
    candidate: StrategyLadderCandidateEvent,
) -> tuple[int, str, str]:
    return (
        candidate.resolved_timestamp_ms,
        candidate.pair,
        candidate.timeframe or "",
    )


def summarize_candidate_count_semantics(
    candidate_events: tuple[StrategyLadderCandidateEvent, ...],
) -> CandidateCountSemantics:
    if not candidate_events:
        return CandidateCountSemantics(
            total_candidate_count=0,
            unique_candidate_count=0,
            base_event_count=0,
            per_engine_candidate_count=None,
            engine_native_candidate_count=0,
            proxy_candidate_count=0,
            engine_count=0,
            candidate_source_status="CANDIDATE_SOURCE_NOT_PROVEN",
        )

    unique_candidates = {
        _candidate_identity(candidate): candidate for candidate in candidate_events
    }
    base_events = {
        _base_event_identity(candidate)
        for candidate in unique_candidates.values()
    }
    counts_by_engine = Counter(
        candidate.engine_id for candidate in unique_candidates.values() if candidate.engine_id
    )
    engine_counts = tuple(counts_by_engine.values())
    per_engine_candidate_count = (
        engine_counts[0]
        if engine_counts and len(set(engine_counts)) == 1
        else None
    )
    sources = {
        str(candidate.candidate_source or "").strip()
        for candidate in unique_candidates.values()
        if str(candidate.candidate_source or "").strip()
    }
    engine_native_candidate_count = sum(
        1
        for candidate in unique_candidates.values()
        if candidate.candidate_source == "ENGINE_NATIVE"
    )
    proxy_candidate_count = sum(
        1
        for candidate in unique_candidates.values()
        if candidate.candidate_source == "COMPAT_FEATURE_DISCOVERY"
    )
    if not sources:
        candidate_source_status = "CANDIDATE_SOURCE_NOT_PROVEN"
    elif sources == {"ENGINE_NATIVE"}:
        candidate_source_status = "CANDIDATE_SOURCE_ENGINE_NATIVE"
    elif sources == {"COMPAT_FEATURE_DISCOVERY"}:
        candidate_source_status = "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY"
    elif "COMPAT_FEATURE_DISCOVERY" in sources and "ENGINE_NATIVE" in sources:
        candidate_source_status = "CANDIDATE_SOURCE_MIXED_ENGINE_AND_PROXY"
    else:
        candidate_source_status = "CANDIDATE_SOURCE_FALLBACK_SYNTHETIC"
    return CandidateCountSemantics(
        total_candidate_count=len(candidate_events),
        unique_candidate_count=len(unique_candidates),
        base_event_count=len(base_events),
        per_engine_candidate_count=per_engine_candidate_count,
        engine_native_candidate_count=engine_native_candidate_count,
        proxy_candidate_count=proxy_candidate_count,
        engine_count=len(counts_by_engine),
        candidate_source_status=candidate_source_status,
    )


def summarize_replay_count_semantics(
    *,
    unique_candidate_count: int,
    bucket_results: tuple[StrategyLadderBucketReplayResult, ...],
) -> ReplayCountSemantics:
    replay_record_count = len(bucket_results)
    capital_bucket_record_count = replay_record_count
    evaluation_record_count = replay_record_count
    promotion_record_count = replay_record_count
    replay_expansion_factor: float | None = None
    replay_expansion_axis = ""
    if unique_candidate_count > 0 and replay_record_count > 0:
        replay_expansion_factor = round(replay_record_count / unique_candidate_count, 6)
        if replay_record_count > unique_candidate_count:
            capital_bucket_count = len(
                {
                    int(result.capital_bucket)
                    for result in bucket_results
                    if result.capital_bucket is not None
                }
            )
            replay_expansion_axis = (
                "capital_bucket" if capital_bucket_count > 1 else "evaluation_context"
            )
    return ReplayCountSemantics(
        replay_record_count=replay_record_count,
        evaluation_record_count=evaluation_record_count,
        promotion_record_count=promotion_record_count,
        capital_bucket_record_count=capital_bucket_record_count,
        replay_expansion_factor=replay_expansion_factor,
        replay_expansion_axis=replay_expansion_axis,
    )

