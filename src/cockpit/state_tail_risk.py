"""Phase 2 adapter — Taleb tail-risk breakers from ``local_lab_tail_risk_review.json``.

This adapter doubles as the cockpit's "Refusal / Tail-Risk" section. The
canonical V5.3 refusal journal is not persisted to disk yet (Phase 2.1 follow-up
will wire it). Until then we surface the closest equivalent: the POT-GPD
tail-risk breakers (THR-R01/R02/R03) emitted by the Local IA Lab analysis.
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


class TailRiskBreaker(BaseModel, frozen=True):
    threshold_id: str
    period_kind: str = ""
    review_status: str = ""
    fit_ready: bool = False
    period_count: int = 0
    positive_loss_period_count: int = 0
    exceedance_count: int = 0
    var_estimate: float | None = None
    hard_cap_satisfied: bool | None = None
    hard_cap_binding: bool | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


class TailRiskSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    review_status: str = ""
    review_ready: bool = False
    breaker_count: int = 0
    ready_breaker_count: int = 0
    partial_breaker_count: int = 0
    blocked_breaker_count: int = 0
    breakers: tuple[TailRiskBreaker, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def _find_latest_tail_risk(build_root: Path) -> Path | None:
    bundle = _find_latest_bundle(build_root)
    if bundle is None:
        return None
    candidate = bundle.parent.parent / "local_lab_tail_risk_review.json"
    return candidate if candidate.is_file() else None


def read_tail_risk(build_root: Path) -> TailRiskSnapshot:
    path = _find_latest_tail_risk(build_root)
    if path is None:
        return TailRiskSnapshot(source_status="missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse tail risk review %s: %s", path, exc)
        return TailRiskSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return TailRiskSnapshot(source_status="parse_error", source_path=str(path))

    breakers_raw = payload.get("breakers") or ()
    breakers = tuple(
        TailRiskBreaker(
            threshold_id=str(b.get("threshold_id", "")),
            period_kind=str(b.get("period_kind", "")),
            review_status=str(b.get("review_status", "")),
            fit_ready=bool(b.get("fit_ready", False)),
            period_count=int(b.get("period_count", 0) or 0),
            positive_loss_period_count=int(b.get("positive_loss_period_count", 0) or 0),
            exceedance_count=int(b.get("exceedance_count", 0) or 0),
            var_estimate=_optional_float(b.get("var_estimate")),
            hard_cap_satisfied=b.get("hard_cap_satisfied"),
            hard_cap_binding=b.get("hard_cap_binding"),
            blocking_reasons=tuple(str(r) for r in b.get("blocking_reasons") or ()),
            caution_flags=tuple(str(f) for f in b.get("caution_flags") or ()),
        )
        for b in breakers_raw
        if isinstance(b, dict)
    )
    return TailRiskSnapshot(
        source_status="ok",
        source_path=str(path),
        review_status=str(payload.get("review_status", "")),
        review_ready=bool(payload.get("review_ready", False)),
        breaker_count=int(payload.get("breaker_count", 0) or 0),
        ready_breaker_count=int(payload.get("ready_breaker_count", 0) or 0),
        partial_breaker_count=int(payload.get("partial_breaker_count", 0) or 0),
        blocked_breaker_count=int(payload.get("blocked_breaker_count", 0) or 0),
        breakers=breakers,
        blocking_reasons=tuple(str(r) for r in payload.get("blocking_reasons") or ()),
        caution_flags=tuple(str(f) for f in payload.get("caution_flags") or ()),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["TailRiskBreaker", "TailRiskSnapshot", "read_tail_risk"]
