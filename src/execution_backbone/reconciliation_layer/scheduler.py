"""Bounded boot + periodic reconciliation scheduler for the canonical Build-3 rail."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError
from execution_backbone.emergency_circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchReason,
)

from .recovery_trigger import RecoveryAction


class ReconciliationSchedulerCalibrationConfig(BaseModel, frozen=True):
    """Opt-in calibration seam for THR-I04."""

    calibration_root: str = "config/calibration"
    calibration_version: str = "v1"
    reconciliation_interval_threshold_id: str = "THR-I04"
    minimum_interval_s: float = Field(default=60.0, gt=0.0)
    maximum_interval_s: float = Field(default=86_400.0, gt=0.0)


class ReconciliationSchedulerThresholds(BaseModel, frozen=True):
    """Typed threshold set for the bounded reconciliation scheduler seam."""

    periodic_interval_s: float = Field(..., gt=0.0)

    @classmethod
    def from_documented_defaults(cls) -> "ReconciliationSchedulerThresholds":
        return cls(periodic_interval_s=3600.0)


class ReconciliationSchedulerTrigger(StrEnum):
    BOOT = "boot"
    PERIODIC = "periodic"


class ReconciliationSchedulerState(BaseModel, frozen=True):
    """Persisted in-memory state of the bounded reconciliation scheduler."""

    boot_completed: bool = False
    boot_blocked_trading: bool = False
    last_run_trigger: ReconciliationSchedulerTrigger | None = None
    last_run_ts: float | None = None
    next_due_ts: float | None = None
    last_recovery_action: str = RecoveryAction.NONE.value
    last_max_severity: str = "info"


class ReconciliationSchedulerRunResult(BaseModel, frozen=True):
    """Typed scheduler result for the boot/periodic seam."""

    trigger: ReconciliationSchedulerTrigger
    executed: bool
    now: float = Field(..., ge=0.0)
    interval_s: float = Field(..., gt=0.0)
    trading_blocked: bool = False
    circuit_breaker_tripped: bool = False
    detail: str = ""
    recovery_action: str = RecoveryAction.NONE.value
    divergence_count: int = Field(default=0, ge=0)
    runtime_result: Any = None
    state: ReconciliationSchedulerState = Field(default_factory=ReconciliationSchedulerState)


class ReconciliationExecutor(Protocol):
    """Minimal executor surface required by the bounded scheduler seam."""

    def reconcile(self, now: float) -> Any:
        ...


def resolve_reconciliation_scheduler_thresholds(
    config: ReconciliationSchedulerCalibrationConfig | None = None,
) -> ReconciliationSchedulerThresholds:
    """Resolve THR-I04 from the shared calibration catalog."""

    calibration = config or ReconciliationSchedulerCalibrationConfig()
    if calibration.minimum_interval_s > calibration.maximum_interval_s:
        raise CalibrationArtifactValidationError(
            "THR-I04 minimum_interval_s must be <= maximum_interval_s"
        )
    loader = CalibrationLoader(calibration.calibration_root)
    collection = loader.load(version=calibration.calibration_version)
    raw_value = loader.get_value(
        collection,
        calibration.reconciliation_interval_threshold_id,
    )
    interval_s = _resolve_positive_float(
        raw_value,
        threshold_id=calibration.reconciliation_interval_threshold_id,
    )
    if interval_s < calibration.minimum_interval_s:
        raise CalibrationArtifactValidationError(
            "THR-I04 falls below the bounded reconciliation minimum interval"
        )
    if interval_s > calibration.maximum_interval_s:
        raise CalibrationArtifactValidationError(
            "THR-I04 exceeds the bounded reconciliation maximum interval"
        )
    return ReconciliationSchedulerThresholds(periodic_interval_s=interval_s)


class ReconciliationScheduler:
    """Bounded boot + periodic scheduler for canonical reconciliation calls."""

    def __init__(
        self,
        thresholds: ReconciliationSchedulerThresholds | None = None,
    ) -> None:
        self._thresholds = thresholds or ReconciliationSchedulerThresholds.from_documented_defaults()
        self._state = ReconciliationSchedulerState()

    @property
    def state(self) -> ReconciliationSchedulerState:
        return self._state

    def boot_reconcile(
        self,
        executor: ReconciliationExecutor,
        *,
        now: float,
        circuit_breaker: EmergencyCircuitBreaker | None = None,
        trip_circuit_breaker_on_unresolved: bool = True,
    ) -> ReconciliationSchedulerRunResult:
        timestamp = _require_scheduler_timestamp(now, context="ReconciliationScheduler.boot_reconcile")
        runtime_result = executor.reconcile(timestamp)
        stale_only_bootstrap = _is_stale_only_bootstrap_reconciliation(runtime_result)
        unresolved = (
            runtime_result.recovery_decision.action != RecoveryAction.NONE
            and not stale_only_bootstrap
        )
        circuit_breaker_tripped = False
        if unresolved and circuit_breaker is not None and trip_circuit_breaker_on_unresolved:
            circuit_breaker.trip(
                KillSwitchReason.CRITICAL_DIVERGENCE,
                (
                    "boot reconciliation found unresolved divergences: "
                    f"{runtime_result.recovery_decision.reason}"
                ),
            )
            circuit_breaker_tripped = True
        self._state = ReconciliationSchedulerState(
            boot_completed=True,
            boot_blocked_trading=unresolved,
            last_run_trigger=ReconciliationSchedulerTrigger.BOOT,
            last_run_ts=timestamp,
            next_due_ts=timestamp + self._thresholds.periodic_interval_s,
            last_recovery_action=runtime_result.recovery_decision.action.value,
            last_max_severity=runtime_result.divergence_summary.max_severity.value,
        )
        return ReconciliationSchedulerRunResult(
            trigger=ReconciliationSchedulerTrigger.BOOT,
            executed=True,
            now=timestamp,
            interval_s=self._thresholds.periodic_interval_s,
            trading_blocked=unresolved,
            circuit_breaker_tripped=circuit_breaker_tripped,
            detail=(
                "boot reconciliation established the initial aligned baseline"
                if stale_only_bootstrap
                else (
                "boot reconciliation found unresolved divergences"
                if unresolved
                else "boot reconciliation aligned local and remote state"
                )
            ),
            recovery_action=runtime_result.recovery_decision.action.value,
            divergence_count=runtime_result.divergence_summary.total_divergences,
            runtime_result=runtime_result,
            state=self._state,
        )

    def run_periodic_if_due(
        self,
        executor: ReconciliationExecutor,
        *,
        now: float,
        circuit_breaker: EmergencyCircuitBreaker | None = None,
        trip_circuit_breaker_on_critical: bool = True,
    ) -> ReconciliationSchedulerRunResult:
        timestamp = _require_scheduler_timestamp(
            now,
            context="ReconciliationScheduler.run_periodic_if_due",
        )
        if self._state.next_due_ts is None:
            return ReconciliationSchedulerRunResult(
                trigger=ReconciliationSchedulerTrigger.PERIODIC,
                executed=False,
                now=timestamp,
                interval_s=self._thresholds.periodic_interval_s,
                detail="periodic reconciliation unavailable before boot reconciliation",
                state=self._state,
            )
        if timestamp < self._state.next_due_ts:
            return ReconciliationSchedulerRunResult(
                trigger=ReconciliationSchedulerTrigger.PERIODIC,
                executed=False,
                now=timestamp,
                interval_s=self._thresholds.periodic_interval_s,
                detail="periodic reconciliation not due yet",
                state=self._state,
            )
        runtime_result = executor.reconcile(timestamp)
        critical = (
            runtime_result.divergence_summary.is_critical
            or runtime_result.recovery_decision.action == RecoveryAction.HALT_TRADING
        )
        circuit_breaker_tripped = False
        if critical and circuit_breaker is not None and trip_circuit_breaker_on_critical:
            circuit_breaker.trip(
                KillSwitchReason.CRITICAL_DIVERGENCE,
                (
                    "periodic reconciliation found critical divergences: "
                    f"{runtime_result.recovery_decision.reason}"
                ),
            )
            circuit_breaker_tripped = True
        self._state = ReconciliationSchedulerState(
            boot_completed=self._state.boot_completed,
            boot_blocked_trading=self._state.boot_blocked_trading,
            last_run_trigger=ReconciliationSchedulerTrigger.PERIODIC,
            last_run_ts=timestamp,
            next_due_ts=timestamp + self._thresholds.periodic_interval_s,
            last_recovery_action=runtime_result.recovery_decision.action.value,
            last_max_severity=runtime_result.divergence_summary.max_severity.value,
        )
        return ReconciliationSchedulerRunResult(
            trigger=ReconciliationSchedulerTrigger.PERIODIC,
            executed=True,
            now=timestamp,
            interval_s=self._thresholds.periodic_interval_s,
            trading_blocked=critical,
            circuit_breaker_tripped=circuit_breaker_tripped,
            detail=(
                "periodic reconciliation found critical divergences"
                if critical
                else "periodic reconciliation completed"
            ),
            recovery_action=runtime_result.recovery_decision.action.value,
            divergence_count=runtime_result.divergence_summary.total_divergences,
            runtime_result=runtime_result,
            state=self._state,
        )


def _resolve_positive_float(
    raw_value: bool | int | float | str,
    *,
    threshold_id: str,
) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    if isinstance(raw_value, str):
        try:
            raw_value = float(raw_value)
        except ValueError as exc:
            raise CalibrationArtifactValidationError(
                f"{threshold_id} must be numeric, got {raw_value!r}"
            ) from exc
    value = float(raw_value)
    if not math.isfinite(value) or value <= 0.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite positive float"
        )
    return value


def _require_scheduler_timestamp(now: float, *, context: str) -> float:
    if not math.isfinite(now):
        raise ValueError(f"{context} requires finite now")
    if now <= 0.0:
        raise ValueError(f"{context} requires now > 0")
    return now


def _is_stale_only_bootstrap_reconciliation(runtime_result: Any) -> bool:
    recovery_decision = runtime_result.recovery_decision
    return (
        recovery_decision.action == RecoveryAction.SOFT_RESYNC
        and recovery_decision.stale_reconciliation is True
        and runtime_result.divergence_summary.total_divergences == 0
    )


__all__ = [
    "ReconciliationExecutor",
    "ReconciliationScheduler",
    "ReconciliationSchedulerCalibrationConfig",
    "ReconciliationSchedulerRunResult",
    "ReconciliationSchedulerState",
    "ReconciliationSchedulerThresholds",
    "ReconciliationSchedulerTrigger",
    "resolve_reconciliation_scheduler_thresholds",
]
