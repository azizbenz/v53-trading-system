"""External daily orchestration state for governed Build-11 Shadow runs."""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

from interface_contracts.atomic_io import atomic_write_json
from .shadow_session_registry import ShadowSessionEntry


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
    shadow_day_recorded: bool = True
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
    last_error: str | None = None  # BS-65: set when state file was corrupted on load


class _ShadowSessionSummarySlotMetadata(BaseModel):
    """Minimal governed metadata needed to resolve a shadow slot session date."""

    base_session_date: str = ""
    session_dates: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_dates(self) -> "_ShadowSessionSummarySlotMetadata":
        if self.base_session_date:
            date.fromisoformat(self.base_session_date)
        for value in self.session_dates:
            date.fromisoformat(value)
        if self.base_session_date and self.session_dates:
            first_session_date = self.session_dates[0]
            if self.base_session_date != first_session_date:
                raise ValueError(
                    "shadow session summary requires base_session_date to equal the first session_dates entry"
                )
        return self


class _ReplayRunManifestSlotMetadata(BaseModel):
    """Minimal local replay export metadata needed to derive a governed session date."""

    timeframe_scope: str = Field(..., min_length=1)
    start_timestamp_ms: int = Field(..., ge=0)

    def resolve_session_date(self) -> str:
        first_segment = self.timeframe_scope.split("/", 1)[0].strip()
        if first_segment:
            try:
                return date.fromisoformat(first_segment).isoformat()
            except ValueError:
                normalized_datetime = first_segment.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized_datetime).date().isoformat()
        return datetime.fromtimestamp(
            self.start_timestamp_ms / 1000.0,
            tz=timezone.utc,
        ).date().isoformat()


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
                if not isinstance(data, dict):
                    raise ValueError(f"State root must be a JSON object, got {type(data).__name__}")
                return ShadowDailyOrchestratorState(**data)
            except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                # BS-65: fail-safe — backup corrupted file, reset with error marker
                backup = self._state_file.with_suffix(".corrupted")
                try:
                    self._state_file.rename(backup)
                except OSError:
                    pass
                return ShadowDailyOrchestratorState(
                    last_error=f"state_file_corrupted:{type(exc).__name__}:{exc}",
                )
        return ShadowDailyOrchestratorState()

    def _persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    @property
    def state_path(self) -> Path:
        return self._state_file

    def get_completed_runs(self) -> tuple[ShadowDailyExecutionRecord, ...]:
        return tuple(self._state.completed_runs)

    def counted_runs(self) -> tuple[ShadowDailyExecutionRecord, ...]:
        return tuple(
            record for record in self._state.completed_runs if record.shadow_day_recorded
        )

    def recorded_session_dates(self) -> tuple[str, ...]:
        return tuple(record.session_date for record in self._state.completed_runs)

    def completed_session_dates(self) -> tuple[str, ...]:
        return tuple(record.session_date for record in self.counted_runs())

    def last_completed_session_date(self) -> date | None:
        counted_runs = self.counted_runs()
        if not counted_runs:
            return None
        return date.fromisoformat(counted_runs[-1].session_date)

    def _load_json_object(self, path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return payload if isinstance(payload, dict) else None

    def _session_date_from_session_summary(self, export_dir: Path) -> str | None:
        payload = self._load_json_object(export_dir / "local_replay_shadow.shadow_session_summary.json")
        if payload is None:
            return None
        try:
            summary = _ShadowSessionSummarySlotMetadata.model_validate(payload)
        except ValueError:
            return None
        if summary.base_session_date:
            return summary.base_session_date
        if summary.session_dates:
            return summary.session_dates[0]
        return None

    def _session_date_from_session_registry(self, export_dir: Path) -> str | None:
        payload = self._load_json_object(export_dir / "shadow_session_registry.json")
        if payload is None:
            return None
        try:
            entries_payload = payload.get("entries")
            if not isinstance(entries_payload, list) or not entries_payload:
                return None
            first_entry = ShadowSessionEntry.model_validate(entries_payload[0])
        except (TypeError, ValueError):
            return None
        return first_entry.session_date

    def _session_date_from_run_manifest(self, export_dir: Path) -> str | None:
        payload = self._load_json_object(export_dir / "replay_run_manifest.json")
        if payload is None:
            return None
        try:
            manifest = _ReplayRunManifestSlotMetadata.model_validate(payload)
        except ValueError:
            return None
        return manifest.resolve_session_date()

    def _resolved_session_dates_by_source(self, export_dir: Path) -> dict[str, str]:
        session_dates: dict[str, str] = {}
        for source_name, resolver in (
            ("shadow_session_summary", self._session_date_from_session_summary),
            ("shadow_session_registry", self._session_date_from_session_registry),
            ("replay_run_manifest", self._session_date_from_run_manifest),
        ):
            session_date = resolver(export_dir)
            if session_date is not None:
                session_dates[source_name] = session_date
        return session_dates

    def _resolve_slot_session_date(self, export_dir: Path) -> str | None:
        session_dates_by_source = self._resolved_session_dates_by_source(export_dir)
        if not session_dates_by_source:
            return None
        unique_dates = {value for value in session_dates_by_source.values()}
        if len(unique_dates) > 1:
            details = ", ".join(
                f"{source_name}={session_date}"
                for source_name, session_date in session_dates_by_source.items()
            )
            raise ValueError(
                "Shadow slot session_date mismatch across governed metadata sources: "
                + details
            )
        return next(iter(session_dates_by_source.values()))

    def build_slot_from_export_dir(self, export_dir: Path) -> ShadowDailyPlanSlot | None:
        session_date = self._resolve_slot_session_date(export_dir)
        if session_date is None:
            return None
        return ShadowDailyPlanSlot(
            session_date=session_date,
            export_dir_ref=str(export_dir.resolve()),
        )

    def discover_slots(self, exports_root: Path) -> tuple[ShadowDailyPlanSlot, ...]:
        slots: list[ShadowDailyPlanSlot] = []
        if not exports_root.exists():
            return ()
        for item in exports_root.iterdir():
            if not item.is_dir():
                continue
            try:
                slot = self.build_slot_from_export_dir(item)
            except ValueError:
                continue
            if slot is None:
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
