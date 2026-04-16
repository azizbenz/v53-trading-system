"""Sidecar IO helpers for governed LOCAL_REPLAY exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import ValidationError

from local_replay_runtime.replay_orchestrator_models import (
    ReplayChunkSessionSummary,
    ReplayOrchestratorRequest,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_session_config import ReplaySessionConfig
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_LoadedModelT = TypeVar("_LoadedModelT")


def _read_dtr_records(replay_dtr_path: Path) -> tuple[DTRRecord, ...]:
    records: list[DTRRecord] = []
    for line in replay_dtr_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(DTRRecord.model_validate(json.loads(stripped)))
    return tuple(records)


def _load_json_sidecar_with_backup(
    path: Path,
    *,
    label: str,
    parser: Callable[[str], _LoadedModelT],
) -> _LoadedModelT:
    try:
        return parser(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError, TypeError) as exc:
        backup = path.with_suffix(".corrupted")
        try:
            path.replace(backup)
        except OSError:
            pass
        raise ValueError(f"LOCAL_REPLAY {label} is corrupted: {path.name}") from exc


def _load_existing_resume_metadata(
    output_dir: Path,
) -> tuple[ReplaySessionConfig, ReplayRunManifest] | None:
    session_config_path = output_dir / "replay_session_config.json"
    replay_run_manifest_path = output_dir / "replay_run_manifest.json"
    if not session_config_path.exists() or not replay_run_manifest_path.exists():
        return None
    session_config = _load_json_sidecar_with_backup(
        session_config_path,
        label="resume metadata",
        parser=ReplaySessionConfig.model_validate_json,
    )
    replay_run_manifest = _load_json_sidecar_with_backup(
        replay_run_manifest_path,
        label="resume metadata",
        parser=ReplayRunManifest.model_validate_json,
    )
    return session_config, replay_run_manifest


def _validate_resume_request_against_existing_export(
    request: ReplayOrchestratorRequest,
    *,
    session_config: ReplaySessionConfig,
    replay_run_manifest: ReplayRunManifest,
) -> None:
    mismatches: list[str] = []
    expected_fields = (
        ("run_id", request.run_id, session_config.run_id),
        ("strategy_id", request.strategy_id, session_config.strategy_id),
        ("strategy_version", request.strategy_version, session_config.strategy_version),
        ("lineage_version", request.lineage_version, session_config.lineage_version),
        ("profile_scope", request.profile_scope.value, session_config.profile_scope.value),
        ("performance_mode", request.performance_mode, session_config.performance_mode),
        (
            "strategy_classification",
            request.strategy_classification.value,
            replay_run_manifest.strategy_classification.value,
        ),
        ("chunk_count", request.chunk_count, session_config.chunk_count),
    )
    for field_name, actual, expected in expected_fields:
        if actual != expected:
            mismatches.append(f"{field_name} expected {expected!r}, got {actual!r}")

    if not request.run_all_chunks and request.chunk_index != session_config.chunk_index:
        mismatches.append(
            f"chunk_index expected {session_config.chunk_index!r}, got {request.chunk_index!r}"
        )
    if request.input_kind is not None and request.input_kind != session_config.input_kind:
        mismatches.append(
            f"input_kind expected {session_config.input_kind!r}, got {request.input_kind!r}"
        )
    if mismatches:
        raise ValueError(
            "LOCAL_REPLAY resume request does not match the persisted export: "
            + "; ".join(mismatches)
        )


def _load_chunk_session_summary(output_dir: Path) -> ReplayChunkSessionSummary | None:
    chunk_session_path = output_dir / "replay_chunk_session.json"
    if not chunk_session_path.exists():
        return None
    return _load_json_sidecar_with_backup(
        chunk_session_path,
        label="chunk session metadata",
        parser=ReplayChunkSessionSummary.model_validate_json,
    )


__all__ = [
    "_load_chunk_session_summary",
    "_load_existing_resume_metadata",
    "_load_json_sidecar_with_backup",
    "_read_dtr_records",
    "_validate_resume_request_against_existing_export",
]
