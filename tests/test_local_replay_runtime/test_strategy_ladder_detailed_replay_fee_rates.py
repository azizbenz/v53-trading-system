from __future__ import annotations

import pytest

from local_replay_runtime.strategy_ladder_detailed_replay import (
    _fee_source_status_from_payload,
    _row_from_candidate,
)
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.replay_execution_contracts import (
    ReplayExecutionEvaluationRequest,
)
from local_replay_runtime.replay_execution_runtime import evaluate_replay_execution
from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent


def test_detailed_replay_uses_measured_fee_bps_as_execution_fee_rates() -> None:
    candidate = StrategyLadderCandidateEvent(
        candidate_id="fee-candidate-1",
        timestamp_ms=1_700_000_000_000,
        pair="BTCUSDT",
        timeframe="1m",
        engine_id="engine_b",
        strategy_id="strategy_ladder",
        compatibility_payload={
            "pair": "BTCUSDT",
            "close_price": 100.0,
            "expected_edge_bps": 25.0,
            "spread_bps": 1.0,
            "slippage_bps": 2.0,
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
            "planned_notional": 100.0,
            "target_decision_state": "selected",
        },
    )

    row, _assessment, _planned_notional = _row_from_candidate(
        candidate=candidate,
        capital_bucket=100,
        window_manifest=None,
    )

    assert row.maker_fee_rate == pytest.approx(0.001)
    assert row.taker_fee_rate == pytest.approx(0.001)


def test_detailed_replay_fee_rates_clear_fee_model_proxy() -> None:
    candidate = StrategyLadderCandidateEvent(
        candidate_id="fee-candidate-2",
        timestamp_ms=1_700_000_000_000,
        pair="BTCUSDT",
        timeframe="1m",
        engine_id="engine_b",
        strategy_id="strategy_ladder",
        compatibility_payload={
            "pair": "BTCUSDT",
            "close_price": 100.0,
            "expected_edge_bps": 25.0,
            "spread_bps": 1.0,
            "slippage_bps": 2.0,
            "fee_bps": 10.0,
            "fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
            "planned_notional": 100.0,
            "target_decision_state": "selected",
        },
    )
    row, _assessment, _planned_notional = _row_from_candidate(
        candidate=candidate,
        capital_bucket=100,
        window_manifest=None,
    )
    result = evaluate_replay_execution(
        ReplayExecutionEvaluationRequest(
            dataset=HistoricalReplayDataset.from_records(
                dataset_id="fee-candidate-2",
                source_path="synthetic",
                records=(row,),
                source="unit_test",
            )
        )
    )

    payload = result.parity_diagnostics_payload
    assert payload["fee_model_source"] == "CANONICAL_EXECUTION_COST_METER"
    assert "FEE_MODEL_PROXY" not in payload["execution_fidelity_gap_codes"]
    # Updated 2026-05-27 (Patches BACKBONE-PARITY-P1-S1 + S2 + S5) —
    # hard_block_gate + scoring_ranking + risk_filter now default to
    # canonical evaluators (BlockerCondition all False / RankingWeights
    # operational / RiskLimits 1e6 caps). The fee_rates test row has
    # target_decision_state="selected" and planned_notional>0 so
    # execution_intent is non-None and risk_filter evaluates canonically.
    # +3 CANONICAL, -3 LOCAL_REPLAY vs Codex baseline.
    assert payload["backbone_surface_report"]["status_counts"] == {
        "CANONICAL_BACKBONE_USED": 8,
        "LOCAL_REPLAY_FALLBACK_USED": 11,
        "NO_SURFACE_RESULT_AVAILABLE": 2,
    }
    assert payload["backbone_surface_report"]["promotion_allowed"] is False
    spread_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "spread_measurement"
    )
    assert spread_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"


def test_fee_source_status_normalizes_measured_metadata_for_replay_summary() -> None:
    assert (
        _fee_source_status_from_payload(
            {"fee_source_status": "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"}
        )
        == "FEE_SOURCE_EXCHANGE_METADATA"
    )
    assert (
        _fee_source_status_from_payload(
            {"fee_source_status": "MEASURED_FROM_VENUE_API_OVERRIDE"}
        )
        == "FEE_SOURCE_PROVEN"
    )
