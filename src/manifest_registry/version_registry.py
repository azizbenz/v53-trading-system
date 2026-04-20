"""
4.5.5 — Version Registry: canonical versioning of manifest state.

Deterministic, pure, testable. No dynamic timestamps at import.

Provides:
- MANIFEST_VERSION: current version string
- CHANGELOG: canonical, static history of manifest changes
- ManifestSnapshot: frozen snapshot of the full manifest state
- diff_snapshots(): detect additions, removals, status/stage changes between two states
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ─── CHANGE TYPES ─────────────────────────────────────────────────────


class ChangeType(StrEnum):
    INITIAL = "initial"
    MODULE_ADDED = "module_added"
    MODULE_REMOVED = "module_removed"
    STATUS_CHANGED = "status_changed"
    DEPENDENCY_ADDED = "dependency_added"
    DEPENDENCY_REMOVED = "dependency_removed"
    BUILD_STAGE_CHANGED = "build_stage_changed"
    PROFILE_CHANGED = "profile_changed"


# ─── CHANGELOG ENTRY ──────────────────────────────────────────────────


class ManifestChange(BaseModel, frozen=True):
    """Single changelog entry. Fully static — no dynamic fields."""

    version: str
    change_type: ChangeType
    module_name: str = Field(default="")
    description: str


# ─── MANIFEST VERSION ────────────────────────────────────────────────

MANIFEST_VERSION = "1.4.0"

CHANGELOG: tuple[ManifestChange, ...] = (
    ManifestChange(
        version="1.0.0",
        change_type=ChangeType.INITIAL,
        description="Initial manifest: interface_contracts defined",
    ),
    ManifestChange(
        version="1.1.0",
        change_type=ChangeType.MODULE_ADDED,
        module_name="manifest_registry",
        description="Added manifest_registry module (Build-1 step 2)",
    ),
    ManifestChange(
        version="1.2.0",
        change_type=ChangeType.MODULE_ADDED,
        module_name="local_replay_runtime",
        description="Added LOCAL_REPLAY scaffold module to the canonical manifest",
    ),
    ManifestChange(
        version="1.2.0",
        change_type=ChangeType.MODULE_ADDED,
        module_name="backtest_artifact_import",
        description="Added controlled artifact import scaffold to the canonical manifest",
    ),
    ManifestChange(
        version="1.2.0",
        change_type=ChangeType.MODULE_ADDED,
        module_name="meta_learning",
        description="Added Build-9X governed scaffold to the canonical manifest",
    ),
    ManifestChange(
        version="1.3.0",
        change_type=ChangeType.STATUS_CHANGED,
        module_name="monitoring",
        description="Activated the real Build-10 monitoring backend",
    ),
    ManifestChange(
        version="1.3.0",
        change_type=ChangeType.STATUS_CHANGED,
        module_name="ui",
        description="Activated the locked Build-10 operator UI backend surface",
    ),
    ManifestChange(
        version="1.4.0",
        change_type=ChangeType.STATUS_CHANGED,
        module_name="meta_learning",
        description="Activated the governed Build-9X review and export layer",
    ),
)


# ─── MANIFEST SNAPSHOT ───────────────────────────────────────────────


class ModuleSnapshot(BaseModel, frozen=True):
    """Minimal frozen snapshot of a single module's state."""

    module_name: str
    status: str
    build_stage: int
    profile_scope: str
    dependencies: frozenset[str] = Field(default_factory=frozenset)


class ManifestSnapshot(BaseModel, frozen=True):
    """Complete frozen snapshot of the manifest state at a point in time."""

    version: str
    modules: tuple[ModuleSnapshot, ...]


# ─── DIFF RESULT ─────────────────────────────────────────────────────


