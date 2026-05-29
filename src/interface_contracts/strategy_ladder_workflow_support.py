"""Workflow-parent helpers for multi-phase Strategy Ladder diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


PHASE_A1 = "PHASE_A1"
PHASE_A2 = "PHASE_A2"
PHASE_B1 = "PHASE_B1"
PHASE_B_ML = "PHASE_B_ML"
PHASE_B2 = "PHASE_B2"

PHASE_FOLDER_BY_ID: dict[str, str] = {
    PHASE_A1: "phase_a1_preview",
    PHASE_A2: "phase_a2_data_factory",
    PHASE_B1: "phase_b1_candidate_discovery",
    PHASE_B_ML: "phase_b_ml_training_label_factory",
    PHASE_B2: "phase_b2_detailed_replay",
}

PHASE_STATUS_PREVIEW_READY = "PHASE_A1_PREVIEW_READY"
PHASE_STATUS_PREVIEW_BLOCKED = "PHASE_A1_PREVIEW_BLOCKED"
PHASE_STATUS_PREVIEW_CONFIRMATION = "PHASE_A1_REQUIRES_BROAD_CONFIRMATION"
PHASE_STATUS_DATA_FACTORY_READY = "PHASE_A2_DATA_FACTORY_READY"
PHASE_STATUS_DATA_FACTORY_BLOCKED = "PHASE_A2_DATA_FACTORY_BLOCKED"
PHASE_STATUS_STORAGE_BLOCKED = "PHASE_A2_STORAGE_BLOCKED"
PHASE_STATUS_DISCOVERY_READY = "PHASE_B1_CANDIDATE_DISCOVERY_READY"
PHASE_STATUS_DISCOVERY_SAMPLED = "PHASE_B1_CANDIDATE_DISCOVERY_SAMPLE_CAPPED"
PHASE_STATUS_DISCOVERY_BLOCKED = "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
PHASE_STATUS_BML_READY = "PHASE_B_ML_LABEL_FACTORY_READY"
PHASE_STATUS_BML_BLOCKED = "PHASE_B_ML_LABEL_FACTORY_BLOCKED"
PHASE_STATUS_REPLAY_READY = "PHASE_B2_DETAILED_REPLAY_READY"
PHASE_STATUS_PROOF_BLOCKED = "PHASE_B2_BACKTEST_PROOF_BLOCKED"
PHASE_STATUS_PROMOTION_BLOCKED = "PHASE_B2_PROMOTION_BLOCKED_BY_FIDELITY"


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _payload_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class StrategyLadderWorkflowPhaseRecord(BaseModel, frozen=True):
    workflow_run_id: str = Field(..., min_length=1)
    phase_id: str = Field(..., min_length=1)
    phase_run_id: str = Field(..., min_length=1)
    phase_folder: str = Field(..., min_length=1)
    phase_output_root: str = Field(..., min_length=1)
    parent_workflow_ref: str = ""
    job_id: str = ""
    request_hash: str = ""
    phase_status: str = "PHASE_NOT_STARTED"
    blocker_codes: tuple[str, ...] = ()
    error_code: str = ""
    stderr_ref: str = ""
    consumed_artifact_refs: dict[str, str] = Field(default_factory=dict)
    produced_artifact_refs: dict[str, str] = Field(default_factory=dict)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    phase_started_at: str = ""
    phase_completed_at: str = ""


class StrategyLadderWorkflowManifest(BaseModel, frozen=True):
    schema_version: str = Field(default="v1", min_length=1)
    workflow_run_id: str = Field(..., min_length=1)
    workflow_root: str = Field(..., min_length=1)
    request_hash: str = ""
    phase_id: str = ""
    pairs: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    ml_mode: str = "ML_MODE_OFF"
    candidate_discovery_mode: str = "SAMPLE_CAPPED_DEBUG"
    engine_native_sample_size: int = Field(default=10, ge=0)
    b1_5_policy_mode: str = "conservative_hard_only"
    preselected_only: bool = True
    diagnostic_full_replay: bool = False
    engine_count: int = Field(default=4, ge=0)
    allow_broad_run: bool = False
    small_scope_enabled: bool = True
    full_scan_enabled: bool = False
    no_full_scan_enabled: bool = True
    silver_storage_mode_requested: str = "jsonl_debug"
    silver_storage_mode_effective: str = "jsonl_debug"
    current_phase_id: str = ""
    phase_sequence: tuple[str, ...] = ()
    phases: dict[str, StrategyLadderWorkflowPhaseRecord] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    artifact_hash: str = ""


def workflow_manifest_path(workflow_root: Path) -> Path:
    return workflow_root / "workflow_manifest.json"


def workflow_phase_dirname(phase_id: str) -> str:
    return PHASE_FOLDER_BY_ID.get(phase_id, phase_id.lower())


def workflow_phase_root(workflow_root: Path, phase_id: str) -> Path:
    return workflow_root / workflow_phase_dirname(phase_id)


def write_workflow_manifest(
    workflow_root: Path,
    manifest: StrategyLadderWorkflowManifest,
) -> Path:
    workflow_root.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump(mode="json")
    payload["updated_at"] = _utc_now_iso()
    payload["artifact_hash"] = _payload_hash(payload)
    atomic_write_json(workflow_manifest_path(workflow_root), payload, indent=2)
    return workflow_manifest_path(workflow_root)


def read_workflow_manifest(
    workflow_root: Path,
) -> StrategyLadderWorkflowManifest | None:
    path = workflow_manifest_path(workflow_root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return StrategyLadderWorkflowManifest.model_validate(payload)
    except ValueError:
        return None


def ensure_workflow_manifest(
    *,
    workflow_root: Path,
    workflow_run_id: str,
    request_hash: str,
    phase_id: str,
    pairs: tuple[str, ...],
    start: str,
    end: str,
    ml_mode: str,
    candidate_discovery_mode: str,
    engine_native_sample_size: int,
    b1_5_policy_mode: str = "conservative_hard_only",
    preselected_only: bool = True,
    diagnostic_full_replay: bool = False,
    engine_count: int,
    allow_broad_run: bool,
    small_scope_enabled: bool,
    full_scan_enabled: bool,
    no_full_scan_enabled: bool,
    silver_storage_mode_requested: str,
    silver_storage_mode_effective: str,
) -> StrategyLadderWorkflowManifest:
    existing = read_workflow_manifest(workflow_root)
    if existing is not None:
        merged_phase_sequence = tuple(
            dict.fromkeys((*existing.phase_sequence, phase_id))
        )
        manifest = existing.model_copy(
            update={
                "request_hash": request_hash,
                "phase_id": phase_id,
                "pairs": pairs,
                "start": start,
                "end": end,
                "ml_mode": ml_mode,
                "candidate_discovery_mode": candidate_discovery_mode,
                "engine_native_sample_size": int(engine_native_sample_size),
                "b1_5_policy_mode": b1_5_policy_mode,
                "preselected_only": bool(
                    preselected_only and not diagnostic_full_replay
                ),
                "diagnostic_full_replay": bool(diagnostic_full_replay),
                "engine_count": int(engine_count),
                "allow_broad_run": allow_broad_run,
                "small_scope_enabled": small_scope_enabled,
                "full_scan_enabled": full_scan_enabled,
                "no_full_scan_enabled": no_full_scan_enabled,
                "silver_storage_mode_requested": silver_storage_mode_requested,
                "silver_storage_mode_effective": silver_storage_mode_effective,
                "current_phase_id": phase_id,
                "phase_sequence": merged_phase_sequence,
            }
        )
    else:
        manifest = StrategyLadderWorkflowManifest(
            workflow_run_id=workflow_run_id,
            workflow_root=str(workflow_root.resolve()),
            request_hash=request_hash,
            phase_id=phase_id,
            pairs=pairs,
            start=start,
            end=end,
            ml_mode=ml_mode,
            candidate_discovery_mode=candidate_discovery_mode,
            engine_native_sample_size=engine_native_sample_size,
            b1_5_policy_mode=b1_5_policy_mode,
            preselected_only=bool(preselected_only and not diagnostic_full_replay),
            diagnostic_full_replay=bool(diagnostic_full_replay),
            engine_count=engine_count,
            allow_broad_run=allow_broad_run,
            small_scope_enabled=small_scope_enabled,
            full_scan_enabled=full_scan_enabled,
            no_full_scan_enabled=no_full_scan_enabled,
            silver_storage_mode_requested=silver_storage_mode_requested,
            silver_storage_mode_effective=silver_storage_mode_effective,
            current_phase_id=phase_id,
            phase_sequence=(phase_id,) if phase_id else (),
            created_at=_utc_now_iso(),
            updated_at=_utc_now_iso(),
        )
    write_workflow_manifest(workflow_root, manifest)
    return manifest


def upsert_workflow_phase(
    *,
    workflow_root: Path,
    workflow_run_id: str,
    phase_id: str,
    phase_run_id: str,
    phase_output_root: Path,
    parent_workflow_ref: str,
    job_id: str = "",
    request_hash: str = "",
    phase_status: str,
    blocker_codes: tuple[str, ...] | None = None,
    error_code: str | None = None,
    stderr_ref: str | None = None,
    consumed_artifact_refs: dict[str, str] | None = None,
    produced_artifact_refs: dict[str, str] | None = None,
    artifact_hashes: dict[str, str] | None = None,
    phase_started_at: str | None = None,
    phase_completed_at: str | None = None,
) -> StrategyLadderWorkflowManifest:
    manifest = read_workflow_manifest(workflow_root)
    if manifest is None:
        manifest = ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id=workflow_run_id,
            request_hash=request_hash,
            phase_id=phase_id,
            pairs=(),
            start="",
            end="",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
            engine_native_sample_size=10,
            b1_5_policy_mode="conservative_hard_only",
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=True,
            full_scan_enabled=False,
            no_full_scan_enabled=True,
            silver_storage_mode_requested="jsonl_debug",
            silver_storage_mode_effective="jsonl_debug",
        )
    phases = dict(manifest.phases)
    previous = phases.get(phase_id)
    phase_record = StrategyLadderWorkflowPhaseRecord(
        workflow_run_id=workflow_run_id,
        phase_id=phase_id,
        phase_run_id=phase_run_id,
        phase_folder=workflow_phase_dirname(phase_id),
        phase_output_root=str(phase_output_root.resolve()),
        parent_workflow_ref=parent_workflow_ref,
        job_id=job_id or (previous.job_id if previous is not None else ""),
        request_hash=request_hash or (previous.request_hash if previous is not None else ""),
        phase_status=phase_status,
        blocker_codes=(
            tuple(blocker_codes)
            if blocker_codes is not None
            else (previous.blocker_codes if previous is not None else ())
        ),
        error_code=(
            error_code
            if error_code is not None
            else (previous.error_code if previous is not None else "")
        ),
        stderr_ref=(
            stderr_ref
            if stderr_ref is not None
            else (previous.stderr_ref if previous is not None else "")
        ),
        consumed_artifact_refs=consumed_artifact_refs if consumed_artifact_refs is not None else (
            previous.consumed_artifact_refs if previous is not None else {}
        ),
        produced_artifact_refs=produced_artifact_refs if produced_artifact_refs is not None else (
            previous.produced_artifact_refs if previous is not None else {}
        ),
        artifact_hashes=artifact_hashes if artifact_hashes is not None else (
            previous.artifact_hashes if previous is not None else {}
        ),
        phase_started_at=phase_started_at if phase_started_at is not None else (
            previous.phase_started_at if previous is not None else _utc_now_iso()
        ),
        phase_completed_at=phase_completed_at if phase_completed_at is not None else (
            previous.phase_completed_at if previous is not None else ""
        ),
    )
    phases[phase_id] = phase_record
    updated = manifest.model_copy(
        update={
            "current_phase_id": phase_id,
            "phase_sequence": tuple(dict.fromkeys((*manifest.phase_sequence, phase_id))),
            "phases": phases,
        }
    )
    write_workflow_manifest(workflow_root, updated)
    return updated


__all__ = [
    "PHASE_A1",
    "PHASE_A2",
    "PHASE_B1",
    "PHASE_B_ML",
    "PHASE_B2",
    "PHASE_STATUS_BML_BLOCKED",
    "PHASE_STATUS_BML_READY",
    "PHASE_FOLDER_BY_ID",
    "PHASE_STATUS_DATA_FACTORY_BLOCKED",
    "PHASE_STATUS_DATA_FACTORY_READY",
    "PHASE_STATUS_DISCOVERY_BLOCKED",
    "PHASE_STATUS_DISCOVERY_READY",
    "PHASE_STATUS_DISCOVERY_SAMPLED",
    "PHASE_STATUS_PREVIEW_BLOCKED",
    "PHASE_STATUS_PREVIEW_CONFIRMATION",
    "PHASE_STATUS_PREVIEW_READY",
    "PHASE_STATUS_PROOF_BLOCKED",
    "PHASE_STATUS_PROMOTION_BLOCKED",
    "PHASE_STATUS_REPLAY_READY",
    "PHASE_STATUS_STORAGE_BLOCKED",
    "StrategyLadderWorkflowManifest",
    "StrategyLadderWorkflowPhaseRecord",
    "ensure_workflow_manifest",
    "read_workflow_manifest",
    "upsert_workflow_phase",
    "workflow_manifest_path",
    "workflow_phase_dirname",
    "workflow_phase_root",
    "write_workflow_manifest",
]
