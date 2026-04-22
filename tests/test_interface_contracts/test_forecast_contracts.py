from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    BetStructure,
    ConditioningFamily,
    ConditioningRecord,
    EngineId,
    ForecastHorizonClass,
    ForecastSignalCandidate,
    ForecastTargetClass,
    Side,
    SignalCandidate,
    SignalType,
)
from interface_contracts.decision_contracts import SignalCandidate as DecisionSignalCandidate
from interface_contracts.domain_types import RegimeId
from interface_contracts.forecast_contracts import (
    SignalCandidate as ForecastModuleSignalCandidate,
    build_forecast_versions,
    build_scoring_conditioning_records,
    merge_reason_codes,
)


NOW_MS = 1_700_000_000_000


def _conditioning_record(
    *,
    family: ConditioningFamily = ConditioningFamily.SCORING,
    code: str = "scoring.cost_penalty.absorptive",
    triggered_no_trade: bool = False,
) -> ConditioningRecord:
    return ConditioningRecord(
        timestamp_ms=NOW_MS,
        family=family,
        code=code,
        value=0.25,
        triggered_no_trade=triggered_no_trade,
    )


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
        "confidence_band": 0.75,
        "conditioning_state": (_conditioning_record(),),
        "expected_cost": 1.25,
        "expected_break_even": 1.4,
        "expected_ce": 0.35,
        "expected_gain": 2.1,
        "invalidation_ref": " inv-a-1 ",
        "reason_codes": (" score.ok ", " engine_a.breakout "),
        "versions": {" engine_version ": " a-1.0 ", " calibration_version ": " cal-2026-04 "},
    }
    payload.update(updates)
    return ForecastSignalCandidate(**payload)


class TestForecastEnums:
    def test_forecast_target_class_values(self) -> None:
        assert {item.value for item in ForecastTargetClass} == {
            "direction_only",
            "direction_plus_strength",
            "direction_plus_strength_plus_horizon",
            "relative_forecast",
            "intrinsic_forecast",
        }

    def test_forecast_horizon_class_values(self) -> None:
        assert {item.value for item in ForecastHorizonClass} == {
            "intrabar",
            "short",
            "medium",
            "long",
        }

    def test_bet_structure_values(self) -> None:
        assert {item.value for item in BetStructure} == {
            "directional_long",
            "directional_short",
            "mean_revert",
            "breakout",
            "carry",
        }

    def test_conditioning_family_values(self) -> None:
        assert {item.value for item in ConditioningFamily} == {
            "engine_internal",
            "scoring",
            "hard_block",
            "portfolio",
        }


class TestConditioningRecord:
    def test_valid_record_normalizes_code(self) -> None:
        record = _conditioning_record(code=" hard_block.ac_mutual_exclusion.a_holding ")
        assert record.code == "hard_block.ac_mutual_exclusion.a_holding"

    def test_blank_code_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _conditioning_record(code="   ")

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ConditioningRecord(
                timestamp_ms=NOW_MS,
                family=ConditioningFamily.HARD_BLOCK,
                code="hard_block.pair_suspended",
                unexpected="boom",
            )


