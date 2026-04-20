"""Tests for the native engine coordination seam."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side, RefusalCategory
from protocols import (
    EpisodeCloseReason,
    EpisodeRef,
    EngineCoordinationAction,
    EngineCoordinationInput,
    EngineCoordinationThresholds,
    evaluate_engine_coordination,
)


_NOW_NS = 1_700_000_000_000_000_000
_ONE_HOUR_NS = 3_600_000_000_000


def _episode_ref(**overrides: object) -> EpisodeRef:
    payload: dict[str, object] = {
        "episode_id": uuid4(),
        "engine_id_of_origin": EngineId.A,
        "pair": "BTCUSDT",
        "side": Side.BUY,
        "entry_level": Decimal("100"),
        "exit_level": Decimal("102"),
        "bet_structure": BetStructure.DIRECTIONAL_LONG,
        "forecast_horizon_class": ForecastHorizonClass.MEDIUM,
        "forecast_target_class": ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        "closed_at_ns": _NOW_NS - _ONE_HOUR_NS,
        "close_reason": EpisodeCloseReason.TAKE_PROFIT,
        "realized_pnl_decimal": Decimal("2.0"),
    }
    payload.update(overrides)
    return EpisodeRef(**payload)


def _coordination_input(**overrides: object) -> EngineCoordinationInput:
    payload: dict[str, object] = {
        "evaluated_at_ns": _NOW_NS,
        "engine_id": EngineId.C,
        "pair": "BTCUSDT",
        "side": Side.BUY,
    }
    payload.update(overrides)
    return EngineCoordinationInput(**payload)


def test_c_hard_blocks_when_a_holding_block_is_active() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(a_holding_block_active=True),
    )

    assert outcome.blocked is True
    assert outcome.action == EngineCoordinationAction.HARD_BLOCK
    assert outcome.reason_codes == ("hard_block.ac_mutual_exclusion.a_holding",)
    assert outcome.rule_hits == ("R-AC-1",)
    assert outcome.refusal_record is not None
    assert outcome.refusal_record.category == RefusalCategory.HARD_BLOCK
    assert outcome.conditioning_state[0].triggered_no_trade is True


def test_c_hard_blocks_on_recent_a_fire_within_threshold() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            recent_a_fire_same_setup_at_ns=_NOW_NS - 2 * _ONE_HOUR_NS,
        ),
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.ac_recent_fire",)
    assert outcome.rule_hits == ("R-AC-2",)


def test_c_permits_after_recent_a_fire_window_expires() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            recent_a_fire_same_setup_at_ns=_NOW_NS - 6 * _ONE_HOUR_NS,
        ),
        thresholds=EngineCoordinationThresholds(recent_fire_block_ns=4 * _ONE_HOUR_NS),
    )

    assert outcome.blocked is False
    assert outcome.action == EngineCoordinationAction.PERMIT
    assert outcome.refusal_record is None


def test_d_hard_blocks_without_first_episode_ref() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(engine_id=EngineId.D),
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_no_historical_linkage",)
    assert outcome.rule_hits == ("R-D-1",)


def test_d_hard_blocks_on_mismatched_episode_ref() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            engine_id=EngineId.D,
            first_episode_ref=_episode_ref(pair="ETHUSDT"),
        ),
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_no_historical_linkage",)
    assert outcome.refusal_record is not None


def test_d_hard_blocks_when_consecutive_stops_require_reset() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            engine_id=EngineId.D,
            first_episode_ref=_episode_ref(),
            consecutive_d_stop_count=1,
            last_d_stop_at_ns=_NOW_NS - _ONE_HOUR_NS,
        ),
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_consecutive_stops_reset_required",)
    assert outcome.rule_hits == ("R-D-2",)


def test_d_failsafe_override_permits_reentry() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            engine_id=EngineId.D,
            first_episode_ref=_episode_ref(),
            consecutive_d_stop_count=1,
            last_d_stop_at_ns=_NOW_NS - 30 * _ONE_HOUR_NS,
            d_failsafe_override_available=True,
        ),
    )

    assert outcome.blocked is False
    assert outcome.action == EngineCoordinationAction.SIZE_REDUCED
    assert outcome.reason_codes == ("coordination.d_failsafe_override",)
    assert outcome.rule_hits == ("R-D-3",)


def test_d_permits_with_half_size_multiplier_and_resolved_size() -> None:
    outcome = evaluate_engine_coordination(
        _coordination_input(
            engine_id=EngineId.D,
            first_episode_ref=_episode_ref(),
            reference_size=1200.0,
        ),
    )

    assert outcome.blocked is False
    assert outcome.action == EngineCoordinationAction.SIZE_REDUCED
    assert outcome.size_multiplier == 0.5
    assert outcome.resolved_size == 600.0
    assert outcome.refusal_record is None
