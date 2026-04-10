"""
BS-62 regression — DTRStore crash protection and O(N²) serialization fix.

Blind spot: DTRStore had no atexit handler (records lost on crash) and
re-serialized ALL records on every flush_to_disk() call (O(N²) cost).

Fix: atexit.register(self.flush_to_disk) in __init__, plus eager
serialization at persist() time so flush_to_disk() uses cached dicts.
"""

from __future__ import annotations

import atexit
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.trace_persistence_layer import DTRStore


# ── helpers ────────────────────────────────────────────────────────────────

def _record(pair: str = "BTCUSDT", dtr_id: str = "dtr_001") -> DTRRecord:
    return DTRRecord(
        dtr_id=dtr_id,
        timestamp=1700000000.0,
        pair=pair,
        engine_id="engine_a",
        decision_state=DecisionState.EVALUATED,
    )


# ── atexit registration ─────────────────────────────────────────────────────

class TestAtexitRegistration:
    def test_atexit_registered_on_init(self, repo_tmp_path):
        """flush_to_disk is registered with atexit when flush_dir is given."""
        with patch("atexit.register") as mock_register:
            store = DTRStore(flush_dir=repo_tmp_path)
            mock_register.assert_called_once_with(store.flush_to_disk)

    def test_atexit_registered_even_without_flush_dir(self):
        """atexit.register is always called (flush_to_disk is a no-op when no dir)."""
        with patch("atexit.register") as mock_register:
            store = DTRStore()
            mock_register.assert_called_once_with(store.flush_to_disk)

    def test_atexit_flush_writes_file_on_simulated_exit(self, repo_tmp_path):
        """Calling flush_to_disk() directly (as atexit would) writes the file."""
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(_record("BTCUSDT"))
        store.persist(_record("ETHUSDT"))

        # simulate atexit call without explicit path
        store.flush_to_disk()

        output = repo_tmp_path / "dtr_records.json"
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_atexit_flush_no_flush_dir_does_not_raise(self):
        """flush_to_disk() without a flush_dir returns 0 and does not raise."""
        store = DTRStore()
        store.persist(_record())
        assert store.flush_to_disk() == 0  # no-op, no crash


# ── eager serialization / O(N²) fix ────────────────────────────────────────

class TestEagerSerialization:
    def test_serialized_cache_populated_before_flush(self, repo_tmp_path):
        """_serialized is populated at persist() time — before any flush_to_disk() call."""
        store = DTRStore(flush_dir=repo_tmp_path)
        r = _record("BTCUSDT")

        store.persist(r)

        # _serialized must already have content before any flush
        assert len(store._serialized) == 1
        assert store._serialized[0]["pair"] == "BTCUSDT"
        # No flush has happened yet — last_flush_index is still 0
        assert store._last_flush_index == 0

    def test_serialized_cache_length_matches_records(self, repo_tmp_path):
        """_serialized cache stays in sync with _records after each persist."""
        store = DTRStore(flush_dir=repo_tmp_path)
        for i in range(5):
            store.persist(_record(dtr_id=f"dtr_{i:03d}"))

        assert len(store._serialized) == len(store._records) == 5

    def test_flush_uses_serialized_cache_not_records(self, repo_tmp_path):
        """flush_to_disk writes content from the serialized cache."""
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(_record("BTCUSDT"))
        store.persist(_record("SOLUSDT"))
        store.flush_to_disk()

        output = repo_tmp_path / "dtr_records.json"
        data = json.loads(output.read_text(encoding="utf-8"))
        pairs = [d["pair"] for d in data]
        assert pairs == ["BTCUSDT", "SOLUSDT"]

    def test_incremental_flush_still_writes_full_array(self, repo_tmp_path):
        """Second incremental flush writes full array (all records), not just new ones."""
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(_record("BTCUSDT"))
        store.flush_to_disk()  # flush 1

        store.persist(_record("ETHUSDT"))
        store.flush_to_disk()  # flush 2

        output = repo_tmp_path / "dtr_records.json"
        data = json.loads(output.read_text(encoding="utf-8"))
        # Full array: both records present after second flush
        assert len(data) == 2
        assert data[0]["pair"] == "BTCUSDT"
        assert data[1]["pair"] == "ETHUSDT"

    def test_incremental_flush_returns_only_new_count(self, repo_tmp_path):
        """flush_to_disk() return value counts only new records since last flush."""
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(_record())
        store.persist(_record("ETHUSDT"))
        assert store.flush_to_disk() == 2

        store.persist(_record("SOLUSDT"))
        assert store.flush_to_disk() == 1  # only the new one

        assert store.flush_to_disk() == 0  # nothing new

    def test_pending_flush_count_correct_after_incremental(self, repo_tmp_path):
        """pending_flush_count tracks records not yet flushed."""
        store = DTRStore(flush_dir=repo_tmp_path)
        store.persist(_record())
        store.persist(_record("ETHUSDT"))
        assert store.pending_flush_count == 2
        store.flush_to_disk()
        assert store.pending_flush_count == 0

        store.persist(_record("SOLUSDT"))
        assert store.pending_flush_count == 1
