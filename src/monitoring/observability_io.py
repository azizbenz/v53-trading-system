"""I/O helpers for persisted observability exports."""

from __future__ import annotations

from pathlib import Path

from interface_contracts.atomic_io import atomic_write_text
from monitoring.contracts import ObservabilityExport


def write_observability_text_payload(
    export: ObservabilityExport,
    path: Path,
) -> Path:
    """Persist the text payload of a standard observability export."""

    atomic_write_text(path, export.text_payload + "\n")
    return Path(path)


__all__ = ["write_observability_text_payload"]
