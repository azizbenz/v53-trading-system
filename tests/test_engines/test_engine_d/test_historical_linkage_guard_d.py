from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from engines.engine_d.consecutive_stop_counter_d import ConsecutiveStopStateD, record_engine_d_stop
from engines.engine_d.historical_linkage_guard_d import (
    build_engine_d_coordination_input,
    evaluate_engine_d_historical_linkage,
)
from interface_contracts import BetStructure, EngineId, ForecastHorizonClass, ForecastTargetClass, Side
from protocols.closed_episode_journal import EpisodeCloseReason, EpisodeRef
from protocols.engine_coordination_rules import (
    EngineCoordinationAction,
    EngineCoordinationInput,
    evaluate_engine_coordination,
)


_NOW_NS = 1_700_000_000_000_000_000


def _episode_ref(**overrides: object) -> EpisodeRef:
    payload: dict[str, object] = {
        "episode_id": UUID("21111111-1111-1111-1111-111111111111"),
        "engine_id_of_origin": EngineId.A,
        "pair": "BTCUSDT",
        "side": Side.BUY,
        "entry_level": Decimal("100.0"),
        "exit_level": Decimal("104.0"),
        "bet_structure": BetStructure.DIRECTIONAL_LONG,
        "forecast_horizon_class": ForecastHorizonClass.SHORT,
        "forecast_target_class": ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
        "closed_at_ns": _NOW_NS - 1_000,
        "close_reason": EpisodeCloseReason.TIME_STOP,
        "realized_pnl_decimal": Decimal("4.0"),
    }
    payload.update(overrides)
    return EpisodeRef(**payload)


def test_build_engine_d_coordination_input_uses_explicit_stop_state() -> None:
    stop_state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_NOW_NS - 10)

    coordination_input = build_engine_d_coordination_input(
        coordination_input_factory=EngineCoordinationInput,
        evaluated_at_ns=_NOW_NS,
        pair="btcusdt",
        side=Side.BUY,
        first_episode_ref=_episode_ref(),
        stop_state=stop_state,
        reference_size=800.0,
    )

    assert coordination_input.engine_id == EngineId.D
    assert coordination_input.pair == "BTCUSDT"
    assert coordination_input.consecutive_d_stop_count == 1
    assert coordination_input.reference_size == pytest.approx(800.0)


def test_evaluate_engine_d_historical_linkage_blocks_without_episode_ref() -> None:
    outcome = evaluate_engine_d_historical_linkage(
        build_engine_d_coordination_input(
            coordination_input_factory=EngineCoordinationInput,
            evaluated_at_ns=_NOW_NS,
            pair="BTCUSDT",
            side=Side.BUY,
            first_episode_ref=None,
        ),
        evaluator=evaluate_engine_coordination,
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_no_historical_linkage",)


def test_evaluate_engine_d_historical_linkage_blocks_when_reset_required() -> None:
    stop_state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_NOW_NS - 10)

    outcome = evaluate_engine_d_historical_linkage(
        build_engine_d_coordination_input(
            coordination_input_factory=EngineCoordinationInput,
            evaluated_at_ns=_NOW_NS,
            pair="BTCUSDT",
            side=Side.BUY,
            first_episode_ref=_episode_ref(),
            stop_state=stop_state,
        ),
        evaluator=evaluate_engine_coordination,
    )

    assert outcome.blocked is True
    assert outcome.reason_codes == ("hard_block.d_consecutive_stops_reset_required",)


def test_evaluate_engine_d_historical_linkage_permits_half_size_reentry() -> None:
    outcome = evaluate_engine_d_historical_linkage(
        build_engine_d_coordination_input(
            coordination_input_factory=EngineCoordinationInput,
            evaluated_at_ns=_NOW_NS,
            pair="BTCUSDT",
            side=Side.BUY,
            first_episode_ref=_episode_ref(),
            reference_size=800.0,
        ),
        evaluator=evaluate_engine_coordination,
    )

    assert outcome.blocked is False
    assert outcome.action == EngineCoordinationAction.SIZE_REDUCED
    assert outcome.resolved_size == pytest.approx(400.0)
