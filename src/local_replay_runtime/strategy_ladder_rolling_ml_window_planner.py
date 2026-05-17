from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


DEFAULT_ROLLING_TRAIN_DAYS = 180
DEFAULT_ROLLING_VALIDATION_DAYS = 30
DEFAULT_ROLLING_FRESHNESS_DAYS = 30
DEFAULT_ROLLING_CHUNK_DAYS = 30

ROLLING_ML_WINDOW_PLAN_JSON_FILENAME = "rolling_ml_window_plan.json"
ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME = "rolling_ml_window_plan.md"
ROLLING_PLAN_READY = "ROLLING_PLAN_READY"
ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY = (
    "ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY"
)
CHUNK_READY = "CHUNK_READY"
CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY = "CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY"
CHUNK_BLOCKED_BY_ARTIFACT_FRESHNESS = "CHUNK_BLOCKED_BY_ARTIFACT_FRESHNESS"


def _parse_date(raw_value: str) -> date:
    value = (raw_value or "").strip().replace("Z", "+00:00")
    if "T" not in value and " " not in value:
        return date.fromisoformat(value)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_id_expected(
    *,
    chunk_index: int,
    backtest_start: date,
    backtest_end: date,
    train_start: date,
    train_end: date,
    validation_start: date,
    validation_end: date,
) -> str:
    return (
        "strategy_ladder_expected_edge"
        f".chunk{chunk_index:02d}"
        f".bt_{backtest_start.isoformat()}_{backtest_end.isoformat()}"
        f".train_{train_start.isoformat()}_{train_end.isoformat()}"
        f".val_{validation_start.isoformat()}_{validation_end.isoformat()}"
    )


class StrategyLadderRollingMlWindowChunk(BaseModel, frozen=True):
    chunk_index: int = Field(..., ge=1)
    backtest_chunk_start: str
    backtest_chunk_end: str
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    artifact_stale_after: str
    artifact_required: bool = True
    artifact_id_expected: str
    max_valid_backtest_end: str
    status: str = CHUNK_READY


class StrategyLadderRollingMlWindowPlan(BaseModel, frozen=True):
    schema_version: str = "strategy_ladder.rolling_ml_window_plan.v1"
    plan_id: str
    status: str
    timezone: str = "UTC"
    backtest_start_date: str
    backtest_end_date: str
    backtest_days: int = Field(..., ge=1)
    train_days: int = Field(default=DEFAULT_ROLLING_TRAIN_DAYS, ge=1)
    validation_days: int = Field(default=DEFAULT_ROLLING_VALIDATION_DAYS, ge=1)
    freshness_days: int = Field(default=DEFAULT_ROLLING_FRESHNESS_DAYS, ge=1)
    chunk_days: int = Field(default=DEFAULT_ROLLING_CHUNK_DAYS, ge=1)
    available_history_start_date: str | None = None
    required_artifact_count: int = Field(default=0, ge=0)
    ready_chunk_count: int = Field(default=0, ge=0)
    blocker_chunk_count: int = Field(default=0, ge=0)
    effective_chunk_days: int = Field(default=0, ge=1)
    chunks: tuple[StrategyLadderRollingMlWindowChunk, ...] = ()
    blocker_codes: tuple[str, ...] = ()
    json_ref: str | None = None
    markdown_ref: str | None = None


class StrategyLadderRollingMlWindowPlannerRequest(BaseModel, frozen=True):
    backtest_start_date: str = Field(..., min_length=1)
    backtest_days: int = Field(..., ge=1)
    train_days: int = Field(default=DEFAULT_ROLLING_TRAIN_DAYS, ge=1)
    validation_days: int = Field(default=DEFAULT_ROLLING_VALIDATION_DAYS, ge=1)
    freshness_days: int = Field(default=DEFAULT_ROLLING_FRESHNESS_DAYS, ge=1)
    chunk_days: int = Field(default=DEFAULT_ROLLING_CHUNK_DAYS, ge=1)
    timezone: str = "UTC"
    available_history_start_date: str | None = None


