from __future__ import annotations

from local_replay_runtime import (
    LocalLabFailureModeAggregate,
    LocalLabRecalibrationPlan,
    LocalLabReplayCandidateQueue,
    LocalLabResearchPriorityFeatures,
    LocalLabResearchPriorityReport,
    LocalLabResearchPriorityScope,
    build_local_lab_replay_candidate_queue,
)


def test_build_local_lab_replay_candidate_queue_emits_ready_and_blocked_candidates():
    research_priority = LocalLabResearchPriorityReport(
        correlation_id="corr-queue",
        export_dir="E:/lab/export_dir",
        status="ready",
        scope_count=2,
        priority_scope_count=2,
        highest_priority_scope_slug="btcusdt__engine_a",
        highest_priority_score=0.81,
        scopes=(
            LocalLabResearchPriorityScope(
                priority_rank=1,
                pair="BTCUSDT",
                engine_id="engine_a",
                scope_slug="btcusdt__engine_a",
                features=LocalLabResearchPriorityFeatures(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    scope_slug="btcusdt__engine_a",
                    executed_records=4,
                    losing_trade_count=2,
                    loss_rate=0.5,
                    recommended_threshold_ids=("THR-E01", "THR-E02"),
                ),
                priority_score=0.81,
                priority_band="research_now",
                recommended_next_action="replay_recalibration_candidate",
                reason_codes=("THRESHOLD_RECALIBRATION_AVAILABLE",),
                recommended_threshold_ids=("THR-E01", "THR-E02"),
            ),
            LocalLabResearchPriorityScope(
                priority_rank=2,
                pair="ETHUSDT",
                engine_id="engine_b",
                scope_slug="ethusdt__engine_b",
                features=LocalLabResearchPriorityFeatures(
                    pair="ETHUSDT",
                    engine_id="engine_b",
                    scope_slug="ethusdt__engine_b",
                    executed_records=2,
                    losing_trade_count=1,
                    loss_rate=0.5,
                    trace_coverage_count=1,
                ),
                priority_score=0.48,
                priority_band="research_next",
                recommended_next_action="improve_trace_capture",
                reason_codes=("TRACE_COVERAGE_PRESENT",),
            ),
        ),
    )
    recalibration_plan = LocalLabRecalibrationPlan(
        correlation_id="corr-queue",
        export_dir="E:/lab/export_dir",
        report_count=1,
        scope_count=2,
        ready_scope_count=2,
        blocked_scope_count=0,
        executed_records=6,
        losing_trade_count=3,
        dominant_failure_modes=(
            LocalLabFailureModeAggregate(failure_mode="cost_drift", count=2),
        ),
        recommended_threshold_ids=("THR-E01", "THR-E02"),
        action_count=1,
        calibration_candidate_ready=True,
        actions=(),
    )

    queue = build_local_lab_replay_candidate_queue(
        correlation_id="corr-queue",
        export_dir="E:/lab/export_dir",
        research_priority_report=research_priority,
        recalibration_plan=recalibration_plan,
    )

    assert isinstance(queue, LocalLabReplayCandidateQueue)
    assert queue.status == "ready"
    assert queue.candidate_count == 2
    assert queue.ready_candidate_count == 1
    assert queue.blocked_candidate_count == 1
    assert queue.top_scope_slug == "btcusdt__engine_a"
    assert queue.candidates[0].queue_status == "ready_for_local_replay"
    assert queue.candidates[1].queue_status == "blocked_on_trace_capture"


def test_build_local_lab_replay_candidate_queue_returns_no_candidates_when_priority_is_deferred():
    research_priority = LocalLabResearchPriorityReport(
        correlation_id="corr-empty",
        export_dir="E:/lab/export_dir",
        status="monitor_only",
        scope_count=1,
        priority_scope_count=0,
        scopes=(
            LocalLabResearchPriorityScope(
                priority_rank=1,
                pair="SOLUSDT",
                engine_id="engine_c",
                scope_slug="solusdt__engine_c",
                features=LocalLabResearchPriorityFeatures(
                    pair="SOLUSDT",
                    engine_id="engine_c",
                    scope_slug="solusdt__engine_c",
                    executed_records=1,
                    losing_trade_count=0,
                    loss_rate=0.0,
                ),
                priority_score=0.12,
                priority_band="defer",
                recommended_next_action="keep_collecting_evidence",
                reason_codes=("NO_ELEVATED_RESEARCH_PRIORITY",),
            ),
        ),
    )
    recalibration_plan = LocalLabRecalibrationPlan(
        correlation_id="corr-empty",
        export_dir="E:/lab/export_dir",
        report_count=0,
        scope_count=1,
        ready_scope_count=1,
        blocked_scope_count=0,
        executed_records=1,
        losing_trade_count=0,
        dominant_failure_modes=(),
        recommended_threshold_ids=(),
        action_count=0,
        calibration_candidate_ready=False,
        blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        actions=(),
    )

    queue = build_local_lab_replay_candidate_queue(
        correlation_id="corr-empty",
        export_dir="E:/lab/export_dir",
        research_priority_report=research_priority,
        recalibration_plan=recalibration_plan,
    )

    assert queue.status == "no_candidates"
    assert queue.candidate_count == 0
    assert queue.ready_candidate_count == 0
    assert queue.blocked_candidate_count == 0
    assert queue.top_scope_slug == ""
