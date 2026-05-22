from __future__ import annotations

import pytest

from local_replay_runtime.engine_feature_contract_validator import (
    EngineFeatureExpectation,
    audit_engine_feature_contract,
)
from local_replay_runtime.engine_math_canary_audit import (
    _CANARY_PROVENANCE,
    _expected_cost_audit_fields,
    _expected_gain_audit_fields,
)


def test_expected_gain_proxy_is_zeroed_and_blocked_in_b2() -> None:
    payload = {
        "expected_edge_bps": 12.0,
        "expected_edge_provenance": "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
    }
    metadata = _expected_gain_audit_fields(
        payload=payload,
        expected_gain_used_decimal=0.0,
        runtime_mode="B2",
    )
    audit = audit_engine_feature_contract(
        engine_id="engine_b",
        candidate_id="cand-proxy-gain",
        payload={"expected_gain": metadata["expected_gain_used_decimal"]},
        expectations=(
            EngineFeatureExpectation(
                "engine_b",
                "expected_gain",
                "decimal_return",
                "check_cost_feasibility_b",
                proxy_forbidden_in_b2=True,
                sanity_min=0.0,
            ),
        ),
        provenance_by_feature={
            "expected_gain": "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
        },
        feature_metadata_by_feature={"expected_gain": metadata},
        runtime_mode="B2",
        builder_status="TEST",
        builder_provenance="TEST",
    )

    row = audit.rows[0]
    assert metadata["expected_gain_proxy_decimal"] == pytest.approx(0.0012)
    assert metadata["expected_gain_used_decimal"] == 0.0
    assert metadata["expected_gain_truth_status"] == "EXPECTED_EDGE_PROXY_BLOCKED"
    assert metadata["expected_gain_block_reason"] == "EXPECTED_EDGE_PROXY_BLOCKED"
    assert row.status == "invalid"
    assert row.reason == "proxy_used_as_truth_in_b2:EXPECTED_EDGE_PROXY_BLOCKED"


def test_governed_synthetic_expected_gain_is_forbidden_outside_test() -> None:
    payload = {
        "expected_edge_bps": 90.0,
        "expected_edge_provenance": _CANARY_PROVENANCE,
        "expected_edge_truth_status": "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
    }
    blocked = _expected_gain_audit_fields(
        payload=payload,
        expected_gain_used_decimal=0.009,
        runtime_mode="LOCAL_REPLAY",
    )
    allowed = _expected_gain_audit_fields(
        payload=payload,
        expected_gain_used_decimal=0.009,
        runtime_mode="TEST",
    )

    assert blocked["expected_gain_truth_status"] == "EXPECTED_EDGE_PROXY_BLOCKED"
    assert (
        blocked["expected_gain_block_reason"]
        == "EXPECTED_EDGE_SYNTHETIC_CANARY_FORBIDDEN_OUTSIDE_TEST"
    )
    assert allowed["expected_gain_truth_status"] == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
    assert allowed["expected_gain_block_reason"] == ""


def test_expected_cost_unclassified_provenance_fails_contract() -> None:
    metadata = _expected_cost_audit_fields(
        payload={
            "spread_bps": 0.5,
            "slippage_bps": 0.1,
            "latency_penalty_bps": 1.5,
            "fee_bps": 10.0,
        },
        expected_cost_used_decimal=0.0002115,
        book_staleness_ms=0,
    )
    audit = audit_engine_feature_contract(
        engine_id="engine_b",
        candidate_id="cand-unclassified-cost",
        payload={"expected_cost": metadata["expected_cost_used_decimal"]},
        expectations=(
            EngineFeatureExpectation(
                "engine_b",
                "expected_cost",
                "decimal_return",
                "check_cost_feasibility_b",
                measured_required=True,
                sanity_min=0.0,
            ),
        ),
        provenance_by_feature={"expected_cost": "PARTIALLY_MEASURED"},
        feature_metadata_by_feature={"expected_cost": metadata},
        runtime_mode="B2",
        builder_status="TEST",
        builder_provenance="TEST",
    )

    row = audit.rows[0]
    assert metadata["expected_cost_truth_status"] == "COST_PROVENANCE_UNCLASSIFIED"
    assert row.proxy_or_measured == "unclassified"
    assert row.status == "invalid"
    assert row.reason == "expected_cost_provenance_unclassified"


