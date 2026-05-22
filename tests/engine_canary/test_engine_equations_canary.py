from __future__ import annotations

import json
from pathlib import Path

import pytest

from engines.engine_a.engine_a_runner import EngineAInput, run_engine_a
from engines.engine_a.structure_detector_a import StructureInput, StructureVerdict, detect_structure
from engines.engine_b.cost_feasibility_b import CostVerdictB, CostInputB, check_cost_feasibility_b
from engines.engine_b.excess_detector_b import ExcessInput, ExcessVerdict, detect_excess
from engines.engine_b.engine_b_runner import EngineBInput, run_engine_b
from engines.engine_c.engine_c_runner import EngineCInput, run_engine_c
from engines.engine_d.engine_d_models import EngineDInput
from engines.engine_d.engine_d_runner import run_engine_d
from local_replay_runtime.engine_math_canary_audit import (
    _engine_c_emit_payload,
    _engine_d_emit_payload,
    bps_to_decimal,
    build_expected_cost_decimal,
    decimal_to_bps,
    ensure_synthetic_strategy_ladder_canary_fixture,
    percent_to_decimal,
)
from local_replay_runtime.strategy_ladder_replay_evidence import (
    build_measured_slippage_payload,
    build_measured_spread_payload,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from sharia_compliance import ShariaTradeRequest, authorize_trade_type, load_sharia_policy


def test_engine_a_structure_detector_canary_cases() -> None:
    cases = (
        (
            "favorable",
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.25,
                continuation_score=0.50,
                structure_quality=1.0,
                zone_proximity=1.0,
                trend_stability=1.0,
            ),
            0.65,
            StructureVerdict.FAVORABLE,
        ),
        (
            "marginal",
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.25,
                continuation_score=0.70,
                structure_quality=0.50,
                zone_proximity=0.0,
                trend_stability=0.0,
            ),
            0.35,
            StructureVerdict.MARGINAL,
        ),
        (
            "unfavorable",
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.25,
                continuation_score=0.50,
                structure_quality=0.0,
                zone_proximity=0.0,
                trend_stability=0.0,
            ),
            0.20,
            StructureVerdict.UNFAVORABLE,
        ),
        (
            "min_direction_blocks",
            StructureInput(
                pair="BTCUSDT",
                direction_score=0.10,
                continuation_score=1.0,
                structure_quality=1.0,
                zone_proximity=1.0,
                trend_stability=1.0,
            ),
            0.73,
            StructureVerdict.UNFAVORABLE,
        ),
    )

    for _, inputs, expected_score, expected_verdict in cases:
        result = detect_structure(inputs)
        assert result.structure_score == pytest.approx(expected_score, abs=1e-12)
        assert result.verdict == expected_verdict


def test_engine_a_negative_direction_never_becomes_long() -> None:
    structure_result = detect_structure(
        StructureInput(
            pair="BTCUSDT",
            direction_score=-0.50,
            continuation_score=0.80,
            structure_quality=0.80,
            zone_proximity=0.80,
            trend_stability=0.80,
        )
    )
    assert structure_result.verdict == StructureVerdict.FAVORABLE

    output = run_engine_a(
        EngineAInput(
            pair="BTCUSDT",
            direction_score=-0.50,
            continuation_score=0.80,
            structure_quality=0.80,
            zone_proximity=0.80,
            trend_stability=0.80,
            regime="trending_up",
            regime_favorability=0.8,
            regime_confidence=0.8,
            pair_health=0.8,
            data_freshness=0.9,
            flow_coherence=0.8,
            flow_score=0.8,
            cost_preference_score=0.8,
            delta_confirmation=0.9,
            competition_density=0.2,
            expected_gain=0.01,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=4.0,
            delta_safe=0.0005,
            ce_min=0.0001,
            entry_price=100.0,
            realized_vol_current=0.02,
            atr=2.0,
            scoring_version="A_v1",
        )
    )

    assert output.decision.value == "no_trade"
    assert "engine_internal.engine_a.direction.non_long" in output.reason_codes
    assert "engine_a.input.non_long_direction" in output.reason_codes


