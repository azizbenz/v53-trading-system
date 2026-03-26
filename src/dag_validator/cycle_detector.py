"""
5.5.3 — Cycle Detector: detect cycles in the module dependency DAG.

Uses DFS-based topological sort to find all cycles.
Works on both the declared manifest graph and the observed import graph.
"""

from __future__ import annotations

from pydantic import BaseModel

from dag_validator.import_scanner import ScanResult


class CycleResult(BaseModel, frozen=True):
    """Result of cycle detection."""

    cycles: tuple[tuple[str, ...], ...]  # each cycle is a tuple of module names
    has_cycles: bool

    @property
    def cycle_count(self) -> int:
        return len(self.cycles)


def _find_cycles_dfs(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Find all unique cycles in a directed graph using DFS.

    Returns a list of cycles, each represented as a tuple of module names
    forming the cycle path.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in graph}
    path: list[str] = []
    cycles: list[tuple[str, ...]] = []
    seen_cycles: set[frozenset[str]] = set()

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbor in sorted(graph.get(node, set())):
            if neighbor not in color:
                color[neighbor] = WHITE

            if color[neighbor] == GRAY:
                # Found a cycle — extract it
                cycle_start = path.index(neighbor)
                cycle = tuple(path[cycle_start:])
                cycle_key = frozenset(cycle)
                if cycle_key not in seen_cycles:
                    seen_cycles.add(cycle_key)
                    cycles.append(cycle)
            elif color[neighbor] == WHITE:
                dfs(neighbor)

        path.pop()
        color[node] = BLACK

    for node in sorted(graph.keys()):
        if color.get(node, WHITE) == WHITE:
            dfs(node)

    return cycles


def detect_cycles_in_manifest(
    allowed_dependencies: dict[str, frozenset[str]],
) -> CycleResult:
    """Detect cycles in the declared manifest dependency graph.

    Args:
        allowed_dependencies: The manifest whitelist from dependency_registry.

    Returns:
        CycleResult with any cycles found.
    """
    graph: dict[str, set[str]] = {
        mod: set(deps) for mod, deps in allowed_dependencies.items()
    }
    cycles = _find_cycles_dfs(graph)
    return CycleResult(cycles=tuple(cycles), has_cycles=len(cycles) > 0)


def detect_cycles_in_observed(scan: ScanResult) -> CycleResult:
    """Detect cycles in the actually observed import graph.

    Args:
        scan: ScanResult from import_scanner.

    Returns:
        CycleResult with any cycles found.
    """
    graph: dict[str, set[str]] = {}
    for imp in scan.imports:
        if imp.source_module == imp.target_module:
            continue  # self-imports don't create cycles
        graph.setdefault(imp.source_module, set()).add(imp.target_module)
        # Ensure target is in graph even if it has no outgoing edges
        graph.setdefault(imp.target_module, set())

    cycles = _find_cycles_dfs(graph)
    return CycleResult(cycles=tuple(cycles), has_cycles=len(cycles) > 0)
