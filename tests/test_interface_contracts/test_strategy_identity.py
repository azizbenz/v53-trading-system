from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    BetStructure,
    EngineId,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    Side,
    StrategyIdentity,
)


NOW_MS = 1_700_000_000_000


def _forecast_signal(**updates: object) -> ForecastSignalCandidate:
    payload = {
        "timestamp_ms": NOW_MS,
        "strategy_id": "strategy-a-breakout",
        "engine_id": EngineId.A,
        "pair": "btcusdt",
        "side": Side.BUY,
        "forecast_direction": 0.6,
        "forecast_strength": 11.0,
        "forecast_horizon_class": ForecastHorizonClass.SHORT,
        "forecast_target_class": ForecastTargetClass.DIRECTION_PLUS_STRENGTH,
        "bet_structure": BetStructure.BREAKOUT,
        "conditioning_state": (),
        "expected_cost": 1.25,
        "expected_break_even": 1.4,
        "expected_ce": 0.35,
        "expected_gain": 2.1,
        "versions": {"calibration_version": "cal-2026-04"},
    }
    payload.update(updates)
    if payload["conditioning_state"] == ():
        payload["conditioning_state"] = (
            {
                "timestamp_ms": NOW_MS,
                "family": "engine_internal",
                "code": "engine_internal.engine_a.conviction.high",
                "value": 0.9,
                "triggered_no_trade": False,
            },
        )
    return ForecastSignalCandidate(**payload)


class TestStrategyIdentity:
    def test_valid_identity_normalizes_fields(self) -> None:
        identity = StrategyIdentity(
            engine_id=EngineId.B,
            pair=" ethusdt ",
            regime_bucket=" Range_Bound ",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH,
            bet_structure=BetStructure.MEAN_REVERT,
            calibration_version=" cal-2026-04 ",
        )

        assert identity.pair == "ETHUSDT"
        assert identity.regime_bucket == "range_bound"
        assert identity.calibration_version == "cal-2026-04"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            StrategyIdentity(
                engine_id=EngineId.A,
                pair="BTCUSDT",
                regime_bucket="trending_up",
                forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
                bet_structure=BetStructure.BREAKOUT,
                calibration_version="cal-1",
                unexpected="boom",
            )

    def test_frozen_model(self) -> None:
        identity = StrategyIdentity(
            engine_id=EngineId.A,
            pair="BTCUSDT",
            regime_bucket="trending_up",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.BREAKOUT,
            calibration_version="cal-1",
        )
        with pytest.raises(ValidationError):
            identity.pair = "ETHUSDT"

    def test_blank_regime_bucket_rejected(self) -> None:
        with pytest.raises(ValidationError, match="regime_bucket must not be blank"):
            StrategyIdentity(
                engine_id=EngineId.A,
                pair="BTCUSDT",
                regime_bucket="   ",
                forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
                bet_structure=BetStructure.BREAKOUT,
                calibration_version="cal-1",
            )

    def test_blank_calibration_version_rejected(self) -> None:
        with pytest.raises(ValidationError, match="calibration_version must not be blank"):
            StrategyIdentity(
                engine_id=EngineId.A,
                pair="BTCUSDT",
                regime_bucket="trending_up",
                forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
                bet_structure=BetStructure.BREAKOUT,
                calibration_version="   ",
            )

    def test_canonical_key_is_stable(self) -> None:
        identity = StrategyIdentity(
            engine_id=EngineId.C,
            pair="SOLUSDT",
            regime_bucket="breakout",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.BREAKOUT,
            calibration_version="cal-c-7",
        )

        assert identity.canonical_key == (
            "engine_c:SOLUSDT:breakout:direction_plus_strength_plus_horizon:breakout:cal-c-7"
        )

    def test_from_forecast_signal_maps_tuple_fields(self) -> None:
        signal = _forecast_signal(
            engine_id=EngineId.D,
            pair="adausdt",
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.MEAN_REVERT,
        )

        identity = StrategyIdentity.from_forecast_signal(
            signal,
            regime_bucket="reentry_ready",
            calibration_version="cal-d-1",
        )

        assert identity.engine_id == EngineId.D
        assert identity.pair == "ADAUSDT"
        assert identity.regime_bucket == "reentry_ready"
        assert identity.forecast_target_class == ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
        assert identity.bet_structure == BetStructure.MEAN_REVERT
        assert identity.calibration_version == "cal-d-1"
