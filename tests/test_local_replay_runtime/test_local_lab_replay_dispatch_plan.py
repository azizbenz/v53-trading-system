from __future__ import annotations

from local_replay_runtime import (
    LocalLabReplayDispatchPlan,
    LocalLabReplayTicket,
    LocalLabReplayTicketIndex,
    build_local_lab_replay_dispatch_plan,
)


def test_build_local_lab_replay_dispatch_plan_emits_ready_and_blocked_dispatch_items():
    ticket_index = LocalLabReplayTicketIndex(
        correlation_id="corr-dispatch",
        export_dir="E:/lab/export_dir",
        status="ready",
        ticket_count=2,
        ready_ticket_count=1,
        blocked_ticket_count=1,
        top_ticket_id="corr-dispatch:btcusdt__engine_a:replay_ticket",
        top_scope_slug="btcusdt__engine_a",
        tickets=(
            LocalLabReplayTicket(
                ticket_rank=1,
                ticket_id="corr-dispatch:btcusdt__engine_a:replay_ticket",
                scope_slug="btcusdt__engine_a",
                pair="BTCUSDT",
                engine_id="engine_a",
                ticket_status="ready",
                requires_human_ack=False,
                replay_reason="local_lab:replay_recalibration_candidate:btcusdt__engine_a",
                recommended_next_action="replay_recalibration_candidate",
                replay_request={"correlation_id": "corr-dispatch:btcusdt__engine_a:local_replay", "profile": "complete", "runtime_mode": "local_replay", "strategy_classification": "a_variant", "lineage_version": "lin-v53", "replay_reason": "local_lab:replay_recalibration_candidate:btcusdt__engine_a"},
            ),
            LocalLabReplayTicket(
                ticket_rank=2,
                ticket_id="corr-dispatch:ethusdt__engine_b:replay_ticket",
                scope_slug="ethusdt__engine_b",
                pair="ETHUSDT",
                engine_id="engine_b",
                ticket_status="blocked",
                requires_human_ack=True,
                replay_reason="local_lab:improve_trace_capture:ethusdt__engine_b",
                recommended_next_action="improve_trace_capture",
                blocking_reasons=("TRACE_CAPTURE_REQUIRED",),
            ),
        ),
    )

    plan = build_local_lab_replay_dispatch_plan(
        correlation_id="corr-dispatch",
        export_dir="E:/lab/export_dir",
        replay_ticket_index=ticket_index,
    )

    assert isinstance(plan, LocalLabReplayDispatchPlan)
    assert plan.status == "ready"
    assert plan.ticket_count == 2
    assert plan.ready_dispatch_count == 1
    assert plan.blocked_dispatch_count == 1
    assert plan.top_ticket_id == "corr-dispatch:btcusdt__engine_a:replay_ticket"
    assert plan.items[0].dispatch_status == "ready_for_local_dispatch"
    assert plan.items[1].dispatch_status == "blocked_for_local_dispatch"


def test_build_local_lab_replay_dispatch_plan_returns_no_items_when_ticket_index_is_empty():
    ticket_index = LocalLabReplayTicketIndex(
        correlation_id="corr-empty-dispatch",
        export_dir="E:/lab/export_dir",
        status="no_tickets",
        ticket_count=0,
        ready_ticket_count=0,
        blocked_ticket_count=0,
        tickets=(),
    )

    plan = build_local_lab_replay_dispatch_plan(
        correlation_id="corr-empty-dispatch",
        export_dir="E:/lab/export_dir",
        replay_ticket_index=ticket_index,
    )

    assert plan.status == "no_items"
    assert plan.ticket_count == 0
    assert plan.ready_dispatch_count == 0
    assert plan.blocked_dispatch_count == 0
    assert plan.top_ticket_id == ""
