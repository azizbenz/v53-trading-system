"""Canonical raw-source resolution for Patch 6 Strategy Ladder data inputs."""

from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderRawSource,
    StrategyLadderRawSourceReport,
    finalize_hashed_model,
)


def _infer_data_types_from_root(root: Path) -> tuple[tuple[str, ...], str]:
    lowered_parts = {part.lower() for part in root.parts}
    inferred: list[str] = []
    if (
        {"orderbook", "depth"} & lowered_parts
        or any("orderbook" in part or "depth" in part or "book" in part for part in lowered_parts)
    ):
        inferred.append("orderbook")
    if {"klines", "kline", "ohlcv", "candles"} & lowered_parts:
        inferred.append("klines")
    if {"trades", "trade", "aggtrades"} & lowered_parts:
        inferred.append("trades")
    if {"metadata", "filters", "symbol_filters"} & lowered_parts:
        inferred.append("metadata")
    if inferred:
        return tuple(dict.fromkeys(inferred)), "RAW_SOURCE_TYPE_INFERRED"
    return (), "RAW_SOURCE_TYPE_AMBIGUOUS"


def normalize_raw_root_inputs(
    *,
    raw_root: Path | None = None,
    raw_roots: tuple[Path, ...] = (),
    raw_roots_csv: str = "",
) -> tuple[Path, ...]:
    """Normalize one or many raw-root inputs into a stable deduplicated tuple."""

    values: list[Path] = []
    if raw_root is not None:
        values.append(raw_root)
    values.extend(raw_roots)
    if raw_roots_csv.strip():
        values.extend(Path(part.strip()) for part in raw_roots_csv.split(",") if part.strip())
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in values:
        resolved = Path(path).expanduser().resolve()
        normalized = str(resolved).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(resolved)
    return tuple(deduped)


def load_raw_source_manifest(path: Path) -> tuple[StrategyLadderRawSource, ...]:
    """Load one raw-source manifest file."""

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("raw source manifest must be an object")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("raw source manifest must contain a sources array")
    return tuple(
        StrategyLadderRawSource.model_validate(item)
        for item in sources
        if isinstance(item, dict)
    )


