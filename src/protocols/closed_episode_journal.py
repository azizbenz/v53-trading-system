"""Append-only closed A/C episode journal for Engine D historical linkage and replay evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from interface_contracts import (
    EpisodeCloseReason,
    EpisodeRef,
)
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999


class ClosedEpisodeJournalManifest(BaseModel):
    """Audit manifest for a flushed closed-episode journal snapshot."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    record_count: int = Field(..., ge=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    flushed_at_ns: int = Field(..., ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    last_closed_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)


class ClosedEpisodeJournal:
    """Append-only closed-episode journal with deterministic snapshot persistence."""

    def __init__(self, flush_dir: Path | None = None) -> None:
        self._records: list[EpisodeRef] = []
        self._serialized_lines: list[str] = []
        self._records_by_pair: dict[str, list[EpisodeRef]] = {}
        self._records_by_engine: dict[str, list[EpisodeRef]] = {}
        self._flush_dir = Path(flush_dir) if flush_dir is not None else None
        self._last_flush_index = 0

    def append(self, record: EpisodeRef) -> EpisodeRef:
        serialized = record.model_dump_json()
        self._records.append(record)
        self._serialized_lines.append(serialized)
        self._records_by_pair.setdefault(record.pair, []).append(record)
        self._records_by_engine.setdefault(record.engine_id_of_origin.value, []).append(record)
        return record

    def append_batch(self, records: tuple[EpisodeRef, ...]) -> int:
        for record in records:
            self.append(record)
        return len(records)

    def read(self) -> tuple[EpisodeRef, ...]:
        return tuple(self._records)

    def get_by_pair(self, pair: str) -> tuple[EpisodeRef, ...]:
        return tuple(self._records_by_pair.get(pair.upper().strip(), ()))

    def get_by_engine(self, engine_id: EngineId) -> tuple[EpisodeRef, ...]:
        return tuple(self._records_by_engine.get(engine_id.value, ()))

    def eligible_for_engine_d(
        self,
        *,
        pair: str,
        side: Side,
        as_of_ns: int | None = None,
        lookback_ns: int | None = None,
    ) -> tuple[EpisodeRef, ...]:
        normalized_pair = pair.upper().strip()
        earliest_ns = None
        if as_of_ns is not None and lookback_ns is not None:
            earliest_ns = max(0, as_of_ns - lookback_ns)

        eligible = [
            record
            for record in self._records_by_pair.get(normalized_pair, ())
            if record.side == side
            and record.is_d_eligible
            and (as_of_ns is None or record.closed_at_ns <= as_of_ns)
            and (earliest_ns is None or record.closed_at_ns >= earliest_ns)
        ]
        eligible.sort(key=lambda record: record.closed_at_ns, reverse=True)
        return tuple(eligible)

    def most_recent_eligible_for_engine_d(
        self,
        *,
        pair: str,
        side: Side,
        as_of_ns: int | None = None,
        lookback_ns: int | None = None,
    ) -> EpisodeRef | None:
        eligible = self.eligible_for_engine_d(
            pair=pair,
            side=side,
            as_of_ns=as_of_ns,
            lookback_ns=lookback_ns,
        )
        if not eligible:
            return None
        return eligible[0]

    @property
    def size(self) -> int:
        return len(self._records)

    @property
    def pending_flush_count(self) -> int:
        return len(self._records) - self._last_flush_index

    def flush_to_disk(
        self,
        flush_dir: Path | None = None,
        *,
        flushed_at_ns: int | None = None,
    ) -> ClosedEpisodeJournalManifest | None:
        target_dir = Path(flush_dir) if flush_dir is not None else self._flush_dir
        if target_dir is None:
            return None

        jsonl_text = self._build_jsonl_text()
        jsonl_path = target_dir / "closed_episodes.jsonl"
        manifest_path = target_dir / "closed_episode_manifest.json"
        atomic_write_text(jsonl_path, jsonl_text)

        manifest = ClosedEpisodeJournalManifest(
            record_count=len(self._records),
            sha256=self._compute_sha256(jsonl_text),
            flushed_at_ns=flushed_at_ns or self._infer_flush_timestamp_ns(),
            last_closed_at_ns=self._records[-1].closed_at_ns if self._records else None,
        )
        atomic_write_json(manifest_path, manifest.model_dump(mode="json"))
        self._last_flush_index = len(self._records)
        return manifest

    @classmethod
    def load_from_disk(cls, flush_dir: Path) -> "ClosedEpisodeJournal":
        target_dir = Path(flush_dir)
        jsonl_path = target_dir / "closed_episodes.jsonl"
        manifest_path = target_dir / "closed_episode_manifest.json"

        journal = cls(flush_dir=target_dir)
        if not jsonl_path.exists():
            return journal

        jsonl_text = jsonl_path.read_text(encoding="utf-8")
        if manifest_path.exists():
            manifest = ClosedEpisodeJournalManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
            actual_sha = cls._compute_sha256(jsonl_text)
            if manifest.sha256 != actual_sha:
                raise ValueError("closed episode journal manifest hash mismatch")

        for line in jsonl_text.splitlines():
            if not line.strip():
                continue
            journal.append(EpisodeRef.model_validate_json(line))

        journal._last_flush_index = len(journal._records)
        return journal

    def _build_jsonl_text(self) -> str:
        if not self._serialized_lines:
            return ""
        return "\n".join(self._serialized_lines) + "\n"

    def _infer_flush_timestamp_ns(self) -> int:
        if self._records:
            return self._records[-1].closed_at_ns
        return 1_700_000_000_000_000_000

    @staticmethod
    def _compute_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ClosedEpisodeJournalSink:
    """Minimal adapter exposing an append-only closed-episode sink."""

    def __init__(self, journal: ClosedEpisodeJournal) -> None:
        self._journal = journal

    def record_closed_episode(self, episode_ref: EpisodeRef) -> None:
        self._journal.append(episode_ref)


__all__ = [
    "ClosedEpisodeJournal",
    "ClosedEpisodeJournalManifest",
    "ClosedEpisodeJournalSink",
    "EpisodeCloseReason",
    "EpisodeRef",
]
