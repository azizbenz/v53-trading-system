"""Canonical replay performance profiling artifacts for Strategy Ladder."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, process_time
from typing import Iterator

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash
from local_replay_runtime.strategy_ladder_window_cache import (
    StrategyLadderWindowCacheMetrics,
)
from local_replay_runtime.strategy_ladder_window_index import (
    StrategyLadderWindowLookupMetrics,
)


class StrategyLadderReplayPerformancePhase(BaseModel, frozen=True):
    """One measured replay sub-phase."""

    phase_name: str = Field(..., min_length=1)
    status: str = Field(default="NOT_RUN", min_length=1)
    wall_time_s: float = Field(default=0.0, ge=0.0)
    cpu_time_s: float = Field(default=0.0, ge=0.0)
    io_wait_estimate_s: float = Field(default=0.0, ge=0.0)
    rows_processed: int = Field(default=0, ge=0)
    files_scanned: int = Field(default=0, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    replay_record_count: int = Field(default=0, ge=0)
    counters: dict[str, int | float | str] = Field(default_factory=dict)


class StrategyLadderReplayPerformanceHotspot(BaseModel, frozen=True):
    """Simple hotspot projection used in markdown + cockpit."""

    function_name: str = Field(..., min_length=1)
    wall_time_s: float = Field(default=0.0, ge=0.0)
    cpu_time_s: float = Field(default=0.0, ge=0.0)
    io_wait_estimate_s: float = Field(default=0.0, ge=0.0)


class StrategyLadderReplayPerformanceProfile(BaseModel, frozen=True):
    """Top-level artifact written by the canonical replay profiler."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = Field(..., min_length=1)
    status: str = "REPLAY_PERFORMANCE_PROFILE_READY"
    created_at: datetime
    total_wall_time_s: float = Field(default=0.0, ge=0.0)
    total_cpu_time_s: float = Field(default=0.0, ge=0.0)
    total_io_wait_estimate_s: float = Field(default=0.0, ge=0.0)
    candidate_count: int = Field(default=0, ge=0)
    replay_record_count: int = Field(default=0, ge=0)
    rows_processed: int = Field(default=0, ge=0)
    files_scanned: int = Field(default=0, ge=0)
    phases: tuple[StrategyLadderReplayPerformancePhase, ...] = ()
    hottest_functions: tuple[StrategyLadderReplayPerformanceHotspot, ...] = ()
    repeated_lookups: dict[str, int] = Field(default_factory=dict)
    duplicate_scans: dict[str, int] = Field(default_factory=dict)
    indexed_lookup_metrics: dict[str, int | float | str | None] = Field(default_factory=dict)
    window_cache_metrics: dict[str, int | float | str | None] = Field(default_factory=dict)
    bottleneck_summary: tuple[str, ...] = ()
    parquet_fast_path_status: str = "PARQUET_REPLAY_NOT_PROVEN"
    replay_workers_used: int = Field(default=0, ge=0)
    replay_parallelism_ratio: float | None = Field(default=None, ge=0.0)
    replay_cpu_utilization: float | None = Field(default=None, ge=0.0)
    replay_queue_wait_time_s: float = Field(default=0.0, ge=0.0)
    research_fast_debug_mode_status: str = "RESEARCH_FAST_DEBUG_MODE_NOT_REQUESTED"
    shared_payload_build_seconds: float = Field(default=0.0, ge=0.0)
    engine_dataset_build_seconds: float = Field(default=0.0, ge=0.0)
    evaluate_replay_execution_seconds: float = Field(default=0.0, ge=0.0)
    replay_evidence_seconds: float = Field(default=0.0, ge=0.0)
    by_bucket_write_seconds: float = Field(default=0.0, ge=0.0)
    candidate_wrapper_write_seconds: float = Field(default=0.0, ge=0.0)
    cache_hits_book_state: int = Field(default=0, ge=0)
    cache_misses_book_state: int = Field(default=0, ge=0)
    cache_hits_ohlcv: int = Field(default=0, ge=0)
    cache_misses_ohlcv: int = Field(default=0, ge=0)
    artifact_hash: str | None = None