def resolve_strategy_ladder_raw_sources(
    *,
    raw_root: Path | None = None,
    raw_roots: tuple[Path, ...] = (),
    raw_roots_csv: str = "",
    raw_source_manifest_path: Path | None = None,
    dry_run: bool = False,
) -> StrategyLadderRawSourceReport:
    """Resolve and validate all configured raw sources for Patch 6."""

    normalized_roots = normalize_raw_root_inputs(
        raw_root=raw_root,
        raw_roots=raw_roots,
        raw_roots_csv=raw_roots_csv,
    )
    manifest_sources: tuple[StrategyLadderRawSource, ...] = ()
    blockers: list[str] = []
    if raw_source_manifest_path is not None:
        try:
            manifest_sources = load_raw_source_manifest(raw_source_manifest_path)
        except Exception:
            manifest_sources = ()
            blockers.append("RAW_SOURCE_SCHEMA_INVALID")

    sources: list[StrategyLadderRawSource] = []
    if manifest_sources:
        for source in manifest_sources:
            resolved_root = Path(source.root).expanduser().resolve()
            exists = resolved_root.exists()
            if exists:
                status = "RAW_SOURCE_READY" if source.enabled else "RAW_SOURCE_DISABLED"
                reasons: tuple[str, ...] = ()
            elif source.enabled and not dry_run:
                status = "RAW_SOURCE_MISSING"
                reasons = ("RAW_SOURCE_MISSING",)
                blockers.append("RAW_SOURCE_MISSING")
            elif source.enabled:
                status = "RAW_SOURCE_UNMOUNTED"
                reasons = ("RAW_SOURCE_UNMOUNTED",)
                blockers.append("RAW_SOURCE_UNMOUNTED")
            else:
                status = "RAW_SOURCE_DISABLED"
                reasons = ("RAW_SOURCE_DISABLED",)
            sources.append(
                source.model_copy(
                    update={
                        "root": str(resolved_root),
                        "status": status,
                        "typing_status": (
                            "RAW_SOURCE_TYPED_READY"
                            if source.data_types
                            else "RAW_SOURCE_TYPE_NOT_PROVEN"
                        ),
                        "reason_codes": reasons,
                    }
                )
            )
    else:
        for index, root in enumerate(normalized_roots, start=1):
            exists = root.exists()
            status = "RAW_SOURCE_READY" if exists else "RAW_SOURCE_MISSING"
            if not exists:
                blockers.append("RAW_SOURCE_MISSING")
            inferred_data_types, typing_status = _infer_data_types_from_root(root)
            sources.append(
                StrategyLadderRawSource(
                    source_id=f"raw_root_{index:02d}",
                    root=str(root),
                    source_type="raw",
                    exchange="bybit",
                    market_type="spot",
                    data_types=inferred_data_types,
                    priority=index * 10,
                    enabled=True,
                    status=status,
                    typing_status=typing_status,
                    reason_codes=tuple(
                        code
                        for code in (
                            status if status != "RAW_SOURCE_READY" else "",
                            typing_status if typing_status != "RAW_SOURCE_TYPED_READY" else "",
                        )
                        if code
                    ),
                )
            )

    deduped_by_root: dict[str, StrategyLadderRawSource] = {}
    duplicate_blockers: list[str] = []
    for source in sorted(sources, key=lambda item: (item.priority, item.source_id)):
        root_key = str(Path(source.root).resolve()).lower()
        if root_key in deduped_by_root:
            duplicate_blockers.append("RAW_SOURCE_DUPLICATE")
            existing = deduped_by_root[root_key]
            if source.priority < existing.priority:
                deduped_by_root[root_key] = source.model_copy(
                    update={
                        "status": "RAW_SOURCE_DUPLICATE",
                        "reason_codes": ("RAW_SOURCE_DUPLICATE",),
                    }
                )
            continue
        deduped_by_root[root_key] = source

    resolved_sources = tuple(sorted(deduped_by_root.values(), key=lambda item: (-item.priority, item.source_id)))
    exchanges = {item.exchange for item in resolved_sources if item.status == "RAW_SOURCE_READY"}
    market_types = {item.market_type for item in resolved_sources if item.status == "RAW_SOURCE_READY"}
    if len(exchanges) > 1:
        blockers.append("RAW_SOURCE_INCOMPATIBLE_EXCHANGE")
    if len(market_types) > 1:
        blockers.append("RAW_SOURCE_INCOMPATIBLE_MARKET_TYPE")
    if duplicate_blockers:
        blockers.extend(duplicate_blockers)
    overall_status = "RAW_SOURCE_READY"
    typing_status = "RAW_SOURCE_TYPED_READY"
    if not resolved_sources:
        overall_status = "RAW_SOURCE_NOT_PROVEN"
    elif any(item.status in {"RAW_SOURCE_MISSING", "RAW_SOURCE_UNMOUNTED"} for item in resolved_sources):
        overall_status = "RAW_SOURCE_MISSING"
    elif blockers:
        overall_status = "RAW_SOURCE_SCHEMA_INVALID"
    if not resolved_sources:
        typing_status = "RAW_SOURCE_TYPE_NOT_PROVEN"
    elif any(item.typing_status == "RAW_SOURCE_TYPE_AMBIGUOUS" for item in resolved_sources):
        typing_status = "RAW_SOURCE_TYPE_AMBIGUOUS"
    elif any(item.typing_status == "RAW_SOURCE_TYPE_INFERRED" for item in resolved_sources):
        typing_status = "RAW_SOURCE_TYPE_INFERRED"
    report = StrategyLadderRawSourceReport(
        sources=resolved_sources,
        raw_source_status=overall_status,
        raw_source_typing_status=typing_status,
        blocker_codes=tuple(dict.fromkeys(blockers)),
    )
    return finalize_hashed_model(report)


__all__ = [
    "load_raw_source_manifest",
    "normalize_raw_root_inputs",
    "resolve_strategy_ladder_raw_sources",
]
