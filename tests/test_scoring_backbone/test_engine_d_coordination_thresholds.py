from __future__ import annotations

import pytest

from scoring_backbone import (
    EngineDCoordinationThresholdResolverConfig,
    build_engine_d_coordination_threshold_updates,
    resolve_engine_d_coordination_thresholds,
)


_NS_PER_HOUR = 3_600_000_000_000


def test_resolve_engine_d_coordination_thresholds_returns_policy_defaults() -> None:
    resolved = resolve_engine_d_coordination_thresholds()

    assert resolved.d_reset_failsafe_threshold_id == "THR-X10"
    assert resolved.d_consecutive_stop_limit_threshold_id == "THR-X11"
    assert resolved.governance_mode == "policy_governed"
    assert resolved.d_reset_failsafe_hours == pytest.approx(24.0)
    assert resolved.d_reset_failsafe_ns == 24 * _NS_PER_HOUR
    assert resolved.d_consecutive_stop_limit == 1
    assert resolved.to_engine_d_coordination_threshold_updates() == {
        "d_reset_failsafe_ns": 24 * _NS_PER_HOUR,
        "d_consecutive_stop_limit": 1,
    }


def test_build_engine_d_coordination_threshold_updates_returns_runtime_payload() -> None:
    updates = build_engine_d_coordination_threshold_updates(
        EngineDCoordinationThresholdResolverConfig(
            d_reset_failsafe_hours=12.0,
            d_consecutive_stop_limit=2,
        )
    )

    assert updates == {
        "d_reset_failsafe_ns": 12 * _NS_PER_HOUR,
        "d_consecutive_stop_limit": 2,
    }


def test_resolve_engine_d_coordination_thresholds_rejects_values_above_hard_caps() -> None:
    with pytest.raises(ValueError, match="THR-X10"):
        resolve_engine_d_coordination_thresholds(
            EngineDCoordinationThresholdResolverConfig(
                d_reset_failsafe_hours=72.0,
                d_consecutive_stop_limit=1,
            )
        )

    with pytest.raises(ValueError, match="THR-X11"):
        resolve_engine_d_coordination_thresholds(
            EngineDCoordinationThresholdResolverConfig(
                d_reset_failsafe_hours=24.0,
                d_consecutive_stop_limit=4,
            )
        )
