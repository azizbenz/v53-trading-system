"""Capacity and backpressure guardrails for the governed Build-9X layer."""

from __future__ import annotations

from meta_learning.contracts import LearningCapacitySnapshot
from meta_learning.enums import LearningBacklogState, LearningCaptureMode


_BACKPRESSURE_SIGNAL_KEY = "learning.storage.backpressure"


def evaluate_learning_capacity(
    *,
    queue_depth: int,
    queue_oldest_age_ms: int = 0,
    worker_cpu_pct: float = 0.0,
    worker_rss_mb: float = 0.0,
    write_latency_ms: float = 0.0,
    export_failures_total: int = 0,
    log_loss_total: int = 0,
    unprocessed_items_count: int = 0,
    backlog_alert_threshold: int = 1000,
    backlog_protection_threshold: int = 5000,
) -> LearningCapacitySnapshot:
    """Evaluate whether Build-9X must degrade into capture_minimale mode."""

    if queue_depth > backlog_protection_threshold:
        backlog_state = LearningBacklogState.PROTECTION
    elif queue_depth > backlog_alert_threshold:
        backlog_state = LearningBacklogState.ALERT
    else:
        backlog_state = LearningBacklogState.NORMAL

    backpressure_active = backlog_state == LearningBacklogState.PROTECTION
    capture_mode = (
        LearningCaptureMode.CAPTURE_MINIMALE
        if backpressure_active
        else LearningCaptureMode.FULL_CAPTURE
    )
    resolved_unprocessed_items_count = (
        max(unprocessed_items_count, queue_depth - backlog_protection_threshold)
        if backpressure_active
        else unprocessed_items_count
    )

    blocking_reasons: list[str] = []
    observability_reduced = False
    backpressure_signal_key = ""

    if backpressure_active:
        blocking_reasons.append(_BACKPRESSURE_SIGNAL_KEY)
        observability_reduced = True
        backpressure_signal_key = _BACKPRESSURE_SIGNAL_KEY
    if resolved_unprocessed_items_count > 0 and _BACKPRESSURE_SIGNAL_KEY not in blocking_reasons:
        blocking_reasons.append("learning_unprocessed_items_count")
    if log_loss_total > 0:
        blocking_reasons.append("learning_log_loss_total")
    if export_failures_total > 0:
        blocking_reasons.append("learning_export_failures_total")

    blocked_due_to_incomplete_data = bool(
        backpressure_active or resolved_unprocessed_items_count > 0 or log_loss_total > 0
    )

    return LearningCapacitySnapshot(
        queue_depth=queue_depth,
        queue_oldest_age_ms=queue_oldest_age_ms,
        worker_cpu_pct=worker_cpu_pct,
        worker_rss_mb=worker_rss_mb,
        write_latency_ms=write_latency_ms,
        export_failures_total=export_failures_total,
        log_loss_total=log_loss_total,
        unprocessed_items_count=resolved_unprocessed_items_count,
        backlog_alert_threshold=backlog_alert_threshold,
        backlog_protection_threshold=backlog_protection_threshold,
        backlog_state=backlog_state,
        capture_mode=capture_mode,
        observability_reduced=observability_reduced,
        backpressure_active=backpressure_active,
        backpressure_signal_key=backpressure_signal_key,
        review_blocked_due_to_incomplete_data=blocked_due_to_incomplete_data,
        promotion_blocked_due_to_incomplete_data=blocked_due_to_incomplete_data,
        blocking_reasons=tuple(blocking_reasons),
    )


__all__ = [
    "evaluate_learning_capacity",
]