def build_strategy_ladder_rolling_ml_window_plan(
    request: StrategyLadderRollingMlWindowPlannerRequest,
) -> StrategyLadderRollingMlWindowPlan:
    backtest_start = _parse_date(request.backtest_start_date)
    backtest_end = backtest_start + timedelta(days=request.backtest_days - 1)
    available_history_start = (
        _parse_date(request.available_history_start_date)
        if request.available_history_start_date
        else None
    )
    effective_chunk_days = min(request.chunk_days, request.freshness_days)

    chunks: list[StrategyLadderRollingMlWindowChunk] = []
    cursor = backtest_start
    chunk_index = 1
    blocker_codes: list[str] = []

    while cursor <= backtest_end:
        chunk_end = min(
            cursor + timedelta(days=effective_chunk_days - 1),
            backtest_end,
        )
        validation_end = cursor - timedelta(days=1)
        validation_start = validation_end - timedelta(days=request.validation_days - 1)
        train_end = validation_start - timedelta(days=1)
        train_start = train_end - timedelta(days=request.train_days - 1)
        artifact_stale_after = validation_end + timedelta(days=request.freshness_days)
        max_valid_backtest_end = artifact_stale_after
        status = CHUNK_READY
        if chunk_end > artifact_stale_after:
            status = CHUNK_BLOCKED_BY_ARTIFACT_FRESHNESS
            blocker_codes.append(CHUNK_BLOCKED_BY_ARTIFACT_FRESHNESS)
        if available_history_start is not None and train_start < available_history_start:
            status = CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY
            blocker_codes.append(CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY)
        chunks.append(
            StrategyLadderRollingMlWindowChunk(
                chunk_index=chunk_index,
                backtest_chunk_start=cursor.isoformat(),
                backtest_chunk_end=chunk_end.isoformat(),
                train_start=train_start.isoformat(),
                train_end=train_end.isoformat(),
                validation_start=validation_start.isoformat(),
                validation_end=validation_end.isoformat(),
                artifact_stale_after=artifact_stale_after.isoformat(),
                artifact_required=True,
                artifact_id_expected=_artifact_id_expected(
                    chunk_index=chunk_index,
                    backtest_start=cursor,
                    backtest_end=chunk_end,
                    train_start=train_start,
                    train_end=train_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                ),
                max_valid_backtest_end=max_valid_backtest_end.isoformat(),
                status=status,
            )
        )
        cursor = chunk_end + timedelta(days=1)
        chunk_index += 1

    chunk_count = len(chunks)
    ready_chunk_count = sum(1 for chunk in chunks if chunk.status == CHUNK_READY)
    blocker_chunk_count = chunk_count - ready_chunk_count
    if blocker_chunk_count:
        status = ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY
        blocker_codes.append(ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY)
    elif chunk_count == 1:
        status = ROLLING_PLAN_READY
    else:
        status = f"ROLLING_PLAN_REQUIRES_{chunk_count}_ARTIFACTS"

    plan_payload = {
        "backtest_start_date": backtest_start.isoformat(),
        "backtest_end_date": backtest_end.isoformat(),
        "backtest_days": request.backtest_days,
        "train_days": request.train_days,
        "validation_days": request.validation_days,
        "freshness_days": request.freshness_days,
        "chunk_days": request.chunk_days,
        "effective_chunk_days": effective_chunk_days,
        "timezone": request.timezone,
        "available_history_start_date": (
            None if available_history_start is None else available_history_start.isoformat()
        ),
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }
    return StrategyLadderRollingMlWindowPlan(
        plan_id=f"rolling-ml-plan-{_stable_hash(plan_payload)[:16]}",
        status=status,
        timezone=request.timezone,
        backtest_start_date=backtest_start.isoformat(),
        backtest_end_date=backtest_end.isoformat(),
        backtest_days=request.backtest_days,
        train_days=request.train_days,
        validation_days=request.validation_days,
        freshness_days=request.freshness_days,
        chunk_days=request.chunk_days,
        available_history_start_date=(
            None if available_history_start is None else available_history_start.isoformat()
        ),
        required_artifact_count=chunk_count,
        ready_chunk_count=ready_chunk_count,
        blocker_chunk_count=blocker_chunk_count,
        effective_chunk_days=effective_chunk_days,
        chunks=tuple(chunks),
        blocker_codes=tuple(dict.fromkeys(blocker_codes)),
    )


