"""Governed human review gate for Local IA Lab walk-forward evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WalkForwardReviewStatus(StrEnum):
    """Bounded states for the Local IA Lab walk-forward human review."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WalkForwardHumanReview(BaseModel, frozen=True):
    """Human anti-leakage review attached to a Local IA Lab walk-forward study."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_status: WalkForwardReviewStatus = WalkForwardReviewStatus.PENDING
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    walk_forward_window_count: int = Field(default=0, ge=0)
    temporal_split_confirmed: bool = False
    no_future_data_leak_confirmed: bool = False
    feature_timestamp_alignment_confirmed: bool = False
    calibration_fit_window_confirmed: bool = False
    notes: str = ""
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def validate_review(self) -> "WalkForwardHumanReview":
        if self.review_status in {
            WalkForwardReviewStatus.APPROVED,
            WalkForwardReviewStatus.REJECTED,
        }:
            if not self.reviewed_by:
                raise ValueError("Reviewed walk-forward decisions require reviewed_by")
            if self.reviewed_at is None:
                raise ValueError("Reviewed walk-forward decisions require reviewed_at")
        if self.review_status == WalkForwardReviewStatus.APPROVED:
            if self.walk_forward_window_count <= 0:
                raise ValueError("Approved walk-forward review requires walk_forward_window_count > 0")
            if not self.temporal_split_confirmed:
                raise ValueError("Approved walk-forward review requires temporal_split_confirmed=True")
            if not self.no_future_data_leak_confirmed:
                raise ValueError("Approved walk-forward review requires no_future_data_leak_confirmed=True")
            if not self.feature_timestamp_alignment_confirmed:
                raise ValueError(
                    "Approved walk-forward review requires feature_timestamp_alignment_confirmed=True"
                )
            if not self.calibration_fit_window_confirmed:
                raise ValueError(
                    "Approved walk-forward review requires calibration_fit_window_confirmed=True"
                )
        return self


class WalkForwardReviewSummary(BaseModel, frozen=True):
    """Future-facing summary of the governed walk-forward human review."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_required: bool = True
    review_status: WalkForwardReviewStatus
    walk_forward_pass: bool = False
    blocking_reasons: tuple[str, ...] = ()
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    walk_forward_window_count: int = Field(default=0, ge=0)
    notes: str = ""


def build_walk_forward_review_template(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
) -> WalkForwardHumanReview:
    """Create the pending human review template emitted by the Local IA Lab."""

    return WalkForwardHumanReview(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        review_status=WalkForwardReviewStatus.PENDING,
    )


def summarize_walk_forward_review(review: WalkForwardHumanReview) -> WalkForwardReviewSummary:
    """Project the human review into a small future-dashboard-ready summary."""

    blocking_reasons: list[str] = []
    walk_forward_pass = review.review_status == WalkForwardReviewStatus.APPROVED

    if review.review_status == WalkForwardReviewStatus.PENDING:
        blocking_reasons.append("WALK_FORWARD_HUMAN_REVIEW_PENDING")
    elif review.review_status == WalkForwardReviewStatus.REJECTED:
        blocking_reasons.append("WALK_FORWARD_HUMAN_REVIEW_REJECTED")

    if review.walk_forward_window_count <= 0:
        blocking_reasons.append("WALK_FORWARD_WINDOWS_MISSING")
    if not review.temporal_split_confirmed:
        blocking_reasons.append("WALK_FORWARD_TEMPORAL_SPLIT_UNCONFIRMED")
    if not review.no_future_data_leak_confirmed:
        blocking_reasons.append("WALK_FORWARD_FUTURE_DATA_LEAK_UNCONFIRMED")
    if not review.feature_timestamp_alignment_confirmed:
        blocking_reasons.append("WALK_FORWARD_FEATURE_TIMESTAMP_ALIGNMENT_UNCONFIRMED")
    if not review.calibration_fit_window_confirmed:
        blocking_reasons.append("WALK_FORWARD_CALIBRATION_WINDOW_UNCONFIRMED")

    if blocking_reasons:
        walk_forward_pass = False

    return WalkForwardReviewSummary(
        correlation_id=review.correlation_id,
        export_dir=review.export_dir,
        run_id=review.run_id,
        review_status=review.review_status,
        walk_forward_pass=walk_forward_pass,
        blocking_reasons=tuple(blocking_reasons),
        reviewed_by=review.reviewed_by,
        reviewed_at=review.reviewed_at,
        walk_forward_window_count=review.walk_forward_window_count,
        notes=review.notes,
    )


__all__ = [
    "WalkForwardHumanReview",
    "WalkForwardReviewStatus",
    "WalkForwardReviewSummary",
    "build_walk_forward_review_template",
    "summarize_walk_forward_review",
]
