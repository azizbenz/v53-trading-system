"""Phase 2.5 adapter - read-only kill proof status."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


class KillProofSnapshot(OperationalSourceSnapshot):
    kill_switch_status: str = "NOT_PROVEN"
    pid_file_present: bool = False
    halt_flag_watcher_enabled: bool = False
    last_kill_test_at: str | None = None
    last_kill_latency_ms: float | None = None
    last_kill_result: str = ""
    evidence_file: str | None = None


def read_kill_proof(paths: CockpitPaths) -> KillProofSnapshot:
    """Never infer kill proof unless an explicit evidence file exists."""

    evidence_path = _find_evidence_file(paths.service_dir)
    if evidence_path is None:
        return KillProofSnapshot(
            source_status="not_yet_persisted",
            source_file=str(paths.service_dir),
            last_modified_at=None,
            age_seconds=None,
            reason_codes=("kill_proof_not_yet_persisted",),
            kill_switch_status="NOT_PROVEN",
            pid_file_present=paths.pid_file.is_file(),
            halt_flag_watcher_enabled=_halt_flag_watcher_enabled(paths.service_dir),
            evidence_file=None,
        )
    stamp = source_stamp(path=evidence_path, stale_after_seconds=86400.0)
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return KillProofSnapshot(
            source_status="parse_error",
            source_file=str(evidence_path),
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=("kill_proof_parse_failed",),
            kill_switch_status="NOT_PROVEN",
            pid_file_present=paths.pid_file.is_file(),
            halt_flag_watcher_enabled=_halt_flag_watcher_enabled(paths.service_dir),
            evidence_file=str(evidence_path),
        )
    if not isinstance(payload, dict):
        return KillProofSnapshot(
            source_status="parse_error",
            source_file=str(evidence_path),
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=("kill_proof_invalid_payload",),
            kill_switch_status="NOT_PROVEN",
            pid_file_present=paths.pid_file.is_file(),
            halt_flag_watcher_enabled=_halt_flag_watcher_enabled(paths.service_dir),
            evidence_file=str(evidence_path),
        )
    latency_ms = _float(payload.get("last_kill_latency_ms") or payload.get("latency_ms"))
    explicit_status = str(payload.get("kill_switch_status", "")).strip()
    if explicit_status:
        status = explicit_status
    elif latency_ms is not None and latency_ms < 1000.0:
        status = "PROVEN_SHADOW"
    else:
        status = "NOT_PROVEN"
    return KillProofSnapshot(
        source_status=stamp["source_status"],
        source_file=str(evidence_path),
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=stamp["reason_codes"],
        kill_switch_status=status,
        pid_file_present=paths.pid_file.is_file(),
        halt_flag_watcher_enabled=_halt_flag_watcher_enabled(paths.service_dir),
        last_kill_test_at=_string(payload.get("last_kill_test_at") or payload.get("tested_at")),
        last_kill_latency_ms=latency_ms,
        last_kill_result=_string(payload.get("last_kill_result") or payload.get("result")),
        evidence_file=str(evidence_path),
    )


def _find_evidence_file(service_dir: Path) -> Path | None:
    for candidate in (
        service_dir / "kill_switch.proof.json",
        service_dir / "kill_proof.json",
        service_dir / "shadow_kill_proof.json",
        service_dir / "halt_flag_kill_proof.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _halt_flag_watcher_enabled(service_dir: Path) -> bool:
    events_path = service_dir / "shadow_vps_service.events.jsonl"
    if not events_path.is_file():
        return False
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "HALT_FLAG_OBSERVED" in text or "halt_flag" in text.lower()


def _float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _string(value: object) -> str:
    return str(value) if value is not None else ""


__all__ = ["KillProofSnapshot", "read_kill_proof"]
