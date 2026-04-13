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


def write_node_exporter_textfile_payload(
    export: ObservabilityExport,
    collector_dir: Path,
    *,
    filename: str,
) -> Path:
    """Persist an observability export into a node_exporter textfile collector directory."""

    target_path = Path(collector_dir) / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return write_observability_text_payload(export, target_path)


__all__ = [
    "write_observability_text_payload",
    "write_node_exporter_textfile_payload",
]
