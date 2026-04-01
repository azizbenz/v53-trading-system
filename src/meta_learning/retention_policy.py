"""Retention helpers for governed Build-9X records and transitions."""

from __future__ import annotations

from datetime import datetime, timedelta


DIAGNOSTIC_HYPOTHESIS_RETENTION_DAYS = 180
REVIEW_AND_PROMOTION_RETENTION_DAYS = 365


def retention_until_days(created_at: datetime, *, days: int) -> datetime:
    """Return the minimum retention deadline from a creation timestamp."""

    return created_at + timedelta(days=days)


def diagnostic_or_hypothesis_retention(created_at: datetime) -> tuple[datetime, str]:
    """Retention policy for diagnostic and hypothesis records."""

    return (
        retention_until_days(
            created_at,
            days=DIAGNOSTIC_HYPOTHESIS_RETENTION_DAYS,
        ),
        f"min_{DIAGNOSTIC_HYPOTHESIS_RETENTION_DAYS}d_diagnostic_hypothesis_retention",
    )


def review_or_promotion_retention(created_at: datetime) -> tuple[datetime, str]:
    """Retention policy for review decisions and promotion transitions."""

    return (
        retention_until_days(
            created_at,
            days=REVIEW_AND_PROMOTION_RETENTION_DAYS,
        ),
        f"min_{REVIEW_AND_PROMOTION_RETENTION_DAYS}d_review_promotion_retention",
    )


def export_bundle_retention(
    created_at: datetime,
    *,
    review_open: bool,
    replay_open: bool,
) -> tuple[datetime | None, str, bool]:
    """Retention policy for replay bundles while review or replay remains open."""

    retention_policy = "keep_while_review_or_replay_open"
    if review_open or replay_open:
        return None, retention_policy, True
    retention_until, _ = review_or_promotion_retention(created_at)
    return retention_until, retention_policy, False


__all__ = [
    "DIAGNOSTIC_HYPOTHESIS_RETENTION_DAYS",
    "REVIEW_AND_PROMOTION_RETENTION_DAYS",
    "diagnostic_or_hypothesis_retention",
    "export_bundle_retention",
    "review_or_promotion_retention",
    "retention_until_days",
]