class TestForecastSignalCandidate:
    def test_valid_candidate_normalizes_strings(self) -> None:
        candidate = _forecast_signal()
        assert candidate.pair == "BTCUSDT"
        assert candidate.strategy_id == "strategy-a-breakout"
        assert candidate.invalidation_ref == "inv-a-1"
        assert candidate.reason_codes == ("score.ok", "engine_a.breakout")
        assert candidate.versions == {
            "engine_version": "a-1.0",
            "calibration_version": "cal-2026-04",
        }

    def test_conditioning_state_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(conditioning_state=())

    def test_reason_codes_reject_blank_values(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(reason_codes=("valid", " "))

    def test_versions_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(versions={})

    def test_versions_reject_blank_key(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(versions={" ": "a-1.0"})

    def test_versions_reject_blank_value(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(versions={"engine_version": " "})

    def test_expected_ce_must_be_finite(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(expected_ce=float("nan"))

    def test_expected_gain_must_be_finite(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(expected_gain=float("inf"))

    def test_forecast_direction_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(forecast_direction=1.5)

    def test_forecast_strength_upper_bound_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(forecast_strength=21.0)

    def test_confidence_band_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(confidence_band=1.2)

    def test_expected_cost_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(expected_cost=-0.01)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _forecast_signal(unexpected_field="boom")

    def test_candidate_is_frozen(self) -> None:
        candidate = _forecast_signal()
        with pytest.raises(ValidationError):
            candidate.pair = "ETHUSDT"

    def test_module_alias_does_not_replace_package_canonical_signal(self) -> None:
        assert SignalCandidate is DecisionSignalCandidate
        assert ForecastModuleSignalCandidate is ForecastSignalCandidate
        assert ForecastSignalCandidate is not DecisionSignalCandidate

    def test_from_decision_signal_maps_canonical_fields(self) -> None:
        canonical_signal = DecisionSignalCandidate(
            timestamp_ms=NOW_MS,
            pair="ethusdt",
            engine_id=EngineId.B,
            signal_type=SignalType.ENTRY,
            side=Side.SELL,
            confidence=0.8,
            regime=RegimeId.BREAKOUT,
            entry_price=3000.0,
            stop_loss=3050.0,
            take_profit=2900.0,
            max_hold_ms=3_600_000,
            reason="engine_b:breakout",
        )

        candidate = ForecastSignalCandidate.from_decision_signal(
            canonical_signal,
            strategy_id="strategy-b-breakout",
            forecast_direction=-0.7,
            forecast_strength=12.0,
            forecast_horizon_class=ForecastHorizonClass.MEDIUM,
            forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
            bet_structure=BetStructure.DIRECTIONAL_SHORT,
            conditioning_state=(
                _conditioning_record(
                    family=ConditioningFamily.ENGINE_INTERNAL,
                    code="engine_internal.breakout.confirmed",
                ),
            ),
            expected_cost=1.9,
            expected_break_even=2.1,
            expected_ce=0.48,
            expected_gain=4.2,
            versions={
                "engine_version": "b-1.4",
                "calibration_version": "cal-2026-04-15",
            },
            reason_codes=("engine_b.breakout",),
        )

        assert candidate.timestamp_ms == canonical_signal.timestamp_ms
        assert candidate.engine_id == EngineId.B
        assert candidate.pair == "ETHUSDT"
        assert candidate.side == Side.SELL
        assert candidate.strategy_id == "strategy-b-breakout"
        assert candidate.reason_codes == ("engine_b.breakout",)


class TestForecastContractHelpers:
    def test_merge_reason_codes_normalizes_and_deduplicates(self) -> None:
        assert merge_reason_codes(
            (" engine_a.cost.ok ", "engine_a.cost.ok"),
            ("scoring.penalty.context_soft",),
            (" engine_a.conviction.medium ",),
        ) == (
            "engine_a.cost.ok",
            "scoring.penalty.context_soft",
            "engine_a.conviction.medium",
        )

    def test_merge_reason_codes_rejects_blank_values(self) -> None:
        with pytest.raises(ValueError, match="reason_codes"):
            merge_reason_codes(("valid", " "),)

    def test_build_forecast_versions_normalizes_values(self) -> None:
        assert build_forecast_versions(
            scoring_version=" a.v1 ",
            calibration_profile_id=" engine_a.profile.v1 ",
            calibration_status=" READY_FOR_SHADOW ",
            physics_calibration_profile_id=" physics.profile.v1 ",
            physics_calibration_status=" TO_CALIBRATE ",
        ) == {
            "scoring_version": "a.v1",
            "calibration_profile_id": "engine_a.profile.v1",
            "calibration_status": "READY_FOR_SHADOW",
            "physics_calibration_profile_id": "physics.profile.v1",
            "physics_calibration_status": "TO_CALIBRATE",
        }

    def test_build_forecast_versions_rejects_blank_values(self) -> None:
        with pytest.raises(ValueError, match="versions"):
            build_forecast_versions(
                scoring_version=" ",
                calibration_profile_id="engine_a.profile.v1",
                calibration_status="READY_FOR_SHADOW",
                physics_calibration_profile_id="physics.profile.v1",
                physics_calibration_status="TO_CALIBRATE",
            )

    def test_build_scoring_conditioning_records_builds_scoring_family_entries(self) -> None:
        records = build_scoring_conditioning_records(
            timestamp_ms=NOW_MS,
            penalties=(("context_soft", 0.2), ("risk_soft", 0.1)),
        )

        assert tuple(record.family for record in records) == (
            ConditioningFamily.SCORING,
            ConditioningFamily.SCORING,
        )
        assert tuple(record.code for record in records) == (
            "scoring.penalty.context_soft",
            "scoring.penalty.risk_soft",
        )

    def test_build_scoring_conditioning_records_rejects_blank_penalty_id(self) -> None:
        with pytest.raises(ValueError, match="penalty_id"):
            build_scoring_conditioning_records(
                timestamp_ms=NOW_MS,
                penalties=((" ", 0.2),),
            )
