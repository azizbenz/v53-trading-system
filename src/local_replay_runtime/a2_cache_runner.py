"""Drop-in cached wrapper around `run_strategy_ladder_data_factory`.

This module is the SAFE integration shim for the A2 content-addressable cache.
Rather than patching the 4000+ line `strategy_ladder_data_factory.py`
in-place — which is high-risk while Codex is actively shipping heartbeat /
eviction patches there — we expose a parallel entry point that:

  1. Builds the canonical `A2CacheKey` from the request.
  2. Looks the cache up.
  3. **Cache hit**: restores silver/gold/reports + deserializes the cached
     `StrategyLadderDataFactoryResult`. Returns in seconds.
  4. **Cache miss**: calls the original `run_strategy_ladder_data_factory`
     unchanged, then populates the cache from the produced run directory so
     the next call with identical inputs is a hit.

Callers (`scripts/run_strategy_ladder_data_factory.py`,
`strategy_ladder_first_controlled_run`, the cockpit launcher, etc.) opt in
by importing `run_strategy_ladder_data_factory_cached` instead of the raw
function. The trading-decision semantics, engines, thresholds, gates, labels
and outputs are bit-identical to the un-cached path.

Cache is **bypassed automatically** for control-flow modes that don't
produce a stable A2 result:

  * `request.dry_run = True`
  * `request.resume = True`
  * `request.debug_storage_override = True`
  * env `V53_A2_CACHE=0`
  * explicit `cache_enabled=False` argument

Environment variables:

  * `V53_A2_CACHE`     — `1` (default) enables, `0` disables.
  * `V53_A2_CACHE_BASE`— defaults to `L:/cache/a2`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from local_replay_runtime.a2_cache import (
    A2_CACHE_HIT_STATUS,
    A2_CACHE_POPULATED_STATUS,
    A2CacheEntry,
    build_a2_cache_key,
    compute_input_hash,
    lookup_a2_cache,
    populate_a2_cache,
    read_cached_result_blob,
    restore_a2_from_cache,
)
from local_replay_runtime.strategy_ladder_data_factory import (
    run_strategy_ladder_data_factory,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
    StrategyLadderDataFactoryResult,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------


DEFAULT_CACHE_BASE = Path("L:/cache/a2")
ENV_CACHE_BASE = "V53_A2_CACHE_BASE"
ENV_CACHE_ENABLED = "V53_A2_CACHE"


def _resolve_cache_base(explicit: Path | None) -> Path:
    if explicit is not None:
        return Path(explicit)
    env_value = os.environ.get(ENV_CACHE_BASE, "").strip()
    if env_value:
        return Path(env_value)
    return DEFAULT_CACHE_BASE


def _resolve_cache_enabled(explicit: bool | None) -> bool:
    if explicit is not None:
        return bool(explicit)
    env_value = os.environ.get(ENV_CACHE_ENABLED, "").strip()
    if not env_value:
        return True
    return env_value not in {"0", "false", "False", "FALSE", "off", "OFF"}


def _request_bypasses_cache(request: StrategyLadderDataFactoryRequest) -> bool:
    """Return True for control-flow modes that should never touch the cache."""

    if request.dry_run:
        return True
    if request.resume:
        return True
    if getattr(request, "debug_storage_override", False):
        return True
    return False


def _build_cache_key_from_request(request: StrategyLadderDataFactoryRequest):
    return build_a2_cache_key(
        raw_roots=tuple(Path(p) for p in request.raw_roots),
        historical_metadata_root=request.historical_metadata_root,
        pairs=request.pairs,
        engines=request.engines,
        timeframes=request.timeframes,
        feature_names=request.feature_names,
        start=request.start,
        end=request.end,
        data_types=request.data_types,
        compression=request.compression,
        storage_format=request.storage_format,
        max_gold_feature_rows=request.max_gold_feature_rows,
        use_measured_economic_provenance=request.use_measured_economic_provenance,
    )


def _result_from_cache_hit(
    *,
    cache_base: Path,
    cache_hit_entry: A2CacheEntry,
    request: StrategyLadderDataFactoryRequest,
) -> StrategyLadderDataFactoryResult | None:
    """Restore A2 artefacts on disk + deserialize cached result.

    Returns None if the cache entry is missing the serialized result blob —
    callers must then fall back to the un-cached A2 path.
    """

    report_root = Path(request.input_root).resolve()
    restore_a2_from_cache(
        entry=cache_hit_entry,
        cache_base=cache_base,
        target_silver_root=Path(request.silver_root),
        target_gold_root=Path(request.gold_root),
        target_progress_report_path=report_root / "a2_gold_progress_report.json",
        target_report_dir=report_root,
    )
    blob = read_cached_result_blob(cache_base, cache_hit_entry)
    if not blob:
        return None
    return StrategyLadderDataFactoryResult.model_validate_json(blob)


def run_strategy_ladder_data_factory_cached(
    request: StrategyLadderDataFactoryRequest,
    *,
    cache_base: Path | None = None,
    cache_enabled: bool | None = None,
) -> StrategyLadderDataFactoryResult:
    """Cached drop-in for `run_strategy_ladder_data_factory`.

    Returns a `StrategyLadderDataFactoryResult` byte-identical to the one
    the un-cached path would have produced for the same request. On a cache
    hit silver+gold+reports are restored from disk and the typed result is
    deserialized from the cached blob. On a cache miss the original A2 is
    executed and the cache is populated from the produced run directory.
    """

    resolved_cache_base = _resolve_cache_base(cache_base)
    resolved_cache_enabled = _resolve_cache_enabled(cache_enabled)

    if not resolved_cache_enabled or _request_bypasses_cache(request):
        return run_strategy_ladder_data_factory(request)

    try:
        cache_key = _build_cache_key_from_request(request)
        cache_input_hash = compute_input_hash(cache_key)
        cache_hit_entry = lookup_a2_cache(resolved_cache_base, cache_input_hash)
    except Exception as exc:  # noqa: BLE001 - cache lookup must never break A2
        logger.warning(
            "A2 cache lookup failed for run_id=%s: %s — falling back to uncached A2",
            request.run_id,
            exc,
        )
        return run_strategy_ladder_data_factory(request)

    if cache_hit_entry is not None:
        try:
            result = _result_from_cache_hit(
                cache_base=resolved_cache_base,
                cache_hit_entry=cache_hit_entry,
                request=request,
            )
        except Exception as exc:  # noqa: BLE001 - restore must never poison A2
            logger.warning(
                "A2 cache restore failed for input_hash=%s: %s — falling back to uncached A2",
                cache_input_hash,
                exc,
            )
            result = None
        if result is not None:
            logger.info(
                "A2 %s for input_hash=%s (source_run_id=%s prod_safety=%s)",
                A2_CACHE_HIT_STATUS,
                cache_input_hash,
                cache_hit_entry.source_run_id,
                cache_hit_entry.prod_safety_status,
            )
            return result

    # Cache miss (or hit-restore failed) — run A2 normally.
    result = run_strategy_ladder_data_factory(request)

    # Populate the cache so the next run with identical inputs is a hit.
    try:
        report_root = Path(request.input_root).resolve()
        progress_report_path = report_root / "a2_gold_progress_report.json"
        populated_entry = populate_a2_cache(
            cache_base=resolved_cache_base,
            key=cache_key,
            source_run_id=request.run_id,
            source_silver_root=Path(request.silver_root),
            source_gold_root=Path(request.gold_root),
            source_progress_report_path=(
                progress_report_path if progress_report_path.is_file() else None
            ),
            counters_snapshot={},
            gold_feature_row_count=int(
                getattr(result.gold_feature_manifest, "feature_row_count", 0) or 0
            ),
            silver_entry_count=int(len(result.silver_index)),
            source_report_dir=report_root,
            result_blob_json=result.model_dump_json(),
        )
        logger.info(
            "A2 %s for input_hash=%s prod_safety=%s",
            A2_CACHE_POPULATED_STATUS,
            populated_entry.input_hash,
            populated_entry.prod_safety_status,
        )
    except Exception as exc:  # noqa: BLE001 - cache populate must never break A2
        logger.warning(
            "A2 cache populate failed for run_id=%s: %s — uncached result still returned",
            request.run_id,
            exc,
        )
    return result


__all__ = [
    "DEFAULT_CACHE_BASE",
    "ENV_CACHE_BASE",
    "ENV_CACHE_ENABLED",
    "run_strategy_ladder_data_factory_cached",
]
