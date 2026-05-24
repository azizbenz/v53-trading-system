"""Manifest and date-overlap contract for governed ML training sources."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


TRAINING_SOURCE_CONTRACT_REPORT_FILENAME = "training_source_contract_report.json"
ML_TRAIN_EVAL_OVERLAP_REPORT_FILENAME = "ml_train_eval_overlap_report.json"

ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED = "ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED"
TRAINING_SOURCE_CONTRACT_OK = "TRAINING_SOURCE_CONTRACT_OK"
MISSING_MANIFEST_WARNING = "MISSING_MANIFEST_WARNING"
DATE_PARSE_FAILED = "DATE_PARSE_FAILED"
TRAIN_EVAL_OVERLAP_BLOCKED = "TRAIN_EVAL_OVERLAP_BLOCKED"
BACKTEST_START_TOO_EARLY = "BACKTEST_START_TOO_EARLY"
DATASET_ROLE_INVALID = "DATASET_ROLE_INVALID"


class TrainingSourceManifest(BaseModel, frozen=True):
    schema_version: str = "training_source.manifest.v1"
    dataset_role: str = "ML_TRAINING_SOURCE"
    source_type: str = ""
    dataset_name: str = ""
    train_start: str = ""
    train_end: str = ""
    validation_start: str = ""
    validation_end: str = ""
    allowed_backtest_start_after: str = ""
    forbidden_eval_overlap: bool = True
    feature_grounding_registry_version: str = "v1"
    notes: str = ""


class TrainingSourceContractReport(BaseModel, frozen=True):
    schema_version: str = "training_source.contract_report.v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    status: str = TRAINING_SOURCE_CONTRACT_OK
    train_start: str = ""
    train_end: str = ""
    validation_start: str = ""
    validation_end: str = ""
    backtest_start: str = ""
    backtest_end: str = ""
    manifest_path: str = ""
    manifest_status: str = MISSING_MANIFEST_WARNING
    overlap_status: str = "TRAIN_EVAL_SPLIT_NOT_PROVEN"
    source_type: str = ""
    dataset_role: str = ""
    allowed_backtest_start_after: str = ""
    forbidden_eval_overlap: bool = True
    blocker_reason: str = ""
    blocker_reasons: tuple[str, ...] = ()


def _parse_date(raw_value: str) -> date | None:
    value = (raw_value or "").strip().replace("Z", "+00:00")
    if not value:
        return None
    try:
        if "T" not in value and " " not in value:
            return date.fromisoformat(value)
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


def resolve_training_source_manifest_path(root_or_path: Path | None) -> Path | None:
    if root_or_path is None:
        return None
    candidate = Path(root_or_path)
    if candidate.is_file():
        return candidate
    return candidate / "manifest.json"


def load_training_source_manifest(
    root_or_path: Path | None,
) -> tuple[TrainingSourceManifest | None, Path | None, str]:
    manifest_path = resolve_training_source_manifest_path(root_or_path)
    if manifest_path is None or not manifest_path.is_file():
        return None, manifest_path, MISSING_MANIFEST_WARNING
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            return None, manifest_path, DATE_PARSE_FAILED
        return TrainingSourceManifest.model_validate(payload), manifest_path, "MANIFEST_OK"
    except (OSError, TypeError, ValueError):
        return None, manifest_path, DATE_PARSE_FAILED


def _first_non_empty(*values: str) -> str:
    for value in values:
        cleaned = (value or "").strip()
        if cleaned:
            return cleaned
    return ""


def build_training_source_contract_report(
    *,
    manifest_root_or_path: Path | None,
    source_type: str = "",
    train_start: str = "",
    train_end: str = "",
    validation_start: str = "",
    validation_end: str = "",
    backtest_start: str = "",
    backtest_end: str = "",
) -> TrainingSourceContractReport:
    manifest, manifest_path, manifest_status = load_training_source_manifest(
        manifest_root_or_path
    )
    resolved_train_start = _first_non_empty(train_start, "" if manifest is None else manifest.train_start)
    resolved_train_end = _first_non_empty(train_end, "" if manifest is None else manifest.train_end)
    resolved_validation_start = _first_non_empty(
        validation_start,
        "" if manifest is None else manifest.validation_start,
    )
    resolved_validation_end = _first_non_empty(
        validation_end,
        "" if manifest is None else manifest.validation_end,
    )
    resolved_allowed_start = "" if manifest is None else manifest.allowed_backtest_start_after
    resolved_source_type = _first_non_empty(
        source_type,
        "" if manifest is None else manifest.source_type,
    )
    resolved_dataset_role = "" if manifest is None else manifest.dataset_role
    forbidden_eval_overlap = True if manifest is None else bool(manifest.forbidden_eval_overlap)

    blockers: list[str] = []
    manifest_blocking_status = ""
    if manifest is not None and resolved_dataset_role != "ML_TRAINING_SOURCE":
        manifest_blocking_status = DATASET_ROLE_INVALID
        blockers.append(DATASET_ROLE_INVALID)

    parsed_train_end = _parse_date(resolved_train_end)
    parsed_validation_end = _parse_date(resolved_validation_end)
    parsed_backtest_start = _parse_date(backtest_start)
    parsed_allowed_start = _parse_date(resolved_allowed_start)

    date_values_to_check = (
        resolved_train_end,
        resolved_validation_end,
        backtest_start,
        resolved_allowed_start,
    )
    non_empty_date_values = tuple(value for value in date_values_to_check if value)
    parsed_values = (
        parsed_train_end,
        parsed_validation_end,
        parsed_backtest_start,
        parsed_allowed_start,
    )
    if non_empty_date_values and any(
        value is None for raw, value in zip(date_values_to_check, parsed_values) if raw
    ):
        blockers.append(DATE_PARSE_FAILED)

    overlap_status = "TRAIN_EVAL_SPLIT_NOT_PROVEN"
    if parsed_backtest_start is not None:
        overlap_blocked = False
        if parsed_train_end is not None and parsed_train_end >= parsed_backtest_start:
            overlap_blocked = True
        if (
            parsed_validation_end is not None
            and parsed_validation_end >= parsed_backtest_start
        ):
            overlap_blocked = True
        if overlap_blocked and forbidden_eval_overlap:
            overlap_status = TRAIN_EVAL_OVERLAP_BLOCKED
            blockers.append(ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED)
        elif parsed_allowed_start is not None and parsed_backtest_start < parsed_allowed_start:
            overlap_status = BACKTEST_START_TOO_EARLY
            blockers.append(BACKTEST_START_TOO_EARLY)
        else:
            overlap_status = TRAINING_SOURCE_CONTRACT_OK

    unique_blockers = tuple(dict.fromkeys(blockers))
    status = (
        manifest_blocking_status
        or (
            TRAIN_EVAL_OVERLAP_BLOCKED
            if ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED in unique_blockers
            else (
                BACKTEST_START_TOO_EARLY
                if BACKTEST_START_TOO_EARLY in unique_blockers
                else (DATE_PARSE_FAILED if DATE_PARSE_FAILED in unique_blockers else TRAINING_SOURCE_CONTRACT_OK)
            )
        )
    )
    if (
        manifest_status == MISSING_MANIFEST_WARNING
        and not unique_blockers
        and overlap_status != TRAINING_SOURCE_CONTRACT_OK
    ):
        status = MISSING_MANIFEST_WARNING

    return TrainingSourceContractReport(
        status=status,
        train_start=resolved_train_start,
        train_end=resolved_train_end,
        validation_start=resolved_validation_start,
        validation_end=resolved_validation_end,
        backtest_start=backtest_start,
        backtest_end=backtest_end,
        manifest_path="" if manifest_path is None else str(manifest_path),
        manifest_status=manifest_status,
        overlap_status=overlap_status,
        source_type=resolved_source_type,
        dataset_role=resolved_dataset_role,
        allowed_backtest_start_after=resolved_allowed_start,
        forbidden_eval_overlap=forbidden_eval_overlap,
        blocker_reason=",".join(unique_blockers),
        blocker_reasons=unique_blockers,
    )


def write_training_source_contract_report(
    path: Path,
    report: TrainingSourceContractReport,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, report.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "BACKTEST_START_TOO_EARLY",
    "DATASET_ROLE_INVALID",
    "DATE_PARSE_FAILED",
    "MISSING_MANIFEST_WARNING",
    "ML_TRAIN_EVAL_OVERLAP_BLOCKED",
    "ML_TRAIN_EVAL_WINDOW_OVERLAP_BLOCKED",
    "TRAINING_SOURCE_CONTRACT_OK",
    "TRAINING_SOURCE_CONTRACT_REPORT_FILENAME",
    "TRAIN_EVAL_OVERLAP_BLOCKED",
    "TrainingSourceContractReport",
    "TrainingSourceManifest",
    "build_training_source_contract_report",
    "load_training_source_manifest",
    "resolve_training_source_manifest_path",
    "write_training_source_contract_report",
]
