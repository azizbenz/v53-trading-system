"""Typed silver synchronization summaries for the canonical raw-data rail."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.raw_data_processing_contracts import (
    BronzeMarketIndexManifest,
    SilverSynchronizedMarketManifest,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)


# Patch F2 (2026-05-21) — Bronze gap severity classifier.
# Remplace le check binaire `if gap_count > 0 → BRONZE_GAPS_PRESENT`
# par une classification 3-tiers (TOLERANCE / RESEARCH_GRADE / BLOCKED).
# Permet d'accepter des gaps mineurs (≤60s/jour boundary) en research-grade
# tout en restant fail-closed sur les gaps massifs (>60s ou >10 total).
@dataclass(frozen=True)
class BronzeGapSeverityThresholds:
    """Doctrinal thresholds for bronze gap severity classification.

    Research-acceptable defaults : tolère jusqu'à 10 gaps totaux et 60s max
    par gap individuel (boundaries jour entre fichiers raw consécutifs).
    Promotion-acceptable defaults plus stricts : ≤2 gaps, ≤5s max.

    Cohérence avec patch P1 OHLCV severity : research-grade flag explicit
    + fail-closed pour les violations doctrinales.
    """

    research_max_gap_ms: int = 60_000  # 1 min max single gap (research OK)
    research_max_total_gap_count: int = 10  # ≤10 gaps total
    promotion_max_gap_ms: int = 5_000  # 5 sec max single gap (promotion strict)
    promotion_max_total_gap_count: int = 2  # ≤2 gaps total


def classify_bronze_gap_severity(
    *,
    gap_count: int,
    largest_gap_ms: int,
    thresholds: BronzeGapSeverityThresholds | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Classify bronze gap severity into 3-tier taxonomy.

    Returns (severity_status, blocker_codes_to_emit).

    3 statuts possibles :
    - BRONZE_GAPS_WITHIN_TOLERANCE : gap_count = 0 (aucun blocker)
    - BRONZE_GAPS_TOLERATED_RESEARCH_GRADE : gaps mineurs, research-OK
      mais promotion-blocked. Blockers : ..._EXCEEDS_PROMOTION_TOLERANCE.
    - BRONZE_GAPS_BLOCKED : gaps trop importants pour research.
      Blockers : ..._EXCEEDS_RESEARCH_TOLERANCE (hard fail-close).
    """
    cfg = thresholds or BronzeGapSeverityThresholds()
    if gap_count <= 0:
        return "BRONZE_GAPS_WITHIN_TOLERANCE", ()

    research_blockers: list[str] = []
    if largest_gap_ms > cfg.research_max_gap_ms:
        research_blockers.append("BRONZE_GAP_LARGEST_EXCEEDS_RESEARCH_TOLERANCE")
    if gap_count > cfg.research_max_total_gap_count:
        research_blockers.append("BRONZE_GAP_COUNT_EXCEEDS_RESEARCH_TOLERANCE")
    if research_blockers:
        return "BRONZE_GAPS_BLOCKED", tuple(research_blockers)

    promotion_blockers: list[str] = []
    if largest_gap_ms > cfg.promotion_max_gap_ms:
        promotion_blockers.append("BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE")
    if gap_count > cfg.promotion_max_total_gap_count:
        promotion_blockers.append("BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE")
    if promotion_blockers:
        return "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE", tuple(promotion_blockers)

    return "BRONZE_GAPS_WITHIN_TOLERANCE", ()


def _entry_status(entries: tuple[StrategyLadderSilverIndexEntry, ...], *, allowed_schema_prefix: str) -> str:
    if not entries:
        return f"{allowed_schema_prefix}_NOT_PROVEN"
    if all(str(item.schema_status).startswith(allowed_schema_prefix) and "READY" in str(item.schema_status) for item in entries):
        return f"{allowed_schema_prefix}_READY"
    if any("READY" in str(item.schema_status) for item in entries):
        return f"{allowed_schema_prefix}_PARTIAL"
    return f"{allowed_schema_prefix}_BLOCKED"


