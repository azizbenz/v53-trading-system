"""Phase 2 adapter — Carver sizing chain from ``replay_dtr.jsonl``.

Each DTR row carries the full sizing pipeline applied to one opportunity:
``raw_score → penalized_score → final_score → tier → final_size``.
The cockpit aggregates the latest N rows to render a 4-stage funnel.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cockpit.state_replay_metrics import _latest_export_dir


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error"]


class SizingRow(BaseModel, frozen=True):
    pair: str
    engine_id: str
    raw_score: float
    penalized_score: float
    final_score: float
    candidate_size: float
    final_size: float
    tier: str
    decision_state: str
    expected_edge_bps: float
    expected_cost: float
    realized_cost: float
    gross_return: float
    ce_expected: float


class SizingChainSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    rows: tuple[SizingRow, ...] = ()

    @property
    def avg_raw_score(self) -> float:
        return _avg(r.raw_score for r in self.rows)

    @property
    def avg_penalized_score(self) -> float:
        return _avg(r.penalized_score for r in self.rows)

    @property
    def avg_final_score(self) -> float:
        return _avg(r.final_score for r in self.rows)

    @property
    def avg_final_size(self) -> float:
        return _avg(r.final_size for r in self.rows)


def _avg(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def _parse_row(payload: dict) -> SizingRow | None:
    try:
        return SizingRow(
            pair=str(payload.get("pair", "")),
            engine_id=str(payload.get("engine_id", "")),
            raw_score=float(payload.get("raw_score", 0.0) or 0.0),
            penalized_score=float(payload.get("penalized_score", 0.0) or 0.0),
            final_score=float(payload.get("final_score", 0.0) or 0.0),
            candidate_size=float(payload.get("candidate_size", 0.0) or 0.0),
            final_size=float(payload.get("final_size", 0.0) or 0.0),
            tier=str(payload.get("tier", "")),
            decision_state=str(payload.get("decision_state", "")),
            expected_edge_bps=float(payload.get("expected_edge_bps", 0.0) or 0.0),
            expected_cost=float(payload.get("expected_cost", 0.0) or 0.0),
            realized_cost=float(payload.get("realized_cost", 0.0) or 0.0),
            gross_return=float(payload.get("gross_return", 0.0) or 0.0),
            ce_expected=float(payload.get("ce_expected", 0.0) or 0.0),
        )
    except (TypeError, ValueError):
        return None


def read_sizing_chain(auto_exports_root: Path, *, max_rows: int = 50) -> SizingChainSnapshot:
    latest = _latest_export_dir(auto_exports_root)
    if latest is None:
        return SizingChainSnapshot(source_status="missing")
    path = latest / "replay_dtr.jsonl"
    if not path.is_file():
        return SizingChainSnapshot(source_status="missing", source_path=str(path))
    rows: list[SizingRow] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                row = _parse_row(payload)
                if row is not None:
                    rows.append(row)
                if len(rows) >= max_rows:
                    break
    except OSError as exc:
        _logger.warning("Cannot read sizing chain %s: %s", path, exc)
        return SizingChainSnapshot(source_status="parse_error", source_path=str(path))
    return SizingChainSnapshot(
        source_status="ok" if rows else "missing",
        source_path=str(path),
        rows=tuple(rows),
    )


__all__ = ["SizingChainSnapshot", "SizingRow", "read_sizing_chain"]
