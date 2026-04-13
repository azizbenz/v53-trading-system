from __future__ import annotations

from interface_contracts import ProfileId
from local_replay_runtime import (
    LocalLabReplayCandidate,
    LocalLabReplayCandidateQueue,
    build_local_lab_replay_ticket_index,
)


def test_build_local_lab_replay_ticket_index_emits_ready_ticket_for_ready_candidate():
    queue = LocalLabReplayCandidateQueue(
        correlation_id="corr-ticket",
        export_dir="E:/lab/export_dir",
        status="ready",
        candidate_count=1,
        ready_candidate_count=1,
        blocked_candidate_count=0,
        top_scope_slug="btcusdt__engine_a",
        top_priority_score=0.82,
        candidates=(
            LocalLabReplayCandidate(
                replay_rank=1,
                pair="BTCUSDT",
                engine_id="engine_a",
                scope_slug="btcusdt__engine_a",
                priority_rank=1,
                priority_score=0.82,
                priority_band="research_now",
                recommended_next_action="replay_recalibration_candidate",
                queue_status="ready_for_local_replay",
                recommended_threshold_ids=("THR-E01",),
                reason_codes=("THRESHOLD_RECALIBRATION_AVAILABLE",),
            ),
        ),
    )

    index = build_local_lab_replay_ticket_index(
        correlation_id="corr-ticket",
        export_dir="E:/lab/export_dir",
        profile=ProfileId.COMPLETE,
        lineage_version="lin-v53",
        replay_candidate_queue=queue,
    )

    assert index.status == "ready"
    assert index.ticket_count == 1
    assert index.ready_ticket_count == 1
    assert index.top_scope_slug == "btcusdt__engine_a"
    assert index.tickets[0].ticket_status == "ready"
    assert index.tickets[0].replay_request is not None
    assert index.tickets[0].replay_request.replay_reason.startswith("local_lab:")


def test_build_local_lab_replay_ticket_index_blocks_when_engine_mapping_is_unknown():
    queue = LocalLabReplayCandidateQueue(
        correlation_id="corr-ticket-blocked",
        export_dir="E:/lab/export_dir",
        status="ready",
        candidate_count=1,
        ready_candidate_count=1,
        blocked_candidate_count=0,
        top_scope_slug="foo__engine_x",
        top_priority_score=0.61,
        candidates=(
            LocalLabReplayCandidate(
                replay_rank=1,
                pair="FOOUSDT",
                engine_id="engine_x",
                scope_slug="foousdt__engine_x",
                priority_rank=1,
                priority_score=0.61,
                priority_band="research_next",
                recommended_next_action="replay_high_risk_scope",
                queue_status="ready_for_local_replay",
                reason_codes=("SURROGATE_HIGH_RISK_SCOPE",),
            ),
        ),
    )

    index = build_local_lab_replay_ticket_index(
        correlation_id="corr-ticket-blocked",
        export_dir="E:/lab/export_dir",
        profile=ProfileId.COMPLETE,
        lineage_version="lin-v53",
        replay_candidate_queue=queue,
    )

    assert index.status == "blocked_only"
    assert index.ready_ticket_count == 0
    assert index.blocked_ticket_count == 1
    assert index.tickets[0].ticket_status == "blocked"
    assert index.tickets[0].replay_request is None
    assert index.tickets[0].blocking_reasons == ("STRATEGY_CLASSIFICATION_UNRESOLVED",)
