"""Local-only dispatch plan derived from the governed Local IA Lab replay ticket index."""

from __future__ import annotations

from pydantic import BaseModel, Field

from local_replay_runtime.local_lab_replay_ticket_index import (
    LocalLabReplayTicket,
    LocalLabReplayTicketIndex,
)


class LocalLabReplayDispatchItem(BaseModel, frozen=True):
    """One dispatchable or blocked Local IA Lab replay work item."""

    dispatch_rank: int = Field(..., ge=1)
    ticket_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    dispatch_status: str = Field(..., min_length=1)
    ready_for_dispatch: bool = False
    requires_human_ack: bool = False
    replay_reason: str = Field(..., min_length=1)
    recommended_next_action: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()


class LocalLabReplayDispatchPlan(BaseModel, frozen=True):
    """Audit-ready local-only dispatch plan for future replay automation."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    ticket_count: int = Field(default=0, ge=0)
    ready_dispatch_count: int = Field(default=0, ge=0)
    blocked_dispatch_count: int = Field(default=0, ge=0)
    top_ticket_id: str = ""
    items: tuple[LocalLabReplayDispatchItem, ...] = ()


def build_local_lab_replay_dispatch_plan(
    *,
    correlation_id: str,
    export_dir: str,
    replay_ticket_index: LocalLabReplayTicketIndex,
) -> LocalLabReplayDispatchPlan:
    """Build a bounded dispatch plan over governed local replay tickets."""

    items = tuple(
        _build_item(ticket=ticket, dispatch_rank=index + 1)
        for index, ticket in enumerate(replay_ticket_index.tickets)
    )
    ready_dispatch_count = sum(1 for item in items if item.ready_for_dispatch)
    blocked_dispatch_count = sum(1 for item in items if not item.ready_for_dispatch)
    if not items:
        status = "no_items"
        top_ticket_id = ""
    elif ready_dispatch_count > 0:
        status = "ready"
        top_ticket_id = next(item.ticket_id for item in items if item.ready_for_dispatch)
    else:
        status = "blocked_only"
        top_ticket_id = items[0].ticket_id

    return LocalLabReplayDispatchPlan(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=status,
        ticket_count=len(items),
        ready_dispatch_count=ready_dispatch_count,
        blocked_dispatch_count=blocked_dispatch_count,
        top_ticket_id=top_ticket_id,
        items=items,
    )


def _build_item(
    *,
    ticket: LocalLabReplayTicket,
    dispatch_rank: int,
) -> LocalLabReplayDispatchItem:
    ready_for_dispatch = ticket.ticket_status == "ready" and ticket.replay_request is not None
    dispatch_status = "ready_for_local_dispatch" if ready_for_dispatch else "blocked_for_local_dispatch"
    return LocalLabReplayDispatchItem(
        dispatch_rank=dispatch_rank,
        ticket_id=ticket.ticket_id,
        scope_slug=ticket.scope_slug,
        dispatch_status=dispatch_status,
        ready_for_dispatch=ready_for_dispatch,
        requires_human_ack=ticket.requires_human_ack,
        replay_reason=ticket.replay_reason,
        recommended_next_action=ticket.recommended_next_action,
        blocking_reasons=ticket.blocking_reasons,
    )


__all__ = [
    "LocalLabReplayDispatchItem",
    "LocalLabReplayDispatchPlan",
    "build_local_lab_replay_dispatch_plan",
]
