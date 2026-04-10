"""
BS-68 regression — ShadowSessionRegistry.append_entries had no rollback on _persist failure.

Blind spot: append_entries() did:
    self._state.entries.extend(entries)   # memory mutated
    self._persist()                        # if this raises → memory ≠ disk

If _persist() raised (disk full, permission denied), the entries were already in
self._state.entries. The next call to append_entries with the same dates raised
ValueError("already recorded session_date") — permanently deadlocking the registry.
The only recovery was a process restart, which reloaded the pre-persist disk state
and silently discarded the in-memory additions.

Fix: extend into a copy; only commit if _persist() succeeds; roll back on failure.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from protocols.shadow_session_registry import ShadowSessionEntry, ShadowSessionRegistry


def _entry(session_date: str, n: int = 1) -> ShadowSessionEntry:
    return ShadowSessionEntry(
        session_date=session_date,
        counter_day_number=n,
        correlation_id=f"corr-{session_date}",
        run_id=f"run-{session_date}",
        artifact_id=f"art-{session_date}",
        lineage_version="v1.0",
    )


class TestBS68AppendEntriesRollback:

    def test_successful_append_persists_entries(self, repo_tmp_path):
        """Baseline: successful append is visible via get_entries()."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)
        entry = _entry("2026-01-01")

        registry.append_entries((entry,))

        assert len(registry.get_entries()) == 1
        assert registry.get_entries()[0].session_date == "2026-01-01"

    def test_persist_failure_rolls_back_memory(self, repo_tmp_path):
        """BS-68: if _persist() raises, in-memory state must be unchanged."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)
        entry = _entry("2026-01-01")

        with patch.object(registry, "_persist", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                registry.append_entries((entry,))

        # Memory must be rolled back — no entry should be visible
        assert registry.get_entries() == ()

    def test_persist_failure_allows_retry(self, repo_tmp_path):
        """BS-68: after rollback, same entry can be appended on retry."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)
        entry = _entry("2026-01-01")

        # First attempt fails
        with patch.object(registry, "_persist", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                registry.append_entries((entry,))

        # Retry succeeds (no longer raises "already recorded")
        registry.append_entries((entry,))

        assert len(registry.get_entries()) == 1

    def test_persist_failure_does_not_corrupt_existing_entries(self, repo_tmp_path):
        """BS-68: existing entries must survive a failed append attempt."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)
        existing = _entry("2026-01-01", n=1)
        registry.append_entries((existing,))

        new_entry = _entry("2026-01-02", n=2)
        with patch.object(registry, "_persist", side_effect=OSError("out of space")):
            with pytest.raises(OSError):
                registry.append_entries((new_entry,))

        # Only the previously-persisted entry must remain
        entries = registry.get_entries()
        assert len(entries) == 1
        assert entries[0].session_date == "2026-01-01"

    def test_persist_failure_does_not_block_different_date(self, repo_tmp_path):
        """BS-68: after rollback, a different date can also be appended."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)

        with patch.object(registry, "_persist", side_effect=OSError("full")):
            with pytest.raises(OSError):
                registry.append_entries((_entry("2026-02-01", n=1),))

        # Different date should be accepted without "already recorded" error
        registry.append_entries((_entry("2026-02-02", n=2),))

        assert len(registry.get_entries()) == 1

    def test_empty_entries_never_calls_persist(self, repo_tmp_path):
        """append_entries(()) must be a no-op — no persist call, no state change."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)

        with patch.object(registry, "_persist", side_effect=AssertionError("must not call _persist")):
            registry.append_entries(())  # must not raise

        assert registry.get_entries() == ()
