"""Persistent registry of governed Build-11 Shadow session days."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


class ShadowSessionEntry(BaseModel, frozen=True):
    """Single recorded Shadow day appended to the governed session registry."""

    session_date: str = Field(..., min_length=10)
    counter_day_number: int = Field(..., ge=0)
    correlation_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    day_record_ref: str = ""
    export_dir_ref: str = ""


class ShadowSessionRegistryState(BaseModel):
    """Persisted registry of governed Shadow days."""

    entries: list[ShadowSessionEntry] = Field(default_factory=list)


class ShadowSessionRegistry:
    """Append-only registry used to resume a governed Shadow session across runs."""

    def __init__(
        self,
        state_dir: Path,
        *,
        state_filename: str = "shadow_session_registry.json",
    ) -> None:
        self._state_dir = state_dir
        self._state_file = state_dir / state_filename
        self._state = self._load_or_create()

    def _load_or_create(self) -> ShadowSessionRegistryState:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                return ShadowSessionRegistryState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return ShadowSessionRegistryState()

    def _persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    def get_entries(self) -> tuple[ShadowSessionEntry, ...]:
        return tuple(self._state.entries)

    def last_session_date(self) -> date | None:
        if not self._state.entries:
            return None
        return date.fromisoformat(self._state.entries[-1].session_date)

    def validate_session_dates(self, session_dates: tuple[str, ...]) -> None:
        if not session_dates:
            return
        parsed_dates = tuple(date.fromisoformat(value) for value in session_dates)
        if len(parsed_dates) != len(set(parsed_dates)):
            raise ValueError(
                "Shadow session registry entries must be unique per session_date"
            )
        for previous_date, current_date in zip(parsed_dates, parsed_dates[1:]):
            if current_date <= previous_date:
                raise ValueError(
                    "Shadow session registry requires strictly increasing session_date values"
                )
        last_date = self.last_session_date()
        first_new_date = parsed_dates[0]
        if last_date is not None and first_new_date <= last_date:
            raise ValueError(
                "Shadow session registry already recorded session_date(s): "
                + ", ".join(
                    value
                    for value in session_dates
                    if date.fromisoformat(value) <= last_date
                )
            )

    @property
    def state_path(self) -> Path:
        return self._state_file

    def append_entries(self, entries: tuple[ShadowSessionEntry, ...]) -> None:
        if not entries:
            return
        self.validate_session_dates(tuple(entry.session_date for entry in entries))
        self._state.entries.extend(entries)
        self._persist()


__all__ = [
    "ShadowSessionEntry",
    "ShadowSessionRegistryState",
    "ShadowSessionRegistry",
]
