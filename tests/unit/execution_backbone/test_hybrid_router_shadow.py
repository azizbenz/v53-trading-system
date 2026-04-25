from __future__ import annotations

from dataclasses import replace

from execution_backbone.execution_runtime_models import ExecutionSubmissionStatus
from execution_backbone.order_decider.hybrid_router_types import HybridRoutingAction
from execution_backbone.order_decider.intent_builder import OrderType
from tests.support_hybrid_router_v2 import build_calibration, build_opportunity, build_router, build_runtime, build_snapshot


def test_shadow_mode_does_not_emit_order() -> None:
    runtime, adapter, _, _ = build_runtime()
    opportunity = build_opportunity(
        routing_features=build_snapshot(),
        expected_gain=0.0020,
        expected_cost=0.0002,
    )
    predicted_decision = runtime._hybrid_router.decide(build_snapshot(expected_edge_bps=1.0, spread_bps=6.0))
    runtime._hybrid_router.decide = lambda snap: predicted_decision  # type: ignore[method-assign]

    submission = runtime.submit_opportunity(opportunity, now=10.0)

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert len(adapter.submissions) == 1


def test_shadow_mode_still_runs_legacy_path() -> None:
    runtime, adapter, _, _ = build_runtime()

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=build_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert adapter.submissions


def test_shadow_logger_records_predicted_and_runtime_actual() -> None:
    router, calibration, metrics = build_router()
    logger = build_runtime(metrics_sink=metrics)[3]
    decision = router.decide(build_snapshot())
    record = logger.record(
        snapshot=build_snapshot(),
        predicted_decision=decision,
        runtime_actual_action=HybridRoutingAction.MARKET_TAKER.value,
        calibration_version=calibration.calibration_version,
    )

    assert record.predicted_decision == decision
    assert record.runtime_actual_action == HybridRoutingAction.MARKET_TAKER.value


def test_shadow_logger_computes_decision_diff() -> None:
    router, calibration, metrics = build_router()
    logger = build_runtime(metrics_sink=metrics)[3]
    decision = router.decide(build_snapshot())

    record = logger.record(
        snapshot=build_snapshot(),
        predicted_decision=decision,
        runtime_actual_action=HybridRoutingAction.NO_TRADE.value,
        calibration_version=calibration.calibration_version,
    )

    assert record.decision_diff.startswith("predicted_")


def test_shadow_logger_decision_diff_match_when_actions_align() -> None:
    router, calibration, metrics = build_router()
    logger = build_runtime(metrics_sink=metrics)[3]
    decision = router.decide(build_snapshot())

    record = logger.record(
        snapshot=build_snapshot(),
        predicted_decision=decision,
        runtime_actual_action=decision.action.value,
        calibration_version=calibration.calibration_version,
    )

    assert record.decision_diff == "match"


def test_shadow_logger_decision_diff_reason_hint_populated_on_diff() -> None:
    router, calibration, metrics = build_router()
    logger = build_runtime(metrics_sink=metrics)[3]
    decision = router.decide(build_snapshot())

    record = logger.record(
        snapshot=build_snapshot(),
        predicted_decision=decision,
        runtime_actual_action=HybridRoutingAction.NO_TRADE.value,
        calibration_version=calibration.calibration_version,
    )

    assert record.decision_diff_reason_hint


def test_shadow_attach_outcome_links_to_record() -> None:
    router, calibration, metrics = build_router()
    logger = build_runtime(metrics_sink=metrics)[3]
    decision = router.decide(build_snapshot())
    record = logger.record(
        snapshot=build_snapshot(),
        predicted_decision=decision,
        runtime_actual_action=decision.action.value,
        calibration_version=calibration.calibration_version,
    )
    record_id = logger.resolve_record_id(record)

    logger.attach_outcome(
        record_id,
        fill_ratio=1.0,
        time_to_fill_s=0.5,
        slippage_bps=1.2,
        alpha_decay_bps=0.3,
    )
    updated = logger.record_by_id(record_id)

    assert updated is not None
    assert updated.realized_fill_ratio == 1.0
    assert updated.realized_time_to_fill_s == 0.5


def test_live_mode_switches_to_router_path() -> None:
    live_calibration = replace(build_calibration(), live_mode_enabled=True)
    runtime, adapter, _, _ = build_runtime(calibration=live_calibration)

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=build_snapshot(expected_edge_bps=1.0, spread_bps=6.0),
        ),
        now=10.0,
    )

    assert submission.status == ExecutionSubmissionStatus.NO_TRADE
    assert adapter.submissions == []
