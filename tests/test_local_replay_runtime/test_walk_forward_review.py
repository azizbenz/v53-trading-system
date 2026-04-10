from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from local_replay_runtime import (
    WalkForwardHumanReview,
    WalkForwardReviewStatus,
    build_walk_forward_review_template,
    summarize_walk_forward_review,
)


def test_walk_forward_review_template_is_pending_and_blocks_pass():
    template = build_walk_forward_review_template(
        correlation_id="corr-wf-1",
        export_dir="E:/tmp/export_dir",
        run_id="run-wf-1",
    )

    summary = summarize_walk_forward_review(template)

    assert template.review_status == WalkForwardReviewStatus.PENDING
    assert summary.walk_forward_pass is False
    assert "WALK_FORWARD_HUMAN_REVIEW_PENDING" in summary.blocking_reasons


def test_approved_walk_forward_review_requires_all_anti_leakage_checks():
    with pytest.raises(ValidationError, match="temporal_split_confirmed"):
        WalkForwardHumanReview(
            correlation_id="corr-wf-2",
            export_dir="E:/tmp/export_dir",
            run_id="run-wf-2",
            review_status=WalkForwardReviewStatus.APPROVED,
            reviewed_by="operator.aziz",
            reviewed_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
            walk_forward_window_count=5,
            no_future_data_leak_confirmed=True,
            feature_timestamp_alignment_confirmed=True,
            calibration_fit_window_confirmed=True,
        )


def test_approved_walk_forward_review_passes_when_all_checks_are_true():
    review = WalkForwardHumanReview(
        correlation_id="corr-wf-3",
        export_dir="E:/tmp/export_dir",
        run_id="run-wf-3",
        review_status=WalkForwardReviewStatus.APPROVED,
        reviewed_by="operator.aziz",
        reviewed_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        walk_forward_window_count=5,
        temporal_split_confirmed=True,
        no_future_data_leak_confirmed=True,
        feature_timestamp_alignment_confirmed=True,
        calibration_fit_window_confirmed=True,
        notes="No leak or overlap found.",
    )

    summary = summarize_walk_forward_review(review)

    assert summary.walk_forward_pass is True
    assert summary.blocking_reasons == ()
    assert summary.review_status == WalkForwardReviewStatus.APPROVED
