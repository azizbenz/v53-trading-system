"""Versioned dataset provider for deterministic AAOIFI pair-screening snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml

from .contracts import AaoifiPairScreeningRegistry, AaoifiPairScreeningSnapshot


def load_pair_screening_registry(path: Path | str) -> AaoifiPairScreeningRegistry:
    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Pair screening registry {registry_path} does not exist")
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Pair screening registry {registry_path} must deserialize to a mapping")
    normalized = dict(payload)
    snapshots_raw = normalized.get("snapshots", ())
    if not isinstance(snapshots_raw, list | tuple):
        raise ValueError("pair screening registry snapshots must deserialize to a sequence")
    normalized["snapshots"] = tuple(
        AaoifiPairScreeningSnapshot.model_validate(entry) for entry in snapshots_raw
    )
    return AaoifiPairScreeningRegistry.model_validate(normalized)


class FilePairScreeningProvider:
    """Read-only pair-screening provider backed by a local versioned registry."""

    def __init__(self, registry_path: Path | str) -> None:
        self._registry_path = Path(registry_path)
        self._registry = load_pair_screening_registry(self._registry_path)
        self._snapshots_by_pair = {
            snapshot.pair.strip().upper(): snapshot for snapshot in self._registry.snapshots
        }

    @property
    def registry(self) -> AaoifiPairScreeningRegistry:
        return self._registry

    def get_snapshot(self, pair: str) -> AaoifiPairScreeningSnapshot | None:
        return self._snapshots_by_pair.get(pair.strip().upper())


__all__ = ["FilePairScreeningProvider", "load_pair_screening_registry"]
