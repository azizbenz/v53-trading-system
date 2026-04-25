from __future__ import annotations

from execution_backbone.execution_runtime import (
    ExecutionRuntime,
    VenueOrderEvent,
    VenueOrderEventType,
)
from tests.support_hybrid_router_v2 import FakeExecutionVenue, build_opportunity, build_runtime


def test_runtime_with_none_routing_features_uses_legacy_path_exactly() -> None:
    base_adapter = FakeExecutionVenue()
    hybrid_adapter = FakeExecutionVenue()
    base_runtime = ExecutionRuntime(base_adapter)
    hybrid_runtime, _, _, _ = build_runtime(adapter=hybrid_adapter)
    opportunity = build_opportunity(
        routing_features=None,
        expected_gain=0.0020,
        expected_cost=0.0002,
    )

    base_submission = base_runtime.submit_opportunity(opportunity, now=10.0)
    hybrid_submission = hybrid_runtime.submit_opportunity(opportunity, now=10.0)

    assert base_submission.model_dump() == hybrid_submission.model_dump()
    assert len(base_adapter.submissions) == len(hybrid_adapter.submissions) == 1
    assert base_adapter.submissions[0][1].model_dump() == hybrid_adapter.submissions[0][1].model_dump()

    base_adapter.push_events(
        VenueOrderEvent(
            order_id="ord-1",
            event_type=VenueOrderEventType.ACK,
            timestamp=10.5,
        ),
        VenueOrderEvent(
            order_id="ord-1",
            event_type=VenueOrderEventType.FILL,
            timestamp=11.0,
            fill_quantity=0.5,
            fill_price=100.0,
        ),
    )
    hybrid_adapter.push_events(
        VenueOrderEvent(
            order_id="ord-1",
            event_type=VenueOrderEventType.ACK,
            timestamp=10.5,
        ),
        VenueOrderEvent(
            order_id="ord-1",
            event_type=VenueOrderEventType.FILL,
            timestamp=11.0,
            fill_quantity=0.5,
            fill_price=100.0,
        ),
    )

    base_summary = base_runtime.process_events()
    hybrid_summary = hybrid_runtime.process_events()

    assert base_summary.model_dump() == hybrid_summary.model_dump()
    assert base_runtime.get_local_positions() == hybrid_runtime.get_local_positions()
    assert base_runtime._state_tracker.get_open_orders() == hybrid_runtime._state_tracker.get_open_orders()
    assert tuple(base_runtime._terminal_orders.values()) == tuple(hybrid_runtime._terminal_orders.values())