def _plan_markdown(plan: StrategyLadderRollingMlWindowPlan) -> str:
    lines = [
        "# Rolling ML Window Plan",
        "",
        f"- plan_id: `{plan.plan_id}`",
        f"- status: `{plan.status}`",
        f"- timezone: `{plan.timezone}`",
        f"- backtest_window: `{plan.backtest_start_date}` -> `{plan.backtest_end_date}`",
        f"- backtest_days: `{plan.backtest_days}`",
        f"- train_days: `{plan.train_days}`",
        f"- validation_days: `{plan.validation_days}`",
        f"- freshness_days: `{plan.freshness_days}`",
        f"- chunk_days_requested: `{plan.chunk_days}`",
        f"- effective_chunk_days: `{plan.effective_chunk_days}`",
        f"- required_artifact_count: `{plan.required_artifact_count}`",
        "",
        "| Chunk | Backtest | Train | Validation | Stale after | Artifact ID | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for chunk in plan.chunks:
        lines.append(
            "| "
            f"{chunk.chunk_index} | "
            f"{chunk.backtest_chunk_start} -> {chunk.backtest_chunk_end} | "
            f"{chunk.train_start} -> {chunk.train_end} | "
            f"{chunk.validation_start} -> {chunk.validation_end} | "
            f"{chunk.artifact_stale_after} | "
            f"`{chunk.artifact_id_expected}` | "
            f"`{chunk.status}` |"
        )
    if plan.blocker_codes:
        lines.extend(
            [
                "",
                "## Blockers",
                "",
                *[f"- `{code}`" for code in plan.blocker_codes],
            ]
        )
    return "\n".join(lines) + "\n"


def write_strategy_ladder_rolling_ml_window_plan(
    output_dir: Path,
    request: StrategyLadderRollingMlWindowPlannerRequest,
) -> StrategyLadderRollingMlWindowPlan:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = build_strategy_ladder_rolling_ml_window_plan(request)
    json_path = output_dir / ROLLING_ML_WINDOW_PLAN_JSON_FILENAME
    markdown_path = output_dir / ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME
    plan_with_refs = plan.model_copy(
        update={
            "json_ref": str(json_path),
            "markdown_ref": str(markdown_path),
        }
    )
    atomic_write_json(json_path, plan_with_refs.model_dump(mode="json"), indent=2)
    markdown_path.write_text(_plan_markdown(plan_with_refs), encoding="utf-8")
    return plan_with_refs


def load_strategy_ladder_rolling_ml_window_plan(
    path_ref: str | Path,
) -> StrategyLadderRollingMlWindowPlan | None:
    path = Path(path_ref)
    if not path.is_file():
        return None
    try:
        return StrategyLadderRollingMlWindowPlan.model_validate_json(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, TypeError, ValueError):
        return None


__all__ = [
    "CHUNK_BLOCKED_BY_ARTIFACT_FRESHNESS",
    "CHUNK_BLOCKED_BY_MISSING_TRAIN_HISTORY",
    "CHUNK_READY",
    "DEFAULT_ROLLING_CHUNK_DAYS",
    "DEFAULT_ROLLING_FRESHNESS_DAYS",
    "DEFAULT_ROLLING_TRAIN_DAYS",
    "DEFAULT_ROLLING_VALIDATION_DAYS",
    "ROLLING_ML_WINDOW_PLAN_JSON_FILENAME",
    "ROLLING_ML_WINDOW_PLAN_MARKDOWN_FILENAME",
    "ROLLING_PLAN_BLOCKED_BY_INSUFFICIENT_HISTORY",
    "ROLLING_PLAN_READY",
    "StrategyLadderRollingMlWindowChunk",
    "StrategyLadderRollingMlWindowPlan",
    "StrategyLadderRollingMlWindowPlannerRequest",
    "build_strategy_ladder_rolling_ml_window_plan",
    "load_strategy_ladder_rolling_ml_window_plan",
    "write_strategy_ladder_rolling_ml_window_plan",
]
