"""Typed daily PnL breaker with persistent same-day shadow lock."""

from __future__ import annotations

import json
import math
import time
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError
from interface_contracts.atomic_io import atomic_write_json
from risk_backbone.emergency_kill_switch.circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchReason,
)


class DailyPnlBreakerCalibrationConfig(BaseModel, frozen=True):
    """Opt-in calibration seam for THR-R01."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    intraday_breaker_threshold_id: str = "THR-R01"
    hard_cap_drawdown_pct: float = Field(default=0.02, gt=0.0)


class DailyPnlBreakerThresholds(BaseModel, frozen=True):
    """Typed threshold set for the bounded daily breaker seam."""

    intraday_drawdown_breach_pct: float = Field(..., gt=0.0)

    @classmethod
    def from_documented_defaults(cls) -> "DailyPnlBreakerThresholds":
        return cls(intraday_drawdown_breach_pct=0.02)


class DailyPnlBreakerVerdict(StrEnum):
    ACCEPTED = "accepted"
    SHADOW_RECOMMENDED = "shadow_recommended"
    SHADOW_LOCKED = "shadow_locked"


class DailyPnlBreakerState(BaseModel, frozen=True):
    """Persisted daily breaker state."""

    shadow_locked_session_date: str = ""
    state_corrupted: bool = False
    last_reason: str = ""
    last_drawdown_pct: float = Field(default=0.0, ge=0.0)
    last_updated_ts: float | None = None


class DailyPnlBreakerAssessment(BaseModel, frozen=True):
    """Typed assessment returned by the daily breaker."""

    session_date: str
    verdict: DailyPnlBreakerVerdict
    current_equity: float = Field(..., ge=0.0)
    session_peak_equity: float = Field(..., ge=0.0)
    drawdown_pct: float = Field(..., ge=0.0)
    threshold_pct: float = Field(..., gt=0.0)
    should_force_shadow: bool = False
    circuit_breaker_tripped: bool = False
    circuit_breaker_reason: str = ""
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    state: DailyPnlBreakerState = Field(default_factory=DailyPnlBreakerState)


def resolve_daily_pnl_breaker_thresholds(
    config: DailyPnlBreakerCalibrationConfig | None = None,
) -> DailyPnlBreakerThresholds:
    """Resolve THR-R01 from the shared calibration catalog."""

    calibration = config or DailyPnlBreakerCalibrationConfig()
    loader = CalibrationLoader(calibration.calibration_root)
    collection = loader.load(version=calibration.calibration_version)
    raw_value = loader.get_value(
        collection,
        calibration.intraday_breaker_threshold_id,
    )
    threshold_value = _resolve_positive_float(
        raw_value,
        threshold_id=calibration.intraday_breaker_threshold_id,
    )
    if threshold_value > calibration.hard_cap_drawdown_pct:
        raise CalibrationArtifactValidationError(
            "THR-R01 exceeds the bounded daily breaker hard cap; "
            "calibration may tighten this seam but must not relax it beyond 2%"
        )
    return DailyPnlBreakerThresholds(
        intraday_drawdown_breach_pct=threshold_value,
    )


class DailyPnlBreaker:
    """Persistent daily shadow lock derived from governed equity state."""

    def __init__(
        self,
        *,
        state_dir: Path,
        state_filename: str = "daily_pnl_breaker_state.json",
    ) -> None:
        self._state_dir = state_dir
        self._state_path = state_dir / state_filename
        self._state = DailyPnlBreakerState()
        self._restore_from_disk()

    @property
    def state(self) -> DailyPnlBreakerState:
        return self._state

    def evaluate(
        self,
        *,
        session_date: str,
        current_equity: float,
        session_peak_equity: float,
        thresholds: DailyPnlBreakerThresholds | None = None,
        circuit_breaker: EmergencyCircuitBreaker | None = None,
        trip_circuit_breaker_on_breach: bool = False,
        now_ts: float | None = None,
    ) -> DailyPnlBreakerAssessment:
        threshold_set = thresholds or DailyPnlBreakerThresholds.from_documented_defaults()
        evaluated_session_date = _normalize_session_date(session_date)
        drawdown_pct = _compute_drawdown_pct(
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
        )
        current_ts = time.time() if now_ts is None else now_ts

        if self._state.state_corrupted:
            assessment = DailyPnlBreakerAssessment(
                session_date=evaluated_session_date,
                verdict=DailyPnlBreakerVerdict.SHADOW_LOCKED,
                current_equity=current_equity,
                session_peak_equity=session_peak_equity,
                drawdown_pct=drawdown_pct,
                threshold_pct=threshold_set.intraday_drawdown_breach_pct,
                should_force_shadow=True,
                circuit_breaker_tripped=_maybe_trip_circuit_breaker(
                    circuit_breaker=circuit_breaker,
                    trip_circuit_breaker_on_breach=trip_circuit_breaker_on_breach,
                    detail="daily breaker state corruption requires manual operator review",
                ),
                circuit_breaker_reason=(
                    KillSwitchReason.LOSS_BUDGET_BREACH.value
                    if circuit_breaker is not None and trip_circuit_breaker_on_breach
                    else ""
                ),
                reason_codes=("RISK_DAILY_BREAKER_STATE_CORRUPTED",),
                detail="daily breaker state file is corrupted; keep runtime shadowed until explicit reset",
                state=self._state,
            )
            return assessment

        if self._state.shadow_locked_session_date:
            locked_session_date = _normalize_session_date(self._state.shadow_locked_session_date)
            if evaluated_session_date < locked_session_date:
                raise ValueError(
                    "daily breaker session_date cannot move backwards once a shadow lock was recorded"
                )
            if evaluated_session_date > locked_session_date:
                self._state = DailyPnlBreakerState()
                self._persist()

        if self._state.shadow_locked_session_date == evaluated_session_date:
            return DailyPnlBreakerAssessment(
                session_date=evaluated_session_date,
                verdict=DailyPnlBreakerVerdict.SHADOW_LOCKED,
                current_equity=current_equity,
                session_peak_equity=session_peak_equity,
                drawdown_pct=drawdown_pct,
                threshold_pct=threshold_set.intraday_drawdown_breach_pct,
                should_force_shadow=True,
                reason_codes=("RISK_DAILY_BREAKER_ALREADY_LOCKED",),
                detail=(
                    f"daily breaker already locked Shadow for governed session {evaluated_session_date}; "
                    "no automatic same-day reactivation"
                ),
                state=self._state,
            )

        if drawdown_pct >= threshold_set.intraday_drawdown_breach_pct:
            self._state = DailyPnlBreakerState(
                shadow_locked_session_date=evaluated_session_date,
                last_reason="intraday_drawdown_breach",
                last_drawdown_pct=drawdown_pct,
                last_updated_ts=current_ts,
            )
            self._persist()
            circuit_breaker_tripped = _maybe_trip_circuit_breaker(
                circuit_breaker=circuit_breaker,
                trip_circuit_breaker_on_breach=trip_circuit_breaker_on_breach,
                detail=(
                    "daily breaker breach "
                    f"{drawdown_pct:.4f} >= {threshold_set.intraday_drawdown_breach_pct:.4f}"
                ),
            )
            return DailyPnlBreakerAssessment(
                session_date=evaluated_session_date,
                verdict=DailyPnlBreakerVerdict.SHADOW_RECOMMENDED,
                current_equity=current_equity,
                session_peak_equity=session_peak_equity,
                drawdown_pct=drawdown_pct,
                threshold_pct=threshold_set.intraday_drawdown_breach_pct,
                should_force_shadow=True,
                circuit_breaker_tripped=circuit_breaker_tripped,
                circuit_breaker_reason=(
                    KillSwitchReason.LOSS_BUDGET_BREACH.value
                    if circuit_breaker_tripped
                    else ""
                ),
                reason_codes=("RISK_DAILY_BREAKER_BREACHED",),
                detail=(
                    f"intraday drawdown {drawdown_pct:.4f} >= daily breaker "
                    f"{threshold_set.intraday_drawdown_breach_pct:.4f}; shadow lock recorded "
                    f"for governed session {evaluated_session_date}"
                ),
                state=self._state,
            )

        self._state = DailyPnlBreakerState(
            last_reason="accepted",
            last_drawdown_pct=drawdown_pct,
            last_updated_ts=current_ts,
        )
        self._persist()
        return DailyPnlBreakerAssessment(
            session_date=evaluated_session_date,
            verdict=DailyPnlBreakerVerdict.ACCEPTED,
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
            drawdown_pct=drawdown_pct,
            threshold_pct=threshold_set.intraday_drawdown_breach_pct,
            should_force_shadow=False,
            reason_codes=("RISK_DAILY_BREAKER_ACCEPTED",),
            detail="intraday drawdown remains below the daily breaker threshold",
            state=self._state,
        )

    def reset(self, *, operator_detail: str = "") -> DailyPnlBreakerState:
        self._state = DailyPnlBreakerState(
            last_reason=f"operator_reset:{operator_detail}" if operator_detail else "operator_reset",
            last_updated_ts=time.time(),
        )
        self._persist()
        return self._state

    def _restore_from_disk(self) -> None:
        if not self._state_path.exists():
            return
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
            self._state = DailyPnlBreakerState.model_validate(payload)
        except Exception:
            self._state = DailyPnlBreakerState(
                state_corrupted=True,
                last_reason="state_corrupted",
                last_updated_ts=time.time(),
            )
            self._persist()

    def _persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(
            self._state_path,
            self._state.model_dump(mode="json"),
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


def _compute_drawdown_pct(*, current_equity: float, session_peak_equity: float) -> float:
    if not math.isfinite(current_equity) or current_equity < 0.0:
        raise ValueError("daily breaker requires finite current_equity >= 0")
    if not math.isfinite(session_peak_equity) or session_peak_equity <= 0.0:
        raise ValueError("daily breaker requires finite session_peak_equity > 0")
    return max(0.0, (session_peak_equity - current_equity) / session_peak_equity)


def _normalize_session_date(value: str) -> str:
    if not value:
        raise ValueError("daily breaker requires non-empty session_date")
    return date.fromisoformat(value).isoformat()


def _maybe_trip_circuit_breaker(
    *,
    circuit_breaker: EmergencyCircuitBreaker | None,
    trip_circuit_breaker_on_breach: bool,
    detail: str,
) -> bool:
    if circuit_breaker is None or not trip_circuit_breaker_on_breach:
        return False
    circuit_breaker.trip(KillSwitchReason.LOSS_BUDGET_BREACH, detail)
    return True


__all__ = [
    "DailyPnlBreaker",
    "DailyPnlBreakerAssessment",
    "DailyPnlBreakerCalibrationConfig",
    "DailyPnlBreakerState",
    "DailyPnlBreakerThresholds",
    "DailyPnlBreakerVerdict",
    "resolve_daily_pnl_breaker_thresholds",
]