def test_proxy_spread_and_slippage_cannot_become_b2_truth() -> None:
    metadata = _expected_cost_audit_fields(
        payload={
            "spread_bps": 0.5,
            "spread_provenance": "DEFAULT_BY_BOOK_STATUS",
            "slippage_bps": 0.1,
            "slippage_provenance": "DEFAULT_TO_CALIBRATE",
            "latency_penalty_bps": 1.5,
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
        },
        expected_cost_used_decimal=0.0002115,
        book_staleness_ms=0,
    )

    assert metadata["expected_cost_truth_status"] == "PARTIALLY_MEASURED_COST"
    assert metadata["cost_source_used_for_break_even"] != "measured"
    assert metadata["cost_source_used_for_expected_ce_net"] != "measured"


def test_measured_b2_cost_marks_break_even_source_measured() -> None:
    metadata = _expected_cost_audit_fields(
        payload={
            "spread_bps": 9.995,
            "spread_provenance": "MEASURED_FROM_BOOK_RECONSTRUCTION",
            "slippage_bps": 0.1,
            "slippage_provenance": "MEASURED_FROM_KYLE_LAMBDA",
            "latency_penalty_bps": 1.5,
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
        },
        expected_cost_used_decimal=0.00216065,
        book_staleness_ms=0,
    )

    assert metadata["expected_cost_truth_status"] == "FULLY_MEASURED_COST"
    assert metadata["cost_source_used_for_break_even"] == "measured"
    assert metadata["cost_source_used_for_expected_ce_net"] == "measured"


def test_stale_book_spread_is_classified_audit_only() -> None:
    metadata = _expected_cost_audit_fields(
        payload={
            "spread_bps": 9.995,
            "spread_provenance": "MEASURED_FROM_BOOK_SNAPSHOT_STALE",
            "slippage_bps": 0.1,
            "slippage_provenance": "MEASURED_FROM_KYLE_LAMBDA",
            "latency_penalty_bps": 1.5,
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
            "book_depth_staleness_status": "BOOK_DEPTH20_STALE",
        },
        expected_cost_used_decimal=0.00216065,
        book_staleness_ms=4_200_000,
    )

    assert metadata["expected_cost_truth_status"] == "STALE_AUDIT_ONLY_COST"
    assert metadata["cost_source_used_for_break_even"] == "stale_audit_only"
    assert metadata["fill_realism_status"] == "FILL_REALISM_STALE_AUDIT_ONLY"


def test_measured_depth20_partial_fill_keeps_measured_break_even_usage() -> None:
    metadata = _expected_cost_audit_fields(
        payload={
            "spread_bps_measured": 9.995,
            "slippage_bps_measured": 0.25,
            "measured_spread_report": {
                "status": "SPREAD_MEASURED_FROM_BOOK",
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "staleness_ms": 126,
            },
            "measured_slippage_report": {
                "status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
                "walk_cost_bps": 0.25,
                "depth_fill_ratio": 0.62,
                "partial_fill_status": "PARTIAL_DEPTH_FILL",
                "staleness_ms": 126,
            },
            "spread_source_status": "SPREAD_MEASURED_FROM_BOOK",
            "slippage_source_status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
            "latency_penalty_bps": 1.5,
            "latency_source_status": "STATIC_CONSERVATIVE_VENUE_MODEL",
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
            "cost_source_used_for_break_even": "measured",
            "cost_source_used_for_expected_ce_net": "measured",
            "expected_cost_truth_status": "PARTIALLY_MEASURED_COST",
            "fill_realism_status": "FILL_REALISM_PARTIAL_REPLAY",
        },
        expected_cost_used_decimal=0.00117825,
        book_staleness_ms=126,
    )

    assert metadata["expected_cost_truth_status"] == "PARTIALLY_MEASURED_COST"
    assert metadata["cost_source_used_for_break_even"] == "measured"
    assert metadata["cost_source_used_for_expected_ce_net"] == "measured"
    assert metadata["partial_fill_status"] == "PARTIAL_DEPTH_FILL"
    assert metadata["spread_bps_measured"] == pytest.approx(9.995)
    assert metadata["slippage_bps_measured"] == pytest.approx(0.25)
