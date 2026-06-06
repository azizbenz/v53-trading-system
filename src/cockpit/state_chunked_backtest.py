"""Cockpit state reader for chunked (map-reduce) backtest runs, Phase 3.

Surfaces a run produced by ``scripts/run_chunked_backtest.py`` and
``scripts/reduce_backtest_chunks.py`` to the dashboard. Reads, from a run root:

  - ``global_synthesis.json`` (the reduce output; authoritative aggregates), and/or
  - ``chunk_index.json`` plus per-chunk ``chunks/<label>/chunk_manifest.json``
    (live, pre-reduce: lets the grid render before the reduce step has run).

Pure and read-only: returns a typed view-model the template consumes. Never
raises on missing, malformed, or partial files; a not-yet-reduced or absent run
yields explicit ``found`` flags so the page can render an honest state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


_STATUS_BADGE = {
    "CHUNK_COMPLETE": "ok",
    "MISSING": "missing",
}


def _badge_for(status: str) -> str:
    normalized = str(status or "").upper()
    if normalized in _STATUS_BADGE:
        return _STATUS_BADGE[normalized]
    if "BLOCKED" in normalized:
        return "blocked"
    if "FAILED" in normalized:
        return "failed"
    return "missing"


@dataclass(frozen=True)
class ChunkGridEntry:
    label: str
    status: str
    badge: str
    total_wall_s: float
    engine_native_s: float
    candidate_count: int | None
    b2_final_status: str


@dataclass(frozen=True)
class ChunkedRunView:
    found: bool
    run_root: str
    run_id: str = ""
    start: str = ""
    end: str = ""
    granularity: str = ""
    chunk_count: int = 0
    has_synthesis: bool = False
    coverage: dict = field(default_factory=dict)
    performance: dict = field(default_factory=dict)
    economic: dict = field(default_factory=dict)
    data_quality: dict = field(default_factory=dict)
    b2_final_status_counts: dict = field(default_factory=dict)
    pooled_statistical_validation: str = ""
    grid: tuple[ChunkGridEntry, ...] = ()
    error: str = ""


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _load_json(path: Path) -> dict:
    try:
        return _as_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return {}


def _num(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _grid_from_synthesis(per_chunk: object) -> tuple[ChunkGridEntry, ...]:
    entries: list[ChunkGridEntry] = []
    for raw_chunk in _as_list(per_chunk):
        c = _as_dict(raw_chunk)
        if not c:
            continue
        status = str(c.get("status", "UNKNOWN"))
        entries.append(
            ChunkGridEntry(
                label=str(c.get("chunk_label", "")),
                status=status,
                badge=_badge_for(status),
                total_wall_s=round(_num(c.get("total_wall_s")), 1),
                engine_native_s=round(_num(c.get("engine_native_s")), 1),
                candidate_count=_int_or_none(c.get("candidate_count")),
                b2_final_status=str(c.get("b2_final_status") or ""),
            )
        )
    return tuple(entries)


def _grid_from_index(run_root: Path, index: dict) -> tuple[ChunkGridEntry, ...]:
    """Live grid (pre-reduce): read each chunk's manifest under chunks/<label>/."""
    entries: list[ChunkGridEntry] = []
    for raw_chunk in _as_list(index.get("chunks", [])):
        c = _as_dict(raw_chunk)
        label = str(c.get("chunk_label", ""))
        if not label:
            continue
        manifest = _load_json(run_root / "chunks" / label / "chunk_manifest.json")
        index_status = str(c.get("status") or "")
        status = str(manifest.get("status") or ("DRY_RUN" if index_status == "DRY_RUN" else "MISSING"))
        phases = _as_dict(manifest.get("phases"))
        b2 = _as_dict(phases.get("B2"))
        b1 = _as_dict(phases.get("B1"))
        entries.append(
            ChunkGridEntry(
                label=label,
                status=status,
                badge=_badge_for(status),
                total_wall_s=round(_num(manifest.get("total_wall_s")), 1),
                engine_native_s=round(_num(b2.get("engine_native_materialization_s")), 1),
                candidate_count=_int_or_none(b1.get("candidate_count")),
                b2_final_status=str(b2.get("final_status") or ""),
            )
        )
    return tuple(entries)


def _coverage_key_for_badge(badge: str) -> str:
    if badge == "ok":
        return "complete"
    if badge in {"blocked", "failed", "missing"}:
        return badge
    return "missing"


