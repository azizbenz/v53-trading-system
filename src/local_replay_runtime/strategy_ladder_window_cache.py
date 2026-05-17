"""Deterministic replay-window cache for Strategy Ladder raw extraction."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


class StrategyLadderWindowCacheMetrics(BaseModel, frozen=True):
    """Compact counters for replay-window cache usage."""

    schema_version: str = Field(default="v1", min_length=1)
    status: str = "WINDOW_CACHE_NOT_PROVEN"
    cache_hit_count: int = Field(default=0, ge=0)
    cache_miss_count: int = Field(default=0, ge=0)
    reused_extraction_count: int = Field(default=0, ge=0)
    invalid_cache_reject_count: int = Field(default=0, ge=0)
    hardlink_materialization_count: int = Field(default=0, ge=0)
    copy_fallback_count: int = Field(default=0, ge=0)
    cache_reuse_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


@dataclass(frozen=True)
class StrategyLadderWindowCacheRequest:
    """One cacheable replay-window extraction request."""

    source_type: str
    pair: str
    timeframe: str
    window_start_ms: int
    window_end_ms: int
    depth: int | None
    source_hash: str
    include_anchor_before_start: bool
    source_path: Path
    target_path: Path


@dataclass(frozen=True)
class StrategyLadderWindowCacheMiss:
    """One canonical cache miss that requires source extraction once."""

    cache_key: str
    request: StrategyLadderWindowCacheRequest
    cache_path: Path
    meta_path: Path
    target_paths: tuple[Path, ...]
    request_count: int


@dataclass(frozen=True)
class StrategyLadderWindowCacheHit:
    """One cache hit that can be materialized without new extraction."""

    cache_key: str
    cache_path: Path
    meta_path: Path
    row_count: int
    target_paths: tuple[Path, ...]
    request_count: int


@dataclass(frozen=True)
class StrategyLadderWindowCachePlan:
    """Planned hit/miss groups for one extraction batch."""

    hits: tuple[StrategyLadderWindowCacheHit, ...]
    misses: tuple[StrategyLadderWindowCacheMiss, ...]


class StrategyLadderWindowCache:
    """Filesystem-backed deterministic cache for identical extracted windows."""

    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root
        self._cache_hit_count = 0
        self._cache_miss_count = 0
        self._reused_extraction_count = 0
        self._invalid_cache_reject_count = 0
        self._hardlink_materialization_count = 0
        self._copy_fallback_count = 0
        self._total_request_count = 0

    def build_plan(
        self,
        requests: tuple[StrategyLadderWindowCacheRequest, ...],
    ) -> StrategyLadderWindowCachePlan:
        self._total_request_count += len(requests)
        grouped: dict[str, list[StrategyLadderWindowCacheRequest]] = {}
        for request in requests:
            if not request.source_hash:
                continue
            grouped.setdefault(self._cache_key(request), []).append(request)

        hits: list[StrategyLadderWindowCacheHit] = []
        misses: list[StrategyLadderWindowCacheMiss] = []
        for cache_key, group in grouped.items():
            canonical = group[0]
            cache_path = self._cache_root / canonical.source_type / canonical.pair / f"{cache_key}.jsonl"
            meta_path = cache_path.with_suffix(".meta.json")
            target_paths = tuple(
                dict.fromkeys(item.target_path.resolve() for item in group)
            )
            meta = self._load_valid_meta(
                meta_path=meta_path,
                cache_path=cache_path,
                expected_source_hash=canonical.source_hash,
            )
            if meta is not None:
                row_count = int(meta.get("row_count") or 0)
                self._cache_hit_count += 1
                self._reused_extraction_count += max(len(group) - 1, 0)
                hits.append(
                    StrategyLadderWindowCacheHit(
                        cache_key=cache_key,
                        cache_path=cache_path,
                        meta_path=meta_path,
                        row_count=row_count,
                        target_paths=target_paths,
                        request_count=len(group),
                    )
                )
                continue
            self._cache_miss_count += 1
            self._reused_extraction_count += max(len(group) - 1, 0)
            misses.append(
                StrategyLadderWindowCacheMiss(
                    cache_key=cache_key,
                    request=canonical,
                    cache_path=cache_path,
                    meta_path=meta_path,
                    target_paths=target_paths,
                    request_count=len(group),
                )
            )
        return StrategyLadderWindowCachePlan(hits=tuple(hits), misses=tuple(misses))

    def materialize_cache_hits(
        self,
        plan: StrategyLadderWindowCachePlan,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for hit in plan.hits:
            for target_path in hit.target_paths:
                self._copy_cache_to_target(hit.cache_path, target_path)
                counts[str(target_path.resolve())] = hit.row_count
        return counts

    def materialize_cache_misses(
        self,
        plan: StrategyLadderWindowCachePlan,
        *,
        extracted_counts: dict[str, int],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for miss in plan.misses:
            cache_path_key = str(miss.cache_path.resolve())
            row_count = int(extracted_counts.get(cache_path_key, 0))
            if row_count <= 0:
                self._delete_if_exists(miss.cache_path)
                self._delete_if_exists(miss.meta_path)
                continue
            miss.cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": "v1",
                "cache_key": miss.cache_key,
                "source_type": miss.request.source_type,
                "pair": miss.request.pair,
                "timeframe": miss.request.timeframe,
                "window_start_ms": miss.request.window_start_ms,
                "window_end_ms": miss.request.window_end_ms,
                "depth": miss.request.depth,
                "source_hash": miss.request.source_hash,
                "include_anchor_before_start": miss.request.include_anchor_before_start,
                "source_path": str(miss.request.source_path.resolve()),
                "row_count": row_count,
                "artifact_hash": deterministic_payload_hash(
                    {
                        "cache_key": miss.cache_key,
                        "source_hash": miss.request.source_hash,
                        "row_count": row_count,
                    }
                ),
            }
            atomic_write_json(miss.meta_path, payload, indent=2)
            for target_path in miss.target_paths:
                self._copy_cache_to_target(miss.cache_path, target_path)
                counts[str(target_path.resolve())] = row_count
        return counts

    def metrics_snapshot(self) -> StrategyLadderWindowCacheMetrics:
        reuse_ratio = (
            round(self._reused_extraction_count / self._total_request_count, 6)
            if self._total_request_count > 0
            else None
        )
        status = "WINDOW_CACHE_NOT_PROVEN"
        if self._cache_hit_count > 0 or self._cache_miss_count > 0:
            status = "WINDOW_CACHE_READY"
        return StrategyLadderWindowCacheMetrics(
            status=status,
            cache_hit_count=self._cache_hit_count,
            cache_miss_count=self._cache_miss_count,
            reused_extraction_count=self._reused_extraction_count,
            invalid_cache_reject_count=self._invalid_cache_reject_count,
            hardlink_materialization_count=self._hardlink_materialization_count,
            copy_fallback_count=self._copy_fallback_count,
            cache_reuse_ratio=reuse_ratio,
        )

    def _cache_key(self, request: StrategyLadderWindowCacheRequest) -> str:
        payload = {
            "source_type": request.source_type,
            "pair": request.pair,
            "timeframe": request.timeframe,
            "window_start_ms": request.window_start_ms,
            "window_end_ms": request.window_end_ms,
            "depth": request.depth,
            "source_hash": request.source_hash,
            "include_anchor_before_start": request.include_anchor_before_start,
        }
        return deterministic_payload_hash(payload)

    def _load_valid_meta(
        self,
        *,
        meta_path: Path,
        cache_path: Path,
        expected_source_hash: str,
    ) -> dict[str, object] | None:
        if not cache_path.is_file() or not meta_path.is_file():
            return None
        try:
            payload = json_load(meta_path)
        except OSError:
            self._invalid_cache_reject_count += 1
            return None
        if str(payload.get("source_hash") or "") != expected_source_hash:
            self._invalid_cache_reject_count += 1
            return None
        row_count = int(payload.get("row_count") or 0)
        if row_count <= 0:
            self._invalid_cache_reject_count += 1
            return None
        return payload

    def _copy_cache_to_target(self, cache_path: Path, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self._delete_if_exists(target_path)
        try:
            os.link(cache_path, target_path)
            self._hardlink_materialization_count += 1
            return
        except OSError:
            shutil.copyfile(cache_path, target_path)
            self._copy_fallback_count += 1

    @staticmethod
    def _delete_if_exists(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            return


def json_load(path: Path) -> dict[str, object]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


__all__ = [
    "StrategyLadderWindowCache",
    "StrategyLadderWindowCacheMetrics",
    "StrategyLadderWindowCachePlan",
    "StrategyLadderWindowCacheRequest",
]
