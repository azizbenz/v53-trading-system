from __future__ import annotations

from execution_backbone.order_decider.hybrid_router_types import build_full_routing_trace
from tests.support_hybrid_router_v2 import build_router, build_snapshot


def test_compact_trace_used_in_live_monitoring() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_decision(
        decision,
        shadow_only=False,
        calibration_version=calibration.calibration_version,
    )

    projection = metrics.build_projection()

    assert projection.latest_live_routing_trace.action == decision.action.value


def test_full_trace_used_in_shadow_logs() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_shadow_observation(
        full_trace=build_full_routing_trace(
            decision,
            calibration_version=calibration.calibration_version,
            shadow_only=True,
        ),
        decision_diff="match",
    )

    projection = metrics.build_projection()

    assert projection.latest_shadow_routing_trace is not None


def test_compact_trace_field_count_bounded() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_decision(
        decision,
        shadow_only=False,
        calibration_version=calibration.calibration_version,
    )

    payload = metrics.build_projection().latest_live_routing_trace.model_dump()

    assert len(payload) == 8


def test_full_trace_contains_diagnostics() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_shadow_observation(
        full_trace=build_full_routing_trace(
            decision,
            calibration_version=calibration.calibration_version,
            shadow_only=True,
        ),
        decision_diff="match",
    )

    diagnostics = metrics.build_projection().latest_shadow_routing_trace.diagnostics

    assert "ev_maker_raw_bps" in diagnostics


def test_no_secret_or_unbounded_payload_in_either_trace() -> None:
    router, calibration, metrics = build_router()
    decision = router.decide(build_snapshot())
    metrics.record_decision(
        decision,
        shadow_only=False,
        calibration_version=calibration.calibration_version,
    )
    metrics.record_shadow_observation(
        full_trace=build_full_routing_trace(
            decision,
            calibration_version=calibration.calibration_version,
            shadow_only=True,
        ),
        decision_diff="match",
    )

    live_payload = metrics.build_projection().latest_live_routing_trace.model_dump()
    shadow_payload = metrics.build_projection().latest_shadow_routing_trace.model_dump()

    assert "api_key" not in str(live_payload).lower()
    assert "api_key" not in str(shadow_payload).lower()
