"""Tests for interface_contracts.atomic_io — GEM-19 atomic write utilities."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from interface_contracts.atomic_io import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
)


pytestmark = pytest.mark.build1


@pytest.fixture
def tmp_dir(repo_tmp_path):
    return repo_tmp_path


class TestAtomicWriteText:
    """Tests for atomic_write_text."""

    def test_writes_exact_text(self, tmp_dir):
        target = tmp_dir / "out.txt"
        atomic_write_text(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_writes_unicode(self, tmp_dir):
        target = tmp_dir / "unicode.txt"
        content = "données marché — prix: 42000€"
        atomic_write_text(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_overwrites_existing_file(self, tmp_dir):
        target = tmp_dir / "overwrite.txt"
        target.write_text("old content", encoding="utf-8")
        atomic_write_text(target, "new content")
        assert target.read_text(encoding="utf-8") == "new content"

    def test_no_temp_file_left_after_success(self, tmp_dir):
        target = tmp_dir / "clean.txt"
        atomic_write_text(target, "data")
        # Only the target file should exist
        files = list(tmp_dir.iterdir())
        assert len(files) == 1
        assert files[0].name == "clean.txt"

    def test_creates_parent_directories(self, tmp_dir):
        target = tmp_dir / "sub" / "deep" / "file.txt"
        atomic_write_text(target, "nested")
        assert target.read_text(encoding="utf-8") == "nested"

    def test_empty_string(self, tmp_dir):
        target = tmp_dir / "empty.txt"
        atomic_write_text(target, "")
        assert target.read_text(encoding="utf-8") == ""

    def test_large_content(self, tmp_dir):
        target = tmp_dir / "large.txt"
        content = "x" * 100_000
        atomic_write_text(target, content)
        assert target.read_text(encoding="utf-8") == content


class TestAtomicWriteJson:
    """Tests for atomic_write_json."""

    def test_writes_dict(self, tmp_dir):
        target = tmp_dir / "data.json"
        data = {"key": "value", "count": 42}
        atomic_write_json(target, data)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_writes_list(self, tmp_dir):
        target = tmp_dir / "list.json"
        data = [1, 2, 3, "four"]
        atomic_write_json(target, data)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_json_is_indented(self, tmp_dir):
        target = tmp_dir / "indented.json"
        atomic_write_json(target, {"a": 1}, indent=2)
        content = target.read_text(encoding="utf-8")
        assert "\n" in content  # indented = multiline

    def test_overwrites_existing_json(self, tmp_dir):
        target = tmp_dir / "overwrite.json"
        atomic_write_json(target, {"old": True})
        atomic_write_json(target, {"new": True})
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == {"new": True}

    def test_no_temp_file_left(self, tmp_dir):
        target = tmp_dir / "clean.json"
        atomic_write_json(target, {"x": 1})
        files = list(tmp_dir.iterdir())
        assert len(files) == 1

    def test_nested_structure(self, tmp_dir):
        target = tmp_dir / "nested.json"
        data = {
            "state": "tripped",
            "details": {"reason": "divergence", "ts": 1700000000.0},
            "history": [1, 2, 3],
        }
        atomic_write_json(target, data)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data


class TestAtomicWriteBytes:
    """Tests for atomic_write_bytes."""

    def test_writes_exact_bytes(self, tmp_dir):
        target = tmp_dir / "data.bin"
        content = b"\x00\x01\x02\xff"
        atomic_write_bytes(target, content)
        assert target.read_bytes() == content

    def test_overwrites_existing_bytes(self, tmp_dir):
        target = tmp_dir / "overwrite.bin"
        target.write_bytes(b"old")
        atomic_write_bytes(target, b"new")
        assert target.read_bytes() == b"new"

    def test_no_temp_file_left(self, tmp_dir):
        target = tmp_dir / "clean.bin"
        atomic_write_bytes(target, b"data")
        files = list(tmp_dir.iterdir())
        assert len(files) == 1

    def test_empty_bytes(self, tmp_dir):
        target = tmp_dir / "empty.bin"
        atomic_write_bytes(target, b"")
        assert target.read_bytes() == b""

    def test_creates_parent_directories(self, tmp_dir):
        target = tmp_dir / "sub" / "file.bin"
        atomic_write_bytes(target, b"nested")
        assert target.read_bytes() == b"nested"


class TestAtomicWriteFailurePath:
    """Tests for failure behavior — temp file cleanup."""

    def test_text_failure_cleans_temp(self, tmp_dir):
        """If write fails, no partial temp file should remain."""
        target = tmp_dir / "fail.txt"
        with patch("interface_contracts.atomic_io.os.fsync", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                atomic_write_text(target, "data")
        # Target should not exist
        assert not target.exists()
        # No temp files left
        tmp_files = [f for f in tmp_dir.iterdir() if ".tmp_" in f.name]
        assert len(tmp_files) == 0

    def test_json_failure_cleans_temp(self, tmp_dir):
        """JSON write failure should not leave temp files."""
        target = tmp_dir / "fail.json"
        with patch("interface_contracts.atomic_io.os.fsync", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                atomic_write_json(target, {"key": "value"})
        assert not target.exists()
        tmp_files = [f for f in tmp_dir.iterdir() if ".tmp_" in f.name]
        assert len(tmp_files) == 0