@pytest.mark.parametrize(
    ("z_score", "valid", "expected_verdict"),
    (
        (0.50, True, ExcessVerdict.NO_EXCESS),
        (0.99, True, ExcessVerdict.NO_EXCESS),
        (1.00, True, ExcessVerdict.MARGINAL),
        (1.49, True, ExcessVerdict.MARGINAL),
        (1.50, True, ExcessVerdict.EXPLOITABLE),
        (-1.50, True, ExcessVerdict.EXPLOITABLE),
        (0.0, False, ExcessVerdict.INVALID),
    ),
)
def test_engine_b_excess_threshold_cases(
    z_score: float,
    valid: bool,
    expected_verdict: ExcessVerdict,
) -> None:
    result = detect_excess(
        ExcessInput(
            pair="BTCUSDT",
            z_score=z_score,
            z_score_valid=valid,
            structure_is_range=0.5,
            recent_expansion=0.0,
        )
    )
    assert result.verdict == expected_verdict


def test_engine_b_positive_z_remains_non_long() -> None:
    output = run_engine_b(
        EngineBInput(
            pair="BTCUSDT",
            current_price=103.0,
            local_mean=100.0,
            local_std=1.5,
            expected_gain=0.003,
            expected_cost=0.001,
            candidate_size=100.0,
            holding_period=2.0,
        )
    )
    assert output.decision.value == "no_trade"
    assert "engine_internal.engine_b.direction.non_long" in output.reason_codes


def test_engine_b_cost_threshold_cases() -> None:
    just_at_break_even = check_cost_feasibility_b(
        CostInputB(
            pair="BTCUSDT",
            expected_gain=0.0010115,
            expected_cost=0.0002115,
            candidate_size=100.0,
            holding_period=2.0,
            delta_safe=0.0008,
            ce_min=0.0002,
        )
    )
    just_below_break_even = check_cost_feasibility_b(
        CostInputB(
            pair="BTCUSDT",
            expected_gain=0.0010114,
            expected_cost=0.0002115,
            candidate_size=100.0,
            holding_period=2.0,
            delta_safe=0.0008,
            ce_min=0.0002,
        )
    )
    ce_block = check_cost_feasibility_b(
        CostInputB(
            pair="BTCUSDT",
            expected_gain=0.0011,
            expected_cost=0.0002115,
            candidate_size=100.0,
            holding_period=10.0,
            delta_safe=0.0008,
            ce_min=0.0002,
        )
    )

    assert just_at_break_even.verdict == CostVerdictB.INFEASIBLE
    assert just_below_break_even.verdict == CostVerdictB.INFEASIBLE
    assert ce_block.verdict == CostVerdictB.MARGINAL


def test_engine_c_direct_threshold_failures_map_to_reason_codes() -> None:
    breakout_score_fail = dict(_engine_c_emit_payload())
    breakout_score_fail["breakout_strength"] = 0.20
    breakout_score_fail["range_quality"] = 0.50
    breakout_score_fail["compression_quality"] = 0.50
    breakout_score_fail["volume_confirmation"] = 0.50
    breakout_score_fail["range_low"] = 99.0
    breakout_score_fail["range_high"] = 101.0
    breakout_score_fail["entry_price"] = 101.2
    breakout_score_fail["breakout_level"] = 101.0
    output_breakout = run_engine_c(EngineCInput.model_validate(breakout_score_fail))
    assert output_breakout.decision.value == "no_trade"
    assert "engine_c.no_trade.breakout_unstructured" in output_breakout.reason_codes

    fake_breakout_fail = dict(_engine_c_emit_payload())
    fake_breakout_fail["retrace_risk"] = 0.8
    fake_breakout_fail["rejection_wick_ratio"] = 0.9
    fake_breakout_fail["volume_confirmation"] = 0.2
    output_fake = run_engine_c(EngineCInput.model_validate(fake_breakout_fail))
    assert output_fake.decision.value == "no_trade"
    assert "engine_c.no_trade.fake_breakout_blocked" in output_fake.reason_codes


