"""Phase 2 adapter — Capacity guard snapshot.

Source priority:
1. The freshest Build-9X bundle's ``capacity_snapshot`` block, when present.
2. Fallback: ``shadow_vps_service_observability_export.json`` samples.
3. Empty snapshot tagged ``missing`` otherwise.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cockpit.state_lab_review import _find_latest_bundle


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error"]


class CapacityGuardSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    queue_depth: int = 0
    queue_oldest_age_ms: int = 0
    worker_cpu_pct: float = 0.0
    worker_rss_mb: float = 0.0
    write_latency_ms: float = 0.0
    export_failures_total: int = 0
    log_loss_total: int = 0
    unprocessed_items_count: int = 0
    backlog_alert_threshold: int = 0
    backlog_protection_threshold: int = 0
    backlog_state: str = ""
    blocked: bool = False
    block_reasons: tuple[str, ...] = ()


def read_capacity_guard(
    *, build_root: Path, observability_export_path: Path
) -> CapacityGuardSnapshot:
    bundle_path = _find_latest_bundle(build_root)
    if bundle_path is not None:
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning("Cannot parse capacity bundle %s: %s", bundle_path, exc)
        else:
            snapshot = bundle.get("capacity_snapshot") if isinstance(bundle, dict) else None
            if isinstance(snapshot, dict):
                reasons = snapshot.get("block_reasons") or snapshot.get("blocking_reasons") or ()
                return CapacityGuardSnapshot(
                    source_status="ok",
                    source_path=str(bundle_path),
                    queue_depth=int(snapshot.get("queue_depth", 0) or 0),
                    queue_oldest_age_ms=int(snapshot.get("queue_oldest_age_ms", 0) or 0),
                    worker_cpu_pct=float(snapshot.get("worker_cpu_pct", 0.0) or 0.0),
                    worker_rss_mb=float(snapshot.get("worker_rss_mb", 0.0) or 0.0),
                    write_latency_ms=float(snapshot.get("write_latency_ms", 0.0) or 0.0),
                    export_failures_total=int(snapshot.get("export_failures_total", 0) or 0),
                    log_loss_total=int(snapshot.get("log_loss_total", 0) or 0),
                    unprocessed_items_count=int(snapshot.get("unprocessed_items_count", 0) or 0),
                    backlog_alert_threshold=int(snapshot.get("backlog_alert_threshold", 0) or 0),
                    backlog_protection_threshold=int(snapshot.get("backlog_protection_threshold", 0) or 0),
                    backlog_state=str(
                        snapshot.get("backlog_state")
                        or snapshot.get("backlog_status_label", "")
                    ),
                    blocked=bool(snapshot.get("blocked", False)),
                    block_reasons=tuple(str(r) for r in reasons),
                )

    if observability_export_path.is_file():
        try:
            export = json.loads(observability_export_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning(
                "Cannot parse observability export %s: %s",
                observability_export_path,
                exc,
            )
        else:
            samples = export.get("samples") if isinstance(export, dict) else None
            if isinstance(samples, list):
                values = {
                    str(item.get("metric", "")): item.get("value")
                    for item in samples
                    if isinstance(item, dict)
                }
                return CapacityGuardSnapshot(
                    source_status="ok",
                    source_path=str(observability_export_path),
                    queue_depth=int(values.get("queue_depth", 0) or 0),
                    queue_oldest_age_ms=int(values.get("queue_oldest_age_ms", 0) or 0),
                    worker_cpu_pct=float(values.get("worker_cpu_pct", 0.0) or 0.0),
                    worker_rss_mb=float(values.get("worker_rss_mb", 0.0) or 0.0),
                    backlog_state="normal",
                )
    return CapacityGuardSnapshot(source_status="missing")


__all__ = ["CapacityGuardSnapshot", "read_capacity_guard"]
