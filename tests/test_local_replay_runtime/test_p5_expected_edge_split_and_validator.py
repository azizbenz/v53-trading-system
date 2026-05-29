"""P5 (2026-05-29) — test expected-edge schema split + assess_gold_row_prod_safety.

Covers A9 + A10 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - A9: Split expected_edge_bps → proxy_bps + model_bps + row_truth_status enum
  - A10: assess_gold_row_prod_safety returns A2_GOLD_PROD_SAFE_BLOCKED_BY_* codes

Validates:
  - derive_expected_edge_truth_status enum mapping (6 cases)
  - StrategyLadderFeatureRow accepts P5 fields (back-compat)
  - assess_gold_row_prod_safety aggregates blockers from P1-P5
  - Empty blockers when row is fully prod-safe
"""

from __future__ import annotations

from local_replay_runtime.data_science_quality_gates import (
    assess_gold_row_prod_safety,
)
from local_replay_runtime.strategy_ladder_economic_provenance import (
    derive_expected_edge_truth_status,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def test_derive_expected_edge_truth_status_governed() -> None:
    assert (
        derive_expected_edge_truth_status("GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH")
        == "EXPECTED_EDGE_MODEL_GOVERNED"
    )
    assert (
        derive_expected_edge_truth_status("GOVERNED_EDGE_MODEL_READY")
        == "EXPECTED_EDGE_MODEL_GOVERNED"
    )


def test_derive_expected_edge_truth_status_override() -> None:
    assert (
        derive_expected_edge_truth_status("MEASURED_FROM_EDGE_MODEL_OVERRIDE")
        == "EXPECTED_EDGE_MODEL_OVERRIDE"
    )


def test_derive_expected_edge_truth_status_proxy_and_default() -> None:
    assert (
        derive_expected_edge_truth_status("PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE")
        == "EXPECTED_EDGE_PROXY"
    )
    assert (
        derive_expected_edge_truth_status("DEFAULT_TO_CALIBRATE")
        == "EXPECTED_EDGE_DEFAULT_PROXY"
    )


def test_derive_expected_edge_truth_status_blocked_and_unknown() -> None:
    assert (
        derive_expected_edge_truth_status("EDGE_MODEL_BLOCKED:ESTIMATE_FAILED_RuntimeError")
        == "EXPECTED_EDGE_BLOCKED"
    )
    assert derive_expected_edge_truth_status("") == "EXPECTED_EDGE_NOT_PROVEN"
    assert derive_expected_edge_truth_status(None) == "EXPECTED_EDGE_NOT_PROVEN"
    assert derive_expected_edge_truth_status("UNKNOWN_PROVENANCE") == "EXPECTED_EDGE_NOT_PROVEN"


def test_strategy_ladder_feature_row_accepts_p5_split_fields() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        expected_edge_proxy_bps=None,
        expected_edge_model_bps=12.5,
        expected_edge_row_truth_status="EXPECTED_EDGE_MODEL_GOVERNED",
    )

    assert row.expected_edge_proxy_bps is None
    assert row.expected_edge_model_bps == 12.5
    assert row.expected_edge_row_truth_status == "EXPECTED_EDGE_MODEL_GOVERNED"


def test_strategy_ladder_feature_row_p5_back_compat_defaults() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
    )

    assert row.expected_edge_proxy_bps is None
    assert row.expected_edge_model_bps is None
    assert row.expected_edge_row_truth_status == "EXPECTED_EDGE_NOT_PROVEN"


