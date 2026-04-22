from __future__ import annotations

from engines.engine_b.anti_breakout_filter_b import BreakoutVerdict
from engines.engine_b.conviction_builder_b import ConvictionLevelB, TierSuggestionB
from engines.engine_b.cost_feasibility_b import CostVerdictB
from engines.engine_b.engine_b_runner import EngineBDecision, EngineBInput, EngineBOutput
from engines.engine_b.excess_detector_b import ExcessVerdict
from engines.engine_b.signal_candidate_adapter import build_signal_candidate_b
from interface_contracts.decision_contracts import (
    SignalCandidate as DecisionSignalCandidate,
    SignalType,
)
from interface_contracts.domain_types import EngineId, RegimeId, Side
from interface_contracts.forecast_contracts import (
    BetStructure,
    ForecastHorizonClass,
    ForecastTargetClass,
)

PAIR = "BTCUSDT"
STRATEGY_ID = "strategy-b-test-v1"
TIMESTAMP_MS = 1_700_000_000_000


def _make_emit_output_b(**overrides: object) -> EngineBOutput:
    defaults: dict[str, object] = {
        "pair": PAIR,
        "decision": EngineBDecision.EMIT,
        "raw_score": 0.55,
        "penalized_score": 0.45,
        "excess_score": 0.65,
        "breakout_score": 0.15,
        "conviction": ConvictionLevelB.MEDIUM,
        "tier_suggestion": TierSuggestionB.TIER_1,
        "excess_verdict": ExcessVerdict.EXPLOITABLE,
        "breakout_verdict": BreakoutVerdict.CLEAR,
        "cost_verdict": CostVerdictB.FEASIBLE,
        "expected_cost": 0.001,
        "ce_expected": 0.005,
        "ev_net": 0.002,
        "expected_holding_hours": 2.0,
        "scoring_version": "B_v1",
        "calibration_profile_id": "test_profile_b",
        "calibration_status": "active",
        "physics_calibration_profile_id": "test_physics_b",
        "physics_calibration_status": "active",
        "reason_codes": (),
    }
    defaults.update(overrides)
    return EngineBOutput(**defaults)


def _make_signal_candidate_b(
    *,
    side: Side = Side.BUY,
    max_hold_ms: int | None = 2 * 3600 * 1000,
) -> DecisionSignalCandidate:
    return DecisionSignalCandidate(
        timestamp_ms=TIMESTAMP_MS,
        pair=PAIR,
        engine_id=EngineId.B,
        signal_type=SignalType.ENTRY,
        side=side,
        confidence=0.65,
        regime=RegimeId.RANGE_BOUND,
        entry_price=50_000.0,
        max_hold_ms=max_hold_ms,
        reason="engine_b:medium",
    )


def _make_engine_inputs_b(**overrides: object) -> EngineBInput:
    defaults: dict[str, object] = {
        "pair": PAIR,
        "current_price": 50_000.0,
        "local_mean": 50_100.0,
        "local_std": 50.0,
        "expected_gain": 0.003,
        "expected_cost": 0.001,
        "candidate_size": 100.0,
        "holding_period": 2.0,
        "delta_safe": 0.0008,
        "ce_min": 0.002,
        "scoring_version": "B_v1",
    }
    defaults.update(overrides)
    return EngineBInput(**defaults)


def test_returns_none_when_strategy_id_empty() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=" ",
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is None


def test_returns_none_when_decision_no_trade() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(decision=EngineBDecision.NO_TRADE),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is None


def test_emits_forecast_signal_correct_engine_id() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.engine_id == EngineId.B
    assert result.strategy_id == STRATEGY_ID
    assert result.pair == PAIR


def test_bet_structure_always_mean_revert() -> None:
    for side in (Side.BUY, Side.SELL):
        result = build_signal_candidate_b(
            _make_emit_output_b(),
            _make_signal_candidate_b(side=side),
            strategy_id=STRATEGY_ID,
            engine_inputs=_make_engine_inputs_b(),
            timestamp_ms=TIMESTAMP_MS,
        )

        assert result is not None
        assert result.bet_structure == BetStructure.MEAN_REVERT


def test_forecast_strength_within_cap_15() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert 0.0 <= result.forecast_strength <= 15.0


def test_conditioning_state_has_minimum_records() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert len(result.conditioning_state) >= 8


def test_reason_codes_include_conviction() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert any("conviction" in code for code in result.reason_codes)


def test_forecast_target_class_is_direction_plus_strength_plus_horizon() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert (
        result.forecast_target_class
        == ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )


def test_horizon_class_medium_when_no_max_hold_ms() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(max_hold_ms=None),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.forecast_horizon_class == ForecastHorizonClass.MEDIUM


def test_volatility_proxy_uses_local_std_when_available() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(local_std=50.0, current_price=50_000.0),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert "engine_b.forecast.volatility_proxy.local_std_relative" in result.reason_codes


def test_reason_codes_include_optional_toxic_flow_markers() -> None:
    result = build_signal_candidate_b(
        _make_emit_output_b(
            reason_codes=(
                "b.toxic_flow_fade",
                "b.toxic_flow_fade_suppressed.correlation",
            )
        ),
        _make_signal_candidate_b(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_b(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert "b.toxic_flow_fade" in result.reason_codes
    assert "b.toxic_flow_fade_suppressed.correlation" in result.reason_codes
    conditioning_codes = {record.code for record in result.conditioning_state}
    assert "engine_internal.engine_b.toxic_flow_fade.active" in conditioning_codes
    assert (
        "engine_internal.engine_b.toxic_flow_fade.suppressed.correlation"
        in conditioning_codes
    )
