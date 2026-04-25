from __future__ import annotations

from execution_backbone.order_decider.hybrid_router_metrics import HybridRouterMetricsSink


def test_rejection_rate_metric_increments_per_reason() -> None:
    sink = HybridRouterMetricsSink()

    sink.record_bridge_projection(rejected=True, reason="nan_input")
    sink.record_bridge_projection(rejected=True, reason="nan_input")
    sink.record_bridge_projection(rejected=True, reason="low_coverage")

    projection = sink.build_projection()

    assert projection.routing_feature_projection_rejection_total["nan_input"] == 2
    assert projection.routing_feature_projection_rejection_total["low_coverage"] == 1


def test_rejection_rate_breakdown_visible() -> None:
    sink = HybridRouterMetricsSink()

    sink.record_bridge_projection(rejected=True, reason="nan_input")
    sink.record_bridge_projection(rejected=False)

    projection = sink.build_projection()

    assert projection.routing_feature_rejection_rate["overall"] == 0.5
    assert projection.routing_feature_rejection_rate["nan_input"] == 0.5


def test_zero_projections_does_not_explode_metric() -> None:
    projection = HybridRouterMetricsSink().build_projection()

    assert projection.routing_feature_rejection_rate == {}
