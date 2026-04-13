"""Tests Module 2 â€” version_registry: diff manifest detectable, changelog canonique."""

import pytest

from manifest_registry.version_registry import (
    CHANGELOG,
    MANIFEST_VERSION,
    ChangeType,
    ManifestChange,
    ManifestDiff,
    ManifestSnapshot,
    ModuleSnapshot,
    build_current_snapshot,
    diff_snapshots,
    get_changelog,
    get_changes_since,
    get_manifest_version,
)


# â”€â”€â”€ CHANGELOG CANONIQUE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestChangelogCanonique:
    """Changelog must be static, deterministic, and well-formed."""

    def test_manifest_version_is_string(self):
        assert isinstance(get_manifest_version(), str)
        assert len(get_manifest_version()) > 0

    def test_changelog_is_not_empty(self):
        assert len(CHANGELOG) >= 2

    def test_changelog_first_entry_is_initial(self):
        assert CHANGELOG[0].change_type == ChangeType.INITIAL

    def test_changelog_entries_are_frozen(self):
        for entry in CHANGELOG:
            with pytest.raises(Exception):
                entry.version = "hacked"  # type: ignore[misc]

    def test_changelog_no_dynamic_timestamps(self):
        """ManifestChange must NOT have a timestamp field."""
        for entry in CHANGELOG:
            assert not hasattr(entry, "timestamp"), (
                "Changelog entries must not have dynamic timestamps"
            )

    def test_changelog_versions_monotonic(self):
        """Versions in changelog should be in order."""
        versions = [e.version for e in CHANGELOG]
        assert versions == sorted(versions)

    def test_get_changes_since(self):
        changes = get_changes_since("1.0.0")
        assert len(changes) >= 1
        assert changes[0].version == "1.1.0"

    def test_get_changes_since_latest_returns_empty(self):
        changes = get_changes_since(MANIFEST_VERSION)
        assert len(changes) == 0

    def test_get_changes_since_unknown_returns_empty(self):
        changes = get_changes_since("0.0.0")
        assert len(changes) == 0


# â”€â”€â”€ SNAPSHOT BUILDER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestSnapshotBuilder:
    """build_current_snapshot() must produce a coherent snapshot."""

    def test_snapshot_has_version(self):
        snap = build_current_snapshot()
        assert snap.version == MANIFEST_VERSION

    def test_snapshot_has_all_modules(self):
        from manifest_registry.module_inventory import MODULES

        snap = build_current_snapshot()
        snap_names = {m.module_name for m in snap.modules}
        inv_names = {m.module_name for m in MODULES}
        assert snap_names == inv_names

    def test_snapshot_modules_have_dependencies(self):
        snap = build_current_snapshot()
        # interface_contracts has zero deps
        ic = next(m for m in snap.modules if m.module_name == "interface_contracts")
        assert ic.dependencies == frozenset()
        # manifest_registry depends on interface_contracts
        mr = next(m for m in snap.modules if m.module_name == "manifest_registry")
        assert "interface_contracts" in mr.dependencies

    def test_snapshot_is_frozen(self):
        snap = build_current_snapshot()
        with pytest.raises(Exception):
            snap.version = "hacked"  # type: ignore[misc]

    def test_snapshot_deterministic(self):
        """Two consecutive snapshots must be identical."""
        s1 = build_current_snapshot()
        s2 = build_current_snapshot()
        assert s1 == s2


