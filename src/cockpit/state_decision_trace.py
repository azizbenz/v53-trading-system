"""Phase 2.5 adapter - bounded decision trace from replay DTR or service logs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from pydantic import BaseModel, Field

from cockpit.state_freshness import (
    OperationalSourceSnapshot,
    latest_export_dir,
    source_stamp,
)


class DecisionTraceRow(BaseModel, frozen=True):
    timestamp: str = Field(..., min_length=1)
    pair: str = ""
    engine: str = ""
    raw_score: float | None = None
    penalized_score: float | None = None
    final_score: float | None = None
    selected: bool = False
    hard_blocked: bool = False
    refusal_reason: str = ""
    expected_cost: float | None = None
    expected_ce: float | None = None
    final_size: float | None = None

    @property
    def ce_net(self) -> float | None:
        return self.expected_ce


class DecisionTraceSnapshot(OperationalSourceSnapshot):
    entries: tuple[DecisionTraceRow, ...] = ()
    source_message: str = ""
    skipped_corrupt_row_count: int = 0


def _to_iso(timestamp: object) -> str:
    try:
        value = float(timestamp)
    except (TypeError, ValueError):
        return "unknown"
    return datetime.fromtimestamp(value, tz=UTC).isoformat()


def read_decision_trace(auto_exports_root: Path, *, max_entries: int = 12) -> DecisionTraceSnapshot:
    """Parse the latest replay DTR file when it exists."""

    latest = latest_export_dir(auto_exports_root)
    dtr_path = latest / "replay_dtr.jsonl" if latest is not None else None
    if dtr_path is None or not dtr_path.is_file():
        return DecisionTraceSnapshot(
            source_status="not_yet_persisted",
            source_file=str(dtr_path) if dtr_path is not None else None,
            last_modified_at=None,
            age_seconds=None,
            reason_codes=("decision_trace_not_yet_persisted",),
            source_message=(
                "Decision trace not yet persisted. Need replay_dtr.jsonl or service decision log."
            ),
        )
    stamp = source_stamp(path=dtr_path, stale_after_seconds=300.0)
    rows: list[DecisionTraceRow] = []
    skipped = 0
    try:
        lines = dtr_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return DecisionTraceSnapshot(
            source_status="parse_error",
            source_file=str(dtr_path),
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=("decision_trace_read_failed",),
            source_message=(
                "Decision trace not yet persisted. Need replay_dtr.jsonl or service decision log."
            ),
        )
    for line in lines[-max_entries:]:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        decision_state = str(payload.get("decision_state", ""))
        final_size = _float(payload.get("final_size"))
        selected = bool(decision_state == "executed" or (final_size is not None and final_size > 0))
        refusal_reason = str(payload.get("primary_reason", ""))
        if not refusal_reason:
            cause_chain = payload.get("cause_chain") or ()
            if isinstance(cause_chain, list) and cause_chain:
                refusal_reason = str(cause_chain[0])
        rows.append(
            DecisionTraceRow(
                timestamp=_to_iso(payload.get("timestamp")),
                pair=str(payload.get("pair", "")),
                engine=str(payload.get("engine_id", "")),
                raw_score=_float(payload.get("raw_score")),
                penalized_score=_float(payload.get("penalized_score")),
                final_score=_float(payload.get("final_score")),
                selected=selected,
                hard_blocked=bool(payload.get("hard_blocked", False)),
                refusal_reason=refusal_reason,
                expected_cost=_float(payload.get("expected_cost")),
                expected_ce=_float(payload.get("ce_expected")),
                final_size=final_size,
            )
        )
    reason_codes = list(stamp["reason_codes"])
    if skipped:
        reason_codes.append("decision_trace_corrupt_rows_skipped")
    return DecisionTraceSnapshot(
        source_status=stamp["source_status"],
        source_file=str(dtr_path),
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        entries=tuple(rows),
        source_message="" if rows else "Decision trace is empty.",
        skipped_corrupt_row_count=skipped,
    )


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["DecisionTraceRow", "DecisionTraceSnapshot", "read_decision_trace"]
