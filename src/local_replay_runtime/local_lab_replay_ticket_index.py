"""Governed Local IA Lab replay ticket index derived from the replay candidate queue."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime.contracts import LocalReplayRequest
from local_replay_runtime.local_lab_replay_candidate_queue import (
    LocalLabReplayCandidate,
    LocalLabReplayCandidateQueue,
)


_ENGINE_TO_STRATEGY: dict[str, StrategyClassification] = {
    "engine_a": StrategyClassification.A_VARIANT,
    "engine_b": StrategyClassification.B_VARIANT,
    "engine_c": StrategyClassification.C_CANDIDATE,
    "engine_d": StrategyClassification.D_CANDIDATE,
}


class LocalLabReplayTicket(BaseModel, frozen=True):
    """One governed Local IA Lab replay ticket."""

    ticket_rank: int = Field(..., ge=1)
    ticket_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    ticket_status: str = Field(..., min_length=1)
    requires_human_ack: bool = False
    replay_reason: str = Field(..., min_length=1)
    recommended_next_action: str = Field(..., min_length=1)
    recommended_threshold_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    replay_request: LocalReplayRequest | None = None


class LocalLabReplayTicketIndex(BaseModel, frozen=True):
    """Audit-ready index of the next governed Local IA Lab replay tickets."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    ticket_count: int = Field(default=0, ge=0)
    ready_ticket_count: int = Field(default=0, ge=0)
    blocked_ticket_count: int = Field(default=0, ge=0)
    top_ticket_id: str = ""
    top_scope_slug: str = ""
    tickets: tuple[LocalLabReplayTicket, ...] = ()


def build_local_lab_replay_ticket_index(
    *,
    correlation_id: str,
    export_dir: str,
    profile: ProfileId,
    lineage_version: str,
    replay_candidate_queue: LocalLabReplayCandidateQueue,
    strategy_classification: str | None = None,
) -> LocalLabReplayTicketIndex:
    """Build governed local replay tickets from the current bounded replay queue."""

    tickets: list[LocalLabReplayTicket] = []
    explicit_classification = (
        None if strategy_classification is None else StrategyClassification(strategy_classification)
    )
    for candidate in replay_candidate_queue.candidates:
        ticket_status, blocking_reasons, replay_request = _build_ticket_components(
            correlation_id=correlation_id,
            profile=profile,
            lineage_version=lineage_version,
            candidate=candidate,
            explicit_classification=explicit_classification,
        )
        ticket_id = f"{correlation_id}:{candidate.scope_slug}:replay_ticket"
        tickets.append(
            LocalLabReplayTicket(
                ticket_rank=1,
                ticket_id=ticket_id,
                scope_slug=candidate.scope_slug,
                pair=candidate.pair,
                engine_id=candidate.engine_id,
                ticket_status=ticket_status,
                requires_human_ack=ticket_status != "ready",
                replay_reason=_build_replay_reason(candidate),
                recommended_next_action=candidate.recommended_next_action,
                recommended_threshold_ids=candidate.recommended_threshold_ids,
                reason_codes=candidate.reason_codes,
                blocking_reasons=blocking_reasons,
                replay_request=replay_request,
            )
        )

    replay_tickets = tuple(
        ticket.model_copy(update={"ticket_rank": index + 1})
        for index, ticket in enumerate(tickets)
    )
    ready_ticket_count = sum(1 for ticket in replay_tickets if ticket.ticket_status == "ready")
    blocked_ticket_count = sum(1 for ticket in replay_tickets if ticket.ticket_status != "ready")
    if not replay_tickets:
        status = "no_tickets"
        top_ticket_id = ""
        top_scope_slug = ""
    elif ready_ticket_count > 0:
        status = "ready"
        top_ticket_id = replay_tickets[0].ticket_id
        top_scope_slug = replay_tickets[0].scope_slug
    else:
        status = "blocked_only"
        top_ticket_id = replay_tickets[0].ticket_id
        top_scope_slug = replay_tickets[0].scope_slug

    return LocalLabReplayTicketIndex(
        correlation_id=correlation_id,
        export_dir=export_dir,
        status=status,
        ticket_count=len(replay_tickets),
        ready_ticket_count=ready_ticket_count,
        blocked_ticket_count=blocked_ticket_count,
        top_ticket_id=top_ticket_id,
        top_scope_slug=top_scope_slug,
        tickets=replay_tickets,
    )


def _build_ticket_components(
    *,
    correlation_id: str,
    profile: ProfileId,
    lineage_version: str,
    candidate: LocalLabReplayCandidate,
    explicit_classification: StrategyClassification | None,
) -> tuple[str, tuple[str, ...], LocalReplayRequest | None]:
    blocking_reasons = list(candidate.blocking_reasons)
    if explicit_classification is not None:
        strategy_classification = explicit_classification
    else:
        strategy_classification = _ENGINE_TO_STRATEGY.get(candidate.engine_id)
        if strategy_classification is None:
            blocking_reasons.append("STRATEGY_CLASSIFICATION_UNRESOLVED")
            return "blocked", tuple(dict.fromkeys(blocking_reasons)), None
    if candidate.queue_status != "ready_for_local_replay":
        return "blocked", tuple(dict.fromkeys(blocking_reasons)), None
    request = LocalReplayRequest(
        correlation_id=f"{correlation_id}:{candidate.scope_slug}:local_replay",
        profile=profile,
        strategy_classification=strategy_classification,
        lineage_version=lineage_version,
        replay_reason=_build_replay_reason(candidate),
    )
    return "ready", (), request


def _build_replay_reason(candidate: LocalLabReplayCandidate) -> str:
    return f"local_lab:{candidate.recommended_next_action}:{candidate.scope_slug}"


__all__ = [
    "LocalLabReplayTicket",
    "LocalLabReplayTicketIndex",
    "build_local_lab_replay_ticket_index",
]
