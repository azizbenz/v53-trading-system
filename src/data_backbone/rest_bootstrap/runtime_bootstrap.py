"""
Minimal injectable runtime path for Build-2 REST bootstrap.
"""

from __future__ import annotations

import logging
from typing import Protocol

from pydantic import BaseModel

from .bootstrap_reporter import BootstrapEvent, BootstrapOutcome, BootstrapReporter
from .gap_fill_controller import GapFillDecision, GapFillResult, evaluate_gap_fill
from .rate_limit_guard import RateLimitGuard
from .snapshot_fetcher import Snapshot, SnapshotStatus, validate_snapshot_age


logger = logging.getLogger(__name__)


class SnapshotProvider(Protocol):
    """Injected provider used to fetch snapshots or controlled gap fills."""

    def fetch_snapshot(self, pair: str, data_type: str) -> Snapshot:
        ...

    def fill_gap(self, pair: str, data_type: str, gap_start: float, gap_end: float) -> Snapshot:
        ...


class BootstrapRunResult(BaseModel, frozen=True):
    """Observable result of a bootstrap or resync operation."""

    pair: str
    operation: str
    outcome: BootstrapOutcome
    snapshot: Snapshot | None = None
    gap_fill_result: GapFillResult | None = None
    blocked: bool = False
    message: str = ""


class RestBootstrapRuntime:
    """Injectable runtime for controlled REST bootstrap and recovery."""

    def __init__(
        self,
        provider: SnapshotProvider,
        *,
        rate_limit_guard: RateLimitGuard | None = None,
        reporter: BootstrapReporter | None = None,
    ) -> None:
        self._provider = provider
        self._rate_limit = rate_limit_guard or RateLimitGuard()
        self._reporter = reporter or BootstrapReporter()

    def bootstrap(
        self,
        pair: str,
        data_type: str,
        *,
        now: float,
        max_age_s: float = 10.0,
    ) -> BootstrapRunResult:
        logger.info(
            "rest_bootstrap_requested",
            extra={
                "pair": pair,
                "data_type": data_type,
                "timestamp": now,
                "max_age_s": max_age_s,
            },
        )
        if not self._rate_limit.record_call(now):
            return self._record(
                pair=pair,
                operation="bootstrap",
                outcome=BootstrapOutcome.RATE_LIMITED,
                timestamp=now,
                blocked=True,
                message="REST rate limit reached",
            )

        try:
            snapshot = self._provider.fetch_snapshot(pair, data_type)
        except Exception as exc:
            return self._record(
                pair=pair,
                operation="bootstrap",
                outcome=BootstrapOutcome.FETCH_ERROR,
                timestamp=now,
                blocked=True,
                message=str(exc),
            )

        validated = validate_snapshot_age(snapshot, max_age_s=max_age_s, now=now)
        if validated.status == SnapshotStatus.TOO_OLD:
            return self._record(
                pair=pair,
                operation="bootstrap",
                outcome=BootstrapOutcome.SNAPSHOT_TOO_OLD,
                timestamp=now,
                snapshot=validated,
                blocked=True,
                message=f"{pair}: snapshot too old ({validated.age_s:.3f}s)",
            )

        return self._record(
            pair=pair,
            operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS,
            timestamp=now,
            snapshot=validated,
            message=f"{pair}: snapshot accepted",
        )

    def resync(
        self,
        pair: str,
        data_type: str,
        *,
        gap_start: float,
        gap_end: float,
        now: float,
        max_gap_s: float = 300.0,
        max_age_s: float = 10.0,
    ) -> BootstrapRunResult:
        logger.info(
            "rest_gap_fill_requested",
            extra={
                "pair": pair,
                "data_type": data_type,
                "gap_start": gap_start,
                "gap_end": gap_end,
                "timestamp": now,
                "max_gap_s": max_gap_s,
                "max_age_s": max_age_s,
            },
        )
        gap_fill = evaluate_gap_fill(
            pair,
            gap_start,
            gap_end,
            max_gap_s=max_gap_s,
            rate_limited=not self._rate_limit.can_call(now),
        )
        if gap_fill.decision == GapFillDecision.REJECT_RATE_LIMITED:
            return self._record(
                pair=pair,
                operation="gap_fill",
                outcome=BootstrapOutcome.RATE_LIMITED,
                timestamp=now,
                gap_fill_result=gap_fill,
                blocked=True,
                message=gap_fill.message,
            )
        if gap_fill.decision == GapFillDecision.REJECT_TOO_LARGE:
            return self._record(
                pair=pair,
                operation="gap_fill",
                outcome=BootstrapOutcome.GAP_TOO_LARGE,
                timestamp=now,
                gap_fill_result=gap_fill,
                blocked=True,
                message=gap_fill.message,
            )

        self._rate_limit.record_call(now)
        try:
            snapshot = self._provider.fill_gap(pair, data_type, gap_start, gap_end)
        except Exception as exc:
            return self._record(
                pair=pair,
                operation="gap_fill",
                outcome=BootstrapOutcome.FETCH_ERROR,
                timestamp=now,
                gap_fill_result=gap_fill,
                blocked=True,
                message=str(exc),
            )

        validated = validate_snapshot_age(snapshot, max_age_s=max_age_s, now=now)
        if validated.status == SnapshotStatus.TOO_OLD:
            return self._record(
                pair=pair,
                operation="gap_fill",
                outcome=BootstrapOutcome.SNAPSHOT_TOO_OLD,
                timestamp=now,
                snapshot=validated,
                gap_fill_result=gap_fill,
                blocked=True,
                message=f"{pair}: gap fill snapshot too old ({validated.age_s:.3f}s)",
            )

        return self._record(
            pair=pair,
            operation="gap_fill",
            outcome=BootstrapOutcome.SUCCESS,
            timestamp=now,
            snapshot=validated,
            gap_fill_result=gap_fill,
            message=f"{pair}: gap fill accepted",
        )

    @property
    def reporter(self) -> BootstrapReporter:
        return self._reporter

    def _record(
        self,
        *,
        pair: str,
        operation: str,
        outcome: BootstrapOutcome,
        timestamp: float,
        snapshot: Snapshot | None = None,
        gap_fill_result: GapFillResult | None = None,
        blocked: bool = False,
        message: str = "",
    ) -> BootstrapRunResult:
        self._reporter.record(
            BootstrapEvent(
                pair=pair,
                operation=operation,
                outcome=outcome,
                timestamp=timestamp,
                message=message,
            )
        )
        return BootstrapRunResult(
            pair=pair,
            operation=operation,
            outcome=outcome,
            snapshot=snapshot,
            gap_fill_result=gap_fill_result,
            blocked=blocked,
            message=message,
        )