def read_chunked_run(run_root: Path | str) -> ChunkedRunView:
    """Read a chunked-run root into a dashboard view-model. Never raises."""
    root = Path(run_root)
    try:
        is_run_dir = root.is_dir()
    except OSError:
        is_run_dir = False
    if not is_run_dir:
        return ChunkedRunView(found=False, run_root=str(root), error="run root not found")

    synthesis = _load_json(root / "global_synthesis.json")
    index = _load_json(root / "chunk_index.json")
    if not synthesis and not index:
        return ChunkedRunView(
            found=False,
            run_root=str(root),
            error="no chunk_index.json / global_synthesis.json (not a chunked run)",
        )

    if synthesis:
        grid = _grid_from_synthesis(synthesis.get("per_chunk", []))
        return ChunkedRunView(
            found=True,
            run_root=str(root),
            has_synthesis=True,
            run_id=str(synthesis.get("run_id") or index.get("run_id") or root.name),
            start=str(synthesis.get("start") or ""),
            end=str(synthesis.get("end") or ""),
            granularity=str(synthesis.get("granularity") or ""),
            chunk_count=int(_num(synthesis.get("chunk_count"))) or len(grid),
            coverage=_as_dict(synthesis.get("coverage")),
            performance=_as_dict(synthesis.get("performance")),
            economic=_as_dict(synthesis.get("economic")),
            data_quality=_as_dict(synthesis.get("data_quality")),
            b2_final_status_counts=_as_dict(synthesis.get("b2_final_status_counts")),
            pooled_statistical_validation=str(synthesis.get("pooled_statistical_validation") or ""),
            grid=grid,
        )

    # Pre-reduce: build a live view from the index plus per-chunk manifests.
    grid = _grid_from_index(root, index)
    coverage = {"complete": 0, "blocked": 0, "failed": 0, "missing": 0}
    for entry in grid:
        coverage[_coverage_key_for_badge(entry.badge)] += 1
    expected_chunk_count = int(_num(index.get("chunk_count")))
    if expected_chunk_count > len(grid):
        coverage["missing"] += expected_chunk_count - len(grid)
    return ChunkedRunView(
        found=True,
        run_root=str(root),
        has_synthesis=False,
        run_id=str(index.get("run_id") or root.name),
        start=str(index.get("start") or ""),
        end=str(index.get("end") or ""),
        granularity=str(index.get("granularity") or ""),
        chunk_count=expected_chunk_count or len(grid),
        coverage=coverage,
        grid=grid,
        pooled_statistical_validation="PENDING_REDUCE",
        error="reduce not run yet; run scripts/reduce_backtest_chunks.py for pooled aggregates",
    )


@dataclass(frozen=True)
class ChunkedRunSummary:
    run_id: str
    run_root: str
    has_synthesis: bool
    start: str
    end: str
    granularity: str
    chunk_count: int
    complete: int
    blocked: int
    failed: int
    missing: int


def discover_chunked_runs(parent: Path | str) -> tuple[ChunkedRunSummary, ...]:
    """List chunked runs directly under ``parent`` (child dirs containing
    ``chunk_index.json`` or ``global_synthesis.json``), newest name last. Never
    raises; reuses :func:`read_chunked_run` per child for an honest summary.
    """
    root = Path(parent)
    try:
        children = sorted((c for c in root.iterdir() if c.is_dir()), key=lambda p: p.name)
    except OSError:
        return ()
    summaries: list[ChunkedRunSummary] = []
    for child in children:
        if not (
            (child / "chunk_index.json").is_file()
            or (child / "global_synthesis.json").is_file()
        ):
            continue
        view = read_chunked_run(child)
        if not view.found:
            continue
        cov = _as_dict(view.coverage)
        summaries.append(
            ChunkedRunSummary(
                run_id=view.run_id,
                run_root=view.run_root,
                has_synthesis=view.has_synthesis,
                start=view.start,
                end=view.end,
                granularity=view.granularity,
                chunk_count=view.chunk_count,
                complete=int(_num(cov.get("complete"))),
                blocked=int(_num(cov.get("blocked"))),
                failed=int(_num(cov.get("failed"))),
                missing=int(_num(cov.get("missing"))),
            )
        )
    return tuple(summaries)
