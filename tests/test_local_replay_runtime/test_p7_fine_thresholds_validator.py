"""P7 (2026-05-29) — test fine-grained calibration thresholds.

Covers B4 + B5 + C2 + C4 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - B4: book_depth_levels < 20 → blocker
  - B5: fee_schedule_date drift > 90d vs row timestamp → blocker
  - C4: metadata_effective_at staleness > 90d vs row timestamp → blocker

Validates:
  - Schema accepts fee_schedule_date field
  - Validator blocks on insufficient depth
  - Validator blocks on excessive fee drift
  - Validator blocks on excessive metadata staleness
  - Within tolerance → no P7 blockers
"""

from __future__ import annotations

from datetime import datetime, timezone

from local_replay_runtime.data_science_quality_gates import (
    PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS,
    PROD_SAFE_MAX_METADATA_STALENESS_DAYS,
    PROD_SAFE_MIN_BOOK_DEPTH_LEVELS,
    _days_drift,
    assess_gold_row_prod_safety,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def test_prod_safe_thresholds_match_audit() -> None:
    """Audit C5 + C2 + C4 thresholds."""
    assert PROD_SAFE_MIN_BOOK_DEPTH_LEVELS == 20
    assert PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS == 90
    assert PROD_SAFE_MAX_METADATA_STALENESS_DAYS == 90


def test_days_drift_computes_absolute_distance_in_days() -> None:
    # 2025-04-29 in ms: datetime(2025, 4, 29, tzinfo=utc).timestamp() * 1000
    ts_2025_04_29 = int(datetime(2025, 4, 29, tzinfo=timezone.utc).timestamp() * 1000)

    # Same date: 0 days
    assert _days_drift("2025-04-29", ts_2025_04_29) == 0
    # 30 days before
    assert _days_drift("2025-03-30", ts_2025_04_29) == 30
    # 30 days after
    assert _days_drift("2025-05-29", ts_2025_04_29) == 30


def test_days_drift_returns_none_when_inputs_missing() -> None:
    assert _days_drift(None, 1_745_884_800_000) is None
    assert _days_drift("2025-04-29", None) is None
    assert _days_drift(None, None) is None
    assert _days_drift("not-iso", 1_745_884_800_000) is None


def test_strategy_ladder_feature_row_accepts_fee_schedule_date_field() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/...",
        fee_schedule_date="2025-04-29",
    )

    assert row.fee_schedule_date == "2025-04-29"


def _prod_safe_row_with(**overrides) -> StrategyLadderFeatureRow:
    """Fully prod-safe row, mutated by `overrides` (P7 scope)."""
    defaults = {
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "timestamp_ms": int(datetime(2025, 4, 29, tzinfo=timezone.utc).timestamp() * 1000),
        "engine_id": "engine_a",
        "source_ref": "K:/output lab/runs/x/...",
        # P1
        "input_data_hash": "h",
        "method_version_hash": "v",
        "raw_catalog_ref": "ref",
        "feature_set_hash": "fh",
        # P2
        "metadata_effective_at": "2025-04-29",
        "metadata_source": "src",
        "metadata_hash": "mh",
        # P3
        "book_freshness_status": "BOOK_DEPTH20_AVAILABLE_FRESH",
        # P4
        "slippage_truth_status": "SLIPPAGE_A2_KYLE_MEASURED",
        # P5
        "expected_edge_row_truth_status": "EXPECTED_EDGE_MODEL_GOVERNED",
        # P7
        "book_depth_levels": 20,
        "fee_schedule_date": "2025-04-29",
    }
    defaults.update(overrides)
    return StrategyLadderFeatureRow(**defaults)


def test_assess_gold_row_blocks_when_book_depth_insufficient() -> None:
    row = _prod_safe_row_with(book_depth_levels=10)

    blockers = assess_gold_row_prod_safety(row)

    assert any("ORDERBOOK_DEPTH_INSUFFICIENT" in b for b in blockers)


def test_assess_gold_row_blocks_when_book_depth_missing() -> None:
    row = _prod_safe_row_with(book_depth_levels=None)

    blockers = assess_gold_row_prod_safety(row)

    assert any("ORDERBOOK_DEPTH_INSUFFICIENT" in b for b in blockers)


def test_assess_gold_row_blocks_when_fee_schedule_drift_too_large() -> None:
    # Row at 2025-04-29 but fee schedule from 2024-01-01 (drift > 90d)
    row = _prod_safe_row_with(fee_schedule_date="2024-01-01")

    blockers = assess_gold_row_prod_safety(row)

    assert any("FEE_SCHEDULE_DRIFT_TOO_LARGE" in b for b in blockers)


def test_assess_gold_row_blocks_when_fee_schedule_date_missing() -> None:
    row = _prod_safe_row_with(fee_schedule_date=None)

    blockers = assess_gold_row_prod_safety(row)

    assert any("FEE_SCHEDULE_DRIFT_NOT_PROVEN" in b for b in blockers)


def test_assess_gold_row_blocks_when_metadata_staleness_too_large() -> None:
    # Row at 2025-04-29 but metadata from 2024-01-01 (staleness > 90d)
    row = _prod_safe_row_with(
        metadata_effective_at="2024-01-01",
        fee_schedule_date="2024-01-01",  # also fail-closed so we don't conflate
    )

    blockers = assess_gold_row_prod_safety(row)

    assert any("METADATA_STALENESS_TOO_LARGE" in b for b in blockers)


def test_assess_gold_row_no_p7_blockers_when_within_thresholds() -> None:
    row = _prod_safe_row_with()

    blockers = assess_gold_row_prod_safety(row)

    # No P7 blocker codes
    assert not any("ORDERBOOK_DEPTH_INSUFFICIENT" in b for b in blockers)
    assert not any("FEE_SCHEDULE" in b for b in blockers)
    assert not any("METADATA_STALENESS_TOO_LARGE" in b for b in blockers)


def test_assess_gold_row_fully_prod_safe_emits_empty_blockers() -> None:
    """Sanity check: P1-P7 all green → no blockers at all."""
    row = _prod_safe_row_with()

    blockers = assess_gold_row_prod_safety(row)

    assert blockers == ()
