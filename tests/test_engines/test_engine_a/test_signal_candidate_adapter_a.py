from __future__ import annotations

from engines.engine_a.context_validator_a import ContextVerdict
from engines.engine_a.conviction_builder_a import ConvictionLevel, TierSuggestion
from engines.engine_a.cost_feasibility_a import CostVerdict
from engines.engine_a.engine_a_runner import EngineADecision, EngineAInput, EngineAOutput
from engines.engine_a.signal_candidate_adapter import build_signal_candidate_a
from engines.engine_a.structure_detector_a import StructureVerdict
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
STRATEGY_ID = "strategy-a-test-v1"
TIMESTAMP_MS = 1_700_000_000_000


def _make_emit_output_a(**overrides: object) -> EngineAOutput:
    defaults: dict[str, object] = {
        "pair": PAIR,
        "decision": EngineADecision.EMIT,
        "raw_score": 0.75,
        "block_scores": {"structure": 0.8, "context": 0.7},
        "conviction": ConvictionLevel.HIGH,
        "tier_suggestion": TierSuggestion.TIER_1,
        "expected_cost": 0.001,
        "ce_expected": 0.008,
        "ev_net": 0.007,
        "holding_hours": 4.0,
        "scoring_version": "v_test_1",
        "calibration_profile_id": "test_profile_a",
        "calibration_status": "active",
        "physics_calibration_profile_id": "test_physics",
        "physics_calibration_status": "active",
        "structure_verdict": StructureVerdict.FAVORABLE,
        "context_verdict": ContextVerdict.CONFIRMING,
        "cost_verdict": CostVerdict.FEASIBLE,
    }
    defaults.update(overrides)
    return EngineAOutput(**defaults)


def _make_signal_candidate_a(
    *,
    side: Side = Side.BUY,
    max_hold_ms: int | None = 4 * 3600 * 1000,
) -> DecisionSignalCandidate:
    return DecisionSignalCandidate(
        timestamp_ms=TIMESTAMP_MS,
        pair=PAIR,
        engine_id=EngineId.A,
        signal_type=SignalType.ENTRY,
        side=side,
        confidence=0.75,
        regime=RegimeId.HIGH_VOLATILITY,
        entry_price=50_000.0,
        max_hold_ms=max_hold_ms,
        reason="engine_a:high",
    )


def _make_engine_inputs_a(**overrides: object) -> EngineAInput:
    defaults: dict[str, object] = {
        "pair": PAIR,
        "direction_score": 0.8,
        "continuation_score": 0.7,
        "structure_quality": 0.8,
        "zone_proximity": 0.6,
        "trend_stability": 0.7,
        "entry_price": 50_000.0,
        "expected_gain": 0.01,
        "candidate_size": 0.1,
        "delta_safe": 0.005,
        "ce_min": 0.002,
        "scoring_version": "v_test_1",
        "holding_period": 4.0,
        "realized_vol_current": 0.002,
        "realized_kernel_vol_scale": 0.003,
    }
    defaults.update(overrides)
    return EngineAInput(**defaults)


def test_returns_none_when_strategy_id_empty() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id="  ",
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is None


def test_returns_none_when_decision_no_trade() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(decision=EngineADecision.NO_TRADE),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is None


def test_emits_forecast_signal_correct_engine_id() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.engine_id == EngineId.A
    assert result.strategy_id == STRATEGY_ID
    assert result.pair == PAIR


def test_bet_structure_buy_is_directional_long() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(side=Side.BUY),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.bet_structure == BetStructure.DIRECTIONAL_LONG


def test_bet_structure_sell_is_directional_short() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(side=Side.SELL),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.bet_structure == BetStructure.DIRECTIONAL_SHORT


def test_forecast_strength_within_cap_20() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert 0.0 <= result.forecast_strength <= 20.0


def test_conditioning_state_has_minimum_records() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert len(result.conditioning_state) >= 8


def test_reason_codes_include_conviction() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert any("conviction" in code for code in result.reason_codes)


def test_forecast_target_class_is_direction_plus_strength_plus_horizon() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert (
        result.forecast_target_class
        == ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
    )


def test_horizon_class_medium_for_4h_hold() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(max_hold_ms=4 * 3600 * 1000),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert result.forecast_horizon_class == ForecastHorizonClass.MEDIUM


def test_volatility_proxy_uses_kernel_scale_when_current_absent() -> None:
    result = build_signal_candidate_a(
        _make_emit_output_a(),
        _make_signal_candidate_a(),
        strategy_id=STRATEGY_ID,
        engine_inputs=_make_engine_inputs_a(
            realized_vol_current=None,
            realized_kernel_vol_scale=0.004,
        ),
        timestamp_ms=TIMESTAMP_MS,
    )

    assert result is not None
    assert "engine_a.forecast.volatility_proxy.realized_kernel_scale" in result.reason_codes
