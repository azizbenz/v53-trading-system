"""Phase 2 adapter — IA Lab Build-9X review bundle.

Reads ``meta_learning_review.bundle.json`` produced by
``run_local_lab_analysis_bundle.py``. Real schema observed 2026-04-26 has
top-level keys: correlation_id, diagnostics, mistake_classes, breakdown_report,
checklist, hypotheses, candidates, replay_bundles, memory_record, review_export,
capacity_snapshot, review_decisions, archive_eligibility, lifecycle_transitions,
merge_gate_report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error"]


class MergeGate(BaseModel, frozen=True):
    gate_name: str
    passed: bool
    summary: str = ""
    blocking_reasons: tuple[str, ...] = ()


class CandidateRow(BaseModel, frozen=True):
    candidate_id: str
    stage: str = ""
    tests_pending: int = 0


class HypothesisRow(BaseModel, frozen=True):
    hypothesis_id: str
    strength: str = ""
    stage: str = ""


class LifecycleTransition(BaseModel, frozen=True):
    target: str
    from_state: str
    to_state: str
    actor: str = ""


class LabReviewSummary(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    correlation_id: str = ""
    summary: str = ""
    mistake_classes: tuple[str, ...] = ()
    candidates: tuple[CandidateRow, ...] = ()
    hypotheses: tuple[HypothesisRow, ...] = ()
    merge_gates: tuple[MergeGate, ...] = ()
    merge_gates_all_passed: bool = False
    lifecycle_transitions: tuple[LifecycleTransition, ...] = ()
    review_decisions_count: int = 0


def _find_latest_bundle(root: Path) -> Path | None:
    """Search ``build/local_lab_analysis_*/post_trade_review/`` for the freshest bundle."""

    if not root.is_dir():
        return None
    candidates: list[Path] = []
    try:
        for entry in root.iterdir():
            if not entry.is_dir() or not entry.name.startswith("local_lab_analysis"):
                continue
            bundle = entry / "post_trade_review" / "meta_learning_review.bundle.json"
            if bundle.is_file():
                candidates.append(bundle)
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def read_lab_review(build_root: Path) -> LabReviewSummary:
    path = _find_latest_bundle(build_root)
    if path is None:
        return LabReviewSummary(source_status="missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse lab review bundle %s: %s", path, exc)
        return LabReviewSummary(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return LabReviewSummary(source_status="parse_error", source_path=str(path))

    breakdown = payload.get("breakdown_report") or {}
    summary_text = ""
    if isinstance(breakdown, dict):
        summary_text = str(breakdown.get("summary", ""))
    if not summary_text:
        review_export = payload.get("review_export") or {}
        if isinstance(review_export, dict):
            summary_text = str(review_export.get("summary", ""))

    candidates_raw = payload.get("candidates") or ()
    candidates = tuple(
        CandidateRow(
            candidate_id=str(c.get("candidate_id") or c.get("id", "")),
            stage=str(c.get("stage", "")),
            tests_pending=int(c.get("tests_pending", 0) or 0),
        )
        for c in candidates_raw
        if isinstance(c, dict)
    )

    hypotheses_raw = payload.get("hypotheses") or ()
    hypotheses = tuple(
        HypothesisRow(
            hypothesis_id=str(h.get("hypothesis_id") or h.get("id", "")),
            strength=str(h.get("strength", "")),
            stage=str(h.get("stage", "")),
        )
        for h in hypotheses_raw
        if isinstance(h, dict)
    )

    gate_report = payload.get("merge_gate_report") or {}
    gates_raw = gate_report.get("gates", []) if isinstance(gate_report, dict) else []
    gates = tuple(
        MergeGate(
            gate_name=str(g.get("gate_name", "")),
            passed=bool(g.get("passed", False)),
            summary=str(g.get("summary", "")),
            blocking_reasons=tuple(str(r) for r in g.get("blocking_reasons") or ()),
        )
        for g in gates_raw
        if isinstance(g, dict)
    )
    all_passed = bool(gate_report.get("all_passed", False)) if isinstance(gate_report, dict) else False

    transitions_raw = payload.get("lifecycle_transitions") or ()
    transitions = tuple(
        LifecycleTransition(
            target=str(t.get("target") or t.get("entity", "")),
            from_state=str(t.get("from_state") or t.get("from", "")),
            to_state=str(t.get("to_state") or t.get("to", "")),
            actor=str(t.get("actor", "")),
        )
        for t in transitions_raw
        if isinstance(t, dict)
    )

    review_decisions = payload.get("review_decisions") or ()
    decisions_count = len(review_decisions) if isinstance(review_decisions, list) else 0

    return LabReviewSummary(
        source_status="ok",
        source_path=str(path),
        correlation_id=str(payload.get("correlation_id", "")),
        summary=summary_text,
        mistake_classes=tuple(str(m) for m in payload.get("mistake_classes") or ()),
        candidates=candidates,
        hypotheses=hypotheses,
        merge_gates=gates,
        merge_gates_all_passed=all_passed,
        lifecycle_transitions=transitions,
        review_decisions_count=decisions_count,
    )


__all__ = [
    "CandidateRow",
    "HypothesisRow",
    "LabReviewSummary",
    "LifecycleTransition",
    "MergeGate",
    "read_lab_review",
]