# â”€â”€â”€ DIFF ENGINE â€” MODULE ADDED / REMOVED â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffModuleAddedRemoved:
    """Diff must detect module additions and removals."""

    def _base_snapshot(self) -> ManifestSnapshot:
        return ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                ),
                ModuleSnapshot(
                    module_name="mod_b",
                    status="planned",
                    build_stage=2,
                    profile_scope="light",
                ),
            ),
        )

    def test_detect_module_added(self):
        old = self._base_snapshot()
        new = ManifestSnapshot(
            version="1.1.0",
            modules=old.modules + (
                ModuleSnapshot(
                    module_name="mod_c",
                    status="planned",
                    build_stage=3,
                    profile_scope="common",
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert "mod_c" in diff.modules_added

    def test_detect_module_removed(self):
        old = self._base_snapshot()
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(old.modules[0],),  # removed mod_b
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert "mod_b" in diff.modules_removed

    def test_no_changes_identical(self):
        old = self._base_snapshot()
        diff = diff_snapshots(old, old)
        assert not diff.has_changes
        assert diff.modules_added == ()
        assert diff.modules_removed == ()


# â”€â”€â”€ DIFF ENGINE â€” STATUS CHANGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffStatusChanged:
    """Diff must detect status changes."""

    def test_detect_status_change(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="planned",
                    build_stage=1,
                    profile_scope="common",
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert len(diff.status_changed) == 1
        name, old_status, new_status = diff.status_changed[0]
        assert name == "mod_a"
        assert old_status == "planned"
        assert new_status == "active"


# â”€â”€â”€ DIFF ENGINE â€” BUILD STAGE CHANGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffBuildStageChanged:
    """Diff must detect build stage changes."""

    def test_detect_build_stage_change(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="planned",
                    build_stage=1,
                    profile_scope="common",
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="planned",
                    build_stage=3,
                    profile_scope="common",
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert len(diff.stage_changed) == 1
        name, old_stage, new_stage = diff.stage_changed[0]
        assert name == "mod_a"
        assert old_stage == 1
        assert new_stage == 3


# â”€â”€â”€ DIFF ENGINE â€” PROFILE CHANGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffProfileChanged:
    """Diff must detect profile scope changes."""

    def test_detect_profile_change(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="light",
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="complete",
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert len(diff.profile_changed) == 1
        name, old_profile, new_profile = diff.profile_changed[0]
        assert name == "mod_a"
        assert old_profile == "light"
        assert new_profile == "complete"


# â”€â”€â”€ DIFF ENGINE â€” DEPENDENCY CHANGE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffDependencyChanged:
    """Diff must detect dependency additions/removals."""

    def test_detect_dependency_added(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                    dependencies=frozenset({"mod_b"}),
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                    dependencies=frozenset({"mod_b", "mod_c"}),
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert len(diff.deps_added) == 1
        name, added = diff.deps_added[0]
        assert name == "mod_a"
        assert "mod_c" in added

    def test_detect_dependency_removed(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                    dependencies=frozenset({"mod_b", "mod_c"}),
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",
                    build_stage=1,
                    profile_scope="common",
                    dependencies=frozenset({"mod_b"}),
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert len(diff.deps_removed) == 1
        name, removed = diff.deps_removed[0]
        assert name == "mod_a"
        assert "mod_c" in removed


# â”€â”€â”€ DIFF ENGINE â€” COMBINED CHANGES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.mark.build1
class TestDiffCombined:
    """Test diff with multiple simultaneous changes."""

    def test_multiple_changes_detected(self):
        old = ManifestSnapshot(
            version="1.0.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="planned",
                    build_stage=1,
                    profile_scope="common",
                ),
                ModuleSnapshot(
                    module_name="mod_b",
                    status="planned",
                    build_stage=2,
                    profile_scope="light",
                ),
            ),
        )
        new = ManifestSnapshot(
            version="1.1.0",
            modules=(
                ModuleSnapshot(
                    module_name="mod_a",
                    status="active",       # status changed
                    build_stage=1,
                    profile_scope="common",
                ),
                # mod_b removed
                ModuleSnapshot(
                    module_name="mod_c",   # new module
                    status="planned",
                    build_stage=3,
                    profile_scope="complete",
                ),
            ),
        )
        diff = diff_snapshots(old, new)
        assert diff.has_changes
        assert "mod_c" in diff.modules_added
        assert "mod_b" in diff.modules_removed
        assert len(diff.status_changed) == 1
        assert diff.status_changed[0][0] == "mod_a"

    def test_diff_on_current_snapshot_is_stable(self):
        """Diffing current snapshot against itself yields no changes."""
        snap = build_current_snapshot()
        diff = diff_snapshots(snap, snap)
        assert not diff.has_changes
