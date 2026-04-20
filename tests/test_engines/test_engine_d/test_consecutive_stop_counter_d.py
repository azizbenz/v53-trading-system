from __future__ import annotations

from engines.engine_d.consecutive_stop_counter_d import (
    ConsecutiveStopStateD,
    EngineDResetStateStatus,
    inspect_engine_d_reset_state,
    record_engine_d_stop,
    record_fresh_a_detection,
    to_coordination_fields,
)


_STOP_NS = 1_700_000_000_000_000_000


def test_record_engine_d_stop_increments_consecutive_count() -> None:
    state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_STOP_NS)

    assert state.consecutive_stop_count == 1
    assert state.last_stop_at_ns == _STOP_NS


def test_record_fresh_a_detection_resets_count_only_when_detection_is_newer_than_stop() -> None:
    state = record_engine_d_stop(ConsecutiveStopStateD(consecutive_stop_count=1), stopped_at_ns=_STOP_NS)

    stale_detection = record_fresh_a_detection(state, detected_at_ns=_STOP_NS - 1)
    fresh_detection = record_fresh_a_detection(state, detected_at_ns=_STOP_NS + 1)

    assert stale_detection.consecutive_stop_count == 2
    assert fresh_detection.consecutive_stop_count == 0
    assert fresh_detection.last_fresh_a_detection_at_ns == _STOP_NS + 1


def test_to_coordination_fields_matches_protocol_shape() -> None:
    state = ConsecutiveStopStateD(
        consecutive_stop_count=2,
        last_stop_at_ns=_STOP_NS,
        last_fresh_a_detection_at_ns=_STOP_NS + 100,
        failsafe_override_available=True,
    )

    assert to_coordination_fields(state) == {
        "consecutive_d_stop_count": 2,
        "last_d_stop_at_ns": _STOP_NS,
        "last_fresh_a_detection_at_ns": _STOP_NS + 100,
        "d_failsafe_override_available": True,
    }


def test_inspect_reset_state_reports_reset_required_without_fresh_a() -> None:
    state = record_engine_d_stop(ConsecutiveStopStateD(), stopped_at_ns=_STOP_NS)

    inspection = inspect_engine_d_reset_state(state, evaluated_at_ns=_STOP_NS + 10)

    assert inspection.status == EngineDResetStateStatus.RESET_REQUIRED
    assert inspection.reset_required is True
    assert inspection.stop_limit_reached is True
    assert inspection.fresh_a_detection_after_last_stop is False
    assert inspection.failsafe_override_active is False


def test_inspect_reset_state_reports_failsafe_override_when_elapsed() -> None:
    state = ConsecutiveStopStateD(
        consecutive_stop_count=1,
        last_stop_at_ns=_STOP_NS,
        failsafe_override_available=True,
    )

    inspection = inspect_engine_d_reset_state(
        state,
        evaluated_at_ns=_STOP_NS + (25 * 3_600_000_000_000),
    )

    assert inspection.status == EngineDResetStateStatus.FAILSAFE_OVERRIDE_ACTIVE
    assert inspection.reset_required is True
    assert inspection.failsafe_override_active is True
    assert inspection.failsafe_override_remaining_ns == 0