def build_silver_synchronized_market_manifest(
    *,
    symbol: str,
    bronze_index: BronzeMarketIndexManifest,
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...],
) -> SilverSynchronizedMarketManifest:
    """Aggregate silver index entries into one operator-facing synchronization summary."""

    relevant = tuple(item for item in silver_index if item.pair == symbol)
    trade_entries = tuple(item for item in relevant if item.data_type == "trades")
    snapshot_entries = tuple(item for item in relevant if item.data_type == "orderbook_snapshot")
    delta_entries = tuple(item for item in relevant if item.data_type == "orderbook_delta")
    ohlcv_entries = tuple(item for item in relevant if item.data_type == "ohlcv")
    timestamp_values = tuple(
        value
        for item in relevant
        for value in (item.min_timestamp_ms, item.max_timestamp_ms)
        if value is not None
    )
    timestamp_alignment_status = "FEATURE_TIMESTAMP_ALIGNMENT_NOT_PROVEN"
    if relevant and all(
        item.min_timestamp_ms is None
        or item.max_timestamp_ms is None
        or item.max_timestamp_ms >= item.min_timestamp_ms
        for item in relevant
    ):
        timestamp_alignment_status = "FEATURE_TIMESTAMP_ALIGNED"
    depth20_status = "DEPTH20_NOT_PROVEN"
    if any(item.depth_source_status == "BOOK_DEPTH20_AVAILABLE" for item in (*snapshot_entries, *delta_entries)):
        depth20_status = "DEPTH20_READY"
    elif snapshot_entries or delta_entries:
        depth20_status = "DEPTH20_PARTIAL"
    book_trade_alignment_status = "BOOK_TRADE_ALIGNMENT_NOT_PROVEN"
    if trade_entries and (snapshot_entries or delta_entries):
        trade_dates = {item.date for item in trade_entries if item.date}
        book_dates = {item.date for item in (*snapshot_entries, *delta_entries) if item.date}
        book_trade_alignment_status = (
            "BOOK_TRADE_ALIGNMENT_READY"
            if trade_dates & book_dates
            else "BOOK_TRADE_ALIGNMENT_PARTIAL"
        )
    stale_book_count = sum(
        1
        for item in (*snapshot_entries, *delta_entries)
        if item.depth_source_status not in {"BOOK_DEPTH20_AVAILABLE", "BOOK_LIMITED_DEPTH_AVAILABLE"}
    )
    missing_book_count = 0 if snapshot_entries or delta_entries else 1
    missing_trade_count = 0 if trade_entries else 1
    missing_ohlcv_count = 0 if ohlcv_entries else 1
    blocker_codes: list[str] = []
    if missing_trade_count:
        blocker_codes.append("SILVER_MISSING_TRADES")
    if missing_book_count:
        blocker_codes.append("SILVER_MISSING_ORDERBOOK")
    if missing_ohlcv_count:
        blocker_codes.append("SILVER_MISSING_OHLCV")
    # Patch F2 (2026-05-21) — severity classifier remplace BRONZE_GAPS_PRESENT.
    # Backward-compat doctrinal : si gaps > research_tolerance → BLOCKED
    # (équivalent fail-close ancien comportement). Si gaps mineurs (≤10 total,
    # ≤60s individuel) → TOLERATED_RESEARCH_GRADE avec blockers PROMOTION-only.
    bronze_gap_severity_status, bronze_gap_severity_blockers = (
        classify_bronze_gap_severity(
            gap_count=bronze_index.gap_count,
            largest_gap_ms=bronze_index.largest_gap_ms,
        )
    )
    blocker_codes.extend(bronze_gap_severity_blockers)
    if bronze_index.index_status == "BRONZE_INDEX_BLOCKED_BY_SCHEMA":
        blocker_codes.append("BRONZE_SCHEMA_BLOCKER")
    silver_sync_status = "SILVER_SYNC_READY"
    if not relevant:
        silver_sync_status = "SILVER_SYNC_BLOCKED_BY_MISSING_RAW"
    elif blocker_codes:
        silver_sync_status = "SILVER_SYNC_PARTIAL"
    return finalize_hashed_model(
        SilverSynchronizedMarketManifest(
            exchange=bronze_index.exchange,
            market_type=bronze_index.market_type,
            symbol=symbol,
            coverage_start_ms=min(timestamp_values) if timestamp_values else bronze_index.coverage_start_ms,
            coverage_end_ms=max(timestamp_values) if timestamp_values else bronze_index.coverage_end_ms,
            trades_status=_entry_status(trade_entries, allowed_schema_prefix="TRADE_SCHEMA"),
            orderbook_snapshot_status=_entry_status(snapshot_entries, allowed_schema_prefix="ORDERBOOK_SCHEMA"),
            orderbook_delta_status=_entry_status(delta_entries, allowed_schema_prefix="ORDERBOOK_SCHEMA"),
            ohlcv_status=_entry_status(ohlcv_entries, allowed_schema_prefix="KLINE_SCHEMA"),
            depth20_status=depth20_status,
            timestamp_alignment_status=timestamp_alignment_status,
            book_trade_alignment_status=book_trade_alignment_status,
            stale_book_count=stale_book_count,
            missing_book_count=missing_book_count,
            missing_trade_count=missing_trade_count,
            missing_ohlcv_count=missing_ohlcv_count,
            rows_written=sum(item.row_count for item in relevant),
            silver_sync_status=silver_sync_status,
            blocker_codes=tuple(dict.fromkeys(blocker_codes)),
            source_file_refs=tuple(sorted({item.path for item in relevant if item.path})),
        )
    )


