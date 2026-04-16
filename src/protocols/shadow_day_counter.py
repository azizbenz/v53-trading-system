"""
Shadow day counter.

Non-negotiable rules:
1. Light must shadow trade 30 consecutive days before Complete activation.
2. Complete must shadow trade 30 consecutive days before going live.
3. A gap > 24h between shadow runs resets the counter to 0.
4. Counter is persisted to disk.
5. Daily report is generated at each day increment.
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from protocols.shadow_day_counter_models import (
    ShadowCounterState,
    ShadowDayRecord,
    ShadowProfile,
)
from protocols.shadow_day_counter_reporting import generate_shadow_report

_MAX_GAP_SECONDS = 24 * 3600
_STATE_FILENAME = "shadow_counter_{profile}.json"


class ShadowDayCounter:
    """Track consecutive shadow trading days with persistent governed state."""

    def __init__(self, state_dir: Path, profile: ShadowProfile) -> None:
        self._state_dir = state_dir
        self._profile = profile
        self._state_file = state_dir / _STATE_FILENAME.format(profile=profile.value)
        self._state = self._load_or_create()

    def _load_or_create(self) -> ShadowCounterState:
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(
                        f"State root must be a JSON object, got {type(data).__name__}"
                    )
                return ShadowCounterState.model_validate(data)
            except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                backup = self._state_file.with_suffix(".corrupted")
                try:
                    self._state_file.rename(backup)
                except OSError:
                    pass
                return ShadowCounterState(
                    profile=self._profile,
                    last_error=f"state_file_corrupted:{type(exc).__name__}:{exc}",
                )
        return ShadowCounterState(profile=self._profile)

    def _persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    def _replace_state(self, **updates: object) -> None:
        payload = self._state.model_dump(mode="python")
        payload.update(updates)
        self._state = ShadowCounterState.model_validate(payload)

    def record_shadow_day(
        self,
        passed_all_gates: bool,
        metrics_summary: dict[str, float | str] | None = None,
        now: float | None = None,
    ) -> ShadowDayRecord:
        """Record a completed shadow trading day under the hard 24h continuity rule."""

        ts = time.time() if now is None else now
        if self._state.last_shadow_timestamp is not None:
            gap = ts - self._state.last_shadow_timestamp
            if gap > _MAX_GAP_SECONDS:
                self._replace_state(
                    consecutive_days=0,
                    resets=self._state.resets + 1,
                    daily_records=[],
                    started_at=None,
                )

        self._replace_state(last_shadow_timestamp=ts)
        if not passed_all_gates:
            record = ShadowDayRecord(
                day_number=self._state.consecutive_days,
                date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                timestamp=ts,
                profile=self._profile,
                passed_all_gates=False,
                metrics_summary=metrics_summary or {},
            )
            self._persist()
            return record

        if self._state.started_at is None:
            self._replace_state(started_at=ts)

        next_consecutive_days = self._state.consecutive_days + 1
        record = ShadowDayRecord(
            day_number=next_consecutive_days,
            date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            timestamp=ts,
            profile=self._profile,
            passed_all_gates=True,
            metrics_summary=metrics_summary or {},
        )
        self._replace_state(
            consecutive_days=next_consecutive_days,
            daily_records=[*self._state.daily_records, record],
        )
        self._persist()
        return record

    def is_promotion_ready(self) -> bool:
        return self._state.is_complete

    def get_status(self) -> ShadowCounterState:
        return self._state

    def recover_from_records(self, records: tuple[ShadowDayRecord, ...]) -> None:
        """Rebuild state from durable successful day records after counter corruption."""

        if not records:
            raise ValueError("ShadowDayCounter.recover_from_records requires at least one record")

        previous_date: date | None = None
        previous_timestamp: float | None = None
        for index, record in enumerate(records, start=1):
            if record.profile != self._profile:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires matching profile records"
                )
            if not record.passed_all_gates:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires successful records only"
                )
            if record.day_number != index:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires contiguous day_number values"
                )
            current_date = date.fromisoformat(record.date)
            if previous_date is not None and current_date <= previous_date:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires strictly increasing dates"
                )
            if previous_timestamp is not None and record.timestamp <= previous_timestamp:
                raise ValueError(
                    "ShadowDayCounter.recover_from_records requires strictly increasing timestamps"
                )
            previous_date = current_date
            previous_timestamp = record.timestamp

        self._replace_state(
            consecutive_days=len(records),
            last_shadow_timestamp=records[-1].timestamp,
            started_at=records[0].timestamp,
            daily_records=list(records),
            last_error=None,
        )
        self._persist()

    def generate_report(self) -> dict[str, object]:
        """Generate the governed shadow promotion report."""

        return generate_shadow_report(self._state)

    def save_report(self, report_dir: Path | None = None) -> Path:
        target_dir = report_dir or self._state_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = target_dir / f"shadow_report_{self._profile.value}_{ts}.json"
        atomic_write_json(report_file, report)
        return report_file


__all__ = [
    "ShadowCounterState",
    "ShadowDayCounter",
    "ShadowDayRecord",
    "ShadowProfile",
]
