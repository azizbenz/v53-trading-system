"""
GEM-19 — Atomic I/O: write-tmp-then-rename for all state persistence.

Invariant: a crash at any point must never leave a half-written state file.
Pattern: write to .tmp, fsync, then os.replace (atomic on same filesystem).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text atomically via tmp-file + os.replace.

    Guarantees:
    - No partial writes visible at ``path``.
    - fsync before rename to survive power loss.
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_", suffix=".partial")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        # Clean up tmp on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Serialize ``data`` to JSON and write atomically."""
    content = json.dumps(data, ensure_ascii=False, indent=indent, default=str)
    atomic_write_text(path, content)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write raw bytes atomically via tmp-file + os.replace."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_", suffix=".partial")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
