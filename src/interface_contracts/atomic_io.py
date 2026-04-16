"""Atomic file I/O helpers — write-and-rename pattern to prevent partial/corrupt writes."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write *text* to *path* atomically (write to tmp then rename).

    Creates parent directories if they do not exist.
    Calls fsync before rename to ensure durability.
    Raises on I/O failure; leaves the target file unchanged.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp_{uuid.uuid4().hex}"
    try:
        with tmp.open("w", encoding=encoding) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as exc:
        _ = exc
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, data: object, *, indent: int | None = None) -> None:
    """Write *data* as UTF-8 JSON to *path* atomically (write to tmp then rename).

    Creates parent directories if they do not exist.
    Calls fsync before rename to ensure durability.
    Raises on serialization or I/O failure; leaves the target file unchanged.
    """
    atomic_write_text(path, json.dumps(data, indent=indent), encoding="utf-8")


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write *data* as raw bytes to *path* atomically (write to tmp then rename).

    Creates parent directories if they do not exist.
    Calls fsync before rename to ensure durability.
    Raises on I/O failure; leaves the target file unchanged.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp_{uuid.uuid4().hex}"
    try:
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as exc:
        _ = exc
        tmp.unlink(missing_ok=True)
        raise


__all__ = ["atomic_write_bytes", "atomic_write_json", "atomic_write_text"]
