"""Phase 2.5 adapter - source freshness and shared read-only source stamps."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal

from pydantic import BaseModel, Field

try:
    import yaml
except Exception:  # pragma: no cover - yaml is optional at runtime
    yaml = None

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


_logger = logging.getLogger(__name__)

FreshnessStatus = Literal[
    "ok",
    "missing",
    "stale",
    "parse_error",
    "not_yet_persisted",
    "unknown",
]

_STATUS_PRIORITY: dict[FreshnessStatus, int] = {
    "parse_error": 5,
    "missing": 4,
    "stale": 3,
    "not_yet_persisted": 2,
    "unknown": 1,
    "ok": 0,
}


class OperationalSourceSnapshot(BaseModel, frozen=True):
    """Common source metadata required on every Phase 2.5 snapshot."""

    source_status: FreshnessStatus = "unknown"
    source_file: str | None = None
    last_modified_at: str | None = None
    age_seconds: float | None = None
    reason_codes: tuple[str, ...] = ()


class SourceFreshnessEntry(OperationalSourceSnapshot):
    """One important runtime source and its freshness status."""

    source_name: str = Field(..., min_length=1)
    path: str | None = None
    exists: bool = False
    status: FreshnessStatus = "unknown"


class SourceFreshnessSnapshot(OperationalSourceSnapshot):
    """Bounded operator-facing freshness scanner."""

    sources: tuple[SourceFreshnessEntry, ...] = ()
    ok_count: int = 0
    stale_count: int = 0
    missing_count: int = 0
    parse_error_count: int = 0


def _now() -> datetime:
    return datetime.now(tz=UTC)


def source_stamp(
    *,
    path: Path | None,
    stale_after_seconds: float | None = None,
    status_if_missing: FreshnessStatus = "missing",
    validator: Callable[[Path], tuple[bool, tuple[str, ...]]] | None = None,
) -> dict[str, object]:
    """Build the common source stamp for one file or directory."""

    if path is None:
        return {
            "source_status": status_if_missing,
            "source_file": None,
            "last_modified_at": None,
            "age_seconds": None,
            "reason_codes": ("source_path_not_configured",),
        }
    if not path.exists():
        return {
            "source_status": status_if_missing,
            "source_file": str(path),
            "last_modified_at": None,
            "age_seconds": None,
            "reason_codes": ("source_missing",),
        }
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        _logger.warning("Cannot stat source %s: %s", path, exc)
        return {
            "source_status": "parse_error",
            "source_file": str(path),
            "last_modified_at": None,
            "age_seconds": None,
            "reason_codes": ("source_stat_failed",),
        }
    modified_at = datetime.fromtimestamp(mtime, tz=UTC)
    age_seconds = max((_now() - modified_at).total_seconds(), 0.0)
    reason_codes: tuple[str, ...] = ()
    if validator is not None:
        valid, validator_reasons = validator(path)
        if not valid:
            return {
                "source_status": "parse_error",
                "source_file": str(path),
                "last_modified_at": modified_at.isoformat(),
                "age_seconds": age_seconds,
                "reason_codes": validator_reasons or ("source_parse_failed",),
            }
        reason_codes = validator_reasons
    status: FreshnessStatus = "ok"
    if stale_after_seconds is not None and age_seconds > stale_after_seconds:
        status = "stale"
        reason_codes = tuple((*reason_codes, "source_stale"))
    return {
        "source_status": status,
        "source_file": str(path),
        "last_modified_at": modified_at.isoformat(),
        "age_seconds": age_seconds,
        "reason_codes": reason_codes,
    }


def json_validator(path: Path) -> tuple[bool, tuple[str, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ("json_parse_failed",)
    return isinstance(payload, (dict, list)), ()


def yaml_validator(path: Path) -> tuple[bool, tuple[str, ...]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False, ("yaml_read_failed",)
    if yaml is None:
        return (bool(text.strip()), ())
    try:
        yaml.safe_load(text)
    except Exception:
        return False, ("yaml_parse_failed",)
    return True, ()


def directory_validator(path: Path) -> tuple[bool, tuple[str, ...]]:
    if not path.is_dir():
        return False, ("directory_expected",)
    try:
        tuple(path.iterdir())
    except OSError:
        return False, ("directory_scan_failed",)
    return True, ()


def _latest_child_mtime(path: Path) -> float | None:
    if not path.is_dir():
        return None
    latest: float | None = None
    try:
        for child in path.rglob("*"):
            if not child.exists():
                continue
            try:
                child_mtime = child.stat().st_mtime
            except OSError:
                continue
            latest = child_mtime if latest is None else max(latest, child_mtime)
    except OSError:
        return None
    return latest


def latest_export_dir(auto_exports_root: Path) -> Path | None:
    return nth_latest_export_dir(auto_exports_root, index=0)


def nth_latest_export_dir(auto_exports_root: Path, *, index: int) -> Path | None:
    if index < 0 or not auto_exports_root.is_dir():
        return None
    try:
        candidates = sorted(
            (directory for directory in auto_exports_root.iterdir() if directory.is_dir()),
            key=lambda directory: directory.name,
            reverse=True,
        )
    except OSError:
        return None
    return candidates[index] if index < len(candidates) else None


def latest_matching_file(root: Path, pattern: str) -> Path | None:
    if not root.is_dir():
        return None
    try:
        candidates = [path for path in root.rglob(pattern) if path.is_file()]
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: candidate.stat().st_mtime, reverse=True)
    return candidates[0]


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 64), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def read_json_dict(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _entry(
    *,
    source_name: str,
    path: Path | None,
    stale_after_seconds: float | None,
    validator: Callable[[Path], tuple[bool, tuple[str, ...]]] | None,
    status_if_missing: FreshnessStatus = "missing",
) -> SourceFreshnessEntry:
    mtime_override = _latest_child_mtime(path) if path is not None and path.is_dir() else None
    payload = source_stamp(
        path=path,
        stale_after_seconds=stale_after_seconds,
        status_if_missing=status_if_missing,
        validator=validator,
    )
    if mtime_override is not None and payload["source_status"] != "missing":
        modified_at = datetime.fromtimestamp(mtime_override, tz=UTC)
        payload["last_modified_at"] = modified_at.isoformat()
        payload["age_seconds"] = max((_now() - modified_at).total_seconds(), 0.0)
        if (
            stale_after_seconds is not None
            and payload["age_seconds"] is not None
            and float(payload["age_seconds"]) > stale_after_seconds
        ):
            payload["source_status"] = "stale"
            payload["reason_codes"] = tuple(
                (*tuple(payload["reason_codes"]), "source_stale")
            )
    status = payload["source_status"]
    return SourceFreshnessEntry(
        source_name=source_name,
        path=str(path) if path is not None else None,
        exists=bool(path is not None and path.exists()),
        status=status,
        **payload,
    )


def read_source_freshness(paths: CockpitPaths) -> SourceFreshnessSnapshot:
    """Scan the important Local IA Lab -> VPS runtime sources."""

    build_root = paths.build_root or paths.service_dir.parent.parent
    latest_export = latest_export_dir(paths.auto_exports_root)
    latest_replay = latest_export / "replay_metrics.json" if latest_export else None
    latest_feature_bridge = latest_export / "feature_bridge.json" if latest_export else None
    latest_lab_bundle = latest_matching_file(
        build_root,
        "meta_learning_review.bundle.json",
    )
    model_risk_path = paths.service_dir / "model_risk_register.snapshot.json"
    refusal_journal_path = paths.service_dir / "refusal_journal.snapshot.json"
    queue_root = paths.dashboard_command_queue_root
    entries = (
        _entry(
            source_name="warmup_summary",
            path=paths.warmup_summary,
            stale_after_seconds=300.0,
            validator=json_validator,
        ),
        _entry(
            source_name="service_state",
            path=paths.service_state,
            stale_after_seconds=60.0,
            validator=json_validator,
        ),
        _entry(
            source_name="replay_metrics",
            path=latest_replay,
            stale_after_seconds=300.0,
            validator=json_validator,
        ),
        _entry(
            source_name="feature_bridge",
            path=latest_feature_bridge,
            stale_after_seconds=300.0,
            validator=json_validator,
        ),
        _entry(
            source_name="lab_review_bundle",
            path=latest_lab_bundle,
            stale_after_seconds=86400.0,
            validator=json_validator,
        ),
        _entry(
            source_name="thresholds",
            path=paths.calibration_thresholds,
            stale_after_seconds=30.0 * 86400.0,
            validator=yaml_validator,
        ),
        _entry(
            source_name="command_queue",
            path=queue_root,
            stale_after_seconds=300.0,
            validator=directory_validator,
            status_if_missing="not_yet_persisted",
        ),
        _entry(
            source_name="model_risk_snapshot",
            path=model_risk_path,
            stale_after_seconds=300.0,
            validator=json_validator,
            status_if_missing="not_yet_persisted",
        ),
        _entry(
            source_name="refusal_journal_dump",
            path=refusal_journal_path,
            stale_after_seconds=300.0,
            validator=json_validator,
            status_if_missing="not_yet_persisted",
        ),
    )
    overall = worst_status(*(entry.status for entry in entries))
    primary = next((entry for entry in entries if entry.status != "ok"), entries[0])
    return SourceFreshnessSnapshot(
        source_status=overall,
        source_file=primary.source_file,
        last_modified_at=primary.last_modified_at,
        age_seconds=primary.age_seconds,
        reason_codes=primary.reason_codes,
        sources=entries,
        ok_count=sum(1 for entry in entries if entry.status == "ok"),
        stale_count=sum(1 for entry in entries if entry.status == "stale"),
        missing_count=sum(
            1 for entry in entries if entry.status in {"missing", "not_yet_persisted"}
        ),
        parse_error_count=sum(1 for entry in entries if entry.status == "parse_error"),
    )


def worst_status(*statuses: FreshnessStatus) -> FreshnessStatus:
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda status: _STATUS_PRIORITY.get(status, -1))


__all__ = [
    "FreshnessStatus",
    "OperationalSourceSnapshot",
    "SourceFreshnessEntry",
    "SourceFreshnessSnapshot",
    "directory_validator",
    "json_validator",
    "latest_export_dir",
    "latest_matching_file",
    "nth_latest_export_dir",
    "read_json_dict",
    "read_source_freshness",
    "sha256_file",
    "source_stamp",
    "worst_status",
    "yaml_validator",
]