def test_engine_d_missing_history_and_concentration_failures() -> None:
    weak_history = dict(_engine_d_emit_payload())
    weak_history["prior_trade_quality"] = 0.20
    output_history = run_engine_d(EngineDInput.model_validate(weak_history))
    assert output_history.decision.value == "no_trade"
    assert "engine_d.no_trade.history_weak" in output_history.reason_codes

    concentration_block = dict(_engine_d_emit_payload())
    concentration_block["concentration_headroom"] = 0.2
    concentration_block["reentry_lateness"] = 0.9
    concentration_block["continuation_room"] = 1.0
    concentration_block["marginal_edge"] = 1.0
    output_concentration = run_engine_d(EngineDInput.model_validate(concentration_block))
    assert output_concentration.decision.value == "no_trade"
    assert "engine_d.no_trade.concentration_blocked" in output_concentration.reason_codes


def test_unit_conversions_and_expected_cost_sum() -> None:
    assert bps_to_decimal(10.0) == pytest.approx(0.001)
    assert bps_to_decimal(1.0) == pytest.approx(0.0001)
    assert decimal_to_bps(0.00121) == pytest.approx(12.1)
    assert percent_to_decimal(10.0) == pytest.approx(0.10)
    assert build_expected_cost_decimal(
        spread_bps=0.5,
        slippage_bps=0.1,
        fee_bps=10.0,
        latency_penalty_bps=1.5,
    ) == pytest.approx(0.00121)


def test_orderbook_depth_and_spread_canary(tmp_path: Path) -> None:
    fixture_root = ensure_synthetic_strategy_ladder_canary_fixture(tmp_path / "synthetic_strategy_ladder_canary")
    metadata_path = fixture_root / "metadata.jsonl"
    rows = [json.loads(line) for line in metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    scenario = next(row for row in rows if row["scenario_id"] == "SCENARIO_A_LONG_PASS_NATIVE")

    candidate = StrategyLadderCandidateEvent(
        candidate_id="spread-check",
        pair="BTCUSDT",
        timeframe="1m",
        engine_id="engine_b",
        strategy_id="engine_b",
        timestamp_ms=int(scenario["timestamp_ms"]),
        compatibility_payload={"planned_notional": 1000.0, "side": "buy"},
        candidate_source="TEST",
        candidate_data_source_label="TEST",
    )
    window = StrategyLadderRawWindowManifest(
        candidate_id="spread-check",
        pair="BTCUSDT",
        engine_id="engine_b",
        timestamp_ms=int(scenario["timestamp_ms"]),
        window_start_ms=int(scenario["window_start_ms"]),
        window_end_ms=int(scenario["window_end_ms"]),
        raw_trade_path=scenario["raw_trade_path"],
        raw_book_path=scenario["raw_book_path"],
        raw_book_delta_path=scenario["raw_book_delta_path"],
        raw_ohlcv_path=scenario["raw_ohlcv_path"],
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        window_extraction_status="RAW_WINDOW_READY",
        raw_sources_used=("trades", "orderbook", "klines"),
        source_coverage_status="RAW_WINDOW_SOURCE_READY",
    )

    spread = build_measured_spread_payload(
        window_manifest=window,
        decision_timestamp_ms=int(scenario["timestamp_ms"]),
    )
    slippage = build_measured_slippage_payload(
        candidate=candidate,
        window_manifest=window,
        planned_notional=1000.0,
        decision_timestamp_ms=int(scenario["timestamp_ms"]),
    )

    assert spread["status"] == "SPREAD_MEASURED_FROM_BOOK"
    assert spread["mid_price"] == pytest.approx(100.05)
    assert spread["spread_abs"] == pytest.approx(0.10)
    assert spread["spread_bps"] == pytest.approx(9.995002, rel=1e-6)
    assert slippage["status"] == "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
    assert slippage["depth_fill_ratio"] > 0.0


def test_sharia_spot_long_only_canary() -> None:
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    permitted = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-buy",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
        ),
        policy,
    )
    assert permitted.allowed is True

    short_blocked = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-short",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="short",
        ),
        policy,
    )
    assert short_blocked.allowed is False
    assert short_blocked.reason_code == "SHORT_FORBIDDEN"

    futures_blocked = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-futures",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={"trade_mode": "FUTURES", "leverage": 2},
        ),
        policy,
    )
    assert futures_blocked.allowed is False
    assert futures_blocked.reason_code == "NON_SPOT_FORBIDDEN"