def _make_prod_safe_row() -> StrategyLadderFeatureRow:
    """Fully prod-safe row: P1-P5 fields all populated correctly."""
    return StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        # P1
        input_data_hash="abc123",
        method_version_hash="strategy_ladder.gold.v1#deadbeef",
        raw_catalog_ref="silver:raw_bybit_spot:bybit:spot:ohlcv:BTCUSDT:2025-04-29",
        feature_set_hash="1234567890abcdef",
        # P2
        metadata_effective_at="2025-04-29",
        metadata_source="silver:bybit_metadata_cache:bybit:spot:metadata:BTCUSDT:2025-04-29",
        metadata_hash="metadatahashabc",
        # P3 — FRESH
        book_snapshot_age_ms=10_000,
        book_freshness_status="BOOK_DEPTH20_AVAILABLE_FRESH",
        book_freshness_tolerance_ms=60_000,
        # P4 — Kyle measured
        slippage_truth_status="SLIPPAGE_A2_KYLE_MEASURED",
        # P5 — Governed model
        expected_edge_model_bps=12.5,
        expected_edge_row_truth_status="EXPECTED_EDGE_MODEL_GOVERNED",
        # P7 — fine thresholds: depth>=20, fee_schedule_date close to row.timestamp_ms
        book_depth_levels=20,
        fee_schedule_date="2025-04-29",
    )


def test_assess_gold_row_prod_safety_returns_empty_when_row_is_fully_prod_safe() -> None:
    row = _make_prod_safe_row()

    blockers = assess_gold_row_prod_safety(row)

    assert blockers == ()


def test_assess_gold_row_prod_safety_blocks_when_p1_hashes_missing() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        # P1 all missing (None or empty)
    )

    blockers = assess_gold_row_prod_safety(row)

    assert "A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_INPUT_DATA_HASH" in blockers
    assert "A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_METHOD_VERSION_HASH" in blockers
    assert "A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_RAW_CATALOG_REF" in blockers
    assert "A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_FEATURE_SET_HASH" in blockers


def test_assess_gold_row_prod_safety_blocks_on_stale_book() -> None:
    row = _make_prod_safe_row().model_copy(
        update={"book_freshness_status": "BOOK_DEPTH20_AVAILABLE_STALE"}
    )

    blockers = assess_gold_row_prod_safety(row)

    assert any(
        b.startswith("A2_GOLD_PROD_SAFE_BLOCKED_BY_BOOK_NOT_FRESH") for b in blockers
    )


def test_assess_gold_row_prod_safety_blocks_on_default_slippage() -> None:
    row = _make_prod_safe_row().model_copy(
        update={"slippage_truth_status": "SLIPPAGE_A2_RESEARCH_ONLY_DEFAULT"}
    )

    blockers = assess_gold_row_prod_safety(row)

    assert any(
        b.startswith("A2_GOLD_PROD_SAFE_BLOCKED_BY_SLIPPAGE_NOT_PROVEN") for b in blockers
    )


def test_assess_gold_row_prod_safety_blocks_on_proxy_edge() -> None:
    row = _make_prod_safe_row().model_copy(
        update={
            "expected_edge_row_truth_status": "EXPECTED_EDGE_DEFAULT_PROXY",
            "expected_edge_model_bps": None,
            "expected_edge_proxy_bps": 5.0,
        }
    )

    blockers = assess_gold_row_prod_safety(row)

    assert any(
        b.startswith("A2_GOLD_PROD_SAFE_BLOCKED_BY_EXPECTED_EDGE_NOT_GOVERNED")
        for b in blockers
    )


def test_assess_gold_row_prod_safety_aggregates_multiple_blockers() -> None:
    """User's current run: all P1-P5 fail — many blockers, exact mirror of audit."""
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        input_data_hash="",  # P1 fail
        book_freshness_status="BOOK_DEPTH20_AVAILABLE_STALE",  # P3 fail
        slippage_truth_status="SLIPPAGE_A2_RESEARCH_ONLY_DEFAULT",  # P4 fail
        expected_edge_row_truth_status="EXPECTED_EDGE_DEFAULT_PROXY",  # P5 fail
    )

    blockers = assess_gold_row_prod_safety(row)

    # All four cleanup areas should emit blockers
    assert any("INPUT_DATA_HASH" in b for b in blockers)  # P1
    assert any("METADATA" in b for b in blockers)  # P2
    assert any("BOOK_NOT_FRESH" in b for b in blockers)  # P3
    assert any("SLIPPAGE_NOT_PROVEN" in b for b in blockers)  # P4
    assert any("EXPECTED_EDGE_NOT_GOVERNED" in b for b in blockers)  # P5
    # At least 4 distinct cleanup areas
    assert len(blockers) >= 8
