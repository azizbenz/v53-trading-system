"""Phase 2 adapter — HLZ Sharpe deflation guard.

Source: ``local_lab_calibration_methods_review.json`` produced by
``run_local_lab_analysis_bundle.py``. Carries the DSR (Deflated Sharpe Ratio)
floor, the trial count, and the stationarity / walk-forward gate states.
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


class MultipleTestingGuardSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    review_status: str = ""
    review_ready: bool = False

    record_count: int = 0
    executed_record_count: int = 0
    distinct_scope_count: int = 0
    timestamp_count: int = 0

    walk_forward_plan_status: str = ""
    walk_forward_plan_ready: bool = False
    stationarity_status: str = ""
    stationarity_ready: bool = False
    stationarity_pass: bool | None = None

    dsr_status: str = ""
    dsr_ready: bool = False
    dsr_pass: bool | None = None
    dsr_floor: float = 0.0
    dsr_trial_count: int = 0


def _find_latest_calibration_review(build_root: Path) -> Path | None:
    bundle = _find_latest_bundle(build_root)
    if bundle is None:
        return None
    candidate = bundle.parent.parent / "local_lab_calibration_methods_review.json"
    return candidate if candidate.is_file() else None


def read_multiple_testing_guard(build_root: Path) -> MultipleTestingGuardSnapshot:
    path = _find_latest_calibration_review(build_root)
    if path is None:
        return MultipleTestingGuardSnapshot(source_status="missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse calibration review %s: %s", path, exc)
        return MultipleTestingGuardSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return MultipleTestingGuardSnapshot(source_status="parse_error", source_path=str(path))
    return MultipleTestingGuardSnapshot(
        source_status="ok",
        source_path=str(path),
        review_status=str(payload.get("review_status", "")),
        review_ready=bool(payload.get("review_ready", False)),
        record_count=int(payload.get("record_count", 0) or 0),
        executed_record_count=int(payload.get("executed_record_count", 0) or 0),
        distinct_scope_count=int(payload.get("distinct_scope_count", 0) or 0),
        timestamp_count=int(payload.get("timestamp_count", 0) or 0),
        walk_forward_plan_status=str(payload.get("walk_forward_plan_status", "")),
        walk_forward_plan_ready=bool(payload.get("walk_forward_plan_ready", False)),
        stationarity_status=str(payload.get("stationarity_status", "")),
        stationarity_ready=bool(payload.get("stationarity_ready", False)),
        stationarity_pass=payload.get("stationarity_pass"),
        dsr_status=str(payload.get("dsr_status", "")),
        dsr_ready=bool(payload.get("dsr_ready", False)),
        dsr_pass=payload.get("dsr_pass"),
        dsr_floor=float(payload.get("dsr_floor", 0.0) or 0.0),
        dsr_trial_count=int(payload.get("dsr_trial_count", 0) or 0),
    )


__all__ = ["MultipleTestingGuardSnapshot", "read_multiple_testing_guard"]
