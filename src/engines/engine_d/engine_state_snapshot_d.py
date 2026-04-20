"""Append-only persistence for Engine D consecutive-stop state snapshots."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from interface_contracts import Side
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text

from .consecutive_stop_counter_d import ConsecutiveStopStateD


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999


class EngineDStateSnapshot(BaseModel):
    """Frozen per-(pair, side) state snapshot for Engine D restart continuity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    pair: str = Field(..., min_length=1)
    side: Side
    captured_at_ns: int = Field(..., ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    state: ConsecutiveStopStateD

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.upper().strip()
        if not normalized:
            raise ValueError("EngineDStateSnapshot.pair must be non-empty")
        return normalized


class EngineDStateSnapshotManifest(BaseModel):
    """Audit manifest for a flushed Engine D state snapshot journal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    snapshot_count: int = Field(..., ge=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    flushed_at_ns: int = Field(..., ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    last_captured_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)


class EngineDStateSnapshotStore:
    """Append-only JSONL store for Engine D consecutive-stop state snapshots."""

    def __init__(self, flush_dir: Path | None = None) -> None:
        self._snapshots: list[EngineDStateSnapshot] = []
        self._serialized_lines: list[str] = []
        self._snapshots_by_key: dict[tuple[str, Side], list[EngineDStateSnapshot]] = {}
        self._flush_dir = Path(flush_dir) if flush_dir is not None else None
        self._last_flush_index = 0

    def append(self, snapshot: EngineDStateSnapshot) -> EngineDStateSnapshot:
        serialized = snapshot.model_dump_json()
        self._snapshots.append(snapshot)
        self._serialized_lines.append(serialized)
        self._snapshots_by_key.setdefault((snapshot.pair, snapshot.side), []).append(snapshot)
        return snapshot

    def append_state(
        self,
        *,
        pair: str,
        side: Side,
        state: ConsecutiveStopStateD,
        captured_at_ns: int,
    ) -> EngineDStateSnapshot:
        snapshot = EngineDStateSnapshot(
            pair=pair,
            side=side,
            captured_at_ns=captured_at_ns,
            state=state,
        )
        return self.append(snapshot)

    def read(self) -> tuple[EngineDStateSnapshot, ...]:
        return tuple(self._snapshots)

    def latest_snapshot(
        self,
        *,
        pair: str,
        side: Side,
    ) -> EngineDStateSnapshot | None:
        normalized_pair = pair.upper().strip()
        candidates = self._snapshots_by_key.get((normalized_pair, side), ())
        if not candidates:
            return None
        return max(candidates, key=lambda snapshot: snapshot.captured_at_ns)

    def latest_state(
        self,
        *,
        pair: str,
        side: Side,
    ) -> ConsecutiveStopStateD | None:
        snapshot = self.latest_snapshot(pair=pair, side=side)
        if snapshot is None:
            return None
        return snapshot.state

    @property
    def size(self) -> int:
        return len(self._snapshots)

    @property
    def pending_flush_count(self) -> int:
        return len(self._snapshots) - self._last_flush_index

    def flush_to_disk(
        self,
        flush_dir: Path | None = None,
        *,
        flushed_at_ns: int | None = None,
    ) -> EngineDStateSnapshotManifest | None:
        target_dir = Path(flush_dir) if flush_dir is not None else self._flush_dir
        if target_dir is None:
            return None

        jsonl_text = self._build_jsonl_text()
        jsonl_path = target_dir / "engine_d_state_snapshots.jsonl"
        manifest_path = target_dir / "engine_d_state_snapshot_manifest.json"
        atomic_write_text(jsonl_path, jsonl_text)

        manifest = EngineDStateSnapshotManifest(
            snapshot_count=len(self._snapshots),
            sha256=self._compute_sha256(jsonl_text),
            flushed_at_ns=flushed_at_ns or self._infer_flush_timestamp_ns(),
            last_captured_at_ns=(
                max(snapshot.captured_at_ns for snapshot in self._snapshots)
                if self._snapshots
                else None
            ),
        )
        atomic_write_json(manifest_path, manifest.model_dump(mode="json"))
        self._last_flush_index = len(self._snapshots)
        return manifest

    @classmethod
    def load_from_disk(cls, flush_dir: Path) -> "EngineDStateSnapshotStore":
        target_dir = Path(flush_dir)
        jsonl_path = target_dir / "engine_d_state_snapshots.jsonl"
        manifest_path = target_dir / "engine_d_state_snapshot_manifest.json"

        store = cls(flush_dir=target_dir)
        if not jsonl_path.exists():
            return store

        jsonl_text = jsonl_path.read_text(encoding="utf-8")
        if manifest_path.exists():
            manifest = EngineDStateSnapshotManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
            actual_sha = cls._compute_sha256(jsonl_text)
            if manifest.sha256 != actual_sha:
                raise ValueError("engine_d state snapshot manifest hash mismatch")

        for line in jsonl_text.splitlines():
            if not line.strip():
                continue
            store.append(EngineDStateSnapshot.model_validate_json(line))

        store._last_flush_index = len(store._snapshots)
        return store

    def _build_jsonl_text(self) -> str:
        if not self._serialized_lines:
            return ""
        return "\n".join(self._serialized_lines) + "\n"

    def _infer_flush_timestamp_ns(self) -> int:
        if self._snapshots:
            return max(snapshot.captured_at_ns for snapshot in self._snapshots)
        return 1_700_000_000_000_000_000

    @staticmethod
    def _compute_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = [
    "EngineDStateSnapshot",
    "EngineDStateSnapshotManifest",
    "EngineDStateSnapshotStore",
]
