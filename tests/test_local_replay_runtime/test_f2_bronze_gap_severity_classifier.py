"""Tests F2 (2026-05-21) — Bronze gap severity classifier.

Vérifie le classifier 3-tier qui remplace le binary check BRONZE_GAPS_PRESENT :
1. WITHIN_TOLERANCE : gap_count = 0
2. TOLERATED_RESEARCH_GRADE : gaps mineurs (research-OK, promotion-blocked)
3. BLOCKED : gaps massifs (hard fail-close research + promotion)

Couvre aussi backward-compat avec le code existant et l'exposition
du nouveau status dans le silver_quality_report.
"""

from __future__ import annotations

from local_replay_runtime.raw_data_processing_contracts import (
    BronzeMarketIndexManifest,
    SilverSynchronizedMarketManifest,
    finalize_hashed_model,
)
from local_replay_runtime.silver_market_synchronizer import (
    BronzeGapSeverityThresholds,
    build_silver_quality_report,
    classify_bronze_gap_severity,
)


def _make_bronze_index(
    *,
    gap_count: int = 0,
    largest_gap_ms: int = 0,
    index_status: str = "BRONZE_INDEX_READY",
) -> BronzeMarketIndexManifest:
    """Build a minimal BronzeMarketIndexManifest for tests."""
    return finalize_hashed_model(
        BronzeMarketIndexManifest(
            exchange="bybit",
            market_type="spot",
            symbol="BTCUSDT",
            coverage_start_ms=1000,
            coverage_end_ms=2000,
            source_files_count=2,
            source_types_present=("trades", "klines", "orderbook_snapshot"),
            source_types_missing=(),
            gap_count=gap_count,
            largest_gap_ms=largest_gap_ms,
            duplicate_timestamp_count=0,
            out_of_order_count=0,
            index_status=index_status,
            source_file_refs=("/fake/path.csv",),
        )
    )


def _make_silver_manifest(
    *,
    silver_sync_status: str,
    blocker_codes: tuple[str, ...] = (),
    stale_book_count: int = 0,
) -> SilverSynchronizedMarketManifest:
    """Build a minimal SilverSynchronizedMarketManifest for quality_report tests."""
    return finalize_hashed_model(
        SilverSynchronizedMarketManifest(
            exchange="bybit",
            market_type="spot",
            symbol="BTCUSDT",
            coverage_start_ms=1000,
            coverage_end_ms=2000,
            trades_status="TRADE_SCHEMA_READY",
            orderbook_snapshot_status="ORDERBOOK_SCHEMA_READY",
            orderbook_delta_status="ORDERBOOK_SCHEMA_READY",
            ohlcv_status="KLINE_SCHEMA_READY",
            depth20_status="DEPTH20_READY",
            timestamp_alignment_status="FEATURE_TIMESTAMP_ALIGNED",
            book_trade_alignment_status="BOOK_TRADE_ALIGNMENT_READY",
            stale_book_count=stale_book_count,
            missing_book_count=0,
            missing_trade_count=0,
            missing_ohlcv_count=0,
            rows_written=100,
            silver_sync_status=silver_sync_status,
            blocker_codes=blocker_codes,
            source_file_refs=("/fake/path.csv",),
        )
    )


def test_bronze_gap_severity_within_tolerance_no_gaps_2026_05_21() -> None:
    """Patch F2 — gap_count=0 → WITHIN_TOLERANCE, aucun blocker."""
    status, blockers = classify_bronze_gap_severity(gap_count=0, largest_gap_ms=0)
    assert status == "BRONZE_GAPS_WITHIN_TOLERANCE"
    assert blockers == ()


def test_bronze_gap_severity_research_grade_minor_gaps_2026_05_21() -> None:
    """Patch F2 — gaps ≤10 + ≤60s → TOLERATED_RESEARCH_GRADE, promotion-blocked."""
    # Default thresholds : research_max_gap=60s, promotion_max_gap=5s
    # gap=3, largest=60s → promotion-blocked (60s > 5s), research-OK
    status, blockers = classify_bronze_gap_severity(gap_count=3, largest_gap_ms=60_000)
    assert status == "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE"
    assert "BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE" in blockers
    assert "BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE" in blockers
    # Pas de blocker RESEARCH (sous le seuil 60s/10)
    assert all("RESEARCH_TOLERANCE" not in b for b in blockers)


def test_bronze_gap_severity_blocked_largest_gap_exceeds_research_2026_05_21() -> None:
    """Patch F2 — gap > 60s → BLOCKED (hard fail research + promotion)."""
    # largest_gap=120s > research_max=60s → BLOCKED
    status, blockers = classify_bronze_gap_severity(gap_count=1, largest_gap_ms=120_000)
    assert status == "BRONZE_GAPS_BLOCKED"
    assert "BRONZE_GAP_LARGEST_EXCEEDS_RESEARCH_TOLERANCE" in blockers