class ManifestDiff(BaseModel, frozen=True):
    """Result of comparing two ManifestSnapshots."""

    modules_added: tuple[str, ...] = ()
    modules_removed: tuple[str, ...] = ()
    status_changed: tuple[tuple[str, str, str], ...] = ()   # (name, old, new)
    stage_changed: tuple[tuple[str, int, int], ...] = ()    # (name, old, new)
    profile_changed: tuple[tuple[str, str, str], ...] = ()  # (name, old, new)
    deps_added: tuple[tuple[str, frozenset[str]], ...] = ()  # (name, added_deps)
    deps_removed: tuple[tuple[str, frozenset[str]], ...] = ()  # (name, removed_deps)

    @property
    def has_changes(self) -> bool:
        """Return True if any difference was detected."""
        return bool(
            self.modules_added
            or self.modules_removed
            or self.status_changed
            or self.stage_changed
            or self.profile_changed
            or self.deps_added
            or self.deps_removed
        )


# ─── QUERY HELPERS ───────────────────────────────────────────────────


def get_manifest_version() -> str:
    """Return the current manifest version."""
    return MANIFEST_VERSION


def get_changelog() -> tuple[ManifestChange, ...]:
    """Return the full canonical changelog."""
    return CHANGELOG


def get_changes_since(version: str) -> tuple[ManifestChange, ...]:
    """Return all changelog entries after a given version."""
    if version not in {entry.version for entry in CHANGELOG}:
        return ()

    def _parse(value: str) -> tuple[int, ...]:
        try:
            return tuple(int(part) for part in value.split("."))
        except ValueError:
            return ()

    target = _parse(version)
    if not target:
        return ()

    return tuple(entry for entry in CHANGELOG if _parse(entry.version) > target)


# ─── SNAPSHOT BUILDER ────────────────────────────────────────────────


def build_current_snapshot() -> ManifestSnapshot:
    """Build a snapshot from the current live manifest state.

    Uses module_inventory and dependency_registry as source of truth.
    """
    from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES
    from manifest_registry.module_inventory import MODULES

    module_snaps: list[ModuleSnapshot] = []
    for m in MODULES:
        module_snaps.append(
            ModuleSnapshot(
                module_name=m.module_name,
                status=m.status.value,
                build_stage=m.build_stage,
                profile_scope=m.profile_scope.value,
                dependencies=ALLOWED_DEPENDENCIES.get(m.module_name, frozenset()),
            )
        )
    return ManifestSnapshot(version=MANIFEST_VERSION, modules=tuple(module_snaps))


# ─── DIFF ENGINE ─────────────────────────────────────────────────────


def diff_snapshots(old: ManifestSnapshot, new: ManifestSnapshot) -> ManifestDiff:
    """Compare two ManifestSnapshots and return all detected differences.

    Detects:
    - Module additions / removals
    - Status changes
    - Build stage changes
    - Profile scope changes
    - Dependency additions / removals
    """
    old_map: dict[str, ModuleSnapshot] = {m.module_name: m for m in old.modules}
    new_map: dict[str, ModuleSnapshot] = {m.module_name: m for m in new.modules}

    old_names = set(old_map.keys())
    new_names = set(new_map.keys())

    modules_added = tuple(sorted(new_names - old_names))
    modules_removed = tuple(sorted(old_names - new_names))

    status_changed: list[tuple[str, str, str]] = []
    stage_changed: list[tuple[str, int, int]] = []
    profile_changed: list[tuple[str, str, str]] = []
    deps_added: list[tuple[str, frozenset[str]]] = []
    deps_removed: list[tuple[str, frozenset[str]]] = []

    common = old_names & new_names
    for name in sorted(common):
        o = old_map[name]
        n = new_map[name]

        if o.status != n.status:
            status_changed.append((name, o.status, n.status))
        if o.build_stage != n.build_stage:
            stage_changed.append((name, o.build_stage, n.build_stage))
        if o.profile_scope != n.profile_scope:
            profile_changed.append((name, o.profile_scope, n.profile_scope))

        added = n.dependencies - o.dependencies
        removed = o.dependencies - n.dependencies
        if added:
            deps_added.append((name, added))
        if removed:
            deps_removed.append((name, removed))

    return ManifestDiff(
        modules_added=modules_added,
        modules_removed=modules_removed,
        status_changed=tuple(status_changed),
        stage_changed=tuple(stage_changed),
        profile_changed=tuple(profile_changed),
        deps_added=tuple(deps_added),
        deps_removed=tuple(deps_removed),
    )
