"""External daily orchestration state for governed Build-11 Shadow runs."""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts.atomic_io import atomic_write_json


class ShadowDailyPlanSlot(BaseModel, frozen=True):
    """Single daily Shadow slot discovered by the external orchestrator."""

    session_date: str = Field(..., min_length=10)
    export_dir_ref: str = ""

    @model_validator(mode="after")
    def validate_session_date(self) -> "ShadowDailyPlanSlot":
        date.fromisoformat(self.session_date)
        return self


class ShadowDailyExecutionRecord(BaseModel, frozen=True):
    """Audit-ready record of one external daily Shadow orchestration run."""

    session_date: str = Field(..., min_length=10)
    export_dir_ref: str = ""
    shadow_output_dir_ref: str = Field(..., min_length=1)
    local_replay_evidence_ref: str = ""
    shadow_runtime_evidence_ref: str = ""
    shadow_summary_ref: str = Field(..., min_length=1)
    shadow_report_ref: str = Field(..., min_length=1)
    shadow_session_summary_ref: str = Field(..., min_length=1)
    shadow_session_registry_ref: str = Field(..., min_length=1)
    accepted: bool = False
    consecutive_days: int = Field(..., ge=0)
    remaining_days: int = Field(..., ge=0)
    recorded_at: float = Field(default_factory=time.time)

    @model_validator(mode="after")
    def validate_session_date(self) -> "ShadowDailyExecutionRecord":
        date.fromisoformat(self.session_date)
        return self


class ShadowDailyOrchestratorState(BaseModel):
    """Persisted external daily orchestration ledger."""

    completed_runs: list[ShadowDailyExecutionRecord] = Field(default_factory=list)


class ShadowDailyOrchestrator:
    """Persist and select governed daily Shadow runs across invocations."""

    def __init__(
        self,
        state_dir: Path,
        *,
        state_filename: str = "shadow_daily_orchestrator.state.json",
    ) -> None:
        self._state_dir = state_dir
        self._state_file = state_dir / state_filename
        self._state = self._load_or_create()

    def _load_or_create(self) -> ShadowDailyOrchestratorState:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                return ShadowDailyOrchestratorState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return ShadowDailyOrchestratorState()

    def _persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    @property
    def state_path(self) -> Path:
        return self._state_file

    def get_completed_runs(self) -> tuple[ShadowDailyExecutionRecord, ...]:
        return tuple(self._state.completed_runs)

    def completed_session_dates(self) -> tuple[str, ...]:
        return tuple(record.session_date for record in self._state.completed_runs)

    def last_completed_session_date(self) -> date | None:
        if not self._state.completed_runs:
            return None
        return date.fromisoformat(self._state.completed_runs[-1].session_date)

    def discover_slots(self, exports_root: Path) -> tuple[ShadowDailyPlanSlot, ...]:
        slots: list[ShadowDailyPlanSlot] = []
        if not exports_root.exists():
            return ()
        for item in exports_root.iterdir():
            if not item.is_dir():
                continue
            try:
                slot = ShadowDailyPlanSlot(
                    session_date=item.name,
                    export_dir_ref=str(item.resolve()),
                )
            except ValueError:
                continue
            slots.append(slot)
        slots.sort(key=lambda slot: slot.session_date)
        return tuple(slots)

    def select_next_slot(self, exports_root: Path) -> ShadowDailyPlanSlot | None:
        completed = set(self.completed_session_dates())
        for slot in self.discover_slots(exports_root):
            if slot.session_date not in completed:
                return slot
        return None

    def next_demo_slot(self, *, start_date: str | None = None) -> ShadowDailyPlanSlot:
        if start_date is not None:
            return ShadowDailyPlanSlot(session_date=start_date)
        last_date = self.last_completed_session_date()
        if last_date is not None:
            return ShadowDailyPlanSlot(session_date=(last_date + timedelta(days=1)).isoformat())
        today_utc = datetime.now(tz=timezone.utc).date().isoformat()
        return ShadowDailyPlanSlot(session_date=today_utc)

    def record_execution(self, record: ShadowDailyExecutionRecord) -> None:
        existing_dates = set(self.completed_session_dates())
        if record.session_date in existing_dates:
            raise ValueError(
                "Shadow daily orchestrator already completed session_date="
                f"{record.session_date}"
            )
        last_date = self.last_completed_session_date()
        current_date = date.fromisoformat(record.session_date)
        if last_date is not None and current_date <= last_date:
            raise ValueError(
                "Shadow daily orchestrator requires strictly increasing session_date values"
            )
        self._state.completed_runs.append(record)
        self._persist()


__all__ = [
    "ShadowDailyPlanSlot",
    "ShadowDailyExecutionRecord",
    "ShadowDailyOrchestratorState",
    "ShadowDailyOrchestrator",
]