def test_bronze_gap_severity_blocked_count_exceeds_research_2026_05_21() -> None:
    """Patch F2 — gap_count > 10 → BLOCKED."""
    # gap_count=15 > research_max_total=10 → BLOCKED
    status, blockers = classify_bronze_gap_severity(gap_count=15, largest_gap_ms=10_000)
    assert status == "BRONZE_GAPS_BLOCKED"
    assert "BRONZE_GAP_COUNT_EXCEEDS_RESEARCH_TOLERANCE" in blockers


def test_bronze_gap_severity_blocked_combined_count_and_size_2026_05_21() -> None:
    """Patch F2 — count > 10 ET largest > 60s → BLOCKED avec 2 blocker codes."""
    status, blockers = classify_bronze_gap_severity(gap_count=20, largest_gap_ms=120_000)
    assert status == "BRONZE_GAPS_BLOCKED"
    assert "BRONZE_GAP_COUNT_EXCEEDS_RESEARCH_TOLERANCE" in blockers
    assert "BRONZE_GAP_LARGEST_EXCEEDS_RESEARCH_TOLERANCE" in blockers


def test_bronze_gap_severity_research_grade_promotion_only_count_2026_05_21() -> None:
    """Patch F2 — count > 2 mais ≤10, largest ≤5s → research-OK, promotion-blocked."""
    # gap_count=5, largest=4s → promotion-blocked on count only
    status, blockers = classify_bronze_gap_severity(gap_count=5, largest_gap_ms=4_000)
    assert status == "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE"
    assert "BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE" in blockers
    assert "BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE" not in blockers


def test_bronze_gap_severity_within_tolerance_promotion_grade_2026_05_21() -> None:
    """Patch F2 — count ≤2 ET largest ≤5s → WITHIN_TOLERANCE (promotion OK)."""
    # gap_count=1, largest=3s → tout sous promotion thresholds → WITHIN_TOLERANCE
    status, blockers = classify_bronze_gap_severity(gap_count=1, largest_gap_ms=3_000)
    assert status == "BRONZE_GAPS_WITHIN_TOLERANCE"
    assert blockers == ()


def test_bronze_gap_severity_custom_thresholds_2026_05_21() -> None:
    """Patch F2 — thresholds custom permettent override pour tests calibration."""
    strict_thresholds = BronzeGapSeverityThresholds(
        research_max_gap_ms=1_000,  # 1s only research-OK
        research_max_total_gap_count=1,  # 1 gap max research
        promotion_max_gap_ms=500,
        promotion_max_total_gap_count=0,
    )
    # gap=2, largest=2000ms : déjà au-delà du strict research → BLOCKED
    status, blockers = classify_bronze_gap_severity(
        gap_count=2,
        largest_gap_ms=2_000,
        thresholds=strict_thresholds,
    )
    assert status == "BRONZE_GAPS_BLOCKED"


def test_silver_quality_report_exposes_bronze_gap_severity_status_2026_05_21() -> None:
    """Patch F2 — silver_quality_report contient le nouveau champ severity_status."""
    bronze = _make_bronze_index(gap_count=2, largest_gap_ms=60_000)
    silver = _make_silver_manifest(
        silver_sync_status="SILVER_SYNC_PARTIAL",
        blocker_codes=(
            "BRONZE_GAP_LARGEST_EXCEEDS_PROMOTION_TOLERANCE",
            "BRONZE_GAP_COUNT_EXCEEDS_PROMOTION_TOLERANCE",
        ),
    )
    report = build_silver_quality_report(silver, bronze_index=bronze)
    assert "bronze_gap_severity_status" in report
    assert report["bronze_gap_severity_status"] == "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE"
    assert report["bronze_gap_count"] == 2
    assert report["bronze_largest_gap_ms"] == 60_000


def test_silver_quality_report_severity_when_no_gaps_2026_05_21() -> None:
    """Patch F2 — silver_quality_report avec 0 gaps → WITHIN_TOLERANCE."""
    bronze = _make_bronze_index(gap_count=0, largest_gap_ms=0)
    silver = _make_silver_manifest(silver_sync_status="SILVER_SYNC_READY")
    report = build_silver_quality_report(silver, bronze_index=bronze)
    assert report["bronze_gap_severity_status"] == "BRONZE_GAPS_WITHIN_TOLERANCE"


def test_run_f9bb2bdc_gap_pattern_resolves_to_research_grade_2026_05_21() -> None:
    """Patch F2 — pattern observé sur run f9bb2bdc (2 gaps, 60s max) doit
    devenir TOLERATED_RESEARCH_GRADE et NE PLUS être BRONZE_GAPS_PRESENT blocker."""
    # Reproduit la condition exacte du run audit-é
    status, blockers = classify_bronze_gap_severity(gap_count=2, largest_gap_ms=60_000)
    # AVANT F2 : aurait été un blocker générique BRONZE_GAPS_PRESENT
    # APRÈS F2 : research-grade acceptable, blockers PROMOTION-only seulement
    assert status == "BRONZE_GAPS_TOLERATED_RESEARCH_GRADE"
    assert "BRONZE_GAPS_PRESENT" not in blockers  # ancien blocker générique éliminé
    # Nouveaux blockers explicit promotion-only
    assert all("PROMOTION_TOLERANCE" in b for b in blockers)