class StrategyLadderReplayPerformanceProfiler:
    """Mutable collector used by the Strategy Ladder runner."""

    def __init__(self, *, run_id: str) -> None:
        self._run_id = run_id
        self._created_at = datetime.now(tz=UTC)
        self._started_wall = perf_counter()
        self._started_cpu = process_time()
        self._phase_data: dict[str, dict[str, object]] = defaultdict(
            lambda: {
                "phase_name": "",
                "status": "NOT_RUN",
                "wall_time_s": 0.0,
                "cpu_time_s": 0.0,
                "io_wait_estimate_s": 0.0,
                "rows_processed": 0,
                "files_scanned": 0,
                "candidate_count": 0,
                "replay_record_count": 0,
                "counters": {},
            }
        )
        self._indexed_lookup_metrics = StrategyLadderWindowLookupMetrics()
        self._window_cache_metrics = StrategyLadderWindowCacheMetrics()
        self._candidate_count = 0
        self._replay_record_count = 0
        self._rows_processed = 0
        self._files_scanned = 0
        self._replay_subtimers: dict[str, int | float] = {
            "shared_payload_build_seconds": 0.0,
            "engine_dataset_build_seconds": 0.0,
            "evaluate_replay_execution_seconds": 0.0,
            "replay_evidence_seconds": 0.0,
            "by_bucket_write_seconds": 0.0,
            "candidate_wrapper_write_seconds": 0.0,
            "cache_hits_book_state": 0,
            "cache_misses_book_state": 0,
            "cache_hits_ohlcv": 0,
            "cache_misses_ohlcv": 0,
        }

    @contextmanager
    def phase(
        self,
        phase_name: str,
        *,
        status: str = "OK",
        rows_processed: int = 0,
        files_scanned: int = 0,
        candidate_count: int = 0,
        replay_record_count: int = 0,
        counters: dict[str, int | float | str] | None = None,
    ) -> Iterator[None]:
        started_wall = perf_counter()
        started_cpu = process_time()
        try:
            yield
        finally:
            wall_time_s = perf_counter() - started_wall
            cpu_time_s = process_time() - started_cpu
            self.record_phase(
                phase_name,
                status=status,
                wall_time_s=wall_time_s,
                cpu_time_s=cpu_time_s,
                rows_processed=rows_processed,
                files_scanned=files_scanned,
                candidate_count=candidate_count,
                replay_record_count=replay_record_count,
                counters=counters or {},
            )

    def record_phase(
        self,
        phase_name: str,
        *,
        status: str,
        wall_time_s: float,
        cpu_time_s: float,
        rows_processed: int = 0,
        files_scanned: int = 0,
        candidate_count: int = 0,
        replay_record_count: int = 0,
        counters: dict[str, int | float | str] | None = None,
    ) -> None:
        data = self._phase_data[phase_name]
        existing_counters = dict(data["counters"])
        if counters:
            existing_counters.update(counters)
        data.update(
            {
                "phase_name": phase_name,
                "status": status,
                "wall_time_s": float(data["wall_time_s"]) + wall_time_s,
                "cpu_time_s": float(data["cpu_time_s"]) + cpu_time_s,
                "io_wait_estimate_s": float(data["io_wait_estimate_s"])
                + max(wall_time_s - cpu_time_s, 0.0),
                "rows_processed": int(data["rows_processed"]) + rows_processed,
                "files_scanned": int(data["files_scanned"]) + files_scanned,
                "candidate_count": max(int(data["candidate_count"]), candidate_count),
                "replay_record_count": max(
                    int(data["replay_record_count"]),
                    replay_record_count,
                ),
                "counters": existing_counters,
            }
        )
        self._rows_processed += max(rows_processed, 0)
        self._files_scanned += max(files_scanned, 0)

    def observe_window_index_metrics(self, metrics: StrategyLadderWindowLookupMetrics) -> None:
        self._indexed_lookup_metrics = metrics
        self.record_phase(
            "silver_index_lookup",
            status=metrics.status,
            wall_time_s=float(metrics.silver_index_lookup_wall_time_s),
            cpu_time_s=max(
                float(metrics.silver_index_lookup_wall_time_s)
                - float(metrics.filesystem_scan_wall_time_s),
                0.0,
            ),
            files_scanned=int(metrics.files_scanned),
            counters={
                "query_count": int(metrics.query_count),
                "indexed_lookup_hit_count": int(metrics.indexed_lookup_hit_count),
                "index_lookup_miss_count": int(metrics.index_lookup_miss_count),
                "repeated_lookup_count": int(metrics.repeated_lookup_count),
                "query_cache_hit_count": int(metrics.query_cache_hit_count),
            },
        )
        self.record_phase(
            "filesystem_scan",
            status=(
                "FALLBACK_SCAN_USED" if metrics.fallback_scan_count > 0 else metrics.status
            ),
            wall_time_s=float(metrics.filesystem_scan_wall_time_s),
            cpu_time_s=max(float(metrics.filesystem_scan_wall_time_s) * 0.2, 0.0),
            files_scanned=int(metrics.files_scanned),
            counters={
                "fallback_scan_count": int(metrics.fallback_scan_count),
                "duplicate_scan_detected_count": int(
                    metrics.duplicate_scan_detected_count
                ),
                "candidate_entries_evaluated": int(metrics.candidate_entries_evaluated),
            },
        )

    def observe_window_cache_metrics(self, metrics: StrategyLadderWindowCacheMetrics) -> None:
        self._window_cache_metrics = metrics

    def observe_replay_subtimers(
        self,
        *,
        shared_payload_build_seconds: float = 0.0,
        engine_dataset_build_seconds: float = 0.0,
        evaluate_replay_execution_seconds: float = 0.0,
        replay_evidence_seconds: float = 0.0,
        by_bucket_write_seconds: float = 0.0,
        candidate_wrapper_write_seconds: float = 0.0,
        cache_hits_book_state: int = 0,
        cache_misses_book_state: int = 0,
        cache_hits_ohlcv: int = 0,
        cache_misses_ohlcv: int = 0,
    ) -> None:
        self._replay_subtimers.update(
            {
                "shared_payload_build_seconds": round(
                    max(shared_payload_build_seconds, 0.0),
                    6,
                ),
                "engine_dataset_build_seconds": round(
                    max(engine_dataset_build_seconds, 0.0),
                    6,
                ),
                "evaluate_replay_execution_seconds": round(
                    max(evaluate_replay_execution_seconds, 0.0),
                    6,
                ),
                "replay_evidence_seconds": round(max(replay_evidence_seconds, 0.0), 6),
                "by_bucket_write_seconds": round(max(by_bucket_write_seconds, 0.0), 6),
                "candidate_wrapper_write_seconds": round(
                    max(candidate_wrapper_write_seconds, 0.0),
                    6,
                ),
                "cache_hits_book_state": max(cache_hits_book_state, 0),
                "cache_misses_book_state": max(cache_misses_book_state, 0),
                "cache_hits_ohlcv": max(cache_hits_ohlcv, 0),
                "cache_misses_ohlcv": max(cache_misses_ohlcv, 0),
            }
        )

    def finalize_counts(
        self,
        *,
        candidate_count: int,
        replay_record_count: int,
    ) -> None:
        self._candidate_count = candidate_count
        self._replay_record_count = replay_record_count

    def write(self, output_dir: Path) -> StrategyLadderReplayPerformanceProfile:
        output_dir.mkdir(parents=True, exist_ok=True)
        phases = tuple(
            StrategyLadderReplayPerformancePhase.model_validate(payload)
            for _, payload in sorted(
                self._phase_data.items(),
                key=lambda item: item[1]["phase_name"],
            )
        )
        total_wall_time_s = round(max(perf_counter() - self._started_wall, 0.0), 6)
        total_cpu_time_s = round(max(process_time() - self._started_cpu, 0.0), 6)
        total_io_wait_estimate_s = round(
            max(total_wall_time_s - total_cpu_time_s, 0.0),
            6,
        )
        hotspots = tuple(
            StrategyLadderReplayPerformanceHotspot(
                function_name=phase.phase_name,
                wall_time_s=phase.wall_time_s,
                cpu_time_s=phase.cpu_time_s,
                io_wait_estimate_s=phase.io_wait_estimate_s,
            )
            for phase in sorted(phases, key=lambda item: item.wall_time_s, reverse=True)[:5]
        )
        bottlenecks = tuple(
            f"{item.function_name}:{round(item.wall_time_s, 3)}s"
            for item in hotspots[:3]
        )
        indexed_lookup_payload = self._indexed_lookup_metrics.model_dump(mode="json")
        window_cache_payload = self._window_cache_metrics.model_dump(mode="json")
        profile = StrategyLadderReplayPerformanceProfile(
            run_id=self._run_id,
            created_at=self._created_at,
            total_wall_time_s=total_wall_time_s,
            total_cpu_time_s=total_cpu_time_s,
            total_io_wait_estimate_s=total_io_wait_estimate_s,
            candidate_count=self._candidate_count,
            replay_record_count=self._replay_record_count,
            rows_processed=self._rows_processed,
            files_scanned=max(
                self._files_scanned,
                int(indexed_lookup_payload.get("files_scanned") or 0),
            ),
            phases=phases,
            hottest_functions=hotspots,
            repeated_lookups={
                "window_index_repeated_lookup_count": int(
                    indexed_lookup_payload.get("repeated_lookup_count") or 0
                ),
                "window_index_query_cache_hit_count": int(
                    indexed_lookup_payload.get("query_cache_hit_count") or 0
                ),
            },
            duplicate_scans={
                "window_index_duplicate_scan_detected_count": int(
                    indexed_lookup_payload.get("duplicate_scan_detected_count") or 0
                )
            },
            indexed_lookup_metrics=indexed_lookup_payload,
            window_cache_metrics=window_cache_payload,
            bottleneck_summary=bottlenecks,
            shared_payload_build_seconds=float(
                self._replay_subtimers["shared_payload_build_seconds"]
            ),
            engine_dataset_build_seconds=float(
                self._replay_subtimers["engine_dataset_build_seconds"]
            ),
            evaluate_replay_execution_seconds=float(
                self._replay_subtimers["evaluate_replay_execution_seconds"]
            ),
            replay_evidence_seconds=float(
                self._replay_subtimers["replay_evidence_seconds"]
            ),
            by_bucket_write_seconds=float(
                self._replay_subtimers["by_bucket_write_seconds"]
            ),
            candidate_wrapper_write_seconds=float(
                self._replay_subtimers["candidate_wrapper_write_seconds"]
            ),
            cache_hits_book_state=int(self._replay_subtimers["cache_hits_book_state"]),
            cache_misses_book_state=int(self._replay_subtimers["cache_misses_book_state"]),
            cache_hits_ohlcv=int(self._replay_subtimers["cache_hits_ohlcv"]),
            cache_misses_ohlcv=int(self._replay_subtimers["cache_misses_ohlcv"]),
        )
        profile = profile.model_copy(
            update={"artifact_hash": deterministic_payload_hash(profile.model_dump(mode="json"))}
        )
        atomic_write_json(
            output_dir / "replay_performance_profile.json",
            profile.model_dump(mode="json"),
            indent=2,
        )
        atomic_write_text(
            output_dir / "replay_performance_profile.md",
            self._format_markdown(profile),
            encoding="utf-8",
        )
        return profile

    @staticmethod
    def _format_markdown(profile: StrategyLadderReplayPerformanceProfile) -> str:
        lines = [
            "# Replay Performance Profile",
            "",
            f"- run_id: {profile.run_id}",
            f"- status: {profile.status}",
            f"- total_wall_time_s: {profile.total_wall_time_s}",
            f"- total_cpu_time_s: {profile.total_cpu_time_s}",
            f"- total_io_wait_estimate_s: {profile.total_io_wait_estimate_s}",
            f"- candidate_count: {profile.candidate_count}",
            f"- replay_record_count: {profile.replay_record_count}",
            f"- rows_processed: {profile.rows_processed}",
            f"- files_scanned: {profile.files_scanned}",
            f"- parquet_fast_path_status: {profile.parquet_fast_path_status}",
            f"- research_fast_debug_mode_status: {profile.research_fast_debug_mode_status}",
            f"- shared_payload_build_seconds: {profile.shared_payload_build_seconds}",
            f"- engine_dataset_build_seconds: {profile.engine_dataset_build_seconds}",
            f"- evaluate_replay_execution_seconds: {profile.evaluate_replay_execution_seconds}",
            f"- replay_evidence_seconds: {profile.replay_evidence_seconds}",
            f"- by_bucket_write_seconds: {profile.by_bucket_write_seconds}",
            f"- candidate_wrapper_write_seconds: {profile.candidate_wrapper_write_seconds}",
            f"- cache_hits_book_state: {profile.cache_hits_book_state}",
            f"- cache_misses_book_state: {profile.cache_misses_book_state}",
            f"- cache_hits_ohlcv: {profile.cache_hits_ohlcv}",
            f"- cache_misses_ohlcv: {profile.cache_misses_ohlcv}",
            "",
            "## Bottlenecks",
        ]
        if profile.bottleneck_summary:
            lines.extend(f"- {item}" for item in profile.bottleneck_summary)
        else:
            lines.append("- none")
        lines.extend(
            [
                "",
                "## Phases",
            ]
        )
        if not profile.phases:
            lines.append("- none")
        else:
            for phase in profile.phases:
                lines.extend(
                    [
                        f"### {phase.phase_name}",
                        f"- status: {phase.status}",
                        f"- wall_time_s: {phase.wall_time_s}",
                        f"- cpu_time_s: {phase.cpu_time_s}",
                        f"- io_wait_estimate_s: {phase.io_wait_estimate_s}",
                        f"- rows_processed: {phase.rows_processed}",
                        f"- files_scanned: {phase.files_scanned}",
                        f"- candidate_count: {phase.candidate_count}",
                        f"- replay_record_count: {phase.replay_record_count}",
                    ]
                )
                if phase.counters:
                    for key, value in sorted(phase.counters.items()):
                        lines.append(f"- {key}: {value}")
                lines.append("")
        lines.extend(
            [
                "## Indexed Lookup",
                f"- status: {profile.indexed_lookup_metrics.get('status', 'INDEX_LOOKUP_NOT_PROVEN')}",
                f"- indexed_lookup_hit_rate: {profile.indexed_lookup_metrics.get('indexed_lookup_hit_rate')}",
                f"- query_count: {profile.indexed_lookup_metrics.get('query_count', 0)}",
                f"- repeated_lookup_count: {profile.indexed_lookup_metrics.get('repeated_lookup_count', 0)}",
                "",
                "## Window Cache",
                f"- status: {profile.window_cache_metrics.get('status', 'WINDOW_CACHE_NOT_PROVEN')}",
                f"- cache_hit_count: {profile.window_cache_metrics.get('cache_hit_count', 0)}",
                f"- cache_miss_count: {profile.window_cache_metrics.get('cache_miss_count', 0)}",
                f"- cache_reuse_ratio: {profile.window_cache_metrics.get('cache_reuse_ratio')}",
                "",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "StrategyLadderReplayPerformancePhase",
    "StrategyLadderReplayPerformanceProfile",
    "StrategyLadderReplayPerformanceProfiler",
]
