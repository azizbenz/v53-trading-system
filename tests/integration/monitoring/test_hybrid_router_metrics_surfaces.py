from __future__ import annotations

from tests.support_hybrid_router_v2 import build_router, build_snapshot


def test_all_volume_counters_exposed() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_fallback_blocked_by_runtime()
    metrics.record_shadow_observation(
        full_trace=__import__(
            "execution_backbone.order_decider.hybrid_router_types",
            fromlist=["build_full_routing_trace"],
        ).build_full_routing_trace(
            decision,
            calibration_version=calibration.calibration_version,
            shadow_only=True,
        ),
        decision_diff="match",
    )

    projection = metrics.build_projection()

    assert "hybrid_router_no_trade_total" in projection.model_dump()
    assert "hybrid_router_fallback_blocked_by_runtime_total" in projection.model_dump()


def test_distribution_metrics_exposed_including_raw_minus_taker() -> None:
    router, _, metrics = build_router()
    router.decide(build_snapshot())

    projection = metrics.build_projection()

    assert projection.ev_maker_raw_minus_taker_bps.count == 1
    assert projection.ev_maker_weighted_minus_taker_bps.count == 1


def test_calibration_metrics_exposed_even_when_empty() -> None:
    projection = build_router()[2].build_projection()

    assert projection.hybrid_router_p_fill_realized_vs_predicted_brier.ready is False
    assert projection.hybrid_router_wait_realized_vs_predicted_mae_s.ready is False


def test_bridge_rejection_rate_exposed() -> None:
    metrics = build_router()[2]
    metrics.record_bridge_projection(rejected=True, reason="nan_input")
    metrics.record_bridge_projection(rejected=False)

    projection = metrics.build_projection()

    assert projection.routing_feature_projection_rejection_total["nan_input"] == 1
    assert projection.routing_feature_rejection_rate["overall"] == 0.5


def test_shadow_decision_diff_matrix_exposed() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_shadow_observation(
        full_trace=__import__(
            "execution_backbone.order_decider.hybrid_router_types",
            fromlist=["build_full_routing_trace"],
        ).build_full_routing_trace(
            decision,
            calibration_version=calibration.calibration_version,
            shadow_only=True,
        ),
        decision_diff="predicted_LIMIT_MAKER_actual_NO_TRADE",
    )

    projection = metrics.build_projection()

    assert projection.hybrid_router_shadow_decision_diff_total[
        "predicted_LIMIT_MAKER_actual_NO_TRADE"
    ] == 1
