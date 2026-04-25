from __future__ import annotations

from dataclasses import replace

import pytest

from execution_backbone.execution_routing_features import RoutingFeatureProjectionError
from tests.support_hybrid_router_v2 import (
    FakeLobSnapshot,
    FakeRegimeSignal,
    build_calibration,
    build_opportunity,
    build_router,
    build_top_of_book,
    build_venue_fees,
)
from execution_backbone.execution_routing_bridge import ExecutionRoutingBridge


def test_project_nominal_produces_snapshot() -> None:
    _, calibration, metrics = build_router()
    bridge = ExecutionRoutingBridge(
        calibration,
        metrics,
        resolve_current_time_ns=lambda: 1_500_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )

    snapshot = bridge.project(
        opportunity=build_opportunity(),
        lob_regime_snapshot=FakeLobSnapshot(),
        regime_signal=FakeRegimeSignal(),
        top_of_book=build_top_of_book(),
        venue_fees=build_venue_fees(),
    )

    assert snapshot.side == "BUY"


def test_project_rejects_nan_input_with_reason() -> None:
    _, calibration, metrics = build_router()
    bridge = ExecutionRoutingBridge(
        calibration,
        metrics,
        resolve_current_time_ns=lambda: 1_500_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )

    with pytest.raises(RoutingFeatureProjectionError) as exc_info:
        bridge.project(
            opportunity=build_opportunity(),
            lob_regime_snapshot=replace(FakeLobSnapshot(), spread_bps=float("nan")),
            regime_signal=FakeRegimeSignal(),
            top_of_book=build_top_of_book(),
            venue_fees=build_venue_fees(),
        )

    assert exc_info.value.rejection_reason == "nan_input"


def test_project_rejects_low_coverage_ratio_with_reason() -> None:
    _, calibration, metrics = build_router()
    bridge = ExecutionRoutingBridge(
        calibration,
        metrics,
        resolve_current_time_ns=lambda: 1_500_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )

    with pytest.raises(RoutingFeatureProjectionError) as exc_info:
        bridge.project(
            opportunity=build_opportunity(),
            lob_regime_snapshot=replace(FakeLobSnapshot(), observation_coverage_ratio=0.1),
            regime_signal=FakeRegimeSignal(),
            top_of_book=build_top_of_book(),
            venue_fees=build_venue_fees(),
        )

    assert exc_info.value.rejection_reason == "low_coverage"


def test_project_rejects_stale_lob_snapshot_with_reason() -> None:
    calibration = build_calibration(max_snapshot_age_s=0.1)
    _, _, metrics = build_router(calibration=calibration)
    bridge = ExecutionRoutingBridge(
        calibration,
        metrics,
        resolve_current_time_ns=lambda: 2_000_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )

    with pytest.raises(RoutingFeatureProjectionError) as exc_info:
        bridge.project(
            opportunity=build_opportunity(),
            lob_regime_snapshot=FakeLobSnapshot(computed_at_ns=1_000_000_000),
            regime_signal=FakeRegimeSignal(),
            top_of_book=build_top_of_book(),
            venue_fees=build_venue_fees(),
        )

    assert exc_info.value.rejection_reason == "stale_snapshot"


def test_project_side_passthrough() -> None:
    _, calibration, metrics = build_router()
    bridge = ExecutionRoutingBridge(
        calibration,
        metrics,
        resolve_current_time_ns=lambda: 1_500_000_000,
        resolve_volatility_stats=lambda pair, window: (0.01, 0.005),
    )

    snapshot = bridge.project(
        opportunity=build_opportunity(side="sell"),
        lob_regime_snapshot=FakeLobSnapshot(),
        regime_signal=FakeRegimeSignal(),
        top_of_book=build_top_of_book(),
        venue_fees=build_venue_fees(),
    )

    assert snapshot.side == "SELL"