def build_silver_quality_report(
    manifest: SilverSynchronizedMarketManifest,
    *,
    bronze_index: BronzeMarketIndexManifest,
) -> dict[str, object]:
    """Build one compact quality report for operator diagnostics."""

    # Patch F2 (2026-05-21) — re-compute severity for the operator report.
    # Idempotent : reuses thresholds defaults, juste pour exposer le tier
    # à l'audit (le status est aussi dérivable depuis blocker_codes mais
    # exposé explicit pour scripts downstream).
    bronze_gap_severity_status, _ = classify_bronze_gap_severity(
        gap_count=bronze_index.gap_count,
        largest_gap_ms=bronze_index.largest_gap_ms,
    )
    return {
        "schema_version": "v1",
        "symbol": manifest.symbol,
        "silver_sync_status": manifest.silver_sync_status,
        "timestamp_alignment_status": manifest.timestamp_alignment_status,
        "book_trade_alignment_status": manifest.book_trade_alignment_status,
        "depth20_status": manifest.depth20_status,
        "stale_book_count": manifest.stale_book_count,
        "missing_book_count": manifest.missing_book_count,
        "missing_trade_count": manifest.missing_trade_count,
        "missing_ohlcv_count": manifest.missing_ohlcv_count,
        "bronze_gap_count": bronze_index.gap_count,
        "bronze_largest_gap_ms": bronze_index.largest_gap_ms,
        "bronze_gap_severity_status": bronze_gap_severity_status,
        "source_file_refs": list(manifest.source_file_refs),
        "blocker_codes": list(manifest.blocker_codes),
    }


def write_silver_market_reports(
    output_dir: Path,
    *,
    manifest: SilverSynchronizedMarketManifest,
    bronze_index: BronzeMarketIndexManifest,
) -> tuple[str, str]:
    """Write the canonical silver synchronization outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "silver_synchronized_market_manifest.json"
    quality_path = output_dir / "silver_quality_report.json"
    atomic_write_json(manifest_path, manifest.model_dump(mode="json"), indent=2)
    atomic_write_json(quality_path, build_silver_quality_report(manifest, bronze_index=bronze_index), indent=2)
    return str(manifest_path.resolve()), str(quality_path.resolve())


def load_silver_synchronized_market_manifest(path: Path) -> SilverSynchronizedMarketManifest:
    """Load one persisted silver synchronization manifest."""

    return SilverSynchronizedMarketManifest.model_validate_json(path.read_text(encoding="utf-8-sig"))


__all__ = [
    "BronzeGapSeverityThresholds",
    "build_silver_quality_report",
    "build_silver_synchronized_market_manifest",
    "classify_bronze_gap_severity",
    "load_silver_synchronized_market_manifest",
    "write_silver_market_reports",
]
