from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_replay_runtime.engine_math_canary_audit import (
    ensure_synthetic_strategy_ladder_canary_fixture,
    reconstruct_native_candidate_case,
    run_synthetic_strategy_ladder_e2e,
)
from local_replay_runtime.strategy_ladder_economic_provenance import EconomicProvenance
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)


def _load_metadata_row(asset_root: Path, scenario_id: str) -> dict[str, object]:
    rows = [
        json.loads(line)
        for line in (asset_root / "metadata.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return next(row for row in rows if row["scenario_id"] == scenario_id)


def test_synthetic_strategy_ladder_e2e_matches_oracle(tmp_path: Path) -> None:
    asset_root = ensure_synthetic_strategy_ladder_canary_fixture(
        tmp_path / "synthetic_strategy_ladder_canary"
    )
    report = run_synthetic_strategy_ladder_e2e(asset_root, runtime_mode="TEST")

    assert report["all_ok"] is True
    assert report["scenario_count"] == 9

    cases = {(row["engine_id"], row["scenario_id"]): row for row in report["results"]}
    assert cases[("engine_a", "SCENARIO_A_LONG_PASS_NATIVE")]["actual_decision"] == "emit"
    assert cases[("engine_a", "SCENARIO_A_NEGATIVE_DIRECTION_BLOCK")]["actual_decision"] == "no_trade"
    assert cases[("engine_b", "SCENARIO_B_EXCESS_PASS")]["actual_decision"] == "emit"
    assert cases[("engine_b", "SCENARIO_B_NO_EXCESS")]["actual_decision"] == "no_trade"
    assert cases[("engine_b", "SCENARIO_B_COST_FAIL")]["actual_decision"] == "no_trade"
    assert cases[("engine_c", "SCENARIO_C_BREAKOUT_PASS")]["actual_decision"] == "emit"
    assert cases[("engine_c", "SCENARIO_C_NO_BREAKOUT")]["actual_builder_status"] == "ENGINE_C_INPUT_BUILDER_NO_BREAKOUT"
    assert cases[("engine_d", "SCENARIO_D_REENTRY_PASS")]["actual_decision"] == "emit"
    assert cases[("engine_d", "SCENARIO_D_NO_HISTORY")]["actual_decision"] == "no_trade"


def test_synthetic_canary_truth_source_is_forbidden_outside_test(tmp_path: Path) -> None:
    asset_root = ensure_synthetic_strategy_ladder_canary_fixture(
        tmp_path / "synthetic_strategy_ladder_canary"
    )
    with pytest.raises(ValueError, match="GOVERNED_SYNTHETIC_CANARY"):
        run_synthetic_strategy_ladder_e2e(asset_root, runtime_mode="LOCAL_REPLAY")


def test_b2_proxy_expected_edge_never_becomes_truth(tmp_path: Path) -> None:
    asset_root = ensure_synthetic_strategy_ladder_canary_fixture(
        tmp_path / "synthetic_strategy_ladder_canary"
    )
    row = _load_metadata_row(asset_root, "SCENARIO_B_EXCESS_PASS")
    candidate = StrategyLadderCandidateEvent(
        candidate_id=str(row["candidate_id"]),
        pair=str(row["pair"]),
        timeframe=str(row["timeframe"]),
        engine_id=str(row["engine_id"]),
        strategy_id=str(row["engine_id"]),
        timestamp_ms=int(row["timestamp_ms"]),
        compatibility_payload={"planned_notional": float(row["planned_notional"])},
        candidate_source="TEST",
        candidate_data_source_label="TEST",
    )
    window = StrategyLadderRawWindowManifest(
        candidate_id=str(row["candidate_id"]),
        pair=str(row["pair"]),
        engine_id=str(row["engine_id"]),
        timestamp_ms=int(row["timestamp_ms"]),
        window_start_ms=int(row["window_start_ms"]),
        window_end_ms=int(row["window_end_ms"]),
        raw_trade_path=str(row["raw_trade_path"]),
        raw_book_path=str(row["raw_book_path"]),
        raw_book_delta_path=str(row["raw_book_delta_path"]),
        raw_ohlcv_path=str(row["raw_ohlcv_path"]),
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        window_extraction_status="RAW_WINDOW_READY",
        raw_sources_used=("trades", "orderbook", "klines"),
        source_coverage_status="RAW_WINDOW_SOURCE_READY",
    )
    provenance = EconomicProvenance(
        expected_edge_bps=30.0,
        expected_edge_provenance="EXPECTED_EDGE_PROXY_BLOCKED",
        spread_bps=4.0,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=2.0,
        slippage_provenance="MEASURED_FROM_KYLE_LAMBDA",
        latency_penalty_bps=0.5,
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=10.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measurement_warnings=(),
        expected_edge_model_status="EXPECTED_EDGE_PROXY_BLOCKED",
        expected_edge_model_artifact_hash="TEST",
        expected_edge_model_feature_hash="TEST",
    )

    case = reconstruct_native_candidate_case(
        candidate=candidate,
        window=window,
        economic_provenance=provenance,
    )

    assert case.engine_input_payload["expected_gain"] == 0.0
