"""Phase 2.5 adapter - current run vs previous run, with sample-size restraint."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from cockpit.runtime_support import CockpitRuntimeSurfaces
from cockpit.state_freshness import (
    OperationalSourceSnapshot,
    latest_export_dir,
    nth_latest_export_dir,
    read_json_dict,
    source_stamp,
)

if TYPE_CHECKING:
    from cockpit.state import WarmupSummary


class ProofTransition(BaseModel, frozen=True):
    previous: str | float | int | None = None
    current: str | float | int | None = None
    delta: float | None = None
    changed: bool = False


class RunComparisonSnapshot(OperationalSourceSnapshot):
    status: str = "unknown"
    current_run_id: str = ""
    previous_run_id: str = ""
    sample_warning: str = ""
    eligible_transition: ProofTransition = ProofTransition()
    service_transition: ProofTransition = ProofTransition()
    engines_active_count_transition: ProofTransition = ProofTransition()
    ce_net_transition: ProofTransition = ProofTransition()
    exec_rate_transition: ProofTransition = ProofTransition()
    queue_completed_transition: ProofTransition = ProofTransition()
    blocking_reasons_changed: tuple[str, ...] = ()


def _read_metrics(path: Path | None) -> dict[str, object]:
    return read_json_dict(path) if path is not None else None  # type: ignore[return-value]


def _transition(previous: object, current: object) -> ProofTransition:
    delta = None
    try:
        if previous is not None and current is not None:
            delta = float(current) - float(previous)
    except (TypeError, ValueError):
        delta = None
    return ProofTransition(
        previous=previous,
        current=current,
        delta=delta,
        changed=previous != current,
    )


def read_run_comparison(
    auto_exports_root: Path,
    *,
    runtime: CockpitRuntimeSurfaces,
    warmup: WarmupSummary | None,
) -> RunComparisonSnapshot:
    """Compare the newest export day against the previous one without overclaiming."""

    current_dir = latest_export_dir(auto_exports_root)
    previous_dir = nth_latest_export_dir(auto_exports_root, index=1)
    latest_metrics_path = current_dir / "replay_metrics.json" if current_dir else None
    latest_stamp = source_stamp(path=latest_metrics_path, stale_after_seconds=300.0)
    if current_dir is None:
        return RunComparisonSnapshot(
            source_status="missing",
            source_file=None,
            last_modified_at=None,
            age_seconds=None,
            reason_codes=("run_history_missing",),
            status="insufficient_history",
        )
    current_metrics = _read_metrics(current_dir / "replay_metrics.json")
    current_bridge = _read_metrics(current_dir / "feature_bridge.json")
    current_manifest = _read_metrics(current_dir / "replay_run_manifest.json")
    if previous_dir is None:
        reason_codes = list(latest_stamp["reason_codes"])
        if current_metrics is not None and int(current_metrics.get("total_records", 0) or 0) < 30:
            reason_codes.append("SAMPLE_TOO_SMALL")
        return RunComparisonSnapshot(
            source_status=latest_stamp["source_status"],
            source_file=str(latest_stamp["source_file"]) if latest_stamp["source_file"] else None,
            last_modified_at=latest_stamp["last_modified_at"],
            age_seconds=latest_stamp["age_seconds"],
            reason_codes=tuple(dict.fromkeys(reason_codes)),
            status="insufficient_history",
            current_run_id=str((current_manifest or {}).get("run_id", current_dir.name)),
            sample_warning="SAMPLE_TOO_SMALL"
            if int((current_metrics or {}).get("total_records", 0) or 0) < 30
            else "",
        )
    previous_metrics = _read_metrics(previous_dir / "replay_metrics.json")
    previous_bridge = _read_metrics(previous_dir / "feature_bridge.json")
    previous_manifest = _read_metrics(previous_dir / "replay_run_manifest.json")
    current_records = int((current_metrics or {}).get("total_records", 0) or 0)
    sample_warning = "SAMPLE_TOO_SMALL" if current_records < 30 else ""
    current_engines = len(tuple((current_bridge or {}).get("engines") or ()))
    previous_engines = len(tuple((previous_bridge or {}).get("engines") or ()))
    current_reasons = tuple(str(reason) for reason in (warmup.blocking_reasons if warmup else ()))
    blocking_changed = tuple(current_reasons)
    return RunComparisonSnapshot(
        source_status=latest_stamp["source_status"],
        source_file=str(latest_stamp["source_file"]) if latest_stamp["source_file"] else None,
        last_modified_at=latest_stamp["last_modified_at"],
        age_seconds=latest_stamp["age_seconds"],
        reason_codes=tuple(
            dict.fromkeys(
                (
                    *tuple(latest_stamp["reason_codes"]),
                    *(("SAMPLE_TOO_SMALL",) if sample_warning else ()),
                )
            )
        ),
        status="ok",
        current_run_id=str((current_manifest or {}).get("run_id", current_dir.name)),
        previous_run_id=str((previous_manifest or {}).get("run_id", previous_dir.name)),
        sample_warning=sample_warning,
        eligible_transition=_transition(None, warmup.eligible_to_trade if warmup else None),
        service_transition=_transition(
            None,
            runtime.monitoring_payload.service_status if runtime.monitoring_payload else None,
        ),
        engines_active_count_transition=_transition(previous_engines, current_engines),
        ce_net_transition=_transition(
            (previous_metrics or {}).get("ce_net"),
            (current_metrics or {}).get("ce_net"),
        ),
        exec_rate_transition=_transition(
            _exec_rate(previous_metrics),
            _exec_rate(current_metrics),
        ),
        queue_completed_transition=_transition(
            None,
            runtime.queue_snapshot.completed_result_count
            if runtime.queue_snapshot is not None
            else None,
        ),
        blocking_reasons_changed=blocking_changed,
    )


def _exec_rate(payload: dict[str, object] | None) -> float | None:
    if not payload:
        return None
    total_records = int(payload.get("total_records", 0) or 0)
    if total_records <= 0:
        return 0.0
    return float(payload.get("executed_count", 0) or 0) / float(total_records)


__all__ = ["ProofTransition", "RunComparisonSnapshot", "read_run_comparison"]
